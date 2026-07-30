# WAVE-01 — Desbloquear el turno

| | |
|---|---|
| **Fase** | 1 · Desbloquear la demo |
| **Riesgo** | Bajo — tres cambios locales, ninguno toca arquitectura |
| **Esfuerzo** | ~1 sesión |
| **Modelo sugerido** | `scout` (brief) → Opus (código) → `worker` (tests) |
| **Cierra hallazgos** | B, C, E |

> Antes de empezar: leé `README.md` y `PROGRESS.md`. Re-localizá los símbolos con
> `graphify query`. **Las líneas de este documento son orientativas; los símbolos son la
> verdad.**

---

## Por qué (hallazgo)

Tres defectos independientes que, juntos, producen el síntoma que rompe la demo: **el
holograma se queda callado, o tarda tres minutos en hablar.**

### B · La ruta web se come el turno cuando el stream sale vacío

`llm_backend.stream_llm_response` (≈L1063) sale del bucle de backends con un `return`
**incondicional**. `produced` se calcula pero sólo se consulta dentro del `except`:

```python
        produced = False
        try:
            if _cot_log_enabled():
                print(f"[LLM/CoT] intento stream backend={backend}", flush=True)
            async for chunk in _stream_backend_response(backend, messages):
                produced = True
                yield chunk
            return                       # ← incondicional: sale aunque produced sea False
        except Exception as error:
            print(f"[LLM] Error usando backend '{backend}', probando fallback: {error}")
            if produced:                 # ← el único sitio donde se consulta
                return
```

Si el backend responde **200 con cero tokens** —lo normal cuando un modelo de razonamiento
consume los 180 `max_tokens` dentro de `<think>` y no llega a escribir respuesta— no hay
excepción, así que el `return` de la línea del éxito dispara y el turno termina sin una sola
palabra. El fallback nunca se intenta. El frontend recibe `streaming_started` → `text_done` sin
`text_chunk` en medio.

La ruta síncrona **ya lo hace bien** en `iter_reply_tokens` (≈L898). Este es el patrón a
replicar, no uno nuevo a inventar:

```python
                produced = False
                for token in _iter_openai_compatible_tokens(backend, messages):
                    produced = True
                    yield token
                if produced:
                    return
                # …
                continue   # Stream vacío: probar siguiente backend.
```

### C · Sangrado de modelo entre proveedores → 404 garantizado en el fallback

`provider_config.resolve_model` (≈L230) cae al genérico `LLM_MODEL` cuando el proveedor no
tiene su variable específica poblada:

```python
    if p.model_env:
        specific = (env.get(p.model_env) or "").strip()
        if specific:
            return specific

    if p.generic_model_fallback:
        generic = (env.get("LLM_MODEL") or "").strip()
        if generic:
            return generic

    return p.default_model
```

`LLM_MODEL` vale hoy `nvidia/nemotron-3-nano-30b-a3b:free`, que es un id **namespaced de
OpenRouter**. Groq no conoce ese id. Resultado, verificado en runtime:

```
openrouter      key=SET  model='nvidia/nemotron-3-nano-30b-a3b:free'
groq            key=SET  model='nvidia/nemotron-3-nano-30b-a3b:free'   ← 404 garantizado
cadena cloud configurada: ['openrouter', 'groq']
primario: openrouter | timeout: 90.0 s | max_tokens: 180 | LLM_LOG_COT: False
```

El segundo eslabón de la cadena de fallback está envenenado por construcción: no es un
proveedor de respaldo, es 90 s más de espera antes del mismo fracaso. Con `_request_timeout` en
90.0 (≈L62), el peor caso es **~180 s antes de la primera palabra**. Y las dos advertencias que
nombrarían la causa están silenciadas: `_cot_log_enabled` (≈L524) trae default `"1"` en el
código, pero el `.env` del equipo lo apaga con `LLM_LOG_COT=0` — medido en runtime,
`LLM_LOG_COT: False`. El operador ve un holograma mudo y ningún diagnóstico.

### E · `max_tokens=180` no alcanza para un modelo de razonamiento

`_max_tokens` (≈L44) devuelve 180. El modelo configurado emite cadena de pensamiento **dentro
del mismo presupuesto** que la respuesta. 180 tokens se gastan razonando y la respuesta al
visitante llega truncada o no llega. Es la causa raíz del stream vacío que el defecto B luego
convierte en silencio.

---

## Precondiciones

```bash
git status --short                      # limpio
.venv/bin/python -m pytest tests/ -q    # 203 pasando
```
Es la primera WAVE: no depende de ninguna otra.

---

## Alcance

Anclado en símbolos. Confirmá cada uno con `graphify query` antes de editar.

