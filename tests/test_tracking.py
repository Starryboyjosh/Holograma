"""Histéresis M-of-N sobre etiquetas (§13 I4).

Tests del módulo puro ``vision/tracking.py``: sin cv2, numpy ni time real.
"""

from vision.tracking import (
    CONFIRMED,
    INACTIVE,
    NEW,
    TENTATIVE,
    LabelHysteresis,
)


def _run(tracker, sequence, now=0.0):
    """Corre la secuencia de sets de labels, devolviendo (eventos, now).

    Cada elemento de *sequence* es un set de labels visto en un ciclo; el
    instante avanza 1.0 s por ciclo. *now* permite continuar una secuencia
    previa sin reiniciar el reloj.
    """
    events = []
    for labels in sequence:
        now += 1.0
        events.extend(tracker.update(set(labels), now))
    return events, now


def test_single_cycle_flicker_does_not_confirm():
    """Un parpadeo de un ciclo nunca llega a CONFIRMED ni emite evento."""
    tracker = LabelHysteresis(confirm_cycles=2)
    events, _ = _run(tracker, [{"A"}, set(), {"A"}])
    assert events == []
    assert tracker.state("A") == NEW


def test_confirms_after_two_consecutive_cycles():
    """Dos ciclos consecutivos confirman el label exactamente una vez."""
    tracker = LabelHysteresis(confirm_cycles=2)
    events, _ = _run(tracker, [{"A"}, {"A"}])
    assert events == [{"event": "detected", "label": "A"}]
    assert tracker.state("A") == CONFIRMED


def test_confirmed_fires_only_once():
    """Una vez confirmado, seguir viéndolo no re-emite el evento."""
    tracker = LabelHysteresis(confirm_cycles=2)
    events, _ = _run(tracker, [{"A"}, {"A"}, {"A"}, {"A"}])
    assert [e for e in events if e["event"] == "detected"] == [
        {"event": "detected", "label": "A"}
    ]


def test_forgotten_after_absence():
    """CONFIRMED sin verse durante forget_seconds pasa a INACTIVE."""
    tracker = LabelHysteresis(confirm_cycles=2, forget_seconds=10.0)
    events, now = _run(tracker, [{"A"}, {"A"}] + [set()] * 10)
    assert "forgotten" not in {e["event"] for e in events}
    assert tracker.state("A") == CONFIRMED
    events2, now = _run(tracker, [set()], now=now)
    assert events2 == [{"event": "forgotten", "label": "A"}]
    assert tracker.state("A") == INACTIVE


def test_flicker_after_confirm_resets_progress():
    """Ausencia tras confirmar degrada a INACTIVE; reaparecer requiere reconfirmar."""
    tracker = LabelHysteresis(confirm_cycles=2, forget_seconds=5.0)
    _, now = _run(tracker, [{"A"}, {"A"}])
    events, now = _run(tracker, [set(), set(), set(), set(), set(), set()], now=now)
    assert events[-1] == {"event": "forgotten", "label": "A"}
    # Reaparece: no se confirma de golpe, debe volver a sumar ciclos.
    events2, now = _run(tracker, [{"A"}], now=now)
    assert events2 == []
    assert tracker.state("A") == TENTATIVE
    events3, _ = _run(tracker, [{"A"}], now=now)
    assert events3 == [{"event": "detected", "label": "A"}]


def test_new_reset_after_tentative_flicker():
    """Un label TENTATIVE que se pierde un ciclo pasa a NEW (sin evento)."""
    tracker = LabelHysteresis(confirm_cycles=2)
    _, now = _run(tracker, [{"A"}])
    _, _ = _run(tracker, [set()], now=now)
    assert tracker.state("A") == NEW


def test_inactive_pruned_after_retain():
    """Los INACTIVE se purgan tras retain_seconds."""
    tracker = LabelHysteresis(confirm_cycles=2, forget_seconds=2.0, retain_seconds=5.0)
    _, now = _run(tracker, [{"A"}, {"A"}])
    _, now = _run(tracker, [set(), set(), set()], now=now)
    assert tracker.state("A") == INACTIVE
    _, now = _run(tracker, [set(), set()], now=now)
    assert tracker.state("A") is None


def test_multi_label_independent():
    """Dos labels evolucionan de forma independiente."""
    tracker = LabelHysteresis(confirm_cycles=2)
    events, _ = _run(tracker, [{"A", "B"}, {"A"}])
    assert events == [{"event": "detected", "label": "A"}]
    assert tracker.state("A") == CONFIRMED
    assert tracker.state("B") == NEW


def test_confirm_cycles_one_immediate():
    """Con confirm_cycles=1 la confirmación es inmediata (sin histéresis)."""
    tracker = LabelHysteresis(confirm_cycles=1)
    events, _ = _run(tracker, [{"A"}])
    assert events == [{"event": "detected", "label": "A"}]
