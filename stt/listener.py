"""
Speech-to-text listener using Faster-Whisper and sounddevice.

Regla de Oro A: Todas las rutas usan pathlib.Path.
Regla de Oro B: Micrófono con sounddevice (no pyaudio).

Uso básico:
    from stt.listener import WhisperListener
    listener = WhisperListener()
    text = listener.listen_once()
"""

import tempfile
import wave
from pathlib import Path

import numpy as np

from utils import _env, _env_float, _env_int, _is_quiet, configure_utf8_stdio

configure_utf8_stdio()

# Caché de hotwords STT: reconstruir desde data/*.json en cada turnos era ~70 ms
# y generaba decenas de miles de términos. Se invalida si cambia el mtime de las fuentes.
_HOTWORDS_CACHE: dict[str, object] = {"signature": None, "value": None}


def _hotwords_sources_signature(paths) -> str:
    parts: list[str] = []
    for path in paths:
        try:
            st = path.stat()
            parts.append(f"{path.name}:{st.st_mtime_ns}:{st.st_size}")
        except OSError:
            parts.append(f"{path.name}:missing")
    return "|".join(parts)


# Frases que Whisper suele "alucinar" cuando sólo hay silencio, música o ruido.
# Se descartan para que la IA no responda a comandos inexistentes.
_HALLUCINATION_PHRASES = {
    "gracias",
    "gracias.",
    "gracias por ver el video",
    "gracias por ver el video.",
    "¡gracias por ver el video!",
    "subtítulos realizados por la comunidad de amara.org",
    "subtitulos realizados por la comunidad de amara.org",
    "subtítulos por la comunidad de amara.org",
    "¡suscríbete!",
    "suscríbete",
    "más información en www.alimmenta.com",
}


