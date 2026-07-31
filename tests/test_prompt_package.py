"""Tests del ensamblador único de prompt (WAVE-05).

Lo que estos casos protegen es un equilibrio, no un número: el prompt tiene que
encoger mucho (15.516 chars de contexto por turno, se responda lo que se
responda) **sin** que el modelo pierda el dato con el que responder. Recortar
por recortar es fácil y se paga en alucinaciones.

Por eso los dos casos centrales van juntos y ninguno vale sin el otro:

- `test_contexto_medio_bajo_2500_chars` mide que de verdad encogió.
- `test_datos_criticos_presentes` mide que cada pregunta institucional sigue
  llevando encima la sección que la responde.

El resto vigila el presupuesto, los guardarraíles y el rollback por variable de
entorno, que es la salida de emergencia si esto se porta mal en el evento.
"""

import pytest

import prompt_package as PP
import skills.unev_content as UC
import skills.university as U
from prompt_package import (
    MAX_CONTEXT_CHARS,
    MAX_SECTION_CHARS,
    build_prompt_package,
    build_university_context,
)

# Pregunta institucional → fragmento que el modelo necesita tener delante para
# responderla sin inventar. Son literales del contenido real, no paráfrasis.
DATOS_CRITICOS: tuple[tuple[str, str], ...] = (
    ("¿Qué significa UNEV?", "Instituto Universitario de Educación Virtual"),
    ("¿Qué carreras ofrecen?", "Programación Web"),
    ("Háblame de Programación Web", "Programación Web"),
    ("¿Dónde queda la universidad?", "San Pedro Sula"),
    ("¿Los títulos son válidos?", "Aprobación y validez de títulos"),
    ("¿Cuál es el mínimo para entrar?", "Requisitos de admisión"),
)

PREGUNTAS_OBLIGATORIAS: tuple[str, ...] = (
    "Cuéntame un chiste",
    "¿Qué significa UNEV?",
    "¿Qué carreras ofrecen?",
    "Háblame de Programación Web",
    "¿Y cuánto dura?",
    "¿Dónde queda la universidad?",
    "¿Los títulos son válidos?",
    "¿Qué es la lluvia de peces?",
    "Hola",
    "¿Cuál es el precio actual de algo que requiere internet?",
    "¿Qué hora es?",
)


@pytest.fixture(autouse=True)
def contexto_limpio(monkeypatch):
    """Cachés limpias y selección activa, pase lo que pase en el entorno.

    Lo segundo importa: si el operador dejó ``HOLOGRAM_SELECTIVE_CONTEXT=0``
    exportado tras un rollback, la suite mediría el camino equivocado y pasaría
    en verde sin comprobar nada. El caso del rollback fija la variable él mismo.
    """
    monkeypatch.setenv("HOLOGRAM_SELECTIVE_CONTEXT", "1")
    U.invalidate_context_cache()
    yield
    U.invalidate_context_cache()


def _paquete(pregunta: str) -> PP.PromptPackage:
    """Paquete con ``system_prompt`` neutro: acá se mide el contexto, no el modo."""
    return build_prompt_package(pregunta, system_prompt="")


def test_contexto_medio_bajo_2500_chars():
    """La mitad del objetivo de la WAVE: que el bloque institucional encoja."""
    completo = len(U.get_university_context())
    tamanos = [_paquete(pregunta).context_chars for pregunta in PREGUNTAS_OBLIGATORIAS]
    media = sum(tamanos) / len(tamanos)
    assert media < 2500, f"media {media:.0f} chars"
    # Y que ninguna pregunta suelta se acerque al bloque completo: una media baja
    # con un pico de 15.000 chars no sería una mejora, sería una lotería.
    assert max(tamanos) < completo / 2


def test_datos_criticos_presentes():
    """La otra mitad, y la que importa: el dato para responder sigue estando.

    Un contexto corto que no trae la respuesta es peor que el bloque completo:
    el modelo rellena el hueco. Este caso es el que impide "optimizar" el prompt
    a base de quitarle lo que hace falta.
    """
    for pregunta, dato in DATOS_CRITICOS:
        contexto = _paquete(pregunta).university_context
        assert dato in contexto, f"{pregunta!r} perdió {dato!r}"


