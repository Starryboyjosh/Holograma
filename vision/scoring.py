"""Fusión ponderada por calidad de canales de logo (§13 I3).

Reemplaza la escalera ``if/elif`` de ``_match_logo_in_gray`` por:

    score = Σ(w_c · q_c_eff · s_c) / Σ(w_c · q_c_eff)

sobre tres canales (template, ORB, HSV). Cada canal aporta:

  - ``s_c``    : evidencia cruda del canal (0–1), o ``None`` si no hay
                 con qué comparar.
  - ``w_c``    : peso del canal.
  - ``q_c``    : piso de calidad del canal. Si la evidencia no lo alcanza,
                 el canal pesa proporcionalmente menos (q_c_eff < 1) en vez
                 de arrastrar un 1.0 silencioso.

Un canal **sin evidencia** (``s_c is None``) se elimina del numerador Y del
denominador. Ese es el arreglo estructural de la clase de bug que I1 corrige
puntualmente: un 1.0 por "no sé" inflaba la fusión igual que un match real.

Módulo puro: solo numpy, sin cv2. Tests en ``tests/test_vision_scoring.py``.
"""

from __future__ import annotations

import numpy as np

CHANNEL_WEIGHTS: dict[str, float] = {
    "template": 0.5,
    "orb": 0.3,
    "hsv": 0.2,
}

CHANNEL_FLOORS: dict[str, float] = {
    "template": 0.40,
    "orb": 0.50,
    "hsv": 0.30,
}


def fuse_logo_channels(
    scores: dict[str, float | None],
    weights: dict[str, float] | None = None,
    floors: dict[str, float] | None = None,
) -> float:
    """Fusión ponderada por calidad de los canales de logo.

    Parameters
    ----------
    scores:
        Evidencia cruda por canal (0–1). Un canal con valor ``None`` significa
        "sin evidencia" y se excluye del numerador y del denominador.
    weights:
        Peso por canal; ``CHANNEL_WEIGHTS`` si no se pasa.
    floors:
        Piso de calidad por canal; ``CHANNEL_FLOORS`` si no se pasa.

    Returns
    -------
    float
        Score fusionado 0–1. ``0.0`` si ningún canal tiene evidencia.
    """
    if not scores:
        return 0.0
    w_all = CHANNEL_WEIGHTS if weights is None else weights
    q_all = CHANNEL_FLOORS if floors is None else floors

    num = np.float64(0.0)
    den = np.float64(0.0)
    for name, s in scores.items():
        if s is None:
            continue  # Sin evidencia: fuera del numerador Y denominador.
        w = float(w_all.get(name, 0.0))
        if w <= 0.0:
            continue
        q = float(q_all.get(name, 1.0))
        q_eff = 1.0 if q <= 0.0 else float(np.clip(float(s) / q, 0.0, 1.0))
        num += w * q_eff * float(s)
        den += w * q_eff
    if den <= 0.0:
        return 0.0
    return float(np.clip(num / den, 0.0, 1.0))


def channel_quality_eff(s: float | None, q: float) -> float:
    """Calidad efectiva de un canal: 0 sin evidencia, 0–1 según el piso."""
    if s is None:
        return 0.0
    if q <= 0.0:
        return 1.0 if float(s) > 0.0 else 0.0
    return float(np.clip(float(s) / q, 0.0, 1.0))
