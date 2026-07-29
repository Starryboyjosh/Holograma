# Holograma UNEV

Asistente multimodal para la Universidad Virtual (UNEV): LLM, visión (presencia), voz (STT/TTS) y API WebSocket. Puede correr **local** (Ollama, Whisper, Piper, YOLO) o con APIs en la nube.

## Qué hay en el repo

| Ruta | Rol |
|------|-----|
| `call.py` | CLI: teclado / voz / cámara; ruta **sync** del LLM (`generate_reply`) |
| `main.py` | FastAPI + WebSocket + lifespan; orquesta la ruta **async** web |
| `app/` | Servicios Fase 3: `ConversationService`, `LLMService`, `CameraContextProvider`, WS |
| `app/tools/` | Herramientas del LLM (function calling): navegación web con Lightpanda |
| `llm_backend.py` | Streaming/fallback de proveedores, CoT en terminal, timeouts unificados |
| `provider_config.py` | Contrato de proveedores (`LLM_PROVIDER`, keys, modelos) |
| `camera_context.py` | Contexto de cámara neutro (sin acoplar CLI ↔ LLM) |
| `vision/` | Cámara OpenCV + YOLOE open-vocab (`yoloe-26n-seg`); `geometry.py` e `image_signals.py` son funciones puras testeables sin cargar el modelo |
| `stt/` | Faster-Whisper + sounddevice |
| `docker-compose.yml` | Servicio Lightpanda (motor de navegación web) y, con perfil `full`, el backend |
| `skills/` + `data/` | Router local, UNEV, Honduras |
| `hologram_controller.py` | Ventilador holográfico TCP (opcional) |
| `frontend/` | UI React + shell Tauri |
| `scripts/` | Setup, diagnóstico, launchers |
| `security.py` / `auth_token.py` | Saneo, redacción de secretos, token API opt-in |
| `graphify-out/` | Grafo de conocimiento del repo — **generado, no versionado** (ver abajo) |
| `tests/` | Pytest (contratos de proveedor, unificación LLM, servicios, etc.) |

Config de referencia (no secretos): [`.env.example`](.env.example), [`config.example.json`](config.example.json).  
Detalle de proveedores: [`docs/CONFIG.md`](docs/CONFIG.md). Holograma físico: [`docs/HOLOGRAM.md`](docs/HOLOGRAM.md).

### Dos rutas de LLM (intencional)

```
Voz / CLI  →  call.ask_ai  →  generate_reply()      (sync, CoT en terminal)
Web / WS   →  ConversationService  →  LLMService  →  stream_llm_response()
```

El contexto de cámara se **inyecta** en ambos casos (`camera_context=…`). `llm_backend` no importa `call` (rompe el ciclo de dependencias). En web, el callback de cámara alimenta `CameraContextProvider`; en voz, `call` usa `camera_context.build_camera_context`.

## Navegación web (Lightpanda)

El LLM puede leer una página en tiempo real mediante la herramienta
`browse_web_page` (function calling). El motor es **Lightpanda**, único y sin
fallback: se habla CDP por WebSocket, sin Puppeteer ni Node.

```bash
docker compose up -d lightpanda          # motor en ws://127.0.0.1:9222
./.venv/bin/python scripts/smoke_lightpanda.py   # prueba de humo
```

Funciona con modelos locales (Ollama) y de nube, siempre que el modelo soporte
`tools` — en Ollama se comprueba con `ollama show <modelo>`.

**Sin internet no se ofrece la herramienta.** Antes de cada turno se comprueba
que Lightpanda responda y que haya red; si no, al modelo se le inyecta una
instrucción que le prohíbe prometer una consulta que no puede hacer, en vez de
dejarle inventar datos o quedarse esperando un timeout. Es el caso típico de un
kiosco con modelo local y la red caída.

| Variable | Uso |
|----------|-----|
| `HOLOGRAM_WEB_TOOLS` | `auto` (default, solo si el prompt lo pide) · `always` · `off` |
| `LIGHTPANDA_CDP_URL` | `ws://127.0.0.1:9222`; en Compose `ws://lightpanda:9222` |
| `LIGHTPANDA_MAX_CHARS` | Recorte del texto extraído (default `8000`) |
| `HOLOGRAM_TOOL_TEMPERATURE` | Determinismo al decidir si navegar (default `0.0`) |

En modo `auto` un pre-filtro detecta URLs y palabras de tiempo real, así que las
preguntas normales sobre la UNEV no pagan la llamada extra al LLM.

> El puerto 9222 se publica **solo en loopback**: el endpoint CDP permite
> controlar el navegador por completo, así que no lo expongas a la red.

## Reglas de compatibilidad Linux ↔ Windows

1. **`pathlib`** para rutas de archivos  
2. **`sounddevice`** para micrófono (no PyAudio)  
3. Dependencias en **`requirements.txt`**

## Instalación

```bash
python -m venv .venv
./.venv/bin/pip install --upgrade pip setuptools wheel
# Opcional (visión / torch CPU):
./.venv/bin/pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
./.venv/bin/pip install -r requirements.txt
./.venv/bin/python scripts/setup_hologram.py
```

Windows (PowerShell): usa `py -m venv .venv` y `.\.venv\Scripts\…` en lugar de `./.venv/bin/…`.

