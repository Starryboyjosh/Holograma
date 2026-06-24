"""Tests de la lógica de autorización por token (auth_token). Puras."""

import auth_token as at


def test_generate_token_is_random_and_urlsafe():
    a, b = at.generate_token(), at.generate_token()
    assert a != b
    assert len(a) >= 32
    # url-safe: sin caracteres problemáticos
    assert all(c.isalnum() or c in "-_" for c in a)


def test_auth_disabled_when_no_expected_token():
    # sin token configurado, todo pasa (comportamiento histórico)
    assert at.request_authorized("/api/config", "POST", None, None) is True
    assert at.request_authorized("/api/config", "POST", None, "") is True


def test_reads_never_require_token():
    assert at.is_path_privileged("/api/config", "GET") is False
    assert at.request_authorized("/api/config", "GET", None, "secret") is True


def test_privileged_write_requires_matching_token():
    assert at.request_authorized("/api/config", "POST", None, "secret") is False
    assert at.request_authorized("/api/config", "POST", "wrong", "secret") is False
    assert at.request_authorized("/api/config", "POST", "secret", "secret") is True


def test_non_privileged_path_passes_even_with_token():
    assert at.request_authorized("/api/providers", "POST", None, "secret") is True


def test_privileged_prefixes_are_covered():
    for prefix in ("/api/config", "/api/unev-content", "/api/camera", "/api/train/image"):
        assert at.is_path_privileged(prefix, "POST") is True


def test_tokens_match_is_constant_time_safe():
    assert at.tokens_match("abc", "abc") is True
    assert at.tokens_match("abc", "abcd") is False
    assert at.tokens_match(None, "x") is False
    assert at.tokens_match("anything", None) is True  # auth apagada
