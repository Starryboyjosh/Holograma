# Estado real del repositorio

## Existente

- `HologramFanController`.
- TCP puerto `50200`.
- `play_file(index)`.
- Rango `0..255`.
- `HologramStateManager`.
- Cola, dedupe y reconexión.
- Estados `idle`, `listening`, `thinking`, `speaking`.
- Endpoints para una unidad.
- UI para una conexión.
- Tests de controlador.
- Script/prueba de tres IP.

## IP históricas

- `10.10.2.211`
- `10.10.2.212`
- `10.10.2.213`

No se conoce su posición física definitiva.

## Rutas de conversación

```text
call.py → ruta sync
ConversationService → ruta async/web
```

## Brechas

- Director de tres unidades.
- Catálogo.
- Rotación.
- ScenePlan.
- MediaRouter.
- UI multiunidad.
- Simulador integral.
- Status detallado.
