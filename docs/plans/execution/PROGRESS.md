# PROGRESS — estado vivo de la ejecución

**Este archivo es la memoria del plan.** Se actualiza en la Puerta 2 de cada WAVE, antes de
parar. Un modelo que llega sin contexto lee `README.md` y este archivo, y sabe exactamente
dónde está todo.

Última actualización: **2026-07-30** — los 13 archivos del plan están escritos (10 WAVEs + este
archivo + `README.md` + el documento maestro `../HOLOGRAM_CONTEXT_AND_MODEL_ARCHITECTURE_PLAN.md`)
y commiteados en `514b2e4`. **WAVE-01 (`99d40c7`) y WAVE-02 (`cd3b1cd`) ejecutadas y commiteadas.**

> **Cambio de protocolo — 2026-07-30, decisión del usuario.** Las verificaciones que necesitan
> hardware físico, percepción humana o una llamada de pago real **no** bloquean el cierre de cada
> WAVE: se acumulan en [`PRUEBAS-MANUALES-PENDIENTES.md`](PRUEBAS-MANUALES-PENDIENTES.md) y el
> usuario las revisa todas juntas **al terminar las WAVEs**. Todo lo demás (suite, ruff, prueba de
> reversión, evidencia de la métrica) se sigue exigiendo wave por wave, sin excepción.

---

## Estado

| WAVE | Estado | Commit | Fecha | Notas |
|---|---|---|---|---|
| 01 · Desbloquear el turno | ✅ commiteada | `99d40c7` | 2026-07-30 | criterio 4 no cumplido → WAVE-09 |
| 02 · Filtro CoT streaming | ✅ commiteada | `cd3b1cd` | 2026-07-30 | smoke test de audio diferido → pruebas manuales |
| 03 · Instrumentación | ✅ commiteada | `9313531` | 2026-07-30 | línea base offline lista; latencias reales diferidas → P03-1 |
| 04 · Secciones de contexto | 🟡 en curso | — | 2026-07-30 | **siguiente** |
| 05 · PromptPackage + router | ⬜ pendiente | — | — | |
| 06 · Memoria de sesión | ⬜ pendiente | — | — | |
| 07 · Paridad de rutas | ⬜ pendiente | — | — | |
| 08 · Política de cámara | ⬜ pendiente | — | — | |
| 09 · Política de modelos | ⬜ pendiente | — | — | espera decisión humana en su puerta |
| 10 · Dataset de evaluación | ⬜ pendiente | — | — | |

Estados: ⬜ pendiente · 🟡 en curso · ✅ commiteada · ⛔ bloqueada (ver Desvíos)

**Siguiente acción:** ejecutar `WAVE-04-secciones-contexto.md` siguiendo `README.md`.
Fase 1 cerrada: las tres WAVEs de la demo están commiteadas.

---

## Línea base (antes de cualquier WAVE)

Medido el 2026-07-29 sobre `main` en el commit `6458e07`, con el `.env` + `config.json` reales
del equipo.

### Suite
```
203 funciones de test en 28 archivos, todas pasando
209 casos ejecutados por pytest (la diferencia es parametrización), exit 0
0 tests cubren skills/router.py, skills/university.py, skills/honduras.py,
  skills/utils.py, skills/event_mode.py
```

> Los dos números son correctos y describen cosas distintas: **203 funciones** escritas,
> **209 casos** ejecutados. Si al verificar la Puerta 1 ves 209 pasando, está bien.

### Prompt por turno
| Métrica | Valor |
|---|---|
| Contexto institucional (`get_university_context`) | **15.516 chars** (UNEV 13.076 + Honduras 2.438) |
| Prompt total por turno | **~18.439–18.814 chars** |
| Tokens de entrada estimados (3,5 ch/token) | **~5.340** |
| Peso de la pregunta del visitante en el prompt | **0,3–0,4 %** |
| Variación del contexto según la pregunta | **0 %** — es idéntico siempre |
| Reducción alcanzable con recuperación selectiva | **90,1 % medio** (18.439 → 1.833; rango 83,6–95,1 %) |

