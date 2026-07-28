"""Modelos validados del catálogo holográfico; no contienen transporte TCP."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

FanRole = Literal["top", "center", "bottom"]
MascotState = Literal["idle", "listening", "thinking", "speaking", "error", "offline"]
PromotionAction = Literal["continue_rotation", "focus_item", "focus_category"]

_ROLES: tuple[FanRole, ...] = ("top", "center", "bottom")
_PLAYABLE_MASCOT_STATES = ("idle", "listening", "thinking", "speaking")


def _index(value: int, label: str = "index") -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 255:
        raise ValueError(f"{label} debe estar entre 0 y 255.")
    return value


@dataclass(frozen=True)
class FanUnitConfig:
    enabled: bool = True
    ip: str = ""
    port: int = 50200
    identify_index: int = 255

    def __post_init__(self) -> None:
        if not isinstance(self.enabled, bool):
            raise ValueError("enabled debe ser booleano.")
        if not isinstance(self.ip, str):
            raise ValueError("ip debe ser texto.")
        if self.enabled and not self.ip.strip():
            raise ValueError("Una unidad habilitada requiere IP.")
        if not isinstance(self.port, int) or isinstance(self.port, bool) or not 1 <= self.port <= 65535:
            raise ValueError("port debe estar entre 1 y 65535.")
        _index(self.identify_index, "identify_index")


@dataclass(frozen=True)
class IdentityMedia:
    id: str
    title: str
    index: int
    enabled: bool = True
    default: bool = False
    keywords: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.title.strip():
            raise ValueError("La identidad requiere id y título.")
        _index(self.index)
        if any(not isinstance(keyword, str) or not keyword.strip() for keyword in self.keywords):
            raise ValueError("Las keywords deben ser textos no vacíos.")


@dataclass(frozen=True)
class PromotionMedia:
    id: str
    title: str
    index: int
    enabled: bool = True
    categories: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()
    duration_seconds: float = 10
    priority: int = 0
    rotation_enabled: bool = True

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.title.strip():
            raise ValueError("La promoción requiere id y título.")
        _index(self.index)
        if self.duration_seconds <= 0:
            raise ValueError("duration_seconds debe ser mayor que cero.")
        if not isinstance(self.priority, int) or isinstance(self.priority, bool):
            raise ValueError("priority debe ser entero.")
        if not isinstance(self.rotation_enabled, bool):
            raise ValueError("rotation_enabled debe ser booleano.")
        if any(not isinstance(category, str) or not category.strip() for category in self.categories):
            raise ValueError("Las categorías deben ser textos no vacíos.")


@dataclass(frozen=True)
class RotationConfig:
    enabled: bool = True
    resume_mode: Literal["next", "current"] = "next"
    minimum_context_seconds: float = 10
    maximum_context_seconds: float = 45

    def __post_init__(self) -> None:
        if self.resume_mode not in ("next", "current"):
            raise ValueError("resume_mode inválido.")
        if self.minimum_context_seconds < 0 or self.maximum_context_seconds < self.minimum_context_seconds:
            raise ValueError("Ventana de rotación inválida.")


@dataclass(frozen=True)
class RoutingConfig:
    mode: Literal["rules", "local", "hybrid", "small_model", "disabled"] = "hybrid"
    minimum_confidence: float = 0.75
    small_model_enabled: bool = True
    small_model_timeout_seconds: float = 1.5
    identity_hold_seconds: float = 4
    max_identity_changes_per_turn: int = 1

    def __post_init__(self) -> None:
        if self.mode not in ("rules", "local", "hybrid", "small_model", "disabled"):
            raise ValueError("mode de routing inválido.")
        if not 0 <= self.minimum_confidence <= 1:
            raise ValueError("minimum_confidence debe estar entre 0 y 1.")
        if self.small_model_timeout_seconds <= 0 or self.identity_hold_seconds < 0:
            raise ValueError("Tiempos de routing inválidos.")
        if self.max_identity_changes_per_turn < 0:
            raise ValueError("max_identity_changes_per_turn inválido.")


@dataclass(frozen=True)
class ScenePlan:
    center_identity: str = "holomind"
    promotion_action: PromotionAction = "continue_rotation"
    promotion_id: str | None = None
    promotion_category: str | None = None
    confidence: float = 0
    source: str = "fallback"
    reason_code: str = "NO_RELIABLE_MATCH"
    context_id: str | None = None

    def __post_init__(self) -> None:
        if not self.center_identity.strip():
            raise ValueError("center_identity es obligatorio.")
        if self.promotion_action not in ("continue_rotation", "focus_item", "focus_category"):
            raise ValueError("promotion_action inválido.")
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence debe estar entre 0 y 1.")
        if self.promotion_action == "focus_item" and not self.promotion_id:
            raise ValueError("focus_item requiere promotion_id.")
        if self.promotion_action == "focus_category" and not self.promotion_category:
            raise ValueError("focus_category requiere promotion_category.")


@dataclass(frozen=True)
class FanUnitStatus:
    role: FanRole
    enabled: bool
    ip: str
    port: int
    connected: bool
    current_index: int | None
    current_media_id: str | None
    last_error: str | None
    worker_alive: bool
    requested_index: int | None = None
    last_sent_index: int | None = None
    last_send_result: str | None = None
    last_send_at: float | None = None
    semantic_id: str | None = None
    retry_count: int = 0


@dataclass(frozen=True)
class HologramStatus:
    units: dict[FanRole, FanUnitStatus]
    default_identity_id: str
    rotation: dict = field(default_factory=dict)


@dataclass(frozen=True)
class HologramConfig:
    version: int = 1
    units: dict[FanRole, FanUnitConfig] = field(default_factory=dict)
    mascot_states: dict[str, int] = field(default_factory=dict)
    identities: tuple[IdentityMedia, ...] = ()
    promotions: tuple[PromotionMedia, ...] = ()
    rotation: RotationConfig = field(default_factory=RotationConfig)
    routing: RoutingConfig = field(default_factory=RoutingConfig)

    def __post_init__(self) -> None:
        if self.version != 1:
            raise ValueError("Versión de catálogo no compatible.")
        if set(self.units) != set(_ROLES):
            raise ValueError("units debe contener top, center y bottom.")
        for state in _PLAYABLE_MASCOT_STATES:
            if state not in self.mascot_states:
                raise ValueError(f"Falta el estado de mascota {state}.")
            _index(self.mascot_states[state], f"mascot_states.{state}")
        all_ids = [item.id for item in self.identities] + [item.id for item in self.promotions]
        if len(all_ids) != len(set(all_ids)):
            raise ValueError("Los IDs de medios deben ser únicos.")
        defaults = [item for item in self.identities if item.default and item.enabled]
        if len(defaults) != 1:
            raise ValueError("Debe existir exactamente una identidad predeterminada habilitada.")
        holomind = [item for item in self.identities if item.id == "holomind" and item.enabled]
        if len(holomind) != 1:
            raise ValueError("Holomind debe estar disponible y habilitado.")

    @property
    def default_identity_id(self) -> str:
        return next(item.id for item in self.identities if item.default and item.enabled)

    @classmethod
    def default(cls) -> HologramConfig:
        return cls(
            units={role: FanUnitConfig(enabled=False) for role in _ROLES},
            mascot_states={"idle": 0, "listening": 1, "thinking": 3, "speaking": 2},
            identities=(IdentityMedia("holomind", "Holomind", 0, default=True, keywords=("holomind",)),),
        )

    @classmethod
    def from_dict(cls, raw: dict) -> HologramConfig:
        if not isinstance(raw, dict):
            raise ValueError("El catálogo debe ser un objeto JSON.")
        units = {role: FanUnitConfig(**raw.get("units", {}).get(role, {})) for role in _ROLES}
        identities = tuple(
            IdentityMedia(**{**item, "keywords": tuple(item.get("keywords", ()))})
            for item in raw.get("identities", [])
        )
        promotions = tuple(
            PromotionMedia(
                **{
                    **item,
                    "categories": tuple(item.get("categories", (item.get("category"),)) if item.get("category") and "categories" not in item else item.get("categories", ())),
                    "keywords": tuple(item.get("keywords", item.get("topics", ()))),
                }
            )
            for item in raw.get("promotions", [])
        )
        return cls(
            version=raw.get("version", 1), units=units,
            mascot_states=dict(raw.get("mascot_states", {})), identities=identities,
            promotions=promotions, rotation=RotationConfig(**raw.get("rotation", {})),
            routing=RoutingConfig(**raw.get("routing", {})),
        )

    def to_dict(self) -> dict:
        return asdict(self)
