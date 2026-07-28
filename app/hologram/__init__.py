"""Dominio y orquestación de las unidades holográficas."""

from .compatibility import create_legacy_hologram_manager
from .config_store import HologramConfigStore
from .director import HologramDirector
from .models import (
    FanRole,
    HologramConfig,
    MascotState,
    PromotionAction,
    ScenePlan,
)
from .rotation import PromotionRotationManager, RealClock, VirtualClock
from .simulator import HologramSimulator, SimulatorEvent
from .unit_manager import HologramUnitManager

__all__ = [
    "FanRole",
    "HologramConfig",
    "HologramConfigStore",
    "HologramDirector",
    "HologramUnitManager",
    "HologramSimulator",
    "MascotState",
    "PromotionAction",
    "PromotionRotationManager",
    "RealClock",
    "ScenePlan",
    "SimulatorEvent",
    "VirtualClock",
    "create_legacy_hologram_manager",
]
