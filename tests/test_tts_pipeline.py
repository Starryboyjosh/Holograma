"""Pipeline de TTS en streaming: la síntesis debe solaparse con el audio.

Piper tarda cientos de ms en sintetizar. Si eso ocurre entre frase y frase, se
oye un silencio en mitad de la respuesta. Estos tests fijan que la cláusula N+1
se sintetiza mientras suena la N, y que el orden de reproducción se respeta.
"""

import threading
import time

import pytest

import call


@pytest.fixture
def tts_probe(monkeypatch):
    """Sustituye Piper y la reproducción por dobles instrumentados."""

    class Probe:
        def __init__(self):
            self.synth_seconds = 0.05
            self.play_seconds = 0.08
            self.events = []           # (tipo, texto, instante)
            self.played = []           # textos en orden de reproducción
            self.concurrent = False    # ¿hubo síntesis durante una reproducción?
            self._playing = threading.Event()
            self._lock = threading.Lock()

        def synth(self, text):
            if self._playing.is_set():
                self.concurrent = True
            time.sleep(self.synth_seconds)
            with self._lock:
                self.events.append(("synth", text, time.monotonic()))
            return _FakeWav(text)

        def play(self, path):
            self._playing.set()
            with self._lock:
                self.events.append(("play", str(path), time.monotonic()))
                self.played.append(str(path))
            time.sleep(self.play_seconds)
            self._playing.clear()
            return True

    class _FakeWav:
        """Sustituto de Path que no toca el disco."""

        def __init__(self, text):
            self.text = text

        def unlink(self, missing_ok=False):
            return None

        def __str__(self):
            return self.text

    probe = Probe()
    monkeypatch.setenv("TTS_BACKEND", "piper")
    monkeypatch.setenv("HOLOGRAM_QUIET", "1")
    monkeypatch.setattr(call, "_piper_available", lambda: True)
    monkeypatch.setattr(call, "_piper_synth_to_wav", probe.synth)
    monkeypatch.setattr(call, "play_wav_file", probe.play)
    monkeypatch.setattr(call.hologram, "set_state", lambda *a, **k: None)
    monkeypatch.setattr(call, "_hologram_paused", False)
    return probe


CLAUSES = [
    "Hola, bienvenido. ",
    "Soy el asistente de la UNEV. ",
    "Puedo hablarte de carreras. ",
    "Tambien de admisiones. ",
]


def test_synthesis_overlaps_playback(tts_probe):
    """El corazón del arreglo: sintetizar mientras suena la frase anterior."""
    call.speak_streaming_from_llm(iter(CLAUSES))
    assert tts_probe.concurrent is True


def test_no_dead_gap_between_clauses(tts_probe):
    """Sin pipeline había un hueco = tiempo de síntesis entre cada frase."""
    call.speak_streaming_from_llm(iter(CLAUSES))
    plays = [t for kind, _, t in tts_probe.events if kind == "play"]
    assert len(plays) >= 2
    gaps = [
        plays[i + 1] - (plays[i] + tts_probe.play_seconds)
        for i in range(len(plays) - 1)
    ]
    # Holgura generosa para no depender del planificador del SO.
    assert max(gaps) < tts_probe.synth_seconds * 0.6


def test_playback_order_is_preserved(tts_probe):
    call.speak_streaming_from_llm(iter(CLAUSES))
    joined = " ".join(tts_probe.played)
    assert joined.index("bienvenido") < joined.index("UNEV")
    assert joined.index("UNEV") < joined.index("carreras")


def test_returns_full_text(tts_probe):
    result = call.speak_streaming_from_llm(iter(CLAUSES))
    assert "bienvenido" in result
    assert "admisiones" in result


def test_all_text_is_spoken_including_remainder(tts_probe):
    """La última cláusula sin puntuación final no se puede perder."""
    call.speak_streaming_from_llm(iter(["Hola. ", "Sin punto final"]))
    joined = " ".join(tts_probe.played)
    assert "Sin punto final" in joined


def test_waits_for_audio_before_returning(tts_probe):
    """Devolver antes de que acabe el audio dejaría al turno siguiente pisarlo."""
    tts_probe.play_seconds = 0.15
    start = time.monotonic()
    call.speak_streaming_from_llm(iter(CLAUSES))
    elapsed = time.monotonic() - start
    plays = [t for kind, _, t in tts_probe.events if kind == "play"]
    assert elapsed >= len(plays) * tts_probe.play_seconds * 0.9


def test_speak_lock_is_released(tts_probe):
    call.speak_streaming_from_llm(iter(CLAUSES))
    assert call.speak_lock.acquire(blocking=False) is True
    call.speak_lock.release()


def test_on_text_receives_every_token(tts_probe):
    seen = []
    call.speak_streaming_from_llm(iter(CLAUSES), on_text=seen.append)
    assert "".join(seen) == "".join(CLAUSES)


def test_on_speaking_fires_once_at_first_audio(tts_probe):
    calls = {"n": 0}

    def mark():
        calls["n"] += 1

    call.speak_streaming_from_llm(iter(CLAUSES), on_speaking=mark)
    assert calls["n"] == 1


def test_on_text_failure_does_not_break_the_turn(tts_probe):
    def boom(_token):
        raise RuntimeError("frontend caido")

    result = call.speak_streaming_from_llm(iter(CLAUSES), on_text=boom)
    assert "bienvenido" in result
    assert tts_probe.played


def test_synthesis_failure_falls_back_to_os_voice(tts_probe, monkeypatch):
    """Si Piper falla en una cláusula, esa frase la dice la voz del sistema."""
    spoken_os = []
    monkeypatch.setattr(call, "_piper_synth_to_wav", lambda text: None)
    monkeypatch.setattr(call, "_speak_chunk_os", lambda text: spoken_os.append(text))
    call.speak_streaming_from_llm(iter(CLAUSES))
    assert spoken_os
    assert "bienvenido" in " ".join(spoken_os)


def test_playback_crash_does_not_hang_the_turn(tts_probe, monkeypatch):
    """Si el hilo de audio muriera, `wav_q` se llenaría y el join colgaría."""

    def boom(_path):
        raise RuntimeError("dispositivo de audio ocupado")

    monkeypatch.setattr(call, "play_wav_file", boom)
    finished = threading.Event()

    def run():
        call.speak_streaming_from_llm(iter(CLAUSES))
        finished.set()

    threading.Thread(target=run, daemon=True).start()
    assert finished.wait(timeout=10), "el turno se colgó tras fallar la reproducción"


def test_synthesis_crash_does_not_hang_the_turn(tts_probe, monkeypatch):
    def boom(_text):
        raise RuntimeError("piper murió")

    spoken_os = []
    monkeypatch.setattr(call, "_piper_synth_to_wav", boom)
    monkeypatch.setattr(call, "_speak_chunk_os", lambda t: spoken_os.append(t))
    finished = threading.Event()

    def run():
        call.speak_streaming_from_llm(iter(CLAUSES))
        finished.set()

    threading.Thread(target=run, daemon=True).start()
    assert finished.wait(timeout=10), "el turno se colgó tras fallar la síntesis"
    # El texto sigue saliendo por la voz del sistema.
    assert spoken_os


def test_empty_stream_falls_back_to_an_apology(tts_probe):
    """Sin tokens no hay cláusulas, así que entra el fallback de una pasada.

    `_postprocess_reply("")` devuelve la disculpa estándar; el kiosko debe
    decirla en voz alta en vez de quedarse mudo delante del visitante.
    """
    result = call.speak_streaming_from_llm(iter([]))
    assert "no pude generar una respuesta" in result
    assert tts_probe.played  # se locutó, no silencio
