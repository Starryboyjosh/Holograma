"""Hotwords STT: caché por mtime y tamaño acotado (no reparsear JSON cada turno)."""

from pathlib import Path

import stt.listener as listener


def test_hotwords_cached_on_second_call(monkeypatch):
    # Forzar reconstrucción limpia.
    listener._HOTWORDS_CACHE["signature"] = None
    listener._HOTWORDS_CACHE["value"] = None

    wl = listener.WhisperListener()
    first = wl._load_db_hotwords()
    sig_after = listener._HOTWORDS_CACHE["signature"]
    assert sig_after is not None

    # Segunda llamada no debe re-leer si la firma no cambia.
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
    listener._HOTWORDS_CACHE["signature"] = None
    listener._HOTWORDS_CACHE["value"] = None
    wl = listener.WhisperListener()
    raw = wl._load_db_hotwords() or ""
    # Antes se generaban ~70k términos (~cientos de KB). Ahora está acotado.
    assert len(raw) < 20_000

