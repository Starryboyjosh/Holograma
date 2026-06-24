"""Tests del contrato de proveedor/modelo (provider_config).

Cubren la lógica que antes estaba dispersa y era contradictoria, incluida la
regresión del bug: elegir Ollama seguía usando la nube si quedaba una key vieja.
Son puros: no tocan red ni el entorno del proceso.
"""

import provider_config as pc


def test_explicit_ollama_ignores_stale_cloud_key():
    """Regresión: proveedor explícito 'ollama' nunca cae a la nube por una key vieja."""
    env = {"LLM_PROVIDER": "ollama", "OPENROUTER_API_KEY": "sk-old", "OPENAI_API_KEY": "sk-x"}
    assert pc.select_backend(env) == "ollama"


def test_explicit_cloud_provider_is_authoritative_even_without_key():
    """Si el operador elige openai, no se cambia en silencio a otro proveedor."""
    env = {"LLM_PROVIDER": "openai", "OPENROUTER_API_KEY": "sk-router"}
    assert pc.select_backend(env) == "openai"


def test_local_alias_maps_to_ollama():
    assert pc.select_backend({"LLM_PROVIDER": "local"}) == "ollama"


def test_anthropic_alias_maps_to_claude_native():
    assert pc.select_backend({"LLM_PROVIDER": "anthropic"}) == "claude_native"


def test_autodetect_order_prefers_openrouter():
    env = {"OPENAI_API_KEY": "a", "OPENROUTER_API_KEY": "b", "NVIDIA_API_KEY": "c"}
    assert pc.select_backend(env) == "openrouter"


def test_autodetect_falls_through_to_next_key():
    assert pc.select_backend({"NVIDIA_API_KEY": "c"}) == "nvidia"


def test_no_keys_no_ollama_is_local_only():
    assert pc.select_backend({}, ollama_ready=lambda: False) == "local_only"


def test_no_keys_with_ollama_ready_is_ollama():
    assert pc.select_backend({}, ollama_ready=lambda: True) == "ollama"


def test_legacy_llm_backend_override_wins():
    env = {"LLM_BACKEND": "nvidia", "LLM_PROVIDER": "openai", "OPENAI_API_KEY": "x"}
    assert pc.select_backend(env) == "nvidia"


def test_legacy_auto_is_ignored():
    env = {"LLM_BACKEND": "auto", "LLM_PROVIDER": "openai"}
    assert pc.select_backend(env) == "openai"


# --- resolución de modelo -------------------------------------------------


def test_model_uses_llm_model_for_cloud_providers():
    """El modelo de la interfaz (LLM_MODEL) aplica también a OpenAI/NVIDIA."""
    assert pc.resolve_model("openai", {"LLM_MODEL": "gpt-4o"}) == "gpt-4o"
    assert pc.resolve_model("nvidia", {"LLM_MODEL": "meta/llama"}) == "meta/llama"


def test_provider_specific_model_overrides_generic():
    env = {"LLM_MODEL": "gpt-4o", "OPENAI_MODEL": "gpt-4o-mini"}
    assert pc.resolve_model("openai", env) == "gpt-4o-mini"


def test_model_defaults_when_unset():
    assert pc.resolve_model("openai", {}) == pc.PROVIDERS["openai"].default_model


def test_ollama_never_inherits_generic_cloud_model():
    """Ollama no debe usar un modelo de la nube si solo está LLM_MODEL."""
    assert pc.resolve_model("ollama", {"LLM_MODEL": "gpt-4o"}) == pc.PROVIDERS["ollama"].default_model
    assert pc.resolve_model("ollama", {"OLLAMA_MODEL": "qwen3:8b"}) == "qwen3:8b"


# --- key / base url -------------------------------------------------------


def test_resolve_api_key_reads_provider_field():
    assert pc.resolve_api_key("openai", {"OPENAI_API_KEY": "sk-1"}) == "sk-1"
    assert pc.resolve_api_key("ollama", {"OPENAI_API_KEY": "sk-1"}) == ""


def test_resolve_base_url_override_and_default():
    assert pc.resolve_base_url("nvidia", {}) == pc.PROVIDERS["nvidia"].default_base_url
    assert pc.resolve_base_url("nvidia", {"NVIDIA_BASE_URL": "http://x/v1/"}) == "http://x/v1"


def test_custom_openai_needs_explicit_base_url():
    assert pc.resolve_base_url("custom_openai", {}) == ""
    assert pc.resolve_base_url("custom_openai", {"OPENAI_COMPAT_BASE_URL": "http://h:8080/v1"}) == "http://h:8080/v1"


def test_custom_openai_resolves_key_and_model_from_compat_env():
    """El proveedor 'custom_openai' lee key/modelo de las variables OPENAI_COMPAT_*.

    Son las que la interfaz de Ajustes persiste vía /api/config para un endpoint
    propio compatible con OpenAI.
    """
    env = {
        "OPENAI_COMPAT_API_KEY": "sk-local",
        "OPENAI_COMPAT_MODEL": "my-served-model",
        "OPENAI_COMPAT_BASE_URL": "http://127.0.0.1:8080/v1",
    }
    assert pc.resolve_api_key("custom_openai", env) == "sk-local"
    assert pc.resolve_model("custom_openai", env) == "my-served-model"
    # Sin OPENAI_COMPAT_MODEL, el modelo genérico (LLM_MODEL) sí aplica al endpoint.
    assert pc.resolve_model("custom_openai", {"LLM_MODEL": "x"}) == "x"


def test_custom_openai_public_info_flags_base_url_requirement():
    info = {p["id"]: p for p in pc.all_providers_public_info(
        {"OPENAI_COMPAT_BASE_URL": "http://h:8080/v1", "OPENAI_COMPAT_API_KEY": "sk-x"}
    )}
    assert info["custom_openai"]["needs_base_url"] is True
    assert info["custom_openai"]["base_url"] == "http://h:8080/v1"
    assert info["custom_openai"]["key_configured"] is True


# --- metadata pública (sin secretos) -------------------------------------


def test_public_info_reports_key_configured_without_leaking():
    info = {p["id"]: p for p in pc.all_providers_public_info({"OPENAI_API_KEY": "sk-secret"})}
    assert info["openai"]["key_configured"] is True
    assert info["openrouter"]["key_configured"] is False
    # nunca se expone el valor de la key
    assert "sk-secret" not in str(info)


def test_keyless_providers_report_configured_true():
    info = {p["id"]: p for p in pc.all_providers_public_info({})}
    assert info["ollama"]["key_configured"] is True
    assert info["local_only"]["requires_key"] is False
