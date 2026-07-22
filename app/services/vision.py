"""Proveedor del contexto de cámara para el LLM.

`llm_backend.stream_llm_response` recibe el contexto de cámara **inyectado**
por el orquestador (`camera_context=...`); este proveedor sostiene el último
análisis y lo construye en un solo lugar inyectable. El *builder* por defecto
usa la lógica neutra de `camera_context` (sin acoplarse a la CLI `call`),
así que el ciclo `call ↔ llm_backend` queda roto: ni `app/` ni `llm_backend`
importan `call` para obtener contexto de cámara.
"""

from collections.abc import Callable

from camera_context import build_camera_context, is_visual_object_question

# builder: (análisis, include_objects) -> string | None
ContextBuilder = Callable[[dict, bool], str | None]


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

    def build_context(self, prompt: str | None = None) -> str | None:
        if not self._analysis:
            return None
        include_objects = is_visual_object_question(prompt)
        builder = self._builder or self._default_builder
        return builder(self._analysis, include_objects)

    @staticmethod
    def _default_builder(analysis: dict, include_objects: bool = False) -> str | None:
        return build_camera_context(analysis, include_objects=include_objects)
