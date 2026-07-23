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

from utils import _env, _env_float, _env_int, _is_quiet

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
        "yellow embroidered logo on blue polo",
        "ITEE school logo on chest",
        "blue polo with yellow ITEE badge",
        "yellow logo badge on blue uniform",
        "ITEE uniform",
        "uniforme ITEE",
        # Solo para mapear salidas del modelo → etiqueta operador.
        # El post-filtro de estructura (amarillo+azul) evita FP de camisas genéricas.
        "school uniform",
        "student uniform",
    ),
    "uniforme": (
        "school uniform with logo badge",
        "student uniform embroidered logo",
        "school uniform",
    ),
}

# Open-vocab de etiquetas con fotos en Entrenar: umbral alto; la aceptación
# final la da el match con la imagen de referencia (no el color).
_LOGO_OPEN_VOCAB_MIN_CONF = 0.45

# --- Logos de Entrenar (cualquier colegio / etiqueta) ---
#
# Fuente de verdad: fotos de ``data/training_metadata.json`` (+ crop x,y,w,h).
# Matching: template multi-escala (TM_CCOEFF_NORMED) + ORB.
# NO se usa color (amarillo/azul): ITEE es un caso; luego habrá otros colegios.
#
# Open-vocab YOLOE solo sugiere; sin match a la plantilla de Entrenar no cuenta
# como esa etiqueta. El cuello/placket se evita con geometría de ROI pecho.
_ORB_MIN_GOOD_MATCHES = 14
_ORB_RATIO = 0.75
_TMPL_MATCH_MIN = 0.62
#
# Geometría del logo relativa a la caja persona (YOLO), fracciones 0=arriba/izq:
#
#   y ∈ [0.36, 0.58]  → pecho (bajo cuello; el placket suele estar en y<0.34)
#   x ∈ [0.08, 0.48]  → pecho izquierdo en imagen del kiosco
#   YOLO_LOGO_MIRROR=1 si el logo sale al otro lado (cámara espejo).
#
# Cualquier detección con centro en y < COLLAR_Y_MAX se considera cuello y se
# descarta (aunque diga «Uniforme ITEE» al 90 %).
_LOGO_Y0 = 0.36
_LOGO_Y1 = 0.58
_LOGO_X0, _LOGO_X1 = 0.08, 0.48
_COLLAR_Y_MAX = 0.34  # por encima = cuello / placket / cara


def _logo_roi_fractions() -> tuple[float, float, float, float]:
    """(y0, y1, x0, x1) del ROI logo en fracciones de la caja persona.

    Vertical = pecho bajo el cuello. Horizontal = lado del logo bordado.
    """
    y0 = _env_float("YOLO_LOGO_Y0", _LOGO_Y0)
    y1 = _env_float("YOLO_LOGO_Y1", _LOGO_Y1)
    x0 = _env_float("YOLO_LOGO_X0", _LOGO_X0)
    x1 = _env_float("YOLO_LOGO_X1", _LOGO_X1)
    if os.getenv("YOLO_LOGO_MIRROR", "0").lower() in ("1", "true", "yes"):
        x0, x1 = 1.0 - x1, 1.0 - x0
    # Clamp: nunca subir el ROI al cuello (y0 >= collar).
    collar = _env_float("YOLO_COLLAR_Y_MAX", _COLLAR_Y_MAX)
    y0 = max(collar + 0.02, min(0.70, y0))
    y1 = max(y0 + 0.10, min(0.85, y1))
    x0 = max(0.0, min(0.80, x0))
    x1 = max(x0 + 0.12, min(1.0, x1))
    return y0, y1, x0, x1


def _collar_y_max() -> float:
    return max(0.20, min(0.45, _env_float("YOLO_COLLAR_Y_MAX", _COLLAR_Y_MAX)))


def _xyxy_tuple(xyxy) -> tuple[float, float, float, float]:
    """Normaliza `box.xyxy[0]` de Ultralytics (tensor) o de fakes de test (list)."""
    if hasattr(xyxy, "tolist"):
        vals = xyxy.tolist()
    else:
        vals = list(xyxy)
    return float(vals[0]), float(vals[1]), float(vals[2]), float(vals[3])


def _compute_scale_back(frame, prepared) -> float:
    """Factor para reescalar cajas del frame reducido al frame original."""
    scale_back = 1.0
    if prepared is not frame and prepared is not None and frame is not None:
        try:
            scale_back = frame.shape[1] / float(prepared.shape[1])
        except Exception:
            scale_back = 1.0
    return scale_back


