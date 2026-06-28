"""
YOLOv8/v11 person detector for the UNEV hologram.

Regla de Oro A: Todas las rutas usan pathlib.Path.
Compatible con Linux y Windows.

Uso básico:
    from vision.person_detector import YoloPersonDetector
    detector = YoloPersonDetector()
    detector.load()
    detected = detector.detect_person_once()
"""

import json
import threading
import time
from pathlib import Path

from utils import _env, _env_float

# COCO class ID for "person"
_PERSON_CLASS_ID = 0


class YoloPersonDetector:
    """Detect people using YOLOe26 via the Ultralytics library.

    Parameters
    ----------
    model_name : str
        Model file name or path.  Accepts YOLO v8/v11 (``yolo26n.pt``) weights.
        The environment variable ``YOLO_MODEL`` overrides this value.
    confidence_threshold : float
        Minimum confidence to consider a detection valid.
    """

    def __init__(self, model_name=None, confidence_threshold=None):
        self.model_name = model_name or _env("YOLO_MODEL", "yolo26n.pt")
        self.confidence_threshold = confidence_threshold or _env_float(
            "YOLO_CONFIDENCE", 0.5
        )
        self.model = None
        self.face_analyzer = None
        self._custom_classes: list[str] = []
        self._custom_vocabulary: list[str] = []
        self._last_reload_time = 0
        # Prompts de texto YOLOE/YOLO-World: si el modelo cargado no los soporta
        # (p. ej. un yolo26n estándar), detect_custom_objects falla. Lo detectamos
        # una sola vez y desactivamos esa ruta para no repetir el error ni saturar
        # el log (ver detect_custom_objects).
        self._custom_detect_disabled = False
        # La inferencia de objetos personalizados (YOLOE) es cara; correrla en cada
        # cuadro (~30 fps) desperdicia CPU. La limitamos a su propio intervalo y
        # reusamos el último resultado entre corridas (Fase 4). Configurable con
        # HOLOGRAM_CUSTOM_OBJECT_INTERVAL (segundos; 0 = sin throttle, cada cuadro).
        self._custom_interval = _env_float("HOLOGRAM_CUSTOM_OBJECT_INTERVAL", 2.0)
        self._last_custom_time = 0.0
        self._last_custom_objects: list[dict] = []
        # Último cuadro anotado (JPEG) para transmitir al frontend vía MJPEG.
        self._latest_jpeg: bytes | None = None
        self._jpeg_lock = threading.Lock()
        # Suscriptores del feed MJPEG. Codificar JPEG en cada iteración (~30 fps)
        # gasta CPU aunque nadie mire; con cero suscriptores el bucle se salta el
        # imencode por completo. El contador lo mueven los handlers de /api/video_feed.
        self._feed_subscribers = 0
        self._feed_lock = threading.Lock()
        # Señal cooperativa de parada: al activarla, run_continuous sale del bucle
        # y el context manager de Camera libera el dispositivo (apagar = liberar).
        self._stop_event = threading.Event()
        self._load_training_data()

    def stop(self):
        """Solicita que run_continuous termine y libere la cámara."""
        self._stop_event.set()

    def load(self):
        """Load the YOLO model.  Downloads weights automatically on first run."""
        try:
            from ultralytics import YOLO
        except ImportError as error:
            raise RuntimeError(
                "Falta instalar ultralytics. "
                "Ejecuta: pip install ultralytics"
            ) from error

        model_path = Path(self.model_name)
        if not model_path.is_absolute():
            base_dir = Path(__file__).resolve().parent.parent
            # Try models/ subdirectory first
            model_path_in_models = base_dir / "models" / model_path
            if model_path_in_models.exists() or not (base_dir / model_path).exists():
                model_path = model_path_in_models
            else:
                model_path = base_dir / model_path

        if not model_path.exists():
            fallback_path = model_path.parent / "yolo26n.pt"
            if fallback_path.exists():
                print(f"[YOLO] AVISO: {model_path.name} no existe. Usando fallback {fallback_path.name}.")
                model_path = fallback_path

        if not model_path.exists():
            print(f"[YOLO] ERROR: No se encontró el modelo {model_path}. La cámara no estará disponible.")
            return self

        print(f"[YOLO] Cargando modelo {model_path.name}...")
        try:
            self.model = YOLO(str(model_path))
            print("[YOLO] Modelo listo.")
        except Exception as error:
            print(f"[YOLO] ERROR al cargar el modelo: {error}")
        return self

    def _ensure_loaded(self):
        """Load the model if it hasn't been loaded yet."""
        if self.model is None:
            self.load()

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
            if self._custom_classes or self._custom_vocabulary:
                print(f"[YOLO] Clases entrenadas actualizadas: {self._custom_classes}")
                print(f"[YOLO] Vocabulario abierto actualizado: {self._custom_vocabulary}")

    def _build_text_prompt(self):
        """Combine custom classes and vocabulary into a single YOLOE text prompt."""
        terms = list(self._custom_classes)
        for t in self._custom_vocabulary:
            if t not in terms:
                terms.append(t)
        return ", ".join(terms)

    def detect_custom_objects(self, frame):
        """Detect custom objects using YOLOE text prompts from training data."""
        # Si una llamada previa falló porque el modelo no soporta prompts de
        # texto, no reintentamos: ahorra CPU y evita spam de logs en cada cuadro.
        if self._custom_detect_disabled:
            return []

        # Reload training data every 5 seconds if needed
        current_time = time.time()
        if current_time - getattr(self, "_last_reload_time", 0) > 5.0:
            self._load_training_data()
            self._last_reload_time = current_time

        prompt = self._build_text_prompt()
        if not prompt:
            return []

        # Throttle: la inferencia YOLOE corre en su propio intervalo, no en cada
        # cuadro. Entre corridas devolvemos el último resultado cacheado, así el
        # bucle de personas (~30 fps) no arrastra el coste de los objetos custom.
        if current_time - self._last_custom_time < self._custom_interval:
            return self._last_custom_objects

        self._ensure_loaded()
        objects = []
        try:
            results = self.model.predict(frame, text=prompt, verbose=False)
            for result in results:
                for box in result.boxes:
                    confidence = float(box.conf[0])
                    if confidence >= self.confidence_threshold:
                        cls_id = int(box.cls[0])
                        cls_name = result.names.get(cls_id, "unknown")
                        x1, y1, x2, y2 = box.xyxy[0].tolist()
                        objects.append({
                            "label": cls_name,
                            "confidence": confidence,
                            "box": (x1, y1, x2, y2),
                        })
        except Exception as error:
            # Un yolo26n estándar NO acepta `text=` (eso es de YOLOE/YOLO-World).
            # Antes el error se tragaba con `except Exception: pass`, ocultando
            # por completo el fallo. Lo registramos una vez y desactivamos la
            # ruta para no repetirlo en cada cuadro del bucle continuo.
            print(
                "[YOLO] Detección de objetos personalizados desactivada: el "
                f"modelo no soporta prompts de texto ({error})."
            )
            self._custom_detect_disabled = True
            return []
        self._last_custom_time = current_time
        self._last_custom_objects = objects
        return objects

    # ------------------------------------------------------------------
    # Detection helpers
    # ------------------------------------------------------------------

    def detect_persons_in_frame(self, frame):
        """Return a list of person detections in *frame*.

        Each detection is a dict with keys ``confidence`` and ``box``
        (a tuple of ``(x1, y1, x2, y2)``).
        """
        self._ensure_loaded()

        results = self.model(frame, verbose=False)
        persons = []

        for result in results:
            for box in result.boxes:
                class_id = int(box.cls[0])
                confidence = float(box.conf[0])

                if class_id == _PERSON_CLASS_ID and confidence >= self.confidence_threshold:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    persons.append({
                        "confidence": confidence,
                        "box": (x1, y1, x2, y2),
                    })

        return persons

    def analyze_frame(self, frame):
        """Return person and custom object detections plus optional safe face count.

        Sólo se reportan objetos personalizados que el modelo de visión realmente
        detecta en el cuadro.  No se infiere ni se inyecta ninguna identidad: el
        sistema analiza presencia de personas y objetos visibles, no quién es cada
        quien.
        """
        persons = self.detect_persons_in_frame(frame)
        custom_objects = self.detect_custom_objects(frame)

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

        print(f"[YOLO] Iniciando detección continua (cámara {camera_index})...")

        self._stop_event.clear()
        with Camera(source=camera_index) as cam:
            while not self._stop_event.is_set():
                frame = cam.read_frame()
                if frame is None:
                    time.sleep(0.1)
                    continue

                now = time.time()
                # La detección YOLO corre cada *interval_seconds*; entre cuadros se
                # reutiliza el último análisis para mantener el video fluido sin
                # saturar la CPU/GPU.
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

                    if event != "no_person" and event != "person_still_present":
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
                # Sin suscriptores nos saltamos el imencode (caro a ~30 fps) por
                # completo; la detección/eventos siguen corriendo igual.
                if self.has_feed_subscribers():
                    self._store_annotated_frame(frame, last_analysis)
                time.sleep(0.03)

    # ------------------------------------------------------------------
    # Availability check
    # ------------------------------------------------------------------

    @staticmethod
    def is_available():
        """Return True if ultralytics and OpenCV are importable."""
        try:
            import cv2  # noqa: F401
            from ultralytics import YOLO  # noqa: F401
            return True
        except ImportError:
            return False


def get_vision_status():
    """Return a human-readable status string for the vision subsystem."""
    try:
        import cv2
        cv_version = cv2.__version__
    except ImportError:
        return "Visión no disponible: falta opencv-python. Ejecuta: pip install opencv-python"

    try:
        from ultralytics import YOLO  # noqa: F401
    except ImportError:
        return "Visión no disponible: falta ultralytics. Ejecuta: pip install ultralytics"

    model = _env("YOLO_MODEL", "yolo26n.pt")
    return f"Visión activa: OpenCV {cv_version}, modelo YOLO '{model}'."
