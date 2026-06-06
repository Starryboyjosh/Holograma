# Holograma UNEV

Holograma y guía interactivo inteligente para la Universidad Virtual (UNEV) diseñado para funcionar de manera local o en la nube. Integra procesamiento de lenguaje natural (LLM), visión artificial para la detección de presencia, reconocimiento de voz (STT) y síntesis de habla (TTS).

---

## 📋 Resumen del Proyecto

El **Holograma UNEV** es un asistente interactivo multimodal de última generación. Está diseñado para interactuar con los visitantes a través de múltiples canales:
- **Visual**: Detecta la llegada de personas, grupos o vestimenta formal usando la cámara del dispositivo.
- **Auditivo (Voz)**: Escucha preguntas mediante el micrófono, las transcribe en tiempo real y responde usando síntesis de voz natural en español.
- **Digital (WebSockets/API)**: Proporciona una interfaz basada en FastAPI para streaming de texto y simulación de flujos de audio avanzados (XTTS).

El sistema puede operar de manera 100% local (sin internet) mediante modelos eficientes optimizados para CPU/GPU locales, o conectarse a APIs externas si se prefiere.

---

## 🛠️ Componentes y Arquitectura

El proyecto está estructurado de forma modular, dividiéndose en los siguientes componentes principales:

### 1. Núcleo y Orquestador (`call.py`)
- **Punto de Entrada**: Orquesta las interacciones del holograma unificando las entradas (teclado, micrófono, cámara) con las salidas (consola, voz TTS).
- **Control de Estado**: Administra el hilo de reproducción de audio y bloquea llamadas superpuestas para evitar la interrupción de la voz.

### 2. Backend de Lenguaje (`llm_backend.py`)
Soporta múltiples proveedores de modelos de lenguaje, seleccionables por variables de entorno:
- **Ollama (Local)**: Modelo por defecto `gemma4:e4b` o `qwen3:8b`.
- **OpenRouter & Anthropic (Nube)**: Modelos como Llama 3.3 y Claude 3.5 Sonnet.
- **OpenAI & NVIDIA NIM**: Integración con GPT-4o-mini y API de microservicios de Nvidia.
- **Local Only (Sin LLM)**: Si no hay conexión a internet ni Ollama disponible, utiliza un enrutador local de expresiones regulares para responder a preguntas comunes usando la base de datos de la universidad.

### 3. API y Servidor Web (`main.py`)
- **FastAPI**: Ofrece una API REST y un servidor de WebSockets en `/ws/chat`.
- **Streaming Asíncrono**: Transmite las respuestas del LLM al cliente en tiempo real (`text_chunk`).
- **Simulación XTTS**: Integra un pipeline simulado para generación rápida de voz en formato web.

### 4. Reconocimiento de Voz - STT (`stt/listener.py`)
- **Faster-Whisper**: Motor de transcripción local rápido optimizado para español.
- **Captura con `sounddevice`**: Graba del micrófono de forma nativa sin requerir compilar dependencias complejas.
- **Detección de Silencio**: Mide la amplitud RMS en tiempo real para detener la grabación automáticamente al terminar de hablar.

### 5. Síntesis de Voz - TTS (`call.py` - Sección TTS)
- **Piper TTS**: Sintetizador de voz ultrarrápido y local que utiliza el modelo en español `es_MX-claude-high.onnx`.
- **Segmentación Inteligente**: Divide el texto del LLM por cláusulas y oraciones para iniciar la reproducción de voz antes de que el LLM termine de generar toda la respuesta (baja latencia).
- **Motores Alternativos**: Fallback automático a la voz nativa del sistema operativo (SAPI en Windows, `espeak-ng` o `spd-say` en Linux).

### 6. Visión Artificial (`vision/`)
Detección en tiempo real a través de OpenCV y modelos YOLO:
- `vision/camera.py`: Captura y procesamiento cross-platform de la cámara.
- `vision/person_detector.py`: Detector basado en **YOLOv8** / **YOLOv11** (`yolov8n.pt` o `yolo11n.pt`). Gatilla eventos automáticos cuando alguien se acerca (`person_entered`), cuando se detecta un grupo (`group_detected`), o cuando la persona se retira (`person_left`).

