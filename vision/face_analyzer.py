"""
Safe face presence analysis with OpenCV.

This module only detects/counts visible faces. It intentionally does not infer
identity, age, gender, race, emotion, health, or any other sensitive attribute.
"""



from utils import _env_float, _env_int


class FaceAnalyzer:
    """Count visible frontal faces using OpenCV's bundled Haar cascade."""

    def __init__(self, scale_factor=None, min_neighbors=None, min_size=None):
        self.scale_factor = scale_factor or _env_float("FACE_SCALE_FACTOR", 1.1)
        self.min_neighbors = min_neighbors or _env_int("FACE_MIN_NEIGHBORS", 5)
        configured_min_size = min_size or _env_int("FACE_MIN_SIZE", 48)
        self.min_size = (configured_min_size, configured_min_size)
        self._classifier = None

    def load(self):
        try:
            import cv2
        except ImportError as error:
            raise RuntimeError(
                "Falta instalar opencv-python. Ejecuta: pip install opencv-python"
            ) from error

        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        classifier = cv2.CascadeClassifier(cascade_path)
        if classifier.empty():
            raise RuntimeError("No pude cargar el clasificador de rostros de OpenCV.")

        self._classifier = classifier
        return self

    def _ensure_loaded(self):
        if self._classifier is None:
            self.load()

    def analyze_frame(self, frame):
        """Return a safe visual summary for a frame."""
        self._ensure_loaded()

        import cv2

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self._classifier.detectMultiScale(
            gray,
            scaleFactor=self.scale_factor,
            minNeighbors=self.min_neighbors,
            minSize=self.min_size,
        )

        boxes = [
            (int(x), int(y), int(x + w), int(y + h))
            for x, y, w, h in faces
        ]
        return {
            "face_count": len(boxes),
            "boxes": boxes,
            "description": self.describe_count(len(boxes)),
        }

    @staticmethod
    def describe_count(face_count):
        if face_count <= 0:
            return "No veo rostros claramente de frente."
        if face_count == 1:
            return "Veo a una persona frente a mí."
        return f"Veo {face_count} personas frente a mí."

    @staticmethod
    def is_available():
        try:
            import cv2  # noqa: F401
            return True
        except ImportError:
            return False
