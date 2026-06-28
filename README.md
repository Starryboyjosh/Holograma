# Holograma UNEV

Holograma y guía interactivo inteligente para la Universidad Virtual (UNEV) diseñado para funcionar de manera local o en la nube. Integra procesamiento de lenguaje natural (LLM), visión artificial para la detección de presencia, reconocimiento de voz (STT) y síntesis de habla (TTS).

---

## 📋 Resumen del Proyecto

El **Holograma UNEV** es un asistente interactivo multimodal de última generación. Está diseñado para interactuar con los visitantes a través de múltiples canales:
- **Visual**: Detecta la llegada de personas, grupos o vestimenta formal usando la cámara del dispositivo.
- **Auditivo (Voz)**: Escucha preguntas mediante el micrófono, las transcribe en tiempo real y responde usando síntesis de voz natural en español.
- **Digital (WebSockets/API)**: Proporciona una interfaz basada en FastAPI para streaming de texto y eventos de estado del TTS local.

El sistema puede operar de manera 100% local (sin internet) mediante modelos eficientes optimizados para CPU/GPU locales, o conectarse a APIs externas si se prefiere.

---

## 🛠️ Componentes y Arquitectura

El proyecto está estructurado de forma modular, dividiéndose en los siguientes componentes principales:

### 1. Núcleo y Orquestador (`call.py`)
- **Punto de Entrada**: Orquesta las interacciones del holograma unificando las entradas (teclado, micrófono, cámara) con las salidas (consola, voz TTS).
- **Control de Estado**: Administra el hilo de reproducción de audio y bloquea llamadas superpuestas para evitar la interrupción de la voz.
- **Pipeline de Streaming TTS**: Segmentación inteligente por cláusulas y oraciones para iniciar la reproducción de voz antes de que el LLM termine de generar toda la respuesta (baja latencia).

### 2. Backend de Lenguaje (`llm_backend.py`)
Soporta múltiples proveedores de modelos de lenguaje, seleccionables por variables de entorno:
- **Ollama (Local)**: Modelo por defecto `gemma4:e4b` o `qwen3:8b`.
- **OpenRouter & Anthropic (Nube)**: Modelos como Llama 3.3 y Claude 3.5 Sonnet.
- **OpenAI & NVIDIA NIM**: Integración con GPT-4o-mini y API de microservicios de Nvidia.
- **Local Only (Sin LLM)**: Si no hay conexión a internet ni Ollama disponible, utiliza un enrutador local de expresiones regulares para responder a preguntas comunes usando la base de datos de la universidad.
- **Streaming Asíncrono**: Función `stream_llm_response` para transmitir respuestas en tiempo real vía WebSockets.

### 3. API y Servidor Web (`main.py`)
- **FastAPI**: Ofrece una API REST y un servidor de WebSockets en `/ws/chat`.
- **Streaming Asíncrono**: Transmite las respuestas del LLM al cliente en tiempo real (`text_chunk`).
- **Eventos TTS**: Notifica al frontend cuando la respuesta se envía a Piper o al fallback local del sistema operativo.

### 4. Reconocimiento de Voz - STT (`stt/listener.py`)
- **Faster-Whisper**: Motor de transcripción local rápido optimizado para español.
- **Captura con `sounddevice`**: Graba del micrófono de forma nativa sin requerir compilar dependencias complejas.
- **Detección de Silencio**: Mide la amplitud RMS en tiempo real para detener la grabación automáticamente al terminar de hablar.
- **Prompt Contextual**: Incluye vocabulario específico de UNEV para mejorar la transcripción de siglas y términos técnicos.

### 5. Síntesis de Voz - TTS (`call.py` - Sección TTS)
- **Piper TTS**: Sintetizador de voz ultrarrápido y local que utiliza el modelo en español `es_MX-claude-high.onnx`.
- **Segmentación Inteligente**: Divide el texto del LLM por cláusulas y oraciones para iniciar la reproducción de voz antes de que el LLM termine de generar toda la respuesta (baja latencia).
- **Motores Alternativos**: Fallback automático a la voz nativa del sistema operativo (SAPI en Windows, `espeak-ng` o `spd-say` en Linux).
- **Configuración Flexible**: Variable `TTS_BACKEND` para seleccionar `auto`, `piper`, `windows`, `linux`.

