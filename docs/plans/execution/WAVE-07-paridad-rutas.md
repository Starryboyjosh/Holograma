# WAVE-07 — Paridad de rutas y skills antes del LLM

| | |
|---|---|
| **Fase** | 2 · Contexto y memoria (cierre) |
| **Riesgo** | Medio |
| **Esfuerzo** | 1 sesión |
| **Modelo sugerido** | `scout` (brief obligatorio) → Opus (código) → `worker` (tests) |
| **Cierra hipótesis/hallazgos** | H5 · hallazgos H, L (cierre) |

> Antes de empezar: leé `README.md` y `PROGRESS.md`. Re-localizá los símbolos con
> `graphify query`. Las líneas de este documento son orientativas.

---

## Por qué

### H5 · Las skills locales sólo corren si el backend es `local_only`

`route_local_skill` se invoca en tres sitios, y **los tres están detrás de la misma condición**:

| Sitio | Guarda |
|---|---|
| `call.py::ask_ai` ≈L983 | `if get_selected_backend() == "local_only":` |
| `call.py::ask_ai_and_speak` ≈L1022 | `if get_selected_backend() == "local_only":` |
| `llm_backend.py::_local_only_reply` ≈L366 | sólo se llama desde ramas `backend == "local_only"` (≈L907, L939, L1092, L1111) |

```python
def ask_ai(user_input, mode=None):
    mode = mode or CURRENT_MODE

    if get_selected_backend() == "local_only":     # ← la única puerta
        local_response = route_local_skill(user_input)
        if local_response:
            return local_response

    return generate_reply(...)
```

La configuración real del equipo es `openrouter`. **Es decir: en producción las skills locales
no corren nunca.** Sólo aparecen como último recurso cuando ya se agotó la cadena de
proveedores — precisamente el caso más lento.

Lo que eso deja invisible, medido en `data/honduras_info.json`:

```
cultura_general: 970 entradas
```

**970 respuestas de cultura general hondureña, escritas y listas, que el sistema no usa** porque
el backend seleccionado no es `local_only`. Y lo mismo vale para las secciones UNEV que el router
sí acierta: hoy la respuesta correcta e instantánea existe, y el sistema prefiere pagar 200–800
ms de red y arriesgar una alucinación.

Con el router con umbral de WAVE-05, esto pasa de ser peligroso a ser la mejora de latencia más
barata del plan: **respuesta local con confianza alta = 0 tokens, 0 ms de red, 0 alucinaciones.**

### Hallazgo H · El modo de evento no llega a la ruta web

`llm_backend.py::stream_llm_response` ≈L1076:

```python
        system_prompt = get_system_prompt("normal")     # ← fijado a mano
```

Mientras tanto la ruta de voz sí tiene modos. `call.py` ≈L66:

```python
CURRENT_MODE = os.getenv("HOLOGRAM_MODE", "normal")
```

y `set_mode` (≈L1056–L1074) lo cambia en caliente a **`judges`**, **`expo`**, **`admissions`** o
`normal`, guardándolo en un **global de módulo de `call.py`** que la ruta web no consulta.

Consecuencia concreta: en una visita de jurado, el operador pone el modo `judges`, el holograma
por voz adopta el tono correcto, y **la misma pregunta hecha desde la interfaz web responde en
modo `normal`**. Dos personalidades en el mismo kiosco, en el mismo evento.

`skills/event_mode.py::get_system_prompt` (≈L8) además **no tiene ningún test** — está entre los
módulos de `skills/` con cobertura cero.

### Hallazgo L · Cierre de la paridad

WAVE-05 unificó el ensamblado del prompt. Falta lo demás: el corte pre-LLM, el modo de evento y
el camino `local_only` por WebSocket. Al terminar esta WAVE, **el mismo enunciado por CLI y por
`/ws/chat` debe producir la misma decisión** — y debe haber un test que lo demuestre, que es el
primer test de paridad real del repositorio.

---

## Precondiciones

```bash
git status --short                      # limpio
git log --oneline -1                    # WAVE-06 commiteada
.venv/bin/python -m pytest tests/ -q    # verde
```

**Dependencia dura con WAVE-05.** Sacar `route_local_skill` de detrás de la guarda de
`local_only` **sin el umbral de confianza sería una regresión grave**: hoy «Háblame de
Programación Web» devuelve vulgarismos hondureños, y ese texto pasaría a ser la respuesta final
del kiosco, sin LLM que lo suavice. Con el router de WAVE-05 y su umbral, es correcto. Verificá
antes de tocar nada:

```bash
.venv/bin/python -c "
from skills.router import route_local_skill
r = route_local_skill('Háblame de Programación Web')
print('PARAR: falta WAVE-05' if r and 'ulgarismo' in r else 'OK, WAVE-05 aplicada')
"
```

También WAVE-06, porque la resolución de referencias debe ocurrir **antes** del corte local: «¿y
cuánto dura?» tiene que expandirse antes de que el router decida responder sin LLM.

---

## Alcance

### 1. Skills locales en la tubería común, con umbral

Mover la consulta al router **fuera** de la guarda `local_only`, a un único punto compartido por
las dos rutas — el mismo sitio donde WAVE-05 ensambla el `PromptPackage`.

Reglas:

- **Sólo se corta el LLM por encima del umbral de confianza de WAVE-05.** Un umbral de corte
  puede ser *más alto* que el de selección de secciones: equivocarse eligiendo secciones cuesta
  tokens; equivocarse respondiendo directo cuesta una respuesta equivocada frente a un visitante.
  Si usás dos umbrales, documentá ambos en `PROGRESS.md`.
- Por debajo del umbral, la skill **no responde**: aporta secciones y el LLM contesta. El
  comportamiento por defecto sigue siendo el LLM.
- La respuesta local debe **atravesar el mismo camino de salida** que la del LLM: mismos eventos
  de broadcast, mismo TTS, mismos ganchos del orquestador del holograma. Una respuesta local que
  se salta `text_done` o el cierre de turno deja el holograma colgado — es el error más probable
  de esta WAVE.
- Debe registrarse en las métricas de WAVE-03 (`local_skill_hit`, y `provider` reflejando que no
  hubo llamada de red).

### 2. Modo de evento en las dos rutas

- El modo pasa a estar **accesible desde ambas rutas**, en lugar de vivir sólo en el global
  `CURRENT_MODE` de `call.py`.
- `stream_llm_response` deja de fijar `"normal"` a mano y recibe el modo real (parámetro
  **opcional con default**, para no romper llamadores ni tests).
- `set_mode` sigue funcionando por voz, y su efecto se ve **también** en la ruta web.
- Los cuatro modos existentes (`normal`, `judges`, `expo`, `admissions`) se conservan tal cual.
  No inventes modos nuevos ni cambies los textos de `skills/event_mode.py`.

Si el modo termina expuesto por API o WebSocket, tratalo como una **entrada validada**: sólo los
cuatro valores conocidos, con fallback a `normal` ante cualquier otro. Es un endpoint que cambia
la personalidad del kiosco en vivo.

### 3. `local_only` por WebSocket, sin recorrer la cadena

Cuando el backend seleccionado es `local_only`, la ruta web debe cortar **antes** de intentar
proveedores. Hoy llega ahí por `_local_only_reply` al final de `stream_llm_response`, después de
haber recorrido la cadena.

### 4. Test de paridad

El entregable conceptual de esta WAVE: mismo enunciado por la ruta síncrona y por
`ConversationService.handle_prompt` → **mismas secciones, mismo modo, misma decisión de cortar o
no, misma respuesta**. Sin red, con el LLM sustituido por un doble.

### Archivos
`call.py`, `llm_backend.py`, `app/services/conversation.py`, `app/services/llm.py`, el
ensamblador de WAVE-05, `main.py`, más tests.

---

## Fuera de alcance

- **Cambiar el contenido de las skills o de `event_mode.py`.** Acá se cambia *cuándo* se
  consultan, no *qué* dicen.
- **Tocar el router.** Umbral y aciertos son de WAVE-05. Si al exponer las skills descubrís
  falsos positivos nuevos, **anotalos en `PROGRESS.md`** — no los parchees acá (regla 6).
- La política de cámara → **WAVE-08**.
- Modelo, `max_tokens`, temperatura, fast-fail de conectividad → **WAVE-09**.
- El dataset completo y los primeros tests exhaustivos de `skills/` → **WAVE-10**. Acá se añade
  el primer test de `event_mode.py`, no su cobertura completa.
