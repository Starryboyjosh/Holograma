"""Descriptor de persona desde las máscaras (§13 I5).

Tests del módulo puro ``vision/person_signature.py``: solo numpy.
"""

import numpy as np

from vision.person_signature import (
    person_signature,
    person_signature_band,
    signature_distance,
)

def test_signature_shape_and_normalized():
    """Descriptor = 3 bandas × (8+4+4) bins, L2-normalizado por banda."""
    hsv = np.zeros((100, 50, 3), dtype=np.uint8)
    hsv[..., 0] = 90  # un verde
    hsv[..., 1] = 200
    hsv[..., 2] = 100
    mask = np.zeros((100, 50), dtype=np.float32)
    mask[20:80, 10:40] = 1.0
    sig = person_signature(mask, hsv)
    assert sig is not None
    assert sig.shape == (3 * (8 + 4 + 4),)
    # L2 por banda: el primer bloque de 16 bins debe tener norma 1.
    assert np.isclose(np.linalg.norm(sig[:16]), 1.0)
    assert np.isclose(np.linalg.norm(sig[16:32]), 1.0)
    assert np.isclose(np.linalg.norm(sig[32:]), 1.0)


def test_signature_none_when_no_pixels():
    hsv = np.zeros((20, 20, 3), dtype=np.uint8)
    mask = np.zeros((20, 20), dtype=np.float32)
    assert person_signature(mask, hsv) is None
    assert person_signature(None, hsv) is None
    assert person_signature(mask, None) is None


def test_signature_none_on_shape_mismatch():
    mask = np.zeros((20, 20), dtype=np.float32)
    mask[5:10, 5:10] = 1.0
    hsv = np.zeros((21, 20, 3), dtype=np.uint8)
    assert person_signature(mask, hsv) is None


def test_identical_persons_have_small_distance():
    hsv = np.zeros((100, 50, 3), dtype=np.uint8)
    hsv[..., 0] = 90
    hsv[..., 1] = 200
    hsv[..., 2] = 100
    mask = np.zeros((100, 50), dtype=np.float32)
    mask[20:80, 10:40] = 1.0
    a = person_signature(mask, hsv)
    b = person_signature(mask, hsv)
    assert signature_distance(a, b) < 1e-9


def test_different_colors_have_larger_distance():
    hsv_red = np.zeros((100, 50, 3), dtype=np.uint8)
    hsv_red[..., 0] = 0
    hsv_red[..., 1] = 200
    hsv_red[..., 2] = 100
    hsv_blue = np.zeros((100, 50, 3), dtype=np.uint8)
    hsv_blue[..., 0] = 120
    hsv_blue[..., 1] = 200
    hsv_blue[..., 2] = 100
    mask = np.zeros((100, 50), dtype=np.float32)
    mask[20:80, 10:40] = 1.0
    d = signature_distance(person_signature(mask, hsv_red), person_signature(mask, hsv_blue))
    assert d > 0.05


def test_distance_none_returns_one():
    assert signature_distance(None, None) == 1.0
    assert signature_distance(None, np.zeros(16)) == 1.0


def test_band_helper_requires_pixels():
    band = person_signature_band(
        np.zeros((10, 10), dtype=np.float32),
        np.zeros((10, 10, 3), dtype=np.uint8),
    )
    assert band is None


class _FakeMask:
    def __init__(self, data):
        self.data = data


class _FakeBox:
    def __init__(self, cls_id, conf, xyxy):
        self.cls = [cls_id]
        self.conf = [conf]
        self.xyxy = [np.array(xyxy)]


class _FakeResult:
    def __init__(self, boxes, masks, names):
        self.boxes = boxes
        self.masks = masks
        self.names = names


class _FakeModel:
    def __init__(self, result):
        self.result = result

    def set_classes(self, names, pe=None):  # noqa: ARG002
        pass

    def predict(self, frame, **kwargs):  # noqa: ARG002
        return [self.result]


def test_detector_extracts_signatures_from_masks(monkeypatch):
    """I5: _predict_boxes con YOLO_PERSON_SIGNATURES=1 llena _last_person_signatures.

    Los descriptores se guardan aparte del detector; `analysis` queda limpio.
    """
    import vision.person_detector as pd

    monkeypatch.setenv("YOLO_PERSON_SIGNATURES", "1")
    monkeypatch.setenv("YOLO_MAX_SIDE", "0")
    det = pd.YoloPersonDetector()
    monkeypatch.setattr(det, "_load_training_data", lambda: None)
    det._custom_classes = []
    det._custom_vocabulary = []
    det._prompt_key = None

    h = w = 32
    mask = np.zeros((h, w), dtype=np.float32)
    mask[8:24, 8:24] = 1.0
    result = _FakeResult(
        boxes=[_FakeBox(0, 0.9, [4, 4, 28, 28])],
        masks=_FakeMask(np.stack([mask])),
        names={0: "person"},
    )
    det.model = _FakeModel(result)
    frame = np.zeros((32, 32, 3), dtype=np.uint8)
    frame[..., 0] = 100
    frame[..., 1] = 150
    frame[..., 2] = 50

    hits = det._predict_boxes(frame, 0.3)
    assert len(hits) == 1
    assert len(det._last_person_signatures) == 1
    sig = det._last_person_signatures[0]["signature"]
    assert sig.shape == (3 * 16,)
    assert det._last_person_signatures[0]["box"] == (4, 4, 28, 28)

    # analysis no expone los descriptores.
    analysis = det.analyze_frame(frame)
    assert "signatures" not in analysis
    assert "signature" not in analysis


def test_detector_skips_signatures_when_disabled(monkeypatch):
    """I5: sin YOLO_PERSON_SIGNATURES, no se computan descriptores."""
    import vision.person_detector as pd

    monkeypatch.setenv("YOLO_PERSON_SIGNATURES", "0")
    monkeypatch.setenv("YOLO_MAX_SIDE", "0")
    det = pd.YoloPersonDetector()
    monkeypatch.setattr(det, "_load_training_data", lambda: None)
    det._custom_classes = []
    det._custom_vocabulary = []
    det._prompt_key = None

    h = w = 32
    mask = np.zeros((h, w), dtype=np.float32)
    mask[8:24, 8:24] = 1.0
    result = _FakeResult(
        boxes=[_FakeBox(0, 0.9, [4, 4, 28, 28])],
        masks=_FakeMask(np.stack([mask])),
        names={0: "person"},
    )
    det.model = _FakeModel(result)
    frame = np.zeros((32, 32, 3), dtype=np.uint8)

    hits = det._predict_boxes(frame, 0.3)
    assert len(hits) == 1
    assert det._last_person_signatures == []
