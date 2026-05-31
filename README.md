# Holograma UNEV

Demo de holograma/guía interactivo para UNEV con respuestas locales, backend LLM opcional y voz con Piper.

## Requisitos principales

- Python 3
- Piper TTS instalado para voz de mejor calidad
- Linux: `aplay`, `paplay`, `pw-play`, `ffplay` o `mpv` para reproducir audio
- Windows: PowerShell viene incluido; si Piper no está disponible, se usa la voz nativa de Windows
- Ollama opcional para conversación abierta

## Instalación recomendada

Linux/macOS:

`python -m venv .venv`

`./.venv/bin/python -m pip install -r requirements.txt`

`./.venv/bin/python call.py`

Windows PowerShell:

`py -m venv .venv`

`.\.venv\Scripts\python -m pip install -r requirements.txt`

`.\.venv\Scripts\python call.py`

El código también intenta encontrar Piper dentro de `.venv`, `.env` o `venv` aunque no actives el entorno virtual. No hay fallback a voz inglesa; si no existe una voz `es_*.onnx`, el programa pedirá una voz en español.

## Modelo LLM recomendado

El backend local de Ollama está configurado por defecto para usar:

`qwen3:8b`

Descarga el modelo con:

`ollama pull qwen3:8b`

Luego ejecuta:

`LLM_BACKEND=ollama python call.py`

## Voz en español en Linux y Windows

El proyecto intenta hablar así:

1. Usa Piper si está instalado y encuentra una voz `es_*.onnx`.
2. En Windows, si Piper no está disponible, usa la voz nativa de Windows. Si Windows no tiene una voz en español instalada, usará la voz predeterminada.
3. En Linux, si Piper no está disponible, intenta usar `espeak-ng`, `espeak` o `spd-say`.

La voz actual es:

- `es_MX-claude-high.onnx`
- `es_MX-claude-high.onnx.json`

También puedes forzar otra voz con:

`PIPER_MODEL_PATH=mi_voz.onnx python call.py`

También puedes forzar el motor de voz:

- `TTS_BACKEND=piper python call.py`
- `TTS_BACKEND=windows python call.py`
- `TTS_BACKEND=linux python call.py`

En Windows puedes indicar una voz específica instalada con:

`WINDOWS_TTS_VOICE="Microsoft Sabina Desktop" python call.py`

## Modo sin Ollama

Si no tienes Ollama, el holograma igual puede responder preguntas básicas de UNEV usando skills locales, por ejemplo:

- ¿Qué es UNEV?
- Carreras o programas
- Admisiones
- Ubicación
- Página oficial
- Aprobación oficial

Para forzar ese modo:

`LLM_BACKEND=local_only python call.py`

## Uso

Ejecuta:

`python call.py`

Comandos útiles dentro del chat:

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
