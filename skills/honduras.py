import json
from pathlib import Path

from skills.utils import normalize_text

BASE_DIR = Path(__file__).resolve().parent.parent
JSON_PATH = BASE_DIR / "data" / "honduras_info.json"
CATALOG_PATH = BASE_DIR / "data" / "honduras_cultura_general.json"

HONDURAS_INFO = {}

if not JSON_PATH.exists():
    raise RuntimeError(f"ERROR CRÍTICO: No se encontró el archivo de datos requerido en: {JSON_PATH}")

try:
    with JSON_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
        HONDURAS_INFO = {
            "name": data["name"],
            "website": data["website"],
            "description": data["description"],
            "main_claim": data["main_claim"],
            "approval": data["approval"],
            "address": data["address"],
            "programs": {},
            "proceres": {},
            "vulgarismos": {},
            "simbolos_patrios": {},
        }
        programs_data = data.get("programs", {})
        for prog_key, prog_desc in programs_data.items():
            HONDURAS_INFO["programs"][prog_key.lower().strip()] = prog_desc
        proceres_data = data.get("proceres", {})
        for proc_key, proc_desc in proceres_data.items():
            HONDURAS_INFO["proceres"][proc_key.lower().strip()] = proc_desc
        vulg_data = data.get("vulgarismos", {})
        for vulg_key, vulg_desc in vulg_data.items():
            HONDURAS_INFO["vulgarismos"][vulg_key.lower().strip()] = vulg_desc
        simb_data = data.get("simbolos_patrios", {})
        for simb_key, simb_desc in simb_data.items():
            HONDURAS_INFO["simbolos_patrios"][simb_key.lower().strip()] = simb_desc
            
except Exception as e:
    raise RuntimeError(f"ERROR CRÍTICO al leer o decodificar el archivo de datos {JSON_PATH}: {e}")



# ==============================================================================
# SISTEMA DE INDEXACIÓN OPTIMIZADO PARA BÚSQUEDAS (MÓDULO DE RENDIMIENTO)
# ==============================================================================
HONDURAS_EXACT_LOOKUP = {}
HONDURAS_PARTIAL_LOOKUP = []

def _build_search_index():
    """
    Pre-calcula índices de texto normalizados en el arranque del servidor/script.
    Garantiza búsquedas directas en O(1) y evita llamadas repetitivas en caliente
    a normalize_text() reduciendo el uso de CPU.
    """
    global HONDURAS_EXACT_LOOKUP, HONDURAS_PARTIAL_LOOKUP
    HONDURAS_EXACT_LOOKUP = {}
    HONDURAS_PARTIAL_LOOKUP = []
    
    # Procesar Categorías estándar con formato "Título: Descripción"
    standard_categories = ["programs", "proceres", "vulgarismos", "simbolos_patrios"]
    for category in standard_categories:
        for key, desc in HONDURAS_INFO.get(category, {}).items():
            norm_key = normalize_text(key)
            formatted_string = f"{key.title()}: {desc}"
            HONDURAS_EXACT_LOOKUP[norm_key] = formatted_string
            HONDURAS_PARTIAL_LOOKUP.append((norm_key, formatted_string))

# Inicialización única del mapa de memoria indexado
_build_search_index()


# ==============================================================================
# CULTURA GENERAL BAJO DEMANDA (WAVE A-1)
# ==============================================================================
# El catálogo de cultura general (970 preguntas, ~126 KB) ya no se carga en el
# import: pesaba el arranque y ninguna regla del router lo consultaba (el router
# solo llama `get_program_info` con las claves de `programs`). Vive en
# `honduras_cultura_general.json` y solo se lee si una consulta llega acá.

_CATALOG_CACHE: dict[str, str] | None = None
_CATALOG_PARTIAL: list[tuple[str, str]] | None = None


