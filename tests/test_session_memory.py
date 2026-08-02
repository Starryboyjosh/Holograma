"""Tests de WAVE-06: memoria de sesión y preguntas de seguimiento.

El criterio de aceptación: «Háblame de Programación Web» → «¿Y cuánto dura?»
responde sobre Programación Web, en las dos rutas (voz síncrona y web async).

Disciplina de la WAVE (runbook):

* **Reloj inyectado** para la expiración: ningún test duerme minutos.
* **Cero red**: la ruta de voz se prueba con el backend monkeypatcheado
  (misma técnica que `tests/test_metrics.py`); la web con un LLM doble.
* **El estado es de proceso (kiosco)**: un solo estado compartido; dos
  servicios (dos "conexiones") ven la misma conversación.
* **Firmas retrocompatibles**: los seis símbolos del hallazgo A siguen
  llamándose sin el parámetro de historial.
"""

import asyncio
import inspect

import pytest

import llm_backend as lb
from app.services.conversation import ConversationService
from app.services.llm import LLMService
from app.services.session_memory import (
    SessionMemory,
    get_session,
    reset_session,
)
from prompt_package import MAX_CONTEXT_CHARS, PromptPackage
from skills.router import route_local_skill

SYSTEM = "Eres un asistente de la UNEV."
CONTEXTO = ""

# La línea base de WAVE-05 (PROGRESS.md): prompt total por turno antes de
# cualquier poda. El historial tiene que caber holgadamente por debajo de eso.
PROMPT_TOTAL_PRE_WAVE05 = 18_439


# --------------------------------------------------------------------------- #
# Dobles
# --------------------------------------------------------------------------- #
class RecordingLLM:
    """Un LLM doble que acepta `history` y registra todo lo que recibe."""

    def __init__(self, chunks=("respuesta",)):
        self._chunks = chunks
        self.calls: list[dict] = []

    async def stream(self, prompt, camera_context=None, history=None):
        self.calls.append(
            {
                "prompt": prompt,
                "camera_context": camera_context,
                "history": list(history or []),
            }
        )
        for chunk in self._chunks:
            yield chunk


class _FakeConn:
    def __init__(self):
        self.messages: list[dict] = []

    async def broadcast(self, message: dict) -> None:
        self.messages.append(message)


@pytest.fixture(autouse=True)
def sesion_limpia():
    """Cada test arranca con el estado del proceso vacío y lo restaura."""
    reset_session()
    yield
    reset_session()


# --------------------------------------------------------------------------- #
# Ruta de voz (síncrona, por `call.ask_ai`)
# --------------------------------------------------------------------------- #
def test_followup_duracion_ruta_voz(monkeypatch):
    """«Háblame de Programación Web» → «¿Y cuánto dura?» responde 2 años.

    Sin el fix, la segunda pregunta no tiene sujeto y el modelo no sabe de qué
    hablar; acá además el doble registra los mensajes y demuestra que la
    referencia llegó expandida y con el historial enhebrado.
    """
    from call import ask_ai

    recorded: dict = {}
    real_build = lb._build_messages

    def fake_build(
        user_input, system_prompt, university_context, camera_context=None, history=None
    ):
        recorded["messages"] = real_build(
            user_input, system_prompt, university_context, camera_context, history
        )
        return recorded["messages"]

    monkeypatch.setattr(lb, "_build_messages", fake_build)
    monkeypatch.setattr(lb, "get_selected_backend", lambda: "openrouter")
    monkeypatch.setattr(lb, "_candidate_backends", lambda primary: ["openrouter"])

    def fake_tokens(backend, messages):
        user = messages[-1]["content"].lower()
        if "programación" in user and "web" in user:
            yield "Programación Web tiene una duración de 2 años."
        else:
            yield "No sé de qué carrera hablas."

    monkeypatch.setattr(lb, "_iter_openai_compatible_tokens", fake_tokens)

    primera = ask_ai("Háblame de Programación Web")
    assert "2 años" in primera

    segunda = ask_ai("¿Y cuánto dura?")
    assert "2 años" in segunda, (
        "El follow-up no se resolvió contra la entidad activa; "
        f"el doble respondió: {segunda!r}"
    )

    mensajes = recorded["messages"]
    ultima_pregunta = mensajes[-1]["content"]
    assert "Programación Web" in ultima_pregunta
    assert [m["role"] for m in mensajes] == ["system", "user", "assistant", "user"]


