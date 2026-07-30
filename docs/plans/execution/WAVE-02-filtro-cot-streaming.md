# WAVE-02 — Filtro de razonamiento en streaming

| | |
|---|---|
| **Fase** | 1 · Desbloquear la demo |
| **Riesgo** | Medio — toca el camino por el que pasa **todo** el texto hablado y difundido |
| **Esfuerzo** | ~1 sesión |
| **Modelo sugerido** | `scout` (brief) → Opus (código) → `worker` (tests) |
| **Cierra hallazgos** | D |

> Antes de empezar: leé `README.md` y `PROGRESS.md`. Re-localizá los símbolos con
> `graphify query`. **Las líneas son orientativas; los símbolos son la verdad.**

---

## Por qué (hallazgo D)

**El holograma lee en voz alta su propio razonamiento.** Reproducido en la auditoría: con el
modelo de razonamiento configurado, Piper diría literalmente

```
1. <think>El usuario pregunta por la duracion de Programacion Web.
2. Segun el contexto son 2 anos.
3. Debo responder breve.</think>La carrera de Programacion Web dura 2 anos.
```

La causa es que la limpieza es **por bloque completo** mientras el consumo es **por cláusula
parcial**. Tres piezas conspiran:

### 1. `call.clean_for_tts` (≈L114) sólo reconoce bloques cerrados y un solo tag

```python
    clean_text = re.sub(
        r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE
    )
```

Dos limitaciones:
- Exige `<think>` **y** `</think>` en el mismo string. Una cláusula suelta como
  `<think>El usuario pregunta por la duración.` no coincide y pasa entera al TTS.
- Cubre sólo el literal `think`. `_strip_qwen_thinking` (≈L505) ya cubre
  `think|thinking|reasoning|analysis|scratchpad` con espacios opcionales
  (`<\s*/?\s*tag\s*>`). Los otros cuatro tags no se filtran nunca en streaming.

### 2. El bucle de voz limpia **después** de cortar

En `call.speak_streaming_from_llm` (≈L779):

```python
            ready, speech_buf, first = pop_ready_speech(speech_buf, first)
            for piece in ready:
                piece = clean_for_tts(piece)
```

`pop_ready_speech` corta por puntuación. El punto de `«El usuario pregunta por la duración.»`
—que está **dentro** del `<think>`— es un corte válido, así que la cláusula sale del buffer con
el `<think>` abierto y sin cierre. `clean_for_tts` no puede hacer nada con eso: le llega un
fragmento, no un bloque.

Además, `on_text(token)` recibe el token **crudo**, antes de cualquier limpieza.

### 3. La ruta web no limpia en absoluto

En `app/services/conversation.py`, `handle_prompt` (≈L139) difunde el chunk tal cual:

```python
                    await self._conn.broadcast(
                        {
                            "type": "text_chunk",
                            "text": chunk,
                        }
                    )
```
y alimenta el TTS con el mismo chunk sin pasar por `clean_for_tts`:
```python
                    speech_buf += chunk
                    ready, speech_buf, first_speech = pop_ready_speech(
                        speech_buf,
                        first_speech,
                    )
```
La pantalla muestra el razonamiento y Piper lo habla.

### 4. La red de seguridad llega tarde

`_postprocess_reply` (definido en `llm_backend.py`, importado en `call.py` ≈L785) se aplica al
texto completo **al final** de `speak_streaming_from_llm` (≈L856): después de que el audio ya
sonó. Limpia el valor devuelto, no lo que el visitante escuchó.

### La pieza que ya existe y hay que reutilizar

`_CotStreamMirror` (≈L562) **ya resuelve el problema difícil**: mantiene `in_think` entre
chunks y guarda una cola de 24 chars para no partir una etiqueta a la mitad
(`_CotStreamMirror.feed`, ≈L622). Ese es el algoritmo correcto.

Pero **está acoplado al logging** y por eso no sirve tal cual:

```python
        if not _cot_log_enabled():
            # Seguimos contando por si alguien habilita el log a mitad de turno.
            self.answer_chars += len(text)
            return
```

Con `LLM_LOG_COT=0` —el valor real del `.env` del equipo— la máquina de estados **no corre**.
El trabajo de esta WAVE es extraer ese algoritmo a un filtro independiente del logging, no
reinventarlo.

---

## Precondiciones

```bash
git status --short                      # limpio
git log --oneline -1                    # WAVE-01 commiteada
.venv/bin/python -m pytest tests/ -q    # verde
```

WAVE-01 primero: sin ella, un turno que consume el presupuesto razonando ni siquiera llega a
producir texto que filtrar.

---

## Alcance

### 1. Filtro incremental con estado — pieza nueva, algoritmo prestado

Un objeto con estado por turno, en `llm_backend.py` (junto a `_strip_qwen_thinking`, que
comparte el juego de tags):

- `feed(text) -> str`: devuelve **sólo** el texto visible, tragándose lo que está dentro de un
  bloque de razonamiento.
