"""Tests del gate de disponibilidad web y su integración con el stream.

El caso que más importa: **modelo local sin internet**. Ahí el LLM sigue
respondiendo, así que sin gate intentaría navegar y solo conseguiría timeouts.
"""

import pytest

from app.tools import availability, orchestrator, schema


@pytest.fixture(autouse=True)
def clean_cache():
    availability.reset_cache()
    yield
    availability.reset_cache()


# --- Sondeos ---


def test_internet_reachable_true_when_any_host_answers(monkeypatch):
    monkeypatch.setattr(availability, "_tcp_reachable", lambda h, p, t: h == "8.8.8.8")
    assert availability.internet_reachable() is True


def test_internet_reachable_false_when_none_answer(monkeypatch):
    monkeypatch.setattr(availability, "_tcp_reachable", lambda h, p, t: False)
    assert availability.internet_reachable() is False


def test_lightpanda_reachable_parses_cdp_url(monkeypatch):
    monkeypatch.setenv("LIGHTPANDA_CDP_URL", "ws://lightpanda:9333")
    seen = {}

    def fake(host, port, timeout):
        seen["host"], seen["port"] = host, port
        return True

    monkeypatch.setattr(availability, "_tcp_reachable", fake)
    assert availability.lightpanda_reachable() is True
    assert seen == {"host": "lightpanda", "port": 9333}


def test_connectivity_hosts_are_configurable(monkeypatch):
    monkeypatch.setenv("HOLOGRAM_CONNECTIVITY_HOSTS", "10.0.0.1:53, 10.0.0.2:443")
    assert availability._connectivity_hosts() == [("10.0.0.1", 53), ("10.0.0.2", 443)]


# --- Gate ---


def test_unavailable_when_lightpanda_is_down(monkeypatch):
    monkeypatch.setattr(availability, "lightpanda_reachable", lambda: False)
    monkeypatch.setattr(availability, "internet_reachable", lambda: True)
    ok, reason = availability.web_tools_available()
    assert ok is False
    assert "Lightpanda" in reason


def test_unavailable_when_offline(monkeypatch):
    monkeypatch.setattr(availability, "lightpanda_reachable", lambda: True)
    monkeypatch.setattr(availability, "internet_reachable", lambda: False)
    ok, reason = availability.web_tools_available()
    assert ok is False
    assert reason == "sin conexión a internet"


def test_available_when_both_reachable(monkeypatch):
    monkeypatch.setattr(availability, "lightpanda_reachable", lambda: True)
    monkeypatch.setattr(availability, "internet_reachable", lambda: True)
    assert availability.web_tools_available() == (True, "ok")


def test_off_mode_short_circuits_before_probing(monkeypatch):
    monkeypatch.setenv("HOLOGRAM_WEB_TOOLS", "off")

    def explode():
        raise AssertionError("no debe sondear la red en modo off")

    monkeypatch.setattr(availability, "lightpanda_reachable", explode)
    ok, reason = availability.web_tools_available()
    assert ok is False
    assert "off" in reason


def test_result_is_cached(monkeypatch):
    calls = {"n": 0}

    def counted():
        calls["n"] += 1
        return True

    monkeypatch.setattr(availability, "lightpanda_reachable", counted)
    monkeypatch.setattr(availability, "internet_reachable", lambda: True)
    availability.web_tools_available()
    availability.web_tools_available()
    assert calls["n"] == 1


# --- Pre-filtro del modo auto ---


@pytest.mark.parametrize(
    "prompt",
    [
        "¿qué noticias hay hoy?",
        "Lee https://unev.edu.hn/admisiones",
        "¿cuál es el precio del dólar?",
        "busca en internet la fecha del examen",
        "mira este enlace",
    ],
)
def test_prompt_suggests_web_detects_realtime_intent(prompt):
    assert orchestrator.prompt_suggests_web(prompt) is True


@pytest.mark.parametrize(
    "prompt",
    [
        "¿qué carreras ofrece la UNEV?",
        "hola, ¿cómo estás?",
        "explícame qué es la ingeniería en sistemas",
    ],
)
def test_prompt_without_web_intent(prompt):
    assert orchestrator.prompt_suggests_web(prompt) is False


def test_auto_mode_skips_probe_for_local_questions(monkeypatch):
    monkeypatch.setenv("HOLOGRAM_WEB_TOOLS", "auto")

    def explode():
        raise AssertionError("no debe sondear si el prompt no pide web")

    monkeypatch.setattr(availability, "lightpanda_reachable", explode)
    offer, reason = orchestrator.should_offer_web_tools("¿qué carreras hay?")
    assert offer is False
    assert "no requiere" in reason


