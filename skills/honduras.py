import json
from pathlib import Path

from skills.utils import normalize_text

BASE_DIR = Path(__file__).resolve().parent.parent
JSON_PATH = BASE_DIR / "data" / "honduras_info.json"

HONDURAS_INFO = {}

DEFAULT_HONDURAS_INFO = {
    "name": "Honduras",
    "description": (
        "Honduras es una ecología de saberes donde convergen diversas cosmovisiones "
        "indígenas y afrohondureñas, conformando una identidad nacional definida por "
        "su naturaleza multiétnica, multicultural y una vasta riqueza ecológica y social."
    ),
    "main_claim": (
        "República multiétnica y multicultural con 10 Pueblos Indígenas y "
        "Afrohondureños (PIAH) que conforman el corazón de su identidad nacional."
    ),
    "approval": (
        "Hito fundacional: ratificación del Convenio 169 de la Organización "
        "Internacional del Trabajo (OIT), establecido el 27 de junio de 1989, "
        "ratificado por el Estado de Honduras en 1994 y con entrada en vigencia "
        "plena en 1995."
    ),
    "address": (
        "República de Honduras, con capital en Tegucigalpa. Los 10 Pueblos Indígenas "
        "y Afrohondureños habitan regiones específicas: los Lenca en Intibucá; los "
        "Garífuna en la Costa Norte (incluyendo Omoa); los Negros de Habla Inglesa o "
        "Creoles en las Islas de la Bahía y Costa Norte; y los grupos Misquito, "
        "Tawahka, Maya-Chortí, Nahua, Nahualt, Tolupan y Pesh en sus respectivos "
        "asentamientos regionales."
    ),
    "website": "[https://www.presidencia.gob.hn/](https://www.presidencia.gob.hn/)",
    "programs": {
        "era precolombina y ancestral": (
            "La configuración del tejido social hondureño encuentra su génesis en la "
            "profundidad temporal de las civilizaciones ancestrales. La presencia de "
            "los Mayas y la herencia de los pueblos originarios lenca, nahua y "
            "garífuna, entre otros, aportan una cosmovisión que se erige como el "
            "corazón del desarrollo sociocultural de la nación. Las lenguas maternas "
            "son reconocidas como vehículos esenciales de desarrollo cognitivo."
        ),
        "evolución lingüística y colonial": (
            "El mestizaje en Honduras operó como un proceso de reconfiguración "
            "identitaria donde el español se impuso como lengua nacional. Según Van "
            "Wijk (1961), generó rasgos morfosintácticos singulares como el voseo "
            "generalizado, el leísmo, la pérdida de identidad del artículo definido "
            "(l'amor, l'arcalde), la adverbialización de adjetivos (canta bonito) y "
            "construcciones pleonásticas posesivas (mi casa mía), junto con "
            "influencias léxicas de los enclaves bananeros de la United Fruit Company."
        ),
        "periodo de investigación y reconocimiento (s. xix-xx)": (
            "La institucionalización del estudio de la lengua legitimó el habla "
            "popular. En 1899 se publicó el primer diccionario de hondureñismos y se "
            "consolidó la Academia Hondureña de la Lengua. La edición de 1992 del "
            "Diccionario de la RAE incorporó 302 términos hondureños, cifra que "
            "ascendió a 1,950 en 2001 y actualmente alcanza 2,782 registros."
        ),
        "periodo contemporáneo y salvaguarda (2022-2035)": (
            "La política estatal se fundamenta en la reparación histórica de los "
            "derechos lingüísticos. Bajo el Gobierno de la Refundación se impulsa el "
            "Plan Nacional 2025-2035 en consonancia con el Decenio Internacional de "
            "las Lenguas Indígenas (2022-2032), salvaguardando lenguas maternas "
            "frente a la globalización y la discriminación, mediante documentación "
            "de gramáticas y educación plurilingüe."
        ),
    },
    "proceres": {
        "alberto de jesús membreño": (
            "Destacado intelectual que publicó en 1899 el primer diccionario de "
            "hondureñismos bajo el título 'Vocabulario de los provincialismos de "
            "Honduras'. Su obra representó el primer esfuerzo sistemático por "
            "codificar el pensamiento popular y otorgar una fisonomía propia al "
            "castellano hablado en el territorio nacional."
        ),
        "francisco cruz castro": (
            "Eminente figura cuya contribución a la preservación del patrimonio fue "
            "fundamental a través de su obra 'Botica del pueblo'. Su vocabulario "
            "médico, botánico y cotidiano sirvió de base empírica para que "
            "investigadores posteriores, especialmente Alberto de Jesús Membreño, "
            "pudieran estructurar el primer catálogo de términos hondureños."
        ),
        "annarella vélez osejo": (
            "Historiadora y actual Secretaria de Estado en los Despachos de las "
            "Culturas, las Artes y los Patrimonios de los Pueblos de Honduras. "
            "Ejerce liderazgo estratégico en la implementación del Plan Nacional de "
            "Salvaguarda de las Lenguas, promoviendo el reconocimiento de la "
            "diversidad cultural como patrimonio común."
        ),
        "cintia marizel bernárdez": (
            "Jefa de la Unidad de Educación Plurilingüe y Multicultural. Determinante "
            "en la creación del diagnóstico sociolingüístico conocido como el 'árbol "
            "de problemas', coordina la producción de materiales pedagógicos y "
            "recursos didácticos para fortalecer competencias comunicativas en "
            "lenguas maternas dentro de las comunidades de los 10 pueblos originarios."
        ),
    },
    "vulgarismos": {
        "voseo generalizado": (
            "Uso extendido del pronombre 'vos' en lugar de 'tú' como rasgo "
            "morfosintáctico característico del habla informal hondureña."
        ),
        "leísmo": (
            "Uso del pronombre 'le' en lugar de 'lo' o 'la' como complemento directo, "
            "rasgo identificado por Van Wijk (1961) en el habla hondureña."
        ),
        "pérdida del artículo definido ante vocal": (
            "Fenómeno de contracción que produce formas como 'l'amor' por 'el amor' "
            "o 'l'arcalde' por 'el alcalde' en el habla popular."
        ),
        "adverbialización de adjetivos": (
            "Construcciones como 'canta bonito' donde el adjetivo funciona como "
            "adverbio, característico del español hondureño."
        ),
        "construcciones pleonásticas posesivas": (
            "Expresiones redundantes como 'mi casa mía' que duplican la marca de "
            "posesión, propias del habla coloquial nacional."
        ),
        "mínimo": (
            "Término léxico para referirse al banano, derivado de los estándares de "
            "exportación de los enclaves bananeros de la United Fruit Company."
        ),
    },
    "simbolos_patrios": {
        "lenguas maternas": (
            "Reconocidas en el Plan Nacional de Salvaguarda como vehículos "
            "esenciales de desarrollo cognitivo que permiten al individuo imaginar, "
            "crear y conceptualizar su realidad desde un entorno cultural propio."
        ),
        "convenio 169 de la oit": (
            "Instrumento internacional ratificado por Honduras en 1994 que constituye "
            "el marco jurídico fundacional para el reconocimiento de los derechos de "
            "los Pueblos Indígenas y Afrohondureños."
        ),
        "los 10 pueblos indígenas y afrohondureños (piah)": (
            "Lenca, Garífuna, Negros de Habla Inglesa o Creoles, Misquito, Tawahka, "
            "Maya-Chortí, Nahua, Nahualt, Tolupan y Pesh: corazón multiétnico y "
            "multicultural de la identidad nacional hondureña."
        ),
        "academia hondureña de la lengua": (
            "Institución que consolidó la codificación del castellano hablado en "
            "Honduras, posicionándolo como un contribuyente mayoritario al léxico "
            "hispánico global con 2,782 registros en el DRAE."
        ),
        "plan nacional de salvaguarda 2025-2035": (
            "Política estatal de reparación histórica de los derechos lingüísticos, "
            "alineada con el Decenio Internacional de las Lenguas Indígenas "
            "(2022-2032) impulsado por la UNESCO."
        ),
    },
}