### 6. Visión Artificial (`vision/`)
Detección en tiempo real a través de OpenCV y modelos YOLO:
- `vision/camera.py`: Captura y procesamiento cross-platform de la cámara (soporte para DSHOW en Windows, V4L2 en Linux).
- `vision/person_detector.py`: Detector basado en **YOLOe26** (`yoloe26.pt`). Gatilla eventos automáticos cuando alguien se acerca (`person_entered`), cuando se detecta un grupo (`group_detected`), o cuando la persona se retira (`person_left`).
- `vision/face_analyzer.py`: Conteo seguro de rostros visibles usando Haar cascades de OpenCV. **No identifica personas ni infiere edad, género, raza, emoción, salud u otros atributos sensibles**.

### 7. Habilidades Locales y Datos (`skills/` & `data/`)
Lógica personalizada para comportamientos específicos:
- `skills/presence.py`: Gestiona los tiempos de espera (cooldowns) para no saludar repetitivamente a la misma persona.
- `skills/event_mode.py`: Configura los prompts del sistema y saludos según el modo activo (`normal`, `judges`, `expo`, `admissions`).
- `skills/appearance.py`: Genera observaciones cordiales sobre la vestimenta detectada (por ejemplo, detectar si viste formal).
- `skills/university.py` & `data/unev_info.json`: Base de conocimiento local estructurada sobre carreras, admisiones, campus e información institucional de UNEV.
- `skills/honduras.py` & `data/honduras_info.json`: Conocimiento contextual sobre Honduras (pueblos indígenas, historia lingüística, próceres, vulgarismos, símbolos patrios).
- `skills/router.py`: Enrutador local que decide qué skill responder basándose en palabras clave del usuario.

---

## 3 Reglas de Oro (Compatibilidad Linux ↔ Windows)

| Regla | Qué hace | Dónde se aplica |
|-------|---------|-----------------|
| **A. `pathlib`** | Rutas de archivos con `pathlib.Path` en vez de strings | Todo el proyecto |
| **B. `sounddevice`** | Micrófono con `sounddevice` en vez de `pyaudio` | `stt/listener.py` |
| **C. `requirements.txt`** | Todas las dependencias en un solo archivo | `requirements.txt` |

---

## 🚀 Instalación y Configuración Rápida

### 1. Clonar e instalar dependencias:

**Linux/macOS:**
```bash
python -m venv .venv
./.venv/bin/pip install --upgrade pip setuptools wheel
./.venv/bin/pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
./.venv/bin/pip install -r requirements.txt
./.venv/bin/python setup_hologram.py  # Asistente de configuración interactiva
```

**Windows PowerShell:**
```powershell
py -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip setuptools wheel
.\.venv\Scripts\pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python setup_hologram.py  # Asistente de configuración interactiva
```

### 2. Descargar Modelo Ollama (Recomendado para uso local):
```bash
ollama pull gemma3:1b
```

### 3. Ejecutar:
- **Modo Teclado (Consola):**
  ```bash
  python call.py
  ```
- **Modo Completo (Voz + Cámara YOLO):**
  ```bash
  python call.py --voice --camera
  ```
- **Modo Servidor Web API:**
  ```bash
  uvicorn main:app --reload
  ```

---

## ⚙️ Variables de Entorno y Configuración (`config.json` / `.env`)

