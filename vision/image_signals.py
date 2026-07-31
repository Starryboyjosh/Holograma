"""Señales de imagen para el matching de logos: HSV, glare, template y ORB.

Funciones puras sobre recortes de imagen, sin estado del detector ni YOLO.
Reciben las referencias ya calculadas (histogramas, plantillas, descriptores) en
lugar de ir a buscarlas, de modo que se pueden probar con matrices sintéticas
sin cargar Ultralytics ni el checkpoint.

``cv2`` y ``numpy`` se importan a nivel de módulo: antes se importaban dentro de
bucles que corren en cada frame.
"""

from __future__ import annotations

try:  # OpenCV es obligatorio en producción, opcional para importar el módulo.
    import cv2
except ImportError:  # pragma: no cover - entorno sin OpenCV
    cv2 = None

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None

# --- Firma de color HSV -------------------------------------------------
# Histograma 2D Hue×Saturation. Detecta si el parche tiene los colores del logo
# (amarillo+azul de ITEE, rojo+blanco de otro colegio...) sin hardcodear ninguno.
HSV_HUE_BINS = 18
HSV_SAT_BINS = 16

# --- Rechazo de ventanas / luz blanca -----------------------------------
# Un píxel "blanco" es poco saturado y muy brillante. Los umbrales anteriores
# (sat<35, val>195, ratio>55%) dejaban pasar ventanas con luz difusa, que
# rondan sat~38 / val~185.
GLARE_SAT_MAX = 40
GLARE_VAL_MIN = 180
GLARE_RATIO_MAX = 0.40
GLARE_MEAN_SAT_MAX = 32.0
GLARE_MEAN_VAL_MIN = 175.0

# --- Template matching ---------------------------------------------------
# 7 escalas relativas al ancho del ROI: el logo cambia mucho de tamaño según la
# distancia persona-cámara. Con 3-4 escalas fallaba de lejos y de muy cerca.
TEMPLATE_SCALES = (0.14, 0.20, 0.28, 0.38, 0.50, 0.65, 0.80)
TEMPLATE_MIN_SIDE = 16
# Desviación típica mínima: un ROI o template plano no tiene textura que
# matchear y vuelve inestable a TM_CCOEFF_NORMED.
ROI_MIN_STDDEV = 4.0
TEMPLATE_MIN_STDDEV = 8.0

# --- ORB -----------------------------------------------------------------
ORB_FEATURES = 700
ORB_RATIO = 0.75
ORB_MIN_GOOD_MATCHES = 14


def _is_bgr(img) -> bool:
    """True si es una imagen BGR de 3 canales con contenido."""
    if img is None or getattr(img, "size", 0) == 0:
        return False
    shape = getattr(img, "shape", ())
    return len(shape) == 3 and shape[2] == 3


