import threading

from app.hologram.models import FanUnitConfig
from app.hologram.unit_manager import HologramUnitManager


class FakeFan:
    events = []
    event = threading.Event()
    failures = 0

    def __init__(self, ip, port):
        self.ip, self.port, self.is_connected = ip, port, False

    def connect(self):
        if FakeFan.failures:
            FakeFan.failures -= 1
            raise ConnectionError("offline")
        self.is_connected = True
        FakeFan.events.append(("connect", self.ip))

    def start(self): pass
    def shutdown(self): FakeFan.events.append(("shutdown", self.ip))
    def disconnect(self): self.is_connected = False
    def play_file(self, index):
        FakeFan.events.append(("play", self.ip, index))
        FakeFan.event.set()


def manager(ip="10.0.0.1"):
    FakeFan.events, FakeFan.event, FakeFan.failures = [], threading.Event(), 0
    return HologramUnitManager("top", FanUnitConfig(ip=ip), FakeFan, min_send_gap=0, reconnect_delay=0)


def test_deduplication_reconnection_and_idempotent_shutdown():
    unit = manager()
    unit.start()
    unit.start()
    unit.request(2, "x")
    assert FakeFan.event.wait(1)
    unit.request(2, "x")
    assert [e for e in FakeFan.events if e[0] == "play"] == [("play", "10.0.0.1", 2)]
    unit.close()
    unit.close()
    assert not unit.status().worker_alive


def test_disconnected_unit_reconnects_without_breaking_worker():
    unit = manager()
    FakeFan.failures = 1
    unit.start()
    unit.request(4, "retry")
    assert FakeFan.event.wait(1)
    assert unit.is_connected
    unit.close()


def test_concurrent_commands_are_serialized():
    unit = manager()
    unit.start()
    threads = [threading.Thread(target=unit.request, args=(i, str(i))) for i in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert FakeFan.event.wait(1)
    unit.close()
    assert len([e for e in FakeFan.events if e[0] == "play"]) >= 1
