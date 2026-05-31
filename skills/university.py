import unicodedata

UNEV_INFO = {
    "name": "UNEV",
    "description": (
        "UNEV es una universidad virtual en Honduras creada para ofrecer "
        "educación superior accesible, flexible y de calidad."
    ),
    "main_claim": "Primera y única universidad 100% virtual en Honduras.",
    "approval": (
        "Aprobada nacionalmente por el Consejo de Educación Superior de Honduras "
        "con el acuerdo 4995-381-2023, Sesión Ordinaria 381 del 9 de junio de 2023."
    ),
    "address": (
        "Colonia Trejo, entre 9 y 10 calle, 21 avenida C, instalaciones del ITEE, "
        "Edificio 1 ala izquierda, Segunda planta, San Pedro Sula, Cortés, 21104."
    ),
    "website": "https://unev.edu.hn/",
    "programs": {
        "diseño gráfico": (
            "El Tecnólogo Diseñador Gráfico desarrolla propuestas creativas e "
            "innovadoras para campañas, marcas y medios digitales, con visión "
            "emprendedora y proyección hacia el mercadeo, la educación y la publicidad."
        ),
        "administración de empresas": (
            "El Tecnólogo Administrador de Empresas será un profesional creativo e "
            "innovador, con iniciativa emprendedora y capacidad de trabajo en equipo, "
            "capaz de apoyar la gestión de las áreas funcionales de la empresa y "
            "aportar soluciones prácticas a problemas reales."
        ),
        "programación web": (
            "El Tecnólogo Programador Web será un profesional integral y ético, "
            "capaz de desarrollar aplicaciones seguras y funcionales, combinando "
            "diseño, bases de datos y análisis de software según las necesidades del cliente."
        ),
    },
}


def normalize_text(text):
    """Lowercase text and remove accents for simple Spanish keyword matching."""
    text = text.lower().strip()
    normalized = unicodedata.normalize("NFD", text)
    return "".join(
        character for character in normalized if unicodedata.category(character) != "Mn"
    )


def get_university_summary():
    return (
        f"{UNEV_INFO['name']} es una universidad virtual de Honduras. "
        f"{UNEV_INFO['main_claim']} "
        "Ofrece programas orientados al mundo laboral actual, con un modelo flexible "
        "para estudiar desde cualquier lugar."
    )


def get_programs_summary():
    programs = UNEV_INFO["programs"]

    return (
        "Actualmente puedo hablarte de estos programas de UNEV: Diseño Gráfico, "
        "Administración de Empresas y Programación Web. "
        f"Diseño Gráfico: {programs['diseño gráfico']} "
        f"Administración de Empresas: {programs['administración de empresas']} "
        f"Programación Web: {programs['programación web']}"
    )


def get_program_info(program_name):
    normalized_program_name = normalize_text(program_name)

    for program, description in UNEV_INFO["programs"].items():
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
        "Para iniciar tu proceso de admisión en UNEV, puedes visitar la página oficial "
        "de la universidad o llenar el formulario de contacto. También puedes indicar "
        "tu carrera de interés: Diseño Gráfico, Programación Web o Administración de Empresas."
    )


def get_location_info():
    return f"La dirección registrada de UNEV es: {UNEV_INFO['address']}"


def get_approval_info():
    return UNEV_INFO["approval"]


def get_website_info():
    return f"Puedes visitar la página oficial de UNEV en {UNEV_INFO['website']}"


def get_university_context():
    programs = ", ".join(program.title() for program in UNEV_INFO["programs"].keys())

    return (
        "Información institucional de UNEV:\n"
        f"- Nombre: {UNEV_INFO['name']}\n"
        f"- Descripción: {UNEV_INFO['description']}\n"
        f"- Diferenciador: {UNEV_INFO['main_claim']}\n"
        f"- Aprobación: {UNEV_INFO['approval']}\n"
        f"- Dirección: {UNEV_INFO['address']}\n"
        f"- Sitio web oficial: {UNEV_INFO['website']}\n"
        f"- Programas conocidos: {programs}.\n"
        "Si el visitante pregunta por datos no incluidos aquí, no inventes. "
        "Recomienda revisar la página oficial o contactar a UNEV."
    )
