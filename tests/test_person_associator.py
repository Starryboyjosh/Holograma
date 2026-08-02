"""Asociación locks → Hungarian → dummy adaptativo → veto de empate (§13 I6).

Tests del módulo puro ``vision/tracking.py`` (PersonAssociator): numpy +
scipy perezoso. Sin cv2 ni time real.
"""

import numpy as np

from vision.tracking import CONFIRMED, INACTIVE, NEW, TENTATIVE, PersonAssociator


def _det(box, confidence=0.9, signature=None):
    d = {"box": box, "confidence": confidence}
    if signature is not None:
        d["signature"] = signature
    return d


def _drive(assoc, frames):
    """Corre los frames (listas de detecciones) y devuelve los eventos totales."""
    events = []
    now = 0.0
    for dets in frames:
        now += 1.0
        events.extend(assoc.update(list(dets), now))
    return events


def test_new_person_creates_track_and_confirms():
    a = PersonAssociator(confirm_cycles=2)
    events = _drive(a, [[_det((0, 0, 50, 100))], [_det((0, 0, 50, 100))]])
    assert events == [{"event": "detected", "id": 1}]
    assert a.state(1) == CONFIRMED
    assert a.confirmed() == {1}


def test_new_person_needs_confirm_cycles():
    a = PersonAssociator(confirm_cycles=2)
    events = _drive(a, [[_det((0, 0, 50, 100))]])
    assert events == []
    assert a.state(1) == TENTATIVE


def test_stable_person_does_not_reconfirm():
    a = PersonAssociator(confirm_cycles=2)
    events = _drive(a, [[_det((0, 0, 50, 100))] for _ in range(5)])
    detected = [e for e in events if e["event"] == "detected"]
    assert detected == [{"event": "detected", "id": 1}]


def test_forgotten_after_absence():
    a = PersonAssociator(confirm_cycles=2, forget_seconds=5.0)
    _drive(a, [[_det((0, 0, 50, 100))], [_det((0, 0, 50, 100))]])
    events = _drive(a, [[] for _ in range(6)])
    assert [e for e in events if e["event"] == "forgotten"] == [
        {"event": "forgotten", "id": 1}
    ]
    assert a.state(1) == INACTIVE


def test_two_persons_get_two_tracks():
    a = PersonAssociator(confirm_cycles=2)
    frame = [_det((0, 0, 50, 100)), _det((200, 0, 250, 100))]
    events = _drive(a, [frame, frame])
    assert len(a.confirmed()) == 2


def test_tie_veto_with_identical_boxes():
    """Cajas idénticas sin descriptor: veto de empate, prefiere no adivinar.

    Dos tracks existentes y detecciones con cajas idénticas → las detecciones
    se arrastran sin asignar (no se compromete nada).
    """
    a = PersonAssociator(confirm_cycles=2)
    # Dos detecciones idénticas en el primer ciclo → dos tracks con la MISMA
    # caja: ningún score distingue cuál es cuál.
    _drive(a, [[_det((0, 0, 50, 100)), _det((0, 0, 50, 100))]])
    assert len(a.tracks) == 2
    # Dos detecciones con caja idéntica a ambos tracks → empate perfecto.
    frame = [_det((0, 0, 50, 100)), _det((0, 0, 50, 100))]
    events = _drive(a, [frame])
    # El veto evita que se comprometan; no crea tracks nuevos.
    assert events == []
    assert len(a.tracks) == 2
    assert len(a._pending) == 2


def test_lock_commits_strong_unique_pair():
    """Locks: s1>=0.90 con margen amplio se compromete de una vez."""
    a = PersonAssociator(s1_lock=0.90, lock_margin=0.05, confirm_cycles=2)
    sig_a = np.zeros(48)
    sig_a[0] = 1.0
    sig_b = np.zeros(48)
    sig_b[1] = 1.0
    frame = [_det((0, 0, 50, 100), signature=sig_a), _det((200, 0, 250, 100), signature=sig_b)]
    events = _drive(a, [frame, frame])
    assert len(a.confirmed()) == 2


def test_adaptive_dummy_range():
    a = PersonAssociator()
    assert a.adaptive_dummy(1.0) == 0.05
    assert a.adaptive_dummy(0.0) == 0.25
    assert 0.0 <= a.adaptive_dummy(0.5) <= 0.72
    assert a.adaptive_dummy(0.5) == 0.05 + 0.20 * 0.5


def test_low_confidence_prefers_new_identity():
    """Con baja confianza, el dummy sube y una detección débil crea identidad
    nueva en vez de asignarse a un track con el que casa mal."""
    a = PersonAssociator(confirm_cycles=2)
    _drive(a, [[_det((0, 0, 50, 100))], [_det((0, 0, 50, 100))]])
    n_before = len(a.tracks)
    # Detección lejana y con poca confianza: crea track nuevo (dummy alto).
    events = _drive(a, [[_det((400, 0, 450, 100), confidence=0.1)]])
    assert len(a.tracks) == n_before + 1


def test_no_descriptor_uses_geometry_only():
    """Sin descriptor, la asociación es solo geometría (IoU)."""
    a = PersonAssociator(confirm_cycles=2)
    frame = [_det((0, 0, 50, 100)), _det((200, 0, 250, 100))]
    _drive(a, [frame])
    # La segunda detección del siguiente ciclo con caja idéntica al track 2
    # sigue el mismo track (no crea uno nuevo).
    events = _drive(a, [frame])
    assert len(a.tracks) == 2


def test_pending_vetoed_carried_to_next_cycle():
    """Las detecciones veteadas se reintroducen en el siguiente ciclo."""
    a = PersonAssociator(confirm_cycles=2)
    _drive(a, [[_det((0, 0, 50, 100)), _det((0, 0, 50, 100))]])
    # Caja idéntica a ambos tracks → veto; el pending se reintroduce después.
    frame = [_det((0, 0, 50, 100)), _det((0, 0, 50, 100))]
    _drive(a, [frame])
    assert a._pending, "debe arrastrar las veteadas al siguiente ciclo"
    # En el siguiente ciclo, las reintroduce como candidatas (sin tracks nuevos).
    n_before = len(a.tracks)
    _drive(a, [frame])
    assert len(a.tracks) == n_before


def test_greedy_fallback_without_scipy(monkeypatch):
    """Si scipy falla, el Hungarian cae al greedy sin romperse."""
    import vision.tracking as vt

    def boom(*args, **kwargs):
        raise ImportError("scipy no disponible")

    monkeypatch.setattr(vt.PersonAssociator, "_hungarian", boom)
    a = PersonAssociator(confirm_cycles=2)
    frame = [_det((0, 0, 50, 100)), _det((200, 0, 250, 100))]
    _drive(a, [frame, frame])
    assert len(a.confirmed()) == 2
