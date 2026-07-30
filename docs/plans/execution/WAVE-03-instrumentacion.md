# WAVE-03 — Instrumentación y línea base

| | |
|---|---|
| **Fase** | 1 · Desbloquear la demo |
| **Riesgo** | Bajo — sólo añade observación, no cambia comportamiento |
| **Esfuerzo** | ~1 sesión |
| **Modelo sugerido** | `scout` (brief) → Opus (código) → `worker` (tests y la corrida de la línea base) |
| **Cierra hallazgos** | ninguno — **habilita medir los demás** |

> Antes de empezar: leé `README.md` y `PROGRESS.md`. Re-localizá los símbolos con
> `graphify query`.

---

## Por qué

Las WAVEs 04 y 05 prometen reducir el contexto de **18.439 → ≤ 2.500 chars** y subir la
precisión del router de **4/7 → ≥ 9/10**. Sin instrumentación esas cifras no son verificables:
serían una afirmación, no un criterio de aceptación.

Hoy el sistema no reporta nada de lo que importa. Sabemos que el contexto pesa 15.516 chars
porque la auditoría lo midió **desde fuera**, con un script; en producción no queda rastro. No
hay forma de saber, tras un evento real, cuántos turnos cayeron al fallback, cuántos activaron
una skill local, ni cuánto tardó la primera palabra.

Esta WAVE es deliberadamente aburrida y va tercera **a propósito**: se instrumenta el sistema
*después* de arreglar los defectos que rompen la demo (WAVE-01, 02) y *antes* de tocar la
arquitectura de contexto (WAVE-04+), para que la línea base que se registre sea la del sistema
ya funcional. Medir un sistema roto produce una base engañosa.

---

## Precondiciones

```bash
git status --short                      # limpio
git log --oneline -1                    # WAVE-02 commiteada
.venv/bin/python -m pytest tests/ -q    # verde
```

---

## Alcance

### 1. Métricas por turno

Una línea estructurada por turno, en **ambas** rutas (voz/CLI y web/WebSocket):

| Campo | Significado | De dónde sale |
|---|---|---|
| `context_chars` | Tamaño del bloque de contexto institucional enviado | longitud de lo que `_build_messages` inyecta |
| `prompt_chars` | Tamaño total del prompt (todos los mensajes) | suma de los `content` de `messages` |
| `estimated_input_tokens` | `prompt_chars / 3.5`, redondeado | derivado — documentá el divisor |
| `local_skill_hit` | Nombre de la skill que respondió, o `None` | retorno de `route_local_skill` |
| `provider` / `model` | Backend y modelo realmente usados | `provider_config.resolve_model`, backend efectivo |
| `time_to_first_token_ms` | Del envío al primer token | ya hay un `t0` en `speak_streaming_from_llm`; reutilizalo |
| `time_to_first_clause_ms` | Del envío a la primera cláusula hablada | `pop_ready_speech` |
| `fallback_count` | Cuántos backends se intentaron antes del que respondió | bucle de `_candidate_backends` |
| `route` | `voice` \| `web` | quién llama |
| `event_mode` | Modo activo (`normal`/`judges`/`expo`/`admissions`) | `call.CURRENT_MODE` / `get_system_prompt` |

`estimated_input_tokens` es una **estimación** con el divisor 3,5 ch/token que usó la auditoría.
Etiquetala como estimación en el log; no la presentes como conteo real de tokens.

### 2. Un solo punto de emisión

Un helper único (p. ej. en `llm_backend.py` o un módulo `metrics` pequeño) al que llamen las dos
rutas. **No** dupliques el formateo en `call.py` y en `conversation.py`: la divergencia entre las
dos rutas es precisamente el problema que este plan viene a cerrar (ver WAVE-07).

### 3. Redacción de secretos

`main.py` ya tiene un mecanismo de redacción para su endpoint de configuración. Buscalo con
`graphify query "redacción de claves en la configuración"` y **reutilizalo**. Ninguna métrica
debe contener claves, ni el prompt completo, ni el contexto completo — sólo longitudes.

### 4. Activación

Flag `HOLOGRAM_METRICS=1` (default: activo; el volumen es de una línea por turno, y en un
kiosco eso es despreciable). Seguí el patrón de `_tts_stream_enabled()` para leer el flag.

### 5. La línea base — el entregable real de esta WAVE