### Latencias medidas
| Operación | Tiempo |
|---|---|
| `get_university_context()` en frío | 0,129 ms |
| `get_university_context()` cacheado | ~0 ms |
| `route_local_skill()` | 0,0116 ms |
| Peor caso de cadena de fallback | **~180 s** antes de la primera palabra |

> El coste del contexto **no** es construirlo (es gratis y está cacheado). Es enviarlo:
> ~5.340 tokens de prefill por turno, en cada turno.

### Configuración viva (sin secretos)
```
proveedor primario : openrouter
modelo             : nvidia/nemotron-3-nano-30b-a3b:free   (modelo de razonamiento, tier free)
cadena cloud       : ['openrouter', 'groq']
groq               : clave presente (se usa para STT: whisper-large-v3-turbo)
LLM_MAX_TOKENS     : 180
LLM_REQUEST_TIMEOUT: 90.0 s
LLM_LOG_COT        : False
```
Variables leídas: `LLM_BACKEND`, `LLM_MODEL`, `LLM_MAX_TOKENS`, `LLM_REQUEST_TIMEOUT`,
`LLM_LOG_COT`, `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, `GROQ_API_KEY`, `GROQ_MODEL`.
**Nunca registres valores de claves en este archivo.**

### Precisión del router (11 preguntas obligatorias)
`route_local_skill` acierta **4 de las 7 preguntas que le corresponden** (las nº 2–8). Contando
también las cuatro donde devolver `None` es lo correcto (nº 1, 9, 10, 11), son **8 de 11**.
Los dos denominadores describen cosas distintas y conviene no mezclarlos: **4/7 mide el enrutado**,
que es lo que este plan arregla.

Falsos positivos medidos por coincidencia de subcadena sin límite de palabra (p. ej. `Europa` →
`ropa`, `joven` → `ven`, y sobre todo `Háblame` → `habla` → vulgarismos). Tabla completa,
pregunta por pregunta, en `../HOLOGRAM_CONTEXT_AND_MODEL_ARCHITECTURE_PLAN.md`, **§5** (Auditoría
del prompt actual).

---

## Objetivos numéricos del plan

Cada uno se verifica con la instrumentación de WAVE-03. Sin número, no hay criterio.

| Métrica | Base | Objetivo | WAVE |
|---|---|---|---|
| Contexto medio por turno | 18.439 chars | **≤ 2.500** | 05 |
| Tokens de entrada estimados | ~5.340 | **≤ 750** | 05 |
| Peor caso de fallback | ~180 s | **< 20 s** | ~~01~~ → **09** (depende de `LLM_REQUEST_TIMEOUT`) |
| Cláusulas con CoT habladas | posible | **0 ✅ logrado** (falta confirmar por oído: P02-1) | 02 |
| Turnos vacíos por stream vacío en la ruta web | posible | **0 ✅ logrado** | 01 |
| Precisión del router (11 preguntas) | **4/7 aplicables** (8/11 total) | **≥ 6/7** (≥ 10/11) | 05 · 06 |
| Follow-ups resueltos (`«¿y cuánto dura?»`) | 0 % | **funciona en ambas rutas** | 06 |
| Tests que cubren `skills/` | 0 | **> 0, con dataset** | 10 |

---

## Registro por WAVE

Al cerrar cada WAVE, añadí un bloque acá con este formato. No borres bloques anteriores.

```markdown
### WAVE-NN — <título>
- Commit: <sha corto> · Fecha: <YYYY-MM-DD>
- Archivos tocados: <lista>
- Tests añadidos: <archivo::caso, ...>
- Métricas antes → después: <...>
- Criterios de aceptación: <cumplidos / cuáles no y por qué>
- Desvíos del plan: <ninguno / qué y por qué>
- Hallazgos nuevos (NO arreglados): <...>
- Revisión humana: <OK de quién, fecha>
```

### WAVE-01 — Desbloquear el turno
- Commit: `99d40c7` · Fecha: 2026-07-30
- Archivos tocados: `llm_backend.py`, `provider_config.py`, `tests/test_llm_fallback.py` (nuevo).
  `.env` local: `LLM_MAX_TOKENS` 180 → 800, `LLM_LOG_COT` 0 → 1 (no versionado).
  `main.py` y `.env.example` **no** se tocaron: el primero no documenta estas variables y el
  segundo documenta el default del código (450), que no cambió.
- Tests añadidos: `tests/test_llm_fallback.py::test_stream_vacio_cae_al_siguiente_backend`,
  `::test_stream_vacio_en_todos_los_backends_devuelve_respuesta_local`,
  `::test_texto_parcial_no_reintenta_otro_backend`, `::test_stream_vacio_registra_advertencia`,
  `::test_resolve_model_no_filtra_generico_a_otro_proveedor`,
  `::test_resolve_model_respeta_variable_especifica`
- Métricas antes → después:
  - Suite: 209 → **215 casos**, exit 0.
  - Turnos vacíos por stream vacío en la ruta web: posible → **0** (la cadena continúa).
  - Modelo efectivo de `groq` en la cadena: `nvidia/nemotron-3-nano-30b-a3b:free` (id que su API
    no conoce, fallo garantizado tras 90 s) → **`llama-3.3-70b-versatile`**, respaldo real.
  - Peor caso de la cadena: ~180 s → **~180 s, sin cambio** (ver criterios).
- Criterios de aceptación: 1, 2 y 3 cumplidos con salida real. **El 4 (`< 20 s`) NO se cumple**,
  y su justificación en el archivo de la WAVE era incorrecta: suponía que el eslabón envenenado
  desaparecía de la cadena. No desaparece —y aunque lo hiciera, un solo eslabón a 90 s ya excede
  los 20 s. Bajar el peor caso es exclusivamente `LLM_REQUEST_TIMEOUT`, que §14 asigna a
  **WAVE-09**. Se deja constancia y se mueve el objetivo allá.
- Desvíos del plan:
  - **`resolve_model`: ninguna de las dos opciones del archivo era aplicable tal cual.** La
    Opción 1 (genérico sólo para el primario) rompe `test_model_uses_llm_model_for_cloud_providers`
    y exigiría cambiar la firma, porque `resolve_model` no sabe quién es el primario. La Opción 2
    literal ("rechazar ids con `/`") rompe la misma prueba: **NVIDIA usa namespace legítimamente**
    (`meta/llama`; su propio default es `moonshotai/kimi-k2.6`).
    **Implementado (espíritu de la Opción 2):** campo nuevo `Provider.model_id_style` con valores
    `"namespaced"` (openrouter, nvidia) · `"bare"` (openai, groq, claude_native) · `"any"` (default
    permisivo: custom_openai, ollama, local_only). El filtro se aplica **sólo** a la herencia de
    `LLM_MODEL`; el override específico por proveedor (`GROQ_MODEL`, `OPENAI_MODEL`) sigue mandando.
    **Por qué así:** el default permisivo mantiene la compatibilidad hacia atrás (nadie hereda menos
    que antes salvo cuando la forma es incompatible), no cambia ninguna firma, no toca `select_backend`
    ni `resolve_api_key`, y deja pasar las cuatro pruebas existentes de `resolve_model` sin editarlas.
    Documentado en el docstring de `resolve_model`.
  - **Pase de revisión con agente `worker`: omitido.** La sesión tenía instrucción de no lanzar
    subagentes salvo pedido explícito. La WAVE lo marca como "asistencia, NO la puerta"; la revisión
    humana sí se hizo.
- Hallazgos nuevos (NO arreglados): ver RUFF-1 abajo.
- Revisión humana: OK explícito del usuario, 2026-07-30, tras presentar el checklist completo, los
  dos desvíos y el resumen del diff.
- Pruebas manuales diferidas: **P01-1**, **P01-2** (ver `PRUEBAS-MANUALES-PENDIENTES.md`).

### WAVE-02 — Filtro de razonamiento en streaming
- Commit: `cd3b1cd` · Fecha: 2026-07-30
- Archivos tocados: `llm_backend.py`, `call.py`, `tests/test_cot_filter.py` (nuevo).
  `utils.py` intacto (`git diff` vacío, como exige la WAVE). `app/services/conversation.py` **no**
  se tocó: filtrar en el origen del stream bastó para las dos rutas, así que el servicio sigue sin
  saber nada de etiquetas.
- Qué se hizo:
  - El juego de tags (`think|thinking|reasoning|analysis|scratchpad`) pasó a constantes de módulo
    en `llm_backend.py` —`_COT_TAGS`, `COT_BLOCK_RE`, `COT_LOOSE_TAG_RE`, `COT_OPEN_RE`,
    `COT_CLOSE_RE`, `COT_ANY_TAG_RE`— y ahora lo consumen los tres interesados:
    `_strip_qwen_thinking`, `_CotStreamMirror` y el filtro nuevo. **Una sola definición.**
  - Clase nueva `_CotStreamFilter` (`feed(text) -> str` / `flush() -> str`), con estado `in_think`
    por turno y cola de 24 caracteres para que una etiqueta partida entre chunks no se cuele.
    Un bloque abierto que nunca cierra se descarta entero.
  - Aplicado en los **tres** puntos que emiten tokens en streaming:
    `_iter_openai_compatible_tokens` (ruta de voz) y las dos ramas de `_stream_backend_response`
    (claude_native y openai-compatible, ruta web). El espejo `_CotStreamMirror` recibe el texto
    **crudo** antes de filtrar: sigue sirviendo de diagnóstico.
  - Los dos sitios **no**-streaming quedan sin filtro a propósito: acumulan en `parts` y ya pasan
    por `_postprocess_reply` → `_strip_qwen_thinking`.
  - `call.clean_for_tts` pasó de conocer sólo `<think>` a usar el regex compartido, incluidas
    etiquetas sueltas sin pareja.
  - Flag de rollback `HOLOGRAM_COT_FILTER=0`, con la forma de `_tts_stream_enabled()`.
- Tests añadidos (`tests/test_cot_filter.py`, 8): `::test_bloque_partido_entre_chunks_no_se_emite`,
  `::test_clausula_con_think_abierto_no_llega_al_tts`, `::test_texto_sin_tags_pasa_intacto`,
  `::test_los_cinco_tags_se_filtran`, `::test_tag_abierto_sin_cerrar_al_final_se_descarta`,
  `::test_filtro_funciona_con_LLM_LOG_COT_apagado`, `::test_flag_desactiva_el_filtro`,
  `::test_ruta_web_difunde_texto_limpio`
- Métricas antes → después:
  - Suite: 215 → **223 casos**, exit 0.
  - Cláusulas con CoT habladas (simulador del hallazgo D, chunks de 1 carácter): **2 de 3 → 0 de 1**.
    Antes: `'<think>El usuario pregunta…'` / `'Debo responder breve.</think>La carrera…'`.
    Después: una sola cláusula, `'La carrera de Programacion Web dura 2 anos.'`
  - Etiquetas que `clean_for_tts` sabía quitar: **1 de 5 → 5 de 5**.
  - Prueba de reversión: con `llm_backend.py` y `call.py` en `git stash`, **8 de 8 fallan**;
    restaurados, 8 de 8 pasan.
  - `ruff` en los archivos tocados: limpio. Proyecto: sigue en 18 errores preexistentes (RUFF-1).
- Criterios de aceptación: cumplidos, con una contradicción del propio archivo resuelta (abajo).
- Desvíos del plan:
  - **§2 contradice al criterio 7.** §2 pide que un chunk vacío tras filtrar "tampoco cuente como
    stream vacío para el `produced` de WAVE-01"; el criterio 7 pide que un turno enteramente de
    razonamiento caiga al fallback de WAVE-01. Son incompatibles: lo primero implica `produced=True`
    sin texto y lo segundo `produced=False`.
    **Implementado el criterio 7:** sólo se emite texto visible, así que un turno todo-CoT deja
    `produced=False` y se prueba el siguiente backend. Verificado en vivo con dobles: la cadena
    imprime `[LLM] Stream vacío del backend 'openrouter': probando el siguiente` y groq responde.
    **Por qué así:** la lectura de §2 dejaría el turno cerrado en silencio, que es exactamente el
    defecto que WAVE-01 acababa de cerrar.
  - **Pase de revisión con agente `worker`: omitido**, por el mismo motivo que en WAVE-01
    (instrucción de sesión de no lanzar subagentes). La WAVE lo marca como "asistencia, NO la puerta".
- Hallazgos nuevos (NO arreglados): ninguno.
- Revisión humana: OK explícito del usuario, 2026-07-30, tras presentar el checklist completo, la
  evidencia antes/después del hallazgo D y el desvío §2 vs criterio 7.
- Pruebas manuales diferidas: **P02-1** (smoke test de audio), **P02-2**, **P02-3**
  (ver `PRUEBAS-MANUALES-PENDIENTES.md`).

### WAVE-03 — Instrumentación del turno
- Commit: `9313531` · Fecha: 2026-07-30
- Archivos tocados: `metrics.py` (**nuevo**), `llm_backend.py`, `call.py`,
  `tests/test_metrics.py` (**nuevo**), `.env.example`, `README.md`.
  `app/services/conversation.py` **no** se tocó, y eso es más fuerte que lo que sugería la WAVE
  (lo listaba como archivo a modificar): instrumentando en el generador que ya posee el bucle de
  backends, las dos rutas quedan cubiertas sin que el servicio sepa nada de métricas. Es
  exactamente lo que pide §2 ("no dupliques el formateo en `call.py` y en `conversation.py`").
- Qué se hizo:
  - Módulo `metrics.py` con `TurnMetrics`: **un solo punto de emisión y un solo formato** para las
    dos rutas. Una línea JSON por turno, prefijo `[METRICS]`, con `route`, `event_mode`,
    `provider`, `model`, `context_chars`, `prompt_chars`, `estimated_input_tokens`,
    `local_skill_hit`, `time_to_first_token_ms`, `time_to_first_clause_ms`, `fallback_count`.
  - Instanciado en `iter_reply_tokens` (`route="voice"`) y `stream_llm_response` (`route="web"`),
    en ambos casos con el `emit()` dentro de un `finally`: cubre el retorno normal, la caída al
    fallback local y el consumidor que abandona el generador a media respuesta. `emit()` es
    idempotente porque un `GeneratorExit` lo dispararía además del cierre normal.
  - `time_to_first_clause_ms` se calcula **dentro** de `TurnMetrics` reutilizando
    `pop_ready_speech` (tabla de reutilización) sobre el mismo stream que ve el consumidor, en vez
    de sacar un callback hasta `speak_streaming_from_llm` / `ConversationService`. Así el hito sale
    idéntico en las dos rutas y no hubo que tocar `LLMService` ni sus dobles.
  - Secretos: la línea pasa por `security.redact_secrets(payload, os.environ)`, la **misma**
    función y la misma invocación que usa `main.py`. La línea lleva longitudes, nunca contenido.
  - Flag de rollback `HOLOGRAM_METRICS=0`, documentado en `.env.example` y `README.md`.
- Tests añadidos (`tests/test_metrics.py`, 7): `::test_metrica_emitida_una_vez_por_turno_ruta_web`,
  `::test_metrica_emitida_una_vez_por_turno_ruta_voz`,
  `::test_metrica_incluye_los_campos_obligatorios`, `::test_metrica_no_contiene_secretos`,
  `::test_metrica_no_contiene_el_prompt_completo`, `::test_fallback_count_refleja_los_intentos`,
  `::test_flag_desactiva_las_metricas`
- Métricas antes → después:
  - Suite: 223 → **230 casos**, exit 0.
  - Turnos con métrica: **0 → 1 línea por turno**, en las dos rutas y con el mismo formato.
  - Prueba de reversión: con `llm_backend.py` y `call.py` en HEAD (y `metrics.py` presente),
    **7 de 7 fallan**; revertido también el módulo, la colección ni siquiera arranca. Restaurado,
    7 de 7 pasan.
  - `ruff` en los archivos tocados: limpio. Proyecto: sigue en **18** errores preexistentes
    (RUFF-1), sin cambio.
  - `git diff --stat tests/` sobre los tests previos: **vacío** (criterio 7). `git diff` sobre
    `requirements*.txt` y `pyproject.toml`: **vacío** (cero dependencias nuevas).

#### Línea base de las 11 preguntas obligatorias

Medida **offline**, sin red y sin una sola llamada de pago: se construye el prompt real con
`_build_messages(pregunta, get_system_prompt("normal"), get_university_context(), None)` y se
miden longitudes. Con `HOLOGRAM_CAMERA=1`, que es el default del kiosco.

| # | pregunta | ctx | prompt | ~tok | skill local |
|---|----------|-----|--------|------|-------------|
| 1 | ¿Cómo estás? | 15.516 | 18.496 | 5.285 | no |
| 2 | ¿Qué significa UNEV? | 15.516 | 18.504 | 5.287 | no |
| 3 | ¿Qué carreras ofrecen? | 15.516 | 18.506 | 5.287 | sí |
| 4 | ¿Cuánto dura Programación Web? | 15.516 | 18.514 | 5.290 | sí |
| 5 | ¿Y cuánto dura? | 15.516 | 18.499 | 5.285 | no |
| 6 | ¿Dónde queda la UNEV? | 15.516 | 18.505 | 5.287 | sí |
| 7 | ¿Está aprobada por el CES? | 15.516 | 18.510 | 5.289 | sí |
| 8 | Háblame de la lluvia de peces. | 15.516 | 18.514 | 5.290 | sí |
| 9 | ¿Qué ves frente a ti? | 15.516 | 18.505 | 5.287 | no |
| 10 | ¿Cuál es el precio actual de algo que requiere internet? | 15.516 | 18.540 | 5.297 | no |
| 11 | Cuéntame un chiste. | 15.516 | 18.503 | 5.287 | no |

**Contexto institucional = 15.516 chars, idéntico en las 11.** Media de entrada estimada:
**~5.288 tokens/turno**. Coincide con el `~5.340` de la auditoría → **criterio 6 cumplido**.

Qué columnas son de qué naturaleza, para no confundirlas al revisar:

| Campo | Cómo se obtuvo |
|---|---|
| `context_chars`, `prompt_chars`, `estimated_input_tokens`, `local_skill_hit` | **offline**, deterministas, en la tabla de arriba |
| `route`, `event_mode`, `fallback_count` | offline, verificados con backends dobles en los tests |
| `provider`, `model` | offline en los tests; el valor **real** depende del `.env` vivo |
| `time_to_first_token_ms`, `time_to_first_clause_ms` | **requieren una llamada de pago real**: con dobles salen 0–1 ms y no dicen nada. Diferido → **P03-1** |

> **Reconciliación de la línea base (importante para WAVE-04/05).** El prompt mide 16.9 K chars
> con `HOLOGRAM_CAMERA=0` y 18.5 K con `HOLOGRAM_CAMERA=1`: `get_system_prompt` le añade el bloque
> "REGLAS DE HUMANIZACIÓN VISUAL", **+1.593 chars (~455 tokens) en cada turno**, se hable o no de
> lo que ve la cámara. El `~5.340` de la auditoría es la cifra con cámara encendida, que es el
> escenario de producción. Al comparar contra el objetivo de ≤ 750 tokens hay que usar **5.288**,
> no 4.833.

- Criterios de aceptación: 1–7 cumplidos. El criterio 6 (la línea base reproduce los 15.516 chars
  y los ~5.340 tokens de la auditoría) se cumple exactamente, con la reconciliación de arriba.
- Desvíos del plan:
  - **`local_skill_hit` es un booleano, no el nombre de la skill.** La tabla de la WAVE pide el
    nombre, pero `route_local_skill` devuelve el **texto ya renderizado** y no identifica quién
    respondió. Sacarle el nombre exige modificar `skills/router.py`, y esta WAVE dice explícitamente
    que **observa sin alterar lo que mide**. El nombre pertenece a WAVE-05, que reescribe el router.
  - **La línea sale por `stderr`, no por `stdout`.** No fue una preferencia: emitiendo por stdout se
    rompía `test_llm_fallback.py::test_stream_vacio_registra_advertencia`, que afirma sobre *todo*
    lo impreso, y el criterio 7 prohíbe tocar un test previo. Además stdout es el log humano del
    kiosco y el canal del sidecar. Se aísla con `2> metrics.log`.
  - **`HOLOGRAM_METRICS` documentada en `.env.example` + `README.md`, no en `main.py`.** La WAVE
    nombraba `main.py`, pero `metrics_enabled()` usa `utils._env`, que lee **sólo** `os.environ`:
    meter la variable en el `default_config` de `main.py` la expondría por `GET /api/config` sin
    que eso la controle, que sería documentación falsa.
  - **Pase de revisión con agente `worker`: omitido**, igual que en WAVE-01 y WAVE-02
    (instrucción de sesión de no lanzar subagentes). La WAVE lo marca como "asistencia, NO la puerta".
- Hallazgos nuevos (NO arreglados): **OBS-1**, **OBS-2** (ver la sección de abajo).
- Revisión humana: OK explícito del usuario, 2026-07-30, tras presentar el checklist completo
  (230 pasando, 7/7 fallan al revertir, `context_chars` = 15.516 re-medido), el resumen del diff
  y los tres desvíos. En el mismo turno autorizó **encadenar WAVE-04 en esta sesión**, saltando
  la parada del runbook.
- Pruebas manuales diferidas: **P03-1**, **P03-2** (ver `PRUEBAS-MANUALES-PENDIENTES.md`).

---

## Desvíos y hallazgos nuevos

Todo lo que se encuentre roto **fuera** del alcance de la WAVE en curso va acá, sin arreglarse.
Incluí archivo y símbolo para que sea accionable después.

### Abiertos desde la auditoría (fuera del alcance de las 10 WAVEs)

- **SEC-1 · Clave en texto plano.** `config.json` guarda una clave de Groq en claro y es el
  almacén principal, porque `POST /api/config` persiste ahí todas las claves. No está en git
  (verificado con `git ls-files`). **Recomendación: rotar esa clave** y consolidar los secretos
  en `.env`. No es una WAVE porque no es un cambio de código; es una acción del operador.
  *Estado: reportado, pendiente de acción humana.*

- **INFO-1 · Discrepancia de proveedor en el briefing.** La documentación previa asumía Groq +
  `qwen3-8b-instant` como ruta de chat. La configuración viva es OpenRouter +
  `nvidia/nemotron-3-nano-30b-a3b:free`; la clave de Groq existe pero sirve al STT. Cualquier
  documento que afirme lo contrario está desactualizado. *Estado: sólo informe.*

- **INFO-2 · La capa de herramientas web nunca existió.** `git log --all -S` devuelve cero
  commits: no hay nada que "restaurar". Si se quiere búsqueda web, es obra nueva y necesita su
  propio plan. *Estado: sólo informe, fuera del alcance de este plan.*

### Nuevos (añadir acá durante la ejecución)

- **RUFF-1 · 18 errores de lint preexistentes fuera del alcance.** `ruff check .` no está limpio en
  `main`, y no lo estaba antes de WAVE-01: `skills/honduras.py` (10), `vision/person_detector.py` (4),
  `utils.py` (1), `stt/listener.py` (1), `tests/test_hotwords_cache.py` (1),
  `tests/test_custom_object_interval.py` (1). Mayormente variables sin usar; 14 los arregla
  `ruff --fix`. Los archivos tocados por cada WAVE sí deben quedar limpios, y WAVE-01 lo está.
  *Estado: anotado, no arreglado (regla "anotá, no arregles"). Candidato a una limpieza propia.*

- **OBS-1 · `test_stream_vacio_registra_advertencia` afirma sobre todo el stdout.** La aserción es
  `assert "groq" not in salida` sobre `capsys.readouterr().out` **entero**, no sobre la línea de
  advertencia. Cualquier log futuro que nombre un backend rompe ese test sin que haya una regresión
  real; ya obligó a mover las métricas a stderr en WAVE-03. Arreglo: acotar la aserción a las
  líneas que empiezan por `[LLM]`. *Estado: anotado, no arreglado — es un test previo y el
  criterio 7 prohíbe tocarlo dentro de esta WAVE.*

- **OBS-2 · El bloque visual del system prompt se envía siempre.** Con `HOLOGRAM_CAMERA=1`,
  `skills/event_mode.get_system_prompt` añade "REGLAS DE HUMANIZACIÓN VISUAL" —**+1.593 chars,
  ~455 tokens por turno**— aunque la pregunta no tenga nada que ver con lo que ve la cámara (10 de
  las 11 obligatorias). Es ~8,6 % del prompt y es condicionable por intención. *Estado: anotado,
  no arreglado. Encaja en **WAVE-08** (política de cámara) y le da munición a **WAVE-05**.*

- **INFO-3 · `audit_prompt.md` sin trackear en la raíz.** Archivo de trabajo previo al plan, sigue
  fuera de git. Decidir si se archiva bajo `docs/` o se borra. *Estado: sólo informe.*

---

## Decisiones pendientes de humano

| # | Decisión | Se necesita en | Estado |
|---|---|---|---|
| D1 | `LLM_MAX_TOKENS`: la propuesta es 800. Confirmar con las métricas reales de WAVE-03. | Puerta de WAVE-01 (provisional) y WAVE-09 (definitiva) | **provisional aplicada**: 800 en el `.env` local (era 180). Sin hardcodear: el default del código sigue en 450. Confirmar en WAVE-09. |
| D4 | `LLM_REQUEST_TIMEOUT` (hoy 90 s por eslabón, cadena de 4 → peor caso ~180 s de espera cloud). Para cumplir el objetivo de **< 20 s** hace falta un timeout escalonado o un presupuesto de cadena. Es cambio de `.env`, cero código. Riesgo: cortar respuestas lentas legítimas. | Puerta de WAVE-09 | **abierta** — heredada de WAVE-01, ver su registro |
| D2 | Seguir con el modelo de razonamiento en tier `:free`, o pasar a un no-razonador de pago. Afecta latencia a primera palabra en vivo. | Puerta de WAVE-09 | abierta |
| D3 | TTL de frescura de cámara (hoy 60 s hardcodeado). Valor y comportamiento con dato viejo. | Puerta de WAVE-08 | abierta |

Fuera de discusión en este plan: **ElevenLabs está fuera de alcance; Piper sigue siendo el
TTS.**
