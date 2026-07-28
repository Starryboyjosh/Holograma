import pytest

from app.hologram.models import PromotionMedia
from app.hologram.rotation import PromotionRotationManager, VirtualClock


class Sink:
    def __init__(self):
        self.commands = []

    def request(self, index, media_id, context_id=None):
        self.commands.append((index, media_id, context_id))


def promotions():
    return (
        PromotionMedia("a", "A", 1, duration_seconds=2, priority=1),
        PromotionMedia("b", "B", 2, duration_seconds=2),
        PromotionMedia("disabled", "D", 3, enabled=False),
        PromotionMedia("c", "C", 3, duration_seconds=2),
    )


def test_rotation_loops_deterministically_and_skips_disabled():
    clock, sink = VirtualClock(), Sink()
    rotation = PromotionRotationManager(promotions(), sink, clock=clock)
    rotation.start()
    assert sink.commands[-1][1] == "promotion:a"
    clock.advance(2)
    rotation.tick()
    assert sink.commands[-1][1] == "promotion:b"
    clock.advance(2)
    rotation.tick()
    assert sink.commands[-1][1] == "promotion:c"
    clock.advance(2)
    rotation.tick()
    assert sink.commands[-1][1] == "promotion:a"
    rotation.stop()
    assert not rotation.get_status()["thread_alive"]


def test_pause_resume_and_context_continue_from_next():
    clock, sink = VirtualClock(), Sink()
    rotation = PromotionRotationManager(promotions(), sink, clock=clock)
    rotation.start()
    rotation.pause()
    clock.advance(20)
    assert sink.commands == [(1, "promotion:a", None)]
    rotation.resume()
    rotation.focus_item("c", "turn-1")
    assert sink.commands[-1] == (3, "promotion:c", "turn-1")
    rotation.finish_context("turn-1")
    assert sink.commands[-1][1] == "promotion:b"
    rotation.finish_context("turn-1")
    rotation.stop()


def test_category_and_invalid_or_empty_catalog():
    clock, sink = VirtualClock(), Sink()
    rotation = PromotionRotationManager((PromotionMedia("a", "A", 1, categories=("careers",)),), sink, clock=clock)
    rotation.focus_category("careers", "ctx")
    assert sink.commands[-1] == (1, "promotion:a", "ctx")
    with pytest.raises(ValueError):
        rotation.focus_category("missing")
    with pytest.raises(ValueError):
        rotation.focus_item("missing")
    rotation.stop()
    empty = PromotionRotationManager((), Sink(), clock=VirtualClock())
    empty.start()
    assert empty.get_status()["current"] is None
    empty.close()
