"""Geometría de cajas y ROI del pecho, sin dependencias de YOLO ni de OpenCV.

Todo aquí es **función pura**: entra una caja, sale una caja. Vivía dentro de
``YoloPersonDetector`` mezclado con la inferencia, lo que obligaba a instanciar
el detector (y por tanto a cargar Ultralytics) para probar aritmética de
rectángulos.

Convención de fracciones respecto a la caja de la persona:
``0`` = arriba/izquierda, ``1`` = abajo/derecha.
"""

from __future__ import annotations

import os

from utils import _env_float

# Geometría del logo relativa a la caja persona (YOLO):
#   y ∈ [0.36, 0.58]  → pecho (bajo el cuello; el placket suele estar en y<0.34)
#   x ∈ [0.08, 0.48]  → pecho izquierdo en la imagen del kiosco
#   YOLO_LOGO_MIRROR=1 si el logo sale al otro lado (cámara espejo).
LOGO_Y0 = 0.36
LOGO_Y1 = 0.58
LOGO_X0 = 0.08
LOGO_X1 = 0.48
COLLAR_Y_MAX = 0.34  # por encima = cuello / placket / cara

# Tamaño mínimo de la caja del logo, en fracción de la zona del pecho. Los
# logos bordados ocupan un área visible considerable; con 0.30/0.38 el overlay
# dibujaba cuadros de ~20 px, invisibles en el vídeo del kiosko.
SNAP_MIN_W_FRACTION = 0.55
SNAP_MIN_H_FRACTION = 0.65
SNAP_MIN_SIDE_PX = 50.0

# Margen que se deja a cada lado al clampear el centro dentro del pecho.
SNAP_CENTER_MARGIN = 0.10


def logo_roi_fractions() -> tuple[float, float, float, float]:
    """``(y0, y1, x0, x1)`` del ROI del logo en fracciones de la caja persona.

    Vertical = pecho bajo el cuello. Horizontal = lado del logo bordado.
    """
    y0 = _env_float("YOLO_LOGO_Y0", LOGO_Y0)
    y1 = _env_float("YOLO_LOGO_Y1", LOGO_Y1)
    x0 = _env_float("YOLO_LOGO_X0", LOGO_X0)
    x1 = _env_float("YOLO_LOGO_X1", LOGO_X1)
    if os.getenv("YOLO_LOGO_MIRROR", "0").lower() in ("1", "true", "yes"):
        x0, x1 = 1.0 - x1, 1.0 - x0
    # Clamp: nunca subir el ROI al cuello (y0 >= collar).
    collar = _env_float("YOLO_COLLAR_Y_MAX", COLLAR_Y_MAX)
    y0 = max(collar + 0.02, min(0.70, y0))
    y1 = max(y0 + 0.10, min(0.85, y1))
    x0 = max(0.0, min(0.80, x0))
    x1 = max(x0 + 0.12, min(1.0, x1))
    return y0, y1, x0, x1


def collar_y_max() -> float:
    """Fracción por encima de la cual empieza el cuello (nunca es el logo)."""
    return max(0.20, min(0.45, _env_float("YOLO_COLLAR_Y_MAX", COLLAR_Y_MAX)))


def xyxy_tuple(xyxy) -> tuple[float, float, float, float]:
    """Normaliza ``box.xyxy[0]`` de Ultralytics (tensor) o de fakes de test (list)."""
    vals = xyxy.tolist() if hasattr(xyxy, "tolist") else list(xyxy)
    return float(vals[0]), float(vals[1]), float(vals[2]), float(vals[3])


def compute_scale_back(frame, prepared) -> float:
    """Factor para reescalar cajas del frame reducido al frame original."""
    if prepared is None or frame is None or prepared is frame:
        return 1.0
    try:
        return frame.shape[1] / float(prepared.shape[1])
    except (AttributeError, IndexError, ZeroDivisionError, TypeError):
        return 1.0


def scale_box(box, scale_back) -> tuple[float, float, float, float]:
    """Reescala una caja ``(x1, y1, x2, y2)`` si ``scale_back != 1.0``."""
    if scale_back == 1.0:
        return box
    x1, y1, x2, y2 = box
    return (x1 * scale_back, y1 * scale_back, x2 * scale_back, y2 * scale_back)


def chest_zone(person_box: tuple) -> tuple[float, float, float, float]:
    """Rectángulo absoluto del pecho ``(x1, y1, x2, y2)`` de una persona."""
    px1, py1, px2, py2 = (float(v) for v in person_box)
    p_h = max(1.0, py2 - py1)
    p_w = max(1.0, px2 - px1)
    y0r, y1r, x0r, x1r = logo_roi_fractions()
    return (
        px1 + x0r * p_w,
        py1 + y0r * p_h,
        px1 + x1r * p_w,
        py1 + y1r * p_h,
    )


