"""Coordinación fail-soft de una escena semántica por turno conversacional."""

from __future__ import annotations

import logging
import threading
import uuid

from .director import HologramDirector
from .media_router import MediaRouter
from .scene_observer import SceneObserver

logger = logging.getLogger(__name__)


class HologramConversationOrchestrator:
    def __init__(self, router: MediaRouter, director: HologramDirector, observer: SceneObserver | None = None) -> None:
        self._router, self._director = router, director
        self._observer = observer or SceneObserver(director.config.routing.identity_hold_seconds)
        self._lock = threading.RLock()
        self._active_context_id: str | None = None
        self._current_identity = "holomind"
        self._closed: set[str] = set()

    @property
    def active_context_id(self) -> str | None:
        with self._lock:
            return self._active_context_id

    def reconfigure(self) -> None:
        self._router.replace_config(self._director.config)

    def mark_listening(self) -> None:
        self._safe(lambda: self._director.set_mascot_state("listening"), "listening")

    def mark_thinking(self) -> None:
        self._safe(lambda: self._director.set_mascot_state("thinking"), "thinking")

    def mark_speaking(self) -> None:
        self._safe(lambda: self._director.set_mascot_state("speaking"), "speaking")

    def start_turn(self, user_message: str, context: str | None = None, mode: str | None = None, skill: str | None = None) -> str:
        context_id = str(uuid.uuid4())
        with self._lock:
            if getattr(self._router, "config", self._director.config) is not self._director.config:
                self._router.replace_config(self._director.config)
            self._active_context_id = context_id
            self._current_identity = "holomind"
            self._observer.begin(context_id)
        self.mark_thinking()
        try:
            plan = self._router.route(user_message, context, mode, skill, context_id)
            with self._lock:
                if self._active_context_id != context_id:
                    return context_id
                self._current_identity = plan.center_identity
            self._director.apply_scene(plan)
        except Exception as error:
            logger.warning("hologram_turn_router_fallback context_id=%s error=%s", context_id, type(error).__name__)
        return context_id

    def observe_response_text(self, text: str, context_id: str | None = None) -> None:
        with self._lock:
            current = context_id or self._active_context_id
            if current is None or current != self._active_context_id:
                return
            allowed = {item.id for item in self._director.config.identities if item.enabled}
            identity = self._observer.observe(text, current, self._current_identity, allowed)
            if identity is None:
                return
            self._current_identity = identity
        self._safe(lambda: self._director.set_identity(identity), "observer")

    def finish_turn(self, context_id: str | None = None) -> bool:
        return self._close_turn(context_id, "finish")

    def fail_turn(self, error: Exception | None = None, context_id: str | None = None) -> bool:
        if error is not None:
            logger.warning("hologram_turn_failed error=%s", type(error).__name__)
        return self._close_turn(context_id, "fail")

    def _close_turn(self, context_id: str | None, outcome: str) -> bool:
        with self._lock:
            current = context_id or self._active_context_id
            if current is None or current in self._closed or current != self._active_context_id:
                return False
            self._closed.add(current)
            self._active_context_id = None
            self._current_identity = "holomind"
        self._safe(lambda: self._director.finish_promotion_context(current), f"{outcome}_context")
        self._safe(self._director.resume_rotation, f"{outcome}_rotation")
        self._safe(lambda: self._director.set_identity("holomind"), f"{outcome}_identity")
        self._safe(lambda: self._director.set_mascot_state("idle"), f"{outcome}_idle")
        return True

    @staticmethod
    def _safe(callback, action: str) -> None:
        try:
            callback()
        except Exception as error:
            logger.warning("hologram_turn_action_failed action=%s error=%s", action, type(error).__name__)
