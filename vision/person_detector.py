"""
Detector de visión del holograma UNEV: un solo modelo open-vocab YOLOE.

Por defecto ``yoloe-26n-seg.pt``: personas + objetos personalizados (etiquetas
de la pantalla Entrenar / open_vocabulary) en **una** inferencia por ciclo.
Todos los caminos de detección (frame, once, continuo, labels ad-hoc) usan
ese checkpoint vía Ultralytics ``YOLOE`` — no hay modelo COCO ni YOLO-World.

Regla de Oro A: Todas las rutas usan pathlib.Path.

Uso básico:
    from vision.person_detector import YoloPersonDetector
    detector = YoloPersonDetector()
    detector.load()
    detected = detector.detect_person_once()
"""

import json
import os
import threading
import time
from pathlib import Path

try:  # OpenCV es obligatorio en runtime, opcional para importar el módulo.
    import cv2
except ImportError:  # pragma: no cover - entorno sin OpenCV
    cv2 = None

from utils import _env, _env_float, _env_int, _is_quiet

# Geometría y señales de imagen viven en módulos propios (funciones puras,
# testeables sin cargar Ultralytics). Se importan con los nombres privados
# históricos para no reescribir cada punto de uso.
from vision.geometry import (
    best_person_for_box as _best_person_for_box_fn,
)
from vision.geometry import (
    clamp_box_to_frame,
)
from vision.geometry import (
    collar_y_max as _collar_y_max,
)
from vision.geometry import (
    compute_scale_back as _compute_scale_back,
)
from vision.geometry import (
    logo_roi_fractions as _logo_roi_fractions,
)
from vision.geometry import (
    point_in_logo_zone as _point_in_logo_zone_fn,
)
from vision.geometry import (
    rel_center_on_person as _rel_center_on_person_fn,
)
from vision.geometry import (
    scale_box as _scale_box,
)
from vision.geometry import (
    snap_box_to_logo_zone as _snap_box_to_logo_zone_fn,
)
from vision.geometry import (
    xyxy_tuple as _xyxy_tuple,
)
from vision.image_signals import (
    ROI_MIN_STDDEV,
    compare_hsv_signature,
    compute_hsv_hist,
    is_white_light_or_glare,
    match_orb,
    match_template_multiscale,
)
from vision.person_signature import person_signature
from vision.scoring import fuse_logo_channels
from vision.tracking import LabelHysteresis, PersonAssociator

# Checkpoint canónico del kiosco. Cualquier legacy se redirige aquí.
DEFAULT_YOLOE_WEIGHTS = "yoloe-26n-seg.pt"
# Nombres antiguos (COCO / World / YOLOE mayor) → se fuerzan al canónico.
_LEGACY_WEIGHT_ALIASES = frozenset(
    {
        "yolo26n.pt",
        "yolov8n.pt",
        "yolov8s.pt",
        "yolov8s-world.pt",
        "yolov8m-world.pt",
        "yoloe-11s-seg.pt",
        "yoloe-11n-seg.pt",
    }
)
# Ultralytics / CLIP se degradan con demasiados prompts; cap razonable.
_MAX_OPEN_VOCAB_PROMPTS = 40

# Etiquetas que cuentan como "persona" al partir el resultado open-vocab.
_PERSON_LABELS = frozenset(
    {
        "person",
        "persona",
        "people",
        "human",
        "hombre",
        "mujer",
        "estudiante",
        "student",
    }
)

# Siempre se piden en set_classes (presencia del kiosco). YOLOE open-vocab
# responde mejor con varios sinónimos de persona (inglés + español).
_BASE_PERSON_PROMPTS: tuple[str, ...] = (
    "person",
    "persona",
    "people",
    "human",
    "man",
    "woman",
    "estudiante",
)

# Sinónimos open-vocab. Clave = etiqueta del operador en minúsculas.
# IMPORTANTE (YOLOE text prompts): NO usar términos genéricos como "blue shirt",
# "polo azul" o "polo shirt" — el modelo los asocia a CUALQUIER camisa y genera
# falsos "Uniforme ITEE". Preferir prompts específicos del logo / bordado.
# Docs Ultralytics YOLOE: set_classes + get_text_pe; prompts concretos = menos FP.
# https://docs.ultralytics.com/models/yoloe/
_OPEN_VOCAB_ALIASES: dict[str, tuple[str, ...]] = {
    "uniforme itee": (
        # Específicos del logo (preferidos por YOLOE / menos FP).
        "ITEE yellow logo embroidery",
        "yellow embroidered logo badge",
        "ITEE school logo on chest",
        "ITEE school emblem",
        "yellow logo badge on blue uniform",
        "ITEE uniform",
        "uniforme ITEE",
        # Solo para mapear salidas del modelo → etiqueta operador.
        "school uniform",
        "student uniform",
    ),
    "uniforme": (
        "school uniform logo badge",
        "student uniform embroidered logo",
        "school emblem badge",
        "school uniform",
    ),
}

# Open-vocab de etiquetas con fotos en Entrenar: umbral alto; la aceptación
# final la da el match con la imagen de referencia (no el color).
_LOGO_OPEN_VOCAB_MIN_CONF = 0.45

# --- Logos de Entrenar (cualquier colegio / etiqueta) ---
#
# Fuente de verdad: fotos de ``data/training_metadata.json`` (+ crop x,y,w,h).
# Matching: firma de color HSV + pirámide multi-escala (TM_CCOEFF_NORMED) + ORB.
#
# Open-vocab YOLOE solo sugiere; sin match a la plantilla de Entrenar no cuenta
# como esa etiqueta. El cuello/placket se evita con geometría de ROI pecho.
# El score combinado es 0.75*template + 0.25*ORB; cuando ORB=0 (logos bordados
# pequeños), el máximo posible es 0.75*tmpl.  Con tmpl real ~0.60 eso da ~0.45.
# Umbral 0.42 acepta matches reales sin tragarse ruido.
_TMPL_MATCH_MIN = 0.42

# Versión del formato de ``data/logo_index.npz``. Se incrementa cuando cambia
# el esquema de la caché: el npz actual en disco (sin ``by_hsv``, sin esta
# clave) debe rechazarse y reconstruirse en vez de cargarse a medias (§13 I1).
# v3 (WAVE-20/I10): ``meta_sig`` incluye el estado de cada imagen referenciada.
_LOGO_CACHE_VERSION = 3


def _yolo_debug() -> bool:
    """``HOLOGRAM_YOLO_DEBUG`` activo. Estaba copiado en 4 sitios distintos."""
    return os.getenv("HOLOGRAM_YOLO_DEBUG", "0").lower() in ("1", "true", "yes")


# Prioridad de la señal que produjo una detección custom. Un match contra la
# foto de Entrenar (plantilla + HSV + ORB) es evidencia mucho más fuerte que el
# texto open-vocab, que es semánticamente amplio: «school uniform» dispara con
# cualquier camisa. Ver §4.3 de yolo_instructions.md.
_SOURCE_PRIORITY = {
    "logo_ref": 3,
    "logo_ref_verified": 3,
    "logo_chest": 3,
    "logo_visual": 3,
    "open_vocab_snapped": 1,
}


def _source_rank(obj: dict) -> int:
    return _SOURCE_PRIORITY.get(obj.get("source") or "", 0)


