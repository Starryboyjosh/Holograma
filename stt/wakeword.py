"""
Detector de palabra clave (wake word) con openWakeWord.

Regla de Oro A: Todas las rutas usan pathlib.Path.
Regla de Oro B: Micrófono con sounddevice (no pyaudio).

Corre siempre-activo sobre el micrófono de la laptop con un único
``sd.InputStream`` continuo (sin abrir/cerrar el stream por trozos) y detecta
una palabra clave para activar la escucha completa de Whisper. Pensado para
lugares ruidosos, donde tener el micrófono "siempre transcribiendo" satura el
modelo y genera comandos falsos.

Uso básico:
    from stt.wakeword import WakeWordDetector
    detector = WakeWordDetector()
    if detector.wait_for_wake():
        # ... se detectó la palabra clave, escuchar con Whisper ...

Modelo:
    - ``WAKEWORD_MODEL`` puede ser el nombre de un modelo preentrenado de
      openWakeWord ("hey_jarvis", "alexa", "hey_mycroft", ...) o la ruta a un
      modelo personalizado ``.onnx``/``.tflite`` (p. ej. uno entrenado para
      "Hola UNEV"). Por defecto: "hey_jarvis".
    - ``WAKEWORD_THRESHOLD`` es el score mínimo [0-1] para disparar (def. 0.5).
"""

from pathlib import Path

from utils import _env, _env_float, _is_quiet, configure_utf8_stdio

configure_utf8_stdio()

# openWakeWord trabaja a 16 kHz, PCM int16, en frames de 80 ms (1280 muestras).
_WAKE_SAMPLE_RATE = 16000
_FRAME_SAMPLES = 1280


