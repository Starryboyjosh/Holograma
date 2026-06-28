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

## Límite de tokens y robustez de la respuesta

- **`LLM_MAX_TOKENS`** (entero, por defecto **450**) — único límite de longitud para
  **todos** los backends. Antes cada ruta tenía su propio número (350 en Ollama,
  450 en la nube, 1024 en streaming de Claude, sin límite en otra) y las respuestas
  se cortaban de forma incoherente. Ahora `_max_tokens()` lo centraliza; un valor
  inválido o ≤0 cae al defecto.
- **No se descartan respuestas válidas.** El filtro anti-inglés ya **no tira** la
  respuesta cuando sospecha que vino en inglés: registra un aviso y la entrega
  igual. Descartarla era la causa del síntoma "no puedo responder en este momento".
- **Selección de backend fuera del event loop.** En la ruta async
  (`stream_llm_response`, la del WebSocket) la elección de backend —que incluye el
  sondeo de Ollama, cacheado con `OLLAMA_READY_TTL_SECONDS`— corre en
  `asyncio.to_thread`, para que el sondeo nunca congele el loop (síntoma de
  "freeze"). La generación ya usa clientes async (`AsyncOpenAI`/`AsyncAnthropic`).

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
  La respuesta redacta las API keys (`***`) y expone banderas `*_API_KEY_SET`;
  también devuelve `OPENAI_COMPAT_BASE_URL` (no es secreto) para que el formulario
  pueda pre-rellenar la URL del endpoint propio. La escritura de `config.json` y
  `.env` es **atómica** (temporal + `os.replace`).

## Interfaz de Ajustes

La pantalla de Ajustes (`frontend/src/screens/SettingsScreen.tsx` →
`components/ProviderConfigCard.tsx`) se construye sobre `GET /api/providers`: un
único selector de proveedor (los 7, agrupados nube/local) con su descripción, el
estado *configurado/sin key*, campo de modelo (texto libre, con sugerencias para
Ollama), campo de URL base solo para `custom_openai`, y un botón **"Probar
conexión"** que llama a `POST /api/llm/test`. La key es de **solo escritura**: el
campo vacío nunca borra la guardada. El mapeo formulario→contrato es puro y
testeable en [`frontend/src/lib/providerForm.ts`](../frontend/src/lib/providerForm.ts).

## Pruebas

`pytest` cubre la selección de backend (incluida la regresión de Ollama), la
precedencia de modelo y los mensajes de "Probar conexión". Se ejecutan sin la
pila de ML (no requieren `torch`/`whisper`):

```bash
.venv/bin/pytest            # 112 pruebas
.venv/bin/ruff check .      # estilo del backend
```

En el frontend, la lógica del formulario y la tarjeta de proveedor tienen pruebas
con Vitest + Testing Library:

```bash
cd frontend && npm test     # Vitest: providerForm + ProviderConfigCard + AssistantScreen
```

## Endurecimiento de seguridad (Fase D.1)

[`security.py`](../security.py) centraliza dos defensas, puras y testeadas:

- **Redacción de secretos** (`redact_secrets`): ninguna API key aparece en logs ni
  en respuestas de error. Se aplica a los `except` de `/api/config`, `/api/speak` y
  los endpoints de entrenamiento, y al error crudo de proveedor en
  `llm_backend._humanize_probe_error`.
- **Saneo / límite de tamaño** (`clamp_text`): el `prompt` del chat (visitante), el
  texto de TTS y las **etiquetas de visión / vocabulario editables** (que terminan
  en el prompt del LLM) se truncan y se les quitan caracteres de control/ancho cero
  —acota el coste/DoS y la superficie de inyección de prompts.

CORS es configurable con `CORS_ALLOW_ORIGINS` (lista separada por comas; vacío =
`*`, válido porque el backend solo escucha en localhost). Pendiente para una fase
con la shell de Tauri: token de capacidad para WS/REST, keyring del SO para los
secretos y límites de tasa.
