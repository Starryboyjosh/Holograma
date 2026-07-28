import json
import time

import pytest

import main
from app.hologram.models import FanUnitConfig, HologramConfig, IdentityMedia, PromotionMedia
from app.hologram.simulator import HologramSimulator
from app.hologram.unit_manager import HologramUnitManager
from main import HologramTestPayload
from main import test_hologram_unit as api_test_hologram_unit


class Fan:
    sent: list[int] = []
    fail_send = False

    def __init__(self, ip, port):
        self.is_connected = False

    def connect(self): self.is_connected = True
    def start(self): pass
    def pause(self): pass
    def play(self): pass
    def loop_current(self): pass
    def next_file(self): pass
    def prev_file(self): pass
    def brightness_up(self): pass
    def brightness_down(self): pass
    def shutdown(self): pass
    def disconnect(self): self.is_connected = False
    def play_file(self, index):
        if Fan.fail_send:
            raise OSError("send failed")
        Fan.sent.append(index)


def test_zero_and_255_are_valid_across_models_manager_and_simulator():
    assert IdentityMedia("holomind", "Holomind", 0, default=True).index == 0
    assert PromotionMedia("general", "General", 255).index == 255
    unit = HologramUnitManager("top", FanUnitConfig(ip="127.0.0.1"), Fan, min_send_gap=0)
    unit.start()
    unit.execute_legacy("play_file", 0)
    status = unit.status()
    assert status.requested_index == 0
    assert status.last_sent_index == 0
    assert status.last_send_result == "sent"
    assert status.last_send_at is not None and status.last_send_at > time.time() - 10
    assert status.retry_count == 0
    unit.close()
    simulator = HologramSimulator()
    simulator.connect("center")
    simulator.play("center", 0, "identity:holomind")
    assert simulator.get_events()[-1]["resolved_index"] == 0


def test_direct_legacy_failure_keeps_last_successful_index_and_requested_zero():
    Fan.sent, Fan.fail_send = [], False
    unit = HologramUnitManager("top", FanUnitConfig(ip="127.0.0.1"), Fan, min_send_gap=0)
    unit.execute_legacy("play_file", 255)
    Fan.fail_send = True
    with pytest.raises(OSError, match="send failed"):
        unit.execute_legacy("play_file", 0)
    status = unit.status()
    assert status.requested_index == 0
    assert status.last_sent_index == 255
    assert status.last_send_result == "error"
    assert status.retry_count == 1
    assert status.last_error == "send failed"
    unit.close()


@pytest.mark.parametrize("index", [-1, 256, 1.5, "abc"])
def test_invalid_physical_indexes_are_rejected(index):
    with pytest.raises((TypeError, ValueError)):
        IdentityMedia("holomind", "Holomind", index, default=True)  # type: ignore[arg-type]


def test_api_test_with_zero_sends_exact_zero_not_identify_index(monkeypatch):
    sent: list[int] = []

    class Unit:
        config = FanUnitConfig(ip="10.0.0.1", identify_index=255)
        def status(self): return type("Status", (), {"connected": True})()
        def execute_legacy(self, command, index):
            assert command == "play_file"
            sent.append(index)

    class Director:
        units = {"top": Unit()}

    monkeypatch.setattr(main, "_hologram_director", Director())
    response = api_test_hologram_unit("top", HologramTestPayload(index=0))
    assert response["status"] == "ok"
    assert response["index"] == 0
    assert sent == [0]
    for invalid in (-1, 256):
        result = api_test_hologram_unit("top", HologramTestPayload(index=invalid))
        assert json.loads(result.body)["code"] == "HOLOGRAM_INVALID_INDEX"


def test_default_config_keeps_zero_on_restart(tmp_path):
    from app.hologram.config_store import HologramConfigStore
    store = HologramConfigStore(tmp_path / "media.json")
    config = HologramConfig.default()
    store.save(config)
    assert store.load().mascot_states["idle"] == 0
    assert store.load().identities[0].index == 0
