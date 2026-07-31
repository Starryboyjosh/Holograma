"""WAVE-03 — una línea de métrica por turno, en las dos rutas.

El sistema no dejaba rastro de lo que costaba un turno: ni el tamaño del
contexto, ni cuántos backends se intentaron, ni cuánto tardó la primera palabra.
Sin eso, las metas de las WAVEs 04/05 (contexto ≤ 2.500 chars, router ≥ 9/10)
serían afirmaciones sin criterio de aceptación.

Lo que se blinda acá, además de que la línea exista:

* que sea **una sola** por turno y con el **mismo formato** en voz y en web —
  la divergencia entre las dos rutas es el defecto de fondo del plan;
* que no lleve claves, ni el prompt, ni el contexto completo. Una WAVE de
  logging es exactamente donde se filtra un secreto por accidente.

Sin red y sin llamadas a APIs de pago: todo backend está monkeypatcheado.
"""

import asyncio
import json
import sys
import types

from test_app_services import RecordingConnection  # doble ya existente

import llm_backend as lb
import metrics as mx
from app.services.conversation import ConversationService
from app.services.llm import LLMService

PROMPT = "¿Cuánto dura Programación Web?"
# Contexto de juguete: reconocible dentro de la línea si alguna vez se colara.
CONTEXTO = "CONTEXTO-INSTITUCIONAL-" + "x" * 500
SYSTEM = "Eres el asistente de la UNEV."


def _lineas(capsys):
    """Sólo las líneas de métrica de lo impreso hasta ahora.

    Van por **stderr** a propósito (ver el docstring de `metrics`): stdout es el
    log humano del kiosco y el canal del sidecar.
    """
    salida = capsys.readouterr().err
    return [
        linea for linea in salida.splitlines() if linea.startswith(mx.PREFIX)
    ]


def _payload(linea):
    """El JSON de una línea de métrica."""
    return json.loads(linea[len(mx.PREFIX) :].strip())


def _ruta_voz(monkeypatch, *, chunks=("La carrera dura 2 años.",), backends=("openrouter",)):
    """Prepara la ruta síncrona con backends falsos y devuelve el drenador."""
    monkeypatch.setattr(lb, "get_selected_backend", lambda: backends[0])
    monkeypatch.setattr(lb, "_candidate_backends", lambda primary: list(backends))

    def fake_tokens(provider, messages):
        yield from chunks

    monkeypatch.setattr(lb, "_iter_openai_compatible_tokens", fake_tokens)

    def drenar(prompt=PROMPT, **kwargs):
        return list(
            lb.iter_reply_tokens(prompt, SYSTEM, CONTEXTO, None, **kwargs)
        )

    return drenar


def _ruta_web(monkeypatch, *, chunks=("La carrera dura 2 años.",)):
    """Prepara la ruta async con un backend falso; devuelve el turno completo."""
    # `stream_llm_response` importa `call` de forma indirecta a través del
    # servicio de cámara; el doble evita arrastrar la CLI entera.
    fake_call = types.ModuleType("call")
    fake_call._last_camera_analysis = None
    fake_call._build_camera_context = lambda analysis: ""
    monkeypatch.setitem(sys.modules, "call", fake_call)

    monkeypatch.setattr(lb, "get_selected_backend", lambda: "openrouter")
    monkeypatch.setattr(lb, "_candidate_backends", lambda primary: ["openrouter"])

    async def fake_stream(backend, messages):
        for trozo in chunks:
            yield trozo

    monkeypatch.setattr(lb, "_stream_backend_response", fake_stream)

    async def turno():
        conn = RecordingConnection()
        # `LLMService()` sin doble usa la ruta real: el turno entra por
        # `ConversationService` y sale por `stream_llm_response`.
        servicio = ConversationService(llm=LLMService(), connection=conn)
        await servicio.handle_prompt(PROMPT)
        return conn

    return turno


# --------------------------------------------------------------------------- #
# Una línea por turno, en las dos rutas
# --------------------------------------------------------------------------- #
def test_metrica_emitida_una_vez_por_turno_ruta_web(monkeypatch, capsys):
    """Un turno por `ConversationService` deja exactamente una línea."""
    turno = _ruta_web(monkeypatch)

    conn = asyncio.run(turno())

    lineas = _lineas(capsys)
    assert len(lineas) == 1, f"se esperaba 1 métrica, hubo {len(lineas)}: {lineas}"
    assert _payload(lineas[0])["route"] == "web"
    # El turno además tiene que seguir funcionando: la métrica no lo altera.
    assert any(m.get("type") == "text_chunk" for m in conn.messages)


def test_metrica_emitida_una_vez_por_turno_ruta_voz(monkeypatch, capsys):
    """Ídem por la ruta síncrona, y con varios tokens en el mismo turno."""
    drenar = _ruta_voz(monkeypatch, chunks=("La carrera ", "dura ", "2 años."))

    assert "".join(drenar()) == "La carrera dura 2 años."

    lineas = _lineas(capsys)
    assert len(lineas) == 1, f"se esperaba 1 métrica, hubo {len(lineas)}: {lineas}"
    assert _payload(lineas[0])["route"] == "voice"