- **Refactor de `call.py`.** Es enorme y tiene globals de módulo por todas partes. La tentación
  de "arreglarlo mientras estoy acá" es real: resistila. La reorganización de carpetas está
  diferida por decisión explícita del proyecto.
- Unificar `CURRENT_MODE` con la configuración del holograma o con `HologramConfigStore`. Acá
  sólo se lo hace legible desde las dos rutas.

---

## Tests a añadir

Archivo: `tests/test_route_parity.py` (nuevo).

| Caso | Qué prueba | Debe fallar sin el fix porque… |
|---|---|---|
| `test_skill_local_corre_con_backend_cloud` | Con `openrouter` seleccionado y confianza alta, se responde local **sin** llamar al doble del LLM. | Hoy la guarda `local_only` lo impide. **Es H5.** |
| `test_cultura_general_accesible_en_cloud` | Una de las 970 entradas responde con backend cloud. | Idem: 970 respuestas invisibles. |
| `test_bajo_umbral_va_al_llm` | Confianza baja → se llama al LLM. | Guardarraíl: el default sigue siendo el LLM. |
| `test_respuesta_local_emite_eventos_completos` | La respuesta local emite los mismos broadcasts/cierre de turno que la del LLM (incluido `text_done`). | Es la forma en que esta WAVE deja el holograma colgado. |
| `test_modo_evento_llega_a_ruta_web` | Con modo `judges`, el prompt de la ruta web **no** es el de `normal`. | `get_system_prompt("normal")` está fijado a mano en ≈L1076. **Es el hallazgo H.** |
| `test_los_cuatro_modos` | `normal`, `judges`, `expo`, `admissions` producen cuatro prompts distintos por ambas rutas. | Primer test de `skills/event_mode.py`. |
| `test_modo_invalido_cae_en_normal` | Un modo desconocido no propaga basura al prompt. | Validación de entrada. |
| `test_local_only_por_websocket_no_recorre_cadena` | Con `local_only`, cero intentos de proveedor. | Hoy llega al final de la cadena. |
| `test_paridad_cli_vs_web` | Parametrizado sobre las 11 preguntas: mismas secciones, mismo modo, misma decisión. | **No existe ningún test de paridad hoy.** |

`test_respuesta_local_emite_eventos_completos` merece atención: un corte pre-LLM que se salta el
camino de salida deja al holograma esperando un `finish_turn` que nunca llega, y eso **no se ve
en un test de contenido**. Escribilo mirando qué hace `handle_prompt` en su camino normal.

---

## Verificación

```bash
.venv/bin/python -m pytest tests/ -q
.venv/bin/python -m pytest tests/test_route_parity.py -v
git stash && .venv/bin/python -m pytest tests/test_route_parity.py -q ; git stash pop
.venv/bin/ruff check .

# H5: la skill local debe correr con backend cloud
.venv/bin/python -c "
from llm_backend import get_selected_backend
print('backend seleccionado:', get_selected_backend())
"

# El modo de evento, visible desde las dos rutas (adaptá al símbolo real)
.venv/bin/python -c "
from skills.event_mode import get_system_prompt
for m in ('normal','judges','expo','admissions'):
    print(f'{m:12} {len(get_system_prompt(m)):5} chars')
"
```

**Prueba manual obligatoria:**

1. Con `openrouter` activo, preguntá algo de `cultura_general` por voz **y** por web: debe
   responder rápido, sin latencia de red, y con el texto local.
2. Poné modo `judges` por voz y hacé la misma pregunta desde la web: **el tono debe cambiar en
   las dos**.
3. Comprobá que tras una respuesta local el holograma vuelve a `idle` y no queda hablando ni
   colgado.

El paso 3 es el que ningún test cubre bien. Anotá los tres resultados.

---

## Criterios de aceptación

1. Con backend cloud y confianza alta, la skill local responde **sin** llamada al LLM.
2. Las 970 entradas de `cultura_general` son accesibles con cualquier backend.
3. Bajo el umbral, la respuesta sigue viniendo del LLM: el default no cambió.
4. La respuesta local recorre el mismo camino de salida (broadcasts, TTS, cierre de turno) que la
   del LLM; el holograma vuelve a `idle`.
5. `stream_llm_response` **ya no** contiene `get_system_prompt("normal")` fijado a mano.
6. Los cuatro modos producen prompts distintos **en las dos rutas**; un modo inválido cae en
   `normal`.
