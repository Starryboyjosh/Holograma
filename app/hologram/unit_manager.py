"""Worker aislado por ventilador, construido sobre el transporte existente."""

from __future__ import annotations

import queue
import threading
import time
from collections.abc import Callable

from hologram_controller import HologramFanController

from .models import FanRole, FanUnitConfig, FanUnitStatus


class HologramUnitManager:
    def __init__(
        self, role: FanRole, config: FanUnitConfig,
        controller_factory: Callable[..., HologramFanController] = HologramFanController,
        min_send_gap: float = 0.25, reconnect_delay: float = 1.0,
    ) -> None:
        self.role, self.config, self._factory = role, config, controller_factory
        self._min_send_gap, self._reconnect_delay = min_send_gap, reconnect_delay
        self._queue: queue.Queue[tuple[int, str] | None] = queue.Queue()
        self._stop, self._lock = threading.Event(), threading.RLock()
        self._thread: threading.Thread | None = None
        self._fan: HologramFanController | None = None
        self._desired: tuple[int, str] | None = None
        self._current: tuple[int, str] | None = None
        self._last_error: str | None = None
        self._next_reconnect = 0.0
        self._last_send = 0.0

    def start(self) -> None:
        with self._lock:
            if not self.config.enabled or not self.config.ip.strip() or (self._thread and self._thread.is_alive()):
                return
            self._stop.clear()
            self._thread = threading.Thread(target=self._run, name=f"hologram-{self.role}", daemon=True)
            self._thread.start()

    def request(self, index: int, media_id: str, context_id: str | None = None) -> None:
        if not 0 <= index <= 255:
            raise ValueError("index debe estar entre 0 y 255.")
        if not self.config.enabled:
            return
        request = (index, media_id)
        with self._lock:
            if request == self._current or request == self._desired:
                return
            self._desired = request
            self._queue.put(request)

    def execute_legacy(self, command: str, index: int | None = None) -> None:
        """Mantiene los comandos manuales heredados fuera de la ruta de IA."""
        with self._lock:
            if not self.config.enabled or not self._ensure_connected() or self._fan is None:
                raise ConnectionError("El holograma no está conectado.")
            commands = {
                "start": self._fan.start, "shutdown": self._fan.shutdown,
                "pause": self._fan.pause, "play": self._fan.play,
                "loop_current": self._fan.loop_current, "next_file": self._fan.next_file,
                "prev_file": self._fan.prev_file, "brightness_up": self._fan.brightness_up,
                "brightness_down": self._fan.brightness_down,
            }
            if command == "play_file":
                if index is None or not 0 <= index <= 255:
                    raise ValueError("play_file requiere index entre 0 y 255.")
                self._fan.play_file(index)
                self._current = (index, f"legacy:{index}")
            elif command in commands:
                commands[command]()
            else:
                raise ValueError(f"Comando desconocido: {command}")
            self._last_send = time.monotonic()

    def close(self) -> None:
        with self._lock:
            thread = self._thread
            if thread is None and self._fan is None:
                return
            self._stop.set()
            self._queue.put(None)
        if thread is not None:
            thread.join(timeout=6)
        with self._lock:
            self._thread = None
            self._disconnect(shutdown=True)
            self._current = None
            self._desired = None

    @property
    def is_connected(self) -> bool:
        with self._lock:
            return bool(self._fan and self._fan.is_connected)

    def status(self) -> FanUnitStatus:
        with self._lock:
            return FanUnitStatus(self.role, self.config.enabled, self.config.ip, self.config.port,
                self.is_connected, self._current[0] if self._current else None,
                self._current[1] if self._current else None, self._last_error,
                bool(self._thread and self._thread.is_alive()))

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                request = self._queue.get(timeout=0.1)
            except queue.Empty:
                request = self._desired
            while request is not None:
                try:
                    newer = self._queue.get_nowait()
                except queue.Empty:
                    break
                if newer is None:
                    request = None
                    break
                request = newer
            if request is None:
                continue
            self._apply(request)

    def _apply(self, request: tuple[int, str]) -> None:
        with self._lock:
            if request == self._current or not self._ensure_connected():
                return
            gap = self._min_send_gap - (time.monotonic() - self._last_send)
            if gap > 0 and self._stop.wait(gap):
                return
            try:
                assert self._fan is not None
                self._fan.play_file(request[0])
                self._last_send, self._current, self._last_error = time.monotonic(), request, None
            except (ConnectionError, OSError) as error:
                self._last_error = str(error)
                self._disconnect()
                self._next_reconnect = time.monotonic() + self._reconnect_delay

    def _ensure_connected(self) -> bool:
        if self._fan is not None and self._fan.is_connected:
            return True
        if time.monotonic() < self._next_reconnect:
            return False
        try:
            fan = self._factory(self.config.ip, self.config.port)
            fan.connect()
            fan.start()
            self._fan, self._current, self._last_error = fan, None, None
            return True
        except (ConnectionError, OSError) as error:
            self._last_error = str(error)
            self._fan = None
            self._next_reconnect = time.monotonic() + self._reconnect_delay
            return False

    def _disconnect(self, shutdown: bool = False) -> None:
        if self._fan is None:
            return
        try:
            if shutdown:
                self._fan.shutdown()
        except (ConnectionError, OSError):
            pass
        try:
            self._fan.disconnect()
        finally:
            self._fan = None
