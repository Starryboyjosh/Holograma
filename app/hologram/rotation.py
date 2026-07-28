"""Rotación determinista del catálogo inferior.

El worker usa un reloj inyectable: las pruebas pueden avanzar un ``VirtualClock``
sin dormir y la aplicación real utiliza ``RealClock`` basado en ``Event.wait``.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Protocol

from .models import PromotionMedia, RotationConfig


class Clock(Protocol):
    def now(self) -> float: ...
    def wait(self, seconds: float, stop: threading.Event) -> bool: ...


class RealClock:
    def now(self) -> float:
        return time.monotonic()

    def wait(self, seconds: float, stop: threading.Event) -> bool:
        return stop.wait(max(0.0, seconds))


class VirtualClock:
    """Reloj de pruebas; ``advance`` despierta al scheduler inmediatamente."""

    def __init__(self, initial: float = 0.0) -> None:
        self._now = initial
        self._condition = threading.Condition()

    def now(self) -> float:
        with self._condition:
            return self._now

    def advance(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("El reloj no puede retroceder.")
        with self._condition:
            self._now += seconds
            self._condition.notify_all()

    def wait(self, seconds: float, stop: threading.Event) -> bool:
        deadline = self.now() + max(0.0, seconds)
        with self._condition:
            while self._now < deadline and not stop.is_set():
                self._condition.wait()
            return stop.is_set()


class PromotionSink(Protocol):
    def request(self, index: int, media_id: str, context_id: str | None = None) -> None: ...


class PromotionRotationManager:
    def __init__(
        self,
        promotions: tuple[PromotionMedia, ...] | list[PromotionMedia],
        sink: PromotionSink,
        config: RotationConfig | None = None,
        clock: Clock | None = None,
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        self._promotions = tuple(promotions)
        self._sink = sink
        self._config = config or RotationConfig()
        self._clock = clock or RealClock()
        self._on_error = on_error
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._active = False
        self._paused = False
        self._context_id: str | None = None
        self._context_mode: str | None = None
        self._context_item: str | None = None
        self._context_items: tuple[PromotionMedia, ...] = ()
        self._context_position = 0
        self._current: PromotionMedia | None = None
        self._next_position = 0
        self._deadline: float | None = None
        self._last_error: str | None = None

    @property
    def eligible(self) -> tuple[PromotionMedia, ...]:
        return tuple(
            sorted(
                (item for item in self._promotions if item.enabled and item.rotation_enabled),
                key=lambda item: (-item.priority, item.id),
            )
        )

    def replace_promotions(self, promotions: tuple[PromotionMedia, ...] | list[PromotionMedia]) -> None:
        with self._lock:
            self._promotions = tuple(promotions)
            self._next_position = 0
            if self._active and self._context_id is None:
                self._dispatch_next_locked()

    def start(self) -> None:
        with self._lock:
            if self._active:
                return
            self._active, self._paused = True, False
            self._start_worker_locked()
            self._dispatch_next_locked()

    def pause(self) -> None:
        with self._lock:
            if self._active:
                self._paused = True
                self._deadline = None

    def resume(self) -> None:
        with self._lock:
            if not self._active:
                self.start()
                return
            self._paused = False
            if self._current is None and self._context_id is None:
                self._dispatch_next_locked()
            elif self._current is not None:
                self._deadline = self._clock.now() + self._current.duration_seconds

    def stop(self) -> None:
        with self._lock:
            self._active = False
            self._paused = False
            self._context_id = self._context_mode = self._context_item = None
            self._context_items = ()
            self._context_position = 0
            self._current = None
            self._deadline = None
            self._stop.set()
            thread = self._thread
        if thread is not None:
            thread.join(timeout=3)
        with self._lock:
            self._thread = None

    def focus_item(self, promotion_id: str, context_id: str | None = None) -> None:
        item = next((item for item in self._promotions if item.id == promotion_id and item.enabled), None)
        if item is None:
            raise ValueError(f"Promoción inexistente o deshabilitada: {promotion_id}.")
        with self._lock:
            self._begin_context_locked("item", item, context_id)

    def focus_category(self, category: str, context_id: str | None = None) -> None:
        category = category.strip()
        if not category:
            raise ValueError("La categoría es obligatoria.")
        item = next(
            (item for item in self.eligible if category in item.categories), None
        )
        if item is None:
            raise ValueError(f"Categoría sin promociones elegibles: {category}.")
        with self._lock:
            self._begin_context_locked("category", item, context_id)

    def finish_context(self, context_id: str | None = None) -> None:
        with self._lock:
            if self._context_id is None:
                return
            if context_id is not None and context_id != self._context_id:
                return
            self._context_id = self._context_mode = self._context_item = None
            self._context_items = ()
            self._context_position = 0
            self._current = None
            self._deadline = None
            if self._active and not self._paused:
                self._dispatch_next_locked()

    def get_status(self) -> dict:
        with self._lock:
            items = self.eligible
            next_item = None
            if items:
                next_item = items[self._next_position % len(items)]
            return {
                "active": self._active,
                "paused": self._paused,
                "current": self._media_status(self._current),
                "next": self._media_status(next_item),
                "context_id": self._context_id,
                "context_mode": self._context_mode,
                "thread_alive": bool(self._thread and self._thread.is_alive()),
                "last_error": self._last_error,
            }

    def close(self) -> None:
        self.stop()

    def tick(self) -> None:
        """Procesa inmediatamente un vencimiento del reloj inyectado.

        Es útil para pruebas deterministas y también permite a un scheduler
        externo conducir la rotación sin crear otro loop.
        """
        with self._lock:
            if self._active and not self._paused and self._deadline is not None and self._clock.now() >= self._deadline:
                self._current = None
                self._deadline = None
                if self._context_id is not None and self._context_mode == "category":
                    self._dispatch_context_next_locked()
                elif self._context_id is not None:
                    self._context_id = self._context_mode = self._context_item = None
                    self._context_items = ()
                    self._dispatch_next_locked()
                else:
                    self._dispatch_next_locked()

    def _run(self) -> None:
        while not self._stop.is_set():
            with self._lock:
                deadline = self._deadline
                active = self._active and not self._paused
            if not active or deadline is None:
                self._clock.wait(0.1, self._stop)
                continue
            if self._clock.wait(max(0.0, deadline - self._clock.now()), self._stop):
                break
            with self._lock:
                if self._active and not self._paused and self._deadline == deadline:
                    self._current = None
                    self._deadline = None
                    if self._context_id is not None and self._context_mode == "category":
                        self._dispatch_context_next_locked()
                    elif self._context_id is not None:
                        self._context_id = self._context_mode = self._context_item = None
                        self._context_items = ()
                        self._dispatch_next_locked()
                    else:
                        self._dispatch_next_locked()

    def _dispatch_next_locked(self) -> None:
        items = self.eligible
        if not items or not self._active or self._paused:
            self._current = None
            self._deadline = None
            return
        item = items[self._next_position % len(items)]
        self._next_position = (self._next_position + 1) % len(items)
        context_id = self._context_id
        try:
            self._request(item.index, f"promotion:{item.id}", context_id)
        except Exception as error:  # fail-soft: bottom no puede detener la app
            self._last_error = str(error)
            if self._on_error:
                self._on_error(self._last_error)
        self._current = item
        self._deadline = self._clock.now() + item.duration_seconds

    def _begin_context_locked(self, mode: str, item: PromotionMedia, context_id: str | None) -> None:
        if not self._active:
            self._active, self._paused = True, False
            self._start_worker_locked()
        self._context_id = context_id or f"context-{id(item)}"
        self._context_mode, self._context_item = mode, item.id
        if mode == "category":
            self._context_items = tuple(p for p in self.eligible if set(item.categories) & set(p.categories))
        else:
            self._context_items = (item,)
        self._context_position = 0
        self._current = item
        try:
            self._request(item.index, f"promotion:{item.id}", self._context_id)
        except Exception as error:
            self._last_error = str(error)
            if self._on_error:
                self._on_error(self._last_error)
        self._deadline = self._clock.now() + item.duration_seconds

    def _start_worker_locked(self) -> None:
        self._stop.clear()
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._run, name="hologram-rotation", daemon=True)
            self._thread.start()

    def _dispatch_context_next_locked(self) -> None:
        if not self._context_items or not self._active or self._paused:
            return
        item = self._context_items[self._context_position % len(self._context_items)]
        self._context_position = (self._context_position + 1) % len(self._context_items)
        self._context_item = item.id
        try:
            self._request(item.index, f"promotion:{item.id}", self._context_id)
        except Exception as error:
            self._last_error = str(error)
            if self._on_error:
                self._on_error(self._last_error)
        self._current = item
        self._deadline = self._clock.now() + item.duration_seconds

    @staticmethod
    def _media_status(item: PromotionMedia | None) -> dict | None:
        if item is None:
            return None
        return {"id": item.id, "index": item.index, "title": item.title, "duration_seconds": item.duration_seconds}

    def _request(self, index: int, media_id: str, context_id: str | None) -> None:
        """Compatibilidad con sinks heredados de dos argumentos usados en tests."""
        try:
            self._sink.request(index, media_id, context_id)
        except TypeError:
            self._sink.request(index, media_id)
