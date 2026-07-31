"""Router local determinista: puntúa **todas** las reglas y gana la mejor.

Reemplaza la cascada de ``if any(word in text ...)`` que tenía dos defectos
estructurales, los dos medidos en producción:

1. **Coincidencia por subcadena.** ``normalize_text("Háblame")`` → ``"hablame"``,
   que *contiene* ``"habla"``. Como el ``if`` de vulgarismos iba antes que todo
   el enrutado UNEV, «Háblame de Programación Web» respondía con lingüística
   hondureña. Acá se compara contra **tokens completos**, nunca subcadenas.
2. **Gana el primer ``if``, no el mejor.** Sin puntuación no había forma de que
   «Háblame de la lluvia de peces» prefiriera cultura sobre vulgarismos. Acá se
   evalúan todas las reglas y gana la de mayor puntuación, con desempate
   determinista por nombre de tema.

El esquema de confianza es el de `app/hologram/media_router.py` (que ya está
probado en este mismo repositorio): puntuaciones enteras 0–100 por regla,
``confidence = min(0.99, mejor / 100)``, y un umbral ``MINIMUM_CONFIDENCE`` con
el mismo valor por defecto (0.75) que ``RoutingConfig.minimum_confidence``.
Bajo el umbral no se inventa una sección: se cae al conjunto por defecto.

**Sin red, sin embeddings, sin vector store.** Enrutar cuesta ~0,01 ms; una
llamada de clasificación costaría 200–800 ms. Cuatro órdenes de magnitud.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field

import skills.honduras as honduras
from skills.university import (
    get_admission_info,
    get_approval_info,
    get_location_info,
    get_program_info,
    get_programs_summary,
    get_university_summary,
    get_website_info,
    normalize_text,
)

__all__ = [
    "route_local_skill",
    "route_query",
    "RouteDecision",
    "MINIMUM_CONFIDENCE",
    "DEFAULT_SECTIONS",
]

# ---------------------------------------------------------------------------
# Puntuación
# ---------------------------------------------------------------------------
# Mismos tramos enteros 0–100 de `media_router._rank_promotions`. Los valores se
# eligen contra el umbral: un término *primario* solo (78) ya lo supera; uno de
# *apoyo* solo (62) no, y necesita compañía. Ese es todo el mecanismo del umbral.
_SCORE_EXACT = 95  # la consulta entera es el término
_SCORE_PHRASE = 88  # frase multipalabra presente
_SCORE_PRIMARY = 78  # palabra clave propia de la regla
_SCORE_SUPPORT = 62  # palabra de apoyo: sola NO alcanza el umbral
_SCORE_STACK = 4  # cada coincidencia adicional distinta
_SCORE_CAP = 99  # igual que el `min(0.99, ...)` de media_router

# Umbral de confianza. Mismo valor por defecto que
# `app/hologram/models.RoutingConfig.minimum_confidence`, y la comparación es la
# misma: `confidence < MINIMUM_CONFIDENCE` → no hay decisión específica.
MINIMUM_CONFIDENCE = 0.75

# Conjunto por defecto cuando hay señal institucional pero **ninguna regla llega
# al umbral**: lo mínimo para que el modelo sepa de quién habla sin volver a
# enviar los 15.516 chars. La cabecera con la nota de la sigla y el cierre
# anti-invención NO están acá: `get_context_sections` los añade siempre, se pida
# lo que se pida (son guardarraíles, no secciones).
DEFAULT_SECTIONS: tuple[str, ...] = ("name", "main_claim", "description")

# Sin **ninguna** señal institucional (un chiste, un saludo, una pregunta sobre
# el clima) no se manda ni una sección: sólo los guardarraíles.
_NO_SECTIONS: tuple[str, ...] = ()

# Palabras que delatan que la pregunta es sobre la institución. Sirven para dos
# cosas: activar reglas cuyos términos son genéricos de más para disparar solos
# (`precio`, `dura`) y distinguir «pregunta institucional sin regla clara» de
# «pregunta que no va con nosotros».
_INSTITUTIONAL_ANCHORS: frozenset[str] = frozenset(
    {
        "unev",
        "universidad",
        "universitario",
        "instituto",
        "carrera",
        "carreras",
        "programa",
        "programas",
        "estudiar",
        "estudio",
        "estudios",
        "matricula",
        "inscripcion",
        "admision",
        "clase",
        "clases",
        "cuatrimestre",
        "semestre",
        "titulo",
        "titulos",
        "tecnico",
        "diplomado",
        "campus",
        "beca",
        "becas",
        "programacion",
        "diseno",
        "grafico",
        "administracion",
        "empresas",
        "honduras",
    }
)

# Términos que abren el dominio Honduras. Las reglas hondureñas *genéricas*
# (ubicación, sitio, admisión, aprobación, resumen) sólo compiten si aparece uno
# de estos: es la traducción declarativa del `if honduras:` que las envolvía.
_HONDURAS_TERMS: tuple[str, ...] = (
    "honduras",
    "hondureño",
    "hondureña",
    "hondureñismo",
    "hondureñismos",
    "catracho",
    "catracha",
)

_WORD_RE = re.compile(r"[a-z0-9]+")


def _terms(text: str) -> tuple[str, ...]:
    """Tokens normalizados de un texto, en orden.

    Pasa por `normalize_text` (minúsculas + sin acentos) y luego parte por
    caracteres alfanuméricos, así que la puntuación y los signos de apertura
    (`¿`, `¡`) desaparecen sin reglas especiales.
    """
    return tuple(_WORD_RE.findall(normalize_text(text)))


def _norm_term(term: str) -> str:
    """Un término de regla, normalizado igual que la consulta.

    **Esto es lo que resucita los 6 literales acentuados muertos.** Antes, un
    literal como ``"hondureño"`` se comparaba contra un texto ya sin acentos y
    no coincidía nunca. Ahora los dos lados pasan por la misma normalización, de
    modo que el defecto no puede reaparecer al añadir un término nuevo: se
    escribe en español correcto y coincide igual.
    """
    return " ".join(_WORD_RE.findall(normalize_text(term)))


@dataclass(frozen=True)
class _Rule:
    """Una regla de enrutado. Todos sus términos se comparan por palabra completa."""

    topic: str
    sections: tuple[str, ...]
    skill: Callable[[], str] | None = None
    phrases: tuple[str, ...] = ()
    primary: tuple[str, ...] = ()
    support: tuple[str, ...] = ()
    # Si está, la regla sólo compite cuando aparece alguno de estos términos.
    # Reemplaza al anidamiento `if honduras: ... if carreras:` de la versión
    # anterior, y evita que términos genéricos secuestren preguntas ajenas.
    requires: tuple[str, ...] = ()
    # Literal (con acentos) que se pasa **tal cual** a `get_program_info`. Es una
    # clave de datos, no una comparación: no se normaliza nunca.
    program: str | None = None
    # Índices precalculados, para no normalizar en cada turno.
    _idx: dict[str, tuple] = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True)
class RouteDecision:
    """Qué decidió el router, con su confianza y las secciones que pide.

    Espejo de `LocalRouteResult` de `media_router.py`: candidatos, confianza y
    un ``reason_code`` legible para el log.
    """

    topic: str | None
    confidence: float
    sections: tuple[str, ...]
    reason_code: str
    candidates: tuple[str, ...] = ()

    @property
    def above_threshold(self) -> bool:
        return self.confidence >= MINIMUM_CONFIDENCE


def _index(rule: _Rule) -> dict[str, tuple]:
    """Normaliza los términos de una regla una sola vez, al importar el módulo."""
    if rule._idx:
        return rule._idx
    for name in ("phrases", "primary", "support", "requires"):
        normalized = [_norm_term(t) for t in getattr(rule, name)]
        words = frozenset(t for t in normalized if t and " " not in t)
        multi = tuple(sorted({t for t in normalized if " " in t}))
        rule._idx[name] = (words, multi)
    return rule._idx


def _hits(bucket: tuple, words: frozenset[str], joined: str) -> int:
    """Cuántos términos distintos del grupo aparecen como palabra completa."""
    single, multi = bucket
    count = len(single & words)
    count += sum(1 for phrase in multi if f" {phrase} " in joined)
    return count


def _score(rule: _Rule, words: frozenset[str], joined: str, whole: str) -> int:
    """Puntuación entera 0–100 de una regla, con el escalonado de media_router."""
    idx = _index(rule)
    if idx["requires"][0] or idx["requires"][1]:
        if not _hits(idx["requires"], words, joined):
            return 0

    phrase_hits = _hits(idx["phrases"], words, joined)
    primary_hits = _hits(idx["primary"], words, joined)
    support_hits = _hits(idx["support"], words, joined)
    total_hits = phrase_hits + primary_hits + support_hits
    if not total_hits:
        return 0

    if whole and (whole in idx["phrases"][1] or whole in idx["phrases"][0] or whole in idx["primary"][0]):
        base = _SCORE_EXACT
    elif phrase_hits:
        base = _SCORE_PHRASE
    elif primary_hits:
        base = _SCORE_PRIMARY
    else:
        base = _SCORE_SUPPORT
    return min(_SCORE_CAP, base + _SCORE_STACK * (total_hits - 1))


# ---------------------------------------------------------------------------
# Reglas
# ---------------------------------------------------------------------------
# Orden de `sections`: de más a menos relevante. El presupuesto de contexto
# recorta **por la cola**, así que la primera clave de cada regla es la que
# responde la pregunta y la última es el acompañamiento.
_RULES: tuple[_Rule, ...] = (
    # --- Honduras: patrimonio cultural (no es una segunda universidad) --------
    _Rule(
        topic="honduras.proceres",
        sections=("honduras",),
        skill=honduras.get_proceres_info,
        phrases=("cruz castro",),
        primary=("prócer", "próceres", "personaje", "personajes", "biografía", "Membreño", "Annarella", "Bernárdez"),
        support=_HONDURAS_TERMS,
    ),
    _Rule(
        topic="honduras.vulgarismos",
        sections=("honduras",),
        skill=honduras.get_vulgarismos_info,
        # "minimo" estaba acá y mandaba «¿cuál es el mínimo para entrar?» a
        # lingüística. No es un sinónimo de nada de esta rama: se quitó.
        primary=("vulgarismo", "vulgarismos", "voseo", "leísmo", "hondureñismo", "hondureñismos", "modismo", "modismos"),
        support=(*_HONDURAS_TERMS, "habla", "hablan", "lenguaje", "dialecto", "acento"),
    ),
    _Rule(
        topic="honduras.simbolos",
        sections=("honduras",),
        skill=honduras.get_simbolos_patrios_info,
        phrases=("convenio 169", "símbolos patrios"),
        primary=("símbolo", "símbolos", "patrio", "patrios", "piah", "oit", "bandera", "escudo", "himno"),
        support=(*_HONDURAS_TERMS, "convenio"),
    ),
    _Rule(
        topic="honduras.cultura",
        sections=("honduras",),
        skill=honduras.get_university_summary,
        phrases=("lluvia de peces", "patrimonio cultural", "patrimonio inmaterial"),
        primary=("folclor", "folclore", "folklore", "tradición", "tradiciones", "leyenda", "leyendas", "costumbre", "costumbres", "patrimonio"),
        support=(*_HONDURAS_TERMS, "cultura", "cultural"),
    ),
    _Rule(
        topic="honduras.precolombina",
        sections=("honduras",),
        program="era precolombina y ancestral",
        phrases=("era precolombina",),
        primary=("precolombina", "precolombino", "ancestral"),
        support=_HONDURAS_TERMS,
    ),
    _Rule(
        topic="honduras.linguistica",
        sections=("honduras",),
        program="evolución lingüística y colonial",
        phrases=("evolución lingüística",),
        primary=("lingüística", "lingüístico", "colonial", "colonia"),
        support=_HONDURAS_TERMS,
    ),
    _Rule(
        topic="honduras.investigacion",
        sections=("honduras",),
        program="periodo de investigación y reconocimiento (s. xix-xx)",
        phrases=("investigación y reconocimiento", "periodo de investigación"),
        # "investigación" y "reconocimiento" quedan de **apoyo**, no primarios:
        # solos no deben secuestrar «¿hacen investigación en la UNEV?».
        support=(*_HONDURAS_TERMS, "investigación", "reconocimiento"),
    ),
    _Rule(
        topic="honduras.contemporaneo",
        sections=("honduras",),
        program="periodo contemporáneo y salvaguarda (2022-2035)",
        phrases=("periodo contemporáneo",),
        primary=("contemporáneo", "contemporánea", "salvaguarda"),
        support=_HONDURAS_TERMS,
    ),
    # Genéricas de Honduras: sólo compiten si se nombra Honduras, igual que
    # cuando vivían dentro del `if honduras:`.
    _Rule(
        topic="honduras.periodos",
        sections=("honduras",),
        skill=honduras.get_programs_summary,
        requires=_HONDURAS_TERMS,
        primary=("periodo", "periodos", "etapa", "etapas", "historia", "cronología"),
        support=("carrera", "carreras", "programa", "programas"),
    ),
    _Rule(
        topic="honduras.ubicacion",
        sections=("honduras",),
        skill=honduras.get_location_info,
        requires=_HONDURAS_TERMS,
        phrases=("dónde queda", "dónde está", "cómo llego"),
        primary=("ubicación", "dirección", "capital", "tegucigalpa"),
        support=_HONDURAS_TERMS,
    ),
    _Rule(
        topic="honduras.website",
        sections=("honduras",),
        skill=honduras.get_website_info,
        requires=_HONDURAS_TERMS,
        primary=("página", "sitio", "website", "url", "web"),
        support=_HONDURAS_TERMS,
    ),
    _Rule(
        topic="honduras.admision",
        sections=("honduras",),
        skill=honduras.get_admission_info,
        requires=_HONDURAS_TERMS,
        primary=("admisión", "admisiones", "inscripción", "matrícula", "ingresar"),
        support=_HONDURAS_TERMS,
    ),
    _Rule(
        topic="honduras.aprobacion",
        sections=("honduras",),
        skill=honduras.get_approval_info,
        requires=_HONDURAS_TERMS,
        phrases=("convenio 169",),
        primary=("aprobación", "aprobada", "oficial"),
        support=_HONDURAS_TERMS,
    ),
    _Rule(
        topic="honduras.general",
        sections=("honduras",),
        skill=honduras.get_university_summary,
        requires=_HONDURAS_TERMS,
        primary=_HONDURAS_TERMS,
    ),
    # --- UNEV ----------------------------------------------------------------
    _Rule(
        topic="unev.programas",
        sections=("programs", "academic_model"),
        skill=get_programs_summary,
        phrases=("oferta académica", "qué puedo estudiar", "qué estudiar"),
        primary=("carrera", "carreras", "programa", "programas", "tecnólogo"),
        support=("ofrecen", "ofrece", "hay", "estudiar", "técnico"),
    ),
    _Rule(
        topic="unev.programa_web",
        sections=("programs", "academic_model"),
        program="programación web",
        phrases=("programación web", "desarrollo web"),
        primary=("programación", "programador", "programar"),
        support=("carrera", "programa", "estudiar", "web", "software", "código"),
    ),
    _Rule(
        topic="unev.programa_diseno",
        sections=("programs", "academic_model"),
        program="diseño gráfico",
        phrases=("diseño gráfico",),
        primary=("diseño", "gráfico", "diseñador"),
        support=("carrera", "programa", "estudiar"),
    ),
    _Rule(
        topic="unev.programa_admin",
        sections=("programs", "academic_model"),
        program="administración de empresas",
        phrases=("administración de empresas",),
        primary=("administración", "empresa", "empresas", "administrador"),
        support=("carrera", "programa", "estudiar", "negocio", "negocios"),
    ),
    _Rule(
        topic="unev.duracion",
        sections=("academic_model", "programs"),
        # Genérica de más para disparar sola: «¿y cuánto dura?» sin sujeto es
        # justamente el follow-up que resuelve WAVE-06, no esta WAVE.
        requires=tuple(sorted(_INSTITUTIONAL_ANCHORS)),
        phrases=("cuánto dura", "cuánto tiempo", "cuántos años", "cuántos meses"),
        primary=("duración", "dura", "duran", "año", "años"),
        support=("carrera", "carreras", "programa", "programas", "ciclo", "ciclos"),
    ),
    _Rule(
        topic="unev.costo",
        sections=("admission_requirements", "common_questions"),
        requires=tuple(sorted(_INSTITUTIONAL_ANCHORS)),
        phrases=("cuánto cuesta", "cuánto vale", "forma de pago"),
        primary=("precio", "precios", "costo", "costos", "cuesta", "mensualidad", "arancel", "aranceles", "pago", "pagos"),
        support=("carrera", "carreras", "matrícula", "inscripción"),
    ),
    _Rule(
        topic="unev.admision",
        sections=("admission_requirements", "programs"),
        skill=get_admission_info,
        phrases=("para entrar", "cómo ingreso", "cómo me inscribo", "requisitos de admisión"),
        # "mínimo"/"mínimos" viven acá, que es su sitio: preguntan por la nota o
        # el requisito mínimo de ingreso.
        primary=("admisión", "admisiones", "inscripción", "matrícula", "ingresar", "aplicar", "requisito", "requisitos", "mínimo", "mínimos"),
        support=("entrar", "ingreso", "estudiar", "carrera", "carreras"),
    ),
    _Rule(
        topic="unev.ubicacion",
        sections=("address", "infrastructure"),
        skill=get_location_info,
        phrases=("dónde queda", "dónde está", "dónde se encuentra", "cómo llego", "en qué dirección"),
        primary=("ubicación", "dirección", "sede", "campus", "queda", "ubicada", "ubicado"),
        support=("unev", "universidad", "instalaciones"),
    ),
    _Rule(
        topic="unev.aprobacion",
        sections=("approval", "governance"),
        skill=get_approval_info,
        phrases=("válidos los títulos", "está aprobada"),
        primary=("aprobada", "aprobado", "aprobación", "acreditada", "acreditación", "oficial", "consejo", "registro", "ces", "válido", "válidos", "validez"),
        support=("título", "títulos", "unev", "universidad", "reconocida"),
    ),
    _Rule(
        topic="unev.website",
        sections=("website",),
        skill=get_website_info,
        phrases=("página web", "sitio web", "página oficial"),
        primary=("página", "sitio", "website", "url"),
        support=("unev", "universidad", "web", "internet"),
    ),
    _Rule(
        topic="unev.siglas",
        sections=("acronyms", "full_name", "name", "independence_note"),
        skill=get_university_summary,
        phrases=("qué significa unev", "qué significa la unev", "qué quiere decir unev", "nombre completo"),
        primary=("sigla", "siglas", "acrónimo", "acrónimos", "significa", "significan", "abreviatura"),
        support=("unev", "universidad", "nombre"),
    ),
    _Rule(
        topic="unev.presentacion",
        sections=DEFAULT_SECTIONS,
        skill=get_university_summary,
        phrases=(
            "qué es unev",
            "qué es la unev",
            "qué es la universidad",
            "cuéntame de unev",
            "háblame de unev",
            "quién eres",
            "preséntate",
            "información de unev",
            "información sobre unev",
            "sobre unev",
        ),
        primary=("unev",),
        support=("universidad", "instituto", "institución"),
    ),
)

# Los temas son únicos: el desempate por nombre es total y determinista.
assert len({rule.topic for rule in _RULES}) == len(_RULES)
for _rule in _RULES:
    _index(_rule)


def route_query(user_input: str) -> RouteDecision:
    """Enruta una consulta evaluando **todas** las reglas; gana la mejor.

    Devuelve siempre un `RouteDecision`, nunca ``None``: cuando nada llega al
    umbral, el resultado trae el conjunto por defecto y el motivo. Así el
    llamador no tiene que replicar la política de "qué mando si no sé".

    Reglas de decisión, en orden:

    - **Ninguna coincidencia y ninguna palabra institucional** → sin secciones.
      Un chiste o un saludo no necesitan los datos de la universidad, y mandarlos
      es exactamente el desperdicio que esta WAVE elimina.
    - **Hay señal institucional pero nada supera el umbral** → `DEFAULT_SECTIONS`.
      El modelo sabe de quién habla sin recibir el bloque completo.
    - **Alguna regla supera el umbral** → sus secciones.
    """
    terms = _terms(user_input)
    words = frozenset(terms)
    joined = f" {' '.join(terms)} "
    whole = " ".join(terms)

    scored = [(rule, _score(rule, words, joined, whole)) for rule in _RULES]
    scored = [(rule, score) for rule, score in scored if score]
    # Desempate por nombre de tema: dos reglas empatadas resuelven siempre igual,
    # corrida tras corrida y máquina tras máquina.
    scored.sort(key=lambda item: (-item[1], item[0].topic))

    candidates = tuple(rule.topic for rule, _ in scored[:5])
    if not scored:
        institutional = bool(words & _INSTITUTIONAL_ANCHORS)
        return RouteDecision(
            topic=None,
            confidence=0.0,
            sections=DEFAULT_SECTIONS if institutional else _NO_SECTIONS,
            reason_code="INSTITUTIONAL_NO_RULE" if institutional else "NO_LOCAL_MATCH",
        )

    best_rule, best_score = scored[0]
    confidence = min(0.99, best_score / 100)
    if confidence < MINIMUM_CONFIDENCE:
        return RouteDecision(
            topic=None,
            confidence=confidence,
            sections=DEFAULT_SECTIONS,
            reason_code="BELOW_THRESHOLD",
            candidates=candidates,
        )
    return RouteDecision(
        topic=best_rule.topic,
        confidence=confidence,
        sections=best_rule.sections,
        reason_code="RULE_MATCH",
        candidates=candidates,
    )


def _render(rule: _Rule) -> str | None:
    """Texto de la skill ganadora, o ``None`` si la regla no tiene respuesta propia."""
    if rule.program is not None:
        # Literal con acentos: es una **clave de datos**, se pasa tal cual.
        source = honduras if rule.topic.startswith("honduras.") else None
        return (source.get_program_info if source else get_program_info)(rule.program)
    if rule.skill is not None:
        return rule.skill()
    return None


def route_local_skill(user_input):
    """Respuesta local para la consulta, o ``None`` si no hay ninguna.

    Contrato intacto (``str | None``): `call.ask_ai` la usa para cortocircuitar
    antes del LLM y `metrics._local_skill_would_answer` sólo mira su verdad.
    Lo que cambió es **cómo** se decide, no qué se devuelve.
    """
    decision = route_query(user_input)
    if decision.topic is None:
        return None
    for rule in _RULES:
        if rule.topic == decision.topic:
            return _render(rule)
    return None
