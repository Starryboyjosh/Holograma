"""Descriptor de persona desde las máscaras (§13 I5).

``yoloe-26n-seg`` ya calcula máscaras que hoy se descartan. Este módulo las
aprovecha para describir a cada persona con un vector compacto de color por
bandas corporales: histogramas HSV agrupados en 3 bandas horizontales
(cabeza/torso/piernas), L2-normalizados. Sirve para asociar la misma persona
entre ciclos (I6) sin usar ORB (inestable ante pose/cambio de ciclo).

Módulo puro: solo numpy. La conversión BGR→HSV y el redimensionado del frame
los hace el llamador (necesitan cv2); aquí solo se histograma y normaliza.
"""

from __future__ import annotations

import numpy as np

BANDS = 3
H_BINS = 8
S_BINS = 4
V_BINS = 4


def _band_hists(hsv_band: np.ndarray, mask_band: np.ndarray) -> np.ndarray | None:
    """Histogramas HSV de los píxeles de la persona en una banda.

    ``hsv_band`` es el frame HSV (H, W, 3) limitado a la banda; ``mask_band``
    es la máscara binaria de la persona en esa misma banda (H, W). Devuelve el
    vector concatenado [H.., S.., V..] o ``None`` si la banda no tiene píxeles.
    """
    pixels = hsv_band[mask_band > 0]
    if pixels.shape[0] == 0:
        return None
    hist = np.concatenate(
        [
            np.histogram(pixels[:, 0], bins=H_BINS, range=(0, 180))[0],
            np.histogram(pixels[:, 1], bins=S_BINS, range=(0, 256))[0],
            np.histogram(pixels[:, 2], bins=V_BINS, range=(0, 256))[0],
        ]
    ).astype(np.float64)
    norm = np.linalg.norm(hist)
    return hist / norm if norm > 0 else hist


def person_signature(mask: np.ndarray, hsv: np.ndarray) -> np.ndarray | None:
    """Descriptor de una persona: 3 bandas × (H+S+V) histograms L2-normalizado.

    Parameters
    ----------
    mask:
        Máscara de la persona (H, W), valores >0 = pertenece a la persona.
    hsv:
        Frame en espacio HSV (H, W, 3), de la MISMA resolución que *mask*.

    Returns
    -------
    np.ndarray or None
        Vector concatenado de las 3 bandas, L2-normalizado por banda. ``None``
        si la máscara no tiene píxeles o el frame no es válido.
    """
    if mask is None or hsv is None:
        return None
    if len(hsv.shape) != 3 or hsv.shape[2] < 3:
        return None
    if mask.shape[:2] != hsv.shape[:2]:
        return None
    h, w = mask.shape[:2]
    rows = np.argwhere(np.any(mask > 0, axis=1))
    if rows.shape[0] == 0:
        return None
    y0 = int(rows[:, 0].min())
    y1 = int(rows[:, 0].max()) + 1
    span = y1 - y0
    if span <= 0:
        return None
    out: list[np.ndarray] = []
    for b in range(BANDS):
        by0 = y0 + int(round(span * b / BANDS))
        by1 = y0 + int(round(span * (b + 1) / BANDS))
        by1 = max(by1, by0 + 1)
        by0 = min(by0, h - 1)
        by1 = min(by1, h)
        band_h = person_signature_band(mask[by0:by1, :], hsv[by0:by1, :])
        if band_h is None:
            return None
        out.append(band_h)
    return np.concatenate(out)


def person_signature_band(mask_band: np.ndarray, hsv_band: np.ndarray) -> np.ndarray | None:
    """Descriptor HSV de una banda: histogramas concatenados y L2-normalizados."""
    return _band_hists(hsv_band, mask_band)


def signature_distance(a: np.ndarray | None, b: np.ndarray | None) -> float:
    """Distancia (1 − coseno) entre dos descriptores, 1.0 si alguno es None.

    Los descriptores son L2-normalizados por banda, así que el coseno por banda
    coincide con el producto punto del vector concatenado.
    """
    if a is None or b is None:
        return 1.0
    a = np.asarray(a, dtype=np.float64).ravel()
    b = np.asarray(b, dtype=np.float64).ravel()
    if a.shape != b.shape or a.size == 0:
        return 1.0
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na <= 0 or nb <= 0:
        return 1.0
    return float(1.0 - float(np.dot(a, b) / (na * nb)))
