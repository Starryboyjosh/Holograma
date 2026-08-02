"""Orquestador de un turno de conversación (el corazón de la Fase 3).

Recibe un prompt y produce, por **un solo** emisor de eventos
(`ConnectionManager`), la secuencia que el frontend espera:

    status:streaming_started → text_chunk* → text_done
        → (si hay TTS) audio_status:processing → audio_status:completed

Con TTS streaming (default): el audio arranca en la primera cláusula lista
mientras el LLM sigue generando (menor latencia a primer audio). Sin TTS
streaming se puede forzar el comportamiento antiguo con
``HOLOGRAM_TTS_STREAM=0`` (habla el texto completo al final).

Contratos que codifica (y que `tests/test_app_services.py` blinda):

* **Un solo emisor.** Solo este servicio emite; el TTS NO reemite texto (la causa
  del atasco en "hablando", síntoma B). El texto sale una vez, desde el stream.
* **Nada bloqueante en el loop.** El TTS (Piper, sync y bloqueante) se ejecuta con
  `asyncio.to_thread`, nunca sobre el event loop.
* **Estado inyectado, no global.** LLM, conexión, cámara y TTS llegan por el
  constructor; no hay variables de módulo mutables ni monkey-patching.
* **Errores → evento `error`.** El frontend vuelve a `idle` al recibirlo.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator, Callable
from typing import Protocol

from app.services.llm import supports_history
from app.services.session_memory import get_session
from utils import pop_ready_speech


def _tts_stream_enabled() -> bool:
    return os.getenv("HOLOGRAM_TTS_STREAM", "1").lower() not in (
        "0",
        "false",
        "no",
        "off",
    )


class _LLM(Protocol):
    def stream(
        self,
        prompt: str,
        camera_context: str | None = None,
        history: list[dict] | None = None,
    ) -> AsyncIterator[str]: ...


class _Session(Protocol):
    def resolve(self, user_input: str) -> str: ...

    def observe(self, user_input: str, reply: str) -> None: ...

    def history(self) -> list[dict[str, str]]: ...


class _Connection(Protocol):
    async def broadcast(self, message: dict) -> None: ...


class _Camera(Protocol):
    def build_context(self, prompt: str) -> str | None: ...


class _HologramOrchestrator(Protocol):
    def start_turn(
        self,
        user_message: str,
        context: str | None = None,
        mode: str | None = None,
        skill: str | None = None,
    ) -> str: ...

    def observe_response_text(
        self,
        text: str,
        context_id: str | None = None,
    ) -> None: ...

    def mark_speaking(self) -> None: ...

    def finish_turn(self, context_id: str | None = None) -> bool: ...

    def fail_turn(
        self,
        error: Exception | None = None,
        context_id: str | None = None,
    ) -> bool: ...


class ConversationService:
    def __init__(
        self,
        llm: _LLM,
        connection: _Connection,
        camera: _Camera | None = None,
        speak: Callable[[str], None] | None = None,
        tts_done: Callable[[], None] | None = None,
        hologram_orchestrator: _HologramOrchestrator | None = None,
        session: _Session | None = None,
    ) -> None:
        self._llm = llm
        self._conn = connection
        self._camera = camera

        # `speak` es un callable SÍNCRONO (Piper bloquea);
        # se delega a un hilo.
        self._speak = speak

        # Cierre de turno TTS (p. ej. holograma → idle). Opcional.
        self._tts_done = tts_done
        self._hologram_orchestrator = hologram_orchestrator

        # Memoria de sesión (WAVE-06). Por defecto, el estado único del
        # proceso: hay un solo ConversationService a nivel de módulo que
        # difunde a todos los clientes, y la memoria debe ser de
        # dispositivo/sesión, no por conexión. Los tests pueden inyectar
        # una instancia propia.
        self._session = session if session is not None else get_session()

    async def _hologram_call(self, method: str, *args, **kwargs):
        """Ejecuta una operación del holograma sin romper la conversación."""
        orchestrator = self._hologram_orchestrator
        if orchestrator is None:
            return None

        try:
            callback = getattr(orchestrator, method)
            return await asyncio.to_thread(callback, *args, **kwargs)
        except Exception:
            # El control holográfico es fail-soft:
            # nunca debe interrumpir la conversación principal.
            return None

    async def _speak_piece(self, text: str) -> None:
        """Reproduce una pieza de texto sin bloquear el event loop."""
        if not self._speak or not text.strip():
            return

        await asyncio.to_thread(self._speak, text)

    async def _finish_tts(self) -> None:
        """Ejecuta el callback final del TTS de forma fail-soft."""
        if self._tts_done is None:
            return

        try:
            await asyncio.to_thread(self._tts_done)
        except Exception:
            pass

    async def handle_prompt(self, prompt: str) -> str:
        """Procesa un turno completo y devuelve el texto generado.

        Devuelve una cadena vacía cuando falla la generación principal.

        Una vez iniciado el contexto holográfico, `finish_turn()` se ejecuta
        siempre mediante el bloque `finally`, incluso si falla el stream,
        un broadcast, el TTS o la tarea es cancelada.

        Desde WAVE-06 el turno pasa por la memoria de sesión: las referencias
        sin antecedente («¿y cuánto dura?») se resuelven contra la entidad
        activa **antes** de llegar al LLM, el historial de los últimos N turnos
        viaja en el prompt y, al terminar, la respuesta se observa para el
        turno siguiente.
        """
        await self._conn.broadcast(
            {
                "type": "status",
                "status": "streaming_started",
            }
        )

        resolved = self._session.resolve(prompt)

        camera_context = (
            self._camera.build_context(resolved)
            if self._camera is not None
            else None
        )

        context_id = await self._hologram_call(
            "start_turn",
            resolved,
            context=camera_context,
        )

        history = self._session.history()
        stream_history = {"history": history} if supports_history(self._llm.stream) else {}

        chunks: list[str] = []
        speech_buf = ""
        first_speech = True
        audio_started = False
        stream_tts = bool(self._speak) and _tts_stream_enabled()

        try:
            try:
                async for chunk in self._llm.stream(
                    resolved,
                    camera_context=camera_context,
                    **stream_history,
                ):
                    chunks.append(chunk)

                    await self._hologram_call(
                        "observe_response_text",
                        chunk,
                        context_id,
                    )

                    await self._conn.broadcast(
                        {
                            "type": "text_chunk",
                            "text": chunk,
                        }
                    )

                    if not stream_tts:
                        continue

                    speech_buf += chunk
                    ready, speech_buf, first_speech = pop_ready_speech(
                        speech_buf,
                        first_speech,
                    )

                    for piece in ready:
                        if not audio_started:
                            await self._hologram_call("mark_speaking")
                            await self._conn.broadcast(
                                {
                                    "type": "audio_status",
                                    "status": "processing",
                                }
                            )
                            audio_started = True

                        await self._speak_piece(piece)

            except asyncio.CancelledError:
                await self._hologram_call(
                    "fail_turn",
                    RuntimeError("cancelled"),
                    context_id=context_id,
                )
                raise

            except Exception as error:
                await self._hologram_call(
                    "fail_turn",
                    error,
                    context_id=context_id,
                )

                await self._conn.broadcast(
                    {
                        "type": "error",
                        "message": str(error),
                    }
                )
                return ""

            full_text = "".join(chunks)

            self._session.observe(resolved, full_text)

            await self._conn.broadcast({"type": "text_done"})

            if self._speak and full_text.strip():
                try:
                    if stream_tts:
                        # Resto del buffer sin puntuación final o frase corta.
                        remainder = speech_buf.strip()

                        if remainder:
                            if not audio_started:
                                await self._hologram_call("mark_speaking")
                                await self._conn.broadcast(
                                    {
                                        "type": "audio_status",
                                        "status": "processing",
                                    }
                                )
                                audio_started = True

                            await self._speak_piece(remainder)

                        elif not audio_started:
                            # El stream no produjo cláusulas listas.
                            # Se reproduce el texto completo una sola vez.
                            await self._hologram_call("mark_speaking")
                            await self._conn.broadcast(
                                {
                                    "type": "audio_status",
                                    "status": "processing",
                                }
                            )
                            audio_started = True

                            await self._speak_piece(full_text)

                    else:
                        # Modo clásico: reproduce todo al terminar el stream.
                        await self._hologram_call("mark_speaking")
                        await self._conn.broadcast(
                            {
                                "type": "audio_status",
                                "status": "processing",
                            }
                        )
                        audio_started = True

                        await self._speak_piece(full_text)

                except asyncio.CancelledError:
                    await self._hologram_call(
                        "fail_turn",
                        RuntimeError("cancelled"),
                        context_id=context_id,
                    )
                    await self._finish_tts()
                    raise

                except Exception as error:
                    await self._hologram_call(
                        "fail_turn",
                        error,
                        context_id=context_id,
                    )

                    await self._conn.broadcast(
                        {
                            "type": "error",
                            "message": f"TTS: {error}",
                        }
                    )

                    await self._finish_tts()
                    return full_text

                if audio_started:
                    await self._conn.broadcast(
                        {
                            "type": "audio_status",
                            "status": "completed",
                        }
                    )
                    await self._finish_tts()

            return full_text

        finally:
            # Garantiza que:
            # - top vuelva a idle;
            # - center vuelva a Holomind;
            # - bottom reanude su rotación;
            # incluso si falla un broadcast, el TTS o la tarea se cancela.
            await self._hologram_call(
                "finish_turn",
                context_id,
            )
