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

# Kiosco UNEV: el visitante habla en español. Cualquier valor vacío/auto cae a "es"
# para que Whisper no auto-detecte inglés en entornos ruidosos.
_SPANISH_LANGUAGE_ALIASES = frozenset(
    {
        "es",
        "es-es",
        "es-mx",
        "es-hn",
        "es-419",
        "spanish",
        "español",
        "espanol",
        "castellano",
    }
)


def _resolve_stt_language(language: str | None = None) -> str:
    """Idioma efectivo para STT. Por defecto y en duda: español (``es``).

    ``WHISPER_LANGUAGE=auto`` (o vacío) se fuerza a ``es``: en el holograma no
    queremos detección automática de idioma (suele equivocarse con ruido/música).
    """
    raw = (language if language is not None else _env("WHISPER_LANGUAGE", "es") or "es")
    raw = str(raw).strip().lower()
    if not raw or raw in ("auto", "none", "null", "detect"):
        return "es"
    if raw in _SPANISH_LANGUAGE_ALIASES:
        return "es"
    return raw


# Límite duro de la API de Groq Whisper (error 400 si se supera).
# https://console.groq.com — "prompt length must be 896 characters or fewer"
_GROQ_STT_PROMPT_MAX = 896


def _truncate_stt_prompt(text: str, max_chars: int) -> str:
    """Corta el prompt al tope, preferiblemente en un espacio (no parte un término).

    Además se acota por bytes UTF-8 al mismo tope: Groq a veces reporta longitudes
    distintas al ``len()`` de Python con tildes/ñ (español).
    """
    if not text:
        return ""
    max_chars = max(1, int(max_chars))
    text = text.strip()
    if len(text) > max_chars:
        cut = text[:max_chars].rsplit(" ", 1)[0]
        text = cut if cut else text[:max_chars]
    # Tope por bytes UTF-8 (tildes, ñ, etc. pesan 2 bytes).
    encoded = text.encode("utf-8")
    if len(encoded) <= max_chars:
        return text
    # Recortar hasta caber en max_chars bytes; luego en el último espacio.
    while text and len(text.encode("utf-8")) > max_chars:
        text = text[:-1]
    if " " in text:
        maybe = text.rsplit(" ", 1)[0]
        if maybe:
            text = maybe
    return text.strip()

# Vocabulario base del kiosco (siempre presente): dominio del asistente + UNEV +
# Honduras. Se combina con data/unev_info.json, honduras_info.json y
# open_vocabulary.txt. No meter aquí entradas de cultura_general (ruido).
_CONTEXT_HOTWORDS: tuple[str, ...] = (
    # Producto / kiosco
    "Holograma",
    "Holograma UNEV",
    "holograma",
    "asistente virtual",
    "MISSYOU",
    # Institución
    "UNEV",
    "U N E V",
    "Instituto Universitario de Educación Virtual",
    "universidad virtual",
    "educación virtual",
    "San Pedro Sula",
    "Cortés",
    "ITEE",
    "Instituto Tecnológico de Electricidad y Electrónica",
    "Instituto Tecnológico de Excelencia Educativa",
    "Colonia Trejo",
    "ExpoTech",
    "Expo Tech",
    "feria tecnológica",
    "Feria Tecnológica",
    "Raúl Peña Moreno",
    "Nathalie Cuadrado",
    "Cesar Arguijo",
    "Gladys Ferrufino",
    # Programas y admisión
    "diseño gráfico",
    "Diseño Gráfico",
    "programación web",
    "Programación Web",
    "administración de empresas",
    "Administración de Empresas",
    "técnico universitario",
    "Técnico Universitario",
    "admisión",
    "admisiones",
    "matrícula",
    "inscripción",
    "carreras",
    "créditos",
    "cuatrimestre",
    "ciclos intensivos",
    "PRIND",
    "Programa de Inmersión y Nivelación Digital",
    "Agile Learning",
    "Tecnoaulas",
    "Biblioteca Virtual",
    "SAT",
    "Sistema de Alerta Temprana",
    "CES",
    "Consejo de Educación Superior",
    "DES",
    "Dirección de Educación Superior",
    "UNAH",
    "LMS",
    # Honduras (contexto cultural frecuente en el kiosco)
    "Honduras",
    "Tegucigalpa",
    "Comayagüela",
    "La Ceiba",
    "San Pedro Sula",
    "Islas de la Bahía",
    "Intibucá",
    "Garífuna",
    "Lenca",
    "Creoles",
    "Misquito",
    "Miskito",
    "Tawahka",
    "Maya-Chortí",
    "Nahua",
    "Tolupan",
    "Pesh",
    "PIAH",
    "Pueblos Indígenas y Afrohondureños",
    "baleada",
    "nacatamal",
    "pollo chuco",
    "alcitrón",
    "sisimite",
    "lluvia de peces",
    "Yoro",
    "Café de Honduras",
    "Convenio 169",
    "OIT",
    "Academia Hondureña de la Lengua",
)


