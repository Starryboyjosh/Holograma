"""WAVE-01 — la cadena de fallback no puede dejar el turno vacío.

Cubre dos defectos que dejaban al visitante sin respuesta:

* ``stream_llm_response()`` retornaba tras un stream vacío (HTTP 200 sin un solo
  token) en vez de probar el siguiente backend, mientras que la ruta de voz
  (``iter_reply_tokens``) sí lo hacía. Rutas distintas, semánticas distintas.
* ``resolve_model()`` derramaba ``LLM_MODEL`` —que es la variable *específica* de
  OpenRouter— a los demás proveedores de la cadena, que recibían un id que su
  API no conoce y agotaban su timeout sin poder responder.

Sin red y sin llamadas a APIs de pago: todo backend está monkeypatcheado.
"""

import asyncio
import sys
import types

import llm_backend as lb
import provider_config as pc

PROVIDER_DEFAULTS = {pid: p.default_model for pid, p in pc.PROVIDERS.items()}


def _inject_fake_call(monkeypatch):
    """Evita el import perezoso real de ``call`` (efectos globales: chdir, Qt…)."""
    fake_call = types.ModuleType("call")
    fake_call._last_camera_analysis = None
    fake_call._build_camera_context = lambda analysis: ""
    monkeypatch.setitem(sys.modules, "call", fake_call)


def _fake_streams(monkeypatch, por_backend, intentos):
    """Instala un ``_stream_backend_response`` que sirve tokens de un dict.

    ``por_backend`` mapea backend → lista de tokens (lista vacía = stream vacío)
    o una excepción a lanzar. ``intentos`` acumula el orden real de intentos.
    """

    async def fake_stream(backend, messages):
        intentos.append(backend)
        guion = por_backend[backend]
        if isinstance(guion, BaseException):
            raise guion
        for token in guion:
            yield token

    monkeypatch.setattr(lb, "_stream_backend_response", fake_stream)


def _collect(prompt="¿cuánto cuesta la carrera?"):
    async def run():
        return [chunk async for chunk in lb.stream_llm_response(prompt)]

    return asyncio.run(run())


# --------------------------------------------------------------------------- #
# stream_llm_response(): un stream vacío no es una respuesta
# --------------------------------------------------------------------------- #
def test_stream_vacio_cae_al_siguiente_backend(monkeypatch):
    """Backend 1 responde en blanco → se prueba el 2, y su texto llega entero."""
    _inject_fake_call(monkeypatch)
    monkeypatch.setattr(lb, "get_selected_backend", lambda: "openrouter")
    monkeypatch.setattr(lb, "_candidate_backends", lambda primary: ["openrouter", "groq"])

    intentos: list[str] = []
    _fake_streams(monkeypatch, {"openrouter": [], "groq": ["La ", "matrícula"]}, intentos)

    assert _collect() == ["La ", "matrícula"]
    assert intentos == ["openrouter", "groq"], "no se intentó el segundo backend"


def test_stream_vacio_en_todos_los_backends_devuelve_respuesta_local(monkeypatch):
    """Agotada la cadena en blanco, el turno se cierra con la skill local."""
    _inject_fake_call(monkeypatch)
    monkeypatch.setattr(lb, "get_selected_backend", lambda: "openrouter")
    monkeypatch.setattr(lb, "_candidate_backends", lambda primary: ["openrouter", "groq"])
    monkeypatch.setattr(lb, "_local_only_reply", lambda prompt: "RESPUESTA_LOCAL")

    intentos: list[str] = []
    _fake_streams(monkeypatch, {"openrouter": [], "groq": []}, intentos)

    assert _collect() == ["RESPUESTA_LOCAL"], "el turno quedó vacío"
    assert intentos == ["openrouter", "groq"]


