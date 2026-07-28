import pytest

from app.hologram.rotation import VirtualClock
from app.hologram.simulator import HologramSimulator


def test_simulator_captures_three_roles_and_semantic_events():
    simulator = HologramSimulator(clock=VirtualClock())
    for role in ("top", "center", "bottom"):
        simulator.connect(role)
    simulator.play("bottom", 8, "systems-degree", "turn-123")
    event = simulator.get_events()[-1]
    assert event == {
        "timestamp": 0.0, "role": "bottom", "ip": "10.0.0.3", "command": "play_file",
        "semantic_id": "systems-degree", "resolved_index": 8, "context_id": "turn-123",
        "result": "sent", "error": None,
    }
    simulator.close()


def test_simulator_connection_send_failures_and_recovery():
    simulator = HologramSimulator(clock=VirtualClock())
    fan = simulator.fans["bottom"]
    fan.fail_connect = True
    with pytest.raises(ConnectionError):
        simulator.connect("bottom")
    fan.fail_connect = False
    simulator.connect("bottom")
    fan.fail_send = True
    with pytest.raises(OSError):
        simulator.play("bottom", 4, "promo")
    fan.fail_send = False
    simulator.play("bottom", 4, "promo")
    assert simulator.get_events()[-1]["result"] == "sent"
    simulator.disconnect("bottom")
    simulator.close()
