"""Servicio de LLM: envuelve la **única** ruta async de generación.

`llm_backend.stream_llm_response` ya es la ruta async correcta (usa
`AsyncOpenAI`/`AsyncAnthropic`, selección de backend fuera del event loop). Este
servicio la expone como una interfaz inyectable para que el orquestador dependa de
un objeto y no del módulo —así se puede testear con un stream falso, sin tocar
proveedores ni red.
"""

from collections.abc import AsyncGenerator, Callable

# Una función de stream: (prompt, camera_context) -> async generator de fragmentos.
StreamFn = Callable[..., AsyncGenerator[str, None]]


class LLMService:
    def __init__(self, stream_fn: StreamFn | None = None) -> None:
        # Inyectable para los tests; por defecto, la ruta real (import perezoso para
        # no acoplar el import de este módulo a `llm_backend`/`provider_config`).
        self._stream_fn = stream_fn

    async def stream(
        self, prompt: str, camera_context: str | None = None
    ) -> AsyncGenerator[str, None]:
        stream_fn = self._stream_fn
        if stream_fn is None:
            import llm_backend

            stream_fn = llm_backend.stream_llm_response
        async for chunk in stream_fn(prompt, camera_context=camera_context):
            yield chunk