def _scale_box(box, scale_back) -> tuple[float, float, float, float]:
    """Reescala una caja ``(x1, y1, x2, y2)`` si ``scale_back != 1.0``."""
    x1, y1, x2, y2 = box
    if scale_back != 1.0:
        return (x1 * scale_back, y1 * scale_back, x2 * scale_back, y2 * scale_back)
    return box


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
        return crop if crop.size else img

    def _rebuild_logo_templates(self) -> None:
        """Indexa fotos de Entrenar como plantillas grises + descriptores ORB.

        Optimización de memoria/CPU:
        - Una sola plantilla uint8 gris por foto (max lado ~128), no 7 escalas.
          ``matchTemplate`` ya reescala al tamaño del ROI en runtime.
        - ORB sobre la misma miniatura (~160 px).
        - Opcional: caché ``data/logo_index.npz`` para no releer JPEGs cada reload.
        """
        self._logo_templates = {}
        self._logo_images = {}
        base = Path(__file__).resolve().parent.parent
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

        meta_sig = f"{meta_path.stat().st_mtime_ns}:{meta_path.stat().st_size}"
        # Caché: si el metadata no cambió, cargar arrays ya preparados.
        try:
            if cache_path.is_file():
                cached = np.load(str(cache_path), allow_pickle=True)
                sig = cached["meta_sig"]
                sig_s = str(sig.item() if hasattr(sig, "item") else sig)
                if sig_s == meta_sig:
                    by_img = dict(cached["by_img"].item())
                    by_des = dict(cached["by_des"].item())
                    self._logo_images = by_img
                    self._logo_templates = by_des
                    n_img = sum(len(v) for v in by_img.values())
                    n_orb = sum(len(v) for v in by_des.values())
                    mem = sum(g.nbytes for imgs in by_img.values() for g in imgs)
                    mem += sum(d.nbytes for dess in by_des.values() for d in dess)
                    print(
                        f"[YOLO] Logos Entrenar (caché npz): "
                        f"plantillas={n_img} ORB={n_orb} "
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

            # --- 1 plantilla gris compacta (no pirámide de 7 tamaños) ---
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
                    by_img=np.asarray(by_img, dtype=object),
                    by_des=np.asarray(by_des, dtype=object),
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

    def _point_in_logo_zone(
        self, cx: float, cy: float, person_box: tuple, tol: float = 0.04
    ) -> bool:
        """True si el centro (cx,cy) cae en el pecho-logo de la persona."""
        px1, py1, px2, py2 = person_box
        p_h = max(1.0, py2 - py1)
        p_w = max(1.0, px2 - px1)
        rel_y = (cy - py1) / p_h
        rel_x = (cx - px1) / p_w
        # Cuello / placket amarillo: nunca es el logo ITEE.
        if rel_y < _collar_y_max() - tol * 0.5:
            return False
        y0r, y1r, x0r, x1r = _logo_roi_fractions()
        if rel_y < y0r - tol or rel_y > y1r + tol:
            return False
        if rel_x < x0r - tol or rel_x > x1r + tol:
            return False
        return True

    @staticmethod
    def _rel_center_on_person(
        box: tuple, person_box: tuple
    ) -> tuple[float, float] | None:
        """Centro de ``box`` en fracciones 0–1 respecto a la caja persona."""
        if not box or not person_box or len(box) < 4 or len(person_box) < 4:
            return None
        px1, py1, px2, py2 = [float(v) for v in person_box]
        p_h = max(1.0, py2 - py1)
        p_w = max(1.0, px2 - px1)
        cx = 0.5 * (float(box[0]) + float(box[2]))
        cy = 0.5 * (float(box[1]) + float(box[3]))
        return (cx - px1) / p_w, (cy - py1) / p_h

    def _snap_box_to_logo_zone(
        self, box: tuple, person_box: tuple
    ) -> tuple[float, float, float, float]:
        """Recorta/mueve la caja open-vocab al ROI pecho-logo (evita dibujar en el cuello)."""
        px1, py1, px2, py2 = [float(v) for v in person_box]
        p_h = max(1.0, py2 - py1)
        p_w = max(1.0, px2 - px1)
        y0r, y1r, x0r, x1r = _logo_roi_fractions()
        zx1 = px1 + x0r * p_w
        zx2 = px1 + x1r * p_w
        zy1 = py1 + y0r * p_h
        zy2 = py1 + y1r * p_h
        # Intersección box ∩ zona logo; si no hay solape, caja centrada en la zona.
        bx1, by1, bx2, by2 = [float(v) for v in box]
        ix1, iy1 = max(bx1, zx1), max(by1, zy1)
        ix2, iy2 = min(bx2, zx2), min(by2, zy2)
        if ix2 - ix1 >= 12 and iy2 - iy1 >= 12:
            return (ix1, iy1, ix2, iy2)
        # Sin solape útil: ancla al centro de la zona logo (~tamaño del logo).
        cw = max(28.0, 0.35 * (zx2 - zx1))
        ch = max(28.0, 0.45 * (zy2 - zy1))
        cx = 0.5 * (zx1 + zx2)
        cy = 0.5 * (zy1 + zy2)
        return (cx - cw * 0.5, cy - ch * 0.5, cx + cw * 0.5, cy + ch * 0.5)

    def _best_person_for_box(
        self, box: tuple, persons: list[dict]
    ) -> tuple | None:
        """Caja persona que contiene el centro de ``box``, o la de mayor solape."""
        if not box or not persons:
            return None
        cx = 0.5 * (float(box[0]) + float(box[2]))
        cy = 0.5 * (float(box[1]) + float(box[3]))
        best = None
        best_area = -1.0
        for p in persons:
            pb = p.get("box")
            if not pb or len(pb) < 4:
                continue
            px1, py1, px2, py2 = [float(v) for v in pb]
            if px1 <= cx <= px2 and py1 <= cy <= py2:
                area = (px2 - px1) * (py2 - py1)
                if area > best_area:
                    best_area = area
                    best = (px1, py1, px2, py2)
        if best is not None:
            return best
        # Sin contención: la persona más cercana por centro
        best_d = None
        for p in persons:
            pb = p.get("box")
            if not pb or len(pb) < 4:
                continue
            px1, py1, px2, py2 = [float(v) for v in pb]
            pcx = 0.5 * (px1 + px2)
            pcy = 0.5 * (py1 + py2)
            d = (pcx - cx) ** 2 + (pcy - cy) ** 2
            if best_d is None or d < best_d:
                best_d = d
                best = (px1, py1, px2, py2)
        return best

    def _is_uniform_label(self, label: str) -> bool:
        """Compat: true si el nombre sugiere uniforme (UI/tests)."""
        key = str(label or "").strip().lower()
        return "uniforme" in key or "itee" in key

    def _is_logo_trained_label(self, label: str) -> bool:
        """True si hay imágenes de Entrenar (plantilla/ORB) para esta etiqueta."""
        if not label:
            return False
        if label in self._logo_images or label in self._logo_templates:
            return True
        key = label.strip().lower()
        for k in list(self._logo_images.keys()) + list(self._logo_templates.keys()):
            if str(k).strip().lower() == key:
                return True
        return False

    def _logo_templates_for(self, label: str) -> list:
        if label in self._logo_images:
            return self._logo_images[label]
        key = label.strip().lower()
        for k, v in self._logo_images.items():
            if str(k).strip().lower() == key:
                return v
        return []

    def _logo_orb_for(self, label: str) -> list:
        if label in self._logo_templates:
            return self._logo_templates[label]
        key = label.strip().lower()
        for k, v in self._logo_templates.items():
            if str(k).strip().lower() == key:
                return v
        return []

    def _match_template_multiscale(
        self, gray_roi, templates: list
    ) -> tuple[float, tuple | None]:
        """Mejor score TM_CCOEFF_NORMED vs plantillas de Entrenar (multi-escala)."""
        try:
            import cv2
        except ImportError:
            return 0.0, None
        if gray_roi is None or gray_roi.size == 0 or not templates:
            return 0.0, None
        try:
            import numpy as np

            if float(np.std(gray_roi)) < 4.0:
                # ROI plano (negro/blanco): no hay textura que matchear.
                return 0.0, None
        except Exception:
            pass
        try:
            gray_roi = cv2.equalizeHist(gray_roi)
        except Exception:
            pass
        rh, rw = gray_roi.shape[:2]
        best_score = 0.0
        best_box = None
        # Escalas relativas al ancho del ROI pecho (menos pasos = más rápido;
        # una sola plantilla uint8 se reescala aquí, no se guardan 7 copias).
        rels = (0.14, 0.20, 0.28, 0.38, 0.50)
        for tmpl in templates:
            th0, tw0 = tmpl.shape[:2]
            if tw0 < 8 or th0 < 8:
                continue
            try:
                import numpy as np

                # Plantilla casi constante (p. ej. tests) → TM_CCOEFF_NORMED inestable.
                if float(np.std(tmpl)) < 8.0:
                    continue
            except Exception:
                pass
            aspect = th0 / float(tw0)
            for rel in rels:
                sw = max(16, int(rw * rel))
                sh = max(16, int(sw * aspect))
                if sw >= rw - 2 or sh >= rh - 2:
                    continue
                try:
                    resized = cv2.resize(tmpl, (sw, sh), interpolation=cv2.INTER_AREA)
                    res = cv2.matchTemplate(gray_roi, resized, cv2.TM_CCOEFF_NORMED)
                    _mn, mx, _ml, max_loc = cv2.minMaxLoc(res)
                except Exception:
                    continue
                if mx > best_score:
                    best_score = float(mx)
                    x, y = int(max_loc[0]), int(max_loc[1])
                    best_box = (float(x), float(y), float(x + sw), float(y + sh))
        return best_score, best_box

    def _match_orb_in_roi(self, gray_roi, des_list: list) -> float:
        """Score 0–1 por coincidencias ORB con descriptores de Entrenar."""
        try:
            import cv2
        except ImportError:
            return 0.0
        if gray_roi is None or gray_roi.size == 0 or not des_list:
            return 0.0
        try:
            gray_roi = cv2.equalizeHist(gray_roi)
        except Exception:
            pass
        try:
            orb = cv2.ORB_create(700)
            _kp, des = orb.detectAndCompute(gray_roi, None)
        except Exception:
            return 0.0
        if des is None or len(des) < 6:
            return 0.0
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        best_good = 0
        for ref_des in des_list:
            if ref_des is None or len(ref_des) < 4:
                continue
            try:
                pairs = bf.knnMatch(ref_des, des, k=2)
            except Exception:
                continue
            good = 0
            for pair in pairs:
                if len(pair) < 2:
                    continue
                m, n = pair
                if m.distance < _ORB_RATIO * n.distance:
                    good += 1
            if good > best_good:
                best_good = good
        if best_good <= 0:
            return 0.0
        # Normalizar: ~ORB_MIN_GOOD_MATCHES → score ~1.
        return min(1.0, best_good / float(max(8, _ORB_MIN_GOOD_MATCHES)))

    def _match_logo_in_gray(
        self, gray_roi, label: str
    ) -> tuple[float, tuple | None, str]:
        """Match plantilla+ORB de ``label`` en un ROI gris. → (score, box_rel, method)."""
        imgs = self._logo_templates_for(label)
        des_list = self._logo_orb_for(label)
        tmpl_score, tmpl_box = self._match_template_multiscale(gray_roi, imgs)
        orb_score = self._match_orb_in_roi(gray_roi, des_list)
        # Combinar: template manda en localización; ORB refuerza confianza.
        if tmpl_box is not None and tmpl_score >= _env_float(
            "YOLO_LOGO_TMPL_MIN", _TMPL_MATCH_MIN
        ) * 0.90:
            conf = min(0.98, 0.75 * tmpl_score + 0.25 * orb_score)
            return conf, tmpl_box, "template"
        if orb_score >= 0.85 and tmpl_box is not None:
            conf = min(0.95, 0.55 * tmpl_score + 0.45 * orb_score)
            return conf, tmpl_box, "orb+template"
        if orb_score >= 0.95:
            # Solo ORB fuerte: caja = centro del ROI (sin localización fina).
            rh, rw = gray_roi.shape[:2]
            s = min(rw, rh) * 0.35
            cx, cy = rw * 0.5, rh * 0.5
            box = (cx - s * 0.5, cy - s * 0.5, cx + s * 0.5, cy + s * 0.5)
            return orb_score, box, "orb"
        return 0.0, None, "none"

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
        try:
            import cv2
        except ImportError:
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
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        score, rel_box, _method = self._match_logo_in_gray(gray, label)
        tmpl_min = _env_float("YOLO_LOGO_TMPL_MIN", _TMPL_MATCH_MIN)
        if score < tmpl_min * 0.92 or rel_box is None:
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
        """
        if frame is None:
            return []
        if not self._logo_images and not self._logo_templates:
            return []
        try:
            import cv2
        except ImportError:
            return []

        persons = persons or []
        if not persons:
            try:
                h, w = frame.shape[:2]
            except Exception:
                return []
            if h < 32 or w < 32:
                return []
            persons = [
                {
                    "box": (w * 0.18, h * 0.08, w * 0.82, h * 0.98),
                    "confidence": 0.0,
                }
            ]

        rois = self._person_chest_rois(frame, persons)
        if not rois:
            return []

        found: list[dict] = []
        tmpl_min = _env_float("YOLO_LOGO_TMPL_MIN", _TMPL_MATCH_MIN)
        debug = os.getenv("HOLOGRAM_YOLO_DEBUG", "0").lower() in ("1", "true", "yes")
        labels = set(self._logo_images) | set(self._logo_templates)

        for label in labels:
            best_conf = 0.0
            best_box_frame = None
            best_detail = ""

            for crop, (ox1, oy1, ox2, oy2), person_box in rois:
                gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
                score, rel_box, method = self._match_logo_in_gray(gray, label)
                if rel_box is None or score < tmpl_min * 0.90:
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
                best_box_frame = (fx1, fy1, fx2, fy2)
                best_detail = f"{method} score={score:.2f}"

            accept = best_conf >= tmpl_min * 0.92 and best_box_frame is not None
            if debug and (accept or best_conf >= 0.45):
                print(
                    f"[YOLO] Logo ref «{label}» conf={best_conf:.2f} "
                    f"({best_detail}) accept={accept}"
                )
            if not accept:
                continue
            found.append(
                {
                    "label": label,
                    "confidence": float(best_conf),
                    "box": best_box_frame,
                    "source": "logo_ref",
                }
            )
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
        out: list[tuple[str, float, tuple]] = []
        for result in results:
            names = getattr(result, "names", None) or {}
            boxes = getattr(result, "boxes", None)
            if boxes is None:
                continue
            for box in boxes:
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
                out.append((raw_name, confidence, (x1, y1, x2, y2)))
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
        debug = os.getenv("HOLOGRAM_YOLO_DEBUG", "0").lower() in (
            "1",
            "true",
            "yes",
        )
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
            filtered.append(
                {
                    **obj,
                    "box": refined or search_box,
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
        """Una entrada por label (mejor confianza)."""
        best: dict[str, dict] = {}
        for obj in custom_objects:
            lab = obj["label"]
            prev = best.get(lab)
            if prev is None or obj["confidence"] > prev["confidence"]:
                best[lab] = obj
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
                }
            )

        custom_objects = self._dedupe_custom(
            self._filter_uniform_objects(custom_objects, persons, frame=frame)
        )
        # Preferir match por imagen de referencia sobre open-vocab del mismo label.
        _logo_pref = ("logo_ref", "logo_ref_verified", "logo_chest")
        by_src: dict[str, dict] = {}
        for obj in custom_objects:
            lab = obj.get("label", "")
            src = obj.get("source") or ""
            prev = by_src.get(lab)
            if prev is None:
                by_src[lab] = obj
                continue
            prev_src = prev.get("source") or ""
            if src in _logo_pref and prev_src not in _logo_pref:
                by_src[lab] = obj
            elif prev_src in _logo_pref and src not in _logo_pref:
                pass
            elif float(obj.get("confidence") or 0) > float(
                prev.get("confidence") or 0
            ):
                by_src[lab] = obj
        custom_objects = list(by_src.values())

        self._detect_cycles += 1
        debug = os.getenv("HOLOGRAM_YOLO_DEBUG", "0").lower() in (
            "1",
            "true",
            "yes",
        )
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
        """Run a detection loop calling *callback(event, count)* on changes.

        Parameters
        ----------
        callback : callable
            Called with ``(event: str, count: int)`` where event is one of
            ``"person_entered"``, ``"person_still_present"``,
            ``"group_detected"``, ``"person_left"``, or ``"no_person"``.
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
        last_custom_labels: set[str] = set()
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
                    new_labels = current_custom_labels - last_custom_labels
                    if new_labels:
                        callback("custom_object_detected", len(new_labels), analysis)

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
                    last_custom_labels = current_custom_labels

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
