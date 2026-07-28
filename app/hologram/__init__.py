"""Dominio y orquestación de las unidades holográficas."""

from .compatibility import create_legacy_hologram_manager
from .config_store import HologramConfigStore
from .conversation_orchestrator import HologramConversationOrchestrator
from .director import HologramDirector
from .media_router import LocalRouteResult, MediaRouter, normalize_media_text
from .models import (
    FanRole,
    HologramConfig,
    MascotState,
    PromotionAction,
    ScenePlan,
)
from .rotation import PromotionRotationManager, RealClock, VirtualClock
from .router_provider import MediaRouteRequest, MediaRouteResult, MediaRouterProvider
from .scene_observer import SceneObserver
from .simulator import HologramSimulator, SimulatorEvent
from .unit_manager import HologramUnitManager

__all__ = [
    "FanRole",
    "HologramConfig",
    "HologramConfigStore",
    "HologramConversationOrchestrator",
    "HologramDirector",
    "HologramUnitManager",
    "LocalRouteResult",
    "MediaRouteRequest",
    "MediaRouteResult",
    "MediaRouter",
    "MediaRouterProvider",
    "HologramSimulator",
    "MascotState",
    "PromotionAction",
    "PromotionRotationManager",
    "RealClock",
    "ScenePlan",
    "SceneObserver",
    "SimulatorEvent",
    "VirtualClock",
    "create_legacy_hologram_manager",
    "normalize_media_text",
]
