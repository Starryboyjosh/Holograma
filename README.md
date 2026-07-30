# Holograma UNEV

Asistente multimodal para la Universidad Virtual (UNEV): LLM multistreaming con fallback entre proveedores, visión open-vocab (YOLOE), voz (STT/TTS) y API WebSocket con orquestación centralizada. Corre **local** (Ollama, Whisper, Piper, YOLOE) o con APIs en la nube (OpenRouter, OpenAI, Anthropic, NVIDIA, Groq, endpoint propio compatible OpenAI).

## Arquitectura

### Tres capas de orquestación (Fase 3)

```
ConversationService (orquestador de turno)
  ├── LLMService        → stream_llm_response()  (ruta async con fallback multi-proveedor)
  ├── CameraContextProvider  → build_context()    (contexto de visión inyectado, no global)
  └── ConnectionManager      → broadcast()        (único emisor de eventos WS, elimina carreras)
```

- **ConversationService** (`app/services/conversation.py`): orquesta un turno completo: emite `streaming_started → text_chunk* → text_done → audio_status`, ejecuta TTS en `to_thread` (nunca bloquea el event loop), y entrega errores como evento `error`.
- **LLMService** (`app/services/llm.py`): envoltura inyectable de `llm_backend.stream_llm_response` para tests sin red.
- **CameraContextProvider** (`app/services/vision.py`): sostiene el último análisis YOLO y construye contexto de cámara desacoplado de la CLI. Rompe el ciclo `call ↔ llm_backend`.
- **ConnectionManager** (`app/connection.py`): registro + difusión async de eventos a todos los clientes WS. Puente `broadcast_threadsafe` para hilos de voz/cámara.

### Dos rutas de LLM (intencional)

```
Voz / CLI  →  call.ask_ai  →  generate_reply() → iter_reply_tokens()  (sync, TTS por cláusulas)
Web / WS   →  ConversationService.handle_prompt() → LLMService.stream() → stream_llm_response()  (async)
```

Ambas rutas comparten `llm_backend` (fallback, CoT, timeouts). El contexto de cámara se **inyecta** en ambas (`camera_context=…`). `llm_backend` no importa `call` —el ciclo de dependencias está roto.

### Fallback multi-proveedor

`llm_backend._candidate_backends()` construye una cadena de respaldo:
1. Proveedor elegido (autoritativo, respeta `LLM_PROVIDER`)
2. Otros proveedores cloud con credenciales configuradas
3. Ollama local (si responde + modelo instalado)
4. `local_only` (skills embebidas, último recurso)

Cada intento sigue una sonda cacheada de Ollama (`OLLAMA_READY_TTL_SECONDS`, fuera del event loop con `to_thread`). Timeout unificado `LLM_REQUEST_TIMEOUT` (default 90 s) y límite de tokens `LLM_MAX_TOKENS` (default 450) para todos los backends.

### Streaming de TTS por cláusulas

`HOLOGRAM_TTS_STREAM=1` (default): Piper arranca en la primera frase completa mientras el LLM sigue generando, reduciendo latencia a primer audio. `HOLOGRAM_TTS_STREAM=0`: habla el texto completo al final del stream.

## Qué hay en el repo

| Ruta | Rol |
|------|-----|
| `main.py` | FastAPI + WebSocket + lifespan; orquesta la ruta async web |
| `call.py` | CLI: teclado / voz / cámara; ruta sync del LLM |
| `app/` | Servicios Fase 3: `ConversationService`, `LLMService`, `CameraContextProvider`, `ConnectionManager` |
| `llm_backend.py` | Streaming/fallback multi-proveedor, CoT en terminal, timeouts unificados, caché de readiness |
| `provider_config.py` | Contrato de 8 proveedores (`LLM_PROVIDER`, keys, modelos, detección automática) |
| `camera_context.py` | Contexto de cámara neutro (desacoplado de CLI ↔ LLM) |
| `vision/` | Cámara OpenCV + YOLOE open-vocab (`yoloe-26n-seg`), detector de personas, análisis facial |
| `stt/` | Faster-Whisper + sounddevice, wakeword |
| `skills/` | Router local, contenido UNEV, Honduras, presencia, modos de evento, apariencia, universidad |
| `data/` | Contenido institucional UNEV, info de Honduras, vocabulario abierto, metadatos de entrenamiento, logo index |
| `hologram_controller.py` | Ventilador holográfico TCP (estado, playlist, pausa/reanudación, fail-soft) |
| `security.py` | Redacción de secretos en logs/respuestas, saneo de prompts (anti-DoS/inyección) |
| `auth_token.py` | Token de capacidad opt-in para endpoints privilegiados |
| `scripts/` | Setup, diagnóstico, launchers (`Holograma.sh`, `Holograma.cmd`, `run_web.*`) |
| `static/` | Frontend compilado (SPA React) servido por FastAPI |
| `frontend/` | UI React + shell Tauri (fuente, no compilado) |
| `graphify-out/` | Grafo de conocimiento del repo (`graph.json`, `GRAPH_REPORT.md`, `graph.html`) |
| `tests/` | 17 archivos de pytest (contratos de proveedor, LLM unify, servicios, cámara, holograma, seguridad, STT) |

