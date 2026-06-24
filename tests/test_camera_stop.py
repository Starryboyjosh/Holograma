"""Test del mecanismo de parada/liberación de la cámara (Fase B).

No requiere cámara real ni la pila de visión (cv2/ultralytics se importan de forma
perezosa dentro de los métodos): se inyecta un Camera falso y se mockea analyze.
"""

import threading
import time

import vision.person_detector as pd


def test_run_continuous_stops_and_releases_camera(monkeypatch):
    released = {"value": False}

    class FakeCamera:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            released["value"] = True  # el context manager libera el dispositivo
            return False

        def read_frame(self):
            time.sleep(0.005)
            return object()  # cuadro no nulo

    import vision.camera

    monkeypatch.setattr(vision.camera, "Camera", FakeCamera)

    detector = pd.YoloPersonDetector()
    monkeypatch.setattr(
        detector,
        "analyze_frame",
        lambda frame: {"person_count": 0, "persons": [], "custom_objects": []},
    )
    monkeypatch.setattr(detector, "_store_annotated_frame", lambda *a, **k: None)

    thread = threading.Thread(
        target=detector.run_continuous,
        args=(lambda *a, **k: None,),
        kwargs={"camera_index": 0, "interval_seconds": 0.01},
        daemon=True,
    )
    thread.start()
    time.sleep(0.05)
    assert thread.is_alive(), "el bucle debería estar corriendo"

    detector.stop()
    thread.join(timeout=2.0)

    assert not thread.is_alive(), "stop() debe terminar el bucle"
    assert released["value"] is True, "apagar la cámara debe liberar el dispositivo"


def test_stop_is_idempotent_before_run():
    detector = pd.YoloPersonDetector()
    detector.stop()  # no debe lanzar aunque no esté corriendo
    assert detector._stop_event.is_set()
