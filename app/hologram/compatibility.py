"""Adaptador de la API de una unidad para los consumidores heredados."""

from __future__ import annotations

import os
from dataclasses import replace

from hologram_controller import DEFAULT_STATE_CLIPS, resolve_state_clips

from .director import HologramDirector
from .models import FanUnitConfig, HologramConfig


class LegacyHologramAdapter:
    def __init__(self, director: HologramDirector) -> None:
        self._director = director
        self.state_clips = director.config.mascot_states

    @property
    def enabled(self) -> bool:
        return self._director.units["top"].config.enabled

    @property
    def ip(self) -> str | None:
        return self._director.units["top"].config.ip or None

    @property
    def port(self) -> int:
        return self._director.units["top"].config.port

    @property
    def is_connected(self) -> bool:
        return self._director.units["top"].is_connected

    def start(self) -> None:
        self._director.start()

    def close(self) -> None:
        self._director.close()

    def set_state(self, state: str) -> None:
        self._director.set_mascot_state(state)  # type: ignore[arg-type]

    def configure(self, ip: str, port: int = 50200) -> None:
        if not ip.strip() or not 1 <= port <= 65535:
            raise ValueError("La dirección IP y el puerto del holograma son inválidos.")
        self.close()
        config = self._director.config
        units = dict(config.units)
        units["top"] = FanUnitConfig(enabled=True, ip=ip.strip(), port=port)
        self._director = HologramDirector(replace(config, units=units))
        self.state_clips = self._director.config.mascot_states
        self.start()

    def disable(self) -> None:
        self.close()
        config = self._director.config
        units = dict(config.units)
        units["top"] = FanUnitConfig(enabled=False, port=config.units["top"].port)
        self._director = HologramDirector(replace(config, units=units))

    def execute(self, command: str, index: int | None = None) -> None:
        # Endpoint manual heredado: no es una vía de IA y conserva su contrato.
        self._director.units["top"].execute_legacy(command, index)


def create_legacy_hologram_manager(verbose: bool = False) -> LegacyHologramAdapter:
    del verbose
    ip = os.getenv("HOLOGRAM_TCP_IP", "").strip()
    try:
        port = int(os.getenv("HOLOGRAM_TCP_PORT", "50200"))
    except ValueError:
        port = 50200
    clips = resolve_state_clips()
    config = HologramConfig.default()
    units = dict(config.units)
    units["top"] = FanUnitConfig(enabled=bool(ip), ip=ip, port=port)
    config = replace(config, units=units, mascot_states={**DEFAULT_STATE_CLIPS, **clips})
    return LegacyHologramAdapter(HologramDirector(config))
