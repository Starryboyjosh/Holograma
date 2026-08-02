"""Tests del router determinista con puntuación y umbral (WAVE-05).

El router local no tenía ni un test. Enrutaba con una cascada de
``if any(palabra in texto ...)`` que fallaba de dos maneras medibles, y las dos
llegaban al visitante:

- **Subcadena en vez de palabra**: «Háblame de Programación Web» contenía
  ``"habla"`` y se respondía con vulgarismos hondureños.
- **Gana el primer ``if``**, no la mejor coincidencia, así que no había forma de
  arreglar lo anterior salvo reordenando a ciegas.

Estos casos fijan el comportamiento nuevo: palabra completa, todas las reglas
puntuadas, umbral explícito y latencia acotada.
"""

import time

import pytest

import skills.university as U
from skills.router import (
    DEFAULT_SECTIONS,
    MINIMUM_CONFIDENCE,
    route_local_skill,
    route_query,
)

# Las 11 preguntas de la auditoría, con el tema esperado. ``None`` significa
# «ninguna regla debe superar el umbral»: son preguntas que no son nuestras
# (un chiste, la hora) o que dependen de memoria conversacional (WAVE-06).
PREGUNTAS_OBLIGATORIAS: tuple[tuple[str, str | None], ...] = (
    ("Cuéntame un chiste", None),
    ("¿Qué significa UNEV?", "unev.siglas"),
    ("¿Qué carreras ofrecen?", "unev.programas"),
    ("Háblame de Programación Web", "unev.programa_web"),
    ("¿Y cuánto dura?", "unev.duracion"),
    ("¿Dónde queda la universidad?", "unev.ubicacion"),
    ("¿Los títulos son válidos?", "unev.aprobacion"),
    ("¿Qué es la lluvia de peces?", "honduras.cultura"),
    ("Hola", None),
    ("¿Cuál es el precio actual de algo que requiere internet?", None),
    ("¿Qué hora es?", None),
)


@pytest.fixture(autouse=True)
def contexto_limpio():
    """Cachés de contexto limpias: el router pide secciones y las cachés son globales."""
    U.invalidate_context_cache()
    yield
    U.invalidate_context_cache()


def test_hablame_de_no_cae_en_vulgarismos():
    """El defecto que motivó la WAVE: ``"habla"`` ⊂ ``"hablame"``.

    Con comparación por subcadena, **cualquier** «Háblame de…» se respondía con
    lingüística hondureña. Se comprueba sobre tres temas distintos para que el
    caso no se pueda pasar arreglando sólo el de Programación Web.
    """
    for pregunta in (
        "Háblame de Programación Web",
        "Háblame de la UNEV",
        "Háblame de los requisitos de admisión",
    ):
        decision = route_query(pregunta)
        assert decision.topic != "honduras.vulgarismos", pregunta
        assert decision.topic is not None, pregunta
        respuesta = route_local_skill(pregunta)
        assert respuesta and "vulgarismo" not in respuesta.lower(), pregunta


def test_minimo_va_a_admision():
    """«mínimo» era un término de vulgarismos y secuestraba una pregunta de ingreso."""
    decision = route_query("¿Cuál es el mínimo para entrar?")
    assert decision.topic == "unev.admision"
    assert "admission_requirements" in decision.sections
    assert "Requisitos de admisión" in (route_local_skill("¿Cuál es el mínimo para entrar?") or "")


def test_vulgarismos_sigue_funcionando():
    """Arreglar el falso positivo no puede romper el caso legítimo."""
    for pregunta in (
        "¿Qué son los vulgarismos hondureños?",
        "Explícame el voseo en Honduras",
        "¿Qué es un hondureñismo?",
    ):
        assert route_query(pregunta).topic == "honduras.vulgarismos", pregunta


def test_literales_acentuados_alcanzables():
    """Los 6 literales acentuados estaban muertos por construcción.

    ``normalize_text`` quita acentos de la consulta, así que un término de regla
    escrito ``"hondureño"`` no coincidía **nunca**. Ahora los dos lados pasan por
    la misma normalización; esto vigila que siga siendo así.
    """
    for pregunta, esperado in (
        ("¿Qué es un hondureñismo?", "honduras.vulgarismos"),
        ("Háblame de la era precolombina", "honduras.precolombina"),
        ("¿Cuál fue la evolución lingüística de Honduras?", "honduras.linguistica"),
        ("Cuéntame del periodo contemporáneo de Honduras", "honduras.contemporaneo"),
        ("¿Qué pasó en el periodo de investigación y reconocimiento?", "honduras.investigacion"),
    ):
        assert route_query(pregunta).topic == esperado, pregunta