def _hotwords_sources_signature(paths) -> str:
    parts: list[str] = []
    for path in paths:
        try:
            st = path.stat()
            parts.append(f"{path.name}:{st.st_mtime_ns}:{st.st_size}")
        except OSError:
            parts.append(f"{path.name}:missing")
    return "|".join(parts)


def _normalize_hotword(term: str) -> str:
    """Limpia un término de hotword (paréntesis rotos, puntuación, basura)."""
    import re

    hw = (term or "").strip()
    if not hw:
        return ""
    # Quitar colas de paréntesis/corchetes mal cerrados o años largos entre ().
    hw = re.sub(r"\s*[\(\[][^)\]]*$", "", hw)
    hw = re.sub(r"\s*[\(\[].*?[\)\]]\s*", " ", hw)
    hw = hw.strip(".,!?;:()-\"' \t")
    hw = re.sub(r"\s+", " ", hw)
    return hw


def _hotword_priority(term: str) -> tuple:
    """Orden: siglas y nombres cortos primero; frases largas al final."""
    t = term.strip()
    # Siglas puras (CES, UNEV, PRIND) → máxima prioridad.
    if t.isupper() and 2 <= len(t) <= 8 and t.isalpha():
        return (0, len(t), t.lower())
    # Nombres propios cortos / 1-2 palabras.
    words = t.split()
    if len(words) <= 2 and len(t) <= 28:
        return (1, len(t), t.lower())
    if len(words) <= 4 and len(t) <= 48:
        return (2, len(t), t.lower())
    return (3, len(t), t.lower())


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


