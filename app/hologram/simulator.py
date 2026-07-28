"""Simulador determinista de tres ventiladores para pruebas y diagnósticos."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any

from .rotation import Clock, RealClock


@dataclass(frozen=True)
class SimulatorEvent:
    timestamp: float
    role: str
    ip: str
    command: str
    semantic_id: str | None
    resolved_index: int | None
    context_id: str | None
    result: str
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp, "role": self.role, "ip": self.ip,
            "command": self.command, "semantic_id": self.semantic_id,
            "resolved_index": self.resolved_index, "context_id": self.context_id,
            "result": self.result, "error": self.error,
        }


class SimulatedFan:
    def __init__(self, simulator: HologramSimulator, role: str, ip: str, latency: float = 0) -> None:
        self.simulator, self.role, self.ip, self.latency = simulator, role, ip, latency
        self.connected = False
        self.fail_connect = False
        self.fail_send = False

    def connect(self) -> None:
        if self.fail_connect:
            self.simulator.record(self.role, self.ip, "connect", None, None, None, "error", "connect failed")
            raise ConnectionError("simulated connection failure")
        self.connected = True
        self.simulator.record(self.role, self.ip, "connect", None, None, None, "sent")

    def disconnect(self) -> None:
        self.connected = False
        self.simulator.record(self.role, self.ip, "disconnect", None, None, None, "sent")

    def play_file(self, index: int, semantic_id: str | None = None, context_id: str | None = None) -> None:
        if not self.connected:
            raise ConnectionError("simulated fan is disconnected")
        if self.fail_send:
            self.simulator.record(self.role, self.ip, "play_file", semantic_id, index, context_id, "error", "send failed")
            raise OSError("simulated send failure")
        if self.latency:
            self.simulator.clock.wait(self.latency, self.simulator.stop_event)
        self.simulator.record(self.role, self.ip, "play_file", semantic_id, index, context_id, "sent")

    def start(self) -> None:
        self.simulator.record(self.role, self.ip, "start", None, None, None, "sent")

    def shutdown(self) -> None:
        self.simulator.record(self.role, self.ip, "shutdown", None, None, None, "sent")


class HologramSimulator:
    def __init__(self, ips: dict[str, str] | None = None, clock: Clock | None = None, latency: float = 0) -> None:
        ips = ips or {"top": "10.0.0.1", "center": "10.0.0.2", "bottom": "10.0.0.3"}
        self.clock = clock or RealClock()
        self.stop_event = threading.Event()
        self.events: list[SimulatorEvent] = []
        self._lock = threading.RLock()
        self.fans = {role: SimulatedFan(self, role, ip, latency) for role, ip in ips.items()}

    def connect(self, role: str) -> None:
        self.fans[role].connect()

    def disconnect(self, role: str) -> None:
        self.fans[role].disconnect()

    def play(self, role: str, index: int, semantic_id: str | None = None, context_id: str | None = None) -> None:
        self.fans[role].play_file(index, semantic_id, context_id)

    def record(self, role, ip, command, semantic_id, index, context_id, result, error=None) -> None:
        with self._lock:
            self.events.append(SimulatorEvent(self.clock.now(), role, ip, command, semantic_id, index, context_id, result, error))

    def get_events(self) -> list[dict]:
        with self._lock:
            return [event.as_dict() for event in self.events]

    def close(self) -> None:
        self.stop_event.set()
        for fan in self.fans.values():
            if fan.connected:
                fan.disconnect()