| Variable | Default | Descripción |
|----------|---------|-------------|
| `LLM_BACKEND` | `auto` | `auto`, `nvidia`, `openai`, `ollama`, `local_only`, `openrouter`, `claude_native` |
| `LLM_PROVIDER` | `openrouter` | Proveedor para streaming WebSocket: `openrouter`, `openai`, `claude_native` |
| `LLM_MODEL` | `meta-llama/llama-3.3-70b-instruct` | Modelo para APIs en la nube |
| `OLLAMA_MODEL` | `gemma3:1b` | Modelo local a ejecutar en Ollama para fallback rápido |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | URL del servidor Ollama |
| `HOLOGRAM_MODE` | `normal` | Modo activo: `normal`, `judges`, `expo`, `admissions` |
| `HOLOGRAM_INPUT` | `keyboard` | Método de entrada: `keyboard` o `voice` |
| `HOLOGRAM_CAMERA` | `0` | Poner en `1` para activar visión artificial |
| `HOLOGRAM_CAMERA_INDEX` | `0` | Índice de la cámara a usar |
| `HOLOGRAM_CAMERA_BACKEND` | `auto` | Backend OpenCV: `dshow`, `msmf`, `v4l2` |
| `HOLOGRAM_TCP_IP` | *(vacío)* | IP del ventilador físico MISSYOU. Vacío = IA en modo solo-software (no toca el dispositivo). `10.10.10.1` por WiFi directo. Ver [`docs/HOLOGRAM.md`](docs/HOLOGRAM.md) |
| `HOLOGRAM_TCP_PORT` | `50200` | Puerto TCP del dispositivo (fijo en el protocolo) |
| `HOLOGRAM_TCP_VERBOSE` | `0` | `1` registra cada comando de 3 bytes enviado al dispositivo |
| `HOLOGRAM_CLIP_IDLE` / `_LISTENING` / `_SPEAKING` / `_THINKING` | `0` / `1` / `2` / `3` | Índice de clip en la playlist por estado de la IA. Es el ORDEN en que cargaste los MP4 en la app HoloMissYou. Sólo redefínelo si no los cargaste en ese orden |
| `YOLO_MODEL` | `yoloe26.pt` | Modelo YOLO (`yoloe26.pt`) |
| `YOLO_CONFIDENCE` | `0.5` | Umbral de confianza para detección |
| `YOLO_INTERVAL_SECONDS` | `1.0` | Segundos entre ciclos de detección |
| `HOLOGRAM_CUSTOM_OBJECT_INTERVAL` | `2.0` | Intervalo propio (s) para la inferencia de objetos personalizados (YOLOE), más cara que la de personas. Entre corridas se reusa el último resultado; `0` = en cada cuadro |
| `HOLOGRAM_FACE_ANALYSIS` | `0` | Poner en `1` para contar rostros visibles de forma segura con OpenCV |
| `PRESENCE_ENTER_SECONDS` | `0.8` | Presencia sostenida (s) antes de saludar a quien entra (anti-rebote de entrada: evita saludar por un falso positivo de un solo cuadro). `0` = saludo inmediato |
| `PRESENCE_ABSENCE_SECONDS` | `5` | Ausencia sostenida (s) antes de declarar que la persona se fue (anti-rebote: evita cortes por un cuadro perdido) |
| `PRESENCE_GREETING_COOLDOWN` | `40` | Segundos mínimos entre saludos de presencia |
| `PRESENCE_GROUP_COOLDOWN` | `180` | Segundos mínimos entre saludos a grupos |
| `WHISPER_MODEL` | `base` | Modelo de STT (`tiny`, `base`, `small`, `medium`) |
| `WHISPER_DEVICE` | `cpu` | Dispositivo: `cpu`, `cuda` |
| `WHISPER_COMPUTE_TYPE` | `int8` | Tipo de cómputo: `int8`, `float16`, `float32` |
| `WHISPER_LANGUAGE` | `es` | Idioma para transcripción |
| `WHISPER_SILENCE_THRESHOLD` | `0.01` | Umbral RMS para detectar silencio |
| `WHISPER_SILENCE_DURATION` | `1.5` | Segundos de silencio antes de parar grabación |
| `WHISPER_MAX_RECORD_SECONDS` | `15.0` | Límite máximo de grabación |
| `WHISPER_NOISE_FACTOR` | `2.5` | Factor sobre el ruido ambiente para el umbral adaptativo (clave en lugares ruidosos) |
| `WHISPER_CALIBRATION_SECONDS` | `0.4` | Segundos de calibración del ruido ambiente al iniciar cada escucha |
| `HOLOGRAM_VOICE_TRIGGER` | `ptt` | Activación: `ptt` (botón del orbe/ENTER), `presentation` (responde solo cuando la cámara ve gente), `auto` (escucha siempre) |
| `WAKEWORD_MODEL` | `hey_jarvis` | (Opcional) Modelo openWakeWord. El módulo `stt/wakeword.py` queda para uso futuro; no está cableado por defecto |
| `WAKEWORD_THRESHOLD` | `0.5` | (Opcional) Score mínimo [0-1] para la palabra clave |
| `TTS_BACKEND` | `auto` | Backend de voz: `auto`, `piper`, `windows`, `linux` |
| `PIPER_MODEL_PATH` | - | Ruta personalizada del modelo `.onnx` para Piper |
| `PIPER_COMMAND` | - | Comando personalizado para ejecutar Piper |
| `PIPER_TIMEOUT_SECONDS` | `120` | Timeout para generación de voz |
| `WINDOWS_TTS_VOICE` | - | Nombre de voz SAPI específica en Windows |