## Proveedores de IA soportados

| Proveedor (`LLM_PROVIDER`) | Tipo | API key | Default URL |
|---------------------------|------|---------|-------------|
| `openrouter` | nube | `OPENROUTER_API_KEY` | fija |
| `openai` | nube | `OPENAI_API_KEY` | configurable |
| `claude_native` | nube | `ANTHROPIC_API_KEY` | fija |
| `nvidia` | nube | `NVIDIA_API_KEY` | configurable |
| `groq` | nube | `GROQ_API_KEY` (compartida con STT cloud) | configurable |
| `custom_openai` | nube/proxy | `OPENAI_COMPAT_API_KEY` | obligatoria |
| `ollama` | local | — | configurable |
| `local_only` | local | — | — |

La elección de proveedor es **autoritativa**: si eliges Ollama, se usa Ollama aunque queden API keys cloud configuradas. Cada turno puede caer al siguiente en la cadena de fallback. Detalles en [`docs/CONFIG.md`](docs/CONFIG.md).

## Instalación

```bash
python -m venv .venv
./.venv/bin/pip install --upgrade pip setuptools wheel
./.venv/bin/pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu  # visión
./.venv/bin/pip install -r requirements.txt
./.venv/bin/python scripts/setup_hologram.py
```

Windows (PowerShell): `py -m venv .venv`, `.\.venv\Scripts\…`.

Copia `.env.example` → `.env`. Modelos YOLO/Piper van en `models/` (ignorados por git). Ollama local recomendado: `ollama pull gemma3:1b`.

## Ejecutar

| Modo | Comando |
|------|---------|
| API + frontend | `./.venv/bin/python main.py` (o `bash scripts/Holograma.sh` / `scripts/Holograma.cmd`) |
| Teclado (CLI) | `./.venv/bin/python call.py` |
| Voz + cámara (CLI) | `./.venv/bin/python call.py --voice --camera` |
| Diagnóstico | `./.venv/bin/python scripts/diagnose_hologram.py --speak "Hola"` |
| Sin cámara/mic | `HOLOGRAM_CAMERA=0 HOLOGRAM_INPUT=keyboard ./.venv/bin/python main.py` |

La API escucha en `HOLOGRAM_PORT` (default `8000`), host `HOLOGRAM_HOST` (default `127.0.0.1`). `--reload` para autorecarga en desarrollo.

## Configuración esencial

Todas las variables en [`.env.example`](.env.example):

| Variable | Uso |
|----------|------|
| `LLM_PROVIDER` / `LLM_MODEL` / `OLLAMA_MODEL` | Proveedor y modelo |
| `LLM_MAX_TOKENS` | Límite de salida (default 450) |
| `LLM_REQUEST_TIMEOUT` | Timeout HTTP cloud (default 90 s) |
| `LLM_LOG_COT` | Razonamiento en terminal (1=activo) |
| `HOLOGRAM_CAMERA` / `YOLO_MODEL` | Visión (`1` + `yoloe-26n-seg.pt`) |
| `YOLO_CONFIDENCE` / `YOLO_CUSTOM_CONFIDENCE` / `YOLO_UNIFORM_CONFIDENCE` | Umbrales de detección |
| `YOLO_IMGSZ` / `YOLO_INTERVAL_SECONDS` | Coste de inferencia local |
| `PRESENCE_ENTER_SECONDS` / `PRESENCE_ABSENCE_SECONDS` | Anti-rebote de presencia |
| `WHISPER_MODEL` / `WHISPER_LANGUAGE` / `WHISPER_BEAM_SIZE` | STT |
| `TTS_BACKEND` / `HOLOGRAM_TTS_STREAM` | TTS (Piper in-process o CLI) |
| `HOLOGRAM_TCP_IP` / `HOLOGRAM_TCP_PORT` | Ventilador físico (vacío = modo software) |
| `HOLOGRAM_CLIP_IDLE/LISTENING/SPEAKING/THINKING` | Índices de playlist en el dispositivo |
| `CORS_ALLOW_ORIGINS` | Orígenes CORS permitidos (vacío = `*`) |
| `HOLOGRAM_API_TOKEN` | Token de capacidad opt-in para endpoints privilegiados |
| `OLLAMA_READY_TTL_SECONDS` | Cache de sondeo Ollama (default 10 s) |