Corré las **11 preguntas obligatorias** en las dos rutas y registrá la tabla en `PROGRESS.md`.
Estas son, verbatim:

```text
 1. ¿Cómo estás?
 2. ¿Qué significa UNEV?
 3. ¿Qué carreras ofrecen?
 4. ¿Cuánto dura Programación Web?
 5. ¿Y cuánto dura?            ← inmediatamente después de la 4
 6. ¿Dónde queda la UNEV?
 7. ¿Está aprobada por el CES?
 8. Háblame de la lluvia de peces.
 9. ¿Qué ves frente a ti?
10. ¿Cuál es el precio actual de algo que requiere internet?
11. Cuéntame un chiste.
```

Registrá por pregunta: `context_chars`, `estimated_input_tokens`, `local_skill_hit`,
`time_to_first_token_ms`, `fallback_count`. **Estas mismas 11 preguntas son el criterio de
aceptación de WAVE-05 y la semilla del dataset de WAVE-10.** No cambies el enunciado ni el
orden; la 5 sólo tiene sentido después de la 4.

Si correrlas contra el proveedor real implica coste, pedí autorización antes. Las métricas de
contexto (`context_chars`, `prompt_chars`, `local_skill_hit`) se pueden obtener **sin llamar al
LLM**, construyendo los mensajes y midiéndolos; hacé eso primero y marcá claramente qué
columnas son offline y cuáles requirieron una llamada real.

### Archivos
`llm_backend.py`, `call.py`, `app/services/conversation.py`, `main.py` (documentación de la
variable), más tests, más `PROGRESS.md`.

---

## Fuera de alcance

- **Cambiar** el contexto, el router o el prompt. Esta WAVE **observa**; no altera nada de lo
  que mide. Si al instrumentar descubrís algo mal, va a `PROGRESS.md`.
- Dashboards, exportación a Prometheus, persistencia en base de datos. Una línea de log
  estructurada es suficiente para este plan.
- Trazas distribuidas, OpenTelemetry, nuevas dependencias. Si creés que hace falta una
  dependencia, pará y preguntá (Puerta 0).
- Métricas de cámara y de STT → **WAVE-08** y fuera de plan respectivamente.

---

## Tests a añadir

Archivo: `tests/test_metrics.py` (nuevo).

| Caso | Qué prueba | Debe fallar sin el fix porque… |
|---|---|---|
| `test_metrica_emitida_una_vez_por_turno_ruta_web` | Un turno por `ConversationService` emite exactamente una línea de métrica. | Hoy no se emite ninguna. |
| `test_metrica_emitida_una_vez_por_turno_ruta_voz` | Ídem por la ruta síncrona. | Ídem. |
| `test_metrica_incluye_los_campos_obligatorios` | Los diez campos de la tabla están presentes. | Ídem. |
| `test_metrica_no_contiene_secretos` | Con claves falsas en el entorno, la línea no contiene ninguna. | Blindaje: es el riesgo real de una WAVE de logging. |
| `test_metrica_no_contiene_el_prompt_completo` | Sólo longitudes; el texto del contexto no aparece. | Un log de 18 KB por turno es inaceptable. |
| `test_fallback_count_refleja_los_intentos` | Dos backends fallidos y uno bueno → `fallback_count == 2`. | Ídem. |
| `test_flag_desactiva_las_metricas` | `HOLOGRAM_METRICS=0` → sin líneas. | Verifica el rollback. |

---

## Verificación

```bash
.venv/bin/python -m pytest tests/ -q
.venv/bin/python -m pytest tests/test_metrics.py -v
git stash && .venv/bin/python -m pytest tests/test_metrics.py -q ; git stash pop
.venv/bin/ruff check .

# Línea base offline (sin llamar al LLM, sin coste):
# construir los mensajes de las 11 preguntas y medirlos.
.venv/bin/python -c "
from skills.university import get_university_context
from skills.event_mode import get_system_prompt
from skills.router import route_local_skill
import llm_backend as L
qs = ['¿Cómo estás?','¿Qué significa UNEV?','¿Qué carreras ofrecen?',
      '¿Cuánto dura Programación Web?','¿Y cuánto dura?','¿Dónde queda la UNEV?',
      '¿Está aprobada por el CES?','Háblame de la lluvia de peces.',
      '¿Qué ves frente a ti?','¿Cuál es el precio actual de algo que requiere internet?',
      'Cuéntame un chiste.']
ctx = get_university_context(); sp = get_system_prompt('normal')
print(f'{\"pregunta\":52} {\"ctx\":>7} {\"prompt\":>7} {\"~tok\":>6}  skill')
for q in qs:
    msgs = L._build_messages(q, sp, ctx, None)
    total = sum(len(m.get('content') or '') for m in msgs)
    hit = route_local_skill(q)
    print(f'{q[:50]:52} {len(ctx):7} {total:7} {round(total/3.5):6}  {bool(hit)}')
"
```
La salida de ese último comando **es** la línea base. Pegala en `PROGRESS.md`.