class WakeWordDetector:
    """Detecta una palabra clave en streaming con openWakeWord."""

    def __init__(self, model=None, threshold=None):
        self.model_spec = model or _env("WAKEWORD_MODEL", "hey_jarvis")
        self.threshold = (
            threshold
            if threshold is not None
            else _env_float("WAKEWORD_THRESHOLD", 0.5)
        )
        self._model = None

    # ------------------------------------------------------------------
    # Carga perezosa del modelo
    # ------------------------------------------------------------------

    def _load_model(self):
        if self._model is not None:
            return self._model

        try:
            import openwakeword
            from openwakeword.model import Model
        except ImportError as error:
            raise RuntimeError(
                "Falta instalar openwakeword. "
                "Ejecuta: pip install openwakeword"
            ) from error

        import inspect

        # Modelos base (melspectrogram + embedding): las versiones modernas los
        # descargan; openwakeword 0.4.x los trae incluidos en el wheel
        # (resources/models), así que esto es opcional según la versión.
        download = getattr(getattr(openwakeword, "utils", None), "download_models", None)
        if callable(download):
            try:
                download()
            except Exception as error:  # red caída, etc.: seguimos
                if not _is_quiet():
                    print(f"[WAKE] AVISO: no se pudieron descargar modelos base ({error}).")

        params = inspect.signature(Model.__init__).parameters
        is_modern = "wakeword_models" in params  # API >=0.5 acepta nombres cortos

        spec_path = Path(self.model_spec)  # Regla A: pathlib
        is_custom_path = spec_path.exists()
        label = spec_path.stem if is_custom_path else self.model_spec

        if not _is_quiet():
            print(f"[WAKE] Cargando modelo de palabra clave '{label}'...")

        if is_modern:
            target = str(spec_path) if is_custom_path else self.model_spec
            kwargs = {"wakeword_models": [target]}
            if "inference_framework" in params:
                kwargs["inference_framework"] = (
                    "tflite"
                    if is_custom_path and spec_path.suffix == ".tflite"
                    else "onnx"
                )
            self._model = Model(**kwargs)
        else:
            # API legacy (0.4.x): requiere rutas .onnx explícitas. Los modelos
            # preentrenados vienen incluidos en el paquete.
            if is_custom_path:
                model_path = str(spec_path)
            else:
                model_path = self._find_bundled_model(openwakeword, self.model_spec)
            if model_path:
                self._model = Model(wakeword_model_paths=[model_path])
            else:
                if not _is_quiet():
                    print(
                        f"[WAKE] AVISO: no se encontró '{self.model_spec}'; "
                        "cargando todos los modelos preentrenados."
                    )
                self._model = Model()

        if not _is_quiet():
            print("[WAKE] Detector de palabra clave listo.")
        return self._model

    @staticmethod
    def _find_bundled_model(openwakeword_module, name):
        """Resuelve un nombre corto a la ruta de un .onnx incluido (0.4.x).

        Ej.: ``hey_jarvis`` -> ``resources/models/hey_jarvis_v0.1.onnx``.
        """
        import glob

        pkg_dir = Path(openwakeword_module.__file__).resolve().parent
        models_dir = pkg_dir / "resources" / "models"
        base_models = {"embedding_model.onnx", "melspectrogram.onnx", "silero_vad.onnx"}
        for pattern in (f"{name}.onnx", f"{name}_v*.onnx", f"{name}*.onnx"):
            matches = sorted(glob.glob(str(models_dir / pattern)))
            matches = [m for m in matches if Path(m).name not in base_models]
            if matches:
                return matches[0]
        return None

    # ------------------------------------------------------------------
    # Escucha continua
    # ------------------------------------------------------------------

    def wait_for_wake(self, should_continue=None):
        """Bloquea hasta detectar la palabra clave.

        Parameters
        ----------
        should_continue : callable, optional
            Función sin argumentos que devuelve ``True`` mientras se deba seguir
            escuchando. Permite cancelar de forma limpia (p. ej. al pausar el
            holograma). Si devuelve ``False`` se aborta y se retorna ``False``.

        Returns
        -------
        bool
            ``True`` si se detectó la palabra clave; ``False`` si se canceló.
        """
        try:
            import sounddevice as sd
        except ImportError as error:
            raise RuntimeError(
                "Falta instalar sounddevice. Ejecuta: pip install sounddevice"
            ) from error

        import queue as _queue

        model = self._load_model()
        if hasattr(model, "reset"):
            model.reset()  # limpiar estado previo (API moderna)

        audio_q = _queue.Queue()

        def _callback(indata, frames, time_info, status):  # noqa: ARG001
            audio_q.put(indata[:, 0].copy())

        if not _is_quiet():
            print(
                f"[WAKE] Esperando palabra clave (umbral={self.threshold})... "
                "di la palabra clave para activar."
            )

        try:
            with sd.InputStream(
                samplerate=_WAKE_SAMPLE_RATE,
                channels=1,
                dtype="int16",
                blocksize=_FRAME_SAMPLES,
                callback=_callback,
            ):
                while True:
                    if should_continue is not None and not should_continue():
                        return False
                    try:
                        frame = audio_q.get(timeout=0.5)
                    except _queue.Empty:
                        continue

                    scores = model.predict(frame)
                    # scores: {nombre_modelo: score}. Disparar si alguno supera
                    # el umbral (con un modelo cargado normalmente hay uno solo).
                    if any(score >= self.threshold for score in scores.values()):
                        if not _is_quiet():
                            top = max(scores, key=scores.get)
                            print(
                                f"[WAKE] ¡Palabra clave detectada! "
                                f"({top}={scores[top]:.2f})"
                            )
                        return True
        except Exception as error:
            if not _is_quiet():
                print(f"[WAKE] Error escuchando palabra clave: {error}")
            return False

    # ------------------------------------------------------------------
    # Disponibilidad
    # ------------------------------------------------------------------

    @staticmethod
    def is_available():
        """Return True if openwakeword and sounddevice are importable."""
        try:
            import openwakeword  # noqa: F401
            import sounddevice  # noqa: F401
            return True
        except ImportError:
            return False
