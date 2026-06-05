"""
Speech-to-text listener using Faster-Whisper and sounddevice.

Regla de Oro A: Todas las rutas usan pathlib.Path.
Regla de Oro B: Micrófono con sounddevice (no pyaudio).

Uso básico:
    from stt.listener import WhisperListener
    listener = WhisperListener()
    text = listener.listen_once()
"""

import os
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np


def configure_utf8_stdio():
    """Keep Windows consoles from crashing on non-ASCII output."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")


configure_utf8_stdio()


def _env(name, default=None):
    """Read a non-empty environment variable or return a default."""
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return value.strip()


def _env_float(name, default):
    value = _env(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _env_int(name, default):
    value = _env(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


class WhisperListener:
    """Record from the microphone and transcribe with Faster-Whisper.

    Parameters
    ----------
    model_size : str
        Whisper model size.  Defaults to the ``WHISPER_MODEL`` env var or
        ``"base"`` (fast, ~150 MB).
    language : str
        Language hint for Whisper.  Defaults to ``"es"`` (Spanish).
    sample_rate : int
        Recording sample rate in Hz.
    silence_threshold : float
        RMS amplitude below which audio is considered silence.
    silence_duration : float
        Seconds of continuous silence before the recording stops.
    max_record_seconds : float
        Hard limit on recording length to avoid runaway captures.
    """

    def __init__(
        self,
        model_size=None,
        language=None,
        sample_rate=None,
        silence_threshold=None,
        silence_duration=None,
        max_record_seconds=None,
    ):
        self.model_size = model_size or _env("WHISPER_MODEL", "base")
        self.language = language or _env("WHISPER_LANGUAGE", "es")
        self.sample_rate = sample_rate or _env_int("WHISPER_SAMPLE_RATE", 16000)
        self.silence_threshold = silence_threshold or _env_float(
            "WHISPER_SILENCE_THRESHOLD", 0.01
        )
        self.silence_duration = silence_duration or _env_float(
            "WHISPER_SILENCE_DURATION", 1.5
        )
        self.max_record_seconds = max_record_seconds or _env_float(
            "WHISPER_MAX_RECORD_SECONDS", 15.0
        )

        self._model = None

    # ------------------------------------------------------------------
    # Lazy model loading
    # ------------------------------------------------------------------

    def _load_model(self):
        """Load the Faster-Whisper model on first use."""
        if self._model is not None:
            return self._model

        try:
            from faster_whisper import WhisperModel
        except ImportError as error:
            raise RuntimeError(
                "Falta instalar faster-whisper. "
                "Ejecuta: pip install faster-whisper"
            ) from error

        device = _env("WHISPER_DEVICE", "auto")
        compute_type = _env("WHISPER_COMPUTE_TYPE", "int8")

        print(
            f"[STT] Cargando modelo Whisper '{self.model_size}' "
            f"(device={device}, compute={compute_type})..."
        )

        try:
            self._model = WhisperModel(
                self.model_size,
                device=device,
                compute_type=compute_type,
            )
        except RuntimeError as error:
            error_str = str(error)
            if device != "cpu" and ("cublas" in error_str.lower() or "cuda" in error_str.lower() or "onnxruntime" in error_str.lower()):
                print(
                    f"[STT] AVISO: Error al cargar modelo en '{device}' ({error}). "
                    "Intentando fallback en 'cpu'..."
                )
                self._model = WhisperModel(
                    self.model_size,
                    device="cpu",
                    compute_type="int8",
                )
            else:
                raise

        print("[STT] Modelo Whisper listo.")
        return self._model

    # ------------------------------------------------------------------
    # Audio recording with sounddevice (Regla B)
    # ------------------------------------------------------------------

    def _record_until_silence(self):
        """Record audio from the default microphone until silence is detected.

        Returns a numpy array of shape ``(samples,)`` with float32 values.
        """
        try:
            import sounddevice as sd
        except ImportError as error:
            raise RuntimeError(
                "Falta instalar sounddevice. "
                "Ejecuta: pip install sounddevice"
            ) from error

        chunk_duration = 0.5  # seconds per chunk
        chunk_samples = int(self.sample_rate * chunk_duration)
        max_chunks = int(self.max_record_seconds / chunk_duration)

        recorded_chunks = []
        silent_chunks = 0
        silence_chunks_needed = int(self.silence_duration / chunk_duration)

        print("[STT] Escuchando... (habla y haré una pausa cuando termines)")

        for _ in range(max_chunks):
            try:
                chunk = sd.rec(
                    chunk_samples,
                    samplerate=self.sample_rate,
                    channels=1,
                    dtype="float32",
                )
                sd.wait()
            except Exception as error:
                print(f"[STT] Error grabando audio: {error}")
                break

            recorded_chunks.append(chunk.flatten())

            # Silence detection via RMS
            rms = np.sqrt(np.mean(chunk ** 2))

            if rms < self.silence_threshold:
                silent_chunks += 1
            else:
                silent_chunks = 0

            if silent_chunks >= silence_chunks_needed and len(recorded_chunks) > 2:
                break

        if not recorded_chunks:
            return np.array([], dtype=np.float32)

        return np.concatenate(recorded_chunks)

    def _audio_to_wav_path(self, audio):
        """Write a float32 numpy array to a temporary WAV file.

        Returns a ``pathlib.Path`` pointing to the WAV file (Regla A).
        """
        tmp = tempfile.NamedTemporaryFile(
            suffix=".wav", delete=False, dir=None
        )
        wav_path = Path(tmp.name)  # Regla A: pathlib
        tmp.close()

        # Convert float32 [-1, 1] to int16
        int16_audio = np.clip(audio * 32767, -32768, 32767).astype(np.int16)

        with wave.open(str(wav_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.sample_rate)
            wf.writeframes(int16_audio.tobytes())

        return wav_path

    # ------------------------------------------------------------------
    # Transcription
    # ------------------------------------------------------------------

    def transcribe_file(self, audio_path):
        """Transcribe a WAV file and return the text.

        Parameters
        ----------
        audio_path : str or Path
            Path to the WAV file (Regla A: accepts Path objects).
        """
        model = self._load_model()
        audio_path = Path(audio_path)  # Regla A

        # Prompt inicial para contextualizar el vocabulario de la universidad (mejora transcripción de siglas)
        default_prompt = (
            "UNEV, universidad virtual de Honduras, diseño gráfico, "
            "programación web, administración de empresas, admisión, carreras."
        )
        prompt = _env("WHISPER_PROMPT", default_prompt)

        segments, info = model.transcribe(
            str(audio_path),
            language=self.language,
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
            initial_prompt=prompt,
        )

        text_parts = [segment.text.strip() for segment in segments]
        return " ".join(text_parts).strip()

    def listen_once(self):
        """Record from the microphone and return the transcribed text.

        Returns an empty string if nothing was captured or transcribed.
        """
        audio = self._record_until_silence()

        if audio.size == 0:
            print("[STT] No se capturó audio.")
            return ""

        wav_path = self._audio_to_wav_path(audio)

        try:
            text = self.transcribe_file(wav_path)
        finally:
            try:
                wav_path.unlink()  # Regla A: pathlib for deletion too
            except OSError:
                pass

        if text:
            print(f"[STT] Transcripción: {text}")
        else:
            print("[STT] No se detectó habla.")

        return text

    # ------------------------------------------------------------------
    # Availability check
    # ------------------------------------------------------------------

    @staticmethod
    def is_available():
        """Return True if sounddevice and faster-whisper are importable."""
        try:
            import sounddevice  # noqa: F401
            from faster_whisper import WhisperModel  # noqa: F401
            return True
        except ImportError:
            return False


def get_stt_status():
    """Return a human-readable status string for the STT subsystem."""
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        input_devices = [
            d for d in devices
            if d.get("max_input_channels", 0) > 0
        ]
        mic_status = (
            f"{len(input_devices)} micrófono(s) detectado(s)"
            if input_devices
            else "no se detectaron micrófonos"
        )
    except ImportError:
        return "STT no disponible: falta sounddevice. Ejecuta: pip install sounddevice"
    except Exception as error:
        mic_status = f"error consultando dispositivos: {error}"

    try:
        from faster_whisper import WhisperModel  # noqa: F401
        whisper_status = "faster-whisper instalado"
    except ImportError:
        return (
            "STT no disponible: falta faster-whisper. "
            "Ejecuta: pip install faster-whisper"
        )

    model = _env("WHISPER_MODEL", "base")
    return f"STT activo: modelo Whisper '{model}', {mic_status}, {whisper_status}."