def _load_catalog() -> None:
    """Carga el catálogo de cultura general una sola vez (lazy)."""
    global _CATALOG_CACHE, _CATALOG_PARTIAL
    if _CATALOG_CACHE is not None:
        return
    _CATALOG_CACHE = {}
    _CATALOG_PARTIAL = []
    if not CATALOG_PATH.exists():
        return
    try:
        with CATALOG_PATH.open("r", encoding="utf-8") as f:
            cult_data = json.load(f).get("cultura_general", {})
        for cult_key, cult_desc in cult_data.items():
            norm_key = normalize_text(cult_key)
            _CATALOG_CACHE[norm_key] = cult_desc
            _CATALOG_PARTIAL.append((norm_key, cult_desc))
    except Exception:
        # El catálogo es prescindible: sin él la skill responde el fallback.
        _CATALOG_CACHE = {}


def get_cultura_general_info(query: str) -> str | None:
    """Busca una pregunta de cultura general en el catálogo bajo demanda.

    Exacta O(1) primero; luego coincidencia por subcadena. ``None`` si no hay
    respuesta (quien llame debe decir "no invento, te busco" en vez de rellenar).
    """
    normalized_query = normalize_text(query)
    if _CATALOG_CACHE is None:
        _load_catalog()
    if normalized_query in _CATALOG_CACHE:
        return _CATALOG_CACHE[normalized_query]
    for norm_key, formatted_result in _CATALOG_PARTIAL or ():
        if norm_key in normalized_query or normalized_query in norm_key:
            return formatted_result
    return None


# ==============================================================================
# FUNCIONES DE EXTRACCIÓN DE CONTEXTO E HISTORIA
# ==============================================================================

def get_university_summary():
    return (
        f"{HONDURAS_INFO['name']} es una república multiétnica y multicultural de "
        f"Centroamérica. {HONDURAS_INFO['main_claim']} "
        "Su identidad nacional se sustenta en una ecología de saberes donde "
        "convergen las cosmovisiones indígenas y afrohondureñas, junto con una rica "
        "tradición lingüística y un sólido marco jurídico de reconocimiento cultural."
    )


def get_programs_summary():
    programs = HONDURAS_INFO["programs"]
    return (
        "La historia de Honduras puede recorrerse a través de cuatro grandes "
        "periodos: Era Precolombina y Ancestral, Evolución Lingüística y Colonial, "
        "Periodo de Investigación y Reconocimiento (S. XIX-XX) y Periodo "
        "Contemporáneo y Salvaguarda (2022-2035). "
        f"Era Precolombina y Ancestral: {programs['era precolombina y ancestral']} "
        f"Evolución Lingüística y Colonial: {programs['evolución lingüística y colonial']} "
        f"Periodo de Investigación y Reconocimiento (S. XIX-XX): {programs['periodo de investigación y reconocimiento (s. xix-xx)']} "
        f"Periodo Contemporáneo y Salvaguarda (2022-2035): {programs['periodo contemporáneo y salvaguarda (2022-2035)']}"
    )


def get_program_info(program_name):
    normalized_program_name = normalize_text(program_name)
    
    # OPTIMIZACIÓN 1: Coincidencia de Hash Directo O(1) instantánea
    if normalized_program_name in HONDURAS_EXACT_LOOKUP:
        return HONDURAS_EXACT_LOOKUP[normalized_program_name]
        
    # OPTIMIZACIÓN 2 (Principio DRY): Búsqueda secuencial unificada por subcadenas (sin loops repetidos)
    for norm_key, formatted_result in HONDURAS_PARTIAL_LOOKUP:
        if norm_key in normalized_program_name or normalized_program_name in norm_key:
            return formatted_result
            
    return (
        "Puedo darte información sobre los periodos históricos (Era Precolombina, "
        "Evolución Lingüística y Colonial, Investigación y Reconocimiento, y "
        "Periodo Contemporáneo), así como sobre próceres (Membreño, Cruz Castro, "
        "Vélez Osejo, Bernárdez), vulgarismos, símbolos patrios y cultura general de Honduras. ¿Sobre cuál tema "
        "te gustaría saber más?"
    )


