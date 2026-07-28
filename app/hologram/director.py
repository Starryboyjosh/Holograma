"""Director semántico único de top, center y bottom."""

from __future__ import annotations

from collections.abc import Callable

from .models import FanRole, HologramConfig, HologramStatus, MascotState, ScenePlan
from .rotation import PromotionRotationManager
from .unit_manager import HologramUnitManager


class HologramDirector:
    def __init__(self, config: HologramConfig, manager_factory: Callable[..., HologramUnitManager] = HologramUnitManager, clock=None) -> None:
        self.config = config
        self._manager_factory = manager_factory
        self._clock = clock
        self.units: dict[FanRole, HologramUnitManager] = {
            role: manager_factory(role, config.units[role]) for role in ("top", "center", "bottom")
        }
        self.rotation = PromotionRotationManager(config.promotions, self.units["bottom"], config.rotation, clock=clock)
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        self._started = True
        for manager in self.units.values():
            manager.start()
        self.restore_default_scene()

    def close(self) -> None:
        if not self._started and not any(unit.status().worker_alive for unit in self.units.values()) and not self.rotation.get_status()["thread_alive"]:
            return
        self.rotation.close()
        for manager in self.units.values():
            manager.close()
        self._started = False

    def set_mascot_state(self, state: MascotState) -> None:
        if state not in self.config.mascot_states:
            return
        self.units["top"].request(self.config.mascot_states[state], f"mascot:{state}")

    def set_identity(self, identity_id: str) -> None:
        identity = next((item for item in self.config.identities if item.id == identity_id and item.enabled), None)
        if identity is None:
            identity = next(item for item in self.config.identities if item.id == "holomind" and item.enabled)
        self.units["center"].request(identity.index, f"identity:{identity.id}")

    def play_promotion(self, promotion_id: str) -> None:
        item = next((item for item in self.config.promotions if item.id == promotion_id and item.enabled), None)
        if item is None:
            raise ValueError(f"Promoción inexistente o deshabilitada: {promotion_id}.")
        self.units["bottom"].request(item.index, f"promotion:{item.id}")

    def start_rotation(self) -> None:
        self.start()
        self.rotation.start()

    def pause_rotation(self) -> None:
        self.rotation.pause()

    def resume_rotation(self) -> None:
        self.rotation.resume()

    def stop_rotation(self) -> None:
        self.rotation.stop()

    def focus_promotion(self, promotion_id: str, context_id: str | None = None) -> None:
        self.start()
        self.rotation.focus_item(promotion_id, context_id)

    def focus_promotion_category(self, category: str, context_id: str | None = None) -> None:
        self.start()
        self.rotation.focus_category(category, context_id)

    def finish_promotion_context(self, context_id: str | None = None) -> None:
        self.rotation.finish_context(context_id)

    def reconfigure(self, config: HologramConfig) -> None:
        was_started = self._started
        self.close()
        self.config = config
        self.units = {role: self._manager_factory(role, config.units[role]) for role in ("top", "center", "bottom")}
        self.rotation = PromotionRotationManager(config.promotions, self.units["bottom"], config.rotation, clock=self._clock)
        if was_started:
            self.start()

    def apply_scene(self, scene_plan: ScenePlan) -> None:
        self.set_identity(scene_plan.center_identity)
        if scene_plan.promotion_action == "focus_item" and scene_plan.promotion_id:
            self.play_promotion(scene_plan.promotion_id)
        elif scene_plan.promotion_action == "focus_category" and scene_plan.promotion_category:
            item = next((p for p in self.config.promotions if p.enabled and scene_plan.promotion_category in p.categories), None)
            if item:
                self.play_promotion(item.id)

    def restore_default_scene(self) -> None:
        self.set_mascot_state("idle")
        self.set_identity(self.config.default_identity_id)

    def get_status(self) -> HologramStatus:
        return HologramStatus(
            {role: manager.status() for role, manager in self.units.items()},
            self.config.default_identity_id,
            self.rotation.get_status(),
        )