### 7. Habilidades Locales y Datos (`skills/` & `data/`)
Lógica personalizada para comportamientos específicos:
- `skills/presence.py`: Gestiona los tiempos de espera (cooldowns) para no saludar repetitivamente a la misma persona.
- `skills/event_mode.py`: Configura los prompts del sistema y saludos según el modo activo (`normal`, `judges`, `expo`, `admissions`).
- `skills/appearance.py`: Genera observaciones cordiales sobre la vestimenta detected (por ejemplo, detectar si viste formal).
- `skills/university.py` & `data/unev_info.json`: Base de conocimiento local estructurada sobre carreras, admisiones, campus e información institucional de UNEV.

---

## 3 Reglas de Oro (Compatibilidad Linux ↔ Windows)

| Regla | Qué hace | Dónde se aplica |
|-------|---------|-----------------|
| **A. `pathlib`** | Rutas de archivos con `pathlib.Path` en vez de strings | Todo el proyecto |
| **B. `sounddevice`** | Micrófono con `sounddevice` en vez de `pyaudio` | `stt/listener.py` |
| **C. `requirements.txt`** | Todas las dependencias en un solo archivo | `requirements.txt` |

---

## 🚀 Instalación y Configuración Rápida

1. **Clonar e instalar dependencias:**

   Linux/macOS:
   ```bash
   python -m venv .venv
   ./.venv/bin/pip install --upgrade pip setuptools wheel
   ./.venv/bin/pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
   ./.venv/bin/pip install -r requirements.txt
   ./.venv/bin/python setup_hologram.py  # Asistente de configuración interactiva
   ```

   Windows PowerShell:
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\python -m pip install --upgrade pip setuptools wheel
   .\.venv\Scripts\pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
   .\.venv\Scripts\pip install -r requirements.txt
   .\.venv\Scripts\python setup_hologram.py  # Asistente de configuración interactiva
   ```

2. **Descargar Modelo Ollama (Recomendado para uso local):**
   ```bash
   ollama pull gemma4:e4b
   ```

3. **Ejecutar:**
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
| `LLM_BACKEND` | `auto` | `auto`, `nvidia`, `openai`, `ollama`, `local_only` |
| `OLLAMA_MODEL` | `gemma4:e4b` | Modelo local a ejecutar en Ollama |
| `HOLOGRAM_MODE` | `normal` | Modo activo: `normal`, `judges` (jueces), `expo`, `admissions` |
| `HOLOGRAM_INPUT` | `keyboard` | Método de entrada: `keyboard` o `voice` |
| `HOLOGRAM_CAMERA` | `0` | Poner en `1` para activar visión artificial |
| `YOLO_MODEL` | `yolov8n.pt` | Modelo YOLO (`yolov8n.pt` o `yolo11n.pt`) |
| `HOLOGRAM_FACE_ANALYSIS` | `0` | Poner en `1` para contar rostros visibles de forma segura con OpenCV |
| `WHISPER_MODEL` | `base` | Modelo de STT (`tiny`, `base`, `small`, `medium`) |
| `TTS_BACKEND` | `auto` | Backend de voz: `auto`, `piper`, `windows`, `linux` |
| `PIPER_MODEL_PATH` | - | Ruta personalizada del modelo `.onnx` para Piper |

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

El análisis de rostro implementado solo cuenta rostros visibles. No identifica personas ni infiere edad, género, raza, emoción, salud u otros atributos sensibles.

---

## 🍓 Notas para Raspberry Pi 3/5

- Raspberry Pi 5 es la opción práctica para cámara + YOLO nano; Raspberry Pi 3 puede quedarse solo en detección simple o procesamiento muy espaciado.
- En Raspberry Pi usa modelos ligeros: `YOLO_MODEL=yolo11n.pt`, `WHISPER_MODEL=tiny` o `base`, `WHISPER_DEVICE=cpu`, `WHISPER_COMPUTE_TYPE=int8`.
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
- `backend`: Muestra información del backend de IA seleccionado y su estado actual.
- `ayuda`: Muestra la lista de comandos disponibles.
