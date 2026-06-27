"""Proveedor del contexto de cámara para el LLM.

Hoy `llm_backend.stream_llm_response` alcanza el estado global de `call`
(`_last_camera_analysis`) y su `_build_camera_context` con un import perezoso —ese
es el ciclo `call ↔ llm_backend`. Este proveedor sostiene el último análisis y
construye su contexto en un solo lugar inyectable, para que el orquestador se lo
pase explícitamente al LLM (ver `stream_llm_response(camera_context=...)`).

El *builder* por defecto reutiliza el `_build_camera_context` ya existente (import
perezoso, contenido a ESTE módulo), de modo que el ciclo queda en una sola costura
explícita y testeable, no esparcido por la capa de LLM.
"""

from collections.abc import Callable

# builder: análisis (dict) -> string de contexto para el prompt (o None).
ContextBuilder = Callable[[dict], str | None]


class CameraContextProvider:
    def __init__(self, builder: ContextBuilder | None = None) -> None:
        self._analysis: dict | None = None
        self._builder = builder

    @property
    def analysis(self) -> dict | None:
        return self._analysis

    def update(self, analysis: dict | None) -> None:
        """Registra el último análisis de la cámara (lo llamará VisionService)."""
        self._analysis = analysis

    def build_context(self) -> str | None:
        if not self._analysis:
            return None
        builder = self._builder or self._default_builder
        return builder(self._analysis)

    @staticmethod
    def _default_builder(analysis: dict) -> str | None:
        # Reutiliza la lógica existente sin reescribirla; el import perezoso evita
        # cargar la CLI completa salvo cuando de verdad se construye contexto.
        from call import _build_camera_context

        return _build_camera_context(analysis)
