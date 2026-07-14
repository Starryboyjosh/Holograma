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

from utils import (
    _CLAUSE_RE,
    _MIN_FIRST_CHUNK_LEN,
    _MIN_SENTENCE_LEN,
    _SENTENCE_RE,
)


def _tts_stream_enabled() -> bool:
    return os.getenv("HOLOGRAM_TTS_STREAM", "1").lower() not in (
        "0",
        "false",
        "no",
        "off",
    )


def _pop_ready_speech(buf: str, first_chunk: bool) -> tuple[list[str], str, bool]:
    """Extrae cláusulas/oraciones listas para TTS desde un buffer de stream.

    Misma idea que ``call._split_into_chunks``: el primer fragmento usa cláusulas
    (latencia baja); el resto oraciones. Devuelve (piezas, buffer_restante, first).
    """
    ready: list[str] = []
    while buf:
        sep = _CLAUSE_RE if first_chunk else _SENTENCE_RE
        min_len = _MIN_FIRST_CHUNK_LEN if first_chunk else _MIN_SENTENCE_LEN
        matches = list(sep.finditer(buf))
        if not matches:
            break
        # Tomar la primera cláusula/oración completa lo bastante larga.
        match = matches[0]
        head = buf[: match.end()].strip()
        if len(head) < min_len:
            # Aún no hay material suficiente; esperar más tokens.
            break
        ready.append(head)
        buf = buf[match.end() :]
        first_chunk = False
    return ready, buf, first_chunk


class _LLM(Protocol):
    def stream(
        self, prompt: str, camera_context: str | None = None
    ) -> AsyncIterator[str]: ...


class _Connection(Protocol):
    async def broadcast(self, message: dict) -> None: ...


class _Camera(Protocol):
    def build_context(self) -> str | None: ...


class ConversationService:
    def __init__(
        self,
        llm: _LLM,
        connection: _Connection,
        camera: _Camera | None = None,
        speak: Callable[[str], None] | None = None,
    ) -> None:
        self._llm = llm
        self._conn = connection
        self._camera = camera
        # `speak` es un callable SÍNCRONO (Piper bloquea); se delega a un hilo.
        self._speak = speak

    async def _speak_piece(self, text: str) -> None:
        if not self._speak or not text.strip():
            return
        await asyncio.to_thread(self._speak, text)

    async def handle_prompt(self, prompt: str) -> str:
        """Procesa un turno completo y devuelve el texto generado ("" si falló)."""
        await self._conn.broadcast({"type": "status", "status": "streaming_started"})

        camera_context = self._camera.build_context() if self._camera else None

        chunks: list[str] = []
        speech_buf = ""
        first_speech = True
        audio_started = False
        stream_tts = bool(self._speak) and _tts_stream_enabled()

        try:
            async for chunk in self._llm.stream(prompt, camera_context=camera_context):
                chunks.append(chunk)
                await self._conn.broadcast({"type": "text_chunk", "text": chunk})
                if stream_tts:
                    speech_buf += chunk
                    ready, speech_buf, first_speech = _pop_ready_speech(
                        speech_buf, first_speech
                    )
                    for piece in ready:
                        if not audio_started:
                            await self._conn.broadcast(
                                {"type": "audio_status", "status": "processing"}
                            )
                            audio_started = True
                        await self._speak_piece(piece)
        except Exception as error:
            await self._conn.broadcast({"type": "error", "message": str(error)})
            return ""

        full_text = "".join(chunks)
        await self._conn.broadcast({"type": "text_done"})

        if self._speak and full_text.strip():
            try:
                if stream_tts:
                    # Resto del buffer (sin puntuación final o frase corta).
                    remainder = speech_buf.strip()
                    if remainder:
                        if not audio_started:
                            await self._conn.broadcast(
                                {"type": "audio_status", "status": "processing"}
                            )
                            audio_started = True
                        await self._speak_piece(remainder)
                    elif not audio_started:
                        # Stream no produjo cláusulas (respuesta muy corta):
                        # hablar el texto completo una vez.
                        await self._conn.broadcast(
                            {"type": "audio_status", "status": "processing"}
                        )
                        audio_started = True
                        await self._speak_piece(full_text)
                else:
                    # Modo clásico: un solo speak al final del stream.
                    await self._conn.broadcast(
                        {"type": "audio_status", "status": "processing"}
                    )
                    audio_started = True
                    await self._speak_piece(full_text)
            except Exception as error:
                await self._conn.broadcast(
                    {"type": "error", "message": f"TTS: {error}"}
                )
                return full_text
            if audio_started:
                await self._conn.broadcast(
                    {"type": "audio_status", "status": "completed"}
                )

        return full_text
