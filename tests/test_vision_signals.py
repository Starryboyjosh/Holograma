"""Tests de `vision.image_signals` con imágenes sintéticas (sin cámara ni YOLO).

Cubre el rechazo de ventanas/luz blanca, que es el falso positivo que más ha
costado en el kiosko: el YOLOE etiqueta una ventana soleada como "school
uniform" y la verificación contra la foto de Entrenar la aceptaba porque
buscaba el logo en el pecho de la persona, no en la ventana (§4.8 del handoff).
"""

import numpy as np
import pytest

from vision import image_signals as s


def _solid(h, w, bgr):
    img = np.zeros((h, w, 3), dtype=np.uint8)
    img[:, :] = bgr
    return img


def _noise(h, w, seed=0):
    rng = np.random.default_rng(seed)
    return rng.integers(0, 255, size=(h, w, 3), dtype=np.uint8)


# --- Glare / ventanas ---


def test_white_window_is_glare():
    assert s.is_white_light_or_glare(_solid(60, 60, (250, 250, 250))) is True


def test_diffuse_window_light_is_glare():
    """El caso que se escapaba con los umbrales viejos (sat~38, val~185)."""
    img = _solid(60, 60, (190, 188, 186))
    assert s.is_white_light_or_glare(img) is True


def test_saturated_colour_is_not_glare():
    assert s.is_white_light_or_glare(_solid(60, 60, (200, 30, 30))) is False


def test_dark_patch_is_not_glare():
    assert s.is_white_light_or_glare(_solid(60, 60, (20, 20, 20))) is False


def test_glare_ignores_invalid_input():
    assert s.is_white_light_or_glare(None) is False
    assert s.is_white_light_or_glare(np.zeros((0, 0, 3), dtype=np.uint8)) is False
    assert s.is_white_light_or_glare(np.zeros((10, 10), dtype=np.uint8)) is False


# --- Firma de color HSV ---


def test_hsv_hist_shape():
    hist = s.compute_hsv_hist(_noise(40, 40))
    assert hist is not None
    assert hist.shape == (s.HSV_HUE_BINS, s.HSV_SAT_BINS)


def test_hsv_hist_rejects_non_bgr():
    assert s.compute_hsv_hist(np.zeros((10, 10), dtype=np.uint8)) is None
    assert s.compute_hsv_hist(None) is None


def test_same_colour_correlates_high():
    ref = s.compute_hsv_hist(_solid(40, 40, (200, 30, 30)))
    score = s.compare_hsv_signature(_solid(40, 40, (200, 30, 30)), [ref])
    assert score > 0.9


def test_different_colour_correlates_low():
    ref = s.compute_hsv_hist(_solid(40, 40, (30, 30, 200)))  # rojo intenso
    score = s.compare_hsv_signature(_solid(40, 40, (200, 30, 30)), [ref])  # azul
    assert score < 0.5


def test_no_reference_does_not_reject():
    """Sin histogramas de referencia no se puede descartar por color."""
    assert s.compare_hsv_signature(_solid(20, 20, (1, 2, 3)), []) == 1.0


def test_grayscale_skips_colour_gating():
    assert s.compare_hsv_signature(np.zeros((20, 20), dtype=np.uint8), [None]) == 1.0


# --- Template multiescala ---


def test_template_found_inside_roi():
    rng = np.random.default_rng(7)
    roi = rng.integers(0, 255, size=(200, 200), dtype=np.uint8)
    # Incrusta un parche con textura propia y lo usa como plantilla.
    patch = rng.integers(0, 255, size=(40, 40), dtype=np.uint8)
    roi[80:120, 60:100] = patch
    score, box = s.match_template_multiscale(roi, [patch])
    assert score > 0.5
    assert box is not None


def test_flat_roi_has_no_texture_to_match():
    flat = np.full((100, 100), 128, dtype=np.uint8)
    patch = np.random.default_rng(1).integers(0, 255, size=(20, 20), dtype=np.uint8)
    assert s.match_template_multiscale(flat, [patch]) == (0.0, None)