def _looks_like_hallucination(text):
    """Return True if *text* is empty or a known Whisper silence-hallucination."""
    cleaned = text.strip().lower()
    if not cleaned:
        return True
    # Una sola "palabra" muy corta sin contenido real (puntuación, ruido).
    stripped = cleaned.strip(".,!¡¿? ")
    if len(stripped) <= 1:
        return True
    return cleaned in _HALLUCINATION_PHRASES


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
        max_threshold=None,
    ):
        self.model_size = model_size or _env("WHISPER_MODEL", "base")
        self.language = language or _env("WHISPER_LANGUAGE", "es")
        self.sample_rate = sample_rate or _env_int("WHISPER_SAMPLE_RATE", 16000)
        self.silence_threshold = silence_threshold or _env_float(
            "WHISPER_SILENCE_THRESHOLD", 0.02
        )
        self.silence_duration = silence_duration or _env_float(
            "WHISPER_SILENCE_DURATION", 1.2
        )
        self.max_record_seconds = max_record_seconds or _env_float(
            "WHISPER_MAX_RECORD_SECONDS", 12.0
        )
        # Límite máximo para el umbral adaptativo (evita ensordecimiento por ruido/TTS)
        self.max_threshold = max_threshold or _env_float(
            "WHISPER_MAX_THRESHOLD", 0.15
        )
        # Tiempo máximo esperando a que la persona EMPIECE a hablar antes de
        # descartar el intento (evita transcribir silencio puro en bucle).
        self.max_wait_seconds = _env_float("WHISPER_MAX_WAIT_SECONDS", 6.0)
        # Duración mínima de habla útil; por debajo se considera ruido y se ignora.
        self.min_speech_seconds = _env_float("WHISPER_MIN_SPEECH_SECONDS", 0.4)
        # Calibración del ruido ambiente al inicio de cada captura: se mide el RMS
        # del entorno durante unos instantes y el umbral de silencio se eleva por
        # encima de ese piso (umbral adaptativo). Imprescindible en lugares
        # ruidosos, donde un umbral fijo nunca detecta el fin del habla.
        self.calibration_seconds = _env_float("WHISPER_CALIBRATION_SECONDS", 0.4)
        # Factor multiplicativo sobre el ruido ambiente medido. El umbral final es
        # max(silence_threshold, ruido * noise_factor).
        self.noise_factor = _env_float("WHISPER_NOISE_FACTOR", 2.5)

        self._model = None

    # ------------------------------------------------------------------
    # Lazy model loading
    # ------------------------------------------------------------------

    def _load_model(self):
        """Load the Faster-Whisper model on first use."""
        if self.model_size == "whisper-large-v3-turbo":
            return None
        if self._model is not None:
            return self._model

        try:
            from faster_whisper import WhisperModel
        except ImportError as error:
            raise RuntimeError(
                "Falta instalar faster-whisper. "
                "Ejecuta: pip install faster-whisper"
            ) from error

        device = _env("WHISPER_DEVICE", "cpu")
        compute_type = _env("WHISPER_COMPUTE_TYPE", "int8")

        if not _is_quiet():
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
                if not _is_quiet():
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

        if not _is_quiet():
            print("[STT] Modelo Whisper listo.")
        return self._model

    # ------------------------------------------------------------------
    # Audio recording with sounddevice (Regla B)
    # ------------------------------------------------------------------

    def _record_until_silence(self):
        """Record audio from the default microphone until silence is detected.

        Usa un único ``sd.InputStream`` continuo con callback + cola en vez de
        abrir/cerrar el stream por trozos (``sd.rec``/``sd.wait``). Esto elimina
        los huecos muertos entre trozos (que cortaban sílabas) y los *stalls* del
        driver de audio que hacían "trabar" la app. Además calibra el ruido
        ambiente para un umbral adaptativo y conserva un pre-roll para no perder
        la primera sílaba.

        Returns a numpy array of shape ``(samples,)`` with float32 values.
        """
        try:
            import sounddevice as sd
        except ImportError as error:
            raise RuntimeError(
                "Falta instalar sounddevice. "
                "Ejecuta: pip install sounddevice"
            ) from error

        import queue as _queue
        from collections import deque

        block_seconds = 0.05  # bloques de 50 ms: buena resolución sin sobrecarga
        block_samples = int(self.sample_rate * block_seconds)
        silence_blocks_needed = max(1, int(self.silence_duration / block_seconds))
        wait_blocks = max(1, int(self.max_wait_seconds / block_seconds))
        max_blocks = max(1, int(self.max_record_seconds / block_seconds))
        # Pre-roll: ~300 ms previos al inicio del habla que se anteponen a la
        # grabación para no cortar el arranque de la primera palabra.
        preroll_blocks = max(1, int(0.3 / block_seconds))

        audio_q = _queue.Queue()

        def _callback(indata, frames, time_info, status):  # noqa: ARG001
            # El callback corre en el hilo de PortAudio: copiar y encolar es todo
            # lo que se hace aquí para no perder bloques.
            audio_q.put(indata[:, 0].copy())

        recorded = []
        preroll = deque(maxlen=preroll_blocks)
        silent_blocks = 0
        waited_blocks = 0
        speech_started = False
        threshold = self.silence_threshold

        if not _is_quiet():
            print("[STT] Escuchando... (habla y haré una pausa cuando termines)")

        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                blocksize=block_samples,
                callback=_callback,
            ):
                # --- Calibración del ruido ambiente (umbral adaptativo) ---
                calib_blocks = max(1, int(self.calibration_seconds / block_seconds))
                noise_levels = []
                for _ in range(calib_blocks):
                    try:
                        block = audio_q.get(timeout=1.0)
                    except _queue.Empty:
                        break
                    noise_levels.append(float(np.sqrt(np.mean(block ** 2))))
                if noise_levels:
                    noise_floor = float(np.median(noise_levels))
                    threshold = max(
                        self.silence_threshold, noise_floor * self.noise_factor
                    )
                    if self.max_threshold is not None:
                        threshold = min(threshold, self.max_threshold)
                    if not _is_quiet():
                        print(
                            f"[STT] Ruido ambiente={noise_floor:.4f} "
                            f"-> umbral adaptativo={threshold:.4f} (límite={self.max_threshold})"
                        )

                # --- Captura continua ---
                processed = 0
                while processed < max_blocks:
                    try:
                        block = audio_q.get(timeout=self.max_wait_seconds + 1.0)
                    except _queue.Empty:
                        break
                    processed += 1
                    rms = float(np.sqrt(np.mean(block ** 2)))

                    # Fase 1: esperar a que la persona empiece a hablar. Mientras
                    # no haya voz no acumulamos silencio (así no se transcribe
                    # silencio en bucle).
                    if not speech_started:
                        preroll.append(block)
                        if rms >= threshold:
                            speech_started = True
                            recorded.extend(preroll)  # incluir pre-roll
                            preroll.clear()
                        else:
                            waited_blocks += 1
                            if waited_blocks >= wait_blocks:
                                return np.array([], dtype=np.float32)
                        continue

                    # Fase 2: ya hay habla; grabar hasta una pausa sostenida.
                    recorded.append(block)
                    if rms < threshold:
                        silent_blocks += 1
                    else:
                        silent_blocks = 0

                    if silent_blocks >= silence_blocks_needed:
                        break
        except Exception as error:
            if not _is_quiet():
                print(f"[STT] Error grabando audio: {error}")
            return np.array([], dtype=np.float32)

        if not recorded:
            return np.array([], dtype=np.float32)

        audio = np.concatenate(recorded)
        # Descartar capturas demasiado cortas (golpes, ruido, eco) que el modelo
        # tiende a "alucinar" como frases falsas.
        if audio.size < int(self.sample_rate * self.min_speech_seconds):
            return np.array([], dtype=np.float32)

        return audio

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

    def _load_db_hotwords(self):
        """Hotwords desde data/ para Whisper (cacheadas; no releer JSON en cada turno).

        Antes se parseaba ``honduras_info.json`` (~136 KB) en **cada** transcripción
        y se generaban decenas de miles de términos (~70 ms y ruido al modelo).
        Ahora: una sola construcción por cambio de mtime de los ficheros fuente,
        acotada a ``WHISPER_MAX_HOTWORDS`` (default 400) priorizando siglas y
        nombres cortos útiles para UNEV/Honduras.
        """
        import json
        import re

        global _HOTWORDS_CACHE

        data_dir = Path(__file__).resolve().parent.parent / "data"
        vocab_path = data_dir / "open_vocabulary.txt"
        unev_path = data_dir / "unev_info.json"
        honduras_path = data_dir / "honduras_info.json"
        sources = (vocab_path, unev_path, honduras_path)
        signature = _hotwords_sources_signature(sources)
        if (
            _HOTWORDS_CACHE["signature"] == signature
            and _HOTWORDS_CACHE["value"] is not None
        ):
            return _HOTWORDS_CACHE["value"]

        hotwords: set[str] = set()

        # 1. Vocabulario abierto del operador (prioridad alta).
        if vocab_path.exists():
            try:
                for w in re.split(r"[,\n;]+", vocab_path.read_text(encoding="utf-8")):
                    w_clean = w.strip()
                    if w_clean:
                        hotwords.add(w_clean)
            except Exception:
                pass

        def add_acronyms_and_names(text: str) -> None:
            if not isinstance(text, str) or not text:
                return
            for m in re.finditer(r"\b[A-Z]{2,}\b", text):
                hotwords.add(m.group())
            for m in re.finditer(
                r"\b[A-Z][a-záéíóúüñ]+(?:\s+(?:de|del|la|las|y)\s+[A-Z][a-záéíóúüñ]+)*\b",
                text,
            ):
                hotwords.add(m.group())

        def add_dict_keys(mapping: object, *, skip: set[str] | None = None) -> None:
            if not isinstance(mapping, dict):
                return
            skip = skip or set()
            for key in mapping:
                if not isinstance(key, str) or len(key) <= 2 or key in skip:
                    continue
                if key.startswith("¿") or key.endswith("?"):
                    # Preguntas de cultura general: demasiado largas como hotword.
                    continue
                hotwords.add(key.title() if key.islower() else key)

        meta_keys = {
            "name",
            "description",
            "main_claim",
            "approval",
            "address",
            "website",
            "programs",
            "values",
            "governance",
            "infrastructure",
            "academic_model",
            "student_support",
            "admission_requirements",
            "social_projection",
            "virtual_library",
            "international_presence",
            "proceres",
            "vulgarismos",
            "simbolos_patrios",
            "cultura_general",
            "full_name",
        }

        # 2. UNEV: nombres + claves de programas + acrónimos del resumen (no todo el JSON).
        if unev_path.exists():
            try:
                data = json.loads(unev_path.read_text(encoding="utf-8"))
                hotwords.add(str(data.get("name") or "UNEV"))
                full = str(data.get("full_name") or "")
                if full:
                    hotwords.add(full)
                for name in (
                    "Nathalie Cuadrado",
                    "Cesar Arguijo",
                    "Gladys Ferrufino",
                    "Raúl Peña Moreno",
                    "UNEV",
                    "PRIND",
                    "DES",
                    "CES",
                ):
                    hotwords.add(name)
                add_dict_keys(data.get("programs"), skip=meta_keys)
                for field in ("name", "full_name", "main_claim", "approval"):
                    add_acronyms_and_names(str(data.get(field) or ""))
            except Exception:
                pass

        # 3. Honduras: categorías indexadas + lista curada. NO recorrer
        # cultura_general (miles de entradas) ni todo el cuerpo del JSON.
        if honduras_path.exists():
            try:
                data = json.loads(honduras_path.read_text(encoding="utf-8"))
                hotwords.update(
                    [
                        "Garífuna",
                        "Lenca",
                        "Creoles",
                        "Misquito",
                        "Tawahka",
                        "Maya-Chortí",
                        "Nahua",
                        "Tolupan",
                        "Pesh",
                        "PIAH",
                        "baleada",
                        "nacatamal",
                        "pollo chuco",
                        "alcitrón",
                        "sisimite",
                        "Honduras",
                        "Tegucigalpa",
                    ]
                )
                for section in (
                    "programs",
                    "proceres",
                    "vulgarismos",
                    "simbolos_patrios",
                ):
                    add_dict_keys(data.get(section), skip=meta_keys)
                add_acronyms_and_names(str(data.get("main_claim") or ""))
                add_acronyms_and_names(str(data.get("approval") or ""))
            except Exception:
                pass

        stop = {
            "del",
            "las",
            "por",
            "para",
            "con",
            "una",
            "este",
            "esta",
            "como",
            "pero",
            "tipo",
            "especie",
            "dónde",
            "quién",
            "quiénes",
            "cuál",
            "cuáles",
            "cómo",
            "qué",
        }
        cleaned: list[str] = []
        for hw in sorted(hotwords):
            hw_clean = hw.strip(".,!?;:()-\" ")
            if len(hw_clean) > 2 and hw_clean.lower() not in stop:
                cleaned.append(hw_clean)

        # Preferir términos cortos (siglas, nombres) y acotar longitud del string.
        max_n = max(50, _env_int("WHISPER_MAX_HOTWORDS", 400))
        cleaned.sort(key=lambda s: (len(s), s.lower()))
        cleaned = cleaned[:max_n]
        result = " ".join(cleaned) if cleaned else None
        _HOTWORDS_CACHE["signature"] = signature
        _HOTWORDS_CACHE["value"] = result
        return result

    def _transcribe_groq(self, audio_path):
        """Transcribe a WAV file using the Groq API with whisper-large-v3-turbo."""
        api_key = _env("GROQ_API_KEY")
        if not api_key:
            raise ValueError(
                "La clave API de Groq (GROQ_API_KEY) no está configurada. "
                "Por favor, configúrala en los ajustes de STT."
            )

        try:
            from groq import Groq
        except ImportError as error:
            raise RuntimeError(
                "Falta instalar la librería groq. "
                "Ejecuta: pip install groq"
            ) from error

        client = Groq(api_key=api_key)
        audio_path = Path(audio_path)

        if not _is_quiet():
            print(f"[STT] Transcribiendo '{audio_path.name}' con Groq (whisper-large-v3-turbo)...")

        try:
            with open(audio_path, "rb") as file:
                transcription = client.audio.transcriptions.create(
                    file=(audio_path.name, file.read()),
                    model="whisper-large-v3-turbo",
                    temperature=0.0,
                    response_format="verbose_json",
                )
                return transcription.text.strip()
        except Exception as error:
            if not _is_quiet():
                print(f"[STT] Error en la transcripción con Groq: {error}")
            raise

    def transcribe_file(self, audio_path):
        """Transcribe a WAV file and return the text.

        Parameters
        ----------
        audio_path : str or Path
            Path to the WAV file (Regla A: accepts Path objects).
        """
        audio_path = Path(audio_path)  # Regla A
        if self.model_size == "whisper-large-v3-turbo":
            return self._transcribe_groq(audio_path)

        model = self._load_model()

        # Prompt inicial para contextualizar el vocabulario de la universidad (mejora transcripción de siglas)
        default_prompt = (
            "UNEV, universidad virtual de Honduras, diseño gráfico, "
            "programación web, administración de empresas, admisión, carreras."
        )
        prompt = _env("WHISPER_PROMPT", default_prompt)

        # beam_size=5 era el default de faster-whisper (más lento en CPU).
        # WHISPER_BEAM_SIZE=1–2 recorta latencia con poca pérdida en español kiosco.
        beam_size = max(1, _env_int("WHISPER_BEAM_SIZE", 2))
        transcribe_kwargs = {
            "language": self.language,
            "beam_size": beam_size,
            "vad_filter": True,
            "vad_parameters": dict(min_silence_duration_ms=500),
            "initial_prompt": prompt,
            # Determinista y sin arrastrar contexto previo: evita que el modelo
            # repita/alucine frases de turnos anteriores.
            "temperature": 0.0,
            "condition_on_previous_text": False,
            "no_speech_threshold": 0.6,
        }

        # Cargar hotwords dinámicas
        db_hotwords = self._load_db_hotwords()
        if db_hotwords:
            transcribe_kwargs["hotwords"] = db_hotwords

        try:
            segments, info = model.transcribe(str(audio_path), **transcribe_kwargs)
            text_parts = [segment.text.strip() for segment in segments]
        except RuntimeError as error:
            error_str = str(error).lower()
            should_retry_cpu = (
                _env("WHISPER_DEVICE", "cpu") != "cpu"
                and (
                    "cublas" in error_str
                    or "cuda" in error_str
                    or "cudnn" in error_str
                    or "libcublas" in error_str
                )
            )
            if not should_retry_cpu:
                raise

            if not _is_quiet():
                print(
                    f"[STT] AVISO: CUDA falló durante transcripción ({error}). "
                    "Reintentando con CPU..."
                )
            from faster_whisper import WhisperModel

            self._model = WhisperModel(
                self.model_size,
                device="cpu",
                compute_type="int8",
            )
            segments, info = self._model.transcribe(str(audio_path), **transcribe_kwargs)
            text_parts = [segment.text.strip() for segment in segments]

        return " ".join(text_parts).strip()

    def listen_once(self):
        """Record from the microphone and return the transcribed text.

        Returns an empty string if nothing was captured or transcribed.
        """
        audio = self._record_until_silence()

        if audio.size == 0:
            if not _is_quiet():
                print("[STT] No se capturó audio.")
            return ""

        wav_path = self._audio_to_wav_path(audio)

        try:
            text = self.transcribe_file(wav_path)
        except Exception as error:
            if not _is_quiet():
                print(f"[STT] Error durante la transcripción: {error}")
            text = ""
        finally:
            try:
                wav_path.unlink()  # Regla A: pathlib for deletion too
            except OSError:
                pass

        if _looks_like_hallucination(text):
            if not _is_quiet():
                print(f"[STT] Descartado (silencio/alucinación): {text!r}")
            return ""

        if not _is_quiet():
            print(f"[STT] Transcripción: {text}")

        return text

    # ------------------------------------------------------------------
    # Availability check
    # ------------------------------------------------------------------

    @staticmethod
    def is_available():
        """Return True if sounddevice and faster-whisper (or groq if selected) are importable."""
        try:
            import sounddevice  # noqa: F401
            model = _env("WHISPER_MODEL", "base")
            if model == "whisper-large-v3-turbo":
                from groq import Groq  # noqa: F401
            else:
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

    model = _env("WHISPER_MODEL", "base")
    if model == "whisper-large-v3-turbo":
        try:
            from groq import Groq  # noqa: F401
            groq_status = "librería groq instalada"
        except ImportError:
            return "STT no disponible: falta librería groq. Ejecuta: pip install groq"
        
        has_key = bool(_env("GROQ_API_KEY"))
        key_status = "API key configurada" if has_key else "falta API key de Groq"
        return f"STT activo (Groq Cloud): modelo '{model}', {mic_status}, {groq_status}, {key_status}."

    try:
        from faster_whisper import WhisperModel  # noqa: F401
        whisper_status = "faster-whisper instalado"
    except ImportError:
        return (
            "STT no disponible: falta faster-whisper. "
            "Ejecuta: pip install faster-whisper"
        )

    return f"STT activo: modelo Whisper '{model}', {mic_status}, {whisper_status}."
