"""Opciones de inferencia YOLO local (imgsz / device / prepare_frame).

No cargan ultralytics real: mockean model.predict y comprueban kwargs y que la
detección no se omite por sala vacía.
"""

import numpy as np

import vision.person_detector as pd


class _FakeBoxes:
    def __init__(self, items):
        self._items = items

    def __iter__(self):
        return iter(self._items)


class _FakeBox:
    def __init__(self, cls_id, conf, xyxy):
        self.cls = [cls_id]
        self.conf = [conf]
        self.xyxy = [xyxy]


class _FakeResult:
    def __init__(self, boxes, names=None):
        self.boxes = _FakeBoxes(boxes)
        self.names = names or {0: "person"}


class _FakeModel:
    def __init__(self):
        self.calls = []
        self.classes = None

    def set_classes(self, names, pe=None):  # noqa: ARG002
        self.classes = list(names)

    def predict(self, frame, **kwargs):
        self.calls.append({"frame_shape": getattr(frame, "shape", None), **kwargs})
        # Persona open-vocab (prompt "person")
        box = _FakeBox(0, 0.9, [10.0, 20.0, 30.0, 40.0])
        return [_FakeResult([box], names={0: "person"})]


def test_detect_persons_passes_imgsz_and_conf(monkeypatch):
    monkeypatch.setenv("YOLO_IMGSZ", "320")
    monkeypatch.setenv("YOLO_CONFIDENCE", "0.5")
    # Predict usa min(persona, custom); igualar custom para que conf quede 0.5.
    monkeypatch.setenv("YOLO_CUSTOM_CONFIDENCE", "0.5")
    monkeypatch.setenv("YOLO_MAX_SIDE", "0")  # no resize software
    det = pd.YoloPersonDetector()
    monkeypatch.setattr(det, "_load_training_data", lambda: None)
    det._custom_classes = []
    det._custom_vocabulary = []
    det._prompt_key = None
    fake = _FakeModel()
    det.model = fake
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    persons = det.detect_persons_in_frame(frame)

    assert len(persons) == 1
    assert fake.calls, "debe llamar a predict"
    call = fake.calls[0]
    assert call["imgsz"] == 320
    assert call["conf"] == 0.5
    assert call["verbose"] is False
    assert fake.classes and "person" in fake.classes


def test_predict_floor_is_min_of_person_and_custom(monkeypatch):
    """Custom a 0.12 no debe quedar filtrado por conf de persona 0.45."""
    monkeypatch.setenv("YOLO_CONFIDENCE", "0.45")
    monkeypatch.setenv("YOLO_CUSTOM_CONFIDENCE", "0.12")
    monkeypatch.setenv("YOLO_MAX_SIDE", "0")
    det = pd.YoloPersonDetector()
    monkeypatch.setattr(det, "_load_training_data", lambda: None)
    det._custom_classes = ["botella"]
    det._custom_vocabulary = []
    det._prompt_key = None
    fake = _FakeModel()

    def predict(frame, **kwargs):
        fake.calls.append(kwargs)
        # Persona alta + custom por debajo del umbral "persona" pero sobre custom.
        return [
            _FakeResult(
                [
                    _FakeBox(0, 0.9, [1.0, 2.0, 3.0, 4.0]),
                    _FakeBox(1, 0.20, [10.0, 20.0, 30.0, 40.0]),
                ],
                names={0: "person", 1: "botella"},
            )
        ]

    fake.predict = predict
    det.model = fake
    persons, custom = det._detect_all(frame=None)
    assert fake.calls
    assert fake.calls[0]["conf"] == 0.12  # piso = custom
    assert persons and custom
    assert custom[0]["label"] == "botella"


def test_prepare_frame_downscales_large_input(monkeypatch):
    monkeypatch.setenv("YOLO_MAX_SIDE", "320")
    det = pd.YoloPersonDetector()
    big = np.zeros((1080, 1920, 3), dtype=np.uint8)
    small = det._prepare_frame(big)
    assert max(small.shape[0], small.shape[1]) <= 320


def test_empty_room_still_runs_predict(monkeypatch):
    """La sala vacía no debe saltarse la inferencia local."""
    monkeypatch.setenv("YOLO_MAX_SIDE", "0")
    det = pd.YoloPersonDetector()
    monkeypatch.setattr(det, "_load_training_data", lambda: None)
    det._custom_classes = []
    det._prompt_key = None
    fake = _FakeModel()

    def predict_no_person(frame, **kwargs):
        fake.calls.append(kwargs)
        # Solo un objeto no-persona → lista vacía de personas.
        return [_FakeResult([_FakeBox(0, 0.9, [0.0, 0.0, 1.0, 1.0])], names={0: "chair"})]

    fake.predict = predict_no_person
    det.model = fake
    frame = np.zeros((64, 64, 3), dtype=np.uint8)
    persons = det.detect_persons_in_frame(frame)
    assert persons == []
    assert fake.calls, "predict debe ejecutarse aunque no haya personas"


def test_legacy_weights_redirect_to_yoloe(monkeypatch):
    monkeypatch.delenv("YOLO_MODEL", raising=False)
    det = pd.YoloPersonDetector(model_name="yolo26n.pt")
    assert det.model_name == pd.DEFAULT_YOLOE_WEIGHTS
    det2 = pd.YoloPersonDetector(model_name="yolov8s-world.pt")
    assert det2.model_name == pd.DEFAULT_YOLOE_WEIGHTS


def test_predict_passes_iou_and_max_det(monkeypatch):
    monkeypatch.setenv("YOLO_IMGSZ", "320")
    monkeypatch.setenv("YOLO_CONFIDENCE", "0.4")
    monkeypatch.setenv("YOLO_CUSTOM_CONFIDENCE", "0.4")
    monkeypatch.setenv("YOLO_IOU", "0.5")
    monkeypatch.setenv("YOLO_MAX_DET", "25")
    monkeypatch.setenv("YOLO_MAX_SIDE", "0")
    det = pd.YoloPersonDetector()
    monkeypatch.setattr(det, "_load_training_data", lambda: None)
    det._custom_classes = []
    det._prompt_key = None
    fake = _FakeModel()
    det.model = fake
    frame = np.zeros((64, 64, 3), dtype=np.uint8)
    det.detect_persons_in_frame(frame)
    assert fake.calls
    assert fake.calls[0]["iou"] == 0.5
    assert fake.calls[0]["max_det"] == 25


def test_detect_labels_restores_prompts(monkeypatch):
    det = pd.YoloPersonDetector()
    monkeypatch.setattr(det, "_load_training_data", lambda: None)
    det._custom_classes = ["botella"]
    det._custom_vocabulary = []
    det._prompt_key = None
    fake = _FakeModel()

    def predict(frame, **kwargs):
        fake.calls.append({"classes": list(fake.classes or []), **kwargs})
        # Durante ad-hoc: person + mochila
        return [
            _FakeResult(
                [
                    _FakeBox(0, 0.9, [1.0, 2.0, 3.0, 4.0]),
                    _FakeBox(1, 0.85, [5.0, 6.0, 7.0, 8.0]),
                ],
                names={0: "person", 1: "mochila"},
            )
        ]

    fake.predict = predict
    det.model = fake
    # Fijar prompts del kiosco
    assert det.set_prompts() is True
    base_prompts = list(fake.classes)
    assert "person" in base_prompts
    assert "botella" in base_prompts

    hits = det.detect_labels(None, ["mochila"])
    assert hits and hits[0]["label"] == "mochila"
    # Tras ad-hoc se restauran prompts del kiosco
    assert fake.classes is not None
    assert "botella" in fake.classes
    assert "person" in fake.classes
