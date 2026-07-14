"""Construcción del contexto de cámara para el prompt del LLM.

Módulo neutro (sin dependencias de la CLI ``call``) para que tanto ``call``
como ``app.services.vision.CameraContextProvider`` usen la **misma** lógica de
contexto. Rompe la costura ``call ↔ llm_backend``: el LLM ya no importa la CLI
para obtener el contexto de cámara; lo recibe inyectado por el orquestador.
"""

import time


def build_camera_context(analysis: dict) -> str:
    """Convierte un análisis de cámara en texto para el prompt del LLM.

    Si no hay personas en el frame actual pero las hubo hace poco (≤60s),
    reutiliza el último análisis con gente para no "perder" el contexto visual
    entre frames.
    """
    global _last_person_time, _cached_person_analysis

    if analysis.get("person_count", 0) > 0:
        _last_person_time = time.time()
        _cached_person_analysis = analysis.copy()
        active_analysis = analysis
    else:
        if time.time() - _last_person_time <= 60.0:
            active_analysis = _cached_person_analysis
        else:
            active_analysis = analysis

    parts = []
    pc = active_analysis.get("person_count", 0)
    if pc == 1:
        parts.append("Veo a una persona frente a ti en este momento.")
    elif pc > 1:
        parts.append(f"Veo a {pc} personas frente a ti en este momento.")
    fd = active_analysis.get("face_description")
    if fd:
        parts.append(fd)
    co = active_analysis.get("custom_objects", [])
    if co:
        labels = list({o["label"] for o in co})
        parts.append(
            f"Objetos que reconozco visualmente frente a ti: {', '.join(labels[:5])}"
        )
    if not parts:
        parts.append("No veo a nadie frente a ti en este momento.")
    return "\n".join(parts)


# Estado de "última persona vista", compartido con call.py para mantener el
# contexto visual entre frames sin gente.
_last_person_time = 0.0
_cached_person_analysis: dict = {}
