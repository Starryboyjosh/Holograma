"""
Cross-platform OpenCV camera wrapper.

Regla de Oro A: Todas las rutas usan pathlib.Path.
Funciona en Linux y Windows sin cambios.

Uso básico:
    from vision.camera import Camera
    with Camera() as cam:
        frame = cam.read_frame()
"""

import os
from pathlib import Path


def _env_int(name, default):
    """Read an integer environment variable or return a default."""
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    try:
        return int(value.strip())
    except ValueError:
        return default


class Camera:
    """Cross-platform wrapper around OpenCV VideoCapture.

    Supports both live camera indices and video file paths (via ``pathlib.Path``).

    Parameters
    ----------
    source : int, str, or Path
        Camera index (default ``0``) or path to a video file.
    width : int or None
        Requested frame width.  ``None`` uses the camera default.
    height : int or None
        Requested frame height.  ``None`` uses the camera default.
    """

    def __init__(self, source=None, width=None, height=None):
        if source is None:
            source = _env_int("HOLOGRAM_CAMERA_INDEX", 0)

        # Regla A: accept Path objects for video files
        if isinstance(source, Path):
            source = str(source)

        self.source = source
        self.width = width
        self.height = height
        self._capture = None

    def open(self):
        """Open the camera or video source."""
        try:
            import cv2
        except ImportError as error:
            raise RuntimeError(
                "Falta instalar opencv-python. "
                "Ejecuta: pip install opencv-python"
            ) from error

        self._capture = cv2.VideoCapture(self.source)

        if not self._capture.isOpened():
            raise RuntimeError(
                f"No se pudo abrir la fuente de video: {self.source}"
            )

        if self.width is not None:
            self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        if self.height is not None:
            self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

        return self

    def read_frame(self):
        """Read a single frame.  Returns the frame or None on failure."""
        if self._capture is None:
            self.open()

        success, frame = self._capture.read()
        if not success:
            return None

        return frame

    def release(self):
        """Release the camera resource."""
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    @property
    def is_opened(self):
        """Return True if the camera is currently open."""
        return self._capture is not None and self._capture.isOpened()

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
        return False

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def save_frame(self, output_path):
        """Capture one frame and save it to *output_path*.

        Parameters
        ----------
        output_path : str or Path
            Destination file path (Regla A).
        """
        try:
            import cv2
        except ImportError as error:
            raise RuntimeError(
                "Falta instalar opencv-python. "
                "Ejecuta: pip install opencv-python"
            ) from error

        frame = self.read_frame()
        if frame is None:
            raise RuntimeError("No se pudo leer un frame de la cámara.")

        output_path = Path(output_path)  # Regla A
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(output_path), frame)
        return output_path

    @staticmethod
    def is_available():
        """Return True if OpenCV is importable."""
        try:
            import cv2  # noqa: F401
            return True
        except ImportError:
            return False
