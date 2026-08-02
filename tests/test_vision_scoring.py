"""Fusión ponderada por calidad de canales de logo (§13 I3).

Tests del módulo puro ``vision/scoring.py``. No dependen de cv2 ni de
Ultralytics: solo numpy.
"""

import numpy as np

from vision.scoring import (
    CHANNEL_FLOORS,
    CHANNEL_WEIGHTS,
    channel_quality_eff,
    fuse_logo_channels,
)


def test_single_channel_without_floor_scales_to_score():
    """Un solo canal con peso 1.0 y evidencia s devuelve s."""
    out = fuse_logo_channels({"template": 0.6}, weights={"template": 1.0})
    assert out == 0.6


def test_fully_weighted_average():
    """Con dos canales sobre su piso, el resultado es la media ponderada."""
    out = fuse_logo_channels(
        {"template": 1.0, "orb": 1.0},
        weights={"template": 0.5, "orb": 0.5},
        floors={"template": 0.0, "orb": 0.0},
    )
    assert out == 1.0


def test_missing_evidence_removed_from_denominator():
    """I3: un canal sin evidencia (None) no aporta un 1.0 silencioso.

    template=1.0 con peso 0.5 y orb=None con peso 0.3 deben dar el valor del
    template, no bajar por el canal ausente.
    """
    out = fuse_logo_channels(
        {"template": 1.0, "orb": None},
        weights={"template": 0.5, "orb": 0.3},
        floors={"template": 0.0, "orb": 0.0},
    )
    assert out == 1.0


def test_no_evidence_returns_zero():
    assert fuse_logo_channels({"template": None, "orb": None}) == 0.0
    assert fuse_logo_channels({}) == 0.0


def test_below_floor_down_weights_channel():
    """Una evidencia bajo el piso pesa menos que una por encima."""
    high = fuse_logo_channels(
        {"template": 0.9, "orb": 0.9},
        weights={"template": 0.5, "orb": 0.5},
        floors={"template": 0.4, "orb": 0.4},
    )
    low = fuse_logo_channels(
        {"template": 0.9, "orb": 0.1},
        weights={"template": 0.5, "orb": 0.5},
        floors={"template": 0.4, "orb": 0.4},
    )
    assert high > low


def test_channel_quality_eff():
    """q_eff es 0 sin evidencia, 1 sobre el piso, y fracción bajo él."""
    assert channel_quality_eff(None, 0.5) == 0.0
    assert channel_quality_eff(0.8, 0.5) == 1.0
    assert np.isclose(channel_quality_eff(0.2, 0.5), 0.4)
    assert channel_quality_eff(0.0, 0.5) == 0.0


def test_default_weights_floors_are_valid():
    """Los pesos suman 1.0 y los pisos están en [0, 1]."""
    assert np.isclose(sum(CHANNEL_WEIGHTS.values()), 1.0)
    assert all(0.0 <= q <= 1.0 for q in CHANNEL_FLOORS.values())
    assert set(CHANNEL_WEIGHTS) == set(CHANNEL_FLOORS) == {
        "template",
        "orb",
        "hsv",
    }


def test_weighted_hsv_only_matches_weighted_average():
    """HSV con evidencia perfecta y pisos en 0 da la media ponderada."""
    out = fuse_logo_channels(
        {"template": 0.5, "orb": 0.5, "hsv": 1.0},
        weights={"template": 0.5, "orb": 0.3, "hsv": 0.2},
        floors={"template": 0.0, "orb": 0.0, "hsv": 0.0},
    )
    assert np.isclose(out, 0.5 * 0.5 + 0.3 * 0.5 + 0.2 * 1.0)