def get_admission_info():
    return (
        "Para profundizar en la historia, lengua y cultura de Honduras, puedes "
        "consultar las cuatro grandes áreas temáticas: Era Precolombina y Ancestral, "
        "Evolución Lingüística y Colonial, Periodo de Investigación y Reconocimiento, "
        "y Periodo Contemporáneo y Salvaguarda. También puedes preguntar por próceres "
        "como Alberto de Jesús Membreño o Francisco Cruz Castro, por vulgarismos "
        "típicos del habla hondureña, o por los símbolos patrios y culturales del país."
    )


def get_location_info():
    return f"La ubicación y distribución territorial de Honduras es: {HONDURAS_INFO['address']}"


def get_approval_info():
    return HONDURAS_INFO["approval"]


def get_website_info():
    return f"Puedes consultar información oficial del Estado de Honduras en {HONDURAS_INFO['website']}"


def get_proceres_info():
    proceres = HONDURAS_INFO["proceres"]
    return (
        "Próceres y personajes históricos destacados de Honduras: "
        f"Alberto de Jesús Membreño: {proceres['alberto de jesús membreño']} "
        f"Francisco Cruz Castro: {proceres['francisco cruz castro']} "
        f"Annarella Vélez Osejo: {proceres['annarella vélez osejo']} "
        f"Cintia Marizel Bernárdez: {proceres['cintia marizel bernárdez']}"
    )


def get_vulgarismos_info():
    vulgarismos = HONDURAS_INFO["vulgarismos"]
    listado = " ".join(
        f"{nombre.title()}: {descripcion}" for nombre, descripcion in vulgarismos.items()
    )
    return (
        "Vulgarismos y rasgos lingüísticos característicos del habla hondureña: "
        f"{listado}"
    )


def get_simbolos_patrios_info():
    simbolos = HONDURAS_INFO["simbolos_patrios"]
    listado = " ".join(
        f"{nombre.title()}: {descripcion}" for nombre, descripcion in simbolos.items()
    )
    return (
        "Símbolos patrios y culturales que conforman la identidad nacional de Honduras: "
        f"{listado}"
    )


def get_university_context():
    programs = ", ".join(program.title() for program in HONDURAS_INFO["programs"].keys())
    proceres = ", ".join(procer.title() for procer in HONDURAS_INFO["proceres"].keys())
    vulgarismos = ", ".join(vulg.title() for vulg in HONDURAS_INFO["vulgarismos"].keys())
    simbolos = ", ".join(simb.title() for simb in HONDURAS_INFO["simbolos_patrios"].keys())
    
    return (
        "Información histórica y cultural de Honduras:\n"
        f"- Nombre Oficial: República de {HONDURAS_INFO['name']}\n"
        f"- Descripción: {HONDURAS_INFO['description']}\n"
        f"- Diferenciador: {HONDURAS_INFO['main_claim']}\n"
        f"- Hito Fundacional: {HONDURAS_INFO['approval']}\n"
        f"- Capital y Distribución Territorial: {HONDURAS_INFO['address']}\n"
        f"- Sitio web oficial: {HONDURAS_INFO['website']}\n"
        f"- Periodos históricos conocidos: {programs}.\n"
        f"- Próceres y personajes históricos: {proceres}.\n"
        f"- Vulgarismos y rasgos del habla hondureña: {vulgarismos}.\n"
        f"- Símbolos patrios y culturales: {simbolos}.\n"
        "Si el visitante pregunta por datos no incluidos aquí o por temas específicos de cultura general que no coincidan, no inventes. "
        "Recomienda revisar fuentes oficiales del Estado de Honduras, la Academia "
        "Hondureña de la Lengua o la Secretaría de las Culturas, las Artes y los "
        "Patrimonios de los Pueblos de Honduras."
    )