---

## Criterios de aceptación

1. Una línea de métrica por turno en **ambas** rutas, con los diez campos.
2. Ninguna métrica contiene claves, prompts ni contexto completo — sólo longitudes y tiempos.
3. `fallback_count` refleja los intentos reales (verificado con backends simulados).
4. `HOLOGRAM_METRICS=0` silencia todo.
5. **Línea base de las 11 preguntas registrada en `PROGRESS.md`**, indicando por columna si el
   dato es offline o requirió llamada real.
6. `context_chars` de la línea base coincide con los **15.516 chars** medidos en la auditoría.
   Si no coincide, el contenido de `data/unev_info.json` cambió: anotá el nuevo valor como la
   base vigente y decilo en el handoff.
7. Comportamiento sin cambios: las pruebas previas pasan sin modificarse. **Si un test previo
   necesitó cambiar, esta WAVE se salió de su alcance.**

---

## Checklist pre-commit

El compartido de `README.md`, más:

```
[ ] Ningún test previo fue modificado  (git diff --stat tests/ → sólo archivos nuevos)
[ ] Formateo de métricas definido en UN solo sitio, usado por las dos rutas
[ ] Reutilizada la redacción de secretos que ya existe en main.py (no una nueva)
[ ] Línea base de las 11 preguntas pegada en PROGRESS.md, con marca offline/real
[ ] context_chars de la base = 15.516 (o el nuevo valor, justificado)
[ ] Sin dependencias nuevas  (git diff requirements*.txt pyproject.toml → vacío)
[ ] Ninguna llamada de pago hecha sin autorización explícita
```

---

## Commit

```
feat(obs): WAVE-03 instrumentar el turno y registrar la línea base

- métricas por turno en ambas rutas: context_chars, prompt_chars,
  estimated_input_tokens, local_skill_hit, provider/model,
  time_to_first_token_ms, time_to_first_clause_ms, fallback_count, route, event_mode
- un solo punto de emisión, compartido por la ruta de voz y la web
- redacción de secretos reutilizada de main.py; el log lleva longitudes, no contenido
- HOLOGRAM_METRICS=0 para desactivar
- línea base de las 11 preguntas obligatorias registrada en PROGRESS.md
Cierra: ninguno (habilita la verificación de WAVE-04/05)
Métrica: línea base establecida — contexto 15.516 chars, ~5.340 tokens de entrada

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

## Rollback

```bash
HOLOGRAM_METRICS=0     # inmediato
git revert <sha>       # definitivo
```
Riesgo de rollback casi nulo: la WAVE no cambia comportamiento.

---

## Handoff — volcar en `PROGRESS.md`

```markdown
### WAVE-03 — Instrumentación y línea base
- Commit: <sha> · Fecha: <YYYY-MM-DD>
- Archivos tocados: <...>
- Tests añadidos: tests/test_metrics.py::<casos>
- Dónde vive el emisor de métricas: <símbolo y archivo>
- Línea base de las 11 preguntas: <tabla completa>
- context_chars medido: <valor> (esperado 15.516)
- Columnas obtenidas offline vs con llamada real: <detalle>
- Criterios de aceptación: <1–7>
- Desvíos: <...>
- Hallazgos nuevos (NO arreglados): <...>
- Revisión humana: <OK, fecha>
```

Actualizá también la sección **Objetivos numéricos** de `PROGRESS.md` si algún valor base
resultó distinto del medido en la auditoría.

**Después: PARAR.** Acá termina la Fase 1. El sistema ya no se calla, no habla su razonamiento,
y ahora se puede medir. **Es un punto de entrega válido:** si no hay más tiempo, la demo
funciona. La Fase 2 es el rediseño y empieza con una decisión, no con código.