def _correct_kiosk_stt(text: str) -> str:
    """Corrige confusiones frecuentes del STT en el dominio del kiosco UNEV.

    Whisper a menudo oye «UNED» (España) en lugar de «UNEV» (Honduras). No
    inventa contenido: solo normaliza siglas y nombres del campus.
    """
    import re

    if not text:
        return text
    out = text
    # Orden: frases largas primero; luego siglas sueltas.
    replacements = (
        (
            r"\b[Uu]niversidad\s+[Nn]acional\s+de\s+[Ee]ducaci[oó]n\s+a\s+[Dd]istancia\b",
            "Instituto Universitario de Educación Virtual (UNEV)",
        ),
        (r"\bU\.?\s*N\.?\s*E\.?\s*D\.?\b", "UNEV"),
        (r"\bUNED\b", "UNEV"),
        (r"\bUned\b", "UNEV"),
        (r"\buned\b", "UNEV"),
        (r"\bUNEB\b", "UNEV"),
        (r"\bUneb\b", "UNEV"),
        (r"\bUNE\s+V\b", "UNEV"),
        (r"\bExpo\s*tec\b", "ExpoTech"),
        (r"\bEXPO\s*TEC\b", "ExpoTech"),
        (r"\bexpotech\b", "ExpoTech"),
        (r"\bItee\b", "ITEE"),
        (r"\bittee\b", "ITEE"),
    )
    for pattern, repl in replacements:
        out = re.sub(pattern, repl, out)
    return out


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
        self.language = _resolve_stt_language(language)
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
        """Hotwords según el contexto del kiosco (cacheadas por mtime de data/).

        Fuentes (en orden de utilidad):
        1. ``_CONTEXT_HOTWORDS`` — dominio Holograma/UNEV/Honduras (código).
        2. ``data/open_vocabulary.txt`` — vocabulario del operador (visión/STT).
        3. ``data/unev_info.json`` — nombre, programas, siglas, sede.
        4. ``data/honduras_info.json`` — pueblos, próceres, símbolos (no
           ``cultura_general``: miles de Q&A ruidosas).

        Antes se parseaba todo ``honduras_info.json`` en cada turno (~70 ms y
        decenas de miles de términos). Ahora: una construcción por cambio de
        mtime, acotada a ``WHISPER_MAX_HOTWORDS`` (default 400), priorizando
        siglas y nombres cortos.

        Returns
        -------
        str | None
            Términos separados por espacio (formato faster-whisper ``hotwords``
            y reutilizable como base del ``prompt`` de Groq).
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

        # Lista ordenada: baseline primero, luego operador, luego data JSON.
        ordered: list[str] = []
        seen_lower: set[str] = set()

        def add(term: object) -> None:
            if not isinstance(term, str):
                return
            cleaned = _normalize_hotword(term)
            if len(cleaned) <= 2 or len(cleaned) > 80:
                return
            key = cleaned.lower()
            if key in seen_lower:
                return
            seen_lower.add(key)
            ordered.append(cleaned)

        def add_acronyms_and_names(text: str) -> None:
            if not isinstance(text, str) or not text:
                return
            for m in re.finditer(r"\b[A-ZÁÉÍÓÚÜÑ]{2,8}\b", text):
                add(m.group())
            for m in re.finditer(
                r"\b[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+"
                r"(?:\s+(?:de|del|la|las|los|y|e)\s+"
                r"[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+)+\b",
                text,
            ):
                add(m.group())

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
                # Mantener minúsculas de programas ("diseño gráfico") y Title Case
                # de nombres de personas en claves.
                if key.islower() and " " in key:
                    add(key)
                    add(key.title())
                elif key.islower():
                    add(key.title())
                else:
                    add(key)

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
            "mission",
            "vision",
            "faculty",
        }

        # 0. Contexto fijo del kiosco (siempre, aunque falten JSON).
        for term in _CONTEXT_HOTWORDS:
            add(term)

        # 1. Vocabulario abierto del operador (visión / personalizado).
        if vocab_path.exists():
            try:
                for w in re.split(r"[,\n;]+", vocab_path.read_text(encoding="utf-8")):
                    add(w)
            except Exception:
                pass

        # 2. UNEV: identidad + programas + siglas de campos clave.
        if unev_path.exists():
            try:
                data = json.loads(unev_path.read_text(encoding="utf-8"))
                add(data.get("name") or "UNEV")
                add(data.get("full_name") or "")
                add_dict_keys(data.get("programs"), skip=meta_keys)
                for field in (
                    "name",
                    "full_name",
                    "main_claim",
                    "approval",
                    "address",
                    "academic_model",
                    "faculty",
                    "admission_requirements",
                    "social_projection",
                    "values",
                ):
                    add_acronyms_and_names(str(data.get(field) or ""))
            except Exception:
                pass

        # 3. Honduras: secciones indexadas + address (lugares). NO cultura_general.
        if honduras_path.exists():
            try:
                data = json.loads(honduras_path.read_text(encoding="utf-8"))
                add(data.get("name") or "Honduras")
                for section in (
                    "programs",
                    "proceres",
                    "vulgarismos",
                    "simbolos_patrios",
                ):
                    add_dict_keys(data.get(section), skip=meta_keys)
                for field in ("main_claim", "approval", "address", "description"):
                    add_acronyms_and_names(str(data.get(field) or ""))
            except Exception:
                pass

        stop = {
            "del",
            "las",
            "los",
            "por",
            "para",
            "con",
            "una",
            "uno",
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
            "the",
            "and",
            "for",
        }
        cleaned = [t for t in ordered if t.lower() not in stop]

        # Priorizar siglas/nombres cortos; respetar tope configurable.
        max_n = max(50, _env_int("WHISPER_MAX_HOTWORDS", 400))
        cleaned.sort(key=_hotword_priority)
        cleaned = cleaned[:max_n]
        result = " ".join(cleaned) if cleaned else None
        _HOTWORDS_CACHE["signature"] = signature
        _HOTWORDS_CACHE["value"] = result
        return result

    def _build_stt_prompt(self, *, max_chars: int | None = None) -> str:
        """Prompt de contexto para Whisper (local ``initial_prompt`` y Groq ``prompt``).

        Siempre declara **español** y empuja el léxico del kiosco (hotwords de
        ``data/``). Groq no tiene el parámetro ``hotwords`` de faster-whisper;
        el prompt es el canal compartido. ``WHISPER_PROMPT`` en env/config lo
        sustituye por completo si está definido.

        ``max_chars`` acota el resultado (Groq exige ≤896). Por defecto se usa
        ``WHISPER_PROMPT_MAX_CHARS`` (880) para dejar margen con tildes UTF-8.
        """
        # Por defecto bajo el techo de Groq (896): tildes/ñ pueden hacer que el
        # conteo del API sea mayor que len() en Python.
        if max_chars is None:
            max_chars = max(200, _env_int("WHISPER_PROMPT_MAX_CHARS", 880))
        max_chars = min(int(max_chars), _GROQ_STT_PROMPT_MAX)

        override = (_env("WHISPER_PROMPT") or "").strip()
        if override:
            return _truncate_stt_prompt(override, max_chars)

        prefix = (
            "Transcripción en español de Honduras. "
            "El hablante habla solo en español (no en inglés). "
            "La institución se llama UNEV (no UNED ni UNEB): "
            "Instituto Universitario de Educación Virtual. "
            "Campus ITEE Colonia Trejo San Pedro Sula; ExpoTech feria tecnológica. "
            "Asistente del Holograma UNEV: admisión, carreras y cultura. "
            "Vocabulario preferido: "
        )
        budget = max_chars - len(prefix)
        hot = self._load_db_hotwords() or ""
        if budget <= 0:
            return _truncate_stt_prompt(prefix, max_chars)
        if len(hot) > budget:
            cut = hot[:budget].rsplit(" ", 1)[0]
            hot = cut if cut else hot[:budget]
        return _truncate_stt_prompt(prefix + hot, max_chars)

    def _log_stt_decode_config(self, *, backend: str, prompt: str, hotwords: str | None) -> None:
        if _is_quiet():
            return
        n_hot = len((hotwords or "").split()) if hotwords else 0
        utf8_len = len((prompt or "").encode("utf-8"))
        print(
            f"[STT] idioma={self.language} backend={backend} "
            f"hotwords={n_hot} prompt_chars={len(prompt or '')} "
            f"prompt_utf8={utf8_len}",
            flush=True,
        )

    def _transcribe_groq(self, audio_path):
        """Transcribe a WAV file using the Groq API with whisper-large-v3-turbo.

        Groq no expone ``hotwords`` de faster-whisper; se inyecta el mismo
        vocabulario de contexto vía ``prompt`` + ``language="es"``.
        El prompt se trunca a ≤896 caracteres (límite de la API Groq).
        """
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
        # Re-resolver idioma por si cambió el env en caliente desde Ajustes.
        self.language = _resolve_stt_language(self.language)
        # Techo duro de Groq (896). Margen por UTF-8 de tildes/ñ.
        prompt = self._build_stt_prompt(max_chars=_GROQ_STT_PROMPT_MAX)
        prompt = _truncate_stt_prompt(prompt, _GROQ_STT_PROMPT_MAX)
        hotwords = self._load_db_hotwords()
        self._log_stt_decode_config(backend="groq", prompt=prompt, hotwords=hotwords)

        if not _is_quiet():
            print(f"[STT] Transcribiendo '{audio_path.name}' con Groq (whisper-large-v3-turbo)...")

        try:
            with open(audio_path, "rb") as file:
                create_kwargs = {
                    "file": (audio_path.name, file.read()),
                    "model": "whisper-large-v3-turbo",
                    "temperature": 0.0,
                    "response_format": "verbose_json",
                    # Fijo a español del kiosco (no auto-detect).
                    "language": self.language or "es",
                }
                if prompt:
                    create_kwargs["prompt"] = prompt
                transcription = client.audio.transcriptions.create(**create_kwargs)
                return _correct_kiosk_stt(transcription.text.strip())
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
        # Idioma y hotwords se re-evalúan cada turno (Ajustes / env en caliente).
        self.language = _resolve_stt_language(self.language)
        if self.model_size == "whisper-large-v3-turbo":
            return self._transcribe_groq(audio_path)

        model = self._load_model()

        # Prompt + hotwords del contexto UNEV/Honduras/kiosco (español).
        prompt = self._build_stt_prompt()
        db_hotwords = self._load_db_hotwords()
        self._log_stt_decode_config(
            backend=f"faster-whisper/{self.model_size}",
            prompt=prompt,
            hotwords=db_hotwords,
        )

        # beam_size=5 era el default de faster-whisper (más lento en CPU).
        # WHISPER_BEAM_SIZE=1–2 recorta latencia con poca pérdida en español kiosco.
        beam_size = max(1, _env_int("WHISPER_BEAM_SIZE", 2))
        transcribe_kwargs = {
            "language": self.language or "es",
            "task": "transcribe",  # nunca "translate" a inglés
            "beam_size": beam_size,
            "vad_filter": True,
            "vad_parameters": dict(min_silence_duration_ms=500),
            "initial_prompt": prompt,
            # Determinista y sin arrastrar contexto previo: evita que el modelo
            # repita/alucine frases de turnos anteriores.
            "temperature": 0.0,
            "condition_on_previous_text": False,
            "no_speech_threshold": 0.6,
            "multilingual": False,
        }

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

        return _correct_kiosk_stt(" ".join(text_parts).strip())

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

        text = _correct_kiosk_stt(text)

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
