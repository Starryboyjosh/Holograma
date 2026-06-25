# Holograma físico MISSYOU — integración por TCP

Cómo la IA controla el ventilador holográfico MISSYOU (modelos MSPJ65S4 /
MSPJ70S4, 3 unidades en *splicing*). Referencia del protocolo:
[`Holograma_MISSYOU_Referencia_IA.pdf`](Holograma_MISSYOU_Referencia_IA.pdf).

## TL;DR — "cambiar el video por índice" YA es el mecanismo

El dispositivo **no renderiza 3D en vivo: es un reproductor de archivos**. Lo que
parece volumétrico son MP4 pre-renderizados con fondo negro. La única forma de
cambiar lo que se ve es saltar a otro clip de la playlist por su índice, con el
comando estrella del protocolo:

```
0x5B 0x06 N      →  "reproducir clip N"   (N = 0..255, 0 = primer clip)
```

Esto **ya está implementado** en `hologram_controller.py` y se usa de dos formas:

1. **Automática (lo normal):** la IA mapea su estado a un índice de clip y el
   `HologramStateManager` envía `0x5B 0x06 N` cuando el estado cambia. No hay que
   tocar nada — `call.py` ya llama a `hologram.set_state(...)`.
2. **Manual:** `POST /api/hologram/command {"command":"play_file","index":N}` (o
   `manager.execute("play_file", N)`) salta a cualquier clip, p. ej. un video
   promocional fuera de los 4 estados.

No existe una integración TCP "más rica": el protocolo son 10 comandos de 3 bytes
(ver tabla abajo). Por eso **cambiar el clip por índice no es una alternativa a
evaluar, es *el* diseño correcto y ya está hecho.**

## Reparto de responsabilidades: app HoloMissYou ↔ este controlador

| Tarea | Quién la hace | Notas |
|-------|---------------|-------|
| Subir los MP4/JPG a la playlist | **App HoloMissYou / software PC** | Por WiFi (online) o `.ftlv` a la tarjeta TF (offline). Propietario; un cliente TCP no puede replicarlo |
| Fijar el ORDEN de la playlist (índices) | **App HoloMissYou** | Ese orden ES el `N` del comando `0x5B 0x06 N` |
| Activar "Third party control" | **App HoloMissYou** | Setting → toggle verde. Al activarlo el dispositivo se reinicia |
| Conectarse y cambiar de clip en vivo | **Este controlador (TCP)** | `hologram_controller.py` |
| Mapear estado de la IA → clip | **Este controlador** | `HologramStateManager` |

> **Por eso "mejor integración con la app MISSYOU" NO significa reemplazar la
> app.** La app sigue siendo necesaria una vez para cargar los clips, fijar su
> orden y activar el control third-party. Después, el controlador TCP maneja toda
> la reproducción.

## Arquitectura del código

- **`HologramFanController`** — cliente TCP de bajo nivel. Un método por cada
  comando del protocolo (`start`, `shutdown`, `pause`, `play`, `loop_current`,
  `play_file(index)`, `next_file`, `prev_file`, `brightness_up/down`). Context
  manager (`with`). Mensajes de error accionables si la conexión falla.
- **`HologramStateManager`** — el puente IA↔dispositivo, *thread-safe* y
  *fail-soft*:
  - La IA llama `set_state("idle"|"listening"|"speaking"|"thinking")` desde
    cualquier hilo (voice loop, worker de TTS, hilo de cámara); el manager
    encola los cambios y un único hilo en segundo plano los aplica respetando la
    **regla del protocolo: un comando por paquete TCP**, con `min_send_gap` de
    separación (~0.25 s).
  - *Dedupe*: no reenvía el clip que ya está en pantalla.
  - Reconexión automática con *backoff* exponencial; si no hay IP o el
    dispositivo no responde, **nunca bloquea ni propaga excepciones** hacia la IA.
    La IA corre idéntica con o sin holograma físico.
  - `execute(command, index)` da acceso manual a cualquier comando del protocolo.
- **`create_hologram_manager()`** — construye el manager desde el entorno
  (`HOLOGRAM_TCP_IP/PORT/VERBOSE` + el mapeo de clips). Sin `HOLOGRAM_TCP_IP` el
  manager queda deshabilitado (no-op).
- **`resolve_state_clips(env)`** — función pura que resuelve el mapeo
  estado→índice desde `HOLOGRAM_CLIP_*` (ver siguiente sección).

