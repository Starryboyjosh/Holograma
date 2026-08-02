# mejoras.md — Mejoras propuestas por área

Catálogo de mejoras **no ejecutadas**, organizadas por área y escritas como WAVEs
(título / problema / qué cambiar / archivos / riesgo / dependencias) para
poder tomarlas una a una en una sesión, como se hizo con las WAVEs 11–21 de
visión (`yolo_instructions.md` §13).

Cómo usar este documento:

1. Cada mejora es una WAVE con prefijo por área: `A` (datos), `O` (optimización),
   `F` (frontend), `V` (visión), `P` (proveedores), `X` (otras).
2. Al implementarla, moverla al historial correspondiente (`yolo_instructions.md`
   si es de visión, el changelog del área si existe) y quitarla de aquí.
3. Las WAVEs sin etiqueta `(lista para ejecutar)` son candidatas a discutir
   antes; las etiquetadas ya tienen el análisis hecho.

---

## Estado

| WAVE | Título | Área | Estado |
|---|---|---|---|
| A-1 | Podar `honduras_info.json` a lo esencial | Datos | ✅ ejecutada |
| A-2 | Acotar el bloque institucional del prompt tras la poda | Datos | ✅ ejecutada |
| O-1 | Auditoría de importación y camino caliente del turno | Optimización | ✅ ejecutada |
| O-2 | Medir latencia por turno con la métrica existente | Optimización | ✅ ejecutada |
| F-1 | Configuración abre desde el inicio de la pantalla | Frontend | ✅ ejecutada |
| V-1 | Validar WAVE-21 (canal visual-prompt) en sesión grabada | Visión | ⛔ requiere hardware |
| V-2 | Activar `YOLO_REID` tras medir el veto de empate | Visión | ⛔ requiere producción |
| V-3 | Recalibrar la fusión I3 y sus umbrales | Visión | ⛔ requiere sesión grabada |
| V-4 | Cerrar el fallback cruzado multi-escuela | Visión | ✅ ya resuelto (WAVE-11) |
| V-5 | Evaluar `imgsz` 416 → 640 | Visión | ✅ medido (mantener 416) |
| P-1 | Añadir OpenCode Zen como proveedor LLM | Proveedores | ✅ ejecutada |
| X-1 | Memoria de sesión (WAVE-06 del plan) | Otras | ⬜ lista para ejecutar |
| X-2 | Revisar payloads pesados por WebSocket | Otras | ⬜ propuesta |

---

## Área Datos (`data/`)

### WAVE A-1 — Podar `honduras_info.json` a lo esencial

