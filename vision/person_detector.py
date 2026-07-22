"""
Detector de visión del holograma UNEV: un solo modelo open-vocab YOLOE.

Por defecto ``yoloe-26n-seg.pt``: personas + objetos personalizados (etiquetas
de la pantalla Entrenar / open_vocabulary) en **una** inferencia por ciclo.

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


def _is_quiet_yolo() -> bool:
    return _is_quiet()

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

# Siempre se piden en set_classes (presencia del kiosco).
_BASE_PERSON_PROMPTS: tuple[str, ...] = ("person", "persona")

# Sinónimos en inglés (y variantes) para zero-shot open-vocab. Clave = etiqueta
# del operador en minúsculas; valor = prompts extra que el modelo open-vocab entiende.
_OPEN_VOCAB_ALIASES: dict[str, tuple[str, ...]] = {
    "uniforme itee": (
        "school uniform",
        "blue polo shirt",
        "blue school polo",
        "ITEE logo",
        "yellow logo on blue shirt",
        "blue uniform shirt",
        "school polo shirt",
        "student blue polo",
        "student uniform",
        "uniforme escolar",
        "uniforme escolar azul",
        "polo azul",
        "blue shirt",
    ),
    "uniforme": (
        "school uniform",
        "student uniform",
        "uniforme escolar",
        "polo shirt",
    ),
}

# --- Detección de uniforme ITEE (logo bordado) ---
#
# Señales fiables del polo ITEE (no del color azul solo):
#   1) Zona espacial: pecho, BAJO el cuello (no hombro/cara).
#   2) Estructura del logo: bordado AMARILLO sobre tela AZUL en la misma zona.
#   3) Template del logo solo como apoyo, y solo DENTRO de esa zona pecho.
# El azul del hombro/manga sin hilo amarillo NUNCA cuenta como uniforme.
_ORB_MIN_GOOD_MATCHES = 18
_ORB_RATIO = 0.72
_TMPL_MATCH_MIN = 0.68
#
# Geometría del logo relativa a la caja persona (YOLO):
#
#   Cabeza: 0 → HEAD_END. Cuello termina en HEAD_END + HEAD_NECK.
#   Distancia cabeza→cuello = HEAD_NECK (~0.09 de la altura de la persona).
#   Logo: esa distancia DUPLICADA por debajo del final de la cabeza
#     y0 = HEAD_END + 2·HEAD_NECK
#     y1 = y0 + 2·HEAD_NECK   (misma “altura” que el offset)
#   → con defaults: y ≈ 0.46–0.64 (pecho, nunca cuello/cara).
#
#   Horizontal: mitad IZQUIERDA de la caja (donde está el logo en la
#   imagen del kiosco). Si la cámara no va en espejo y el logo sale a la
#   derecha, poner YOLO_LOGO_MIRROR=1.
_LOGO_HEAD_END = 0.28
_LOGO_HEAD_NECK = 0.09  # distancia cabeza→cuello (fracción de altura persona)
_LOGO_X0, _LOGO_X1 = 0.12, 0.52  # pecho izquierdo en imagen (lado del logo)


def _logo_roi_fractions() -> tuple[float, float, float, float]:
    """(y0, y1, x0, x1) del ROI logo en fracciones de la caja persona.

    Vertical = cuello + 2×(cabeza→cuello). Horizontal = pecho del logo.
    """
    head_end = _env_float("YOLO_LOGO_HEAD_END", _LOGO_HEAD_END)
    head_neck = _env_float("YOLO_LOGO_HEAD_NECK", _LOGO_HEAD_NECK)
    head_neck = max(0.04, min(0.20, head_neck))
    head_end = max(0.12, min(0.45, head_end))
    # Distancia cabeza→cuello duplicada bajo la cabeza → centro del pecho-logo.
    y0 = head_end + 2.0 * head_neck
    y1 = y0 + 2.0 * head_neck
    # Overrides opcionales de banda completa (compat).
    y0 = _env_float("YOLO_LOGO_Y0", y0)
    y1 = _env_float("YOLO_LOGO_Y1", y1)
    x0 = _env_float("YOLO_LOGO_X0", _LOGO_X0)
    x1 = _env_float("YOLO_LOGO_X1", _LOGO_X1)
    if os.getenv("YOLO_LOGO_MIRROR", "0").lower() in ("1", "true", "yes"):
        x0, x1 = 1.0 - x1, 1.0 - x0
    # Clamp sensato
    y0 = max(0.30, min(0.75, y0))
    y1 = max(y0 + 0.08, min(0.90, y1))
    x0 = max(0.0, min(0.85, x0))
    x1 = max(x0 + 0.10, min(1.0, x1))
    return y0, y1, x0, x1


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
    """Visión del kiosco: personas (COCO) + custom (open-vocab + logos Entrenar).

    * **Personas:** ``YOLO_PERSON_MODEL`` (default ``yolo26n.pt``) — fiable.
    * **Clases de Entrenar / vocabulario:** open-vocab (``YOLO_MODEL``, p. ej.
      ``yolov8s-world.pt`` o ``yoloe-26n-seg.pt``) **más** matching ORB de las
      fotos de ``training_metadata`` (logos/close-ups que YOLO no ve como objetos).

    Parameters
    ----------
    model_name : str
        Pesos open-vocab (``YOLO_MODEL``). Default ``yolov8s-world.pt``.
    confidence_threshold : float
        Umbral de confianza (personas y open-vocab). Custom open-vocab usa
        además ``YOLO_CUSTOM_CONFIDENCE`` (más bajo por defecto).
    """

    def __init__(self, model_name=None, confidence_threshold=None):
        # Open-vocab (custom). YOLO-World es más fiable con set_classes que YOLOE-26
        # en CPU sin MobileCLIP bien cableado; se puede forzar yoloe vía env.
        self.model_name = model_name or _env("YOLO_MODEL", "yolov8s-world.pt")
        self.person_model_name = _env("YOLO_PERSON_MODEL", "yolo26n.pt")
        self.confidence_threshold = confidence_threshold or _env_float(
            "YOLO_CONFIDENCE", 0.45
        )
        self.custom_confidence = _env_float("YOLO_CUSTOM_CONFIDENCE", 0.18)
        # Tamaño de entrada Ultralytics (menor = más rápido). 320 es un buen
        # equilibrio para kiosco CPU; 640 si hay GPU y se quiere más detalle.
        self.imgsz = _env_int("YOLO_IMGSZ", 320)
        # device vacío = auto de Ultralytics; "cpu", "0", "cuda:0", etc.
        self.device = _env("YOLO_DEVICE", "").strip() or None
        self.half = _env("YOLO_HALF", "0").lower() in ("1", "true", "yes")
        # Lado máximo del frame antes de predecir (ahorra copias si la cámara
        # entrega 1080p). 0 = no redimensionar en software (solo imgsz del modelo).
        self.max_side = _env_int("YOLO_MAX_SIDE", 640)
        # model = open-vocab (tests lo mockean); _person_model = COCO personas.
        self.model = None
        self._person_model = None
        self.face_analyzer = None
        self._custom_classes: list[str] = []
        self._custom_vocabulary: list[str] = []
        # Última lista pasada a set_classes (evita re-encodar el texto cada ciclo).
        self._prompt_key: tuple[str, ...] | None = None
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

    def _load_one_weights(self, name: str, *, open_vocab: bool):
        """Carga un checkpoint Ultralytics (YOLO / YOLOE / YOLOWorld)."""
        from ultralytics import YOLO

        path = self._resolve_weights_path(name)
        load_arg = str(path) if path.exists() else name
        lower = name.lower()
        if open_vocab:
            if "yoloe" in lower:
                try:
                    from ultralytics import YOLOE

                    return YOLOE(load_arg)
                except Exception as err:
                    print(f"[YOLO] YOLOE falló ({err}); probando YOLO-World...")
                    name = "yolov8s-world.pt"
                    path = self._resolve_weights_path(name)
                    load_arg = str(path) if path.exists() else name
                    lower = name.lower()
            if "world" in lower:
                try:
                    from ultralytics import YOLOWorld

                    return YOLOWorld(load_arg)
                except Exception:
                    return YOLO(load_arg)
        return YOLO(load_arg)

    def load(self):
        """Carga modelo de personas + open-vocab. Descarga pesos si hace falta."""
        # 1) Personas (COCO) — prioritario para el kiosco.
        try:
            print(f"[YOLO] Cargando detector de personas: {self.person_model_name}...")
            self._person_model = self._load_one_weights(
                self.person_model_name, open_vocab=False
            )
            print(f"[YOLO] Personas listo ({type(self._person_model).__name__})")
        except Exception as error:
            print(f"[YOLO] ERROR cargando personas ({error})")
            self._person_model = None

        # 2) Open-vocab para clases de Entrenar / vocabulario.
        try:
            print(f"[YOLO] Cargando open-vocab custom: {self.model_name}...")
            self.model = self._load_one_weights(self.model_name, open_vocab=True)
            print(f"[YOLO] Open-vocab listo ({type(self.model).__name__}): {self.model_name}")
            self._apply_classes(self._active_class_list())
        except Exception as error:
            print(f"[YOLO] ERROR open-vocab ({error}); custom solo por logos Entrenar.")
            self.model = None

        # Si no hay person model, reutilizar open-vocab también para personas.
        if self._person_model is None and self.model is not None:
            self._person_model = self.model
            print("[YOLO] Sin yolo26n: personas saldrán del modelo open-vocab.")

        self._rebuild_logo_templates()
        return self

    def _ensure_loaded(self):
        """Load models if they haven't been loaded yet."""
        if self._person_model is None and self.model is None:
            self.load()

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
        """Prompts open-vocab: custom (+ persona solo si no hay modelo COCO aparte)."""
        terms: list[str] = []
        # Si personas van por yolo26n, no mezclar person en open-vocab (más limpio).
        if self._person_model is None or self._person_model is self.model:
            terms.extend(_BASE_PERSON_PROMPTS)
        for t in self._custom_class_list():
            if t not in terms:
                terms.append(t)
        # Sin custom y sin person en la lista, open-vocab no tiene nada que hacer.
        if not terms:
            terms = list(_BASE_PERSON_PROMPTS)
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
        """Configura prompts open-vocab en el modelo único. True si ok."""
        if self.model is None:
            return False
        key = tuple(class_list)
        if key == self._prompt_key:
            return True
        try:
            if hasattr(self.model, "get_text_pe") and hasattr(self.model, "set_classes"):
                try:
                    pe = self.model.get_text_pe(class_list)
                    self.model.set_classes(class_list, pe)
                except TypeError:
                    self.model.set_classes(class_list)
            elif hasattr(self.model, "set_classes"):
                self.model.set_classes(class_list)
            else:
                print(
                    "[YOLO] El modelo no expone set_classes; "
                    "usa un checkpoint YOLOE/YOLO-World (p. ej. yoloe-26n-seg.pt)."
                )
                return False
            self._prompt_key = key
            print(f"[YOLO] Prompts open-vocab activos: {class_list}")
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

    def _build_text_prompt(self):
        """Lista activa de prompts (compat / logging)."""
        return ", ".join(self._active_class_list())

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

    def _rebuild_logo_templates(self) -> None:
        """Indexa fotos de Entrenar como plantillas grises + descriptores ORB."""
        self._logo_templates = {}
        self._logo_images = {}
        meta_path = Path(__file__).resolve().parent.parent / "data" / "training_metadata.json"
        if not meta_path.exists():
            return
        try:
            import cv2

            data = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            return
        if not isinstance(data, list):
            return

        try:
            import cv2

            orb = cv2.ORB_create(800)
        except Exception:
            return

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
            h, w = img.shape[:2]
            # Guardar varias escalas de plantilla (matchTemplate multi-escala).
            for max_side in (64, 96, 128, 192, 256):
                if max(h, w) < max_side // 2:
                    continue
                scale = max_side / float(max(h, w))
                tw, th = max(12, int(w * scale)), max(12, int(h * scale))
                small = cv2.resize(img, (tw, th), interpolation=cv2.INTER_AREA)
                gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
                by_img.setdefault(label, []).append(gray)

            # ORB a ~256 px
            max_side = 256
            scale = max_side / float(max(h, w)) if max(h, w) > max_side else 1.0
            orb_img = cv2.resize(
                img,
                (max(12, int(w * scale)), max(12, int(h * scale))),
                interpolation=cv2.INTER_AREA,
            )
            gray = cv2.cvtColor(orb_img, cv2.COLOR_BGR2GRAY)
            _kp, des = orb.detectAndCompute(gray, None)
            if des is not None and len(des) >= 8:
                by_des.setdefault(label, []).append(des)

        self._logo_templates = by_des
        self._logo_images = by_img
        if by_img or by_des:
            print(
                f"[YOLO] Logos indexados: plantillas={ {k: len(v) for k, v in by_img.items()} } "
                f"ORB={ {k: len(v) for k, v in by_des.items()} }"
            )

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
        y0r, y1r, x0r, x1r = _logo_roi_fractions()
        if rel_y < y0r - tol or rel_y > y1r + tol:
            return False
        if rel_x < x0r - tol or rel_x > x1r + tol:
            return False
        return True

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
        key = str(label or "").strip().lower()
        return "uniforme" in key or "itee" in key

    def _logo_structure_scores(self, bgr_patch) -> tuple[float, float, float, str]:
        """Devuelve (blue_r, yellow_r, skin_r, detail).

        El logo ITEE es bordado **amarillo** sobre polo **azul**.
        Azul solo (hombro) o piel (cara) no bastan.
        """
        try:
            import cv2
        except ImportError:
            return 0.0, 0.0, 0.0, "no-cv"
        if bgr_patch is None or bgr_patch.size == 0:
            return 0.0, 0.0, 0.0, "empty"
        ph, pw = bgr_patch.shape[:2]
        if ph < 8 or pw < 8:
            return 0.0, 0.0, 0.0, "tiny"
        hsv = cv2.cvtColor(bgr_patch, cv2.COLOR_BGR2HSV)
        skin = cv2.inRange(hsv, (0, 25, 40), (25, 200, 255))
        skin2 = cv2.inRange(hsv, (155, 25, 40), (180, 200, 255))
        n = float(skin.size)
        skin_r = float(cv2.countNonZero(skin) + cv2.countNonZero(skin2)) / n
        blue = cv2.inRange(hsv, (95, 55, 25), (135, 255, 220))
        blue_r = float(cv2.countNonZero(blue)) / n
        yellow = cv2.inRange(hsv, (12, 60, 70), (42, 255, 255))
        yel_r = float(cv2.countNonZero(yellow)) / n
        return blue_r, yel_r, skin_r, f"blue={blue_r:.2f} yel={yel_r:.2f} skin={skin_r:.2f}"

    def _find_yellow_logo_seeds(self, bgr_roi) -> list[tuple[int, int, int, int]]:
        """Candidatos de logo: manchas amarillas compactas sobre pecho."""
        try:
            import cv2
        except ImportError:
            return []
        if bgr_roi is None or bgr_roi.size == 0:
            return []
        h, w = bgr_roi.shape[:2]
        hsv = cv2.cvtColor(bgr_roi, cv2.COLOR_BGR2HSV)
        yellow = cv2.inRange(hsv, (12, 55, 60), (42, 255, 255))
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        yellow = cv2.morphologyEx(yellow, cv2.MORPH_OPEN, kernel, iterations=1)
        yellow = cv2.morphologyEx(yellow, cv2.MORPH_CLOSE, kernel, iterations=2)
        n_lab, _labels, stats, _cent = cv2.connectedComponentsWithStats(yellow, 8)
        seeds = []
        area_roi = float(h * w)
        for i in range(1, n_lab):
            x, y, bw, bh, area = stats[i]
            if area < 25 or area > 0.25 * area_roi:
                continue
            aspect = bw / float(max(1, bh))
            if aspect > 4.5 or aspect < 0.25:
                continue
            pad_x, pad_y = int(0.35 * bw) + 4, int(0.35 * bh) + 4
            x1 = max(0, x - pad_x)
            y1 = max(0, y - pad_y)
            x2 = min(w, x + bw + pad_x)
            y2 = min(h, y + bh + pad_y)
            seeds.append((x1, y1, x2, y2))
        return seeds

    def _match_template_multiscale(self, gray_roi, templates: list) -> tuple[float, tuple | None]:
        """Mejor score TM_CCOEFF_NORMED; escalas típicas del logo en el pecho."""
        try:
            import cv2
        except ImportError:
            return 0.0, None
        if gray_roi is None or gray_roi.size == 0 or not templates:
            return 0.0, None
        rh, rw = gray_roi.shape[:2]
        best_score = 0.0
        best_box = None
        for tmpl in templates:
            th0, tw0 = tmpl.shape[:2]
            if tw0 < 8 or th0 < 8:
                continue
            for rel in (0.18, 0.24, 0.30, 0.38):
                sw = max(20, int(rw * rel))
                sh = max(20, int(sw * (th0 / float(tw0))))
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

    def _detect_logo_templates(self, frame, persons: list[dict] | None = None) -> list[dict]:
        """Detecta uniforme ITEE por logo: pecho + amarillo-sobre-azul (+ template).

        Criterio de aceptación (todos):
          1. Hay persona (caja YOLO).
          2. Búsqueda solo en ROI de pecho (no hombro/cuello/cara).
          3. Hay bordado amarillo + tela azul en el parche (no color plano).
          4. Template score alto **o** semilla amarilla clara con azul alrededor.
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
            return []

        rois = self._person_chest_rois(frame, persons)
        if not rois:
            return []

        found: list[dict] = []
        tmpl_min = _env_float("YOLO_LOGO_TMPL_MIN", _TMPL_MATCH_MIN)
        yel_min = _env_float("YOLO_LOGO_YELLOW_MIN", 0.02)
        blue_min = _env_float("YOLO_LOGO_BLUE_MIN", 0.18)
        y0r, y1r, x0r, x1r = _logo_roi_fractions()
        debug = os.getenv("HOLOGRAM_YOLO_DEBUG", "0").lower() in ("1", "true", "yes")
        labels = set(self._logo_images) | set(self._logo_templates)

        for label in labels:
            best_conf = 0.0
            best_box_frame = None
            best_detail = ""
            imgs = self._logo_images.get(label) or []

            for crop, (ox1, oy1, ox2, oy2), person_box in rois:
                gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
                ch, cw = crop.shape[:2]

                candidates: list[tuple[str, float, tuple]] = []
                score, tmpl_box = self._match_template_multiscale(gray, imgs)
                if tmpl_box is not None and score >= tmpl_min * 0.92:
                    candidates.append(("tmpl", float(score), tmpl_box))

                for seed in self._find_yellow_logo_seeds(crop):
                    candidates.append(("seed", 0.55, tuple(float(v) for v in seed)))

                for source, base_score, lb in candidates:
                    ix1 = int(max(0, min(cw - 1, lb[0])))
                    iy1 = int(max(0, min(ch - 1, lb[1])))
                    ix2 = int(max(ix1 + 1, min(cw, lb[2])))
                    iy2 = int(max(iy1 + 1, min(ch, lb[3])))
                    patch = crop[iy1:iy2, ix1:ix2]
                    blue_r, yel_r, skin_r, det = self._logo_structure_scores(patch)

                    if skin_r >= 0.30 and blue_r < 0.20:
                        continue
                    if yel_r < yel_min:
                        continue  # sin bordado amarillo = no es el logo
                    if blue_r < blue_min:
                        continue  # sin tela azul = no es el polo

                    fx1 = float(ox1 + ix1)
                    fy1 = float(oy1 + iy1)
                    fx2 = float(ox1 + ix2)
                    fy2 = float(oy1 + iy2)
                    cx = 0.5 * (fx1 + fx2)
                    cy = 0.5 * (fy1 + fy2)
                    # Doble filtro: ya se recortó el ROI pecho; exigir centro ahí.
                    if not self._point_in_logo_zone(cx, cy, person_box, tol=0.05):
                        continue
                    px1, py1, px2, py2 = person_box
                    p_h = max(1.0, py2 - py1)
                    rel_y = (cy - py1) / p_h
                    rel_x = (cx - px1) / max(1.0, px2 - px1)

                    if source == "tmpl":
                        if base_score < tmpl_min:
                            continue
                        conf = min(
                            0.97,
                            0.50 * base_score
                            + 0.30 * min(1.0, yel_r * 12)
                            + 0.20 * min(1.0, blue_r * 2),
                        )
                    else:
                        conf = min(
                            0.90,
                            0.35
                            + 0.40 * min(1.0, yel_r * 15)
                            + 0.25 * min(1.0, blue_r * 2.5),
                        )
                        if yel_r < yel_min * 1.4:
                            continue

                    if conf <= best_conf:
                        continue
                    best_conf = conf
                    best_box_frame = (fx1, fy1, fx2, fy2)
                    best_detail = (
                        f"{source} s={base_score:.2f} {det} "
                        f"xy%={rel_x:.2f},{rel_y:.2f} zone=({x0r:.2f}-{x1r:.2f},"
                        f"{y0r:.2f}-{y1r:.2f})"
                    )

            accept_min = min(tmpl_min, 0.62)
            accept = best_conf >= accept_min and best_box_frame is not None
            if debug and (accept or best_conf >= 0.4):
                print(
                    f"[YOLO] Logo «{label}» conf={best_conf:.2f} "
                    f"({best_detail}) accept={accept}"
                )
            if not accept:
                continue
            found.append(
                {
                    "label": label,
                    "confidence": float(best_conf),
                    "box": best_box_frame,
                    "source": "logo_chest",
                }
            )
        return found

    def _predict_boxes(self, model, frame, conf: float) -> list[tuple[str, float, tuple]]:
        """Ejecuta predict y devuelve (label, conf, box) en coords del frame original."""
        if model is None:
            return []
        # frame puede ser None en tests con mocks; se reenvía tal cual.
        prepared = self._prepare_frame(frame) if frame is not None else frame
        kwargs = self._predict_kwargs({"conf": conf})
        try:
            results = model.predict(prepared, **kwargs)
        except Exception as error:
            print(f"[YOLO] Error en predict: {error}")
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
                    raw_name = str(cls_id)
                x1, y1, x2, y2 = _scale_box(_xyxy_tuple(box.xyxy[0]), scale_back)
                out.append((raw_name, confidence, (x1, y1, x2, y2)))
        return out

    def _is_person_label(self, raw_name: str) -> bool:
        key = str(raw_name).strip().lower()
        if key in _PERSON_LABELS or key == "person":
            return True
        try:
            return int(key) == 0  # COCO person id
        except (TypeError, ValueError):
            return False

    def _detect_all(self, frame) -> tuple[list[dict], list[dict]]:
        """Personas (COCO) + custom (open-vocab + logos ORB).

        En tests, a menudo solo se mockea ``self.model``: en ese caso un solo
        predict sirve para personas y custom (como el diseño YOLOE pure).
        """
        self._maybe_reload_training()
        self._ensure_loaded()

        persons: list[dict] = []
        custom_objects: list[dict] = []

        single_model = (
            self.model is not None
            and (self._person_model is None or self._person_model is self.model)
        )

        if single_model:
            # Camino tests / un solo open-vocab.
            class_list = self._active_class_list()
            self._apply_classes(class_list)
            # Umbral de predict: el de personas (tests comprueban conf=YOLO_CONFIDENCE).
            # Los custom se refiltran abajo con custom_confidence.
            for raw_name, confidence, box in self._predict_boxes(
                self.model, frame, self.confidence_threshold
            ):
                label = self._map_label(raw_name)
                entry = {"confidence": confidence, "box": box}
                if self._is_person_label(raw_name) or self._is_person_label(label):
                    persons.append(entry)
                elif confidence >= self.custom_confidence:
                    custom_objects.append({"label": label, **entry})
        else:
            # Personas COCO
            if self._person_model is not None:
                for raw_name, confidence, box in self._predict_boxes(
                    self._person_model, frame, self.confidence_threshold
                ):
                    if self._is_person_label(raw_name):
                        persons.append({"confidence": confidence, "box": box})

            # Custom open-vocab
            if self.model is not None and self._custom_class_list():
                class_list = self._active_class_list()
                if self._apply_classes(class_list):
                    for raw_name, confidence, box in self._predict_boxes(
                        self.model, frame, self.custom_confidence
                    ):
                        label = self._map_label(raw_name)
                        if self._is_person_label(label) or self._is_person_label(raw_name):
                            continue
                        custom_objects.append(
                            {"label": label, "confidence": confidence, "box": box}
                        )

        # Logos / recortes en el torso de cada persona (template multi-escala + ORB)
        for hit in self._detect_logo_templates(frame, persons=persons):
            custom_objects.append(
                {
                    "label": hit["label"],
                    "confidence": hit["confidence"],
                    "box": hit["box"],
                    "source": hit.get("source", "logo_chest"),
                }
            )

        # Uniforme open-vocab suele clavar cuello/hombro: solo vale si el
        # centro cae en pecho-logo (misma zona que el template).
        filtered: list[dict] = []
        for obj in custom_objects:
            lab = obj.get("label", "")
            src = obj.get("source") or ""
            if src == "logo_chest":
                filtered.append(obj)
                continue
            if not self._is_uniform_label(lab):
                filtered.append(obj)
                continue
            box = obj.get("box")
            if not box or len(box) < 4:
                continue
            person_box = self._best_person_for_box(box, persons)
            if person_box is None:
                continue
            cx = 0.5 * (float(box[0]) + float(box[2]))
            cy = 0.5 * (float(box[1]) + float(box[3]))
            if self._point_in_logo_zone(cx, cy, person_box, tol=0.06):
                filtered.append(obj)
            elif os.getenv("HOLOGRAM_YOLO_DEBUG", "0").lower() in (
                "1",
                "true",
                "yes",
            ):
                print(
                    f"[YOLO] Descartado «{lab}» open-vocab fuera de pecho-logo "
                    f"(centro rel. a persona)"
                )
        custom_objects = filtered

        # Deduplicar custom por label (mejor confianza).
        best: dict[str, dict] = {}
        for obj in custom_objects:
            lab = obj["label"]
            prev = best.get(lab)
            if prev is None or obj["confidence"] > prev["confidence"]:
                best[lab] = obj
        return persons, list(best.values())

    # ------------------------------------------------------------------
    # Detection helpers
    # ------------------------------------------------------------------

    def detect_persons_in_frame(self, frame):
        """Return a list of person detections in *frame*.

        Each detection is a dict with keys ``confidence`` and ``box``
        (a tuple of ``(x1, y1, x2, y2)``).  Corre siempre que se llame: no se
        omite por "sala vacía" ni por falta de viewers del feed.
        """
        persons, _ = self._detect_all(frame)
        return persons

    def detect_custom_objects(self, frame):
        """Objetos de clases entrenadas / vocabulario + logos ORB.

        Preferir ``analyze_frame`` en el bucle continuo.
        """
        _, custom = self._detect_all(frame)
        return custom

    def analyze_frame(self, frame):
        """Personas + custom (+ rostros opcional)."""
        persons, custom_objects = self._detect_all(frame)

        analysis = {
            "person_count": len(persons),
            "persons": persons,
            "custom_objects": custom_objects,
            "custom_count": len(custom_objects),
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

    def detect_person_in_frame(self, frame):
        """Return True if at least one person is detected in *frame*."""
        return len(self.detect_persons_in_frame(frame)) > 0

    def count_persons_in_frame(self, frame):
        """Return the number of people detected in *frame*."""
        return len(self.detect_persons_in_frame(frame))

    # ------------------------------------------------------------------
    # Single-shot from camera
    # ------------------------------------------------------------------

    def detect_person_once(self, camera_index=None):
        """Open the camera, read one frame, and return True if a person is found."""
        from vision.camera import Camera

        if camera_index is None:
            camera_index = int(_env("HOLOGRAM_CAMERA_INDEX", "0"))

        with Camera(source=camera_index) as cam:
            frame = cam.read_frame()
            if frame is None:
                return False
            return self.detect_person_in_frame(frame)

    def count_persons_once(self, camera_index=None):
        """Open the camera, read one frame, and return the person count."""
        from vision.camera import Camera

        if camera_index is None:
            camera_index = int(_env("HOLOGRAM_CAMERA_INDEX", "0"))

        with Camera(source=camera_index) as cam:
            frame = cam.read_frame()
            if frame is None:
                return 0
            return self.count_persons_in_frame(frame)

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
            cv2.putText(
                annotated,
                str(obj.get("label", "objeto")),
                (x1, max(0, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (60, 200, 90),
                2,
                cv2.LINE_AA,
            )

        count = analysis.get("person_count", 0)
        cv2.putText(
            annotated,
            f"Personas: {count}",
            (10, 24),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
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
    def is_available():
        """Return True if ultralytics and OpenCV are importable."""
        try:
            import cv2  # noqa: F401

            try:
                from ultralytics import YOLOE  # noqa: F401
            except ImportError:
                from ultralytics import YOLO  # noqa: F401
            return True
        except ImportError:
            return False
