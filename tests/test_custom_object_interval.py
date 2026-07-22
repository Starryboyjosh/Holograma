"""Inferencia única YOLOE: personas + custom en el mismo predict.

Antes había un modelo COCO + YOLOE aparte con throttle. Ahora un solo
``yoloe-26n-seg`` hace ambas cosas en ``analyze_frame`` / ``_detect_all``.
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
    """Modelo open-vocab falso: set_classes + un predict con person + custom."""

    def __init__(self):
        self.predict_calls = 0
        self.classes = None

    def set_classes(self, names, pe=None):  # noqa: ARG002
        self.classes = list(names)

    def get_text_pe(self, names):  # noqa: ARG002
        return None

    def predict(self, frame, **kwargs):  # noqa: ARG002
        self.predict_calls += 1
        # cls 0 = person, cls 1 = botella (según set_classes)
        return [
            _FakeResult(
                [
                    _FakeBox(0.95, 0, [1, 2, 3, 4]),
                    _FakeBox(0.9, 1, [10, 20, 30, 40]),
                ],
                {0: "person", 1: "botella"},
            )
        ]


def _make_detector(monkeypatch):
    det = pd.YoloPersonDetector()
    monkeypatch.setattr(det, "_load_training_data", lambda: None)
    det._custom_classes = ["botella"]
    det._custom_vocabulary = []
    det._prompt_key = None
    det._logo_templates = {}
    fake = _FakeModel()
    det.model = fake
    det._person_model = None
    return det, fake


def test_analyze_frame_single_predict_splits_person_and_custom(monkeypatch):
    det, fake = _make_detector(monkeypatch)
    out = det.analyze_frame(frame=None)
    assert fake.predict_calls == 1
    assert out["person_count"] == 1
    assert out["custom_count"] == 1
    assert out["custom_objects"][0]["label"] == "botella"
    assert "person" in (fake.classes or [])
    assert "botella" in (fake.classes or [])


def test_detect_all_applies_person_and_custom_prompts(monkeypatch):
    det, fake = _make_detector(monkeypatch)
    persons, custom = det._detect_all(frame=None)
    assert len(persons) == 1
    assert len(custom) == 1
    assert fake.classes is not None
    assert fake.classes[0] in ("person", "persona")


def test_no_custom_still_detects_person(monkeypatch):
    det, fake = _make_detector(monkeypatch)
    det._custom_classes = []
    det._custom_vocabulary = []
    det._prompt_key = None

    def predict_person_only(frame, **kwargs):
        fake.predict_calls += 1
        return [_FakeResult([_FakeBox(0.9, 0, [1, 2, 3, 4])], {0: "person"})]

    fake.predict = predict_person_only
    persons, custom = det._detect_all(frame=None)
    assert persons and not custom
    assert fake.predict_calls == 1


def test_uniform_alias_maps_to_operator_label(monkeypatch):
    det, fake = _make_detector(monkeypatch)
    det._custom_classes = ["Uniforme ITEE"]
    det._prompt_key = None

    def predict_alias(frame, **kwargs):
        fake.predict_calls += 1
        # Persona [0,0,100,100] + uniforme en pecho-logo (x~12-52%, y~46-64%).
        return [
            _FakeResult(
                [
                    _FakeBox(0.95, 0, [0, 0, 100, 100]),
                    _FakeBox(0.88, 1, [20, 48, 45, 62]),
                ],
                {0: "person", 1: "school uniform"},
            )
        ]

    fake.predict = predict_alias
    _, custom = det._detect_all(frame=None)
    assert custom and custom[0]["label"] == "Uniforme ITEE"


def test_uniform_open_vocab_outside_chest_is_dropped(monkeypatch):
    """Open-vocab en cuello/hombro no cuenta como uniforme."""
    det, fake = _make_detector(monkeypatch)
    det._custom_classes = ["Uniforme ITEE"]
    det._prompt_key = None

    def predict_neck(frame, **kwargs):
        fake.predict_calls += 1
        return [
            _FakeResult(
                [
                    _FakeBox(0.95, 0, [0, 0, 100, 100]),
                    # Centro ~ (80, 30) = pecho derecho / cuello (fuera de logo izq.)
                    _FakeBox(0.90, 1, [70, 20, 90, 40]),
                ],
                {0: "person", 1: "school uniform"},
            )
        ]

    fake.predict = predict_neck
    _, custom = det._detect_all(frame=None)
    assert custom == []