# --------------------------------------------------------------------------- #
# Ruta web (async, por ConversationService.handle_prompt)
# --------------------------------------------------------------------------- #
def test_followup_duracion_ruta_web():
    """Lo mismo por la ruta web: ambas rutas comparten el estado y el historial."""

    async def run():
        llm = RecordingLLM(("Programación Web tiene una duración de 2 años.",))
        servicio = ConversationService(llm=llm, connection=_FakeConn())

        primero = await servicio.handle_prompt("Háblame de Programación Web")
        assert "2 años" in primero
        assert llm.calls[0]["prompt"] == "Háblame de Programación Web"
        assert llm.calls[0]["history"] == []

        segundo = await servicio.handle_prompt("¿Y cuánto dura?")
        assert "2 años" in segundo
        assert llm.calls[1]["prompt"] == "¿Y cuánto dura sobre Programación Web?"
        assert [m["role"] for m in llm.calls[1]["history"]] == ["user", "assistant"]

    asyncio.run(run())


# --------------------------------------------------------------------------- #
# Entidad activa
# --------------------------------------------------------------------------- #
def test_cambio_de_tema_limpia_entidad():
    """Tras «Programación Web», preguntar por Enfermería no arrastra la anterior."""
    sesion = SessionMemory()
    sesion.observe("Háblame de Programación Web", "Programación Web dura 2 años.")
    assert sesion.active_entity == "Programación Web"

    # La pregunta nueva nombra otra carrera: se reemplaza, no se contamina.
    assert sesion.resolve("¿Y Enfermería?") == "¿Y Enfermería?"
    sesion.observe("¿Y Enfermería?", "Enfermería se estudia en la UNEV.")
    assert sesion.active_entity == "Enfermería"

    resuelta = sesion.resolve("¿Cuánto dura?")
    assert "Enfermería" in resuelta
    assert "Programación" not in resuelta


def test_sin_entidad_comportamiento_actual():
    """«¿Y cuánto dura?» como primera pregunta se comporta como hoy."""
    sesion = SessionMemory()
    assert sesion.resolve("¿Y cuánto dura?") == "¿Y cuánto dura?"
    assert route_local_skill("¿Y cuánto dura?") is None

    # Ni con turnos previos que no nombran carrera: sin entidad, no se inventa.
    sesion.observe("Cuéntame un chiste", "¿Por qué el estudiante cruzó la calle?")
    assert sesion.active_entity is None
    assert sesion.resolve("¿Y cuánto dura?") == "¿Y cuánto dura?"


def test_pregunta_institucional_no_se_expande():
    """«¿Los títulos son válidos?» habla de la institución, no de la carrera."""
    from skills.router import route_query

    sesion = SessionMemory()
    sesion.observe("Háblame de Programación Web", "dura 2 años.")
    pregunta = "¿Los títulos son válidos?"
    assert sesion.resolve(pregunta) == pregunta
    assert route_query(pregunta).topic == "unev.aprobacion"


def test_expansion_con_entidad_dentro_no_dobla_entidad():
    """«¿Y cuánto dura Programación Web?» ya tiene sujeto: no se expande."""
    sesion = SessionMemory()
    sesion.observe("Háblame de Programación Web", "dura 2 años.")
    pregunta = "¿Y cuánto dura Programación Web?"
    assert sesion.resolve(pregunta) == pregunta


# --------------------------------------------------------------------------- #
# Expiración y reset
# --------------------------------------------------------------------------- #
def test_expiracion_por_inactividad():
    """Pasado el TTL sin actividad, el visitante siguiente empieza limpio.

    El reloj es inyectado: el test adelanta el tiempo, no lo duerme.
    """
    reloj = [1000.0]
    sesion = SessionMemory(now=lambda: reloj[0], ttl_seconds=180)
    sesion.observe("Háblame de Programación Web", "Programación Web dura 2 años.")
    assert sesion.active_entity == "Programación Web"

    # Aún dentro del TTL: la memoria sigue viva.
    reloj[0] += 179
    assert sesion.resolve("¿Y cuánto dura?") == "¿Y cuánto dura sobre Programación Web?"

    # 2 segundos después del TTL: todo descartado.
    reloj[0] += 2
    assert sesion.active_entity is None
    assert sesion.resolve("¿Y cuánto dura?") == "¿Y cuánto dura?"
    assert sesion.history() == []
    assert sesion.turn_count == 0


def test_reset_explicito():
    """El reset borra entidad e historial (operador con visitante nuevo)."""
    sesion = SessionMemory()
    sesion.observe("Háblame de Programación Web", "Programación Web dura 2 años.")
    sesion.observe("¿Y cuánto dura?", "Dura 2 años.")
    assert sesion.turn_count == 2

    sesion.reset()

    assert sesion.active_entity is None
    assert sesion.history() == []
    assert sesion.turn_count == 0
    assert sesion.resolve("¿Y cuánto dura?") == "¿Y cuánto dura?"