- `flush() -> str`: devuelve lo que quede retenido en la cola al terminar el stream.
- Reglas: reutilizá los `_OPEN_RE` / `_CLOSE_RE` de `_CotStreamMirror` (o extraelos a
  constantes de módulo compartidas — mejor, una sola definición del juego de tags). Mantené la
  cola de 24 chars para no cortar etiquetas entre chunks. **Independiente de
  `_cot_log_enabled()`.**
- Un tag de apertura sin cierre al final del stream: descartá lo retenido. Es razonamiento
  truncado, no respuesta.
- Texto sin ningún tag: sale **byte a byte idéntico**. Este es el criterio de aceptación más
  importante; una regresión acá degrada todas las respuestas normales.

### 2. Aplicarlo en el origen, no en cada consumidor

Filtrá en los generadores de `llm_backend` —`_iter_openai_compatible_tokens` (≈L846) y
`_stream_backend_response` (≈L972)— de modo que **ambas rutas** reciban tokens ya limpios y
`ConversationService` no necesite saber nada de tags.

Cuidado: `_CotStreamMirror` debe seguir recibiendo el texto **crudo** para que el log de
diagnóstico siga sirviendo. Filtro y espejo son dos consumidores del mismo chunk; el orden
importa: espejo primero (crudo), filtro después (lo que se emite).

Un chunk que queda vacío tras filtrar **no se cede**, pero tampoco cuenta como "stream vacío"
para el `produced` de WAVE-01 mientras el filtro sí haya visto texto. Cuidá esta interacción:
un turno enteramente de razonamiento debe caer al fallback, no colgarse.

### 3. Ampliar `clean_for_tts` como red de seguridad

`call.clean_for_tts` se queda —protege también las llamadas no-streaming— pero pasa a usar el
mismo juego de tags que `_strip_qwen_thinking` (los cinco, con espacios opcionales, y también
etiquetas sueltas sin cerrar). **No** dupliques el regex: importá o compartí la definición.

### 4. Flag de rollback

`HOLOGRAM_COT_FILTER=0` desactiva el filtro nuevo y restaura el comportamiento anterior.
Seguí el patrón de `_tts_stream_enabled()` en `app/services/conversation.py` (≈L35), que ya
resuelve la lectura de flags booleanos con el juego `("0","false","no","off")`.

### Archivos
`llm_backend.py`, `call.py`, `app/services/conversation.py` (sólo si el filtro en origen no
alcanza — justificalo), más los tests.

---

## Fuera de alcance

- Cambiar de modelo para no tener razonamiento → **WAVE-09** (decisión D2).
- `max_tokens` / `temperature` → WAVE-01 (ya hecho) y **WAVE-09**.
- Tamaño o composición del contexto → **WAVE-04/05**.
- Memoria conversacional → **WAVE-06**.
- El `get_system_prompt("normal")` hardcodeado en `stream_llm_response` → **WAVE-07**.
- Rediseñar `pop_ready_speech` o la política de corte de cláusulas. El filtro va **antes**;
  el cortador no se toca.
- Nada de ElevenLabs. **Piper sigue siendo el TTS.**

---

## Tests a añadir

Archivo: `tests/test_cot_filter.py` (nuevo).

| Caso | Qué prueba | Debe fallar sin el fix porque… |
|---|---|---|
| `test_bloque_partido_entre_chunks_no_se_emite` | Alimentar `["<thi", "nk>razono", " mucho</thi", "nk>La respuesta."]` → sale exactamente `"La respuesta."` | Hoy nada mantiene estado entre chunks: sale el razonamiento. |
| `test_clausula_con_think_abierto_no_llega_al_tts` | Reproducir el escenario del hallazgo: cláusulas cortadas por `pop_ready_speech` dentro del `<think>`. Ninguna pieza hablada contiene `<think>` ni su texto. | `clean_for_tts` exige bloque cerrado: hoy lo habla. |
| `test_texto_sin_tags_pasa_intacto` | Respuesta normal → salida **idéntica byte a byte**, incluidos espacios. | Blindaje contra regresión (el riesgo real de esta WAVE). |
| `test_los_cinco_tags_se_filtran` | `think`, `thinking`, `reasoning`, `analysis`, `scratchpad`, con espacios (`< think >`) y mayúsculas. | Hoy `clean_for_tts` sólo conoce `<think>`. |
| `test_tag_abierto_sin_cerrar_al_final_se_descarta` | Stream que termina dentro del razonamiento → salida vacía, sin excepción. | Hoy emite el razonamiento entero. |
| `test_filtro_funciona_con_LLM_LOG_COT_apagado` | Con `LLM_LOG_COT=0`, el filtro sigue filtrando. | El `in_think` de `_CotStreamMirror` se apaga con el log; un filtro que herede ese acoplamiento falla acá. |
| `test_flag_desactiva_el_filtro` | `HOLOGRAM_COT_FILTER=0` → pasa todo sin filtrar. | Verifica que el rollback existe y funciona. |
| `test_ruta_web_difunde_texto_limpio` | `ConversationService.handle_prompt` con un LLM falso que cede tags → ningún `text_chunk` contiene tags. | Hoy difunde el chunk crudo. |