def test_guardarrailes_siempre_presentes():
    """Cabecera y cierre van en todos los turnos, incluso sin ninguna sección.

    Son justo lo que más falta hace cuando el contexto es mínimo: sin la nota de
    la sigla, el STT vuelve a colar «UNED»; sin la línea de cierre, el modelo
    inventa lo que no le dieron.
    """
    for pregunta in PREGUNTAS_OBLIGATORIAS:
        contexto = _paquete(pregunta).university_context
        assert "la sigla correcta es UNEV" in contexto, pregunta
        assert "no inventes" in contexto, pregunta

    # Caso extremo: presupuesto ridículo. Los guardarraíles no se negocian.
    minimo = build_prompt_package(
        "Cuéntame un chiste", system_prompt="", total_limit=10, section_limit=10
    )
    assert "la sigla correcta es UNEV" in minimo.university_context
    assert "no inventes" in minimo.university_context


def test_pregunta_no_institucional_no_lleva_secciones():
    """Un chiste no necesita la ficha de la universidad."""
    paquete = _paquete("Cuéntame un chiste")
    assert paquete.sections == ()
    assert paquete.topic is None
    # Sólo guardarraíles: es el suelo, y es pequeño.
    assert paquete.context_chars < 500


def test_tope_por_seccion_descarta_seccion_inflada():
    """Un campo inflado en el editor no puede llenar el prompt.

    Se descarta **entero**, no se trunca: media frase institucional se lee como
    un hecho completo y equivocado, mientras que la ausencia la cubre el
    guardarraíl anti-invención.
    """
    paquete = build_prompt_package(
        "¿Qué es la lluvia de peces?", system_prompt="", section_limit=100
    )
    assert "honduras" in paquete.dropped_sections
    assert paquete.sections == ()
    assert "la sigla correcta es UNEV" in paquete.university_context


def test_tope_total_respetado_con_campo_inflado(monkeypatch):
    """Con un campo real inflado a 40.000 chars, el bloque sigue acotado.

    El panel permite hasta ``MAX_FIELD_CHARS`` (8.000) por campo, y nada impide
    que mañana alguien pegue mucho más de golpe: el presupuesto tiene que
    aguantar sin que el turno se caiga.
    """
    info = dict(UC.get_unev_info())
    info["academic_model"] = "X" * 40000
    # `skills.university` importó la función por nombre, así que se parchea su
    # binding: parchear el módulo de origen no la alcanzaría.
    monkeypatch.setattr(U, "get_unev_info", lambda: info)
    U.invalidate_context_cache()

    paquete = _paquete("¿Qué carreras ofrecen?")
    assert paquete.context_chars <= MAX_CONTEXT_CHARS
    assert "academic_model" in paquete.dropped_sections
    # Lo que sí cabía se conserva: no se tira el turno por un campo roto.
    assert "programs" in paquete.sections
    assert "Programación Web" in paquete.university_context


def test_presupuesto_es_coherente():
    """El tope por sección tiene que estar por debajo del total, o no acota nada."""
    assert MAX_SECTION_CHARS <= MAX_CONTEXT_CHARS


def test_flag_rollback_devuelve_bloque_completo(monkeypatch):
    """``HOLOGRAM_SELECTIVE_CONTEXT=0`` restituye el comportamiento anterior.

    Exacto, carácter por carácter: es la salida de emergencia del evento y tiene
    que ser una decisión de operador, no un despliegue.
    """
    completo = U.get_university_context()
    for valor in ("0", "false", "no", "off"):
        monkeypatch.setenv("HOLOGRAM_SELECTIVE_CONTEXT", valor)
        assert not PP.selective_context_enabled()
        for pregunta in PREGUNTAS_OBLIGATORIAS:
            paquete = _paquete(pregunta)
            assert paquete.university_context == completo, (valor, pregunta)
            assert paquete.selective is False

    monkeypatch.setenv("HOLOGRAM_SELECTIVE_CONTEXT", "1")
    assert PP.selective_context_enabled()
    assert _paquete("¿Qué carreras ofrecen?").university_context != completo