def test_memoria_no_es_por_socket():
    """Dos servicios (dos "conexiones") ven la misma conversación del kiosco.

    Guardarraíl contra el error de diseño más tentador: aislar por socket
    rompería el modelo (hay un único ConversationService que difunde a todos
    los clientes) y una reconexión perdería el hilo a mitad de charla.
    """
    async def run():
        conn = _FakeConn()
        llm_primero = RecordingLLM(("Programación Web dura 2 años.",))
        s1 = ConversationService(llm=llm_primero, connection=conn)
        await s1.handle_prompt("Háblame de Programación Web")

        # "Reconexión": un servicio nuevo (misma sesión compartida).
        llm_segundo = RecordingLLM(("Dura 2 años.",))
        s2 = ConversationService(llm=llm_segundo, connection=conn)
        await s2.handle_prompt("¿Y cuánto dura?")

        assert llm_segundo.calls[0]["prompt"] == "¿Y cuánto dura sobre Programación Web?"
        assert llm_segundo.calls[0]["history"]  # el turno previo llegó al nuevo servicio

    asyncio.run(run())


# --------------------------------------------------------------------------- #
# Historial acotado y coste
# --------------------------------------------------------------------------- #
def test_historial_acotado_a_n_turnos():
    """Con 10 turnos, sólo van los últimos N (3 por defecto) al prompt."""
    sesion = SessionMemory()
    for i in range(10):
        sesion.observe(f"Pregunta {i} sobre Programación Web", f"Respuesta {i}")

    historial = sesion.history()
    assert len(historial) == 6  # 3 turnos × 2 mensajes
    assert historial[-2]["content"] == "Pregunta 9 sobre Programación Web"
    assert historial[0]["content"] == "Pregunta 7 sobre Programación Web"
    assert sesion.turn_count == 3


def test_coste_del_historial():
    """El historial no revierte la poda de WAVE-05.

    Con N=3 y recortes de 120/300 chars, el historial aporta ~1.260 chars y el
    prompt completo (contexto máximo + historial + pregunta) sigue muy por
    debajo del total previo a la WAVE-05 (18.439 chars).
    """
    sesion = SessionMemory()
    respuesta = "El Técnico Universitario en Programación Web tiene una duración de 2 años. " * 6
    for _ in range(6):
        sesion.observe("Háblame de Programación Web", respuesta)
    historial = sesion.history()

    paquete = PromptPackage(
        user_input="¿Y cuánto dura sobre Programación Web?",
        system_prompt=SYSTEM,
        university_context="x" * MAX_CONTEXT_CHARS,
    )
    sistema = "\n\n".join(
        part["content"] for part in paquete.system_messages() if part.get("content")
    )
    total = len(sistema) + sum(len(m["content"]) for m in historial) + 200
    assert total < PROMPT_TOTAL_PRE_WAVE05, (
        f"prompt con historial ({total} chars) >= línea base pre-WAVE-05 "
        f"({PROMPT_TOTAL_PRE_WAVE05})"
    )

    chars_historial = sum(len(m["content"]) for m in historial)
    assert chars_historial <= MAX_CONTEXT_CHARS
    # El peor caso esperado: 3 turnos × (120 + 300) chars de recorte.
    assert chars_historial <= 3 * (120 + 300)


# --------------------------------------------------------------------------- #
# Retrocompatibilidad y rollback
# --------------------------------------------------------------------------- #
def test_firmas_retrocompatibles(monkeypatch):
    """Los seis símbolos del hallazgo A siguen llamables sin el historial.

    Si se quita el default, `FakeLLM` de `tests/test_app_services.py` y los
    llamadores existentes se rompen.
    """
    # _build_messages por posición, como tests/test_metrics.py
    mensajes = lb._build_messages("Hola", SYSTEM, CONTEXTO)
    assert [m["role"] for m in mensajes] == ["system", "user"]
    # Con historial vacío la salida es idéntica a sin historial.
    assert mensajes == lb._build_messages("Hola", SYSTEM, CONTEXTO, None, None)

    # iter_reply_tokens sin historial (backend local_only: cero red)
    monkeypatch.setattr(lb, "_candidate_backends", lambda primary: ["local_only"])
    tokens = list(lb.iter_reply_tokens("Hola", SYSTEM, CONTEXTO, None))
    assert tokens and all(isinstance(t, str) for t in tokens)

    # Las firmas nuevas declaran el default vacío.
    for fn in (
        lb._build_messages,
        lb.iter_reply_tokens,
        lb.generate_reply,
        lb.stream_llm_response,
        LLMService.stream,
    ):
        parametro = inspect.signature(fn).parameters.get("history")
        assert parametro is not None and parametro.default is None, fn


def test_rollback_holoGRAM_SESSION_MEMORY_0(monkeypatch):
    """Con `HOLOGRAM_SESSION_MEMORY=0`, cada turno vuelve a ser el primero."""
    monkeypatch.setenv("HOLOGRAM_SESSION_MEMORY", "0")
    reset_session()
    sesion = get_session()

    sesion.observe("Háblame de Programación Web", "Programación Web dura 2 años.")
    assert sesion.active_entity is None
    assert sesion.history() == []
    assert sesion.resolve("¿Y cuánto dura?") == "¿Y cuánto dura?"