La detección YOLO sigue activa sin personas; el encode MJPEG se espacia si no hay suscriptores. Las API keys se redactan automáticamente en logs y respuestas de error.

## Endpoints de la API

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/` | Frontend SPA |
| `GET` | `/api/config` | Config actual (keys redactadas) |
| `POST` | `/api/config` | Actualizar config (escritura atómica a `.env` + `config.json`) |
| `GET` | `/api/providers` | Metadata de proveedores sin secretos |
| `GET` | `/api/ollama/models` | Modelos instalados en Ollama local |
| `POST` | `/api/llm/test` | Probar conexión sin persistir |
| `GET` | `/api/unev-content` | Contenido institucional |
| `POST` | `/api/unev-content` | Editar contenido (validado) |
| `POST` | `/api/camera` | Encender/apagar cámara |
| `GET` | `/api/video_feed` | MJPEG stream (async) |
| `POST` | `/api/speak` | TTS bajo demanda (cambio de voz incluido) |
| `GET` | `/api/voices` | Voces Piper disponibles |
| `POST` | `/api/train/image` | Entrenar nueva clase visual |
| `GET` | `/api/train/metadata` | Metadatos de entrenamiento |
| `POST` | `/api/train/vocabulary` | Actualizar vocabulario abierto YOLOE |
| `POST` | `/api/hologram/connect` | Conectar ventilador físico |
| `POST` | `/api/hologram/disconnect` | Desconectar ventilador |
| `POST` | `/api/hologram/command` | Comando TCP (play/pause/next/previous/index) |
| `GET` | `/api/hologram/status` | Estado del ventilador |
| `POST` | `/api/hologram/pause_ai` | Pausar IA (mantiene feed de cámara) |
| `POST` | `/api/hologram/resume_ai` | Reanudar IA |
| `WS` | `/ws/chat` | WebSocket de chat + eventos en tiempo real |

## Pruebas

```bash
./.venv/bin/python -m pytest -q           # 17 archivos de prueba
./.venv/bin/ruff check .                   # estilo del backend
./.venv/bin/python scripts/diagnose_hologram.py --speak "Hola"  # diagnóstico completo
```

Contratos clave:
- `tests/test_provider_config.py` — selección de backend, precedencia de modelo
- `tests/test_llm_unify.py` — tokens unificados, CoT, fallback, event loop
- `tests/test_app_services.py` — orquestación de ConversationService
- `tests/test_security.py` — redacción de secretos, saneo de texto
- `tests/test_hologram_controller.py` — conexión TCP, comandos, fail-soft
- `tests/test_llm_backend.py` — limpieza de bloques CoT, detección de inglés, `_require`

Frontend: `cd frontend && npm test` (Vitest + Testing Library).

## Comandos de chat

`ayuda`, `backend`, `modo normal|jueces|expo|admisiones`, `saludar`, `persona` / `se fue` / `grupo` (simulan visión). El modo de activación de voz se cambia desde la WebApp.

## Grafo del código (graphify)

```bash
graphify query "cómo fluye el LLM en web y en voz"
graphify path "ConversationService" "stream_llm_response"
graphify explain "CameraContextProvider"
graphify update .   # tras cambiar código (AST, sin coste de LLM)
```

Abrir `graphify-out/graph.html` o leer `GRAPH_REPORT.md`.

## Licencia

Proyecto educativo UNEV — uso interno y demostrativo.
