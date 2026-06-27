"""Caché con TTL de `_ollama_ready()`.

Antes, cada mensaje sondeaba /api/tags 2–4 veces (dos sondas bloqueantes por
invocación, e invocada varias veces por mensaje), congelando el event loop bajo
carga. Ahora la readiness se memoiza durante OLLAMA_READY_TTL_SECONDS y una sola
sonda combinada responde "servidor arriba + modelo instalado".
"""

import llm_backend as lb


def _reset_cache():
    lb._OLLAMA_READY_CACHE["value"] = None
    lb._OLLAMA_READY_CACHE["expires"] = 0.0


def _make_tags_counter(monkeypatch):
    """Sustituye `_ollama_tags` por uno que cuenta llamadas y reporta el modelo listo."""
    calls = {"n": 0}

    def fake_tags(timeout=1.5):
        calls["n"] += 1
        return {"models": [{"name": lb._ollama_model_name()}]}

    monkeypatch.setattr(lb, "_ollama_tags", fake_tags)
    return calls


def test_ready_is_cached_within_ttl(monkeypatch):
    _reset_cache()
    calls = _make_tags_counter(monkeypatch)
    try:
        assert lb._ollama_ready() is True
        assert lb._ollama_ready() is True
        assert lb._ollama_ready() is True
        assert calls["n"] == 1, "dentro del TTL la readiness debe sondear una sola vez"
    finally:
        _reset_cache()


def test_ready_refreshes_after_ttl_expiry(monkeypatch):
    _reset_cache()
    calls = _make_tags_counter(monkeypatch)
    try:
        assert lb._ollama_ready() is True
        assert calls["n"] == 1
        # Simula que el TTL ya venció sin esperar tiempo real.
        lb._OLLAMA_READY_CACHE["expires"] = 0.0
        assert lb._ollama_ready() is True
        assert calls["n"] == 2, "tras expirar el TTL debe volver a sondear"
    finally:
        _reset_cache()


def test_force_bypasses_cache(monkeypatch):
    _reset_cache()
    calls = _make_tags_counter(monkeypatch)
    try:
        assert lb._ollama_ready() is True
        assert calls["n"] == 1
        assert lb._ollama_ready(force=True) is True
        assert calls["n"] == 2, "force=True debe ignorar la caché vigente"
    finally:
        _reset_cache()


def test_probe_failure_returns_false(monkeypatch):
    _reset_cache()

    def boom(timeout=1.5):
        raise OSError("connection refused")

    monkeypatch.setattr(lb, "_ollama_tags", boom)
    try:
        assert lb._ollama_ready() is False
    finally:
        _reset_cache()


def test_model_absent_returns_false(monkeypatch):
    """El servidor responde, pero el modelo configurado no está instalado."""
    _reset_cache()

    def other_model(timeout=1.5):
        return {"models": [{"name": "un-modelo-distinto:latest"}]}

    monkeypatch.setattr(lb, "_ollama_tags", other_model)
    try:
        assert lb._ollama_ready() is False
    finally:
        _reset_cache()
