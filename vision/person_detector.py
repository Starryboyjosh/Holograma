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

import os
import time
from pathlib import Path

# COCO class ID for "person"
_PERSON_CLASS_ID = 0


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


class YoloPersonDetector:
    """Detect people using YOLOv26 via the Ultralytics library.

    Parameters
    ----------
    model_name : str
        Model file name or path.  Accepts YOLOv26 (``yolo26n.pt``) weights.
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

    def load(self):
        """Load the YOLO model.  Downloads weights automatically on first run."""
        try:
            from ultralytics import YOLO
        except ImportError as error:
            raise RuntimeError(
                "Falta instalar ultralytics. "
                "Ejecuta: pip install ultralytics"
            ) from error

        # Regla A: use pathlib for model path resolution
        model_path = Path(self.model_name)

        print(f"[YOLO] Cargando modelo {model_path.name}...")
        self.model = YOLO(str(model_path))
        print("[YOLO] Modelo listo.")
        return self

    def _ensure_loaded(self):
        """Load the model if it hasn't been loaded yet."""
        if self.model is None:
            self.load()

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
        """Return person detections plus optional safe face count."""
        persons = self.detect_persons_in_frame(frame)
        analysis = {
            "person_count": len(persons),
            "persons": persons,
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

        print(f"[YOLO] Iniciando detección continua (cámara {camera_index})...")

        with Camera(source=camera_index) as cam:
            while True:
                frame = cam.read_frame()
                if frame is None:
                    time.sleep(interval_seconds)
                    continue

                analysis = self.analyze_frame(frame)
                count = analysis["person_count"]
                is_present = count > 0

                if is_present and not was_present:
                    event = "group_detected" if count > 3 else "person_entered"
                elif is_present and was_present:
                    if count > 3 and last_count <= 3:
                        event = "group_detected"
                    else:
                        event = "person_still_present"
                elif not is_present and was_present:
                    event = "person_left"
                else:
                    event = "no_person"

                if event != "no_person" and event != "person_still_present":
                    callback(event, count, analysis)

                was_present = is_present
                last_count = count
                time.sleep(interval_seconds)

    # ------------------------------------------------------------------
    # Availability check
    # ------------------------------------------------------------------

    @staticmethod
    def is_available():
        """Return True if ultralytics and OpenCV are importable."""
        try:
            from ultralytics import YOLO  # noqa: F401
            import cv2  # noqa: F401
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
        ultralytics_ok = True
    except ImportError:
        return "Visión no disponible: falta ultralytics. Ejecuta: pip install ultralytics"

    model = _env("YOLO_MODEL", "yolo26n.pt")
    return f"Visión activa: OpenCV {cv_version}, modelo YOLO '{model}'."
