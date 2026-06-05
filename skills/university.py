import json
import unicodedata
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
JSON_PATH = BASE_DIR / "data" / "unev_info.json"

UNEV_INFO = {}

DEFAULT_UNEV_INFO = {
    "name": "UNEV",
    "full_name": "Instituto Universitario de Educación Virtual",
    "description": (
        "El Instituto Universitario de Educación Virtual (UNEV) es una institución "
        "de educación superior hondureña, secular y contemporánea, con un modelo "
        "100% virtual diseñado para mitigar las brechas de cobertura y conectividad "
        "en el país, ofreciendo formación técnica accesible a poblaciones vulnerables "
        "y geográficamente aisladas. Es totalmente independiente de la Universidad "
        "Nacional Evangélica de la República Dominicana, enfocándose estrictamente "
        "en la competitividad técnica y la inserción expedita en la economía del "
        "conocimiento. Su trayectoria inició en 2017 como 'Universidad Práctica' y "
        "alcanzó consolidación internacional en eventos como EDUTECHNIA 2023 en Bogotá."
    ),
    "main_claim": (
        "Primera universidad 100% virtual en Honduras, enfocada en competitividad "
        "técnica e inserción expedita en la economía del conocimiento."
    ),
    "mission": (
        "Formar profesionales líderes con competencias técnicas y tecnológicas a "
        "nivel nacional e internacional, mediante un modelo de enseñanza práctica, "
        "usando la virtualidad y personal certificado, garantizando la incorporación "
        "a los mercados que requiere el nuevo mundo empresarial."
    ),
    "vision": (
        "Consolidarnos como la Institución de Educación Virtual líder en Honduras y "
        "ser un referente a nivel nacional e internacional en la formación de "
        "profesionales competentes, aptos, íntegros y emprendedores que contribuyan "
        "al desarrollo sostenible del País, revolucionando y adaptando la educación "
        "al mundo moderno y posicionándola al alcance de la población."
    ),
    "values": "Equidad, Honestidad, Perseverancia, Ética, Excelencia y Respeto.",
    "approval": (
        "Aprobada por el Consejo de Educación Superior (CES) mediante el Acuerdo "
        "No. 4995-381-2023 del 9 de junio de 2023, con admisión a trámite previa "
        "según Acuerdo No. 3827-327-2018. Su validez institucional fue ratificada "
        "el 3 de mayo de 2024 con la visita oficial del Rector de la UNAH, "
        "Dr. Odir Fernández, acompañado por la Máster Cleopatra Duarte (Directora "
        "de la DES), la Máster Norma Martínez (JDU), el Dr. Elmer Fernández "
        "(SED-UNAH) y el Máster Oziel Fernández Herrera. Los títulos poseen plena "
        "seguridad jurídica para el ejercicio profesional nacional e internacional "
        "al estar integrados en el registro oficial de la Dirección de Educación "
        "Superior (DES)."
    ),
    "governance": (
        "UNEV es dirigida por un Consejo Administrativo con autonomía estratégica, "
        "bajo el liderazgo del Ingeniero y Fundador Raúl Peña Moreno y su Consejo Académico."
    ),
    "address": (
        "Colonia Trejo, entre 9 y 10 calle, 21 avenida C, instalaciones del ITEE "
        "(Instituto Tecnológico de Electricidad y Electrónica), Edificio 1, ala "
        "izquierda, segunda planta, San Pedro Sula, Cortés."
    ),
    "infrastructure": (
        "La sede central opera bajo una estrategia de Lean OpEx mediante alianza "
        "estratégica de co-working con el ITEE, lo que permite acceder a redes de "
        "conectividad simétrica de alta disponibilidad y soporte técnico de red "
        "centralizado en una zona de alta accesibilidad y seguridad en San Pedro Sula. "
        "Esta sinergia optimiza costos operativos y prioriza la inversión en el "
        "campus digital y plataformas de aprendizaje (LMS)."
    ),
    "website": "[https://unev.edu.hn/](https://unev.edu.hn/)",
    "academic_model": (
        "Modelo 'Agile Learning' basado en el formato de Técnico Universitario "
        "(Tecnólogo). El diseño curricular se compone de ciclos intensivos de "
        "11 semanas con rotación cuatrimestral, lo que acelera la profesionalización "
        "reduciendo el tiempo de formación en un 50% respecto a una licenciatura "
        "tradicional, sin comprometer el rigor académico."
    ),
    "faculty": (
        "Planta docente híbrida que combina perspectiva global con ejecución local. "
        "Destacan perfiles como Nathalie Cuadrado (internacional, Colombia, con más "
        "de 15 años de experiencia en retail y diseño editorial), Cesar Arguijo "
        "(especialista en Ofimática) y Gladys Ferrufino (coordinadora de "
        "comunicación lingüística)."
    ),
    "student_support": (
        "El ecosistema de retención incluye una inducción de dos semanas, programas "
        "de mentoría y el Sistema de Alerta Temprana (SAT), que permite un "
        "Data-driven Student Lifecycle Management. El SAT monitorea algorítmicamente "
        "patrones de inactividad o bajo rendimiento y ejecuta intervención humana "
        "en un plazo de 48 a 72 horas para prevenir la deserción."
    ),
    "admission_requirements": (
        "Carga digital de Título de Educación Media (PDF), DNI y Certificación de "
        "Nacimiento (sin RNP). Evaluación Diagnóstica de Tecnología y Ofimática "
        "(30 minutos) con puntaje mínimo del 70% para ingreso directo. Quienes no "
        "alcancen el puntaje mínimo deben cursar el Programa de Inmersión y "
        "Nivelación Digital (PRIND), un andamiaje obligatorio que asegura el dominio "
        "de las herramientas asincrónicas antes de iniciar la carga técnica."
    ),
    "social_projection": (
        "El Proyecto Tecnoaulas es la estrategia de proyección social de UNEV: "
        "espacios físicos con internet simétrico y hardware de alta gama, con "
        "objetivo de desplegar 50 unidades a nivel nacional. Complementariamente, "
        "la Tienda Virtual de Servicios Sociales registra y digitaliza los proyectos "
        "de vinculación de los estudiantes (como soluciones de gestión para "
        "microempresas) para replicarlos en otras comunidades, conformando una "
        "economía circular del conocimiento."
    ),
    "virtual_library": (
        "La Biblioteca Virtual centraliza el acceso a información en cuatro "
        "dimensiones: (1) Repositorio de libros con consulta simultánea e ilimitada; "
        "(2) Biblioteca Digital de Ciencia y Tecnología con revistas indexadas e "
        "investigaciones de vanguardia; (3) Bibliotecas externas con enlaces a "
        "fuentes de autoridad como la RAE; (4) Guías metodológicas interactivas "
        "para aplicación de normas APA y técnicas de investigación."
    ),
    "international_presence": (
        "UNEV participa en redes internacionales de negocios y programas de "
        "certificación de mentores (Red GIEN), lo que posiciona a sus egresados en "
        "una red de contactos global. Tuvo consolidación internacional en eventos "
        "como EDUTECHNIA 2023 en Bogotá."
    ),
    "programs": {
        "diseño gráfico": (
            "El Técnico Universitario en Diseño Gráfico  tiene un "
            "enfoque en ilustración digital, maquetación editorial, identidad "
            "corporativa y taller de animación, con una clara visión de emprendimiento "
            "digital. Cuenta con 93 créditos totales, 24 asignaturas y una duración "
            "de 2 años bajo el modelo cuatrimestral de ciclos intensivos de 11 semanas."
        ),
        "administración de empresas": (
            "El Técnico Universitario en Administración de Empresas "
            "se especializa en logística, gestión de proyectos, mercadeo digital y "
            "contabilidad aplicada a la resolución de problemas reales. Cuenta con "
            "90 créditos totales, 24 asignaturas y una duración de 2 años bajo el "
            "modelo cuatrimestral de ciclos intensivos de 11 semanas."
        ),
        "programación web": (
            "El Técnico Universitario en Programación Web  ofrece "
            "una formación integral en el desarrollo de aplicaciones seguras, "
            "arquitectura de software y gestión de bases de datos. Tiene una duración "
            "de 2 años bajo el modelo cuatrimestral de ciclos intensivos de 11 semanas, "
            "y se encuentra en fase de actualización de registro ante la DES para el "
            "ciclo 2024."
        ),
    },
}