def test_flat_template_is_skipped():
    rng = np.random.default_rng(2)
    roi = rng.integers(0, 255, size=(120, 120), dtype=np.uint8)
    flat_tmpl = np.full((20, 20), 200, dtype=np.uint8)
    assert s.match_template_multiscale(roi, [flat_tmpl]) == (0.0, None)


def test_template_handles_empty_inputs():
    assert s.match_template_multiscale(None, [np.zeros((9, 9), np.uint8)]) == (0.0, None)
    assert s.match_template_multiscale(np.zeros((9, 9), np.uint8), []) == (0.0, None)


def test_tiny_templates_are_ignored():
    rng = np.random.default_rng(3)
    roi = rng.integers(0, 255, size=(120, 120), dtype=np.uint8)
    assert s.match_template_multiscale(roi, [np.zeros((4, 4), np.uint8)]) == (0.0, None)


# --- ORB ---


def test_orb_matches_itself():
    import cv2

    rng = np.random.default_rng(11)
    img = rng.integers(0, 255, size=(160, 160), dtype=np.uint8)
    orb = cv2.ORB_create(s.ORB_FEATURES)
    _kp, des = orb.detectAndCompute(img, None)
    assert des is not None
    assert s.match_orb(img, [des]) > 0.5


def test_orb_without_references_is_none():
    """WAVE-19 (I9): sin descriptores de referencia no hay evidencia → None."""
    rng = np.random.default_rng(12)
    img = rng.integers(0, 255, size=(80, 80), dtype=np.uint8)
    assert s.match_orb(img, []) is None
    assert s.match_orb(img, [None]) is None


def test_orb_handles_empty_roi():
    assert s.match_orb(None, [np.zeros((10, 32), np.uint8)]) is None


@pytest.mark.parametrize("value", [0, 255])
def test_orb_on_featureless_image_is_none(value):
    """ROI plano: ORB no extrae keypoints → sin evidencia → None (no 0.0)."""
    flat = np.full((80, 80), value, dtype=np.uint8)
    assert s.match_orb(flat, [np.zeros((10, 32), np.uint8)]) is None


def test_match_logo_ladder_uses_template_only_when_orb_is_none(monkeypatch):
    """WAVE-19 (I9): ORB=None no arrastra el score combinado a 0.75·tmpl.

    Con un ROI liso (sin keypoints → None), el conf de la rama template debe
    ser solo el del template, no 0.75·tmpl + 0.25·0. El umbral efectivo pasa a
    0.42 (no 0.56), que era el bug de logos bordados pequeños con ORB=0.
    """
    import vision.person_detector as pd

    det = pd.YoloPersonDetector()
    det._load_training_data = lambda: None
    det._maybe_reload_training = lambda: None
    det._logo_templates = {"Logo ITEE": [np.ones((16, 16), dtype=np.uint8)]}
    det._logo_images = {"Logo ITEE": [np.ones((16, 16), dtype=np.uint8)]}
    det._logo_hsv_hists = {}

    # ORB sin evidencia (ROI liso) y template perfecto en localización.
    monkeypatch.setattr(pd, "match_orb", lambda *a, **k: None)
    monkeypatch.setattr(
        pd,
        "match_template_multiscale",
        lambda *a, **k: (0.60, (2.0, 2.0, 14.0, 14.0)),
    )

    flat = np.full((80, 80, 3), 200, dtype=np.uint8)
    score, rel_box, method = det._match_logo_in_gray(flat, "Logo ITEE")
    assert rel_box is not None
    # Template-only: 0.60, NO 0.75*0.60 + 0.25*0.0 = 0.45.
    assert abs(score - 0.60) < 1e-6
    assert method == "template"

    # Con ORB=0.0 (evidencia negativa) el conf combinado sí baja.
    monkeypatch.setattr(pd, "match_orb", lambda *a, **k: 0.0)
    score2, rel_box2, _method2 = det._match_logo_in_gray(flat, "Logo ITEE")
    assert rel_box2 is not None
    assert abs(score2 - 0.75 * 0.60) < 1e-6
