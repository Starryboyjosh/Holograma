"""Gating del feed MJPEG: el detector solo codifica JPEG si alguien mira.

Codificar el cuadro anotado en cada iteración (~30 fps) gasta CPU aunque nadie
tenga abierto `/api/video_feed`. El detector lleva un contador de suscriptores y
`run_continuous` se salta el `imencode` cuando es cero.
"""

import vision.camera
import vision.person_detector as pd


def test_subscriber_counter_floors_at_zero():
    det = pd.YoloPersonDetector()
    assert det.has_feed_subscribers() is False

    det.feed_subscribe()
    det.feed_subscribe()
    assert det.has_feed_subscribers() is True  # 2 suscriptores

    det.feed_unsubscribe()
    assert det.has_feed_subscribers() is True  # queda 1

    det.feed_unsubscribe()
    assert det.has_feed_subscribers() is False  # 0

    det.feed_unsubscribe()  # no baja de 0 ni revienta
    assert det.has_feed_subscribers() is False


def test_last_jpeg_cleared_when_no_subscribers():
    det = pd.YoloPersonDetector()
    det.feed_subscribe()
    with det._jpeg_lock:
        det._latest_jpeg = b"fake-jpeg"
    det.feed_unsubscribe()  # cae a 0 -> descarta el cuadro viejo
    assert det.get_latest_jpeg() is None


def _count_stores(monkeypatch, subscribe):
    """Corre run_continuous unos cuadros y cuenta cuántas veces guardó un JPEG."""
    monkeypatch.setattr(pd.time, "sleep", lambda *a, **k: None)

    class FakeCamera:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read_frame(self):
            return object()

    monkeypatch.setattr(vision.camera, "Camera", FakeCamera)

    det = pd.YoloPersonDetector()
    if subscribe:
        det.feed_subscribe()

    frames = {"n": 0}

    def fake_analyze(frame):
        frames["n"] += 1
        if frames["n"] >= 3:
            det.stop()
        return {"person_count": 0, "persons": [], "custom_objects": []}

    stores = {"n": 0}

    def spy_store(*a, **k):
        stores["n"] += 1

    monkeypatch.setattr(det, "analyze_frame", fake_analyze)
    monkeypatch.setattr(det, "_store_annotated_frame", spy_store)

    det.run_continuous(lambda *a: None, camera_index=0, interval_seconds=0.0)
    return stores["n"]


def test_run_continuous_skips_encode_without_subscribers(monkeypatch):
    assert _count_stores(monkeypatch, subscribe=False) == 0


def test_run_continuous_encodes_with_subscriber(monkeypatch):
    assert _count_stores(monkeypatch, subscribe=True) > 0
