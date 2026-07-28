# Demostración escolar: tres ventiladores

Esta demostración usa tres ventiladores independientes. Holograma no sube
videos: HoloMissYou administra las playlists y Holograma solo resuelve un ID
semántico al índice configurado y envía `play_file(index)`.

## Modo local recomendado

Ejecute frontend y FastAPI en la misma computadora, con FastAPI en
`127.0.0.1`. No configure `HOLOGRAM_API_TOKEN` ni
`VITE_HOLOGRAM_API_TOKEN`. No hace falta publicar la API para que el backend se
conecte a las IP de los ventiladores.

Para una red controlada posterior puede usar FastAPI en `0.0.0.0` y configurar
el mismo valor en ambos entornos:

```env
HOLOGRAM_API_TOKEN=una_clave_segura
VITE_HOLOGRAM_API_TOKEN=una_clave_segura
```

El valor `VITE_` queda embebido en el frontend: ofrece una protección básica en
una red controlada, no autenticación fuerte para Internet público.

## 1. Cargar los archivos en HoloMissYou

1. Conecte el teléfono a la red `SpinDisplay`.
2. Abra HoloMissYou.
3. Seleccione una sola unidad, nunca un grupo sincronizado/splicing.
4. Abra su playlist y cargue cada video individualmente.
5. Anote el orden visible de los archivos.
6. Repita el proceso para cada ventilador.

No use pantalla unificada. Cada unidad conserva IP, playlist y catálogo de
índices propios.

## 2. Configuración provisional de la demo

| Rol | Contenido lógico | Índice provisional |
|---|---|---:|
| top | `idle` | 0 |
| top | `listening` | 1 |
| top | `thinking` | 2 |
| top | `speaking` | 2 |
| center | `holomind` | 0 |
| center | `unev` | 0 |
| center | `itee` | 1 |
| bottom | `random_1` | 0 |
| bottom | `random_2` | 1 |
| bottom | `random_3` | 2 |

Dos estados lógicos pueden compartir un índice. Mientras no exista un video de
Holomind, `holomind` y `unev` comparten el video UNEV: no elimine la identidad
semántica `holomind`, porque sigue siendo el fallback del sistema.

Para las promociones use `duration_seconds: 10`. El hardware no informa el fin
del archivo: la rotación lógica espera esa duración y solicita `0 → 1 → 2 → 0`.

## 3. Guardar catálogo e IPs

El catálogo persistente es `data/hologram_media.json`. Settings guarda y valida
unidades, identidades y promociones. El editor de estados de mascota sigue
pendiente; para esta demo edite manualmente `mascot_states` con los valores de
la tabla, valide el JSON y reinicie el proceso si ya estaba ejecutándose.

Ejemplo de IPs históricos, solo como referencia:

```text
top     10.10.2.211
center  10.10.2.212
bottom  10.10.2.213
```

La posición física de cada IP debe identificarse en cada instalación. Nunca
copie estos valores a producción sin confirmarlos.

## 4. Calibración física obligatoria

El contrato de software usa base cero, pero la playlist física todavía debe
confirmarse observando el ventilador. Para cada rol pruebe índice `0`, `1` y
`2`, y complete esta tabla:

| Rol | IP | Índice enviado | Contenido observado |
|---|---|---:|---|
| top | | 0/1/2 | |
| center | | 0/1/2 | |
| bottom | | 0/1/2 | |

Puede usar Settings, el endpoint de prueba o:

```bash
.venv/bin/python scripts/diagnose_hologram.py --role center --connect --index 0
```

El software solo confirma que el comando salió sin excepción; el operador debe
observar el ventilador. Si no coincide, corrija el catálogo configurado. No
introduzca un offset global `+1`/`-1` sin evidencia física reproducible.

## 5. Qué hace la IA

```text
Usuario: “Háblame de la UNEV”
MediaRouter: identity_id = "unev"
Director: resuelve el índice UNEV configurado
Hardware: center.play_file(0)
```

Para “¿Qué relación tiene esto con el ITEE?”, el router selecciona `itee` y el
director envía el índice configurado, provisionalmente `center.play_file(1)`.
Sin contexto especial, bottom rota los tres índices. Con promociones
categorizadas puede mostrar una temporalmente y luego reanudar; con tres videos
aleatorios basta la rotación continua.

La IA nunca conoce IP, puerto, índice, archivos físicos ni HoloMissYou.

## Límites honestos

Hardware físico: **NO PROBADO** con este repositorio. La correspondencia real
playlist/índice es **PENDIENTE** de calibración. El panel no confirma reproducción
visual y el editor de estados de mascota está pendiente.