### 1. `llm_backend.stream_llm_response` — gatear el `return` sobre `produced`

Replicar la semántica de `iter_reply_tokens`: si el backend no produjo ningún chunk, **no**
retornar; seguir con el siguiente candidato.

- El `return` del camino de éxito pasa a ser condicional a `produced`.
- Si `produced` es falso, `continue` al siguiente backend.
- Si se agota la lista, el `yield _local_only_reply(prompt)` final (≈L1111) ya cubre el caso.
- Cuando el stream sale vacío, registrar una advertencia con el nombre del backend —
  **independiente de `_cot_log_enabled()`**. Un stream vacío es una anomalía operativa, no
  ruido de depuración.

### 2. `provider_config.resolve_model` — cortar el sangrado

Objetivo: `LLM_MODEL` sólo debe aplicar al proveedor al que pertenece, nunca a otro.

Opción recomendada (mínima y verificable): que el genérico se consuma **sólo** cuando el
proveedor es el seleccionado como primario. Para el resto de la cadena, `default_model` del
proveedor. Alternativa aceptable: exigir que el id genérico sea compatible con el proveedor (p.
ej. rechazar ids con `/` en proveedores que no usan namespace). Elegí una, documentala en el
docstring, y dejá constancia en `PROGRESS.md` de cuál y por qué.

**No** reescribas `select_backend` (≈L192), `resolve_api_key` (≈L257) ni
`configured_cloud_providers` (≈L277). Sólo `resolve_model`.

### 3. Presupuesto de tokens y visibilidad

- `LLM_MAX_TOKENS`: subir a **800** (propuesta; decisión D1 de `PROGRESS.md`, definitiva en
  WAVE-09). `_max_tokens` ya lee la variable: no hardcodees el número nuevo en el código.
- `LLM_LOG_COT=1` mientras se diagnostica, en `.env`.
- `.env` **no** entra en el commit (está gitignored, y así debe seguir). Si `main.py` documenta
  variables de entorno, actualizá esa documentación ahí.

### Archivos
`llm_backend.py`, `provider_config.py`, `main.py` (sólo si documenta las variables), `.env`
(local, no commiteado), más los tests nuevos.

---

## Fuera de alcance

Explícito. Si tocás algo de esta lista, la Puerta 1 falla.

- El filtro de razonamiento en el texto (`<think>`) → **WAVE-02**. Acá sólo se amplía el
  presupuesto de tokens; nada de limpiar tags.
- Métricas e instrumentación → **WAVE-03**.
- `_build_messages`, `get_university_context`, tamaño del contexto → **WAVE-04/05**.
- El `get_system_prompt("normal")` hardcodeado en `stream_llm_response` (≈L1076) → **WAVE-07**.
  Es un defecto real, está anotado, y **no** se toca acá.
- Elegir otro modelo o proveedor → **WAVE-09** (decisión D2).
- Memoria conversacional → **WAVE-06**.
- `temperature` (0.6 hardcodeado en varios sitios) → **WAVE-09**.

---

## Tests a añadir

Archivo: `tests/test_llm_fallback.py` (nuevo, salvo que ya exista uno con este propósito —
confirmalo antes con `ls tests/`).

| Caso | Qué prueba | Debe fallar sin el fix porque… |
|---|---|---|
| `test_stream_vacio_cae_al_siguiente_backend` | Backend A cede cero chunks, backend B cede texto. `stream_llm_response` debe emitir el texto de B. | Hoy el `return` incondicional termina el turno tras A: el resultado es vacío. |
| `test_stream_vacio_en_todos_los_backends_devuelve_respuesta_local` | Todos los backends ceden cero chunks. Debe llegar `_local_only_reply`. | Hoy retorna sin ceder nada. |
| `test_texto_parcial_no_reintenta_otro_backend` | A cede un chunk y luego lanza. **No** debe reintentar con B (mezclaría dos respuestas). | Blinda el comportamiento correcto ya existente contra una regresión del fix. |
| `test_stream_vacio_registra_advertencia` | Un stream vacío emite advertencia con el nombre del backend, incluso con `LLM_LOG_COT=0`. | Hoy el silencio es total. |
| `test_resolve_model_no_filtra_generico_a_otro_proveedor` | Con `LLM_MODEL` = id de OpenRouter y proveedor `groq`, `resolve_model('groq')` **no** devuelve ese id. | Hoy lo devuelve: es el 404. |
| `test_resolve_model_respeta_variable_especifica` | `GROQ_MODEL` poblado gana sobre el genérico. | Blinda la precedencia contra una regresión del fix. |

Guía: mockeá `_stream_backend_response` y el entorno; **cero llamadas de red, cero llamadas a
API de pago**. Para el entorno, seguí el patrón que ya usan los tests existentes de
`provider_config` (buscalos antes de inventar uno).

