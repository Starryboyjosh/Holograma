"""Corrección conservadora de identidad basada en texto que sí será hablado."""

from __future__ import annotations

import re
import time

from .media_router import normalize_media_text


class SceneObserver:
    def __init__(self, identity_hold_seconds: float = 4, clock=time.monotonic) -> None:
        self._hold = identity_hold_seconds
        self._clock = clock
        self._context_id: str | None = None
        self._buffer = ""
        self._changes = 0
        self._last_change = 0.0

    def begin(self, context_id: str) -> None:
        self._context_id, self._buffer, self._changes = context_id, "", 0
        self._last_change = self._clock()

    def observe(self, text: str, context_id: str, current_identity: str, allowed: set[str]) -> str | None:
        if context_id != self._context_id or self._changes >= 1:
            return None
        self._buffer = (self._buffer + " " + text)[-700:]
        normalized = normalize_media_text(self._buffer)
        latest = normalize_media_text(text)
        if len(normalized) < 18 or self._clock() - self._last_change < self._hold:
            return None
        selected = None
        if "itee" in allowed and "itee" in latest and not re.search(r"\b(no|sin)\b.*\bitee\b", latest):
            if any(term in normalized for term in ("afili", "relacion", "particip", "instituto")):
                selected = "itee"
        if selected is None and "unev" in allowed and any(term in normalized for term in ("unev", "universidad evangelica", "la universidad")):
            selected = "unev"
        if selected and selected != current_identity:
            self._changes += 1
            self._last_change = self._clock()
            return selected
        return None
