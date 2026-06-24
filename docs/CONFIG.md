# Configuración de IA — Contrato de proveedor y modelo

Este documento describe **cómo elige el holograma su proveedor de IA y su
modelo**. Toda la lógica vive en un solo lugar: [`provider_config.py`](../provider_config.py).
La interfaz de Ajustes y `llm_backend.py` la consumen; no hay reglas duplicadas.

## Proveedores soportados

| Proveedor (`LLM_PROVIDER`) | Tipo  | API key            | Modelo                                   | URL base |
|----------------------------|-------|--------------------|------------------------------------------|----------|
| `openrouter`               | nube  | `OPENROUTER_API_KEY` | `LLM_MODEL`                            | fija     |
| `openai`                   | nube  | `OPENAI_API_KEY`     | `OPENAI_MODEL` → `LLM_MODEL`           | `OPENAI_BASE_URL` |
| `claude_native` (Anthropic)| nube  | `ANTHROPIC_API_KEY`  | `ANTHROPIC_MODEL` → `LLM_MODEL`        | fija     |
| `nvidia`                   | nube  | `NVIDIA_API_KEY`     | `NVIDIA_MODEL` → `LLM_MODEL`           | `NVIDIA_BASE_URL` |
| `custom_openai`            | nube  | `OPENAI_COMPAT_API_KEY` | `OPENAI_COMPAT_MODEL` → `LLM_MODEL` | `OPENAI_COMPAT_BASE_URL` (obligatoria) |
| `ollama`                   | local | — (ninguna)        | `OLLAMA_MODEL` (nunca hereda `LLM_MODEL`) | `OLLAMA_BASE_URL` |
| `local_only`               | local | — (ninguna)        | — (solo skills)                          | —        |

"`X → LLM_MODEL`" significa: se usa el override específico del proveedor si está
definido; si no, el modelo genérico `LLM_MODEL` que escribe la interfaz; si no,
el modelo por defecto del proveedor.

## Cómo se elige el backend (`select_backend`)

En orden:

1. `LLM_BACKEND` distinto de `auto` → override explícito **(obsoleto, usa
   `LLM_PROVIDER`)**.
2. `LLM_PROVIDER` con un valor válido → **autoritativo**. Si el operador elige
   `ollama`, se usa Ollama aunque queden API keys viejas; nunca se cambia en
   silencio a la nube. Si la key del proveedor elegido falta, el error lo dice
   con claridad en vez de saltar a otro proveedor.
3. Sin elección explícita → autodetección por la primera API key presente
   (orden: OpenRouter, NVIDIA, OpenAI, Anthropic).
4. Sin keys → `ollama` si el servicio responde; si no, `local_only`.

> Corrige el bug anterior: elegir "Local (Ollama)" seguía usando la nube cuando
> quedaba una `OPENROUTER_API_KEY` vieja, porque la selección no tenía caso para
> `ollama` y caía a "cualquier key presente".

Aliases aceptados en `LLM_PROVIDER`: `local`→`ollama`, `anthropic`/`claude`→`claude_native`.

## Endpoints relacionados

- `GET /api/providers` — metadata segura para la interfaz: etiqueta amistosa,
  descripción, si requiere URL base, si admite descubrimiento de modelos y el
  estado **configurado/no configurado** de cada API key. **Nunca** devuelve
  secretos.
- `POST /api/llm/test` `{provider, model?, api_key?, base_url?}` — prueba real de
  conexión **sin guardar nada**. Devuelve un mensaje accionable: "API key
  inválida", "el modelo no existe", "no se pudo conectar", etc. La key enviada
  se usa solo para la prueba; no se persiste ni se devuelve.
- `GET /api/config` / `POST /api/config` — lectura/escritura de la configuración.
  La respuesta redacta las API keys (`***`) y expone banderas `*_API_KEY_SET`.
  La escritura de `config.json` y `.env` es **atómica** (temporal + `os.replace`).

## Pruebas

`pytest` cubre la selección de backend (incluida la regresión de Ollama), la
precedencia de modelo y los mensajes de "Probar conexión". Se ejecutan sin la
pila de ML (no requieren `torch`/`whisper`):

```bash
.venv/bin/pytest            # 29 pruebas
.venv/bin/ruff check .      # estilo del backend
```