if JSON_PATH.exists():
    try:
        with JSON_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
            UNEV_INFO = {
                "name": data.get("name", DEFAULT_UNEV_INFO["name"]),
                "full_name": data.get("full_name", DEFAULT_UNEV_INFO["full_name"]),
                "website": data.get("website", DEFAULT_UNEV_INFO["website"]),
                "description": data.get(
                    "description", DEFAULT_UNEV_INFO["description"]
                ),
                "main_claim": data.get("main_claim", DEFAULT_UNEV_INFO["main_claim"]),
                "mission": data.get("mission", DEFAULT_UNEV_INFO["mission"]),
                "vision": data.get("vision", DEFAULT_UNEV_INFO["vision"]),
                "values": data.get("values", DEFAULT_UNEV_INFO["values"]),
                "approval": data.get("approval", DEFAULT_UNEV_INFO["approval"]),
                "governance": data.get("governance", DEFAULT_UNEV_INFO["governance"]),
                "address": data.get("address", DEFAULT_UNEV_INFO["address"]),
                "infrastructure": data.get(
                    "infrastructure", DEFAULT_UNEV_INFO["infrastructure"]
                ),
                "academic_model": data.get(
                    "academic_model", DEFAULT_UNEV_INFO["academic_model"]
                ),
                "faculty": data.get("faculty", DEFAULT_UNEV_INFO["faculty"]),
                "student_support": data.get(
                    "student_support", DEFAULT_UNEV_INFO["student_support"]
                ),
                "admission_requirements": data.get(
                    "admission_requirements",
                    DEFAULT_UNEV_INFO["admission_requirements"],
                ),
                "social_projection": data.get(
                    "social_projection", DEFAULT_UNEV_INFO["social_projection"]
                ),
                "virtual_library": data.get(
                    "virtual_library", DEFAULT_UNEV_INFO["virtual_library"]
                ),
                "international_presence": data.get(
                    "international_presence",
                    DEFAULT_UNEV_INFO["international_presence"],
                ),
                "programs": {},
            }
            programs_data = data.get("programs", {})
            for prog_key, prog_desc in programs_data.items():
                UNEV_INFO["programs"][prog_key.lower().strip()] = prog_desc
    except Exception as e:
        print(
            f"AVISO: No se pudo cargar {JSON_PATH}. Usando fallback en código. Error: {e}"
        )
        UNEV_INFO = DEFAULT_UNEV_INFO
