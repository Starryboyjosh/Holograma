"""La inferencia de objetos personalizados (YOLOE) corre en su propio intervalo.

`detect_custom_objects` es caro y antes se ejecutaba en cada cuadro desde
`analyze_frame`. Ahora se limita a `HOLOGRAM_CUSTOM_OBJECT_INTERVAL` segundos y
reusa el último resultado entre corridas; así el bucle de personas (~30 fps) no
arrastra el coste de los objetos custom (Fase 4).
"""

import vision.person_detector as pd


class _FakeXY:
    def __init__(self, vals):
        self._vals = vals

    def tolist(self):
        return list(self._vals)


class _FakeBox:
    def __init__(self, conf, cls, xy):
        self.conf = [conf]
        self.cls = [cls]
        self.xyxy = [_FakeXY(xy)]


class _FakeResult:
    def __init__(self, boxes, names):
        self.boxes = boxes
        self.names = names


class _FakeModel:
    """Modelo falso: cuenta cuántas veces se le pide inferencia."""

    def __init__(self):
        self.predict_calls = 0

    def predict(self, frame, text=None, verbose=False):
        self.predict_calls += 1
        return [_FakeResult([_FakeBox(0.9, 0, [1, 2, 3, 4])], {0: "botella"})]


def _make_detector(monkeypatch, clock, interval=2.0):
    monkeypatch.setattr(pd.time, "time", lambda: clock["t"])
    det = pd.YoloPersonDetector()
    # No tocar el disco en el reload de 5 s ni borrar las clases del test.
    monkeypatch.setattr(det, "_load_training_data", lambda: None)
    det._custom_classes = ["botella"]
    det._custom_vocabulary = []
    det._custom_interval = interval
    det.model = _FakeModel()  # _ensure_loaded lo ve != None y no carga el real
    return det


def test_first_call_runs_inference(monkeypatch):
    clock = {"t": 1000.0}
    det = _make_detector(monkeypatch, clock)
    out = det.detect_custom_objects(frame=None)
    assert det.model.predict_calls == 1
    assert out == [{"label": "botella", "confidence": 0.9, "box": (1, 2, 3, 4)}]


def test_second_call_within_interval_uses_cache(monkeypatch):
    clock = {"t": 1000.0}
    det = _make_detector(monkeypatch, clock, interval=2.0)
    first = det.detect_custom_objects(frame=None)
    clock["t"] += 1.5  # < 2.0: aún dentro del intervalo
    second = det.detect_custom_objects(frame=None)
    assert det.model.predict_calls == 1  # no se volvió a inferir
    assert second == first


def test_inference_reruns_after_interval(monkeypatch):
    clock = {"t": 1000.0}
    det = _make_detector(monkeypatch, clock, interval=2.0)
    det.detect_custom_objects(frame=None)
    clock["t"] += 2.5  # > 2.0: vence el intervalo
    det.detect_custom_objects(frame=None)
    assert det.model.predict_calls == 2


def test_zero_interval_runs_every_call(monkeypatch):
    clock = {"t": 1000.0}
    det = _make_detector(monkeypatch, clock, interval=0.0)
    det.detect_custom_objects(frame=None)
    det.detect_custom_objects(frame=None)
    assert det.model.predict_calls == 2  # sin throttle: cada cuadro


def test_no_custom_classes_skips_inference(monkeypatch):
    clock = {"t": 1000.0}
    det = _make_detector(monkeypatch, clock)
    det._custom_classes = []
    det._custom_vocabulary = []
    assert det.detect_custom_objects(frame=None) == []
    assert det.model.predict_calls == 0  # prompt vacío -> ni se intenta inferir
