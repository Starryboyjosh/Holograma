"""Construcción del contexto de cámara para el prompt del LLM.

Módulo neutro (sin dependencias de la CLI ``call``) para que tanto ``call``
como ``app.services.vision.CameraContextProvider`` usen la **misma** lógica de
contexto. Rompe la costura ``call ↔ llm_backend``: el LLM ya no importa la CLI
para obtener el contexto de cámara; lo recibe inyectado por el orquestador.
"""

from __future__ import annotations

import time

# Si el texto del usuario contiene alguno, se inyectan objetos/uniforme al LLM.
_VISUAL_OBJECT_HINTS = (
    "uniforme",
    "ropa",
    "vestido",
    "vestiment",
    "camis",
    "polo",
    "qué llevo",
    "que llevo",
    "qué traigo",
    "que traigo",
    "me ves",
    "puedes ver",
    "qué ves",
    "que ves",
    "qué hay",
    "que hay",
    "descríbeme",
    "describeme",
    "delante",
    "enfrente",
)


def is_visual_object_question(text: str | None) -> bool:
    """True si el visitante pregunta por lo visual / ropa (no un saludo genérico)."""
    if not text:
        return False
    t = text.lower().strip()
    return any(h in t for h in _VISUAL_OBJECT_HINTS)


def build_camera_context(analysis: dict, *, include_objects: bool = False) -> str:
    """Convierte un análisis de cámara en texto para el prompt del LLM.

    Si no hay personas en el frame actual pero las hubo hace poco (≤60s),
    reutiliza el último análisis con gente para no "perder" el contexto visual
    entre frames.

    ``include_objects``: solo True cuando el visitante pregunta por uniforme/ropa/
    qué ves. En saludos y otras preguntas NO se listan objetos para que el
    modelo no mencione el uniforme sin que se lo pidan.
    """
    global _last_person_time, _cached_person_analysis

    if not isinstance(analysis, dict):
        analysis = {}

    if analysis.get("person_count", 0) > 0:
        _last_person_time = time.time()
        _cached_person_analysis = dict(analysis)
        active_analysis = analysis
    else:
        if time.time() - _last_person_time <= 60.0 and _cached_person_analysis:
            active_analysis = _cached_person_analysis
        else:
            active_analysis = analysis

    parts: list[str] = []
    pc = int(active_analysis.get("person_count", 0) or 0)
    if pc == 1:
        parts.append("Veo a una persona frente a ti en este momento.")
    elif pc > 1:
        parts.append(f"Veo a {pc} personas frente a ti en este momento.")
    else:
        parts.append("No veo a nadie frente a ti en este momento.")

    fd = active_analysis.get("face_description")
    if fd:
        parts.append(str(fd))

    if not include_objects:
        parts.append(
            "No menciones ropa, uniforme ni objetos detectados: el visitante "
            "no preguntó por eso en este turno."
        )
        return "\n".join(parts)

    # Deduplicar por etiqueta; conservar la mejor confianza.
    best: dict[str, float | None] = {}
    for o in active_analysis.get("custom_objects") or []:
        if not isinstance(o, dict):
            continue
        lab = str(o.get("label") or "").strip()
        if not lab:
            continue
        conf_raw = o.get("confidence")
        conf: float | None
        try:
            conf = float(conf_raw) if conf_raw is not None else None
        except (TypeError, ValueError):
            conf = None
        prev = best.get(lab)
        if lab not in best or (
            conf is not None and (prev is None or conf > prev)
        ):
            best[lab] = conf

    if best:
        detail_bits = []
        for lab, conf in list(best.items())[:8]:
            if conf is not None:
                detail_bits.append(f"«{lab}» (~{conf:.0%})")
            else:
                detail_bits.append(f"«{lab}»")
        parts.append(
            "El visitante SÍ pregunta por lo visual/ropa. "
            "Objetos confirmados: " + ", ".join(detail_bits) + "."
        )
        parts.append(
            "«Uniforme ITEE» = uniforme escolar del ITEE. Nómbralo con naturalidad."
        )
    else:
        parts.append(
            "El visitante pregunta por lo visual/ropa, pero no hay objetos "
            "confirmados (p. ej. Uniforme ITEE) en este momento. No inventes."
        )

    parts.append(
        "REGLA: describe SOLO lo de este bloque. No inventes objetos ni colores."
    )
    return "\n".join(parts)


# Estado de "última persona vista", compartido con call.py para mantener el
# contexto visual entre frames sin gente.
_last_person_time = 0.0
_cached_person_analysis: dict = {}
