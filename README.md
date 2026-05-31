# Holograma UNEV

Demo de holograma/guía interactivo para UNEV con respuestas locales, backend LLM opcional y voz con Piper.

## Requisitos principales

- Python 3
- Piper TTS instalado y disponible como `piper`
- `aplay` para reproducir audio en Linux
- Ollama opcional para conversación abierta

## Modelo LLM recomendado

El backend local de Ollama está configurado por defecto para usar:

`qwen3:8b`

Descarga el modelo con:

`ollama pull qwen3:8b`

Luego ejecuta:

`LLM_BACKEND=ollama python call.py`

## Voz en español

El proyecto prefiere automáticamente una voz de Piper en español si existe un archivo `es_*.onnx` en la carpeta.

La voz actual es:

- `es_MX-claude-high.onnx`
- `es_MX-claude-high.onnx.json`

También puedes forzar otra voz con:

`PIPER_MODEL_PATH=mi_voz.onnx python call.py`

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