else:
    UNEV_INFO = DEFAULT_UNEV_INFO


def normalize_text(text):
    text = text.lower().strip()
    normalized = unicodedata.normalize("NFD", text)
    return "".join(
        character for character in normalized if unicodedata.category(character) != "Mn"
    )


def get_university_summary():
    return (
        f"{UNEV_INFO['name']} ({UNEV_INFO['full_name']}) es una institución de "
        "educación superior hondureña con modelo 100% virtual. "
        f"{UNEV_INFO['main_claim']} "
        f"Misión: {UNEV_INFO['mission']} "
        f"Visión: {UNEV_INFO['vision']} "
        f"Valores institucionales: {UNEV_INFO['values']} "
        "Opera bajo un modelo cuatrimestral con ciclos intensivos de 11 semanas, "
        "ofreciendo carreras de Técnico Universitario con duración de 2 años. "
        "Su trayectoria inició en 2017 como 'Universidad Práctica' y se consolidó "
        "internacionalmente en EDUTECHNIA 2023 en Bogotá. "
        f"Liderazgo: {UNEV_INFO['governance']}"
    )


def get_programs_summary():
    programs = UNEV_INFO["programs"]
    return (
        "Actualmente UNEV ofrece tres carreras bajo el modelo de Técnico Universitario "
        "(Tecnólogo), con ciclos intensivos de 11 semanas y duración total de 2 años: "
        "Diseño Gráfico (TUDG-03, 93 créditos, 24 asignaturas), Administración de "
        "Empresas (TUAE-01, 90 créditos, 24 asignaturas) y Programación Web "
        "(P-RC2024, en fase de actualización de registro ante la DES). "
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
    return (
        f"La dirección registrada de UNEV es: {UNEV_INFO['address']} "
        f"{UNEV_INFO['infrastructure']}"
    )


def get_approval_info():
    return UNEV_INFO["approval"]


def get_website_info():
    return f"Puedes visitar la página oficial de UNEV en {UNEV_INFO['website']}"


def get_university_context():
    programs = ", ".join(program.title() for program in UNEV_INFO["programs"].keys())
    return (
        "Información institucional de UNEV:\n"
        f"- Nombre: {UNEV_INFO['name']} ({UNEV_INFO['full_name']})\n"
        f"- Descripción: {UNEV_INFO['description']}\n"
        f"- Diferenciador: {UNEV_INFO['main_claim']}\n"
        f"- Misión: {UNEV_INFO['mission']}\n"
        f"- Visión: {UNEV_INFO['vision']}\n"
        f"- Valores: {UNEV_INFO['values']}\n"
        f"- Aprobación: {UNEV_INFO['approval']}\n"
        f"- Gobernanza: {UNEV_INFO['governance']}\n"
        f"- Dirección: {UNEV_INFO['address']}\n"
        f"- Infraestructura: {UNEV_INFO['infrastructure']}\n"
        f"- Modelo académico: {UNEV_INFO['academic_model']}\n"
        f"- Cuerpo docente: {UNEV_INFO['faculty']}\n"
        f"- Acompañamiento estudiantil: {UNEV_INFO['student_support']}\n"
        f"- Requisitos de admisión: {UNEV_INFO['admission_requirements']}\n"
        f"- Proyección social: {UNEV_INFO['social_projection']}\n"
        f"- Biblioteca Virtual: {UNEV_INFO['virtual_library']}\n"
        f"- Presencia internacional: {UNEV_INFO['international_presence']}\n"
        f"- Sitio web oficial: {UNEV_INFO['website']}\n"
        f"- Programas conocidos: {programs}.\n"
        "Si el visitante pregunta por datos no incluidos aquí, no inventes. "
        "Recomienda revisar la página oficial o contactar a UNEV."
    )
