# Holograma UNEV

Asistente multimodal para la Universidad Virtual (UNEV): LLM, visión (presencia), voz (STT/TTS) y API WebSocket. Puede correr **local** (Ollama, Whisper, Piper, YOLO) o con APIs en la nube.

## Qué hay en el repo

| Ruta | Rol |
|------|-----|
| `call.py` | CLI: teclado / voz / cámara |
| `main.py` | FastAPI + WebSocket + lifespan |
| `app/` | Servicios (conversación, LLM, cámara, conexiones WS) |
| `llm_backend.py` / `provider_config.py` | Proveedores LLM y streaming |
| `vision/` | Cámara OpenCV + YOLO local (`yolo26n` / YOLOE-26) |
| `stt/` | Faster-Whisper + sounddevice |
| `skills/` + `data/` | Router local, UNEV, Honduras |
| `hologram_controller.py` | Ventilador holográfico TCP (opcional) |
| `frontend/` | UI React + shell Tauri |
| `scripts/` | Setup, diagnóstico, launchers |
| `security.py` / `auth_token.py` | Saneo, redacción de secretos, token API opt-in |

Config de referencia (no secretos): [`.env.example`](.env.example), [`config.example.json`](config.example.json).  
Detalle de proveedores: [`docs/CONFIG.md`](docs/CONFIG.md). Holograma físico: [`docs/HOLOGRAM.md`](docs/HOLOGRAM.md).

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
| `LLM_PROVIDER` / `OLLAMA_MODEL` | Cerebro (nube o local) |
| `HOLOGRAM_CAMERA` / `YOLO_MODEL` | Visión (`1` + `models/yolo26n.pt`) |
| `YOLO_IMGSZ` / `YOLO_INTERVAL_SECONDS` | Coste de detección local |
| `WHISPER_MODEL` / `WHISPER_BEAM_SIZE` | STT |
| `TTS_BACKEND` / `HOLOGRAM_TTS_STREAM` | Piper u OS; TTS por cláusulas en web |
| `HOLOGRAM_TCP_IP` | Vacío = sin ventilador físico |

La detección YOLO **sigue activa** aunque no haya personas; solo se espacia el coste y el encode MJPEG si nadie mira el feed.

Contenido institucional editable: `data/unev_info.json` (UI “Contenido” / API). Fuente de código: `skills/unev_content.py`.

## Pruebas

```bash
./.venv/bin/python -m pytest -q
./.venv/bin/python scripts/diagnose_hologram.py --speak "Hola"
# API sin cámara/mic:
HOLOGRAM_CAMERA=0 HOLOGRAM_INPUT=keyboard ./.venv/bin/python main.py
```

## Comandos de chat

`ayuda`, `backend`, `modo normal|jueces|expo|admisiones`, `saludar`, `persona` / `se fue` / `grupo` (simulan visión).

## Licencia

Proyecto educativo UNEV — uso interno y demostrativo.