if JSON_PATH.exists():
    try:
        with JSON_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
            HONDURAS_INFO = {
                "name": data.get("name", DEFAULT_HONDURAS_INFO["name"]),
                "website": data.get("website", DEFAULT_HONDURAS_INFO["website"]),
                "description": data.get("description", DEFAULT_HONDURAS_INFO["description"]),
                "main_claim": data.get("main_claim", DEFAULT_HONDURAS_INFO["main_claim"]),
                "approval": data.get("approval", DEFAULT_HONDURAS_INFO["approval"]),
                "address": data.get("address", DEFAULT_HONDURAS_INFO["address"]),
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
        print(f"AVISO: No se pudo cargar {JSON_PATH}. Usando fallback en código. Error: {e}")
        HONDURAS_INFO = DEFAULT_HONDURAS_INFO
else:
    HONDURAS_INFO = DEFAULT_HONDURAS_INFO


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
    for program, description in HONDURAS_INFO["programs"].items():
        normalized_program = normalize_text(program)
        if (
            normalized_program in normalized_program_name
            or normalized_program_name in normalized_program
        ):
            return f"{program.title()}: {description}"
    for procer, description in HONDURAS_INFO["proceres"].items():
        normalized_procer = normalize_text(procer)
        if (
            normalized_procer in normalized_program_name
            or normalized_program_name in normalized_procer
        ):
            return f"{procer.title()}: {description}"
    for vulg, description in HONDURAS_INFO["vulgarismos"].items():
        normalized_vulg = normalize_text(vulg)
        if (
            normalized_vulg in normalized_program_name
            or normalized_program_name in normalized_vulg
        ):
            return f"{vulg.title()}: {description}"
    for simb, description in HONDURAS_INFO["simbolos_patrios"].items():
        normalized_simb = normalize_text(simb)
        if (
            normalized_simb in normalized_program_name
            or normalized_program_name in normalized_simb
        ):
            return f"{simb.title()}: {description}"
    return (
        "Puedo darte información sobre los periodos históricos (Era Precolombina, "
        "Evolución Lingüística y Colonial, Investigación y Reconocimiento, y "
        "Periodo Contemporáneo), así como sobre próceres (Membreño, Cruz Castro, "
        "Vélez Osejo, Bernárdez), vulgarismos y símbolos patrios. ¿Sobre cuál tema "
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
        "Si el visitante pregunta por datos no incluidos aquí, no inventes. "
        "Recomienda revisar fuentes oficiales del Estado de Honduras, la Academia "
        "Hondureña de la Lengua o la Secretaría de las Culturas, las Artes y los "
        "Patrimonios de los Pueblos de Honduras."
    )