---

## Verificación

```bash
# Suite completa
.venv/bin/python -m pytest tests/ -q

# Sólo los nuevos
.venv/bin/python -m pytest tests/test_llm_fallback.py -v

# Los nuevos deben FALLAR sin el fix
git stash
.venv/bin/python -m pytest tests/test_llm_fallback.py -q     # → FALLA
git stash pop
.venv/bin/python -m pytest tests/test_llm_fallback.py -q     # → PASA

# Lint
.venv/bin/ruff check .

# Cadena de proveedores real, sin imprimir secretos
.venv/bin/python -c "
from provider_config import configured_cloud_providers, resolve_model, resolve_api_key
import os
for p in configured_cloud_providers():
    print(f'{p:15} key={\"SET\" if resolve_api_key(p) else \"MISSING\"}  model={resolve_model(p)!r}')
"
```
La última salida es la evidencia del hallazgo C. Pegala en el reporte: los dos proveedores ya
**no** deben mostrar el mismo id.

---

## Criterios de aceptación

Binarios. Sin la salida pegada, no cuentan.

1. Un backend que cede cero chunks **no** termina el turno: la ruta web continúa al siguiente
   candidato. (Test 1 verde.)
2. Agotada la cadena, el visitante recibe `_local_only_reply`, nunca silencio. (Test 2 verde.)
3. `resolve_model('groq')` ya **no** devuelve un id namespaced de OpenRouter, con `LLM_MODEL`
   apuntando a OpenRouter. (Salida del comando pegada.)
4. Peor caso de la cadena de fallback **< 20 s**, no ~180 s. Se cumple porque el eslabón
   envenenado desaparece de la cadena. Documentá el cálculo: nº de candidatos reales ×
   `_request_timeout`.
5. Un stream vacío deja rastro en el log con el nombre del backend, con `LLM_LOG_COT=0`.
6. Las 203 pruebas previas siguen pasando.

---

## Checklist pre-commit

El compartido de `README.md`, más:

```
[ ] Salida de la cadena de proveedores pegada, sin ninguna clave visible
[ ] Verificado que el fix NO cambia el comportamiento con texto parcial + excepción
    (no se reintenta otro backend: mezclaría dos respuestas)
[ ] .env NO está en git status  (git check-ignore .env  → confirma)
[ ] Decisión tomada en resolve_model documentada en el docstring y en PROGRESS.md
[ ] Ningún tag <think> tocado en esta WAVE  (git diff | grep -c 'think'  → 0)
[ ] LLM_MAX_TOKENS cambiado sólo por variable de entorno, no hardcodeado
```

---

## Commit

```
fix(llm): WAVE-01 desbloquear el turno en la ruta web

- stream_llm_response ya no retorna en un stream vacío: cae al siguiente backend,
  replicando la semántica que iter_reply_tokens ya aplicaba
- un stream vacío registra advertencia con el backend, incluso con LLM_LOG_COT=0
- resolve_model deja de filtrar LLM_MODEL a proveedores ajenos: la cadena de
  fallback ya no contiene un id namespaced imposible de resolver
- tests/test_llm_fallback.py cubre stream vacío, texto parcial y resolución de modelo
Cierra: hallazgos B, C, E
Métrica: peor caso de fallback ~180 s → <20 s; turnos vacíos por stream vacío → 0

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

## Rollback

Sin flag: son correcciones de defectos, no comportamiento nuevo opcional.

```bash
git revert <sha>
```
`LLM_MAX_TOKENS` y `LLM_LOG_COT` se revierten editando `.env`, sin tocar código.

---

## Handoff — volcar en `PROGRESS.md`

```markdown
### WAVE-01 — Desbloquear el turno
- Commit: <sha> · Fecha: <YYYY-MM-DD>
- Archivos tocados: <lista de git diff --stat>
- Tests añadidos: tests/test_llm_fallback.py::<casos>
- Métricas antes → después:
  - peor caso fallback: 180 s → <medido>
  - candidatos reales en la cadena: 2 → <n>
  - LLM_MAX_TOKENS: 180 → <valor>
- Decisión en resolve_model: <cuál y por qué>
- Criterios de aceptación: <1–6, cumplidos / no>
- Desvíos: <...>
- Hallazgos nuevos (NO arreglados): <...>
- Revisión humana: <OK, fecha>
```
Actualizá también la tabla de Estado (WAVE-01 → ✅) y, en Decisiones pendientes, el estado de
**D1** (`LLM_MAX_TOKENS`) como *provisional hasta WAVE-09*.

**Después: PARAR.** No empieces WAVE-02 sin una instrucción nueva.
