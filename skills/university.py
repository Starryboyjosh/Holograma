"""Respuestas sobre UNEV. Los datos provienen de la fuente única y editable
``skills.unev_content`` (``data/unev_info.json``); aquí solo se da formato.
"""

from skills.unev_content import get_unev_info
from skills.utils import normalize_text

# Reexport para call.py / router (import histórico).
__all__ = [
    "normalize_text",
    "get_university_summary",
    "get_programs_summary",
    "get_program_info",
    "get_admission_info",
    "get_location_info",
    "get_approval_info",
    "get_website_info",
    "get_university_context",
    "invalidate_context_cache",
]

# Contexto de sistema para el LLM: se reutiliza entre turnos (antes se
# reconstruía en cada mensaje). Se invalida al editar unev_info.
_CONTEXT_CACHE: str | None = None


def invalidate_context_cache() -> None:
    """Limpia la caché de ``get_university_context`` (p. ej. tras editar JSON)."""
    global _CONTEXT_CACHE
    _CONTEXT_CACHE = None


def get_university_summary():
    info = get_unev_info()
    return (
        f"{info['name']} ({info['full_name']}) es una institución de "
        "educación superior hondureña con modelo 100% virtual. "
        f"{info['main_claim']} "
        f"Misión: {info['mission']} "
        f"Visión: {info['vision']} "
        f"Valores institucionales: {info['values']} "
        "Opera bajo un modelo cuatrimestral con ciclos intensivos de 11 semanas, "
        "ofreciendo carreras de Técnico Universitario con duración de 2 años. "
        "Su trayectoria inició en 2017 como 'Universidad Práctica' y se consolidó "
        "internacionalmente en EDUTECHNIA 2023 en Bogotá. "
        f"Liderazgo: {info['governance']}"
    )


def get_programs_summary():
    programs = get_unev_info()["programs"]
    listing = " ".join(
        f"{name.title()}: {desc}" for name, desc in programs.items()
    )
    return (
        "Actualmente UNEV ofrece carreras bajo el modelo de Técnico Universitario "
        "(Tecnólogo), con ciclos intensivos de 11 semanas y duración total de 2 años. "
        f"{listing}"
    )


def get_program_info(program_name):
    normalized_program_name = normalize_text(program_name)
    for program, description in get_unev_info()["programs"].items():
        normalized_program = normalize_text(program)
        if (
            normalized_program in normalized_program_name
            or normalized_program_name in normalized_program
        ):
            return f"{program.title()}: {description}"
    return (
        "Puedo darte información sobre Diseño Gráfico, Administración de Empresas "
        "y Programación Web. ¿Sobre cuál carrera te gustaría saber más?"
    )


def get_admission_info():
    """Admisión desde la fuente editable (evita texto duplicado/desactualizado)."""
    info = get_unev_info()
    req = (info.get("admission_requirements") or "").strip()
    programs = ", ".join(p.title() for p in info.get("programs", {}))
    if req:
        tail = (
            f" Puedes elegir entre: {programs}."
            if programs
            else ""
        )
        return f"Requisitos de admisión en UNEV: {req}{tail}"
    return (
        "Consulta los requisitos de admisión en la página oficial de UNEV o "
        "pregunta por una carrera concreta."
    )


def get_location_info():
    info = get_unev_info()
    return f"La dirección registrada de UNEV es: {info['address']} {info['infrastructure']}"


def get_approval_info():
    return get_unev_info()["approval"]


def get_website_info():
    return f"Puedes visitar la página oficial de UNEV en {get_unev_info()['website']}"


# Etiquetas legibles para el bloque de contexto del LLM (orden de lectura).
_CONTEXT_FIELD_LABELS: dict[str, str] = {
    "name": "Nombre corto / sigla",
    "full_name": "Nombre completo",
    "acronyms": "Siglas y expansión",
    "main_claim": "Diferenciador",
    "description": "Descripción",
    "mission": "Misión",
    "vision": "Visión",
    "values": "Valores",
    "approval": "Aprobación y validez de títulos",
    "governance": "Gobernanza y liderazgo",
    "address": "Dirección / sede",
    "infrastructure": "Infraestructura",
    "academic_model": "Modelo académico",
    "faculty": "Cuerpo docente",
    "student_support": "Acompañamiento estudiantil",
    "admission_requirements": "Requisitos de admisión",
    "social_projection": "Proyección social",
    "virtual_library": "Biblioteca virtual",
    "international_presence": "Presencia internacional",
    "website": "Sitio web oficial",
    "history": "Historia y trayectoria",
    "independence_note": "Independencia institucional (no confundir)",
    "itee_campus": "Campus ITEE y alianza",
    "expotech": "ExpoTech / feria tecnológica ITEE",
    "common_questions": "Preguntas frecuentes (respuestas oficiales)",
}


def get_university_context():
    """Contexto de sistema UNEV + Honduras (cacheado entre turnos del LLM).

    Entrega la información **completa** de ``data/unev_info.json`` (todos los
    campos de texto y la descripción íntegra de cada programa), sin resumir
    carreras a un listado de nombres.
    """
    global _CONTEXT_CACHE
    if _CONTEXT_CACHE is not None:
        return _CONTEXT_CACHE

    from skills.honduras import get_university_context as get_honduras_context
    from skills.unev_content import TEXT_FIELDS

    try:
        honduras_ctx = get_honduras_context()
    except Exception:
        honduras_ctx = ""

    info = get_unev_info()
    lines = [
        "Información institucional de UNEV (fuente completa; no inventes datos fuera de este bloque):",
        "Nota: la sigla correcta es UNEV (Instituto Universitario de Educación Virtual), "
        "nunca UNED ni otras confusiones de voz.",
    ]
    for key in TEXT_FIELDS:
        value = (info.get(key) or "").strip()
        if not value:
            continue
        label = _CONTEXT_FIELD_LABELS.get(key, key)
        lines.append(f"- {label}: {value}")

    programs = info.get("programs") or {}
    if programs:
        lines.append("- Programas (descripción completa de cada uno):")
        for name, desc in programs.items():
            lines.append(f"  * {str(name).title()}: {desc}")

    lines.append(
        "Si el visitante pregunta por un dato no incluido aquí, no inventes. "
        "Recomienda revisar la página oficial o contactar a UNEV."
    )
    unev_ctx = "\n".join(lines)
    _CONTEXT_CACHE = unev_ctx + "\n\n" + honduras_ctx
    return _CONTEXT_CACHE
