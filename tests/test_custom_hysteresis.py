"""Histéresis M-of-N de custom objects dentro de run_continuous (§13 I4).

Un parpadeo de un ciclo (label presente, ausente, presente) NO debe re-disparar
``custom_object_detected``. El label solo se confirma tras ``confirm_cycles``
avistamientos consecutivos (default 2) y se olvida tras ``forget_seconds``.
"""

import vision.camera
import vision.person_detector as pd


def _analysis(count, labels):
    persons = [{"confidence": 0.9, "box": (0, 0, 1, 1)} for _ in range(count)]
    return {
        "person_count": count,
        "persons": persons,
        "custom_objects": [
            {"label": lbl, "confidence": 0.9, "box": (0, 0, 1, 1)} for lbl in labels
        ],
    }


def _drive(monkeypatch, script, frame_dt=1.0):
    """Corre run_continuous sobre una secuencia de (count, labels) y devuelve eventos.

    El reloj avanza *frame_dt* por iteración; el bucle corre a interval=0 para
    analizar cada cuadro. Detiene el bucle al agotar la secuencia.
    """
    monkeypatch.setattr(pd.time, "sleep", lambda *a, **k: None)
    clock = {"t": 0.0}

    def fake_time():
        clock["t"] += frame_dt
        return clock["t"]

    monkeypatch.setattr(pd.time, "time", fake_time)

    class FakeCamera:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read_frame(self):
            return object()

    monkeypatch.setattr(vision.camera, "Camera", FakeCamera)

    detector = pd.YoloPersonDetector()
    script = list(script)
    events = []

    def fake_analyze(frame):
        if not script:
            detector.stop()
            return _analysis(0, [])
        return _analysis(*script.pop(0))

    monkeypatch.setattr(detector, "analyze_frame", fake_analyze)
    monkeypatch.setattr(detector, "_store_annotated_frame", lambda *a, **k: None)

    detector.run_continuous(
        lambda event, count, analysis: events.append(event),
        camera_index=0,
        interval_seconds=0.0,
    )
    return [e for e in events if e != "analysis_update"]


def test_custom_flicker_does_not_retrigger(monkeypatch):
    """I4: un parpadeo de un ciclo no re-dispara custom_object_detected."""
    events = _drive(
        monkeypatch,
        [(1, ["Logo A"]), (1, ["Logo A"]), (1, []), (1, ["Logo A"]), (1, ["Logo A"])],
    )
    # confirm_cycles=2: la primera pareja confirma UNA vez. El parpadeo de un
    # ciclo no llega a olvidar el label (ausencia < forget_seconds=10 s), así
    # que al reaparecer sigue CONFIRMED y NO se re-emite el evento.
    assert [e for e in events if e == "custom_object_detected"] == [
        "custom_object_detected"
    ]


def test_custom_single_cycle_never_detected(monkeypatch):
    """I4: un único ciclo con el label nunca dispara el evento."""
    events = _drive(monkeypatch, [(1, ["Logo A"]), (1, [])])
    assert "custom_object_detected" not in events


def test_custom_sustained_label_detected_once(monkeypatch):
    """I4: un label sostenido dispara el evento una sola vez."""
    events = _drive(monkeypatch, [(1, ["Logo A"])] * 5)
    assert [e for e in events if e == "custom_object_detected"] == [
        "custom_object_detected"
    ]


def test_custom_return_after_forgotten_retriggers(monkeypatch):
    """I4: ausencia > forget_seconds olvida; al volver se re-confirma.

    Con frame_dt=2.0 y forget_seconds=10.0, seis ciclos vacíos tras confirmar
    superan el olvido; la vuelta acumula de nuevo los confirm_cycles.
    """
    monkeypatch.setenv("YOLO_CUSTOM_FORGET_SECONDS", "10.0")
    events = _drive(
        monkeypatch,
        [
            (1, ["Logo A"]),
            (1, ["Logo A"]),
            (1, []),
            (1, []),
            (1, []),
            (1, []),
            (1, []),
            (1, []),
            (1, ["Logo A"]),
            (1, ["Logo A"]),
        ],
        frame_dt=2.0,
    )
    detected = [e for e in events if e == "custom_object_detected"]
    assert detected == ["custom_object_detected", "custom_object_detected"]
