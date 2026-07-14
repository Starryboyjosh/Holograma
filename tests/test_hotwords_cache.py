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
    assert "español" in prompt.lower() or "espanol" in prompt.lower()
    assert len(prompt) > 40


def test_stt_prompt_env_override(monkeypatch):
    monkeypatch.setenv("WHISPER_PROMPT", "solo este prompt de prueba")
    wl = _fresh_listener()
    assert wl._build_stt_prompt() == "solo este prompt de prueba"


def test_resolve_stt_language_defaults_to_spanish(monkeypatch):
    monkeypatch.delenv("WHISPER_LANGUAGE", raising=False)
    assert listener._resolve_stt_language(None) == "es"
    assert listener._resolve_stt_language("") == "es"
    monkeypatch.setenv("WHISPER_LANGUAGE", "auto")
    assert listener._resolve_stt_language(None) == "es"
    monkeypatch.setenv("WHISPER_LANGUAGE", "es-HN")
    assert listener._resolve_stt_language(None) == "es"
    assert listener.WhisperListener().language == "es"


def test_stt_prompt_respects_groq_char_limit():
    """Groq exige prompt ≤896; tildes no deben empujar el conteo del API."""
    wl = _fresh_listener()
    prompt = wl._build_stt_prompt(max_chars=listener._GROQ_STT_PROMPT_MAX)
    assert len(prompt) <= listener._GROQ_STT_PROMPT_MAX
    assert len(prompt.encode("utf-8")) <= listener._GROQ_STT_PROMPT_MAX
    # Truncado forzado también respeta el techo.
    long = "ñ" * 2000 + " UNEV admisión Honduras"
    trimmed = listener._truncate_stt_prompt(long, listener._GROQ_STT_PROMPT_MAX)
    assert len(trimmed) <= listener._GROQ_STT_PROMPT_MAX
    assert len(trimmed.encode("utf-8")) <= listener._GROQ_STT_PROMPT_MAX


def test_local_transcribe_passes_spanish_and_hotwords(monkeypatch):
    """faster-whisper debe recibir language=es, task=transcribe y hotwords."""
    wl = _fresh_listener()
    wl.model_size = "base"
    captured = {}

    class FakeSegments:
        def __iter__(self):
            class Seg:
                text = "hola UNEV"

            yield Seg()

    class FakeModel:
        def transcribe(self, path, **kwargs):
            captured.update(kwargs)
            return FakeSegments(), None

    monkeypatch.setattr(wl, "_load_model", lambda: FakeModel())
    wav = Path(__file__).resolve().parent / "_tmp_local_stt.wav"
    wav.write_bytes(b"RIFF" + b"\x00" * 40)
    try:
        text = wl.transcribe_file(wav)
        assert "hola" in text.lower()
        assert captured.get("language") == "es"
        assert captured.get("task") == "transcribe"
        assert captured.get("multilingual") is False
        assert captured.get("hotwords")
        assert "unev" in captured["hotwords"].lower()
        assert captured.get("initial_prompt")
        assert "español" in captured["initial_prompt"].lower()
    finally:
        wav.unlink(missing_ok=True)


def test_groq_receives_language_and_prompt(monkeypatch):
    """La ruta Groq (config actual) debe inyectar prompt de contexto + español."""
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
        assert captured.get("language") == "es"
        assert "prompt" in captured
        assert "UNEV" in captured["prompt"] or "unev" in captured["prompt"].lower()
        assert "español" in captured["prompt"].lower()
        assert len(captured["prompt"]) <= listener._GROQ_STT_PROMPT_MAX
        assert len(captured["prompt"].encode("utf-8")) <= listener._GROQ_STT_PROMPT_MAX
    finally:
        wav.unlink(missing_ok=True)
