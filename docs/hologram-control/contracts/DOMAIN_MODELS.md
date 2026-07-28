# Modelos de dominio

## Tipos

```python
FanRole = Literal["top", "center", "bottom"]
MascotState = Literal["idle", "listening", "thinking", "speaking", "error", "offline"]
PromotionAction = Literal["continue_rotation", "focus_item", "focus_category"]
```

## Entidades

- `FanUnitConfig`
- `IdentityMedia`
- `PromotionMedia`
- `RotationConfig`
- `RoutingConfig`
- `ScenePlan`
- `FanUnitStatus`
- `HologramStatus`

## Invariantes

- Índices `0..255`.
- IDs únicos.
- Una identidad default.
- Holomind siempre disponible.
- Medios deshabilitados no se seleccionan.
- Ninguna entidad de IA contiene IP o índice.