def test_always_mode_offers_even_for_local_questions(monkeypatch):
    monkeypatch.setenv("HOLOGRAM_WEB_TOOLS", "always")
    monkeypatch.setattr(availability, "lightpanda_reachable", lambda: True)
    monkeypatch.setattr(availability, "internet_reachable", lambda: True)
    offer, _ = orchestrator.should_offer_web_tools("¿qué carreras hay?")
    assert offer is True


# --- Integración con el stream (el caso local+offline) ---


def test_offline_injects_prohibition_block(monkeypatch):
    """Modelo local sin internet: se le prohíbe prometer una consulta web."""
    import llm_backend as lb

    monkeypatch.setenv("HOLOGRAM_WEB_TOOLS", "auto")
    monkeypatch.setattr(availability, "lightpanda_reachable", lambda: True)
    monkeypatch.setattr(availability, "internet_reachable", lambda: False)

    block = lb._web_context_block("¿qué noticias hay hoy?", "sys", "unev", None)
    assert block is not None
    assert block["role"] == "system"
    assert "No tienes acceso a internet" in block["content"]


def test_offline_stays_silent_for_non_web_questions(monkeypatch):
    """Sin internet pero pregunta local: no se menciona la falta de conexión."""
    import llm_backend as lb

    monkeypatch.setenv("HOLOGRAM_WEB_TOOLS", "auto")
    monkeypatch.setattr(availability, "lightpanda_reachable", lambda: False)
    monkeypatch.setattr(availability, "internet_reachable", lambda: False)

    assert lb._web_context_block("¿qué carreras ofrece la UNEV?", "s", "u", None) is None


def test_web_context_is_injected_before_user_message(monkeypatch):
    import llm_backend as lb

    monkeypatch.setattr(
        orchestrator, "should_offer_web_tools", lambda p: (True, "ok")
    )
    monkeypatch.setattr(
        orchestrator, "gather_web_context", lambda *a, **k: "TEXTO DE LA WEB"
    )
    block = lb._web_context_block("noticias de hoy", "sys", "unev", None)
    assert "TEXTO DE LA WEB" in block["content"]


def test_no_block_when_model_declines_to_browse(monkeypatch):
    import llm_backend as lb

    monkeypatch.setattr(orchestrator, "should_offer_web_tools", lambda p: (True, "ok"))
    monkeypatch.setattr(orchestrator, "gather_web_context", lambda *a, **k: None)
    assert lb._web_context_block("noticias de hoy", "sys", "unev", None) is None


def test_tool_phase_failure_does_not_break_the_turn(monkeypatch):
    """Si la fase de herramientas revienta, el turno sigue sin contexto web."""
    import llm_backend as lb

    monkeypatch.setattr(orchestrator, "should_offer_web_tools", lambda p: (True, "ok"))

    def boom(*a, **k):
        raise RuntimeError("proveedor caído")

    monkeypatch.setattr(orchestrator, "gather_web_context", boom)
    assert lb._web_context_block("noticias de hoy", "sys", "unev", None) is None


def test_gather_web_context_survives_provider_error(monkeypatch):
    def boom(backend, messages, tools):
        raise RuntimeError("sin API key")

    monkeypatch.setattr(orchestrator, "chat_with_tools", boom)
    assert orchestrator.gather_web_context("x", "s", "u", backend="groq") is None


def test_tool_phase_temperature_defaults_to_zero(monkeypatch):
    """La decisión de navegar es clasificación, no redacción.

    Con la 0.6 del turno conversacional, un modelo local de 3B llamaba a la
    herramienta solo 2 de cada 3 veces ante el mismo prompt.
    """
    import llm_backend as lb

    monkeypatch.delenv("HOLOGRAM_TOOL_TEMPERATURE", raising=False)
    assert lb._tool_phase_temperature() == 0.0


def test_tool_phase_temperature_is_configurable(monkeypatch):
    import llm_backend as lb

    monkeypatch.setenv("HOLOGRAM_TOOL_TEMPERATURE", "0.3")
    assert lb._tool_phase_temperature() == 0.3


def test_no_web_instruction_is_explicit():
    """El texto debe prohibir, no solo informar."""
    assert "NO afirmes que vas a consultar" in schema.NO_WEB_SYSTEM_INSTRUCTION
    assert "Nunca inventes datos actuales" in schema.NO_WEB_SYSTEM_INSTRUCTION
