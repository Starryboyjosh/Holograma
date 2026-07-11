"""Hotwords STT: caché por mtime, acotado y alineado al contexto UNEV/Honduras."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import stt.listener as listener


def _fresh_listener():
    listener._HOTWORDS_CACHE["signature"] = None
    listener._HOTWORDS_CACHE["value"] = None
    return listener.WhisperListener()


def test_hotwords_cached_on_second_call(monkeypatch):
    wl = _fresh_listener()
    first = wl._load_db_hotwords()
    sig_after = listener._HOTWORDS_CACHE["signature"]
    assert sig_after is not None

    calls = {"n": 0}
    real_read = Path.read_text

    def spy_read(self, *a, **k):
        calls["n"] += 1
        return real_read(self, *a, **k)

    monkeypatch.setattr(Path, "read_text", spy_read)
    second = wl._load_db_hotwords()
    assert second == first
    assert calls["n"] == 0  # hit de caché: sin leer archivos


def test_hotwords_bounded(monkeypatch):
    monkeypatch.setenv("WHISPER_MAX_HOTWORDS", "50")
    wl = _fresh_listener()
    raw = wl._load_db_hotwords() or ""
    # Antes se generaban ~70k términos (~cientos de KB). Ahora está acotado.
    assert len(raw) < 20_000
    # Con tope 50, el string no debe ser enorme.
    assert len(raw.split()) <= 120  # frases multi-palabra


def test_hotwords_include_context_domain():
    """Vocabulario del kiosco + UNEV + Honduras siempre presente."""
    wl = _fresh_listener()
    raw = (wl._load_db_hotwords() or "").lower()
    assert "unev" in raw
    assert "honduras" in raw
    assert "holograma" in raw
    assert "prind" in raw or "diseño" in raw or "diseno" in raw
    # Programas o admisión del contexto institucional
    assert any(
        token in raw
        for token in (
            "admisión",
            "admision",
            "gráfico",
            "grafico",
            "programación",
            "programacion",
            "administración",
            "administracion",
        )
    )


def test_stt_prompt_includes_context():
    wl = _fresh_listener()
    prompt = wl._build_stt_prompt()
    assert "UNEV" in prompt or "unev" in prompt.lower()
    assert "Honduras" in prompt or "honduras" in prompt.lower()
    assert len(prompt) > 40


def test_stt_prompt_env_override(monkeypatch):
    monkeypatch.setenv("WHISPER_PROMPT", "solo este prompt de prueba")
    wl = _fresh_listener()
    assert wl._build_stt_prompt() == "solo este prompt de prueba"


def test_groq_receives_language_and_prompt(monkeypatch):
    """La ruta Groq (config actual) debe inyectar prompt de contexto."""
    wl = _fresh_listener()
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test_fake")

    captured = {}

    class FakeTranscriptions:
        def create(self, **kwargs):
            captured.update(kwargs)

            class R:
                text = "hola unev"

            return R()

    class FakeAudio:
        transcriptions = FakeTranscriptions()

    class FakeClient:
        def __init__(self, api_key=None):
            self.audio = FakeAudio()

    fake_mod = MagicMock()
    fake_mod.Groq = FakeClient
    monkeypatch.setitem(__import__("sys").modules, "groq", fake_mod)

    wav = Path(__file__).resolve().parent / "_tmp_hotwords_test.wav"
    # WAV mínimo 44 bytes header + silencio (no se decodifica aquí)
    wav.write_bytes(b"RIFF" + b"\x00" * 40)
    try:
        text = wl._transcribe_groq(wav)
        assert text == "hola unev"
        assert captured.get("language") in ("es", wl.language)
        assert "prompt" in captured
        assert "UNEV" in captured["prompt"] or "unev" in captured["prompt"].lower()
    finally:
        wav.unlink(missing_ok=True)