### 🎙️ Activación de la voz

Todo el audio (STT con Whisper y TTS con Piper) se procesa en el **servidor**
(la laptop). La WebApp solo dispara la escucha y muestra el estado, así que
funciona en **cualquier navegador** (Firefox incluido) sin Web Speech API y sin
necesidad de una app de escritorio.

El micrófono se captura con un `sounddevice.InputStream` continuo (sin huecos ni
*stalls*) y un **umbral adaptativo** calibrado con el ruido ambiente. Los modos
se cambian en caliente desde la WebApp (sin reiniciar):

- **Push-to-talk (`ptt`, por defecto)**: escucha SOLO al tocar el orbe en la
  WebApp o pulsar **ENTER** en la terminal. Lo más fiable en lugares ruidosos.
- **Presentación (`presentation`)**: manos libres. El holograma saluda y
  responde de forma continua, pero solo mientras la cámara detecta gente
  delante. Ideal para stands/expos.
- **Auto (`auto`)**: escucha continua siempre, sin depender de la cámara.

> La palabra clave (openWakeWord) se retiró del flujo por defecto; el módulo
> `stt/wakeword.py` queda disponible por si se quiere reactivar más adelante.

---

## 🧪 Pruebas recomendadas en laptop

1. **Diagnóstico general de dependencias y audio:**
   ```bash
   ./.venv/bin/python diagnose_hologram.py
   ```

2. **Prueba de voz TTS en Linux/Windows:**
   ```bash
   ./.venv/bin/python diagnose_hologram.py --speak "Hola, prueba de audio del holograma."
   ```

3. **Prueba de cámara, YOLO y conteo seguro de rostros:**
   ```bash
   ./.venv/bin/python diagnose_hologram.py --camera --yolo --faces
   ```

4. **Modo completo con cámara de laptop:**
   ```bash
   HOLOGRAM_FACE_ANALYSIS=1 ./.venv/bin/python call.py --voice --camera
   ```

5. **Humo HTTP/WS sin tomar cámara ni micrófono** (valida el servidor sin hardware):
   ```bash
   ./.venv/bin/python -m pytest -q          # backend en verde (107 pruebas)
   ./.venv/bin/ruff check .                 # estilo limpio
   # Levanta FastAPI sin agarrar cámara/mic (default del puerto: 8000):
   HOLOGRAM_CAMERA=0 HOLOGRAM_INPUT=keyboard ./.venv/bin/python main.py
   # En otra terminal:
   curl -s localhost:8000/api/providers     # JSON de proveedores (sin secretos)
   # Abre un WS a /ws (ver frontend/src/hooks/useChatSocket.ts), envía un prompt y
   # verifica la secuencia de eventos:
   #   streaming_started → text_chunk* → text_done
   #                     → audio_status:processing → audio_status:completed
   ```
   El extremo a extremo con voz y cámara usa `HOLOGRAM_CAMERA=1` / `HOLOGRAM_INPUT=voice`,
   pero entonces el servidor retiene `/dev/video0` y el micrófono: asegúrate de que no
   haya otra instancia corriendo primero.

El análisis de rostro implementado solo cuenta rostros visibles. No identifica personas ni infiere edad, género, raza, emoción, salud u otros atributos sensibles.

---

## 🍓 Notas para Raspberry Pi 3/5

- Raspberry Pi 5 es la opción práctica para cámara + YOLO nano; Raspberry Pi 3 puede quedarse solo en detección simple o procesamiento muy espaciado.
- En Raspberry Pi usa modelos ligeros: `YOLO_MODEL=yoloe26.pt`, `WHISPER_MODEL=tiny` o `base`, `WHISPER_DEVICE=cpu`, `WHISPER_COMPUTE_TYPE=int8`.
- Instala OpenCV y dependencias de audio desde el sistema cuando sea posible:
  ```bash
  sudo apt install python3-opencv portaudio19-dev alsa-utils pipewire-pulse
  ```
