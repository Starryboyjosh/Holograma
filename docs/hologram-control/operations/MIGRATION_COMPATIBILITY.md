# Migración y compatibilidad

## Variables heredadas

- `HOLOGRAM_TCP_IP`
- `HOLOGRAM_TCP_PORT`
- `HOLOGRAM_CLIP_*`

## Regla

Si no existe catálogo nuevo, la configuración heredada opera sobre `top`.

## Endpoints heredados

Continuar delegando a `top` durante estas waves.

## Reversión

Eliminar o renombrar `data/hologram_media.json` permite volver al modo heredado.

No eliminar código antiguo hasta que Sol apruebe la migración.