def compute_hsv_hist(bgr_img):
    """Histograma 2D HSV normalizado, o ``None`` si la entrada no sirve."""
    if cv2 is None or not _is_bgr(bgr_img):
        return None
    try:
        hsv = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist(
            [hsv], [0, 1], None, [HSV_HUE_BINS, HSV_SAT_BINS], [0, 180, 0, 256]
        )
        cv2.normalize(hist, hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
        return hist
    except cv2.error:
        return None


def is_white_light_or_glare(bgr_crop) -> bool:
    """True si el recorte es sobre todo luz blanca / ventana / destello.

    El YOLOE etiqueta ventanas soleadas como "school uniform"; este filtro las
    descarta antes de intentar verificarlas contra la foto de Entrenar.
    """
    if cv2 is None or np is None or not _is_bgr(bgr_crop):
        return False
    try:
        hsv = cv2.cvtColor(bgr_crop, cv2.COLOR_BGR2HSV)
    except cv2.error:
        return False
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    white_ratio = float(
        np.mean(np.logical_and(sat < GLARE_SAT_MAX, val > GLARE_VAL_MIN))
    )
    mean_sat = float(np.mean(sat))
    mean_val = float(np.mean(val))
    return white_ratio > GLARE_RATIO_MAX or (
        mean_sat < GLARE_MEAN_SAT_MAX and mean_val > GLARE_MEAN_VAL_MIN
    )


def compare_hsv_signature(crop, ref_hists: list) -> float:
    """Correlación 0–1 del color del recorte contra histogramas de referencia.

    Devuelve ``1.0`` (no descartar) cuando no hay con qué comparar: sin
    referencias, en escala de grises, o si OpenCV falla. Devuelve ``0.0`` solo
    ante una discrepancia real de color.
    """
    if cv2 is None or crop is None or getattr(crop, "size", 0) == 0:
        return 1.0
    if not _is_bgr(crop):
        # Escala de grises / 1 canal: omitir el gating de color.
        return 1.0
    if not ref_hists:
        return 1.0
    crop_hist = compute_hsv_hist(crop)
    if crop_hist is None:
        return 1.0
    best = 0.0
    for ref_hist in ref_hists:
        if ref_hist is None:
            continue
        try:
            score = float(cv2.compareHist(ref_hist, crop_hist, cv2.HISTCMP_CORREL))
        except cv2.error:
            continue
        best = max(best, score)
    return max(0.0, best)


def _has_texture(img, min_stddev: float) -> bool:
    if np is None:
        return True
    try:
        return float(np.std(img)) >= min_stddev
    except (TypeError, ValueError):
        return True


def _equalized(gray):
    try:
        return cv2.equalizeHist(gray)
    except cv2.error:
        return gray


def match_template_multiscale(gray_roi, templates: list) -> tuple[float, tuple | None]:
    """Mejor score ``TM_CCOEFF_NORMED`` sobre una pirámide de 7 escalas.

    Devuelve ``(score, box_relativa_al_roi)``.
    """
    if cv2 is None or gray_roi is None or getattr(gray_roi, "size", 0) == 0:
        return 0.0, None
    if not templates:
        return 0.0, None
    if not _has_texture(gray_roi, ROI_MIN_STDDEV):
        return 0.0, None

    gray_roi = _equalized(gray_roi)
    rh, rw = gray_roi.shape[:2]
    best_score = 0.0
    best_box = None

    for tmpl in templates:
        if tmpl is None or getattr(tmpl, "size", 0) == 0:
            continue
        th0, tw0 = tmpl.shape[:2]
        if tw0 < 8 or th0 < 8:
            continue
        if not _has_texture(tmpl, TEMPLATE_MIN_STDDEV):
            continue
        aspect = th0 / float(tw0)
        for rel in TEMPLATE_SCALES:
            sw = max(TEMPLATE_MIN_SIDE, int(rw * rel))
            sh = max(TEMPLATE_MIN_SIDE, int(sw * aspect))
            if sw >= rw - 2 or sh >= rh - 2:
                continue
            try:
                resized = cv2.resize(tmpl, (sw, sh), interpolation=cv2.INTER_AREA)
                res = cv2.matchTemplate(gray_roi, resized, cv2.TM_CCOEFF_NORMED)
                _mn, mx, _ml, max_loc = cv2.minMaxLoc(res)
            except cv2.error:
                continue
            if mx > best_score:
                best_score = float(mx)
                x, y = int(max_loc[0]), int(max_loc[1])
                best_box = (float(x), float(y), float(x + sw), float(y + sh))

    return best_score, best_box


def match_orb(gray_roi, ref_descriptors: list) -> float:
    """Score 0–1 por coincidencias ORB contra descriptores de Entrenar."""
    if cv2 is None or gray_roi is None or getattr(gray_roi, "size", 0) == 0:
        return 0.0
    if not ref_descriptors:
        return 0.0

    gray_roi = _equalized(gray_roi)
    try:
        orb = cv2.ORB_create(ORB_FEATURES)
        _kp, des = orb.detectAndCompute(gray_roi, None)
    except cv2.error:
        return 0.0
    if des is None or len(des) < 6:
        return 0.0

    matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    best_good = 0
    for ref_des in ref_descriptors:
        if ref_des is None or len(ref_des) < 4:
            continue
        try:
            pairs = matcher.knnMatch(ref_des, des, k=2)
        except cv2.error:
            continue
        good = sum(
            1
            for pair in pairs
            if len(pair) >= 2 and pair[0].distance < ORB_RATIO * pair[1].distance
        )
        best_good = max(best_good, good)

    if best_good <= 0:
        return 0.0
    # Normalizar: ~ORB_MIN_GOOD_MATCHES coincidencias → score ~1.
    return min(1.0, best_good / float(max(8, ORB_MIN_GOOD_MATCHES)))
