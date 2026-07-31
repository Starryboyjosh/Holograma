"""Respuestas sobre UNEV. Los datos provienen de la fuente única y editable
``skills.unev_content`` (``data/unev_info.json``); aquí solo se da formato.
"""

import sys

from skills.unev_content import TEXT_FIELDS, get_unev_info
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
    "get_context_sections",
    "context_section_keys",
    "invalidate_context_cache",
]

# Contexto de sistema para el LLM: se reutiliza entre turnos (antes se
# reconstruía en cada mensaje). Se invalida al editar unev_info.
_CONTEXT_CACHE: str | None = None

# Cada sección ya renderizada, por clave. Es la caché que hace barato pedir
# subconjuntos distintos en turnos distintos. `_CONTEXT_CACHE` se conserva
# aparte porque el bloque completo es, con diferencia, el subconjunto más
# pedido. Las dos las limpia `invalidate_context_cache`.
_SECTION_CACHE: dict[str, str] | None = None

# Claves desconocidas ya advertidas, para no repetir el aviso en cada turno.
_WARNED_UNKNOWN_SECTIONS: set[str] = set()


def invalidate_context_cache() -> None:
    """Limpia **todas** las cachés de contexto (p. ej. tras editar el JSON).

    Es el único punto de invalidación: `skills.unev_content._invalidate_skill_caches`
    llama acá. Si algún día se añade otra caché de contexto, se limpia también acá
    o el panel de administración editará contenido que el LLM nunca verá.
    """
    global _CONTEXT_CACHE, _SECTION_CACHE
    _CONTEXT_CACHE = None
    _SECTION_CACHE = None
    _WARNED_UNKNOWN_SECTIONS.clear()


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


# Pseudo-secciones: las partes del bloque que no son campos de texto de
# `unev_info`. Se nombran explícitamente para que un router pueda pedirlas igual
# que pide un campo.
PROGRAMS_SECTION = "programs"
HONDURAS_SECTION = "honduras"
PSEUDO_SECTIONS: tuple[str, ...] = (PROGRAMS_SECTION, HONDURAS_SECTION)

# Cabecera y cierre NO son secciones seleccionables: son guardarraíles.
# La cabecera evita que el STT convierta «UNEV» en «UNED»; el cierre prohíbe
# inventar datos. Un subconjunto pequeño es justo cuando más falta hacen, así
# que van **siempre**, incluso pidiendo una sola clave.
_HEADER_LINES: tuple[str, ...] = (
    "Información institucional de UNEV (fuente completa; no inventes datos fuera de este bloque):",
    "Nota: la sigla correcta es UNEV (Instituto Universitario de Educación Virtual), "
    "nunca UNED ni otras confusiones de voz.",
)
_CLOSING_LINE = (
    "Si el visitante pregunta por un dato no incluido aquí, no inventes. "
    "Recomienda revisar la página oficial o contactar a UNEV."
)


def context_section_keys() -> tuple[str, ...]:
    """Todas las claves válidas, en orden de lectura.

    Los 25 campos de ``TEXT_FIELDS`` seguidos de las pseudo-secciones. Pasarlas
    enteras a `get_context_sections` reproduce el bloque completo.
    """
    return tuple(TEXT_FIELDS) + PSEUDO_SECTIONS


def _warn_unknown_section(key: str) -> None:
    """Avisa una vez por clave desconocida, sin tumbar el turno.

    Un router que pide una clave que ya no existe no puede dejar sin respuesta al
    visitante que tiene delante: se ignora y se deja rastro. Va por stderr por lo
    mismo que la métrica de WAVE-03: stdout es el log humano del kiosco.
    """
    if key in _WARNED_UNKNOWN_SECTIONS:
        return
    _WARNED_UNKNOWN_SECTIONS.add(key)
    print(f"[contexto] sección desconocida, ignorada: {key!r}", file=sys.stderr, flush=True)