def test_investigacion_no_secuestra_la_pregunta_institucional():
    """Resucitar «investigación» no debe crear un falso positivo nuevo.

    Es término de **apoyo**, no primario: solo no llega al umbral, así que
    «¿hacen investigación en la UNEV?» sigue siendo una pregunta sobre la UNEV.
    """
    decision = route_query("¿Hacen investigación en la UNEV?")
    assert decision.topic != "honduras.investigacion"
    assert decision.sections == DEFAULT_SECTIONS


def test_umbral_de_confianza():
    """Bajo el umbral no se inventa una sección: se cae al conjunto por defecto."""
    # Señal fuerte: supera el umbral y trae sus propias secciones.
    fuerte = route_query("¿Dónde queda la UNEV?")
    assert fuerte.confidence >= MINIMUM_CONFIDENCE
    assert fuerte.above_threshold and fuerte.reason_code == "RULE_MATCH"

    # Señal débil (sólo una palabra de apoyo): no alcanza, conjunto por defecto.
    debil = route_query("¿Cuál es el precio actual de algo que requiere internet?")
    assert 0 < debil.confidence < MINIMUM_CONFIDENCE
    assert debil.topic is None and debil.reason_code == "BELOW_THRESHOLD"
    assert debil.sections == DEFAULT_SECTIONS

    # Cero señal: ni una sección institucional.
    nula = route_query("Cuéntame un chiste")
    assert nula.confidence == 0.0
    assert nula.sections == () and nula.reason_code == "NO_LOCAL_MATCH"


def test_decision_es_determinista():
    """Misma pregunta, misma decisión. Sin esto no se puede cachear ni auditar."""
    for pregunta, _ in PREGUNTAS_OBLIGATORIAS:
        primera = route_query(pregunta)
        assert all(route_query(pregunta) == primera for _ in range(5)), pregunta


def test_route_local_skill_conserva_su_contrato():
    """Devuelve ``str`` o ``None``, nunca otra cosa.

    `call.ask_ai` corta el turno con su valor de verdad y
    `metrics._local_skill_would_answer` sólo lo convierte a booleano; cambiar el
    tipo rompería las dos en silencio.
    """
    for pregunta, esperado in PREGUNTAS_OBLIGATORIAS:
        respuesta = route_local_skill(pregunta)
        assert respuesta is None or isinstance(respuesta, str)
        if esperado is None:
            assert respuesta is None, pregunta


def test_router_bajo_1ms():
    """Enrutar tiene que ser gratis comparado con la llamada al LLM.

    Presupuesto: 1 ms de media. Es holgado a propósito —hoy ronda las centésimas
    de milisegundo— porque lo que vigila no es la microoptimización sino que
    nadie meta una llamada de red, un modelo o un embedding en el camino: eso
    costaría cientos de milisegundos y se vería de inmediato.
    """
    consultas = [pregunta for pregunta, _ in PREGUNTAS_OBLIGATORIAS] * 10
    inicio = time.perf_counter()
    for consulta in consultas:
        route_query(consulta)
    media_ms = (time.perf_counter() - inicio) / len(consultas) * 1000
    assert media_ms < 1.0, f"{media_ms:.4f} ms de media por consulta"


@pytest.mark.parametrize(
    ("pregunta", "esperado"),
    PREGUNTAS_OBLIGATORIAS,
)
def test_las_11_preguntas_obligatorias(pregunta, esperado):
    """El dataset mínimo de la auditoría, pregunta por pregunta.

    Es el marcador de la WAVE: la línea base acertaba 4 de 7 preguntas
    institucionales. El caso de «¿Y cuánto dura?» lo resuelve WAVE-06: la
    memoria de sesión expande la referencia con la entidad activa **antes** de
    enrutar (ver `app/services/session_memory` y
    `tests/test_session_memory.py`); acá se simula el estado que deja el turno
    anterior y el router ve la consulta completa.
    """
    if pregunta == "¿Y cuánto dura?":
        from app.services.session_memory import SessionMemory

        sesion = SessionMemory()
        sesion.observe(
            "Háblame de Programación Web",
            "Programación Web tiene una duración de 2 años.",
        )
        resuelta = sesion.resolve(pregunta)
        assert resuelta != pregunta
        # La expansión nombra la carrera, y la regla del programa puntúa más
        # (frase + primario + apoyo) que la de duración sola. Es el destino
        # correcto: su respuesta local trae la duración exacta ("2 años").
        assert route_query(resuelta).topic == "unev.programa_web"
        return
    assert route_query(pregunta).topic == esperado
