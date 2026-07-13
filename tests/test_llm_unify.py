"""Unificación de la ruta de LLM (Fases 1 y 2 del plan de mejora).

Cubre tres arreglos puros y verificables sin levantar el backend real:

* ``_max_tokens()`` — un único límite de salida configurable (``LLM_MAX_TOKENS``)
  en vez de los números mágicos por proveedor (350 / 450 / 1024 / sin límite).
* ``_postprocess_reply()`` — el filtro anti-inglés ya NO descarta la respuesta
  (síntoma C: "no puedo responder"); solo registra el aviso y la entrega.
* ``stream_llm_response()`` — la selección de backend (que sondea Ollama por HTTP)
  se ejecuta con ``asyncio.to_thread``, fuera del hilo del event loop (síntoma A).
"""

import asyncio
import sys
import threading
import types

import llm_backend as lb


# --------------------------------------------------------------------------- #
# _max_tokens(): límite unificado y configurable
# --------------------------------------------------------------------------- #
def test_max_tokens_default(monkeypatch):
    monkeypatch.delenv("LLM_MAX_TOKENS", raising=False)
    assert lb._max_tokens() == 450


def test_max_tokens_env_override(monkeypatch):
    monkeypatch.setenv("LLM_MAX_TOKENS", "1200")
    assert lb._max_tokens() == 1200


def test_max_tokens_invalid_falls_back(monkeypatch):
    monkeypatch.setenv("LLM_MAX_TOKENS", "no-soy-un-numero")
    assert lb._max_tokens() == 450


def test_max_tokens_non_positive_falls_back(monkeypatch):
    monkeypatch.setenv("LLM_MAX_TOKENS", "0")
    assert lb._max_tokens() == 450


def test_request_timeout_default(monkeypatch):
    monkeypatch.delenv("LLM_REQUEST_TIMEOUT", raising=False)
    assert lb._request_timeout() == 90.0


def test_request_timeout_override(monkeypatch):
    monkeypatch.setenv("LLM_REQUEST_TIMEOUT", "30")
    assert lb._request_timeout() == 30.0


# --------------------------------------------------------------------------- #
# _postprocess_reply(): el inglés ya no se descarta
# --------------------------------------------------------------------------- #
def test_postprocess_keeps_english_response():
    """Una respuesta en inglés debe entregarse, no convertirse en un error."""
    text = "Welcome! How can I help you today? Feel free to ask. I can help."
    assert lb._postprocess_reply(text) == text


def test_postprocess_strips_thinking_block():
    assert lb._postprocess_reply("<think>razonamiento interno</think>Hola") == "Hola"


def test_postprocess_empty_asks_to_retry():
    out = lb._postprocess_reply("    ")
    assert "repetir" in out.lower()


# --------------------------------------------------------------------------- #
# CoT mirror: log en terminal del razonamiento (diagnóstico de atascos)
# --------------------------------------------------------------------------- #
def test_cot_stream_mirror_counts_think_and_answer(capsys, monkeypatch):
    monkeypatch.setenv("LLM_LOG_COT", "1")
    mirror = lb._CotStreamMirror("ollama", "test-model")
    # Etiqueta de apertura partida entre chunks (caso real de streaming).
    mirror.feed("<thi")
    mirror.feed("nk>paso 1")
    mirror.feed("</think>")
    mirror.feed("Hola UNEV")
    mirror.finish()
    assert mirror.think_chars > 0
    assert mirror.answer_chars == len("Hola UNEV")
    out = capsys.readouterr().out
    assert "[CoT]" in out
    assert "Hola UNEV" in out
    assert "stream end" in out


def test_cot_log_disabled_is_silent(capsys, monkeypatch):
    monkeypatch.setenv("LLM_LOG_COT", "0")
    mirror = lb._CotStreamMirror("ollama", "m")
    mirror.feed("<think>secreto</think>ok")
    mirror.finish()
    assert capsys.readouterr().out == ""


# --------------------------------------------------------------------------- #
# stream_llm_response(): selección de backend fuera del event loop
# --------------------------------------------------------------------------- #
def _inject_fake_call(monkeypatch):
    """Evita el import perezoso real de ``call`` (efectos globales: chdir, Qt…)."""
    fake_call = types.ModuleType("call")
    fake_call._last_camera_analysis = None
    fake_call._build_camera_context = lambda analysis: ""
    monkeypatch.setitem(sys.modules, "call", fake_call)


def test_stream_local_only_yields_canned_reply(monkeypatch):
    _inject_fake_call(monkeypatch)
    monkeypatch.setattr(lb, "get_selected_backend", lambda: "local_only")
    monkeypatch.setattr(lb, "_candidate_backends", lambda primary: ["local_only"])
    monkeypatch.setattr(lb, "_local_only_reply", lambda prompt: "RESPUESTA_LOCAL")

    async def collect():
        return [chunk async for chunk in lb.stream_llm_response("hola")]

    chunks = asyncio.run(collect())
    assert chunks == ["RESPUESTA_LOCAL"]


def test_backend_selection_runs_off_event_loop(monkeypatch):
    """`_candidate_backends` debe ejecutarse en un hilo distinto al del loop.

    El loop de ``asyncio.run`` vive en el hilo principal; ``to_thread`` delega a un
    worker del executor. Si la selección corriera en el hilo del loop, el sondeo
    HTTP a Ollama lo bloquearía (síntoma A).
    """
    _inject_fake_call(monkeypatch)
    loop_thread = threading.get_ident()
    seen = {}

    def fake_candidates(primary):
        seen["thread"] = threading.get_ident()
        return ["local_only"]

    monkeypatch.setattr(lb, "get_selected_backend", lambda: "whatever")
    monkeypatch.setattr(lb, "_candidate_backends", fake_candidates)
    monkeypatch.setattr(lb, "_local_only_reply", lambda prompt: "L")

    async def collect():
        return [chunk async for chunk in lb.stream_llm_response("hola")]

    asyncio.run(collect())
    assert seen["thread"] != loop_thread, (
        "la selección de backend debe correr fuera del hilo del event loop"
    )


# --------------------------------------------------------------------------- #
# _candidate_backends(): cadena de fallback (Fase 2)
# --------------------------------------------------------------------------- #
def test_candidate_backends_inserts_cloud_fallback_before_local(monkeypatch):
    """primario -> otros proveedores con key -> ollama (si responde) -> local_only.

    El primario no se duplica aunque también aparezca en la lista de configurados.
    """
    monkeypatch.setattr(lb, "configured_cloud_providers", lambda: ["openrouter", "nvidia"])
    monkeypatch.setattr(lb, "_ollama_ready", lambda *a, **k: True)
    assert lb._candidate_backends("openrouter") == [
        "openrouter",
        "nvidia",
        "ollama",
        "local_only",
    ]


def test_candidate_backends_skips_ollama_when_not_ready(monkeypatch):
    monkeypatch.setattr(lb, "configured_cloud_providers", lambda: ["openai"])
    monkeypatch.setattr(lb, "_ollama_ready", lambda *a, **k: False)
    assert lb._candidate_backends("openai") == ["openai", "local_only"]


def test_candidate_backends_keeps_primary_when_not_in_configured(monkeypatch):
    """Un primario explícito sin key (p. ej. claude_native) sigue siendo el primer intento."""
    monkeypatch.setattr(lb, "configured_cloud_providers", lambda: ["openrouter"])
    monkeypatch.setattr(lb, "_ollama_ready", lambda *a, **k: False)
    assert lb._candidate_backends("claude_native") == [
        "claude_native",
        "openrouter",
        "local_only",
    ]
