import time

import hologram_controller


class FakeFan:
    events: list[tuple] = []

    def __init__(self, ip, port, verbose=False):
        self.ip = ip
        self.port = port
        self.verbose = verbose
        self.is_connected = False

    def connect(self):
        self.is_connected = True
        self.events.append(("connect", self.ip, self.port))

    def disconnect(self):
        self.is_connected = False
        self.events.append(("disconnect",))

    def start(self):
        self.events.append(("start",))

    def shutdown(self):
        self.events.append(("shutdown",))

    def play_file(self, index):
        self.events.append(("play_file", index))

    def pause(self):
        self.events.append(("pause",))

    def play(self):
        self.events.append(("play",))

    def loop_current(self):
        self.events.append(("loop_current",))

    def next_file(self):
        self.events.append(("next_file",))

    def prev_file(self):
        self.events.append(("prev_file",))

    def brightness_up(self):
        self.events.append(("brightness_up",))

    def brightness_down(self):
        self.events.append(("brightness_down",))


def wait_for_event(event, timeout=1.0):
    deadline = time.monotonic() + timeout
    while event not in FakeFan.events and time.monotonic() < deadline:
        time.sleep(0.01)
    assert event in FakeFan.events


def test_configured_manager_applies_ai_state_clips(monkeypatch):
    FakeFan.events = []
    monkeypatch.setattr(hologram_controller, "HologramFanController", FakeFan)
    manager = hologram_controller.HologramStateManager(min_send_gap=0)

    try:
        manager.configure("10.10.10.1", 50200)
        wait_for_event(("play_file", 0))
        assert manager.is_connected

        manager.set_state("thinking")
        wait_for_event(("play_file", 3))
    finally:
        manager.disable()

    assert manager.enabled is False
    assert manager.is_connected is False


def test_manager_rejects_invalid_connection_settings():
    manager = hologram_controller.HologramStateManager()

    for ip, port in [("", 50200), ("10.10.10.1", 0), ("10.10.10.1", 65536)]:
        try:
            manager.configure(ip, port)
        except ValueError:
            pass
        else:
            raise AssertionError("La configuración inválida debió rechazarse")


def test_resolve_state_clips_defaults_when_env_empty():
    assert hologram_controller.resolve_state_clips({}) == hologram_controller.DEFAULT_STATE_CLIPS


def test_resolve_state_clips_honors_playlist_order_overrides():
    # Operador cargó los clips en otro orden en la app HoloMissYou.
    clips = hologram_controller.resolve_state_clips(
        {
            "HOLOGRAM_CLIP_IDLE": "5",
            "HOLOGRAM_CLIP_LISTENING": "6",
            "HOLOGRAM_CLIP_SPEAKING": "7",
            "HOLOGRAM_CLIP_THINKING": "8",
        }
    )
    assert clips == {"idle": 5, "listening": 6, "speaking": 7, "thinking": 8}


def test_resolve_state_clips_ignores_invalid_values():
    # No entero y fuera de rango → conserva el default, nunca rompe el arranque.
    clips = hologram_controller.resolve_state_clips(
        {"HOLOGRAM_CLIP_IDLE": "x", "HOLOGRAM_CLIP_SPEAKING": "999"}
    )
    assert clips["idle"] == 0
    assert clips["speaking"] == 2


def test_configured_manager_uses_custom_clip_map(monkeypatch):
    FakeFan.events = []
    monkeypatch.setattr(hologram_controller, "HologramFanController", FakeFan)
    manager = hologram_controller.HologramStateManager(
        state_clips={"idle": 9, "listening": 1, "speaking": 2, "thinking": 3},
        min_send_gap=0,
    )

    try:
        manager.configure("10.10.10.1", 50200)
        wait_for_event(("play_file", 9))  # idle remapeado al clip 9
    finally:
        manager.disable()


def test_array_tester_sends_a_different_clip_to_each_hologram(monkeypatch):
    FakeFan.events = []
    monkeypatch.setattr(hologram_controller, "HologramFanController", FakeFan)
    tester = hologram_controller.HologramArrayTester(
        [("10.10.10.1", 0), ("10.10.10.2", 1), ("10.10.10.3", 2)],
        command_gap=0,
    )

    results = tester.run()

    assert results == [
        {"ip": "10.10.10.1", "index": 0, "status": "ok"},
        {"ip": "10.10.10.2", "index": 1, "status": "ok"},
        {"ip": "10.10.10.3", "index": 2, "status": "ok"},
    ]
    assert [event for event in FakeFan.events if event[0] == "play_file"] == [
        ("play_file", 0),
        ("play_file", 1),
        ("play_file", 2),
    ]