### Endpoints (`main.py`)

| Endpoint | Acción |
|----------|--------|
| `POST /api/hologram/connect {ip, port}` | Reconfigura el destino TCP en caliente (sin reiniciar FastAPI) |
| `POST /api/hologram/disconnect` | Desactiva el dispositivo y detiene los reintentos |
| `POST /api/hologram/command {command, index?}` | Comando manual (incl. `play_file`) |
| `GET /api/hologram/status` | `{connected, ip, port, ai_paused}` — la UI lo consulta cada 5 s |

La IP/puerto se persisten en `config.json` + `.env`. La UI es la tarjeta
**"Conexión del holograma"** en *Configuración* (`HologramConnection.tsx` +
`useHologram.ts`): IP, puerto, conectar/desconectar y estado en vivo. Los clips
los elige la IA automáticamente; no hay botones de control manual en la UI por
diseño (ver "Pendientes / opcional").

## Mapeo estado de la IA → clip (y por qué se hizo configurable)

| Estado de la IA | Clip por defecto | Comando |
|-----------------|------------------|---------|
| `idle` (en espera) | 0 — loop suave | `0x5B 0x06 0x00` |
| `listening` (escuchando) | 1 — animación de escucha | `0x5B 0x06 0x01` |
| `speaking` (hablando) | 2 — boca/onda en movimiento | `0x5B 0x06 0x02` |
| `thinking` (pensando) | 3 — animación de proceso | `0x5B 0x06 0x03` |

**Fragilidad que esto resuelve:** el índice `N` es la *posición en la playlist*,
no el nombre del archivo — depende del ORDEN en que el operador cargó los clips
en la app HoloMissYou. Si los carga en otro orden, "idle" deja de ser el clip 0 y
el mapeo se rompe en silencio. Por eso el mapeo es **configurable** sin tocar
código, vía entorno:

```bash
HOLOGRAM_CLIP_IDLE=0
HOLOGRAM_CLIP_LISTENING=1
HOLOGRAM_CLIP_SPEAKING=2
HOLOGRAM_CLIP_THINKING=3
```

Un valor inválido (no entero / fuera de 0–255) se ignora y conserva el default,
con un aviso — nunca rompe el arranque de la IA. Lo resuelve `resolve_state_clips`
(pura y con tests en `tests/test_hologram_controller.py`).

## Autoría de los clips (condiciona toda la parte visual)

Del manual; obligatorio para que el contenido se vea bien:

- **Formato:** MP4 (video) o JPG (imagen), pre-cargados en la tarjeta TF.
- **Fondo negro obligatorio** — lo negro = transparente (no se ilumina).
- **Relación de aspecto:** `5:12` para *splicing* de 3 unidades · `1:1` para una
  sola unidad. El clip de prueba `media/UNEV_prueba_3_paneles.mp4` es un ejemplo
  de 3 paneles.
- **Duración:** ≤ 30 s por clip, en loop, para mejor rendimiento.
- **Cargar en orden conocido** (idle, escuchando, hablando, pensando) para fijar
  los índices 0,1,2,3 — o ajustar `HOLOGRAM_CLIP_*` al orden real.

## Conexión

- **WiFi directo:** PC al hotspot `FXXXXXX` (pass `12345678`) → IP `10.10.10.1`.
- **Vía router SpinDisplay (recomendado para 3 unidades):** descubrir la IP
  (`discover_devices()` o el Monitor de recursos de Windows mirando la conexión
  TCP "Missyou") y fijarla con reserva DHCP.
- Activar "Third party control" en la app **antes** de conectar. En algunos
  equipos hay que desactivar el firewall/antivirus de Windows.

## Pendientes / opcional (no hechos a propósito)

- **Disparo manual de clip en la UI.** El backend ya soporta `play_file` por
  índice; la UI se simplificó a "la IA elige los clips" y se quitaron los
  controles manuales. Si se quiere un botón para clips promocionales (índices > 3),
  reintroducir un control que llame a `/api/hologram/command`.
- **Validar en hardware real:** (1) en *splicing* de 3 fans, confirmar que el
  comando a la unidad host se propaga a las 3; (2) no hay lip-sync real — el clip
  "hablando" es un loop genérico; (3) confirmar los detalles del protocolo en
  pruebas reales (el PDF es documento de trabajo).
