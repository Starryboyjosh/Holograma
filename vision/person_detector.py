class YoloPersonDetector:
    """
    Lightweight wrapper for future YOLO person detection.

    This is intentionally optional. The text demo can run without OpenCV or Ultralytics.
    Install them later with:
        pip install opencv-python ultralytics
    """

    def __init__(self, model_name="yolov8n.pt", confidence_threshold=0.5):
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self.model = None

    def load(self):
        try:
            from importlib import import_module

            ultralytics_module = import_module("ultralytics")
            yolo_class = getattr(ultralytics_module, "YOLO")
        except ImportError as error:
            raise RuntimeError(
                "Falta instalar ultralytics. Ejecuta: pip install ultralytics"
            ) from error

        self.model = yolo_class(self.model_name)
        return self

    def detect_person_in_frame(self, frame):
        if self.model is None:
            self.load()

        model = self.model
        if model is None:
            raise RuntimeError("El modelo YOLO no se cargó correctamente.")

        results = model(frame, verbose=False)

        for result in results:
            for box in result.boxes:
                class_id = int(box.cls[0])
                confidence = float(box.conf[0])

                # COCO class 0 is person.
                if class_id == 0 and confidence >= self.confidence_threshold:
                    return True

        return False

    def detect_person_once(self, camera_index=0):
        try:
            import cv2
        except ImportError as error:
            raise RuntimeError(
                "Falta instalar opencv-python. Ejecuta: pip install opencv-python"
            ) from error

        capture = cv2.VideoCapture(camera_index)

        if not capture.isOpened():
            raise RuntimeError("No se pudo abrir la cámara.")

        try:
            success, frame = capture.read()
            if not success:
                return False

            return self.detect_person_in_frame(frame)
        finally:
            capture.release()