def _rendered_sections() -> dict[str, str]:
    """Cada sección ya formateada, por clave (cacheado).

    Un campo vacío en la fuente **no** aparece en el diccionario: así no produce
    una línea `- Etiqueta: ` colgada, igual que el `continue` del bloque original.
    """
    global _SECTION_CACHE
    if _SECTION_CACHE is not None:
        return _SECTION_CACHE

    info = get_unev_info()
    sections: dict[str, str] = {}
    for key in TEXT_FIELDS:
        value = (info.get(key) or "").strip()
        if not value:
            continue
        label = _CONTEXT_FIELD_LABELS.get(key, key)
        sections[key] = f"- {label}: {value}"

    programs = info.get("programs") or {}
    if programs:
        lines = ["- Programas (descripción completa de cada uno):"]
        lines.extend(f"  * {str(name).title()}: {desc}" for name, desc in programs.items())
        sections[PROGRAMS_SECTION] = "\n".join(lines)

    # Import diferido: `skills.honduras` lee su JSON al importarse y falla duro si
    # no está. Que eso no rompa el import de este módulo.
    try:
        from skills.honduras import get_university_context as get_honduras_context

        sections[HONDURAS_SECTION] = get_honduras_context()
    except Exception:
        # Igual que antes: sin Honduras el turno sigue, con contexto UNEV solo.
        sections[HONDURAS_SECTION] = ""

    _SECTION_CACHE = sections
    return sections


def get_context_sections(keys) -> str:
    """Contexto institucional con **sólo** las secciones pedidas.

    ``keys`` es cualquier iterable de claves de `context_section_keys()`: los 25
    campos de ``TEXT_FIELDS`` más ``"programs"`` y ``"honduras"``.

    Reglas del formato, que son las de hoy y no se negocian:

    - **El orden de salida es el de `TEXT_FIELDS`**, no el de ``keys``. El prompt
      tiene que ser determinista: dos routers que piden lo mismo en distinto
      orden deben producir el mismo texto (y acertar la misma caché de prefijo).
    - **Cabecera y cierre van siempre**, se pida lo que se pida: son guardarraíles
      contra la confusión UNEV/UNED y contra inventar datos.
    - **Claves desconocidas se ignoran** con un aviso por stderr (una vez cada
      una). Frente a un visitante, un router desactualizado degrada la respuesta;
      no la cancela.
    - ``"honduras"`` se anexa al final tras una línea en blanco, tal como lo hacía
      el bloque atómico.

    Con todas las claves es idéntico, carácter por carácter, a
    `get_university_context()`; eso lo vigila `tests/test_context_sections.py`.
    """
    sections = _rendered_sections()
    wanted = {str(key) for key in keys}
    for unknown in sorted(wanted - set(context_section_keys())):
        _warn_unknown_section(unknown)

    lines = list(_HEADER_LINES)
    lines.extend(sections[key] for key in TEXT_FIELDS if key in wanted and key in sections)
    if PROGRAMS_SECTION in wanted and PROGRAMS_SECTION in sections:
        lines.append(sections[PROGRAMS_SECTION])
    lines.append(_CLOSING_LINE)

    texto = "\n".join(lines)
    if HONDURAS_SECTION in wanted:
        # El separador va aunque Honduras venga vacío: así era el bloque atómico
        # y la paridad se mide carácter por carácter.
        texto += "\n\n" + sections.get(HONDURAS_SECTION, "")
    return texto


def get_university_context():
    """Contexto de sistema UNEV + Honduras (cacheado entre turnos del LLM).

    Entrega la información **completa** de ``data/unev_info.json`` (todos los
    campos de texto y la descripción íntegra de cada programa), sin resumir
    carreras a un listado de nombres.

    Desde WAVE-04 es `get_context_sections()` con todas las claves: mismo texto,
    misma caché, mismos llamadores. Quién pide menos que todo es cosa de WAVE-05.
    """
    global _CONTEXT_CACHE
    if _CONTEXT_CACHE is not None:
        return _CONTEXT_CACHE

    _CONTEXT_CACHE = get_context_sections(context_section_keys())
    return _CONTEXT_CACHE