class YoloPersonDetector:
    """Visión del kiosco: un solo YOLOE open-vocab + logos Entrenar (ORB).

    Un checkpoint (default ``yoloe-26n-seg.pt``) hace personas y clases de
    Entrenar / open_vocabulary en **una** inferencia. Los logos de fotos
    de entrenamiento se refuerzan con matching multi-escala + ORB.

    Parameters
    ----------
    model_name : str
        Pesos YOLOE (``YOLO_MODEL``). Default ``yoloe-26n-seg.pt``.
        Nombres legacy (COCO / World) se redirigen al canónico.
    confidence_threshold : float
        Umbral de confianza (personas y open-vocab). Custom open-vocab usa
        además ``YOLO_CUSTOM_CONFIDENCE`` (más bajo por defecto).
    """

    def __init__(self, model_name=None, confidence_threshold=None):
        raw_name = model_name if model_name is not None else _env(
            "YOLO_MODEL", DEFAULT_YOLOE_WEIGHTS
        )
        self.model_name = self._normalize_weights_name(raw_name)
        # YOLOE open-vocab: 0.45 filtraba personas/custom típicos (0.15–0.40)
        # ya en predict, antes del split por tipo.
        self.confidence_threshold = confidence_threshold or _env_float(
            "YOLO_CONFIDENCE", 0.28
        )
        self.custom_confidence = _env_float("YOLO_CUSTOM_CONFIDENCE", 0.12)
        # Umbral open-vocab para etiquetas que tienen fotos de Entrenar.
        self.logo_ov_confidence = _env_float(
            "YOLO_UNIFORM_CONFIDENCE", _LOGO_OPEN_VOCAB_MIN_CONF
        )
        # Compat tests antiguos.
        self.uniform_ov_confidence = self.logo_ov_confidence
        # 416: mejor recall persona/uniforme que 320; aún razonable en CPU.
        self.imgsz = _env_int("YOLO_IMGSZ", 416)
        # device vacío = auto de Ultralytics; "cpu", "0", "cuda:0", etc.
        self.device = _env("YOLO_DEVICE", "").strip() or None
        self.half = _env("YOLO_HALF", "0").lower() in ("1", "true", "yes")
        # Lado máximo del frame antes de predecir (ahorra copias si la cámara
        # entrega 1080p). 0 = no redimensionar en software (solo imgsz del modelo).
        self.max_side = _env_int("YOLO_MAX_SIDE", 960)
        self.iou = _env_float("YOLO_IOU", 0.5)
        self.max_det = _env_int("YOLO_MAX_DET", 50)
        # Contador para logs periódicos de detección (diagnóstico).
        self._detect_cycles = 0
        # Único modelo YOLOE open-vocab (tests lo mockean con FakeModel).
        self.model = None
        self._model_kind = "none"  # "yoloe" | "mock" | "none"
        self.face_analyzer = None
        self._custom_classes: list[str] = []
        self._custom_vocabulary: list[str] = []
        # Última lista pasada a set_classes (evita re-encodar el texto cada ciclo).
        self._prompt_key: tuple[str, ...] | None = None
        self._warmup_done = False
        # label -> list of gray template images (uint8) from training photos
        self._logo_images: dict[str, list] = {}
        # label -> list of ORB descriptors (np.ndarray)
        self._logo_templates: dict[str, list] = {}
        # label -> list of HSV color histograms (np.ndarray)
        self._logo_hsv_hists: dict[str, list] = {}
        self._last_reload_time = 0
        # Último cuadro anotado (JPEG) para transmitir al frontend vía MJPEG.
        self._latest_jpeg: bytes | None = None
        self._jpeg_lock = threading.Lock()
        # Suscriptores del feed MJPEG. Codificar JPEG en cada iteración (~30 fps)
        # gasta CPU aunque nadie mire; con cero suscriptores el bucle se salta el
        # imencode por completo. El contador lo mueven los handlers de /api/video_feed.
        # La detección YOLO NUNCA se apaga por ausencia de personas o de viewers:
        # solo el encode JPEG es opcional.
        self._feed_subscribers = 0
        self._feed_lock = threading.Lock()
        # Señal cooperativa de parada: al activarla, run_continuous sale del bucle
        # y el context manager de Camera libera el dispositivo (apagar = liberar).
        self._stop_event = threading.Event()
        # I5: descriptores de persona (máscaras) del último predict; separados
        # de `analysis` para no difundirlos por WebSocket. Vacio por defecto.
        self._last_person_signatures: list[dict] = []
        # Histéresis M-of-N (I4) para los eventos de custom objects.
        self._label_tracker = LabelHysteresis(
            confirm_cycles=_env_int("YOLO_CUSTOM_CONFIRM_CYCLES", 2),
            forget_seconds=_env_float("YOLO_CUSTOM_FORGET_SECONDS", 10.0),
            retain_seconds=_env_float("YOLO_CUSTOM_RETAIN_SECONDS", 60.0),
        )
        # I6/I7: asociador de tracks de persona (REID) detrás de YOLO_REID.
        # Apagado por defecto; no activar el default hasta medir en producción
        # con qué frecuencia dispara el veto de empate. Mientras YOLO_REID=0,
        # run_continuous se comporta exactamente igual que hoy.
        self._reid_enabled = _env_int("YOLO_REID", 0) != 0
        self._person_associator = PersonAssociator() if self._reid_enabled else None
        # Overlay (I6/I7): tracks confirmados del ciclo previo del asociador.
        self._reid_prev_confirmed = set()
        self._load_training_data()

    @staticmethod
    def _normalize_weights_name(name: str | None) -> str:
        """Fuerza el checkpoint canónico YOLOE; avisa si había un nombre legacy."""
        if not name or not str(name).strip():
            return DEFAULT_YOLOE_WEIGHTS
        raw = str(name).strip()
        base = Path(raw).name.lower()
        if base in _LEGACY_WEIGHT_ALIASES or (
            base.endswith(".pt")
            and "yoloe" not in base
            and "world" not in base
            and base.startswith("yolo")
        ):
            print(
                f"[YOLO] «{raw}» no es YOLOE open-vocab; "
                f"usando {DEFAULT_YOLOE_WEIGHTS}."
            )
            return DEFAULT_YOLOE_WEIGHTS
        if "world" in base and "yoloe" not in base:
            print(
                f"[YOLO] «{raw}» es YOLO-World; el kiosco usa solo YOLOE → "
                f"{DEFAULT_YOLOE_WEIGHTS}."
            )
            return DEFAULT_YOLOE_WEIGHTS
        return raw

    def stop(self):
        """Solicita que run_continuous termine y libere la cámara."""
        self._stop_event.set()

    def _interruptible_sleep(self, seconds: float) -> None:
        """Duerme hasta *seconds* o hasta ``stop()`` (no bloquea el apagado)."""
        if seconds is None or seconds <= 0:
            return
        self._stop_event.wait(timeout=seconds)

    def _predict_kwargs(self, extra: dict | None = None) -> dict:
        """Argumentos comunes de inferencia local (latencia / recursos)."""
        kwargs: dict = {
            "verbose": False,
            "imgsz": self.imgsz,
            "conf": self.confidence_threshold,
            "iou": self.iou,
            "max_det": self.max_det,
        }
        if self.device is not None:
            kwargs["device"] = self.device
        if self.half:
            kwargs["half"] = True
        if extra:
            kwargs.update(extra)
        return kwargs

    def _prepare_frame(self, frame):
        """Opcional: reduce el frame grande antes de YOLO (sin apagar la cámara)."""
        if frame is None or self.max_side <= 0:
            return frame
        try:
            h, w = frame.shape[:2]
        except Exception:
            return frame
        longest = max(h, w)
        if longest <= self.max_side:
            return frame
        try:
            import cv2
        except ImportError:
            return frame
        scale = self.max_side / float(longest)
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))
        return cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

    def _resolve_weights_path(self, model_name: str) -> Path:
        """Resuelve ``models/<name>`` o ruta absoluta/relativa al proyecto."""
        model_path = Path(model_name)
        if model_path.is_absolute():
            return model_path
        base_dir = Path(__file__).resolve().parent.parent
        in_models = base_dir / "models" / model_path
        at_root = base_dir / model_path
        if in_models.exists() or not at_root.exists():
            return in_models
        return at_root

    def _load_yoloe(self, name: str):
        """Carga siempre con Ultralytics ``YOLOE`` (único backend soportado)."""
        from ultralytics import YOLOE

        name = self._normalize_weights_name(name)
        path = self._resolve_weights_path(name)
        load_arg = str(path) if path.exists() else name
        if not path.exists():
            print(
                f"[YOLO] No está en models/ ({path.name}); "
                "Ultralytics intentará descargarlo o usar el nombre de hub."
            )
        return YOLOE(load_arg)

    def load(self):
        """Carga YOLOE (personas + custom en una inferencia) y aplica prompts."""
        try:
            print(f"[YOLO] Cargando YOLOE: {self.model_name}...")
            self.model = self._load_yoloe(self.model_name)
            self._model_kind = type(self.model).__name__.lower()
            print(
                f"[YOLO] Listo ({type(self.model).__name__}): {self.model_name} "
                "(personas + custom open-vocab)"
            )
            self._apply_classes(self._active_class_list())
            self.warmup()
        except Exception as error:
            print(f"[YOLO] ERROR cargando YOLOE ({error})")
            self.model = None
            self._model_kind = "none"
            self._prompt_key = None

        self._rebuild_logo_templates()
        return self

    def _ensure_loaded(self):
        """Load model if it hasn't been loaded yet."""
        if self.model is None:
            self.load()

    def warmup(self, force: bool = False) -> bool:
        """Una inferencia dummy para JIT/CUDA/CLIP tras el load.

        Evita el primer frame lento en el bucle del kiosco. Idempotente.
        """
        if self.model is None:
            return False
        if self._warmup_done and not force:
            return True
        if not hasattr(self.model, "predict"):
            self._warmup_done = True
            return True
        try:
            import numpy as np

            dummy = np.zeros((self.imgsz, self.imgsz, 3), dtype=np.uint8)
            self.model.predict(dummy, **self._predict_kwargs({"conf": 0.01}))
            self._warmup_done = True
            print("[YOLO] Warmup OK")
            return True
        except Exception as error:
            print(f"[YOLO] Warmup omitido ({error})")
            self._warmup_done = True  # no reintentar en bucle
            return False

    def model_info(self) -> dict:
        """Metadatos del modelo cargado (diagnóstico / API)."""
        names = None
        if self.model is not None:
            raw_names = getattr(self.model, "names", None)
            if isinstance(raw_names, dict):
                names = {int(k): str(v) for k, v in raw_names.items()}
            elif raw_names is not None:
                names = list(raw_names)
        return {
            "weights": self.model_name,
            "canonical": DEFAULT_YOLOE_WEIGHTS,
            "backend": type(self.model).__name__ if self.model is not None else None,
            "kind": self._model_kind,
            "loaded": self.model is not None,
            "has_set_classes": bool(
                self.model is not None and hasattr(self.model, "set_classes")
            ),
            "has_get_text_pe": bool(
                self.model is not None and hasattr(self.model, "get_text_pe")
            ),
            "imgsz": self.imgsz,
            "device": self.device,
            "confidence": self.confidence_threshold,
            "custom_confidence": self.custom_confidence,
            "iou": self.iou,
            "max_det": self.max_det,
            "active_prompts": list(self._prompt_key or ()),
            "custom_classes": list(self._custom_classes),
            "vocabulary": list(self._custom_vocabulary),
            "names": names,
            "warmup_done": self._warmup_done,
        }

    def get_active_prompts(self) -> list[str]:
        """Prompts actualmente enviados a ``set_classes`` (o la lista objetivo)."""
        if self._prompt_key is not None:
            return list(self._prompt_key)
        return self._active_class_list()

    def set_prompts(self, prompts: list[str] | None = None) -> bool:
        """Aplica prompts open-vocab (o recalcula desde training/vocab).

        Parameters
        ----------
        prompts : list[str] or None
            Si es None, usa persona + clases Entrenar + vocabulario.
        """
        self._ensure_loaded()
        if prompts is None:
            prompts = self._active_class_list()
        return self._apply_classes(list(prompts))

    def reload_vocabulary(self) -> list[str]:
        """Relee training_metadata + open_vocabulary y re-aplica set_classes."""
        self._load_training_data()
        self._last_reload_time = time.time()
        self.set_prompts()
        return self.get_active_prompts()

    def _custom_class_list(self) -> list[str]:
        """Etiquetas custom (+ sinónimos) sin mezclar las de persona."""
        terms = list(self._custom_classes)
        for t in self._custom_vocabulary:
            if t and t not in terms:
                terms.append(t)
        expanded: list[str] = []
        for t in terms:
            if not t or t.strip().lower() in _PERSON_LABELS:
                continue
            expanded.append(t)
            for alias in _OPEN_VOCAB_ALIASES.get(t.strip().lower(), ()):
                if alias not in expanded:
                    expanded.append(alias)
        return expanded

    def _active_class_list(self) -> list[str]:
        """Prompts open-vocab: persona + custom, dedupe y cap de longitud."""
        terms: list[str] = []
        for t in list(_BASE_PERSON_PROMPTS) + self._custom_class_list():
            if t and t not in terms:
                terms.append(t)
        if len(terms) > _MAX_OPEN_VOCAB_PROMPTS:
            # Prioridad: prompts base de persona + las primeras custom.
            head = [t for t in terms if t in _BASE_PERSON_PROMPTS]
            rest = [t for t in terms if t not in _BASE_PERSON_PROMPTS]
            budget = max(0, _MAX_OPEN_VOCAB_PROMPTS - len(head))
            terms = head + rest[:budget]
            print(
                f"[YOLO] Vocabulario recortado a {_MAX_OPEN_VOCAB_PROMPTS} prompts "
                f"(CLIP/YOLOE)."
            )
        return terms

    def _map_label(self, raw_name: str) -> str:
        """Normaliza nombre de clase (sinónimos → etiqueta del operador)."""
        if not raw_name:
            return raw_name
        key = raw_name.strip().lower()
        if key in _PERSON_LABELS:
            return "person"
        for c in self._custom_classes:
            if c.strip().lower() == key:
                return c
        # Claves más específicas primero (uniforme itee > uniforme).
        for primary, aliases in sorted(
            _OPEN_VOCAB_ALIASES.items(), key=lambda kv: -len(kv[0])
        ):
            if key == primary or key in {a.lower() for a in aliases}:
                for c in self._custom_classes:
                    cl = c.strip().lower()
                    if cl == primary or primary in cl:
                        return c
                return primary.title() if primary.islower() else primary
        return raw_name

    def _apply_classes(self, class_list: list[str]) -> bool:
        """Configura prompts open-vocab en YOLOE vía ``get_text_pe`` + ``set_classes``."""
        if self.model is None:
            return False
        # Dedupe preservando orden
        clean: list[str] = []
        for t in class_list:
            s = str(t).strip()
            if s and s not in clean:
                clean.append(s)
        if not clean:
            clean = list(_BASE_PERSON_PROMPTS)
        if len(clean) > _MAX_OPEN_VOCAB_PROMPTS:
            clean = clean[:_MAX_OPEN_VOCAB_PROMPTS]

        key = tuple(clean)
        if key == self._prompt_key:
            return True

        if not hasattr(self.model, "set_classes"):
            print(
                "[YOLO] El modelo mock/real no expone set_classes; "
                f"se necesita YOLOE ({DEFAULT_YOLOE_WEIGHTS})."
            )
            return False

        try:
            if hasattr(self.model, "get_text_pe"):
                try:
                    pe = self.model.get_text_pe(clean)
                    self.model.set_classes(clean, pe)
                except TypeError:
                    # Mocks / firmas antiguas sin embeddings
                    self.model.set_classes(clean)
            else:
                self.model.set_classes(clean)
            self._prompt_key = key
            print(f"[YOLO] Prompts YOLOE activos ({len(clean)}): {clean}")
            return True
        except Exception as error:
            print(f"[YOLO] No se pudieron aplicar clases open-vocab ({error}).")
            return False

    def _load_training_data(self):
        """Load custom classes from training_metadata.json and open_vocabulary.txt."""
        base_dir = Path(__file__).resolve().parent.parent
        meta_path = base_dir / "data" / "training_metadata.json"
        vocab_path = base_dir / "data" / "open_vocabulary.txt"

        if meta_path.exists():
            try:
                with meta_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                new_classes = []
                for entry in data:
                    label = entry.get("label", "").strip()
                    if label and label not in new_classes:
                        new_classes.append(label)
            except Exception:
                new_classes = list(self._custom_classes)
        else:
            new_classes = list(self._custom_classes)

        if vocab_path.exists():
            try:
                raw = vocab_path.read_text(encoding="utf-8").strip()
                if raw:
                    new_vocab = [
                        t.strip() for t in raw.split(",") if t.strip()
                    ]
                else:
                    new_vocab = []
            except Exception:
                new_vocab = list(self._custom_vocabulary)
        else:
            new_vocab = list(self._custom_vocabulary)

        if new_classes != self._custom_classes or new_vocab != self._custom_vocabulary:
            self._custom_classes = new_classes
            self._custom_vocabulary = new_vocab
            # Forzar re-set_classes en la próxima inferencia.
            self._prompt_key = None
            self._rebuild_logo_templates()
            if self._custom_classes or self._custom_vocabulary:
                print(f"[YOLO] Clases entrenadas actualizadas: {self._custom_classes}")
                print(f"[YOLO] Vocabulario abierto actualizado: {self._custom_vocabulary}")

    def _maybe_reload_training(self) -> None:
        current_time = time.time()
        if current_time - getattr(self, "_last_reload_time", 0) > 5.0:
            self._load_training_data()
            self._last_reload_time = current_time

    def _resolve_training_image(self, thumbnail: str) -> Path | None:
        """Resuelve rutas tipo ``/data/images/x.jpg`` al fichero local."""
        if not thumbnail:
            return None
        raw = str(thumbnail).strip()
        base = Path(__file__).resolve().parent.parent
        candidates = [
            base / raw.lstrip("/"),
            base / "data" / "images" / Path(raw).name,
            Path(raw),
        ]
        for c in candidates:
            if c.is_file():
                return c
        return None

    def _crop_training_roi(self, img, entry: dict):
        """Recorta el bbox de Entrenar (x,y,w,h) si es válido; si no, imagen completa.

        Las cajas vienen de la UI de Entrenar: suelen ser el logo/objeto marcado
        dentro del thumbnail. Usar el crop mejora mucho el matchTemplate/ORB.
        """
        try:
            import cv2  # noqa: F401
        except ImportError:
            return img
        h, w = img.shape[:2]
        try:
            x = float(entry.get("x", 0) or 0)
            y = float(entry.get("y", 0) or 0)
            bw = float(entry.get("w", 0) or 0)
            bh = float(entry.get("h", 0) or 0)
        except (TypeError, ValueError):
            return img
        if bw < 8 or bh < 8:
            return img
        # Fracciones 0–1 vs píxeles absolutos.
        if 0 < bw <= 1.5 and 0 < bh <= 1.5:
            x, y, bw, bh = x * w, y * h, bw * w, bh * h
        x1 = int(max(0, min(w - 1, x)))
        y1 = int(max(0, min(h - 1, y)))
        x2 = int(max(x1 + 1, min(w, x + bw)))
        y2 = int(max(y1 + 1, min(h, y + bh)))
        if x2 - x1 < 8 or y2 - y1 < 8:
            return img
        crop = img[y1:y2, x1:x2]
        if not crop.size:
            return img
        # WAVE-18 (I8): fallback defensivo — una caja en píxeles absolutos
        # (>1.5) que produce un recorte sin textura es casi seguro un box en
        # píxeles CSS display guardado por una UI vieja (EntrenarSection antes
        # de normalizar). No podemos reconstruir el scale del display desde el
        # backend, así que solo lo registramos bajo HOLOGRAM_YOLO_DEBUG y
        # devolvemos el crop: el matcher lo rechazará por textura en vez de
        # fallar en silencio con una región plana.
        if x > 1.5 and _yolo_debug():
            import cv2 as _cv2

            roi = crop
            if len(roi.shape) == 3:
                roi = _cv2.cvtColor(roi, _cv2.COLOR_BGR2GRAY)
            std = float(_cv2.meanStdDev(roi)[1][0][0])
            if std < ROI_MIN_STDDEV:
                print(
                    f"[YOLO] I8: caja en píxeles absolutos ({x:.1f},{y:.1f},"
                    f"{bw:.1f}x{bh:.1f}) sobre imagen {w}x{h} -> crop plano "
                    f"(std={std:.2f}). ¿Box en píxeles CSS display? Re-importar "
                    f"la foto con la UI normalizada (WAVE-18)."
                )
        return crop

    def _rebuild_logo_templates(self, base_dir=None) -> None:
        """Indexa fotos de Entrenar como plantillas grises + descriptores ORB.

        Optimización de memoria/CPU:
        - Una sola plantilla uint8 gris por foto (max lado ~128), no 7 escalas.
          ``matchTemplate`` ya reescala al tamaño del ROI en runtime.
        - ORB sobre la misma miniatura (~160 px).
        - Opcional: caché ``data/logo_index.npz`` para no releer JPEGs cada reload.

        ``base_dir`` permite apuntar a un directorio de pruebas (tests) en vez
        del repo; en producción es ``None`` y se usa la raíz del proyecto.
        """
        self._logo_templates = {}
        self._logo_images = {}
        self._logo_hsv_hists = {}
        base = Path(base_dir) if base_dir is not None else Path(
            __file__
        ).resolve().parent.parent
        meta_path = base / "data" / "training_metadata.json"
        cache_path = base / "data" / "logo_index.npz"
        if not meta_path.exists():
            return
        try:
            import cv2
            import numpy as np

            data = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            return
        if not isinstance(data, list):
            return

        # WAVE-20 (I10): la firma incluye el estado de CADA imagen referenciada
        # (mtime_ns + size), no solo del metadata. Borrar y re-importar fotos en
        # Entrenar sin tocar el metadata (o tocar solo el JPEG) ya no puede
        # servir un npz stale: si cualquier imagen cambia o falta, se reconstruye.
        img_parts: list[str] = []
        for entry in data:
            if not isinstance(entry, dict):
                continue
            img_path = self._resolve_training_image(entry.get("thumbnail") or "")
            if img_path is None:
                img_parts.append("missing")
                continue
            try:
                st = img_path.stat()
                img_parts.append(f"{img_path.name}:{st.st_mtime_ns}:{st.st_size}")
            except OSError:
                img_parts.append(f"{img_path.name}:missing")
        meta_sig = (
            f"{meta_path.stat().st_mtime_ns}:{meta_path.stat().st_size}|"
            f"{','.join(sorted(img_parts))}"
        )
        # Caché: si el metadata, las imágenes y la versión del esquema no
        # cambiaron, cargar arrays ya preparados. Sin la clave `cache_version`
        # (npz escrito por versiones viejas, sin `by_hsv` o con `meta_sig`
        # sin imágenes) se descarta y se reconstruye.
        try:
            if cache_path.is_file():
                cached = np.load(str(cache_path), allow_pickle=True)
                sig = cached["meta_sig"]
                sig_s = str(sig.item() if hasattr(sig, "item") else sig)
                cached_version = int(cached.get("cache_version", 0))
                if sig_s == meta_sig and cached_version == _LOGO_CACHE_VERSION:
                    by_img = dict(cached["by_img"].item())
                    by_des = dict(cached["by_des"].item())
                    by_hsv = dict(cached["by_hsv"].item())
                    self._logo_images = by_img
                    self._logo_templates = by_des
                    self._logo_hsv_hists = by_hsv
                    n_img = sum(len(v) for v in by_img.values())
                    n_orb = sum(len(v) for v in by_des.values())
                    n_hsv = sum(len(v) for v in by_hsv.values())
                    mem = sum(g.nbytes for imgs in by_img.values() for g in imgs)
                    mem += sum(d.nbytes for dess in by_des.values() for d in dess)
                    print(
                        f"[YOLO] Logos Entrenar (caché npz v{_LOGO_CACHE_VERSION}): "
                        f"plantillas={n_img} ORB={n_orb} HSV={n_hsv} "
                        f"labels={list(by_img)} mem≈{mem / 1024:.0f} KiB"
                    )
                    return
        except Exception:
            pass

        try:
            import cv2

            orb = cv2.ORB_create(500)
        except Exception:
            return

        # Max lado de la plantilla en RAM (uint8 gris). Suficiente para logos.
        tmpl_max = max(64, min(192, _env_int("YOLO_LOGO_TMPL_MAX_SIDE", 128)))
        orb_max = max(tmpl_max, min(256, _env_int("YOLO_LOGO_ORB_MAX_SIDE", 160)))

        by_des: dict[str, list] = {}
        by_img: dict[str, list] = {}
        by_hsv: dict[str, list] = {}
        for entry in data:
            if not isinstance(entry, dict):
                continue
            label = str(entry.get("label") or "").strip()
            if not label:
                continue
            img_path = self._resolve_training_image(entry.get("thumbnail") or "")
            if img_path is None:
                continue
            img = cv2.imread(str(img_path))
            if img is None:
                continue
            # Preferir el recorte del logo que dibujó el operador en Entrenar.
            img = self._crop_training_roi(img, entry)
            h, w = img.shape[:2]
            if h < 8 or w < 8:
                continue

            # --- Firma cromática HSV ---
            hsv_hist = self._compute_hsv_hist(img)
            if hsv_hist is not None:
                by_hsv.setdefault(label, []).append(hsv_hist)

            # --- 1 plantilla gris compacta ---
            scale = tmpl_max / float(max(h, w)) if max(h, w) > tmpl_max else 1.0
            tw, th = max(12, int(w * scale)), max(12, int(h * scale))
            small = cv2.resize(img, (tw, th), interpolation=cv2.INTER_AREA)
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            try:
                gray = cv2.equalizeHist(gray)
            except Exception:
                pass
            # Contiguo uint8 para matchTemplate rápido.
            by_img.setdefault(label, []).append(np.ascontiguousarray(gray))

            # --- ORB sobre miniatura un poco mayor ---
            scale_o = orb_max / float(max(h, w)) if max(h, w) > orb_max else 1.0
            orb_img = cv2.resize(
                img,
                (max(12, int(w * scale_o)), max(12, int(h * scale_o))),
                interpolation=cv2.INTER_AREA,
            )
            gray_o = cv2.cvtColor(orb_img, cv2.COLOR_BGR2GRAY)
            try:
                gray_o = cv2.equalizeHist(gray_o)
            except Exception:
                pass
            _kp, des = orb.detectAndCompute(gray_o, None)
            if des is not None and len(des) >= 8:
                by_des.setdefault(label, []).append(np.ascontiguousarray(des))

        self._logo_templates = by_des
        self._logo_images = by_img
        self._logo_hsv_hists = by_hsv
        if by_img or by_des:
            n_img = sum(len(v) for v in by_img.values())
            n_orb = sum(len(v) for v in by_des.values())
            mem = sum(g.nbytes for imgs in by_img.values() for g in imgs)
            mem += sum(d.nbytes for dess in by_des.values() for d in dess)
            print(
                f"[YOLO] Logos Entrenar (referencia): "
                f"plantillas={ {k: len(v) for k, v in by_img.items()} } "
                f"ORB={ {k: len(v) for k, v in by_des.items()} } "
                f"mem≈{mem / 1024:.0f} KiB"
            )
            try:
                np.savez_compressed(
                    str(cache_path),
                    meta_sig=np.asarray(meta_sig),
                    cache_version=np.asarray(_LOGO_CACHE_VERSION),
                    by_img=np.asarray(by_img, dtype=object),
                    by_des=np.asarray(by_des, dtype=object),
                    by_hsv=np.asarray(by_hsv, dtype=object),
                )
            except Exception:
                pass

    def _person_chest_rois(self, frame, persons: list[dict]) -> list[tuple]:
        """ROI del pecho con logo: cuello + 2×(cabeza→cuello), lado del logo.

        Geometría (caja persona YOLO, fracciones 0=arriba/izq … 1=abajo/der):
          - Cabeza 0→HEAD_END; distancia cabeza→cuello = HEAD_NECK.
          - Pecho logo: y0 = HEAD_END + 2·HEAD_NECK (nunca cuello/cara).
          - Horizontal: mitad izquierda de la caja (logo en imagen kiosco).
            YOLO_LOGO_MIRROR=1 invierte X si hace falta.
        """
        if frame is None or not persons:
            return []
        h, w = frame.shape[:2]
        y0r, y1r, x0r, x1r = _logo_roi_fractions()
        rois = []
        for p in persons:
            box = p.get("box")
            if not box or len(box) < 4:
                continue
            x1, y1, x2, y2 = [float(v) for v in box]
            x1 = max(0.0, min(float(w - 1), x1))
            x2 = max(0.0, min(float(w), x2))
            y1 = max(0.0, min(float(h - 1), y1))
            y2 = max(0.0, min(float(h), y2))
            pw, ph = x2 - x1, y2 - y1
            if pw < 40 or ph < 60:
                continue
            tx1 = int(x1 + x0r * pw)
            tx2 = int(x1 + x1r * pw)
            ty1 = int(y1 + y0r * ph)
            ty2 = int(y1 + y1r * ph)
            tx1, ty1 = max(0, tx1), max(0, ty1)
            tx2, ty2 = min(w, tx2), min(h, ty2)
            if tx2 - tx1 < 28 or ty2 - ty1 < 28:
                continue
            crop = frame[ty1:ty2, tx1:tx2]
            if crop.size == 0:
                continue
            rois.append((crop, (tx1, ty1, tx2, ty2), (x1, y1, x2, y2)))
        return rois

    # Geometría: delegada a ``vision.geometry`` (funciones puras). Se mantienen
    # como métodos porque tests y llamadas internas los usan por ese nombre.

    def _point_in_logo_zone(
        self, cx: float, cy: float, person_box: tuple, tol: float = 0.04
    ) -> bool:
        """True si el centro (cx,cy) cae en el pecho-logo de la persona."""
        return _point_in_logo_zone_fn(cx, cy, person_box, tol)

    @staticmethod
    def _rel_center_on_person(
        box: tuple, person_box: tuple
    ) -> tuple[float, float] | None:
        """Centro de ``box`` en fracciones 0–1 respecto a la caja persona."""
        return _rel_center_on_person_fn(box, person_box)

    def _snap_box_to_logo_zone(
        self, box: tuple, person_box: tuple
    ) -> tuple[float, float, float, float]:
        """Mueve la caja al ROI pecho-logo con tamaño proporcional a la persona."""
        return _snap_box_to_logo_zone_fn(box, person_box)

    def _best_person_for_box(
        self, box: tuple, persons: list[dict]
    ) -> tuple | None:
        """Caja persona que contiene el centro de ``box``, o la más cercana."""
        return _best_person_for_box_fn(box, persons)

    def _is_uniform_label(self, label: str) -> bool:
        """Compat: true si el nombre sugiere uniforme (UI/tests)."""
        key = str(label or "").strip().lower()
        return "uniforme" in key or "itee" in key or "uniform" in key

    def _person_index_for_box(self, box, persons: list[dict]) -> int | None:
        """Índice de la persona dueña de ``box`` en ``persons`` (0-based).

        Reutiliza ``best_person_for_box`` (misma heurística de contención → más
        cercana) y devuelve la posición en la lista, no la caja. ``None`` si no
        hay personas o ninguna se puede atribuir (§13 I2).
        """
        if not box or not persons:
            return None
        best = _best_person_for_box_fn(box, persons)
        if best is None:
            return None
        best_key = tuple(round(float(v), 3) for v in best)
        for i, person in enumerate(persons):
            pb = person.get("box")
            if not pb or len(pb) < 4:
                continue
            key = tuple(round(float(v), 3) for v in pb[:4])
            if key == best_key:
                return i
        return None

    def _is_logo_trained_label(self, label: str) -> bool:
        """True si hay imágenes de Entrenar (plantilla/ORB) para esta etiqueta."""
        if not label:
            return False
        if label in self._logo_images or label in self._logo_templates or label in self._logo_hsv_hists:
            return True
        key = label.strip().lower()
        for k in list(self._logo_images.keys()) + list(self._logo_templates.keys()) + list(self._logo_hsv_hists.keys()):
            if str(k).strip().lower() == key:
                return True
        if self._is_uniform_label(label) and (self._logo_images or self._logo_templates or self._logo_hsv_hists):
            return True
        return False

    def _num_trained_labels(self) -> int:
        """Etiquetas distintas con referencias de Entrenar (imagen/ORB/HSV).

        El fallback cruzado de ``_logo_*_for`` (§13 I1) solo debe aplicar cuando
        existe **exactamente una** etiqueta entrenada: ese es el caso de
        bootstrap para el que se escribió (una sola escuela "logo X" respalda
        la etiqueta open-vocab "uniforme X"). Con dos o más, la etiqueta X no
        debe casar contra las plantillas de la escuela Y.
        """
        keys = set(self._logo_images) | set(self._logo_templates) | set(
            self._logo_hsv_hists
        )
        return len(keys)

    def _logo_templates_for(self, label: str) -> list:
        if label in self._logo_images:
            return self._logo_images[label]
        key = label.strip().lower()
        for k, v in self._logo_images.items():
            if str(k).strip().lower() == key:
                return v
        if self._is_uniform_label(label) and self._num_trained_labels() == 1:
            for k, v in self._logo_images.items():
                if self._is_uniform_label(k):
                    return v
        return []

    def _logo_orb_for(self, label: str) -> list:
        if label in self._logo_templates:
            return self._logo_templates[label]
        key = label.strip().lower()
        for k, v in self._logo_templates.items():
            if str(k).strip().lower() == key:
                return v
        if self._is_uniform_label(label) and self._num_trained_labels() == 1:
            for k, v in self._logo_templates.items():
                if self._is_uniform_label(k):
                    return v
        return []

    def _logo_hsv_hists_for(self, label: str) -> list:
        if label in self._logo_hsv_hists:
            return self._logo_hsv_hists[label]
        key = label.strip().lower()
        for k, v in self._logo_hsv_hists.items():
            if str(k).strip().lower() == key:
                return v
        if self._is_uniform_label(label) and self._num_trained_labels() == 1:
            for k, v in self._logo_hsv_hists.items():
                if self._is_uniform_label(k):
                    return v
        return []

    @staticmethod
    def _debug_enabled() -> bool:
        return _yolo_debug()

    @staticmethod
    def _box_is_glare(frame, box) -> bool:
        """True si el recorte del frame en ``box`` es luz blanca / ventana.

        Unifica el recorte + clampeo + chequeo de glare que estaba duplicado
        literalmente en las dos ramas de ``_filter_uniform_objects``.
        """
        if frame is None or box is None:
            return False
        bounds = clamp_box_to_frame(box, getattr(frame, "shape", None))
        if bounds is None:
            return False
        x1, y1, x2, y2 = bounds
        crop = frame[y1:y2, x1:x2]
        if getattr(crop, "size", 0) == 0:
            return False
        return is_white_light_or_glare(crop)

    @staticmethod
    def _compute_hsv_hist(bgr_img):
        """Histograma 2D HSV normalizado (delegado a ``vision.image_signals``)."""
        return compute_hsv_hist(bgr_img)

    @staticmethod
    def _is_white_light_or_glare(bgr_crop) -> bool:
        """True si el recorte es luz blanca / ventana / destello."""
        return is_white_light_or_glare(bgr_crop)

    def _match_hsv_color_signature(self, crop, label: str) -> float:
        """Correlación de firma de color HSV (0–1) contra las fotos de Entrenar."""
        if self._is_white_light_or_glare(crop):
            if self._debug_enabled():
                print(
                    f"[YOLO] Descartado «{label}» por detección de luz blanca / ventana"
                )
            return 0.0
        return compare_hsv_signature(crop, self._logo_hsv_hists_for(label))

    def _match_template_multiscale(
        self, gray_roi, templates: list
    ) -> tuple[float, tuple | None]:
        """Mejor score TM_CCOEFF_NORMED sobre la pirámide multi-escala."""
        return match_template_multiscale(gray_roi, templates)

    def _match_orb_in_roi(self, gray_roi, des_list: list) -> float | None:
        """Score 0–1 por ORB, o ``None`` sin evidencia (WAVE-19/I9)."""
        return match_orb(gray_roi, des_list)

    def _match_logo_in_gray(
        self, crop, label: str
    ) -> tuple[float, tuple | None, str]:
        """Match firma HSV + plantilla multiescala + ORB de ``label`` en un ROI. → (score, box_rel, method)."""
        # Gate de color HSV: por diseño está INERTE (§13 I1). El default es 0.0
        # (nunca rechaza) porque re-activarlo a ciegas puede rechazar logos
        # válidos bajo la iluminación real del kiosco. Se registra el
        # ``color_score`` en cada match aceptado bajo HOLOGRAM_YOLO_DEBUG=1.
        hsv_min = _env_float("YOLO_LOGO_HSV_MIN", 0.0)
        color_score = self._match_hsv_color_signature(crop, label)
        if color_score < hsv_min:
            return 0.0, None, "hsv_mismatch"

        try:
            import cv2
            if len(crop.shape) == 3 and crop.shape[2] == 3:
                gray_roi = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            else:
                gray_roi = crop
        except Exception:
            gray_roi = crop

        imgs = self._logo_templates_for(label)
        des_list = self._logo_orb_for(label)
        tmpl_score, tmpl_box = self._match_template_multiscale(gray_roi, imgs)
        # WAVE-19 (I9): None = ORB sin evidencia (ROI liso / sin keypoints /
        # sin descriptores de referencia), NO evidencia negativa.
        orb_score = self._match_orb_in_roi(gray_roi, des_list)

        # I3 (§13): fusión ponderada por calidad detrás de YOLO_LOGO_FUSION=1.
        # score = Σ(w_c·q_c_eff·s_c) / Σ(w_c·q_c_eff). Un canal sin evidencia
        # (None) no aporta al numerador ni al denominador. Hasta recalibrar el
        # umbral contra una sesión grabada, el default sigue siendo la escalera.
        if _env("YOLO_LOGO_FUSION", "0").lower() in ("1", "true", "yes"):
            conf = fuse_logo_channels(
                {
                    "template": None if tmpl_box is None else tmpl_score,
                    "orb": orb_score,
                    "hsv": color_score,
                }
            )
            self._log_logo_color(label, conf, color_score)
            if conf <= 0.0:
                return 0.0, None, "none"
            # La localización la da el template; sin él, el centro del ROI.
            if tmpl_box is not None:
                return conf, tmpl_box, "template"
            rh, rw = gray_roi.shape[:2]
            s = min(rw, rh) * 0.35
            cx, cy = rw * 0.5, rh * 0.5
            box = (cx - s * 0.5, cy - s * 0.5, cx + s * 0.5, cy + s * 0.5)
            return conf, box, "fusion"

        # Combinar: template manda en localización; ORB refuerza confianza.
        # Gate relajado: tmpl_score real >= 0.40 es suficiente para pasar;
        # el conf combinado se evalúa después contra _TMPL_MATCH_MIN.
        tmpl_min_internal = _env_float("YOLO_LOGO_TMPL_MIN", _TMPL_MATCH_MIN)
        if tmpl_box is not None and tmpl_score >= tmpl_min_internal * 0.85:
            # I9: con ORB sin evidencia (None) el conf es solo template; el
            # umbral efectivo vuelve a 0.42 (no 0.56 = 0.42/0.75 con orb=0).
            conf = min(0.98, tmpl_score if orb_score is None else 0.75 * tmpl_score + 0.25 * orb_score)
            self._log_logo_color(label, conf, color_score)
            return conf, tmpl_box, "template"
        if orb_score is not None and orb_score >= 0.85 and tmpl_box is not None:
            conf = min(0.95, 0.55 * tmpl_score + 0.45 * orb_score)
            self._log_logo_color(label, conf, color_score)
            return conf, tmpl_box, "orb+template"
        if orb_score is not None and orb_score >= 0.95:
            # Solo ORB fuerte: caja = centro del ROI (sin localización fina).
            rh, rw = gray_roi.shape[:2]
            s = min(rw, rh) * 0.35
            cx, cy = rw * 0.5, rh * 0.5
            box = (cx - s * 0.5, cy - s * 0.5, cx + s * 0.5, cy + s * 0.5)
            self._log_logo_color(label, orb_score, color_score)
            return orb_score, box, "orb"
        return 0.0, None, "none"

    def _log_logo_color(self, label: str, conf: float, color_score: float) -> None:
        """Registra el ``color_score`` del match aceptado (datos para I3)."""
        if _yolo_debug():
            print(
                f"[YOLO] Logo «{label}» aceptado conf={conf:.2f} "
                f"color_score={color_score:.2f}"
            )

    def _verify_logo_reference(
        self, frame, box: tuple, label: str
    ) -> tuple[bool, tuple | None, float]:
        """Comprueba que el parche de ``box`` se parece a la foto de Entrenar.

        Returns
        -------
        (ok, refined_box_frame, score)
        """
        if frame is None or box is None or len(box) < 4:
            # Tests sin frame: no se puede verificar referencia.
            return False, None, 0.0
        if not self._is_logo_trained_label(label):
            return False, None, 0.0
        if cv2 is None:
            return False, None, 0.0
        try:
            h, w = frame.shape[:2]
        except Exception:
            return False, None, 0.0
        x1 = int(max(0, min(w - 1, float(box[0]))))
        y1 = int(max(0, min(h - 1, float(box[1]))))
        x2 = int(max(x1 + 1, min(w, float(box[2]))))
        y2 = int(max(y1 + 1, min(h, float(box[3]))))
        # Expandir: el bbox open-vocab a veces es más grande/pequeño que el logo.
        pad_x = max(8, int(0.35 * (x2 - x1)))
        pad_y = max(8, int(0.35 * (y2 - y1)))
        x1 = max(0, x1 - pad_x)
        y1 = max(0, y1 - pad_y)
        x2 = min(w, x2 + pad_x)
        y2 = min(h, y2 + pad_y)
        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            return False, None, 0.0
        score, rel_box, _method = self._match_logo_in_gray(crop, label)
        tmpl_min = _env_float("YOLO_LOGO_TMPL_MIN", _TMPL_MATCH_MIN)
        if score < tmpl_min or rel_box is None:
            return False, None, score
        rx1, ry1, rx2, ry2 = rel_box
        refined = (
            float(x1) + rx1,
            float(y1) + ry1,
            float(x1) + rx2,
            float(y1) + ry2,
        )
        return True, refined, score

    def _detect_logo_templates(self, frame, persons: list[dict] | None = None) -> list[dict]:
        """Detecta logos de Entrenar por **imagen de referencia** (template + ORB).

        No usa color (amarillo/azul). Sirve para ITEE y futuros colegios:
        cada etiqueta con fotos en ``training_metadata`` se busca en el ROI pecho.

        I2 (§13): los bucles van **por ROI primero** (``for roi: for label:``)
        y cada ROI emite **su** mejor etiqueta, con el ``person_index`` de la
        persona dueña. Antes era ``for label: for roi:`` y el "mejor global" por
        etiqueta colapsaba a **una** instancia aunque hubiera varias personas
        con el mismo uniforme. Con ``(label, person_index)`` en ``_dedupe_custom``
        el mismo uniforme de dos estudiantes genera dos objetos.
        """
        if frame is None:
            return []
        if not self._logo_images and not self._logo_templates:
            return []
        if cv2 is None:
            return []

        persons = persons or []
        if not persons:
            return []  # No personas en escena: los logos de uniformes solo existen sobre personas.

        rois = self._person_chest_rois(frame, persons)
        if not rois:
            return []

        found: list[dict] = []
        tmpl_min = _env_float("YOLO_LOGO_TMPL_MIN", _TMPL_MATCH_MIN)
        debug = os.getenv("HOLOGRAM_YOLO_DEBUG", "0").lower() in ("1", "true", "yes")
        labels = set(self._logo_images) | set(self._logo_templates)

        for crop, (ox1, oy1, _ox2, _oy2), person_box in rois:
            best_conf = 0.0
            best_box_frame = None
            best_label = None
            best_detail = ""

            for label in labels:
                score, rel_box, method = self._match_logo_in_gray(crop, label)
                if rel_box is None or score < tmpl_min:
                    continue
                ix1, iy1, ix2, iy2 = rel_box
                fx1 = float(ox1 + ix1)
                fy1 = float(oy1 + iy1)
                fx2 = float(ox1 + ix2)
                fy2 = float(oy1 + iy2)
                cx = 0.5 * (fx1 + fx2)
                cy = 0.5 * (fy1 + fy2)
                # Evitar anclar en cuello aunque el ROI pecho sea holgado.
                if not self._point_in_logo_zone(cx, cy, person_box, tol=0.06):
                    continue
                conf = float(score)
                if conf <= best_conf:
                    continue
                best_conf = conf
                best_box_frame = self._snap_box_to_logo_zone((fx1, fy1, fx2, fy2), person_box)
                best_label = label
                best_detail = f"{method} score={score:.2f}"

            accept = (
                best_conf >= tmpl_min
                and best_box_frame is not None
                and best_label is not None
            )
            if debug and (accept or best_conf >= 0.45):
                print(
                    f"[YOLO] Logo ref «{best_label}» conf={best_conf:.2f} "
                    f"({best_detail}) accept={accept}"
                )
            if not accept:
                continue
            found.append(
                {
                    "label": best_label,
                    "confidence": float(best_conf),
                    "box": best_box_frame,
                    "source": "logo_ref",
                    "person_index": self._person_index_for_box(
                        best_box_frame, persons
                    ),
                }
            )
        return found

    def _detect_logo_visual(self, frame, persons: list[dict] | None = None) -> list[dict]:
        """YOLOE con **visual prompts** (SAVPE) para logos de Entrenar.

        WAVE-21 (I11): cuando ``YOLO_LOGO_VISUAL=1``, YOLOE aprende *one-shot*
        cómo se ve el logo con ``refer_image`` (el thumbnail de Entrenar) +
        ``visual_prompts`` (el bbox que dibujó el operador). Es un canal
        **adicional** al template+ORB: nada lo reemplaza, solo suma evidencia
        detrás de su flag. Los resultados llevan ``source="logo_visual"`` y
        compiten por prioridad/confianza en ``_dedupe_custom`` (§13 I3).

        Caveat de Ultralytics: usar ``refer_image`` fija las clases del modelo
        permanentemente (set_classes). Por eso al terminar se restauran las
        prompts del kiosco con ``_apply_classes`` para no romper la detección
        de personas en el siguiente ciclo.
        """
        flag = os.getenv("YOLO_LOGO_VISUAL", "0").lower() in ("1", "true", "yes")
        if not flag or frame is None or self.model is None:
            return []
        try:
            import numpy as np
            from ultralytics.models.yolo.yoloe import YOLOEVPSegPredictor
        except Exception:
            return []
        if not self._logo_images and not self._logo_templates:
            return []

        base = Path(__file__).resolve().parent.parent
        meta_path = base / "data" / "training_metadata.json"
        if not meta_path.exists():
            return []
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            return []
        if not isinstance(data, list) or not data:
            return []

        # Un referente visual por etiqueta: primer thumbnail con bbox válido.
        refs: list[tuple[str, Path, tuple]] = []
        seen_labels: set[str] = set()
        for entry in data:
            if not isinstance(entry, dict):
                continue
            label = str(entry.get("label") or "").strip()
            if not label or label in seen_labels:
                continue
            img_path = self._resolve_training_image(entry.get("thumbnail") or "")
            if img_path is None:
                continue
            h, w = (0, 0)
            try:
                ref_img = cv2.imread(str(img_path))
                if ref_img is None:
                    continue
                h, w = ref_img.shape[:2]
            except Exception:
                continue
            if h < 8 or w < 8:
                continue
            try:
                x = float(entry.get("x", 0) or 0)
                y = float(entry.get("y", 0) or 0)
                bw = float(entry.get("w", 0) or 0)
                bh = float(entry.get("h", 0) or 0)
            except (TypeError, ValueError):
                continue
            if bw < 8 or bh < 8:
                continue
            if 0 < bw <= 1.5 and 0 < bh <= 1.5:
                x, y, bw, bh = x * w, y * h, bw * w, bh * h
            x1 = float(max(0, min(w - 1, x)))
            y1 = float(max(0, min(h - 1, y)))
            x2 = float(max(x1 + 1, min(w, x + bw)))
            y2 = float(max(y1 + 1, min(h, y + bh)))
            if x2 - x1 < 8 or y2 - y1 < 8:
                continue
            seen_labels.add(label)
            refs.append((label, img_path, (x1, y1, x2, y2)))

        if not refs:
            return []

        found: list[dict] = []
        debug = _yolo_debug()
        for label, img_path, (x1, y1, x2, y2) in refs:
            visual_prompts = {
                "bboxes": np.array([[x1, y1, x2, y2]], dtype=np.float32),
                "cls": np.array([0]),
            }
            try:
                results = self.model.predict(
                    frame,
                    refer_image=str(img_path),
                    visual_prompts=visual_prompts,
                    predictor=YOLOEVPSegPredictor,
                    imgsz=self.imgsz,
                    conf=self.custom_confidence,
                    verbose=False,
                )
            except Exception as error:
                if debug:
                    print(f"[YOLO] Visual prompt «{label}» falló: {error}")
                continue
            finally:
                # refer_image fija las clases del modelo; restaurar el kiosco.
                self._prompt_key = None
                self._apply_classes(self._active_class_list())

            if not results:
                continue
            for result in results:
                boxes = getattr(result, "boxes", None)
                if boxes is None:
                    continue
                for box in boxes:
                    conf = float(box.conf[0])
                    if conf < self.custom_confidence:
                        continue
                    x1f, y1f, x2f, y2f = _xyxy_tuple(box.xyxy[0])
                    found.append(
                        {
                            "label": label,
                            "confidence": conf,
                            "box": (float(x1f), float(y1f), float(x2f), float(y2f)),
                            "source": "logo_visual",
                            "person_index": self._person_index_for_box(
                                (float(x1f), float(y1f), float(x2f), float(y2f)),
                                persons or [],
                            ),
                        }
                    )
                    if debug:
                        print(f"[YOLO] Visual «{label}» conf={conf:.2f}")
        return found

    def _predict_boxes(
        self, frame, conf: float | None = None
    ) -> list[tuple[str, float, tuple]]:
        """Ejecuta ``model.predict`` (YOLOE) y devuelve (label, conf, box) en coords originales.

        Siempre usa ``self.model`` (único YOLOE). ``frame`` puede ser None en tests.
        """
        model = self.model
        if model is None:
            return []
        conf = self.confidence_threshold if conf is None else conf
        # frame puede ser None en tests con mocks; se reenvía tal cual.
        prepared = self._prepare_frame(frame) if frame is not None else frame
        kwargs = self._predict_kwargs({"conf": conf})
        try:
            results = model.predict(prepared, **kwargs)
        except TypeError:
            # Mocks / firmas sin iou/max_det: reintentar solo con kwargs básicos.
            basic = {
                "verbose": False,
                "imgsz": self.imgsz,
                "conf": conf,
            }
            if self.device is not None:
                basic["device"] = self.device
            try:
                results = model.predict(prepared, **basic)
            except Exception as error:
                print(f"[YOLO] Error en predict: {error}")
                return []
        except Exception as error:
            print(f"[YOLO] Error en predict: {error}")
            return []
        if not results:
            return []
        scale_back = _compute_scale_back(frame, prepared) if frame is not None else 1.0
        # I5: descriptor de persona desde las máscaras. Solo cuando está activo,
        # y se guarda aparte (nunca entra en `analysis` ni en el feed MJPEG).
        sig_enabled = _env("YOLO_PERSON_SIGNATURES", "0").lower() in ("1", "true", "yes")
        hsv_small = None
        sig_masks = None
        if sig_enabled and prepared is not None:
            try:
                import cv2 as _cv2
                import numpy as _np
                hsv_full = _cv2.cvtColor(prepared, _cv2.COLOR_BGR2HSV)
            except Exception:
                hsv_full = None
            if hsv_full is not None:
                masks = None
                for result in results:
                    m = getattr(result, "masks", None)
                    if m is not None and getattr(m, "data", None) is not None:
                        masks = m
                        break
                if masks is not None:
                    try:
                        data = masks.data
                        if data is not None and data.shape[0] > 0:
                            hm, wm = data.shape[1], data.shape[2]
                            hsv_small = _cv2.resize(hsv_full, (wm, hm))
                            sig_masks = _np.asarray(data)
                    except Exception:
                        hsv_small = None
                        sig_masks = None
        out: list[tuple[str, float, tuple]] = []
        self._last_person_signatures = []
        for result in results:
            names = getattr(result, "names", None) or {}
            boxes = getattr(result, "boxes", None)
            if boxes is None:
                continue
            for i, box in enumerate(boxes):
                confidence = float(box.conf[0])
                if confidence < conf:
                    continue
                cls_id = int(box.cls[0])
                if isinstance(names, dict):
                    raw_name = str(names.get(cls_id, cls_id))
                else:
                    try:
                        raw_name = str(names[cls_id])
                    except Exception:
                        raw_name = str(cls_id)
                x1, y1, x2, y2 = _scale_box(_xyxy_tuple(box.xyxy[0]), scale_back)
                entry = (raw_name, confidence, (x1, y1, x2, y2))
                out.append(entry)
                if (
                    sig_enabled
                    and sig_masks is not None
                    and self._is_person_label(raw_name)
                    and i < sig_masks.shape[0]
                    and hsv_small is not None
                ):
                    try:
                        sig = person_signature(
                            _np.asarray(sig_masks[i]),
                            hsv_small,
                        )
                        if sig is not None:
                            self._last_person_signatures.append(
                                {"box": (x1, y1, x2, y2), "signature": sig}
                            )
                    except Exception:
                        pass
        return out

    def _is_person_label(self, raw_name: str) -> bool:
        key = str(raw_name).strip().lower()
        if key in _PERSON_LABELS or key == "person":
            return True
        # Índices numéricos solo cuentan si el prompt 0 es persona (open-vocab).
        # No asumir COCO class-id 0: con YOLOE el id depende de set_classes.
        return False

    def _split_detections(
        self, hits: list[tuple[str, float, tuple]]
    ) -> tuple[list[dict], list[dict]]:
        """Parte (raw, conf, box) en personas vs custom según umbrales."""
        persons: list[dict] = []
        custom_objects: list[dict] = []
        for raw_name, confidence, box in hits:
            label = self._map_label(raw_name)
            entry = {"confidence": confidence, "box": box, "raw_label": raw_name}
            if self._is_person_label(raw_name) or self._is_person_label(label):
                persons.append(entry)
            elif confidence >= self.custom_confidence:
                custom_objects.append({"label": label, **entry})
        return persons, custom_objects

    def _filter_uniform_objects(
        self,
        custom_objects: list[dict],
        persons: list[dict],
        frame=None,
    ) -> list[dict]:
        """Filtra custom: logos de Entrenar = match a imagen de referencia.

        - ``logo_ref`` / ``logo_chest``: ya matchearon plantilla/ORB → aceptar.
        - Etiqueta **con** fotos en Entrenar + open-vocab: solo si el parche
          se parece a la referencia (no color ITEE). Sin match → descartar
          (evita «cualquier camisa = Uniforme ITEE» y permite otros colegios).
        - Etiqueta **sin** fotos Entrenar: open-vocab genérico (botella, etc.).
        """
        filtered: list[dict] = []
        debug = _yolo_debug()
        ov_min = float(self.logo_ov_confidence)
        collar_max = _collar_y_max()
        for obj in custom_objects:
            lab = obj.get("label", "")
            src = obj.get("source") or ""
            if src in ("logo_ref", "logo_chest"):
                filtered.append(obj)
                continue

            # Objeto custom sin plantillas de Entrenar → open-vocab libre,
            # salvo nombres tipo "uniforme*": aún se aplica veto de cuello.
            if not self._is_logo_trained_label(lab):
                if self._is_uniform_label(lab):
                    conf_u = float(obj.get("confidence") or 0.0)
                    if conf_u < ov_min:
                        if debug:
                            print(
                                f"[YOLO] Descartado «{lab}» conf baja "
                                f"(sin foto Entrenar; {conf_u:.2f} < {ov_min:.2f})"
                            )
                        continue
                    box = obj.get("box")
                    if self._box_is_glare(frame, box):
                        if debug:
                            print(
                                f"[YOLO] Descartado «{lab}» open-vocab: "
                                f"caja es luz blanca / ventana (sin Entrenar)"
                            )
                        continue
                    person_box = self._best_person_for_box(box, persons) if box else None
                    if person_box is not None and box:
                        rel = self._rel_center_on_person(box, person_box)
                        if rel is not None and rel[1] < collar_max:
                            if debug:
                                print(
                                    f"[YOLO] Descartado «{lab}» en cuello "
                                    f"(sin foto Entrenar; rel_y={rel[1]:.2f})"
                                )
                            continue
                        if not self._point_in_logo_zone(
                            0.5 * (float(box[0]) + float(box[2])),
                            0.5 * (float(box[1]) + float(box[3])),
                            person_box,
                            tol=0.08,
                        ):
                            if debug:
                                print(
                                    f"[YOLO] Descartado «{lab}» fuera de pecho "
                                    f"(sin foto Entrenar)"
                                )
                            continue
                        # Snap bbox al pecho para el overlay.
                        obj = {
                            **obj,
                            "box": self._snap_box_to_logo_zone(box, person_box),
                            "source": "open_vocab_snapped",
                        }
                filtered.append(obj)
                continue

            # --- Etiqueta con imagen(es) de referencia en Entrenar ---
            box = obj.get("box")
            if not box or len(box) < 4:
                continue
            conf = float(obj.get("confidence") or 0.0)
            if conf < ov_min:
                if debug:
                    print(
                        f"[YOLO] Descartado «{lab}» open-vocab conf baja "
                        f"({conf:.2f} < {ov_min:.2f})"
                    )
                continue

            # Filtro de luz blanca sobre la caja YOLOE ORIGINAL, antes de
            # verificar contra la foto de Entrenar. Es deliberado: el segundo
            # intento de `_verify_logo_reference` busca en `person_box` y ahí
            # encontraría el logo real del uniforme, aceptando una ventana como
            # si fuera el logo. Ver §4.8 de yolo_instructions.md.
            if self._box_is_glare(frame, box):
                if debug:
                    print(
                        f"[YOLO] Descartado «{lab}» open-vocab: "
                        f"caja YOLOE es luz blanca / ventana"
                    )
                continue

            person_box = self._best_person_for_box(box, persons)
            search_box = box
            if person_box is not None:
                rel = self._rel_center_on_person(box, person_box)
                if rel is not None and rel[1] < collar_max:
                    # Open-vocab en cuello: reintentar match en ROI pecho.
                    search_box = self._snap_box_to_logo_zone(box, person_box)
                elif not self._point_in_logo_zone(
                    0.5 * (float(box[0]) + float(box[2])),
                    0.5 * (float(box[1]) + float(box[3])),
                    person_box,
                    tol=0.08,
                ):
                    search_box = self._snap_box_to_logo_zone(box, person_box)

            if frame is None:
                # Tests sin frame: no hay referencia que verificar → no aceptar
                # open-vocab de logos entrenados (solo logo_ref lo haría).
                if debug:
                    print(f"[YOLO] Descartado «{lab}» open-vocab sin frame de referencia")
                continue

            ok, refined, score = self._verify_logo_reference(frame, search_box, lab)
            if not ok:
                # Segundo intento: ROI pecho de la persona entera.
                if person_box is not None:
                    ok, refined, score = self._verify_logo_reference(
                        frame, person_box, lab
                    )
            if not ok:
                if debug:
                    print(
                        f"[YOLO] Descartado «{lab}» open-vocab: no coincide con "
                        f"foto Entrenar (score={score:.2f})"
                    )
                continue

            # ── Snap final: el refined de _verify_logo_reference es el
            # rect del template match (puede ser 20×20 px). Siempre
            # escalar al tamaño proporcional del pecho de la persona. ──
            final_box = refined or search_box
            if person_box is not None:
                final_box = self._snap_box_to_logo_zone(final_box, person_box)

            filtered.append(
                {
                    **obj,
                    "box": final_box,
                    "confidence": max(conf, float(score)),
                    "source": "logo_ref_verified",
                }
            )
            if debug:
                print(
                    f"[YOLO] «{lab}» open-vocab verificado vs Entrenar "
                    f"score={score:.2f}"
                )
        return filtered

    @staticmethod
    def _dedupe_custom(custom_objects: list[dict]) -> list[dict]:
        """Una entrada por ``(label, person_index)``: fuente, luego confianza.

        Las fuentes verificadas contra la foto de Entrenar (``logo_ref``,
        ``logo_ref_verified``, ``logo_chest``) ganan SIEMPRE a una detección
        open-vocab del mismo label, aunque el texto traiga más confianza.

        I2 (§13): la clave es ``(label, person_index)`` y no solo ``label`` —
        dos personas con el mismo uniforme entrenado producen **dos** objetos,
        no uno. Sin ``person_index`` (tests, objetos open-vocab genéricos) la
        clave degenera a ``(label, None)`` y el colapso es idéntico al previo.

        Antes se ordenaba solo por confianza aquí, y la preferencia por fuente
        se aplicaba después, en ``_detect_all`` — sobre una lista que ya tenía
        una sola entrada por label, así que no podía cambiar nada. El resultado
        era el contrario al documentado: el open-vocab (semánticamente amplio y
        propenso a falsos positivos) desplazaba al match por plantilla.
        """
        best: dict[tuple, dict] = {}
        for obj in custom_objects:
            key = (obj["label"], obj.get("person_index"))
            prev = best.get(key)
            if prev is None or _source_rank(obj) > _source_rank(prev):
                best[key] = obj
            elif _source_rank(obj) == _source_rank(prev) and float(
                obj.get("confidence") or 0.0
            ) > float(prev.get("confidence") or 0.0):
                best[key] = obj
        return list(best.values())

    def _predict_floor_conf(self) -> float:
        """Conf mínima de ``predict``: la más baja entre persona y custom.

        Ultralytics descarta cajas bajo ``conf`` en el NMS interno. Si usamos
        solo YOLO_CONFIDENCE (p. ej. 0.45), las detecciones custom a 0.15–0.40
        **nunca llegan** a ``_split_detections``.
        """
        floor = min(float(self.confidence_threshold), float(self.custom_confidence))
        # Piso duro para no pedir conf=0 (ruido extremo).
        return max(0.05, floor)

    def _detect_all(self, frame) -> tuple[list[dict], list[dict]]:
        """Personas + custom en un solo predict YOLOE (+ logos ORB)."""
        self._maybe_reload_training()
        self._ensure_loaded()

        persons: list[dict] = []
        custom_objects: list[dict] = []
        hits: list = []

        if self.model is not None:
            self._apply_classes(self._active_class_list())
            # Piso de predict = min(persona, custom); luego se refiltra por tipo.
            hits = self._predict_boxes(frame, self._predict_floor_conf())
            persons, custom_objects = self._split_detections(hits)

        # Logos / recortes en el torso (o ROI de frame si no hay persona).
        for hit in self._detect_logo_templates(frame, persons=persons):
            custom_objects.append(
                {
                    "label": hit["label"],
                    "confidence": hit["confidence"],
                    "box": hit["box"],
                    "source": hit.get("source", "logo_chest"),
                    "person_index": hit.get("person_index"),
                }
            )

        # WAVE-21 (I11): canal adicional con visual prompts (SAVPE) detrás de
        # YOLO_LOGO_VISUAL=1. No reemplaza template+ORB; suma evidencia que
        # compite por prioridad/confianza en `_dedupe_custom`.
        for hit in self._detect_logo_visual(frame, persons=persons):
            custom_objects.append(
                {
                    "label": hit["label"],
                    "confidence": hit["confidence"],
                    "box": hit["box"],
                    "source": hit.get("source", "logo_visual"),
                    "person_index": hit.get("person_index"),
                }
            )

        # `_dedupe_custom` ya resuelve label duplicado priorizando la fuente
        # (logo verificado > open-vocab) y, a igualdad, la confianza.
        custom_objects = self._dedupe_custom(
            self._filter_uniform_objects(custom_objects, persons, frame=frame)
        )

        self._detect_cycles += 1
        debug = _yolo_debug()
        # Log cada ~10 ciclos o si hay detecciones (o debug forzado).
        if debug or self._detect_cycles <= 2 or self._detect_cycles % 10 == 0:
            labels = [o.get("label") for o in custom_objects]
            if not _is_quiet() and (
                debug or persons or custom_objects or self._detect_cycles <= 2
            ):
                print(
                    f"[YOLO] ciclo={self._detect_cycles} "
                    f"hits={len(hits)} persons={len(persons)} "
                    f"custom={labels or '[]'} "
                    f"prompts={self.get_active_prompts()[:8]}… "
                    f"conf_floor={self._predict_floor_conf():.2f}"
                )

        return persons, custom_objects

    # ------------------------------------------------------------------
    # Detection helpers
    # ------------------------------------------------------------------

    def detect_persons_in_frame(self, frame):
        """Lista de personas en *frame* (``confidence``, ``box``).

        Corre siempre: no se omite por sala vacía ni por falta de viewers.
        """
        persons, _ = self._detect_all(frame)
        return persons

    def detect_custom_objects(self, frame):
        """Objetos de clases entrenadas / vocabulario + logos ORB.

        Preferir ``analyze_frame`` en el bucle continuo (un solo predict).
        """
        _, custom = self._detect_all(frame)
        return custom

    def detect_labels(self, frame, labels: list[str], *, conf: float | None = None):
        """Inferencia ad-hoc con prompts temporales (YOLOE ``set_classes``).

        Restaura los prompts del kiosco al terminar. No incluye matching ORB
        de logos (solo open-vocab del modelo).

        Parameters
        ----------
        frame : ndarray
        labels : list[str]
            Prompts temporales (p. ej. ``["botella", "mochila"]``).
        conf : float or None
            Umbral; default ``YOLO_CUSTOM_CONFIDENCE``.
        """
        self._ensure_loaded()
        if self.model is None or not labels:
            return []
        previous_key = self._prompt_key
        # Persona + labels para no perder anclas si el caller las necesita.
        prompts = list(_BASE_PERSON_PROMPTS)
        for lab in labels:
            s = str(lab).strip()
            if s and s not in prompts:
                prompts.append(s)
        try:
            if not self._apply_classes(prompts):
                return []
            thr = self.custom_confidence if conf is None else conf
            hits = self._predict_boxes(frame, thr)
            out: list[dict] = []
            wanted = {str(x).strip().lower() for x in labels}
            for raw_name, confidence, box in hits:
                label = self._map_label(raw_name)
                key = str(label).strip().lower()
                raw_key = str(raw_name).strip().lower()
                if key in wanted or raw_key in wanted or any(
                    w in key or w in raw_key for w in wanted
                ):
                    out.append(
                        {
                            "label": label,
                            "confidence": confidence,
                            "box": box,
                            "raw_label": raw_name,
                            "source": "yoloe_adhoc",
                        }
                    )
            return self._dedupe_custom(out)
        finally:
            # Restaurar prompts del kiosco (persona + Entrenar + vocab).
            if previous_key is not None:
                self._apply_classes(list(previous_key))
            else:
                self._prompt_key = None
                self._apply_classes(self._active_class_list())

    def analyze_frame(self, frame):
        """Personas + custom YOLOE (+ rostros opcional). Un solo predict."""
        persons, custom_objects = self._detect_all(frame)

        analysis = {
            "person_count": len(persons),
            "persons": persons,
            "custom_objects": custom_objects,
            "custom_count": len(custom_objects),
            "model": self.model_name,
            "prompts": self.get_active_prompts(),
            "face_count": None,
            "face_description": None,
        }

        if _env("HOLOGRAM_FACE_ANALYSIS", "0") == "1":
            try:
                if self.face_analyzer is None:
                    from vision.face_analyzer import FaceAnalyzer
                    self.face_analyzer = FaceAnalyzer().load()
                face_result = self.face_analyzer.analyze_frame(frame)
                analysis["face_count"] = face_result["face_count"]
                analysis["face_description"] = face_result["description"]
            except Exception as error:
                analysis["face_description"] = f"Análisis de rostros no disponible: {error}"

        return analysis

    def detect_person_in_frame(self, frame) -> bool:
        """True si hay al menos una persona en *frame*."""
        return len(self.detect_persons_in_frame(frame)) > 0

    def count_persons_in_frame(self, frame) -> int:
        """Número de personas en *frame*."""
        return len(self.detect_persons_in_frame(frame))

    # ------------------------------------------------------------------
    # Single-shot from camera
    # ------------------------------------------------------------------

    def _grab_frame(self, camera_index=None):
        """Abre la cámara un instante y devuelve un frame (o None)."""
        from vision.camera import Camera

        if camera_index is None:
            camera_index = int(_env("HOLOGRAM_CAMERA_INDEX", "0"))
        with Camera(source=camera_index) as cam:
            return cam.read_frame()

    def detect_person_once(self, camera_index=None) -> bool:
        """Abre la cámara, lee un frame y devuelve True si hay persona."""
        frame = self._grab_frame(camera_index)
        if frame is None:
            return False
        return self.detect_person_in_frame(frame)

    def count_persons_once(self, camera_index=None) -> int:
        """Abre la cámara, lee un frame y devuelve el conteo de personas."""
        frame = self._grab_frame(camera_index)
        if frame is None:
            return 0
        return self.count_persons_in_frame(frame)

    def analyze_once(self, camera_index=None) -> dict:
        """Un frame de cámara → ``analyze_frame`` completo (personas + custom)."""
        frame = self._grab_frame(camera_index)
        if frame is None:
            return {
                "person_count": 0,
                "persons": [],
                "custom_objects": [],
                "custom_count": 0,
                "model": self.model_name,
                "prompts": self.get_active_prompts(),
                "face_count": None,
                "face_description": "sin frame",
            }
        return self.analyze_frame(frame)

    # ------------------------------------------------------------------
    # Live annotated frame buffer (MJPEG streaming to the web interface)
    # ------------------------------------------------------------------

    def _draw_overlay(self, frame, analysis):
        """Draw person and custom-object boxes on a copy of *frame*."""
        try:
            import cv2
        except ImportError:
            return frame

        annotated = frame.copy()

        for person in analysis.get("persons", []):
            x1, y1, x2, y2 = (int(v) for v in person["box"])
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (29, 92, 226), 2)
            conf = person.get("confidence", 0.0)
            cv2.putText(
                annotated,
                f"Persona {conf:.0%}",
                (x1, max(0, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (29, 92, 226),
                2,
                cv2.LINE_AA,
            )

        for obj in analysis.get("custom_objects", []):
            x1, y1, x2, y2 = (int(v) for v in obj["box"])
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (60, 200, 90), 2)
            conf = obj.get("confidence", 0.0)
            label = str(obj.get("label", "objeto"))
            cv2.putText(
                annotated,
                f"{label} {conf:.0%}",
                (x1, max(0, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (60, 200, 90),
                2,
                cv2.LINE_AA,
            )

        count = analysis.get("person_count", 0)
        custom_n = analysis.get("custom_count", len(analysis.get("custom_objects") or []))
        header = f"YOLOE | Personas: {count} | Custom: {custom_n}"
        cv2.putText(
            annotated,
            header,
            (10, 24),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
        return annotated

    def _store_annotated_frame(self, frame, analysis):
        """Encode *frame* (with overlay) to JPEG and cache it for streaming."""
        try:
            import cv2
        except ImportError:
            return

        annotated = self._draw_overlay(frame, analysis)
        ok, buffer = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if not ok:
            return
        with self._jpeg_lock:
            self._latest_jpeg = buffer.tobytes()

    def get_latest_jpeg(self):
        """Return the most recent annotated frame as JPEG bytes (or None)."""
        with self._jpeg_lock:
            return self._latest_jpeg

    def feed_subscribe(self):
        """Registra un cliente del feed MJPEG (activa la codificación JPEG)."""
        with self._feed_lock:
            self._feed_subscribers += 1

    def feed_unsubscribe(self):
        """Da de baja un cliente del feed MJPEG (el contador nunca baja de 0).

        Al llegar a cero suscriptores se descarta el último cuadro cacheado: un
        cliente que reconecte no verá un fotograma viejo mientras se genera el
        primero nuevo (verá el placeholder hasta que haya cuadro fresco).
        """
        with self._feed_lock:
            if self._feed_subscribers > 0:
                self._feed_subscribers -= 1
            cleared = self._feed_subscribers == 0
        if cleared:
            with self._jpeg_lock:
                self._latest_jpeg = None

    def has_feed_subscribers(self):
        """¿Hay al menos un cliente viendo el feed anotado?"""
        with self._feed_lock:
            return self._feed_subscribers > 0

    # ------------------------------------------------------------------
    # Continuous detection loop
    # ------------------------------------------------------------------

    def run_continuous(self, callback, camera_index=None, interval_seconds=None):
        """Bucle de detección que llama a *callback(event, count, analysis)*.

        Parameters
        ----------
        callback : callable
            Se invoca con ``(event: str, count: int, analysis: dict)``. Eventos:
            ``"analysis_update"`` (en cada ciclo de detección, para refrescar el
            contexto del LLM), ``"person_entered"``, ``"group_detected"``,
            ``"person_left"`` y ``"custom_object_detected"``.
            ``"person_still_present"`` y ``"no_person"`` se calculan pero NO se
            emiten: solo cambian el estado interno.
        camera_index : int or None
            Camera index (defaults to ``HOLOGRAM_CAMERA_INDEX`` or ``0``).
        interval_seconds : float or None
            Seconds between detection cycles (default ``1.0``).
        """
        from vision.camera import Camera

        if camera_index is None:
            camera_index = int(_env("HOLOGRAM_CAMERA_INDEX", "0"))
        if interval_seconds is None:
            interval_seconds = _env_float("YOLO_INTERVAL_SECONDS", 1.0)

        was_present = False
        last_count = 0
        last_analysis = {"person_count": 0, "persons": [], "custom_objects": []}
        last_detect_time = 0.0

        # Anti-rebote: instante en que la persona dejó de verse. Solo declaramos
        # "person_left" si la ausencia se sostiene, para no cortar la conversación
        # por un cuadro perdido (giro de cabeza, oclusión, parpadeo del detector).
        absent_since = None
        absence_grace = _env_float("PRESENCE_ABSENCE_SECONDS", 5.0)
        # Anti-rebote de ENTRADA, simétrico al de salida: instante del primer
        # cuadro con persona. Solo confirmamos "person_entered"/"group_detected"
        # cuando la presencia se sostiene >= enter_grace, para que un único falso
        # positivo de YOLO (un cuadro suelto) no dispare un saludo. Con 0.0 la
        # entrada es inmediata (comportamiento previo a la Fase 4).
        present_since = None
        enter_grace = _env_float("PRESENCE_ENTER_SECONDS", 0.8)

        print(
            f"[YOLO] Iniciando detección continua local (cámara {camera_index}, "
            f"intervalo {interval_seconds}s, imgsz={self.imgsz})..."
        )

        self._stop_event.clear()
        with Camera(source=camera_index) as cam:
            while not self._stop_event.is_set():
                frame = cam.read_frame()
                if frame is None:
                    self._interruptible_sleep(0.1)
                    continue

                now = time.time()
                # La detección YOLO corre cada *interval_seconds* SIEMPRE
                # (haya o no personas delante de la cámara). No se apaga el
                # modelo por sala vacía: solo se espacia el coste de inferencia.
                # Entre detecciones, con feed activo se reutiliza last_analysis
                # para el overlay MJPEG.
                if now - last_detect_time >= interval_seconds:
                    last_detect_time = now
                    analysis = self.analyze_frame(frame)
                    last_analysis = analysis
                    count = analysis["person_count"]
                    is_present = count > 0
                    event = "no_person"

                    if is_present:
                        absent_since = None  # sigue (o vuelve a estar) presente
                        if not was_present:
                            # Candidato a entrada: arrancar/continuar el temporizador
                            # y confirmar solo cuando la presencia se sostenga.
                            if present_since is None:
                                present_since = now
                            if now - present_since >= enter_grace:
                                event = (
                                    "group_detected" if count > 3 else "person_entered"
                                )
                                was_present = True
                                present_since = None
                        elif count > 3 and last_count <= 3:
                            event = "group_detected"
                        else:
                            event = "person_still_present"
                    elif was_present:
                        # Ausencia: arrancar/continuar el temporizador de gracia y
                        # solo declarar "se fue" cuando se sostenga.
                        if absent_since is None:
                            absent_since = now
                        elif now - absent_since >= absence_grace:
                            event = "person_left"
                            was_present = False
                            absent_since = None
                    else:
                        # Ausencia sin entrada confirmada aún: el candidato no llegó
                        # a sostenerse (rebote), así que se descarta.
                        present_since = None

                    # Siempre empujar el análisis al orquestador (LLM / contexto).
                    # Antes solo se enviaba en entered/left/custom_new: el contexto
                    # se quedaba viejo en "person_still_present" y el LLM no veía
                    # el uniforme aunque YOLOE lo detectara después.
                    callback("analysis_update", count, analysis)

                    if event not in ("no_person", "person_still_present"):
                        callback(event, count, analysis)

                    current_custom_labels = {
                        obj["label"] for obj in analysis.get("custom_objects", [])
                    }
                    # Histéresis M-of-N (I4): un parpadeo de un ciclo ya no
                    # re-dispara "custom_object_detected". El label solo se
                    # declara detectado cuando se ve en N ciclos consecutivos
                    # (confirm_cycles, default 2) y se olvida tras
                    # forget_seconds de ausencia sostenida (default 10 s).
                    track_events = self._label_tracker.update(
                        current_custom_labels, now=now
                    )
                    confirmed_labels = {
                        e["label"]
                        for e in track_events
                        if e["event"] == "detected"
                    }
                    if confirmed_labels:
                        callback("custom_object_detected", len(confirmed_labels), analysis)

                    # `was_present` lo gestiona la máquina de estados de arriba
                    # (entrada -> True; salida solo cuando la ausencia supera el
                    # período de gracia). NO lo reasignamos aquí: hacerlo
                    # (was_present = is_present) anulaba la gracia y un parpadeo de
                    # YOLO re-disparaba "person_entered" -> la cámara volvía a
                    # saludar a la misma persona.
                    # `last_count` solo se actualiza con presencia real para que un
                    # cuadro perdido no reinicie la base de tamaño de grupo.
                    if is_present:
                        last_count = count

                    # I6/I7: overlay de tracks de persona (solo con YOLO_REID=1).
                    # La máquina was_present/present_since/absent_since de arriba
                    # queda intacta; aquí solo se superpone el estado de tracks y,
                    # cuando el conjunto de tracks confirmados cambia por completo
                    # sin que person_count llegue a 0, se emite person_left +
                    # person_entered en vez de continuar la misma presencia en
                    # silencio. Con YOLO_REID=0 este bloque es un no-op.
                    if self._reid_enabled and self._person_associator is not None:
                        self._reid_events = self._reid_track(
                            analysis,
                            count,
                            now,
                        )
                    else:
                        self._reid_events = []
                    for reid_event, reid_analysis in self._reid_events:
                        callback(reid_event, count, reid_analysis)

                # Publica el cuadro anotado SOLO si alguien mira el feed MJPEG.
                # Sin suscriptores nos saltamos el imencode; la detección sigue
                # al ritmo de *interval_seconds* aunque la sala esté vacía.
                if self.has_feed_subscribers():
                    self._store_annotated_frame(frame, last_analysis)
                    # ~25–30 fps de captura/encode mientras alguien mira el feed.
                    self._interruptible_sleep(0.03)
                elif interval_seconds > 0:
                    # Sin viewers: no girar a 30 fps. Dormir hasta la próxima
                    # ventana de detección (el modelo no se apaga; solo espera).
                    # Usar `now` (no un time() extra) mantiene tests deterministas
                    # que monopatanean time.time() por iteración.
                    remaining = interval_seconds - (now - last_detect_time)
                    self._interruptible_sleep(
                        remaining if remaining > 0 else interval_seconds
                    )
                else:
                    # interval 0 = cada cuadro (tests / modo máximo).
                    self._interruptible_sleep(0.0)

    # ------------------------------------------------------------------
    # I6/I7: overlay de tracks de persona (REID, detrás de YOLO_REID=1)
    # ------------------------------------------------------------------

    def _reid_track(self, analysis: dict, count: int, now: float) -> list[tuple]:
        """Alimenta el asociador con las detecciones del ciclo y decide el evento.

        Solo se llama con ``self._reid_enabled`` y un ``_person_associator``
        vivo. Devuelve eventos ``(event, extra_analysis)`` del overlay:
        cuando el conjunto de tracks confirmados cambia por completo sin que
        ``count`` llegue a 0, emite ``person_left`` + ``person_entered`` para
        no continuar la misma presencia en silencio con identidades nuevas.
        """
        events: list[tuple] = []
        associator = self._person_associator
        detections = self._person_detections_from_analysis(analysis)
        associator.update(detections, now=now)
        confirmed_now = set(associator.confirmed())
        prev_confirmed = self._reid_prev_confirmed
        self._reid_prev_confirmed = confirmed_now
        if (
            prev_confirmed
            and count > 0
            and confirmed_now
            and not confirmed_now.intersection(prev_confirmed)
        ):
            events.append(("person_left", analysis))
            events.append(("person_entered", analysis))
        return events

    def _person_detections_from_analysis(self, analysis: dict) -> list[dict]:
        """Detecciones de persona del análisis, con descriptor si disponible.

        El canal de apariencia (I5) se adjunta por IoU de caja: los tracks del
        asociador se emparejan por geometría aunque el fixture no traiga
        máscara (descriptor None → apariencia descartada, solo geometría).
        """
        sigs_by_box: list[dict] = list(self._last_person_signatures)
        out: list[dict] = []
        for person in analysis.get("persons", []):
            box = tuple(person.get("box") or ())
            sig = None
            for s in sigs_by_box:
                if self._boxes_intersect(box, tuple(s.get("box") or ()), overlap=0.5):
                    sig = s.get("signature")
                    break
            out.append(
                {
                    "box": box,
                    "confidence": float(person.get("confidence", 0.5)),
                    "signature": sig,
                }
            )
        return out

    @staticmethod
    def _boxes_intersect(a: tuple, b: tuple, overlap: float = 0.5) -> bool:
        """True si la caja ``b`` solapa lo suficiente con ``a`` (IoU >= overlap)."""
        if not a or not b or len(a) != 4 or len(b) != 4:
            return False
        ax1, ay1, ax2, ay2 = a
        bx1, by1, bx2, by2 = b
        ix1, iy1 = max(ax1, bx1), max(ay1, by1)
        ix2, iy2 = min(ax2, bx2), min(ay2, by2)
        iw, ih = ix2 - ix1, iy2 - iy1
        if iw <= 0 or ih <= 0:
            return False
        inter = iw * ih
        union = (ax2 - ax1) * (ay2 - ay1) + (bx2 - bx1) * (by2 - by1) - inter
        if union <= 0:
            return False
        return (inter / union) >= overlap

    # ------------------------------------------------------------------
    # Availability check
    # ------------------------------------------------------------------

    @staticmethod
    def is_available() -> bool:
        """True si OpenCV y Ultralytics YOLOE están instalados."""
        try:
            import cv2  # noqa: F401
            from ultralytics import YOLOE  # noqa: F401

            return True
        except ImportError:
            return False

    @staticmethod
    def default_weights() -> str:
        """Nombre canónico del checkpoint del kiosco."""
        return DEFAULT_YOLOE_WEIGHTS
