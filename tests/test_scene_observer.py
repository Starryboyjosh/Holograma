from app.hologram.scene_observer import SceneObserver


def test_observer_corrects_once_after_hold_without_mutating_text():
    clock = [0.0]
    observer = SceneObserver(identity_hold_seconds=2, clock=lambda: clock[0])
    observer.begin("turn")
    text = "La Universidad Evangélica de las Américas ofrece carreras."
    assert observer.observe(text[:20], "turn", "holomind", {"holomind", "unev", "itee"}) is None
    clock[0] = 3
    assert observer.observe(text[20:], "turn", "holomind", {"holomind", "unev", "itee"}) == "unev"
    assert observer.observe("ITEE participa", "turn", "unev", {"holomind", "unev", "itee"}) is None
    assert text == "La Universidad Evangélica de las Américas ofrece carreras."


def test_observer_handles_itee_negation_and_stale_turn():
    observer = SceneObserver(identity_hold_seconds=0, clock=lambda: 10)
    observer.begin("new")
    assert observer.observe("La afiliación con ITEE está explicada aquí.", "old", "holomind", {"itee"}) is None
    assert observer.observe("No existe relación con ITEE.", "new", "holomind", {"itee"}) is None
    assert observer.observe("La afiliación con ITEE está explicada aquí.", "new", "holomind", {"itee"}) == "itee"
