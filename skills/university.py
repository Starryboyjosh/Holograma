"""Respuestas sobre UNEV. Los datos provienen de la fuente única y editable
``skills.unev_content`` (``data/unev_info.json``); aquí solo se da formato.
"""

from skills.unev_content import get_unev_info
from skills.utils import normalize_text


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
    return (
        "Para iniciar tu proceso de admisión en UNEV debes presentar de forma digital: "
        "Título de Educación Media (PDF), DNI y Certificación de Nacimiento (sin RNP). "
        "Además, deberás realizar un Examen Diagnóstico de Tecnología y Ofimática "
        "(30 minutos), con un puntaje mínimo del 70% para ingreso directo. Si no "
        "alcanzas el puntaje, ingresarás al Programa de Inmersión y Nivelación Digital "
        "(PRIND), un andamiaje obligatorio que asegura el dominio de las herramientas "
        "asincrónicas antes de iniciar la carga técnica. Puedes elegir entre las "
        "carreras de Diseño Gráfico, Administración de Empresas o Programación Web, "
        "todas con modalidad 100% virtual, duración de 2 años y ciclos cuatrimestrales "
        "intensivos de 11 semanas."
    )


def get_location_info():
    info = get_unev_info()
    return f"La dirección registrada de UNEV es: {info['address']} {info['infrastructure']}"


def get_approval_info():
    return get_unev_info()["approval"]


def get_website_info():
    return f"Puedes visitar la página oficial de UNEV en {get_unev_info()['website']}"


def get_university_context():
    from skills.honduras import get_university_context as get_honduras_context

    try:
        honduras_ctx = get_honduras_context()
    except Exception:
        honduras_ctx = ""

    info = get_unev_info()
    programs = ", ".join(program.title() for program in info["programs"].keys())
    unev_ctx = (
        "Información institucional de UNEV:\n"
        f"- Nombre: {info['name']} ({info['full_name']})\n"
        f"- Descripción: {info['description']}\n"
        f"- Diferenciador: {info['main_claim']}\n"
        f"- Misión: {info['mission']}\n"
        f"- Visión: {info['vision']}\n"
        f"- Valores: {info['values']}\n"
        f"- Aprobación: {info['approval']}\n"
        f"- Gobernanza: {info['governance']}\n"
        f"- Dirección: {info['address']}\n"
        f"- Infraestructura: {info['infrastructure']}\n"
        f"- Modelo académico: {info['academic_model']}\n"
        f"- Cuerpo docente: {info['faculty']}\n"
        f"- Acompañamiento estudiantil: {info['student_support']}\n"
        f"- Requisitos de admisión: {info['admission_requirements']}\n"
        f"- Proyección social: {info['social_projection']}\n"
        f"- Biblioteca Virtual: {info['virtual_library']}\n"
        f"- Presencia internacional: {info['international_presence']}\n"
        f"- Sitio web oficial: {info['website']}\n"
        f"- Programas conocidos: {programs}.\n"
        "Si el visitante pregunta por datos no incluidos aquí, no inventes. "
        "Recomienda revisar la página oficial o contactar a UNEV."
    )
    return unev_ctx + "\n\n" + honduras_ctx