def test_texto_parcial_no_reintenta_otro_backend(monkeypatch):
    """Si ya se emitió texto y luego falla, se cierra el turno: no se mezcla.

    Reintentar con otro backend pegaría dos respuestas distintas en la misma
    frase. Este comportamiento ya existía y la WAVE no lo cambia.
    """
    _inject_fake_call(monkeypatch)
    monkeypatch.setattr(lb, "get_selected_backend", lambda: "openrouter")
    monkeypatch.setattr(lb, "_candidate_backends", lambda primary: ["openrouter", "groq"])

    intentos: list[str] = []

    async def fake_stream(backend, messages):
        intentos.append(backend)
        if backend == "openrouter":
            yield "La matrícula "
            raise RuntimeError("conexión cortada a mitad del stream")
        yield "OTRA RESPUESTA"

    monkeypatch.setattr(lb, "_stream_backend_response", fake_stream)

    assert _collect() == ["La matrícula "]
    assert intentos == ["openrouter"], "no debe reintentar tras texto parcial"


def test_stream_vacio_registra_advertencia(monkeypatch, capsys):
    """El aviso nombra el backend y NO depende de LLM_LOG_COT.

    Con el volcado de CoT apagado (que es como corre el kiosco), un stream vacío
    seguía siendo invisible en el log: no había forma de saber por qué el
    visitante se quedó sin respuesta.
    """
    monkeypatch.setenv("LLM_LOG_COT", "0")
    _inject_fake_call(monkeypatch)
    monkeypatch.setattr(lb, "get_selected_backend", lambda: "openrouter")
    monkeypatch.setattr(lb, "_candidate_backends", lambda primary: ["openrouter", "groq"])

    intentos: list[str] = []
    _fake_streams(monkeypatch, {"openrouter": [], "groq": ["ok"]}, intentos)

    _collect()

    salida = capsys.readouterr().out
    assert "openrouter" in salida
    assert "vacío" in salida.lower()
    assert "groq" not in salida, "groq sí produjo texto: no debe avisar por él"


# --------------------------------------------------------------------------- #
# resolve_model(): LLM_MODEL no se derrama a proveedores ajenos
# --------------------------------------------------------------------------- #
def test_resolve_model_no_filtra_generico_a_otro_proveedor():
    """Un id con namespace no puede heredarlo un proveedor que no lo usa.

    Caso vivo: ``LLM_MODEL=nvidia/nemotron-3-nano-30b-a3b:free`` (el modelo de
    OpenRouter) llegaba a Groq, cuya API no conoce ese id. Ahora Groq cae a su
    modelo por defecto y sigue siendo un respaldo real.
    """
    env = {"LLM_MODEL": "nvidia/nemotron-3-nano-30b-a3b:free"}

    assert pc.resolve_model("openrouter", env) == "nvidia/nemotron-3-nano-30b-a3b:free"
    assert pc.resolve_model("groq", env) == PROVIDER_DEFAULTS["groq"]
    assert pc.resolve_model("openai", env) == PROVIDER_DEFAULTS["openai"]
    # NVIDIA sí usa ids con namespace: para él la herencia sigue siendo válida.
    assert pc.resolve_model("nvidia", env) == "nvidia/nemotron-3-nano-30b-a3b:free"
    # Y al revés: un id sin barra no debe llegar a un proveedor que sí exige uno.
    assert pc.resolve_model("nvidia", {"LLM_MODEL": "gpt-4o"}) == PROVIDER_DEFAULTS["nvidia"]


def test_resolve_model_respeta_variable_especifica():
    """El override por proveedor manda sobre el filtro de forma.

    Quien fija ``GROQ_MODEL`` a mano sabe lo que hace; el filtro sólo protege la
    herencia implícita de ``LLM_MODEL``.
    """
    env = {
        "LLM_MODEL": "nvidia/nemotron-3-nano-30b-a3b:free",
        "GROQ_MODEL": "llama-3.1-8b-instant",
        "OPENAI_MODEL": "gpt-4o",
    }

    assert pc.resolve_model("groq", env) == "llama-3.1-8b-instant"
    assert pc.resolve_model("openai", env) == "gpt-4o"