# --------------------------------------------------------------------------- #
# Contenido de la línea
# --------------------------------------------------------------------------- #
def test_metrica_incluye_los_campos_obligatorios(monkeypatch, capsys):
    """Los diez campos del plan, con valores coherentes con el turno."""
    drenar = _ruta_voz(monkeypatch)

    drenar(event_mode="expo")

    datos = _payload(_lineas(capsys)[0])

    obligatorios = {
        "context_chars",
        "prompt_chars",
        "estimated_input_tokens",
        "local_skill_hit",
        "provider",
        "model",
        "time_to_first_token_ms",
        "time_to_first_clause_ms",
        "fallback_count",
        "route",
        "event_mode",
    }
    faltantes = obligatorios - set(datos)
    assert not faltantes, f"faltan campos en la métrica: {sorted(faltantes)}"

    assert datos["context_chars"] == len(CONTEXTO)
    assert datos["prompt_chars"] > datos["context_chars"]
    # Divisor documentado de la auditoría: 3,5 chars/token. Es una estimación.
    assert datos["estimated_input_tokens"] == round(
        datos["prompt_chars"] / mx.CHARS_PER_TOKEN
    )
    assert datos["provider"] == "openrouter"
    assert datos["event_mode"] == "expo"
    assert datos["fallback_count"] == 0
    # "¿Cuánto dura Programación Web?" la cubre el router local.
    assert datos["local_skill_hit"] is True
    # Los dos hitos de latencia existen aunque el turno haya sido instantáneo.
    assert datos["time_to_first_token_ms"] is not None
    assert datos["time_to_first_clause_ms"] is not None


def test_metrica_no_contiene_secretos(monkeypatch, capsys):
    """Con claves en el entorno, ninguna aparece en la línea.

    Se fuerza el peor caso: una clave metida donde la métrica *sí* mira
    (`LLM_MODEL`, que acaba en el campo `model`). Sin la redacción compartida
    con `main.py`, esa clave saldría impresa en el log del kiosco.
    """
    clave = "gsk_" + "A" * 40
    monkeypatch.setenv("GROQ_API_KEY", clave)
    monkeypatch.setenv("OPENROUTER_API_KEY", "clave-sin-prefijo-conocido-12345")
    monkeypatch.setenv("LLM_MODEL", f"modelo-con-{clave}-pegada")

    drenar = _ruta_voz(monkeypatch)
    drenar()

    linea = _lineas(capsys)[0]
    assert clave not in linea
    assert "clave-sin-prefijo-conocido-12345" not in linea
    assert "REDACTED" in linea, "la clave debía quedar enmascarada, no desaparecer"


def test_metrica_no_contiene_el_prompt_completo(monkeypatch, capsys):
    """Sólo longitudes: ni el contexto ni la pregunta viajan en el log."""
    drenar = _ruta_voz(monkeypatch)

    drenar()

    linea = _lineas(capsys)[0]
    assert CONTEXTO not in linea
    assert "CONTEXTO-INSTITUCIONAL" not in linea
    assert PROMPT not in linea
    assert "La carrera dura 2 años." not in linea
    # Una línea de 18 KB por turno es justo lo que hay que evitar.
    assert len(linea) < 500, f"línea demasiado larga ({len(linea)} chars)"


# --------------------------------------------------------------------------- #
# Fallback y rollback
# --------------------------------------------------------------------------- #
def test_fallback_count_refleja_los_intentos(monkeypatch, capsys):
    """Dos backends caídos y uno bueno → `fallback_count == 2`."""
    monkeypatch.setattr(lb, "get_selected_backend", lambda: "openrouter")
    monkeypatch.setattr(
        lb, "_candidate_backends", lambda primary: ["openrouter", "groq", "openai"]
    )

    def fake_tokens(provider, messages):
        if provider != "openai":
            raise RuntimeError(f"{provider} caído")
        yield "Respuesta del tercero."

    monkeypatch.setattr(lb, "_iter_openai_compatible_tokens", fake_tokens)

    texto = "".join(lb.iter_reply_tokens(PROMPT, SYSTEM, CONTEXTO))

    assert texto == "Respuesta del tercero."
    datos = _payload(_lineas(capsys)[0])
    assert datos["fallback_count"] == 2
    assert datos["provider"] == "openai", "debe registrar el backend que respondió"


def test_flag_desactiva_las_metricas(monkeypatch, capsys):
    """`HOLOGRAM_METRICS=0` silencia todo (rollback inmediato).

    Se comprueban los dos lados en el mismo turno: apagado no imprime nada y
    encendido sí. Sin la segunda mitad, el test pasaría también sin la WAVE
    —donde no hay métricas, no imprimir nada es gratis— y no probaría el flag.
    """
    drenar = _ruta_voz(monkeypatch)

    monkeypatch.setenv("HOLOGRAM_METRICS", "0")
    assert "".join(drenar()) == "La carrera dura 2 años."
    assert _lineas(capsys) == []

    monkeypatch.setenv("HOLOGRAM_METRICS", "1")
    drenar()
    assert len(_lineas(capsys)) == 1