def point_in_logo_zone(
    cx: float, cy: float, person_box: tuple, tol: float = 0.04
) -> bool:
    """True si el centro ``(cx, cy)`` cae en el pecho-logo de la persona."""
    px1, py1, px2, py2 = person_box
    p_h = max(1.0, py2 - py1)
    p_w = max(1.0, px2 - px1)
    rel_y = (cy - py1) / p_h
    rel_x = (cx - px1) / p_w
    # Cuello / placket: nunca es el logo bordado.
    if rel_y < collar_y_max() - tol * 0.5:
        return False
    y0r, y1r, x0r, x1r = logo_roi_fractions()
    if rel_y < y0r - tol or rel_y > y1r + tol:
        return False
    return not (rel_x < x0r - tol or rel_x > x1r + tol)


def rel_center_on_person(
    box: tuple, person_box: tuple
) -> tuple[float, float] | None:
    """Centro de ``box`` en fracciones 0–1 respecto a la caja persona."""
    if not box or not person_box or len(box) < 4 or len(person_box) < 4:
        return None
    px1, py1, px2, py2 = (float(v) for v in person_box)
    p_h = max(1.0, py2 - py1)
    p_w = max(1.0, px2 - px1)
    cx = 0.5 * (float(box[0]) + float(box[2]))
    cy = 0.5 * (float(box[1]) + float(box[3]))
    return (cx - px1) / p_w, (cy - py1) / p_h


def snap_box_to_logo_zone(
    box: tuple, person_box: tuple
) -> tuple[float, float, float, float]:
    """Mueve y agranda la caja hasta el ROI del pecho, con tamaño proporcional.

    El template matching devuelve el rectángulo del template redimensionado
    (a veces 20×18 px), que sobre el vídeo es invisible. Aquí se garantiza un
    tamaño mínimo proporcional al pecho y se clampea dentro de la persona.
    """
    px1, py1, px2, py2 = (float(v) for v in person_box)
    zx1, zy1, zx2, zy2 = chest_zone(person_box)
    zw = max(10.0, zx2 - zx1)
    zh = max(10.0, zy2 - zy1)

    target_w = max(SNAP_MIN_SIDE_PX, SNAP_MIN_W_FRACTION * zw)
    target_h = max(SNAP_MIN_SIDE_PX, SNAP_MIN_H_FRACTION * zh)

    bx1, by1, bx2, by2 = (float(v) for v in box)
    use_w = max(max(1.0, bx2 - bx1), target_w)
    use_h = max(max(1.0, by2 - by1), target_h)

    # El centro debe caer dentro de la zona del pecho.
    cx = 0.5 * (bx1 + bx2)
    cy = 0.5 * (by1 + by2)
    cx = max(zx1 + SNAP_CENTER_MARGIN * zw, min(zx2 - SNAP_CENTER_MARGIN * zw, cx))
    cy = max(zy1 + SNAP_CENTER_MARGIN * zh, min(zy2 - SNAP_CENTER_MARGIN * zh, cy))

    return (
        max(px1, cx - use_w * 0.5),
        max(py1, cy - use_h * 0.5),
        min(px2, cx + use_w * 0.5),
        min(py2, cy + use_h * 0.5),
    )


def best_person_for_box(box: tuple, persons: list[dict]) -> tuple | None:
    """Caja de persona que contiene el centro de ``box``; si ninguna, la más cercana."""
    if not box or not persons:
        return None
    cx = 0.5 * (float(box[0]) + float(box[2]))
    cy = 0.5 * (float(box[1]) + float(box[3]))

    boxes = []
    for person in persons:
        pb = person.get("box")
        if pb and len(pb) >= 4:
            boxes.append(tuple(float(v) for v in pb[:4]))
    if not boxes:
        return None

    # 1) Contención: de las que contienen el centro, la de mayor área.
    containing = [
        b for b in boxes if b[0] <= cx <= b[2] and b[1] <= cy <= b[3]
    ]
    if containing:
        return max(containing, key=lambda b: (b[2] - b[0]) * (b[3] - b[1]))

    # 2) Sin contención: la persona más cercana por centro.
    def distance(b: tuple) -> float:
        return (0.5 * (b[0] + b[2]) - cx) ** 2 + (0.5 * (b[1] + b[3]) - cy) ** 2

    return min(boxes, key=distance)


def clamp_box_to_frame(box, frame_shape) -> tuple[int, int, int, int] | None:
    """Recorta una caja a los límites del frame y la devuelve como enteros.

    Devuelve ``None`` si la caja es inválida o degenerada. Centraliza el
    clampeo que antes estaba copiado en cada punto que recortaba el frame.
    """
    if box is None or len(box) < 4 or frame_shape is None:
        return None
    try:
        fh, fw = frame_shape[:2]
        x1 = int(max(0, min(fw - 1, float(box[0]))))
        y1 = int(max(0, min(fh - 1, float(box[1]))))
        x2 = int(max(x1 + 1, min(fw, float(box[2]))))
        y2 = int(max(y1 + 1, min(fh, float(box[3]))))
    except (TypeError, ValueError, IndexError):
        return None
    if x2 <= x1 or y2 <= y1:
        return None
    return x1, y1, x2, y2
