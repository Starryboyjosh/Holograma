"""Tests de las utilidades de seguridad (redacción de secretos + saneo de texto).

Puras: no tocan red ni el entorno del proceso.
"""

import security


def test_redacts_known_api_key_shapes():
    samples = [
        "sk-or-v1-abcdef0123456789abcdef",
        "sk-proj-ABCDEF0123456789ABCDEF",
        "nvapi-0123456789abcdef0123",
        "AIzaSyA0123456789abcdef0123456789",
        "Authorization: Bearer abcdef0123456789.token",
    ]
    for s in samples:
        out = security.redact_secrets(s)
        assert "***REDACTED***" in out
        # ningún fragmento largo del token sobrevive
        assert "0123456789" not in out


def test_redacts_exact_env_value_even_without_known_prefix():
    env = {"OPENAI_API_KEY": "weirdcustomtoken-not-a-known-prefix-999"}
    out = security.redact_secrets("error: clave weirdcustomtoken-not-a-known-prefix-999 inválida", env)
    assert "weirdcustomtoken" not in out
    assert "***REDACTED***" in out


def test_short_env_value_is_not_masked():
    # un valor trivial (<8 chars) no debe enmascararse para no romper texto normal
    env = {"OPENAI_API_KEY": "abc"}
    assert security.redact_secrets("la respuesta es abc", env) == "la respuesta es abc"


def test_redact_accepts_non_str():
    err = ValueError("falló con sk-proj-abcdef0123456789abcdef")
    out = security.redact_secrets(err)
    assert "***REDACTED***" in out
    assert "0123456789" not in out


def test_redact_leaves_normal_text_untouched():
    text = "Bienvenido a la UNEV. El modelo gpt-4o-mini está activo."
    assert security.redact_secrets(text) == text


def test_clamp_truncates_and_strips_controls():
    raw = "hola\x00\x07 mundo​‮"
    out = security.clamp_text(raw, 50)
    assert out == "hola mundo"


def test_clamp_enforces_max_len():
    assert security.clamp_text("x" * 100, 10) == "x" * 10


def test_clamp_keeps_accents_and_newlines():
    text = "Línea uno\nLínea dos — ñ á é"
    assert security.clamp_text(text, 1000) == text


def test_size_constants_are_sane():
    assert security.MAX_PROMPT_CHARS >= 1000
    assert security.MAX_LABEL_CHARS <= security.MAX_PROMPT_CHARS
