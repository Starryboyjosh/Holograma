"""Tests de la integración de llm_backend con el contrato de proveedor.

No hacen llamadas de red reales: se mockean las sondas de Ollama y se verifican
los mensajes accionables de "Probar conexión".
"""

import llm_backend as lb


def test_get_selected_backend_delegates_to_contract(monkeypatch):
    monkeypatch.delenv("LLM_BACKEND", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-old")
    assert lb.get_selected_backend() == "ollama"


def test_invalid_legacy_backend_is_dropped(monkeypatch):
    monkeypatch.setenv("LLM_BACKEND", "banana")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    assert lb.get_selected_backend() == "openai"


def test_backend_status_uses_resolved_model(monkeypatch):
    monkeypatch.delenv("LLM_BACKEND", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    monkeypatch.setenv("LLM_MODEL", "gpt-4o")
    status = lb.get_backend_status()
    assert "OpenAI" in status and "gpt-4o" in status


def test_probe_local_only_always_ok():
    result = lb.probe_backend("local_only")
    assert result["ok"] is True


def test_probe_unknown_provider():
    assert lb.probe_backend("does-not-exist")["ok"] is False


def test_probe_ollama_server_down(monkeypatch):
    monkeypatch.setattr(lb, "_ollama_server_available", lambda: False)
    result = lb.probe_backend("ollama")
    assert result["ok"] is False
    assert "no responde" in result["message"].lower()


def test_list_ollama_models_sorted_unique(monkeypatch):
    monkeypatch.setattr(
        lb,
        "_ollama_tags",
        lambda timeout=1.5: {
            "models": [
                {"name": "llama3.2:3b"},
                {"name": "gemma3:1b"},
                {"name": "gemma3:1b"},
                {"name": ""},
            ]
        },
    )
    result = lb.list_ollama_models()
    assert result["ok"] is True
    assert result["models"] == ["gemma3:1b", "llama3.2:3b"]
    assert "2" in result["message"]


def test_list_ollama_models_server_down(monkeypatch):
    def boom(timeout=1.5):
        raise OSError("connection refused")

    monkeypatch.setattr(lb, "_ollama_tags", boom)
    result = lb.list_ollama_models()
    assert result["ok"] is False
    assert result["models"] == []
    assert "no responde" in result["message"].lower()


def test_list_ollama_models_empty_install(monkeypatch):
    monkeypatch.setattr(lb, "_ollama_tags", lambda timeout=1.5: {"models": []})
    result = lb.list_ollama_models()
    assert result["ok"] is True
    assert result["models"] == []
    assert "no hay modelos" in result["message"].lower()


def test_probe_ollama_model_missing(monkeypatch):
    monkeypatch.setattr(lb, "_ollama_server_available", lambda: True)
    monkeypatch.setattr(lb, "_ollama_model_available", lambda m=None: False)
    result = lb.probe_backend("ollama", model="gemma3:1b")
    assert result["ok"] is False
    assert "ollama pull" in result["message"]


def test_probe_cloud_missing_key_is_actionable(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = lb.probe_backend("openai", model="gpt-4o-mini")
    assert result["ok"] is False
    assert "api key" in result["message"].lower()


def test_probe_custom_openai_requires_base_url(monkeypatch):
    monkeypatch.delenv("OPENAI_COMPAT_BASE_URL", raising=False)
    result = lb.probe_backend("custom_openai", api_key="k", model="m")
    assert result["ok"] is False
    assert "url base" in result["message"].lower()


def test_humanize_probe_error_maps_common_cases():
    assert "inválida" in lb._humanize_probe_error("openai", Exception("Error 401 unauthorized"))
    assert "no existe" in lb._humanize_probe_error("openai", Exception("model_not_found"))
    assert "conectar" in lb._humanize_probe_error("openai", Exception("Connection refused"))


def test_humanize_probe_error_redacts_leaked_key_in_generic_branch(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-proj-supersecret0123456789")
    # un error inesperado (no mapeado) que arrastra la key cruda del proveedor
    msg = lb._humanize_probe_error("openai", Exception("boom sk-proj-supersecret0123456789"))
    assert "supersecret" not in msg
    assert "***REDACTED***" in msg
