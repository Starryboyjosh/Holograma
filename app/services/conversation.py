"""Orquestador de un turno de conversación (el corazón de la Fase 3).

Recibe un prompt y produce, por **un solo** emisor de eventos
(`ConnectionManager`), la secuencia que el frontend espera:

    status:streaming_started → text_chunk* → text_done
        → (si hay TTS) audio_status:processing → audio_status:completed

Contratos que codifica (y que `tests/test_app_services.py` blinda):

* **Un solo emisor.** Solo este servicio emite; el TTS NO reemite texto (la causa
  del atasco en "hablando", síntoma B). El texto sale una vez, desde el stream.
* **Nada bloqueante en el loop.** El TTS (Piper, sync y bloqueante) se ejecuta con
  `asyncio.to_thread`, nunca sobre el event loop.
* **Estado inyectado, no global.** LLM, conexión, cámara y TTS llegan por el
  constructor; no hay variables de módulo mutables ni monkey-patching.
* **Errores → evento `error`.** El frontend vuelve a `idle` al recibirlo.
"""

import asyncio
from collections.abc import Callable
from typing import Protocol


class _LLM(Protocol):
    def stream(self, prompt: str, camera_context: str | None = None): ...


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

    async def handle_prompt(self, prompt: str) -> str:
        """Procesa un turno completo y devuelve el texto generado ("" si falló)."""
        await self._conn.broadcast({"type": "status", "status": "streaming_started"})

        camera_context = self._camera.build_context() if self._camera else None

        chunks: list[str] = []
        try:
            async for chunk in self._llm.stream(prompt, camera_context=camera_context):
                chunks.append(chunk)
                await self._conn.broadcast({"type": "text_chunk", "text": chunk})
        except Exception as error:
            await self._conn.broadcast({"type": "error", "message": str(error)})
            return ""

        full_text = "".join(chunks)
        await self._conn.broadcast({"type": "text_done"})

        if self._speak and full_text.strip():
            await self._conn.broadcast({"type": "audio_status", "status": "processing"})
            try:
                # Piper es bloqueante: fuera del event loop con to_thread.
                await asyncio.to_thread(self._speak, full_text)
            except Exception as error:
                await self._conn.broadcast(
                    {"type": "error", "message": f"TTS: {error}"}
                )
                return full_text
            await self._conn.broadcast({"type": "audio_status", "status": "completed"})

        return full_text