- Para cámara CSI usa libcamera/Picamera2 o expón la cámara como dispositivo compatible con OpenCV. Para USB normalmente `HOLOGRAM_CAMERA_INDEX=0` basta.
- Mantén `YOLO_INTERVAL_SECONDS` entre `1.0` y `2.0` en Raspberry Pi para evitar saturar CPU.

---

## 🗣️ Comandos del Chat / Sistema

Puedes interactuar con el holograma por voz o texto usando comandos del sistema para alterar su comportamiento en tiempo real:
- `saludar`: Fuerza un saludo inicial.
- `modo jueces`, `modo expo`, `modo admisiones`, `modo normal`: Cambia las directrices de personalidad y respuestas del asistente.
- `persona` / `se fue`: Simula eventos de visión artificial (llegada y salida de personas).
- `grupo`: Simula detección de grupo.
- `formal`: Simula detección de vestimenta formal.
- `juez visual`: Simula detección de jueces/evaluadores.
- `backend`: Muestra información del backend de IA seleccionado y su estado actual.
- `ayuda`: Muestra la lista de comandos disponibles.

---

## 📁 Estructura del Proyecto

```
Holograma/
├── call.py                 # Punto de entrada principal (orquestador)
├── main.py                 # Servidor FastAPI + WebSockets
├── llm_backend.py          # Backends LLM (Ollama, OpenRouter, OpenAI, etc.)
├── setup_hologram.py       # Asistente de configuración interactivo (estilo Hermes)
├── diagnose_hologram.py    # Diagnóstico de hardware y dependencias
├── config.json             # Configuración unificada (generada por setup)
├── requirements.txt        # Dependencias Python (Regla C)
├── .env                    # Variables de entorno (no versionado)
├── .gitignore              # Archivos ignorados por git
├── Holograma.cmd           # Launcher para Windows
├── piper_wrapper.sh        # Wrapper para Piper TTS en Linux
├── es_MX-claude-high.onnx  # Modelo de voz Piper (español)
├── es_MX-claude-high.onnx.json
├── yoloe26.pt              # Modelo YOLOe26 nano
├── data/
│   ├── unev_info.json      # Base de conocimiento UNEV
│   └── honduras_info.json  # Contexto Honduras
├── skills/
│   ├── __init__.py
│   ├── appearance.py       # Observaciones visuales cordiales
│   ├── event_mode.py       # Prompts y saludos por modo
│   ├── honduras.py         # Conocimiento Honduras
│   ├── presence.py         # Gestión de presencia/cooldowns
│   ├── router.py           # Enrutador local de skills
│   └── university.py       # Base de conocimiento UNEV
├── stt/
│   ├── __init__.py
│   └── listener.py         # Faster-Whisper + sounddevice
├── vision/
│   ├── __init__.py
│   ├── camera.py           # Wrapper OpenCV cross-platform
│   ├── face_analyzer.py    # Conteo seguro de rostros (Haar)
│   └── person_detector.py  # YOLOe26 detección de personas
└── piper/                  # Binarios Piper TTS (opcional, no versionado)
```

---

## 🔧 Configuración Avanzada

### Asistente Interactivo (`setup_hologram.py`)
Inspirado en `hermes setup`, este asistente te guía paso a paso:
1. **Cerebro (LLM)**: Ollama local (Gemma 4 E4B / Qwen 3:8B) o Cloud API (OpenRouter, OpenAI, Anthropic).
2. **Oído (STT)**: Whisper Small (250 MB VRAM) o Medium (750 MB VRAM).
3. **Visión (YOLO)**: Activa/desactiva cámara, configura frame skipping.
4. **Hardware Guard**: Calcula VRAM proyectada y advierte si supera 4GB (Quadro T1000).

### Archivo `config.json`
Generado automáticamente por `setup_hologram.py`, contiene la configuración unificada que `call.py` carga al inicio.

---

## 📄 Licencia

Proyecto educativo para la Universidad Virtual (UNEV). Uso interno y demostrativo.
