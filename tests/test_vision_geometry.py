"""Tests de `vision.geometry` y de la prioridad de fuentes del detector.

La geometría es aritmética pura: antes vivía dentro de ``YoloPersonDetector`` y
probarla obligaba a instanciar el detector (y con él, Ultralytics).
"""

import pytest

from vision import geometry as g
from vision.person_detector import YoloPersonDetector

PERSON = (0.0, 0.0, 200.0, 400.0)  # 200x400 px


# --- ROI del pecho ---


def test_roi_defaults(monkeypatch):
    for var in ("YOLO_LOGO_Y0", "YOLO_LOGO_Y1", "YOLO_LOGO_X0", "YOLO_LOGO_X1",
                "YOLO_COLLAR_Y_MAX", "YOLO_LOGO_MIRROR"):
        monkeypatch.delenv(var, raising=False)
    y0, y1, x0, x1 = g.logo_roi_fractions()
    assert (round(y0, 2), round(y1, 2)) == (0.26, 1.0)
    assert (round(x0, 2), round(x1, 2)) == (0.0, 1.0)


def test_roi_never_climbs_into_the_collar(monkeypatch):
    """Aunque se configure un ROI altísimo, no puede invadir el cuello."""
    monkeypatch.setenv("YOLO_LOGO_Y0", "0.05")
    monkeypatch.setenv("YOLO_COLLAR_Y_MAX", "0.34")
    y0, _, _, _ = g.logo_roi_fractions()
    assert y0 > g.collar_y_max()


def test_mirror_flips_horizontal_band(monkeypatch):
    monkeypatch.setenv("YOLO_LOGO_X0", "0.10")
    monkeypatch.setenv("YOLO_LOGO_X1", "0.40")
    monkeypatch.setenv("YOLO_LOGO_MIRROR", "1")
    _, _, x0, x1 = g.logo_roi_fractions()
    assert (round(x0, 2), round(x1, 2)) == (0.60, 0.90)


def test_collar_is_clamped_to_sane_range(monkeypatch):
    monkeypatch.setenv("YOLO_COLLAR_Y_MAX", "9.0")
    assert g.collar_y_max() == 0.45
    monkeypatch.setenv("YOLO_COLLAR_Y_MAX", "-1")
    assert g.collar_y_max() == 0.10


# --- Zona / pertenencia ---


def test_point_in_chest_is_accepted():
    # y=0.45 del alto (180/400), x=0.25 del ancho (50/200): dentro del ROI.
    assert g.point_in_logo_zone(50.0, 180.0, PERSON) is True


def test_point_on_collar_is_rejected():
    # y=0.10 → cuello/cara.
    assert g.point_in_logo_zone(50.0, 40.0, PERSON) is False


def test_point_outside_horizontal_band_is_rejected():
    # x = -10 (fuera de la persona)
    assert g.point_in_logo_zone(-10.0, 180.0, PERSON) is False


def test_rel_center_is_normalised():
    rel = g.rel_center_on_person((90.0, 190.0, 110.0, 210.0), PERSON)
    assert rel == pytest.approx((0.5, 0.5))


def test_rel_center_handles_garbage():
    assert g.rel_center_on_person(None, PERSON) is None
    assert g.rel_center_on_person((1, 2), PERSON) is None


# --- Snap ---


def test_snap_enlarges_a_tiny_box():
    """El bug histórico: template match de 20x20 px, invisible en el vídeo."""
    tiny = (95.0, 185.0, 115.0, 205.0)  # 20x20
    x1, y1, x2, y2 = g.snap_box_to_logo_zone(tiny, PERSON)
    assert (x2 - x1) >= g.SNAP_MIN_SIDE_PX
    assert (y2 - y1) >= g.SNAP_MIN_SIDE_PX


def test_snap_keeps_box_inside_the_person():
    x1, y1, x2, y2 = g.snap_box_to_logo_zone((0.0, 0.0, 5.0, 5.0), PERSON)
    assert x1 >= PERSON[0] and y1 >= PERSON[1]
    assert x2 <= PERSON[2] and y2 <= PERSON[3]


def test_snap_pulls_a_collar_box_down_to_the_chest():
    """Una caja en el cuello debe acabar por debajo del umbral de cuello."""
    collar_box = (80.0, 10.0, 120.0, 40.0)
    _, y1, _, y2 = g.snap_box_to_logo_zone(collar_box, PERSON)
    center_rel_y = (0.5 * (y1 + y2) - PERSON[1]) / (PERSON[3] - PERSON[1])
    assert center_rel_y > g.collar_y_max()


def test_snap_preserves_detected_location_anywhere_on_body():
    """Un logo en el brazo derecho o cintura mantiene su centro sin saltar al pecho izquierdo."""
    body_box = (150.0, 250.0, 170.0, 270.0)
    x1, y1, x2, y2 = g.snap_box_to_logo_zone(body_box, PERSON)
    cx = 0.5 * (x1 + x2)
    cy = 0.5 * (y1 + y2)
    assert cx == pytest.approx(160.0, abs=15.0)
    assert cy == pytest.approx(260.0, abs=15.0)