Para el último caso, seguí los dobles que ya usa `tests/test_app_services.py` en lugar de
escribir mocks nuevos.

---

## Verificación

```bash
.venv/bin/python -m pytest tests/ -q
.venv/bin/python -m pytest tests/test_cot_filter.py -v

# Debe fallar sin el fix
git stash && .venv/bin/python -m pytest tests/test_cot_filter.py -q ; git stash pop

.venv/bin/ruff check .

# Simulación manual del hallazgo D — sin red, sin API
.venv/bin/python -c "
from utils import pop_ready_speech
raw = ('<think>El usuario pregunta por la duracion de Programacion Web. '
       'Segun el contexto son 2 anos. Debo responder breve.</think>'
       'La carrera de Programacion Web dura 2 anos.')
buf, first, spoken = '', True, []
for ch in raw:                      # simula chunks de 1 char (peor caso)
    buf += ch
    ready, buf, first = pop_ready_speech(buf, first)
    spoken += ready
spoken.append(buf)
for i, p in enumerate(spoken, 1):
    print(i, repr(p))
"
```
Ese último comando muestra el defecto **antes** del fix (cláusulas con CoT) y debe mostrar sólo
texto visible **después**, una vez que el filtro se interpone. Pegá ambas salidas como
evidencia: es la prueba más legible de esta WAVE.

Prueba de humo con voz, si hay audio disponible: una pregunta real por CLI y una por
`/ws/chat`. Escuchá. Ninguna palabra de razonamiento.

---

## Criterios de aceptación

1. Con el escenario del hallazgo D, **cero** cláusulas habladas contienen razonamiento, y cero
   eventos `text_chunk` lo contienen.
2. Una respuesta sin tags sale **byte a byte idéntica** a la entrada. (Test de identidad verde.)
3. Los cinco tags se filtran, con espacios y en cualquier caja.
4. Un bloque partido entre chunks arbitrarios se filtra igual (probado con chunks de 1 char).
5. El filtro funciona con `LLM_LOG_COT=0`.
6. `HOLOGRAM_COT_FILTER=0` restaura el comportamiento anterior.
7. Un turno enteramente de razonamiento **no** cuelga: cae al fallback de WAVE-01.
8. Las pruebas previas siguen pasando.

---

## Checklist pre-commit

El compartido de `README.md`, más:

```
[ ] Test de identidad byte-a-byte presente y verde  ← el blindaje contra regresión
[ ] El juego de tags está definido UNA sola vez  (grep -c 'scratchpad' llm_backend.py call.py
    → sin definiciones duplicadas del regex)
[ ] _CotStreamMirror sigue recibiendo texto crudo (el log de diagnóstico no se degradó)
[ ] Verificada la interacción con el `produced` de WAVE-01: turno todo-razonamiento
    cae al fallback y no cuelga
[ ] pop_ready_speech NO fue modificado  (git diff utils.py → vacío)
[ ] Salidas del simulador del hallazgo D pegadas: antes y después
[ ] Prueba de humo con audio hecha, o anotada como no hecha y por qué
```

---

## Commit

```
fix(tts): WAVE-02 filtrar razonamiento en streaming antes de hablar y difundir

- filtro incremental con estado en llm_backend, con el algoritmo in_think de
  _CotStreamMirror extraído e independiente de LLM_LOG_COT
- se aplica en el origen del stream: voz y web reciben tokens ya limpios
- clean_for_tts pasa al juego completo de tags de _strip_qwen_thinking
  (think|thinking|reasoning|analysis|scratchpad), incluidas etiquetas sueltas
- rollback con HOLOGRAM_COT_FILTER=0
- tests/test_cot_filter.py: bloque partido entre chunks, identidad byte a byte,
  los cinco tags, LLM_LOG_COT=0 y difusión web limpia
Cierra: hallazgo D
Métrica: cláusulas con CoT habladas: posible → 0

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

## Rollback

```bash
# Inmediato, sin desplegar código:
HOLOGRAM_COT_FILTER=0

# Definitivo:
git revert <sha>
```

---

## Handoff — volcar en `PROGRESS.md`

```markdown
### WAVE-02 — Filtro de razonamiento en streaming
- Commit: <sha> · Fecha: <YYYY-MM-DD>
- Archivos tocados: <...>
- Tests añadidos: tests/test_cot_filter.py::<casos>
- Dónde quedó el filtro: <símbolo y archivo>
- ¿Hizo falta tocar conversation.py? <sí/no, por qué>
- Métricas antes → después: cláusulas con CoT habladas: posible → 0
- Prueba de humo con audio: <hecha / no, por qué>
- Criterios de aceptación: <1–8>
- Desvíos: <...>
- Hallazgos nuevos (NO arreglados): <...>
- Revisión humana: <OK, fecha>
```

**Después: PARAR.**
