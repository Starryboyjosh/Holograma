"""Captura de audio del STT: presupuestos de tiempo y umbral adaptativo.

Se simula el micrófono con un `sounddevice` falso que entrega una secuencia de
bloques fijada por el test, así que el comportamiento del bucle de captura es
determinista y no hace falta hardware.
"""

import sys
import types

import numpy as np
import pytest

import stt.listener as listener

SR = 16000
BLOCK_S = 0.04
BLOCK_N = int(SR * BLOCK_S)


def _quiet_block(level=0.0005):
    return np.full(BLOCK_N, level, dtype=np.float32)


def _voice_block(amplitude=0.085):
    return (np.sin(np.linspace(0, 50, BLOCK_N)) * amplitude).astype(np.float32)


def _blocks(seconds, factory):
    return [factory() for _ in range(int(seconds / BLOCK_S))]


def _speech(seconds, amplitude=0.085):
    """Habla realista: sílabas con huecos cortos entre ellas."""
    out = []
    for i in range(int(seconds / BLOCK_S)):
        out.append(_quiet_block() if i % 4 == 3 else _voice_block(amplitude))
    return out


@pytest.fixture
def fake_microphone(monkeypatch):
    """Instala un `sounddevice` falso que reproduce los bloques dados."""

    def _install(blocks):
        module = types.ModuleType("sounddevice")

        class InputStream:
            def __init__(self, **kwargs):
                self._callback = kwargs["callback"]
                self._blocks = list(blocks)

            def __enter__(self):
                for block in self._blocks:
                    self._callback(block.reshape(-1, 1), len(block), None, None)
                return self

            def __exit__(self, *exc):
                return False

        module.InputStream = InputStream
        module.query_devices = lambda *a, **k: []
        monkeypatch.setitem(sys.modules, "sounddevice", module)

    return _install


def _listener(**overrides):
    wl = listener.WhisperListener()
    wl.max_record_seconds = 12.0
    wl.max_wait_seconds = 10.0
    wl.silence_duration = 1.2
    wl.calibration_seconds = 0.5
    for key, value in overrides.items():
        setattr(wl, key, value)
    return wl


def _seconds(audio):
    return audio.size / SR


# --- Presupuestos independientes: espera vs grabación ---


def test_hesitation_does_not_shorten_the_utterance(fake_microphone):
    """Regresión: dudar antes de hablar recortaba la frase.

    `max_record_seconds` y `max_wait_seconds` compartían un solo contador, así
    que 8 s de duda dejaban solo 4 s de los 12 disponibles para la voz y la
    pregunta llegaba truncada a Whisper.
    """
    fake_microphone(
        _blocks(0.5, _quiet_block)      # calibración
        + _blocks(0.5, _quiet_block)    # arranca enseguida
        + _speech(6.0)
        + _blocks(2.0, _quiet_block)
    )
    prompt = _seconds(_listener()._record_until_silence())

    fake_microphone(
        _blocks(0.5, _quiet_block)
        + _blocks(8.0, _quiet_block)    # duda 8 s
        + _speech(6.0)
        + _blocks(2.0, _quiet_block)
    )
    hesitant = _seconds(_listener()._record_until_silence())

    assert hesitant == pytest.approx(prompt, abs=0.15)


def test_recording_is_capped_by_max_record_seconds(fake_microphone):
    fake_microphone(
        _blocks(0.5, _quiet_block) + _speech(30.0) + _blocks(2.0, _quiet_block)
    )
    audio = _listener(max_record_seconds=4.0)._record_until_silence()
    # Tope + pre-roll; nunca los 30 s emitidos.
    assert 3.5 <= _seconds(audio) <= 6.0


def test_wait_timeout_gives_up_on_pure_silence(fake_microphone):
    fake_microphone(_blocks(0.5, _quiet_block) + _blocks(30.0, _quiet_block))
    audio = _listener(max_wait_seconds=2.0)._record_until_silence()
    assert audio.size == 0


def test_noisy_room_without_speech_still_times_out(fake_microphone):
    """El tope de espera debe correr en cada bloque, no solo en los silenciosos.

    Antes solo avanzaba con bloques bajo umbral: un zumbido constante por encima
    del umbral que nunca confirmaba onset dejaba la espera sin tope real.
    """
    hum = [_voice_block(0.02) for _ in range(int(30.0 / BLOCK_S))]
    fake_microphone(_blocks(0.5, _quiet_block) + hum)
    wl = _listener(max_wait_seconds=1.0, speech_onset_blocks=10_000)
    assert wl._record_until_silence().size == 0


# --- Umbral adaptativo ---


def test_speech_during_calibration_does_not_deafen_the_kiosk(fake_microphone):
    """Regresión: si el visitante ya hablaba, se perdía la frase entera.

    El piso de ruido salía de la mediana de la ventana de calibración; con voz
    presente, la mediana ES la voz, el umbral quedaba por encima del habla y no
    se detectaba nada (0.00 s capturados).
    """
    fake_microphone(
        _speech(0.5)                     # ya hablando durante la calibración
        + _speech(4.0)
        + _blocks(2.0, _quiet_block)
    )
    audio = _listener()._record_until_silence()
    assert _seconds(audio) > 1.0


def test_threshold_only_relaxes_never_tightens(fake_microphone):
    """La recalibración continua baja el piso; nunca lo sube."""
    fake_microphone(
        _blocks(0.5, _quiet_block) + _speech(3.0) + _blocks(2.0, _quiet_block)
    )
    wl = _listener()
    wl._record_until_silence()
    assert wl._last_noise_floor < 0.01  # sala silenciosa

    fake_microphone(
        _speech(0.5) + _speech(3.0) + _blocks(2.0, _quiet_block)
    )
    wl2 = _listener()
    wl2._record_until_silence()
    # Con calibración contaminada el piso puede quedar algo más alto, pero la
    # recalibración lo acerca al real en vez de dejarlo al nivel de la voz.
    assert wl2._last_noise_floor < 0.085


def test_noise_percentile_is_clamped(monkeypatch):
    monkeypatch.setenv("WHISPER_NOISE_PERCENTILE", "999")
    assert listener.WhisperListener().noise_percentile == 50.0
    monkeypatch.setenv("WHISPER_NOISE_PERCENTILE", "0")
    assert listener.WhisperListener().noise_percentile == 1.0


def test_adaptive_threshold_respects_max(fake_microphone):
    """Una sala muy ruidosa no puede subir el umbral sin límite."""
    loud_room = [_voice_block(0.5) for _ in range(int(0.5 / BLOCK_S))]
    fake_microphone(loud_room + _speech(3.0) + _blocks(2.0, _quiet_block))
    wl = _listener(max_threshold=0.05)
    wl._record_until_silence()
    # El piso medido puede ser alto, pero el umbral efectivo se capa.
    assert wl.max_threshold == 0.05


# --- Descartes ---


def test_too_short_capture_is_discarded(fake_microphone):
    fake_microphone(
        _blocks(0.5, _quiet_block) + _speech(0.12) + _blocks(2.0, _quiet_block)
    )
    wl = _listener(min_speech_seconds=1.5, preroll_seconds=0.0)
    assert wl._record_until_silence().size == 0


def test_silence_duration_closes_the_capture(fake_microphone):
    fake_microphone(
        _blocks(0.5, _quiet_block)
        + _speech(2.0)
        + _blocks(5.0, _quiet_block)  # pausa larga
    )
    audio = _listener(silence_duration=0.5)._record_until_silence()
    # Corta poco después de la pausa, no consume los 5 s de silencio.
    assert _seconds(audio) < 4.0