def test_snap_does_not_shrink_a_large_box():
    big = (20.0, 150.0, 180.0, 250.0)
    x1, y1, x2, y2 = g.snap_box_to_logo_zone(big, PERSON)
    assert (x2 - x1) >= 100.0 and (y2 - y1) >= 100.0


# --- Persona asociada ---


def test_containing_person_wins():
    persons = [{"box": (0, 0, 200, 400)}, {"box": (500, 500, 600, 600)}]
    assert g.best_person_for_box((50, 150, 60, 160), persons) == (0.0, 0.0, 200.0, 400.0)


def test_largest_container_wins_when_nested():
    persons = [{"box": (40, 140, 80, 180)}, {"box": (0, 0, 200, 400)}]
    assert g.best_person_for_box((50, 150, 60, 160), persons) == (0.0, 0.0, 200.0, 400.0)


def test_nearest_person_when_none_contains():
    persons = [{"box": (0, 0, 10, 10)}, {"box": (900, 900, 1000, 1000)}]
    assert g.best_person_for_box((20, 20, 30, 30), persons) == (0.0, 0.0, 10.0, 10.0)


def test_no_persons_returns_none():
    assert g.best_person_for_box((1, 2, 3, 4), []) is None
    assert g.best_person_for_box((1, 2, 3, 4), [{"box": None}]) is None


# --- Escalado / clamp ---


class _Frame:
    def __init__(self, h, w):
        self.shape = (h, w, 3)


def test_scale_back_from_resized_frame():
    assert g.compute_scale_back(_Frame(720, 1280), _Frame(360, 640)) == 2.0


def test_scale_back_is_one_when_not_resized():
    frame = _Frame(720, 1280)
    assert g.compute_scale_back(frame, frame) == 1.0
    assert g.compute_scale_back(None, None) == 1.0


def test_scale_box_applies_factor():
    assert g.scale_box((1.0, 2.0, 3.0, 4.0), 2.0) == (2.0, 4.0, 6.0, 8.0)


def test_clamp_box_to_frame_bounds():
    assert g.clamp_box_to_frame((-50, -50, 5000, 5000), (480, 640, 3)) == (0, 0, 640, 480)


def test_clamp_box_rejects_garbage():
    assert g.clamp_box_to_frame(None, (480, 640, 3)) is None
    assert g.clamp_box_to_frame((1, 2), (480, 640, 3)) is None
    assert g.clamp_box_to_frame(("a", "b", "c", "d"), (480, 640, 3)) is None


def test_xyxy_accepts_tensor_like_and_list():
    class Tensorish:
        def tolist(self):
            return [1, 2, 3, 4]

    assert g.xyxy_tuple(Tensorish()) == (1.0, 2.0, 3.0, 4.0)
    assert g.xyxy_tuple([5, 6, 7, 8]) == (5.0, 6.0, 7.0, 8.0)


# --- Prioridad de fuente (regresión del bug de dedupe) ---


def _obj(source, confidence, label="Uniforme ITEE"):
    return {"label": label, "confidence": confidence, "source": source, "box": (1, 1, 2, 2)}


def test_verified_logo_beats_higher_confidence_open_vocab():
    """Regresión: el open-vocab desplazaba al match verificado por plantilla.

    `_dedupe_custom` ordenaba solo por confianza y la preferencia por fuente se
    aplicaba después, sobre una lista ya colapsada a 1 por label — nunca surtía
    efecto. §4.3 del handoff dice que `logo_ref` es la señal preferida.
    """
    out = YoloPersonDetector._dedupe_custom(
        [_obj("logo_ref", 0.70), _obj("open_vocab_snapped", 0.92)]
    )
    assert len(out) == 1
    assert out[0]["source"] == "logo_ref"


def test_order_of_input_does_not_matter():
    out = YoloPersonDetector._dedupe_custom(
        [_obj("open_vocab_snapped", 0.92), _obj("logo_ref", 0.70)]
    )
    assert out[0]["source"] == "logo_ref"


@pytest.mark.parametrize("verified", ["logo_ref", "logo_ref_verified", "logo_chest"])
def test_every_verified_source_outranks_open_vocab(verified):
    out = YoloPersonDetector._dedupe_custom(
        [_obj("open_vocab_snapped", 0.99), _obj(verified, 0.50)]
    )
    assert out[0]["source"] == verified


def test_confidence_still_breaks_ties_within_same_source():
    out = YoloPersonDetector._dedupe_custom(
        [_obj("logo_ref", 0.55), _obj("logo_ref", 0.80)]
    )
    assert out[0]["confidence"] == 0.80


def test_distinct_labels_are_kept():
    out = YoloPersonDetector._dedupe_custom(
        [_obj("logo_ref", 0.7, label="A"), _obj("open_vocab_snapped", 0.9, label="B")]
    )
    assert {o["label"] for o in out} == {"A", "B"}
