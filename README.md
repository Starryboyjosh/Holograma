# Holograma UNEV

Demo de holograma/guía interactivo para UNEV con IA avanzada: Gemma 4 E4B, YOLOv8/v11, Faster-Whisper y Piper TTS.

## 3 Reglas de Oro (Compatibilidad Linux ↔ Windows)

| Regla | Qué hace | Dónde se aplica |
|-------|---------|-----------------|
| **A. `pathlib`** | Rutas de archivos con `pathlib.Path` en vez de strings | Todo el proyecto |
| **B. `sounddevice`** | Micrófono con `sounddevice` en vez de `pyaudio` | `stt/listener.py` |
| **C. `requirements.txt`** | Todas las dependencias en un solo archivo | `requirements.txt` |

## Requisitos principales

- Python 3.10+
- Ollama con Gemma 4 E4B para conversación inteligente
- Piper TTS para voz de alta calidad en español
- Linux: `aplay`, `paplay`, `pw-play`, `ffplay` o `mpv` para reproducir audio
- Windows: PowerShell incluido; si Piper no está, se usa la voz nativa de Windows

## Instalación y Configuración rápida (Regla C)

Linux/macOS:

```bash
python -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/python setup_hologram.py  # Asistente interactivo de sentidos y VRAM
./.venv/bin/python call.py
```

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python setup_hologram.py  # Asistente interactivo de sentidos y VRAM
.\.venv\Scripts\python call.py
```

## Modelo LLM: Gemma 4 E4B

El backend local de Ollama está configurado por defecto para usar:

```
gemma4:e4b
```

Descarga el modelo con:

```bash
ollama pull gemma4:e4b
```

Luego ejecuta:

```bash
LLM_BACKEND=ollama python call.py
```

También puedes usar otros modelos cambiando la variable de entorno:

```bash
OLLAMA_MODEL=qwen3:8b python call.py
```

## Modos de ejecución

### Modo teclado (default)

```bash
python call.py
```

### Modo voz (micrófono → Whisper → LLM → TTS)

```bash
python call.py --voice
```

O con variable de entorno:

```bash
HOLOGRAM_INPUT=voice python call.py
```

### Modo cámara (detección de personas con YOLO)

```bash
python call.py --camera
```

O con variable de entorno:

```bash
HOLOGRAM_CAMERA=1 python call.py
```

### Modo completo (voz + cámara)

```bash
python call.py --voice --camera
```

## Detección de personas (YOLOv8/v11 + OpenCV)

El holograma puede detectar personas con la cámara usando YOLOv8 o YOLOv11:

- Detecta cuando alguien llega y saluda automáticamente
- Detecta grupos y ajusta el saludo
- Detecta cuando la persona se fue y vuelve a modo espera

Configura el modelo YOLO:

```bash
YOLO_MODEL=yolo11n.pt python call.py --camera    # YOLOv11
YOLO_MODEL=yolov8n.pt python call.py --camera     # YOLOv8 (default)
```

## Speech-to-Text (Faster-Whisper + sounddevice)

El modo voz usa Faster-Whisper para transcribir tu voz en español:

- Graba desde el micrófono con `sounddevice` (Regla B: funciona en Linux y Windows sin compilar PortAudio)
- Detecta silencio automáticamente para saber cuándo terminaste de hablar
- Transcribe con el modelo Whisper `base` por defecto

Configura el modelo Whisper:

```bash
WHISPER_MODEL=small python call.py --voice    # Más preciso (~500MB)
WHISPER_MODEL=base python call.py --voice     # Más rápido (~150MB, default)
```

## Voz en español (Piper TTS)

El proyecto intenta hablar así:

1. Usa Piper si está instalado y encuentra una voz `es_*.onnx`.
2. En Windows, si Piper no está disponible, usa la voz nativa de Windows.
3. En Linux, si Piper no está, intenta usar `espeak-ng`, `espeak` o `spd-say`.

La voz actual es:

- `es_MX-claude-high.onnx`
- `es_MX-claude-high.onnx.json`

Forzar otra voz: `PIPER_MODEL_PATH=mi_voz.onnx python call.py`

Forzar el motor de voz:

- `TTS_BACKEND=piper python call.py`
- `TTS_BACKEND=windows python call.py`
- `TTS_BACKEND=linux python call.py`

## Variables de entorno

| Variable | Default | Descripción |
|----------|---------|-------------|
| `LLM_BACKEND` | `auto` | `auto`, `nvidia`, `openai`, `ollama`, `local_only` |
| `OLLAMA_MODEL` | `gemma4:e4b` | Modelo de Ollama |
| `HOLOGRAM_MODE` | `normal` | `normal`, `judges`, `expo`, `admissions` |
| `HOLOGRAM_INPUT` | `keyboard` | `keyboard` o `voice` |
| `HOLOGRAM_CAMERA` | `0` | `1` para activar detección de personas |
| `HOLOGRAM_CAMERA_INDEX` | `0` | Índice de cámara |
| `YOLO_MODEL` | `yolov8n.pt` | Modelo YOLO (v8 o v11) |
| `YOLO_CONFIDENCE` | `0.5` | Confianza mínima de detección |
| `WHISPER_MODEL` | `base` | Modelo Whisper (`tiny`, `base`, `small`, `medium`) |
| `WHISPER_LANGUAGE` | `es` | Idioma de transcripción |
| `WHISPER_DEVICE` | `auto` | `auto`, `cpu`, `cuda` |
| `TTS_BACKEND` | `auto` | `auto`, `piper`, `windows`, `linux` |
| `PIPER_MODEL_PATH` | - | Ruta al modelo de voz Piper |

## Modo sin Ollama

Si no tienes Ollama, el holograma responde preguntas básicas de UNEV usando skills locales:

- ¿Qué es UNEV?
- Carreras o programas
- Admisiones
- Ubicación
- Página oficial
- Aprobación oficial

Para forzar ese modo: `LLM_BACKEND=local_only python call.py`

## Comandos dentro del chat

- `ayuda`
- `backend`
- `saludar`
- `persona`
- `grupo`
- `formal`
- `modo jueces`
- `modo expo`
- `modo admisiones`
- `modo normal`
- `salir`

## Arquitectura

```
Holograma/
├── call.py                  # Entry point (teclado + voz + cámara)
├── llm_backend.py           # Ollama (Gemma 4 E4B), NVIDIA, OpenAI
├── setup_hologram.py        # Configuración interactiva y estimación de VRAM
├── requirements.txt         # Todas las dependencias (Regla C)
├── stt/                     # Speech-to-Text
│   ├── __init__.py
│   └── listener.py          # sounddevice + faster-whisper (Regla B)
├── vision/
│   ├── __init__.py
│   ├── camera.py            # Wrapper OpenCV cross-platform
│   └── person_detector.py   # YOLOv8/v11 detección de personas
├── skills/
│   ├── appearance.py
│   ├── event_mode.py
│   ├── presence.py
│   ├── router.py
│   └── university.py
└── data/
    └── unev_info.json
```