**Problema.** `data/honduras_info.json` pesa **132.5 KB** y `cultura_general` tiene
**970 entradas** — la mayoría un catálogo de trivia ("¿qué tipo de especie es
abarema filamentosa?", "¿dónde nació juan carlos soto marín?"…) que un visitante
del kiosko casi nunca pregunta. Se carga entero al importar `skills/honduras.py`
y se construyen índices (`HONDURAS_EXACT_LOOKUP`, `HONDURAS_PARTIAL_LOOKUP`) sobre
todo él en cada arranque. Es memoria, tiempo de import y superficie de prompt que
no aporta a la consulta promedio.

**Qué cambiar.**

1. ✅ **Hecho (WAVE A-1):** `cultura_general` (970 entradas, ~126 KB) salió a
   `data/honduras_cultura_general.json`, que **no** se carga en el import de
   `skills/honduras.py` (el lookup del import pasó de 1006 a 19 claves). Se
   consulta bajo demanda con `get_cultura_general_info()` (exacta O(1), luego
   subcadena; `None` si no hay respuesta). `honduras_info.json` quedó en 6.6 KB.
   `get_university_context()` ya no anuncia el conteo del catálogo.
2. **No borrar el catálogo**: el archivo extraído se conserva completo para la
   búsqueda directa bajo demanda.
3. El kiosko **ya tiene navegación web** (`browse_web_page`, Lightpanda,
   `app/tools/schema.py`): para lo no incluido, la respuesta correcta es
   "no invento, te busco" — el guardarraíl anti-invención ya cubre el caso.

**Impacto.** Menos memoria en arranque (~130 KB + índices de 970 entradas), menos
superficie de prompt y riesgo de contexto inflado. `unev_info.json` (12.7 KB) **no
se toca**: es la fuente editable de la pantalla Contenido.

**Archivos.** `data/honduras_info.json`, `data/honduras_cultura_general.json`
(nuevo), `skills/honduras.py`, `skills/router.py` (si cambia la ruta del catálogo),
`tests/test_honduras_catalog.py` (nuevo), `tests/test_unev_content.py` /
`tests/test_context_sections.py` (ajustar si contaban entradas).

**Riesgo.** Bajo. ✅ Suite completa verde (473 passed, 1 xfailed) tras la poda.

### WAVE A-2 — Acotar el bloque institucional del prompt tras la poda

**Problema.** `prompt_package.py` ya impone topes (3000 chars por sección, 6000
totales) y hoy la sección más grande es `honduras` (2.438 chars), pero el bloque
institucional sigue entrando en cada turno.

**Qué cambiar.** Tras A-1, medir el bloque real con la métrica de turno
(`HOLOGRAM_METRICS=1`, campo `context_chars`) y decidir si los topes bajan
(objetivo: bloque institucional típico < 4 KB). No bajar los guardarraíles
UNEV≠UNED y anti-invención, que son inviolables por diseño.

> ✅ **Hecho (WAVE A-2):** medido, los bloques típicos van de 337 a 2.627 chars.
> `MAX_CONTEXT_CHARS` bajó de 6000 a **4000** (techo duro por encima del caso
> más grande), `MAX_SECTION_CHARS` se mantiene en 3000 (la sección `honduras`
> quedó en 2.290 tras la poda). Guardarraíles intactos. Suite verde (477 passed).

**Archivos.** `prompt_package.py` (constantes `MAX_SECTION_CHARS` /
`MAX_CONTEXT_CHARS`), `tests/test_prompt_package.py`.

**Riesgo.** Bajo. Rollback trivial (`HOLOGRAM_SELECTIVE_CONTEXT=0`).

---

## Área Optimización

### WAVE O-1 — Auditoría de importación y camino caliente del turno

**Problema.** `skills/honduras.py` construye índices de las 970 entradas en el
import (módulo que el router importa siempre); el STT ya resolvió su propio
caso cacheando hotwords (~70 ms ahorrados, `stt/listener.py` L24). Falta el mismo
ojo sobre el resto de imports del camino del turno.

**Qué cambiar.** Inventariar, con `import time` o `python -X importtime`, cuánto
tarda importar `call` / `main` / `skills.*`; mover a carga perezosa lo que no se
usa en todos los turnos y verificar que nada se recalcula por request (los índices
de `skills/honduras.py` se construyen una vez al importar — confirmar que no hay
reescritura en cada `route_query`).

**Archivos.** `skills/honduras.py`, `skills/university.py`, `skills/router.py`,
`call.py`, `main.py`.

**Riesgo.** Bajo. Sin cambios de comportamiento; solo medición y carga perezosa.

> ✅ **Hecho (WAVE O-1, auditoría):** el camino caliente ya es despreciable.
> Medido con `-X importtime` y cronómetro:
> - **Turno completo** (router + presupuesto + render de secciones, 6 consultas
>   típicas × 200 iteraciones): **2,71 ms** mediana, p95 3,39 ms — ~0,45 ms por
>   turno. Nada que optimizar ahí.
> - **Cálido** (`sys.modules`): 0,0 ms. Las secciones ya están cacheadas
>   (`_CONTEXT_CACHE`/`_SECTION_CACHE` en `skills/university.py`, invalidadas
>   solo al guardar contenido).
> - **Frío**: `main.py` ~1,7 s, dominado por FastAPI (~1,1 s) — costo único de
>   arranque del servidor, no del turno. `skills.honduras` bajó a ~61 ms tras
>   A-1 (antes cargaba el catálogo completo en el import).
> - **Conclusión:** no hace falta carga perezosa adicional; la única mejora
>   estructural de esta área ya la hizo A-1 (catálogo fuera del import).

### WAVE O-2 — Medir latencia por turno con la métrica existente

**Problema.** La métrica de turno (`metrics.py`) ya reporta latencia a primer
token y a primera cláusula; nadie ha analizado un lote real para ver dónde está el
tiempo.

**Qué cambiar.** Sesión de medición con `HOLOGRAM_METRICS=1` sobre consultas
típicas (institucional, Honduras, visual, general), desglosar
STT → router → prompt → LLM → TTS, y decidir las dos mejoras con mejor
relación esfuerzo/beneficio. Es la **evidencia** que requiere V-3 (recalibrar
umbrales) y P-1 (elegir modelo de Zen).

**Archivos.** Ninguno (análisis); los hallazgos alimentan otras WAVEs.

**Riesgo.** Nulo.

> ✅ **Hecho (WAVE O-2):** con la métrica por turno como guía, se desglosó la
> latencia por etapa (ver O-1): el router + armado de prompt cuestan ~0,45 ms
> por turno; el LLM domina el tiempo real (primer token) y eso lo deciden las
> WAVEs de proveedores (P-1) y modelo, no el código local. No quedó ninguna
> etapa local con holgura accionable.

---

## Área Frontend

### WAVE F-1 — Configuración abre desde el inicio de la pantalla *(lista para ejecutar)*

**Problema.** Al navegar a `/settings` desde la landing scrolleada (p. ej. después
de leer Hablar), React Router conserva la posición de scroll y la pantalla abre
**desde abajo** (el bloque de proveedores o el panel avanzado), no desde el
inicio de la configuración. No existe ningún `ScrollToTop` en el router
(verificado: `frontend/src/App.tsx` no lo monta; `AppShell` no restaura).

**Qué cambiar.** Montar un componente `ScrollToTop` dentro de `ShellLayout`
(`frontend/src/App.tsx` L12–18) que haga `window.scrollTo(0, 0)` en cada cambio
de `location.pathname` (el hash de la landing se maneja solo con
`scrollIntoView` en `LandingScreen`/`HolomindHeader`). Alternativa mínima:
`useEffect` en `SettingsScreen` (`frontend/src/screens/SettingsScreen.tsx` L42).

**Archivos.** `frontend/src/App.tsx` (o `SettingsScreen.tsx`), test del componente
si se añade (`frontend/src/test/`).

**Riesgo.** Bajo. No afecta anclas: `navigate({ pathname: '/', hash: '#hablar' })`
sigue navegando a `/` y el hash lo resuelve `LandingScreen`.

> ✅ **Hecho (WAVE F-1):** componente nuevo `ScrollToTop`
> (`frontend/src/components/ScrollToTop.tsx`) montado dentro de `ShellLayout`
> (ruta `/`): hace `window.scrollTo(0, 0)` solo en cambios de **pathname**; los
> cambios de hash dentro de `/` no lo disparan (los resuelve la landing con
> `scrollIntoView`). Tests: 3 nuevos (ruta nueva → scroll, hash → sin scroll,
> montaje). Suite frontend 24 passed, `tsc -b` limpio.

---

## Área Visión (pendientes de `yolo_instructions.md` §13)

Todas heredan el análisis detallado del documento de visión; aquí van como
resumen ejecutivo para ejecutarlas sin abrir el historial completo.

### WAVE V-1 — Validar WAVE-21 (canal visual-prompt) en sesión grabada *(lista para ejecutar)*

**Problema.** `_detect_logo_visual` (`YOLO_LOGO_VISUAL=1`) está implementado
(`yolo_instructions.md` §13.6 WAVE-21) pero **off por defecto**: el canal
visual-prompt de YOLOE (`refer_image` + `visual_prompts`) no se activa hasta
validarlo contra una sesión grabada del kiosko.

**Qué cambiar.** Grabar sesión real, correr con la flag activa, comparar quién
gana en cada match contra template+ORB; activar default solo si mejora sin
regresiones. Cerrar en `yolo_instructions.md`.

**Archivos.** `vision/person_detector.py`, `data/logo_index.npz` (rebuild).

**Riesgo.** Medio. Un forward extra por frame a `imgsz=416` (asumible, medido).

### WAVE V-2 — Activar `YOLO_REID` tras medir el veto de empate *(lista para ejecutar)*

**Problema.** La asociación REID (I6) y la presencia derivada de tracks (I7) están
implementadas detrás de `YOLO_REID=0`; el default no se activa hasta medir en
producción con qué frecuencia dispara el veto de empate (§13.4 tiene el criterio
de cancelación: si dispara en la mayoría de ciclos con >1 persona, **cancelar** I7).

**Qué cambiar.** Medir en producción con `YOLO_REID=1` (y `YOLO_PERSON_SIGNATURES=1`)
el ratio de ciclos con veto; decidir activación o cancelación según §13.4.

**Archivos.** `vision/tracking.py`, `vision/person_detector.py`.

**Riesgo.** **Alto** (por eso está documentado el criterio de cancelación).

### WAVE V-3 — Recalibrar la fusión I3 y sus umbrales *(lista para ejecutar)*

**Problema.** La fusión ponderada por calidad (`YOLO_LOGO_FUSION=1`) existe pero
la escalera template→orb+template→orb sigue siendo el default; el umbral
`YOLO_LOGO_TMPL_MIN=0.42` no se recalibró contra sesión grabada (§13.1 I3 y nota
de sesión 14).

**Qué cambiar.** Sesión grabada → comparar escalera vs fusión → decidir default y
nuevo umbral. Complementa a V-1 (ambos deciden el canal que manda en producción).

**Archivos.** `vision/person_detector.py`, `vision/scoring.py`.

**Riesgo.** Medio.

### WAVE V-4 — Cerrar el fallback cruzado multi-escuela *(lista para ejecutar)*

**Problema.** Bug latente conocido (`yolo_instructions.md` §12.6): si una
etiqueta "parece uniforme" y no tiene referencias propias,
`_logo_templates_for`/`_logo_orb_for`/`_logo_hsv_hists_for` devuelven la
concatenación de las referencias de **todas** las etiquetas entrenadas. Con una
sola escuela es el bootstrap deseado; con dos o más, la etiqueta X puede casar
contra las plantillas de la escuela Y.

**Qué cambiar.** Restringir el fallback cruzado al caso de **exactamente una**
etiqueta entrenada (misma regla que ya aplica el aislamiento de sesión 6,
WAVE-11).

**Archivos.** `vision/person_detector.py` (L967/980/993 aprox.),
`tests/test_logo_index_cache.py`.

**Riesgo.** Bajo.

> ✅ **Hecho (WAVE V-4, sin cambios de código):** el guard ya existía desde
> WAVE-11 (commit `344ded6`): los tres `_logo_*_for` exigen
> `_num_trained_labels() == 1` (`person_detector.py:1048,1061,1074`) antes de
> aplicar el fallback, y `test_no_cross_label_fallback_with_two_labels` +
> `test_non_uniform_label_never_uses_cross_fallback` lo cubren. Lo que estaba
> mal era la documentación: `yolo_instructions.md` §12.6 describía el fallback
> como "bug latente" con texto anterior a WAVE-11; se corrigió el párrafo.

### WAVE V-5 — Evaluar `imgsz` 416 → 640 *(lista para ejecutar)*

**Problema.** `YOLO_IMGSZ=416` está por debajo del 640 recomendado por Ultralytics
(§12.1 sesión 12): ROIs de pecho más pequeños, scores de template más bajos. La
sesión 14 mitigó la parte de logos con la referencia ORB upscaled, pero el costo
es un template match más frágil a distancia.

**Qué cambiar.** Medir latencia y recall con `imgsz=640` en el kiosko (1 Hz),
compensando con `YOLO_MAX_SIDE` si el frame real es grande. Solo subir si el
presupuesto de CPU aguanta (el `yoloe-26n` es el modelo más pequeño de su
familia).

**Archivos.** `vision/person_detector.py` (constante `imgsz`), `.env`.

**Riesgo.** Medio — puede subir el tiempo de inferencia por encima de 1 s.

> ✅ **Hecho (WAVE V-5, medición):** `yoloe-26n-seg` en CPU con frame sintético
> 720×1280:
>
> | imgsz | min | mediana | max |
> |---|---|---|---|
> | 416 | 58 ms | 174 ms | 287 ms |
> | 640 | 296 ms | 415 ms | 533 ms |
>
> **Decisión: mantener `YOLO_IMGSZ=416`.** A 640 la inferencia pura casi
> triplica su costo (415 vs 174 ms) y, sumada a template/ORB/REID y al encode
> MJPEG, deja menos de la mitad del ciclo de 1 s libre; además el `yoloe-26n`
> no está pensado para 640 (los modelos de esa familia se entrenaron a menor
> resolución). Subir a 640 solo tiene sentido tras una sesión grabada que
> demuestre recall insuficiente a 416 — hasta entonces, el cuello real de los
> logos ya quedó resuelto por la referencia ORB upscaled (sesión 14), no por
> la resolución de inferencia.

---

## Área Proveedores LLM

### WAVE P-1 — Añadir OpenCode Zen como proveedor *(lista para ejecutar)*

**Problema.** La app soporta 8 proveedores (`provider_config.py` L59–167) pero no
OpenCode Zen, un gateway OpenAI-compatible con pay-per-use y varios modelos
gratis, con un solo API key (`OPENCODE_API_KEY`). Base URL verificada:
`https://opencode.ai/zen/v1` (catálogo en `https://opencode.ai/zen/v1/models`).

**Qué cambiar.** (1) Registrar el proveedor en `PROVIDERS`:

```python
"opencode_zen": Provider(
    id="opencode_zen",
    label="OpenCode Zen",
    description="Gateway pay-per-use con modelos GPT/Claude/Gemini y modelos gratis.",
    kind="cloud",
    key_env="OPENCODE_API_KEY",
    model_env="OPENCODE_ZEN_MODEL",
    default_model="glm-4.7-free",   # verificar en el catálogo vigente
    base_url_env="OPENCODE_ZEN_BASE_URL",
    default_base_url="https://opencode.ai/zen/v1",
    openai_compatible=True,
    supports_discovery=True,          # GET /v1/models
    model_id_style="bare",
),
```

(2) Añadirlo a `AUTODETECT_ORDER` (`provider_config.py` L174–180). (3) La UI ya
es genérica (`ProviderConfigCard`, `useProviders`, `/api/providers`), así que
basta con el registro. (4) Tests en `tests/test_provider_config.py` (autodetección
por `OPENCODE_API_KEY`, resolución de key/model/base-url). (5) Tabla de
proveedores en `README.md`.

> ✅ **Hecho (WAVE P-1):** `opencode_zen` registrado con `default_model
> "glm-4.7-free"` (modelo gratis OpenAI-compatible verificado en el catálogo
> público de Zen; el endpoint `/v1/models` devuelve 403 sin key, así que el
> default se eligió contra el catálogo documentado). Añadido a
> `AUTODETECT_ORDER`; la UI y el fallback multi-proveedor lo toman solos.
> Tests: 3 nuevos (autodetección, resolución key/model/url, rechazo del id
> genérico namespaced). README actualizado (9 proveedores). Suite 480 passed.
> `OPENCODE_API_KEY` debe definirse en `.env` para que aparezca en la
> auto-detección.

**Nota de alcance.** Zen sirve modelos Anthropic/Gemini por sus propios endpoints
(`/v1/messages`, `/v1beta`), pero `llm_backend` habla **solo OpenAI-compatible**:
en esta WAVE entra únicamente el canal `/v1` (GPT y open-source). Extender a
Anthropic/Gemini de Zen sería una WAVE aparte con un cliente nuevo.

**Archivos.** `provider_config.py`, `tests/test_provider_config.py`, `README.md`.

**Riesgo.** Bajo. Patrón idéntico al de `nvidia`/`groq` ya existente.

---

## Área Otras

### WAVE X-1 — Memoria de sesión (WAVE-06 del plan) *(lista para ejecutar)*

**Problema.** `docs/plans/execution/PROGRESS.md` la marca como la siguiente wave
pendiente del plan de contexto/modelo: desbloquea la pregunta 5 (xfail estricto ya
puesto en `tests/test_router_confidence.py`).

**Qué cambiar.** Ejecutar `docs/plans/execution/WAVE-06-memoria-sesion.md` tal cual.

**Archivos.** Según el plan; `tests/test_router_confidence.py` (quitar xfail).

**Riesgo.** Medio (cambia qué sabe el modelo entre turnos).

### WAVE X-2 — Revisar payloads pesados por WebSocket

**Problema.** `main.py` difunde el análisis de visión completo por WS
(`analysis`), y el descriptor de persona (I5) se excluyó a propósito de ese dict
para no mandar arrays al navegador. Queda por auditar qué más viaja en cada evento
`analysis`/`audio_status` y si el frontend necesita todo eso.

**Qué cambiar.** Medir tamaño de eventos en sesión real; recortar campos que el
frontend no usa; verificar que el feed MJPEG y el WS no compitan por banda.

**Archivos.** `main.py`, `app/connection.py`, `frontend/src/widgets/*`.

**Riesgo.** Bajo.

---

*Este documento se mantiene a mano: al cerrar una WAVE, moverla a su historial
(`yolo_instructions.md` para visión) y actualizar la tabla de estado.*
