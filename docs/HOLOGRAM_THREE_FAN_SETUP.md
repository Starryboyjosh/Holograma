# Holograma de tres ventiladores

La operación normal usa tres unidades independientes: `top` (mascota), `center`
(identidades) y `bottom` (promociones). Cada una tiene su IP, puerto, playlist,
cola y errores; no usar Sync Group como un único lienzo operativo.

Los IDs semánticos (`unev`, `itee`, `careers`) se resuelven dentro del backend.
El ventilador recibe únicamente un índice numérico base cero, entre `0` y `255`.
El índice `0` es válido. Los nombres oficiales `1-1`, `2-1`, `3-1` identifican
unidades, no índices de reproducción.

Las IP `10.10.2.211`, `.212` y `.213` son ejemplos históricos: identificar el
rol físico en cada instalación antes de guardarlo. No se ha realizado validación
física con este repositorio.

## Operación escolar local

Para la demo use frontend y FastAPI en la misma computadora (`127.0.0.1`) y deje
`HOLOGRAM_API_TOKEN` / `VITE_HOLOGRAM_API_TOKEN` sin configurar. El backend aún
puede alcanzar las IP de las unidades. Para acceso desde otros dispositivos use
una red controlada, `0.0.0.0` y el mismo token en ambas variables; el token Vite
es una protección básica, no seguridad de Internet público. Consulte
`HOLOGRAM_SCHOOL_DEMO.md` para carga, catálogo provisional y calibración.

## Calibración física pendiente

| Rol | IP | Puerto | Índice solicitado | Contenido observado | Resultado |
|---|---|---:|---:|---|---|
| top | | 50200 | 0 | | |
| center | | 50200 | 0 | | |
| bottom | | 50200 | 0 | | |

Identifique una sola IP, pruebe `0`, luego `1`, registre la playlist observada y
corrija el catálogo si no coincide. No introduzca offsets `+1`/`-1` sin evidencia
reproducible.
