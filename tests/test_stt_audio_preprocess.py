"""Preprocesado de audio STT (local + nube): DC, normalización, padding, WAV."""

import wave
from pathlib import Path

import numpy as np

import stt.listener as listener


def _sine(sr: int, seconds: float, freq: float = 220.0, amp: float = 0.05) -> np.ndarray:
    t = np.arange(int(sr * seconds), dtype=np.float32) / sr
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def test_preprocess_removes_dc_and_boosts_quiet_speech():
    wl = listener.WhisperListener()
    wl.sample_rate = 16000
    wl.pad_seconds = 0.0
    wl.highpass_hz = 0.0  # aislar normalización
    wl.normalize_peak = 0.85
    wl.max_boost = 20.0
    wl._last_noise_floor = 0.0

    quiet = _sine(16000, 0.5, amp=0.02) + 0.1  # DC offset + bajo nivel
    out = wl._preprocess_for_stt(quiet)
    assert out.size == quiet.size
    assert abs(float(np.mean(out))) < 0.02  # DC casi eliminado
    peak = float(np.max(np.abs(out)))
    # 0.02 * max_boost(20) → 0.40 (tope de boost); debe subir respecto al original
    assert peak > 0.3
    assert peak <= 1.0
    assert peak > float(np.max(np.abs(quiet - np.mean(quiet))))


def test_preprocess_pads_edges():
    wl = listener.WhisperListener()
    wl.sample_rate = 16000
    wl.pad_seconds = 0.1
    wl.highpass_hz = 80.0
    audio = _sine(16000, 0.3, amp=0.3)
    out = wl._preprocess_for_stt(audio)
    pad = int(16000 * 0.1)
    assert out.size == audio.size + 2 * pad
    # Bordes en silencio (padding)
    assert float(np.max(np.abs(out[:pad]))) < 1e-6
    assert float(np.max(np.abs(out[-pad:]))) < 1e-6


def test_audio_to_wav_is_pcm16_mono_16k(tmp_path, monkeypatch):
    wl = listener.WhisperListener()
    wl.sample_rate = 16000
    wl.pad_seconds = 0.05
    audio = _sine(16000, 0.4, amp=0.1)

    # Forzar temp dir del proceso (NamedTemporaryFile usa /tmp; validamos formato).
    path = wl._audio_to_wav_path(audio)
    try:
        assert path.exists()
        with wave.open(str(path), "rb") as wf:
            assert wf.getnchannels() == 1
            assert wf.getsampwidth() == 2
            assert wf.getframerate() == 16000
            frames = wf.readframes(wf.getnframes())
            assert len(frames) > 1000
    finally:
        path.unlink(missing_ok=True)


def test_highpass_attenuates_dc_step():
    wl = listener.WhisperListener()
    wl.sample_rate = 16000
    # Escalón de DC: el HP debe empujar la media hacia 0 con el tiempo
    x = np.ones(16000, dtype=np.float32)
    y = wl._highpass(x, 80.0)
    assert abs(float(y[-1])) < abs(float(y[10])) or abs(float(np.mean(y))) < 0.5


def test_local_transcribe_still_gets_spanish_kwargs(monkeypatch):
    """Regresión: preprocess no rompe la ruta local de transcribe_file."""
    wl = listener.WhisperListener()
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
    wav = Path(__file__).resolve().parent / "_tmp_stt_pre.wav"
    # Escribir un wav real vía el pipeline
    audio = _sine(16000, 0.3, amp=0.2)
    real = wl._audio_to_wav_path(audio)
    try:
        text = wl.transcribe_file(real)
        assert "hola" in text.lower()
        assert captured.get("language") == "es"
        assert captured.get("vad_filter") is True
        assert "speech_pad_ms" in (captured.get("vad_parameters") or {})
    finally:
        real.unlink(missing_ok=True)
        wav.unlink(missing_ok=True)