7. Con `local_only`, la ruta web corta sin intentar proveedores.
8. `test_paridad_cli_vs_web` verde sobre las 11 preguntas.
9. Métrica de WAVE-03: `local_skill_hit` refleja los cortes locales; la latencia de esos turnos
   es órdenes de magnitud menor. Número pegado.
10. Las 3 pruebas manuales hechas y anotadas.
11. Las pruebas previas pasan. **Si un test previo necesitó cambiar, esta WAVE se salió de su
    alcance** — salvo el ajuste de firma con default, que no debería requerir cambios.

---

## Checklist pre-commit

El compartido de `README.md`, más:

```
[ ] Precondición WAVE-05 verificada (el chequeo de «Háblame de…» impreso arriba)
[ ] Skill local corre con backend cloud, y bajo el umbral sigue yendo al LLM
[ ] Respuesta local emite el camino de salida completo; holograma vuelve a idle (manual)
[ ] grep de get_system_prompt("normal") en llm_backend.py → sin resultados
[ ] Los cuatro modos verificados en AMBAS rutas
[ ] Modo tratado como entrada validada (sólo los 4 valores conocidos)
[ ] Test de paridad CLI vs web verde sobre las 11 preguntas
[ ] Router NO modificado (git diff --stat sin skills/router.py)
[ ] event_mode.py NO modificado en contenido (sólo se lo empieza a testear)
[ ] Firmas nuevas con default: llamadores y dobles de test intactos
[ ] Sin refactor oportunista de call.py (revisá el diff línea por línea)
[ ] Las 3 pruebas manuales hechas
[ ] Umbral(es) de corte documentados en PROGRESS.md
```

---

## Commit

```
fix(context): WAVE-07 paridad de rutas y skills locales antes del LLM

- route_local_skill sale de detrás de la guarda local_only y pasa a la tubería
  común, con corte sólo por encima del umbral de confianza de WAVE-05: las 970
  entradas de cultura_general y las secciones UNEV dejan de ser invisibles con
  los backends cloud
- la respuesta local recorre el mismo camino de salida que la del LLM
  (broadcasts, TTS y cierre de turno del holograma)
- el modo de evento real llega a la ruta web: stream_llm_response deja de fijar
  get_system_prompt("normal") a mano, y los cuatro modos se comportan igual por
  voz y por WebSocket
- local_only por WebSocket corta sin recorrer la cadena de proveedores
- primer test de paridad CLI/web del repositorio, y primer test de event_mode.py
Cierra: hipótesis 5; hallazgos H, L
Métrica: turnos resueltos localmente <n>/11; latencia de esos turnos <antes> → <después>

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

## Rollback

```bash
HOLOGRAM_LOCAL_SKILLS_FIRST=0    # las skills vuelven a correr sólo con local_only
```
El modo de evento en la ruta web **no** necesita flag: es una corrección de un valor fijado a
mano, sin comportamiento nuevo que apagar.

```bash
git revert <sha>
```

---

## Handoff — volcar en `PROGRESS.md`

```markdown
### WAVE-07 — Paridad de rutas y skills pre-LLM
- Commit: <sha> · Fecha: <YYYY-MM-DD>
- Archivos tocados: <...>
- Tests añadidos: tests/test_route_parity.py::<casos>
- Umbral de selección de secciones: <n> · umbral de CORTE pre-LLM: <n> · por qué: <...>
- Dónde vive el punto único de decisión: <módulo y símbolo>
- Cómo viaja el modo de evento a la ruta web: <...>
- Turnos de las 11 resueltos localmente: <n> · latencia: <antes> → <después>
- Pruebas manuales:
  1. cultura_general con backend cloud (voz y web): <...>
  2. modo judges visible en las dos rutas: <...>
  3. holograma vuelve a idle tras respuesta local: <...>
- Criterios de aceptación: <1–11>
- Desvíos: <...>
- Hallazgos nuevos (NO arreglados): <...>
- Revisión humana: <OK, fecha>
```

**Después: PARAR.** Acá cierra la Fase 2 y con ella el núcleo del plan: contexto selectivo,
memoria y una sola tubería para las dos rutas. Volvé a pasar las 11 preguntas por **ambas** rutas
y dejá la tabla en `PROGRESS.md`. La Fase 3 es endurecimiento: valiosa, pero ya no es lo que
rompe la demo.
