"""Inferencia única YOLOE: personas + custom en el mismo predict.

Antes había un modelo COCO + YOLOE aparte con throttle. Ahora un solo
``yoloe-26n-seg`` hace ambas cosas en ``analyze_frame`` / ``_detect_all``.
Logos de Entrenar se validan por imagen de referencia (template/ORB), no por color.
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
    # Evitar que _detect_all recargue training_metadata y repueble plantillas.
    monkeypatch.setattr(det, "_load_training_data", lambda: None)
    monkeypatch.setattr(det, "_maybe_reload_training", lambda: None)
    monkeypatch.setattr(det, "_rebuild_logo_templates", lambda: None)
    det._custom_classes = ["botella"]
    det._custom_vocabulary = []
    det._prompt_key = None
    # Sin plantillas: tests de geometría open-vocab no dependen de fotos Entrenar.
    det._logo_templates = {}
    det._logo_images = {}
    fake = _FakeModel()
    det.model = fake
    det._model_kind = "mock"
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
        # Persona [0,0,100,100] + uniforme en pecho-logo (y~0.40–0.55, x~0.15–0.40).
        return [
            _FakeResult(
                [
                    _FakeBox(0.95, 0, [0, 0, 100, 100]),
                    _FakeBox(0.88, 1, [15, 40, 42, 55]),
                ],
                {0: "person", 1: "school uniform"},
            )
        ]

    fake.predict = predict_alias
    _, custom = det._detect_all(frame=None)
    assert custom and custom[0]["label"] == "Uniforme ITEE"
    # Caja reanclada al ROI pecho (no cuello).
    box = custom[0]["box"]
    cy = 0.5 * (box[1] + box[3])
    assert cy >= 34  # por debajo de la zona cuello (~0.34)


def test_uniform_on_collar_is_rejected_or_snapped_off_neck(monkeypatch):
    """Open-vocab en el placket del cuello no debe dibujar el cuadro ahí."""
    det, fake = _make_detector(monkeypatch)
    det._custom_classes = ["Uniforme ITEE"]
    det._prompt_key = None

    def predict_collar(frame, **kwargs):
        fake.predict_calls += 1
        return [
            _FakeResult(
                [
                    _FakeBox(0.95, 0, [0, 0, 100, 100]),
                    # Centro y≈0.22 → cuello/placket (como en la captura real).
                    _FakeBox(0.90, 1, [40, 15, 60, 30]),
                ],
                {0: "person", 1: "school uniform"},
            )
        ]

    fake.predict = predict_collar
    _, custom = det._detect_all(frame=None)
    assert custom == []


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


def test_uniform_open_vocab_low_conf_dropped(monkeypatch):
    """Open-vocab de uniforme exige conf más alta que objetos genéricos."""
    det, fake = _make_detector(monkeypatch)
    det._custom_classes = ["Uniforme ITEE"]
    det._prompt_key = None
    det.uniform_ov_confidence = 0.45
    det.logo_ov_confidence = 0.45

    def predict_weak(frame, **kwargs):
        fake.predict_calls += 1
        return [
            _FakeResult(
                [
                    _FakeBox(0.95, 0, [0, 0, 100, 100]),
                    _FakeBox(0.25, 1, [20, 48, 45, 62]),  # pecho pero conf baja
                ],
                {0: "person", 1: "school uniform"},
            )
        ]

    fake.predict = predict_weak
    _, custom = det._detect_all(frame=None)
    assert custom == []


def test_logo_trained_open_vocab_requires_reference_match(monkeypatch):
    """Con fotos Entrenar, open-vocab sin match de plantilla no cuenta."""
    import numpy as np

    det, fake = _make_detector(monkeypatch)
    det._custom_classes = ["Uniforme ITEE"]
    det._prompt_key = None
    det._logo_images = {"Uniforme ITEE": [np.ones((40, 40), dtype=np.uint8) * 255]}
    det._logo_templates = {}

    def predict(frame, **kwargs):
        fake.predict_calls += 1
        return [
            _FakeResult(
                [
                    _FakeBox(0.95, 0, [0, 0, 100, 100]),
                    _FakeBox(0.9, 1, [15, 40, 42, 55]),
                ],
                {0: "person", 1: "school uniform"},
            )
        ]

    fake.predict = predict
    frame = np.zeros((120, 100, 3), dtype=np.uint8)
    _, custom = det._detect_all(frame=frame)
    assert custom == []


def test_logo_ref_from_template_match(monkeypatch):
    """Template de Entrenar en el pecho produce source logo_ref."""
    import numpy as np
    import cv2

    det = pd.YoloPersonDetector()
    monkeypatch.setattr(det, "_load_training_data", lambda: None)
    monkeypatch.setattr(det, "_maybe_reload_training", lambda: None)
    monkeypatch.setattr(det, "_rebuild_logo_templates", lambda: None)
    det._custom_classes = ["Logo Colegio X"]
    det._custom_vocabulary = []
    det._prompt_key = None
    det.model = None
    tmpl = np.zeros((48, 48), dtype=np.uint8)
    tmpl[10:38, 10:38] = 200
    tmpl[18:30, 18:30] = 40
    det._logo_images = {"Logo Colegio X": [tmpl]}
    det._logo_templates = {}

    frame = np.zeros((200, 160, 3), dtype=np.uint8)
    persons = [{"box": (10, 10, 150, 190), "confidence": 0.9}]
    rois = det._person_chest_rois(frame, persons)
    assert rois, "debe haber ROI pecho"
    _crop, (ox1, oy1, ox2, oy2), _pb = rois[0]
    ch, cw = _crop.shape[:2]
    sw, sh = max(24, cw // 3), max(24, ch // 3)
    patch = cv2.resize(tmpl, (sw, sh), interpolation=cv2.INTER_AREA)
    y0 = max(0, (ch - sh) // 2)
    x0 = max(0, (cw - sw) // 2)
    frame[oy1 + y0 : oy1 + y0 + sh, ox1 + x0 : ox1 + x0 + sw] = cv2.cvtColor(
        patch, cv2.COLOR_GRAY2BGR
    )

    hits = det._detect_logo_templates(frame, persons=persons)
    assert hits, hits
    assert hits[0]["label"] == "Logo Colegio X"
    assert hits[0]["source"] == "logo_ref"
    assert hits[0]["confidence"] >= 0.55
