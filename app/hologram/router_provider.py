"""Contrato aislado para el submodelo opcional del MediaRouter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class MediaRouteRequest:
    user_message: str
    conversation_mode: str | None
    recent_context: str | None
    identity_candidates: tuple[str, ...]
    promotion_candidates: tuple[str, ...]


@dataclass(frozen=True)
class MediaRouteResult:
    center_identity: str
    promotion_action: str = "continue_rotation"
    promotion_id: str | None = None
    promotion_category: str | None = None
    confidence: float = 0.0
    reason_code: str = "PROVIDER_SELECTION"


class MediaRouterProvider(Protocol):
    def select(self, request: MediaRouteRequest) -> MediaRouteResult: ...