Copia `.env.example` → `.env` (o deja que el setup genere `config.json`).  
Modelos YOLO/Piper van en `models/` (ignorados por git). Ollama local recomendado: `ollama pull gemma3:1b`.

## Ejecutar

| Modo | Comando |
|------|---------|
| Teclado | `./.venv/bin/python call.py` |
| Voz + cámara | `./.venv/bin/python call.py --voice --camera` |
| API + WS | `./.venv/bin/python main.py` (o `scripts/run_web.sh`) |
| Diagnóstico | `./.venv/bin/python scripts/diagnose_hologram.py` |

Frontend: ver `frontend/README.md` (Vite / Tauri). La UI habla con el backend en `HOLOGRAM_PORT` (default `8000`).

## Configuración esencial

Todo el catálogo de variables está en **`.env.example`**. Lo mínimo para un kiosco:

| Variable | Uso típico |
|----------|------------|
| `LLM_PROVIDER` / `OLLAMA_MODEL` | Cerebro (nube, Groq, o local); la elección de proveedor es autoritativa |
| `LLM_MAX_TOKENS` | Límite de salida unificado (default `450`) para todos los backends |
| `LLM_REQUEST_TIMEOUT` | Timeout HTTP en la nube (default `90` s); evita colgar la voz |
| `LLM_LOG_COT` | CoT/razonamiento en terminal (`1` por defecto; `0` para silenciar) |
| `HOLOGRAM_CAMERA` / `YOLO_MODEL` | Visión (`1` + `yoloe-26n-seg.pt`) |
| `YOLO_IMGSZ` / `YOLO_INTERVAL_SECONDS` | Coste de detección local |
| `WHISPER_MODEL` / `WHISPER_BEAM_SIZE` | STT |
| `WHISPER_MAX_RECORD_SECONDS` / `WHISPER_MAX_WAIT_SECONDS` | Presupuestos **independientes**: cuánto se graba y cuánto se espera a que la persona arranque |
| `WHISPER_NOISE_PERCENTILE` / `WHISPER_NOISE_FACTOR` | Umbral adaptativo sobre el ruido ambiente |
| `TTS_BACKEND` / `HOLOGRAM_TTS_STREAM` | Piper u OS; TTS por cláusulas en web |
| `HOLOGRAM_WEB_TOOLS` | Navegación web del LLM (`auto` / `always` / `off`) |
| `HOLOGRAM_TCP_IP` | Vacío = sin ventilador físico |

### Voz: latencia y robustez

El TTS en streaming usa un pipeline de 3 etapas (tokens → síntesis → audio), así
que la cláusula siguiente se sintetiza mientras suena la actual y no hay
silencios entre frases.

En el STT, el umbral de silencio se recalibra **a la baja** durante la espera:
si el visitante ya estaba hablando cuando arrancó la escucha, su voz no se
confunde con el ruido de fondo. Y esperar a que alguien se decida no recorta el
tiempo disponible para grabar su frase.

La detección YOLO **sigue activa** aunque no haya personas; solo se espacia el coste y el encode MJPEG si nadie mira el feed.

Contenido institucional editable: `data/unev_info.json` (UI “Contenido” / API). Fuente de código: `skills/unev_content.py`.

Probar conexión de un proveedor desde la UI (Ajustes) o `POST /api/llm/test` (no persiste keys).

## Pruebas

```bash
./.venv/bin/python -m pytest -q
./.venv/bin/python scripts/diagnose_hologram.py --speak "Hola"
# API sin cámara/mic:
HOLOGRAM_CAMERA=0 HOLOGRAM_INPUT=keyboard ./.venv/bin/python main.py
```

Contratos útiles: `tests/test_llm_unify.py` (tokens, CoT, fallback, event loop),
`tests/test_app_services.py` (orquestación Fase 3), `tests/test_provider_config.py`,
`tests/test_tts_pipeline.py` (solape síntesis/audio), `tests/test_stt_capture_budget.py`
(presupuestos de captura y umbral adaptativo), `tests/test_web_availability.py`
(navegación web y modo sin internet).

Toda la suite corre sin hardware: cámara, micrófono, altavoces y Lightpanda se
sustituyen por dobles.

## Comandos de chat

`ayuda`, `backend`, `modo normal|jueces|expo|admisiones`, `saludar`, `persona` / `se fue` / `grupo` (simulan visión).

## Grafo del código (graphify)

El repo lleva un grafo en `graphify-out/` para navegar arquitectura y dependencias:

```bash
graphify query "cómo fluye el LLM en web y en voz"
graphify path "ConversationService" "stream_llm_response"
graphify explain "CameraContextProvider"
# Tras cambiar código (AST, sin coste de LLM):
graphify update .
```

Abrir `graphify-out/graph.html` en el navegador o leer `GRAPH_REPORT.md`.

**`graphify-out/` no se versiona.** Es un artefacto generado (~7 MB) que se
reescribe entero en cada actualización: `graph.json` y `graph.html` son de una
sola línea, así que cada diff sería el archivo completo. En un clon nuevo se
regenera con `graphify .` (el paso AST no cuesta tokens; la parte semántica de
docs sí usa LLM).

## Licencia

Proyecto educativo UNEV — uso interno y demostrativo.
