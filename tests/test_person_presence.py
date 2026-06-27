"""Máquina de estados de presencia: parpadeos vs. ausencia real.

Estos tests blindan el arreglo del síntoma "la cámara vuelve a saludar a la misma
persona". El bucle `run_continuous` mantiene `was_present` con un período de
gracia; un parpadeo del detector (un cuadro sin detección entre dos con persona)
NO debe contar como que la persona se fue y volvió.

No se necesita cámara ni la pila de visión (cv2/ultralytics se importan de forma
perezosa dentro de los métodos): se inyecta un `Camera` falso y se sustituye
`analyze_frame` por una secuencia guionizada de conteos de personas.
"""

import vision.camera
import vision.person_detector as pd


def _analysis(count):
    """Análisis sintético con *count* personas (forma que devuelve analyze_frame)."""
    persons = [{"confidence": 0.9, "box": (0, 0, 1, 1)} for _ in range(count)]
    return {"person_count": count, "persons": persons, "custom_objects": []}


def _drive(monkeypatch, counts, absence_seconds=5.0):
    """Corre `run_continuous` sobre una secuencia de conteos y devuelve los eventos.

    *counts* es un conteo de personas por cuadro. Cuando se agota, el bucle se
    detiene solo. Todo se ejecuta en memoria y sin esperas reales.
    """
    monkeypatch.setenv("PRESENCE_ABSENCE_SECONDS", str(absence_seconds))
    # El bucle duerme 0.03 s por cuadro; lo anulamos para que el test sea instantáneo.
    monkeypatch.setattr(pd.time, "sleep", lambda *a, **k: None)

    class FakeCamera:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read_frame(self):
            return object()  # frame no-None; el contenido no importa (mockeamos analyze)

    monkeypatch.setattr(vision.camera, "Camera", FakeCamera)

    detector = pd.YoloPersonDetector()
    script = list(counts)
    events = []

    def fake_analyze(frame):
        if not script:
            detector.stop()  # agotada la secuencia: corta el bucle
            return _analysis(0)
        return _analysis(script.pop(0))

    monkeypatch.setattr(detector, "analyze_frame", fake_analyze)
    monkeypatch.setattr(detector, "_store_annotated_frame", lambda *a, **k: None)

    detector.run_continuous(
        lambda event, count, analysis: events.append(event),
        camera_index=0,
        interval_seconds=0.0,  # analizar cada cuadro
    )
    return events


def test_blink_does_not_re_greet(monkeypatch):
    """Un cuadro perdido entre dos presencias NO debe re-disparar person_entered.

    Antes, `was_present = is_present` al final del bucle anulaba el período de
    gracia: el cuadro a 0 ponía was_present=False y el siguiente cuadro con
    persona saludaba otra vez. Con la gracia intacta solo hay UN person_entered.
    """
    events = _drive(monkeypatch, [1, 1, 0, 1, 1], absence_seconds=5.0)
    assert events == ["person_entered"]


def test_real_departure_and_return_greets_again(monkeypatch):
    """Una ausencia sostenida (supera la gracia) sí cuenta como ida y vuelta."""
    events = _drive(monkeypatch, [1, 0, 0, 1], absence_seconds=0.0)
    assert events == ["person_entered", "person_left", "person_entered"]


def test_group_detected_once_for_sustained_group(monkeypatch):
    """Un grupo (>3) dispara group_detected una sola vez mientras se mantiene."""
    events = _drive(monkeypatch, [5, 5, 5], absence_seconds=5.0)
    assert events == ["group_detected"]