def test_paquete_es_determinista():
    """Misma pregunta, mismo prompt. Sin esto no hay caché de prefijo ni auditoría."""
    for pregunta in PREGUNTAS_OBLIGATORIAS:
        primero = _paquete(pregunta)
        for _ in range(3):
            otro = _paquete(pregunta)
            assert otro.university_context == primero.university_context, pregunta
            assert otro.sections == primero.sections, pregunta


def test_orden_de_secciones_no_altera_el_texto():
    """El texto depende de qué se pide, no de en qué orden lo pidió el router."""
    claves = ("programs", "academic_model", "name")
    directo = U.get_context_sections(claves)
    invertido = U.get_context_sections(tuple(reversed(claves)))
    assert directo == invertido


def test_mensajes_de_sistema_conservan_el_formato():
    """El paquete formatea los mensajes de sistema igual que antes.

    `llm_backend._build_messages` delega acá, así que este caso es el que
    garantiza que la delegación no cambió ni el orden ni los prefijos.
    """
    paquete = build_prompt_package(
        "¿Qué carreras ofrecen?", system_prompt="SISTEMA", camera_context="una persona"
    )
    mensajes = paquete.system_messages()
    assert [m["role"] for m in mensajes] == ["system", "system", "system"]
    assert mensajes[0]["content"] == "SISTEMA"
    assert mensajes[1]["content"] == paquete.university_context
    assert mensajes[2]["content"] == "Contexto actual de la cámara:\nuna persona"

    sin_camara = build_prompt_package("¿Qué carreras ofrecen?", system_prompt="SISTEMA")
    assert len(sin_camara.system_messages()) == 2


def test_ambas_rutas_usan_el_mismo_ensamblador():
    """Voz/CLI y web deciden el contexto en el mismo sitio. Ese es el objetivo.

    Antes, `call.ask_ai` pedía el bloque completo y `stream_llm_response` volvía
    a pedirlo por dentro: dos decisiones que podían divergir sin que nadie lo
    notara. Ahora las dos entran por `prompt_package`, y el atajo que usa la ruta
    de voz devuelve exactamente el contexto del paquete completo.
    """
    import call
    import llm_backend

    assert call.build_university_context is build_university_context
    assert llm_backend.build_prompt_package is build_prompt_package
    assert llm_backend.PromptPackage is PP.PromptPackage

    for pregunta in PREGUNTAS_OBLIGATORIAS:
        assert build_university_context(pregunta) == _paquete(pregunta).university_context


def test_ruta_de_voz_envia_el_contexto_reducido(monkeypatch):
    """Comprobación de comportamiento, no sólo de cableado: qué recibe el LLM."""
    import call

    capturado = {}

    def _spy(**kwargs):
        capturado.update(kwargs)
        return "ok"

    monkeypatch.setattr(call, "generate_reply", _spy)
    monkeypatch.setattr(call, "get_selected_backend", lambda: "openrouter")
    monkeypatch.setattr(call, "_camera_context_for_prompt", lambda _: None)

    assert call.ask_ai("¿Dónde queda la universidad?") == "ok"
    contexto = capturado["university_context"]
    assert "San Pedro Sula" in contexto
    assert len(contexto) < len(U.get_university_context()) / 2


def test_metadatos_para_la_metrica():
    """El paquete trae lo que la línea de métrica de WAVE-03 necesita medir."""
    paquete = _paquete("¿Qué carreras ofrecen?")
    assert paquete.context_chars == len(paquete.university_context)
    assert paquete.topic == "unev.programas"
    assert paquete.local_skill_hit is True
    assert 0 < paquete.confidence <= 0.99
    assert paquete.reason_code == "RULE_MATCH"

    vacio = _paquete("Cuéntame un chiste")
    assert vacio.local_skill_hit is False
    assert vacio.confidence == 0.0
