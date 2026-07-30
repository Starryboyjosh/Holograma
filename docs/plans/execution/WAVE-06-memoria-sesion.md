# WAVE-06 — Memoria de sesión y preguntas de seguimiento

| | |
|---|---|
| **Fase** | 2 · Contexto y memoria |
| **Riesgo** | Medio-alto — toca estado compartido en un proceso de kiosco |
| **Esfuerzo** | 1 sesión |
| **Modelo sugerido** | `scout` (brief obligatorio) → Opus (código) → `worker` (tests) |
| **Cierra hallazgos** | A, O |

> Antes de empezar: leé `README.md` y `PROGRESS.md`. Re-localizá los símbolos con
> `graphify query`. Las líneas de este documento son orientativas.

---

## Por qué

### Hallazgo A · No hay historial en ninguna de las dos rutas

Ningún punto de la cadena acepta turnos anteriores. Verificado firma por firma:

| Símbolo | Archivo | Firma actual |
|---|---|---|
| `_build_messages` | `llm_backend.py` ≈L395 | `(user_input, system_prompt, university_context, camera_context=None)` |
| `iter_reply_tokens` | `llm_backend.py` ≈L898 | idem |
| `generate_reply` | `llm_backend.py` ≈L944 | idem |
| `stream_llm_response` | `llm_backend.py` ≈L1063 | `(prompt, camera_context=None)` |
| `LLMService.stream` | `app/services/llm.py` | `(prompt, camera_context=None)` |
| `_LLM.stream` (Protocol) | `app/services/conversation.py` ≈L45 | `(prompt, camera_context=None)` |

**No hay un solo parámetro de historial en todo el camino.** Cada turno es el primero. La
consecuencia se mide con la pregunta 5 de las 11 obligatorias:

```
«¿Cuánto dura Programación Web?»   → 2 años.        ✅
«¿Y cuánto dura?»                  → router: None; el LLM no sabe de qué.  ❌
```

Un visitante frente a un holograma **no repite el nombre completo de la carrera en cada
pregunta**. Es el patrón conversacional más frecuente de un kiosco, y hoy no existe.

### Hallazgo O · El modelo de concurrencia obliga a un diseño concreto

Éste es el punto que hay que entender antes de escribir una línea. En `main.py` ≈L316:

```python
conversation = ConversationService(
    LLMService(stream_fn=stream_llm_response),
    connection=manager,          # ← un ConnectionManager que difunde a TODOS los clientes
    camera=camera_provider,
    ...
)
```

**Hay un único `ConversationService` a nivel de módulo**, y su `_conn.broadcast(...)` (usado en
una docena de sitios de `handle_prompt`, ≈L139–L331) va a **todos** los sockets conectados. Esto
no es un servidor multiusuario: es un kiosco donde varias pantallas ven la misma conversación.

De ahí salen dos reglas **no negociables**:

1. **La memoria NO puede ser por socket.** Aislar por conexión rompe el modelo de kiosco: la
   tablet del operador y la pantalla del holograma dejarían de compartir el hilo. Además una
   reconexión perdería el contexto en mitad de una charla.
2. **La memoria NO puede ser global-para-siempre.** Sin expiración, el visitante nº 2 hereda las
   preguntas del visitante nº 1 — y el modelo responde con la carrera de otra persona. Eso es
   peor que no tener memoria.

La única forma correcta es **ámbito de dispositivo/sesión con expiración por inactividad**: el
estado vive mientras alguien está conversando, y se descarta solo cuando el kiosco queda en
silencio.

---

## Precondiciones

```bash
git status --short                      # limpio
git log --oneline -1                    # WAVE-05 commiteada
.venv/bin/python -m pytest tests/ -q    # verde
```

**Dependencia dura con WAVE-05.** El test de aceptación de esta WAVE arranca con «Háblame de
Programación Web», y hasta WAVE-05 esa frase cae en el falso positivo de `"habla"` y devuelve
vulgarismos hondureños. **Si WAVE-05 no está commiteada, este test no puede pasar y no es culpa
de tu código.** Verificalo antes de empezar:

```bash
.venv/bin/python -c "
from skills.router import route_local_skill
r = route_local_skill('Háblame de Programación Web')
print((r or 'None')[:70])
print('OK, WAVE-05 aplicada' if not r or 'ulgarismo' not in r else 'PARAR: falta WAVE-05')
"
```

También hace falta **WAVE-05** para que la entidad activa se traduzca en secciones: la memoria
guarda «Programación Web», el `PromptPackage` es quien la convierte en contexto.

---

## Alcance

### 1. Estado de conversación

Una estructura con lo mínimo que resuelve el follow-up:

- **Entidad activa**: última carrera/tema del que se habló, con el momento en que se fijó.
- **Últimos N turnos** (pregunta + respuesta, recortadas). Empezá con **N = 3** y dejalo
  configurable; el coste de tokens de esta WAVE debe medirse contra el presupuesto que ganó
  WAVE-05, no gastárselo entero.
- **Marca de tiempo de la última actividad**, para la expiración.
- **TTL de inactividad configurable**; punto de partida razonable: **3 minutos**, la escala de
  una conversación de feria. Anotalo en `PROGRESS.md` como el valor elegido y por qué.

Almacenamiento **en memoria del proceso**. Sin base de datos, sin fichero, sin dependencias
nuevas: los datos de un visitante no deben sobrevivir al proceso — es una propiedad deseable,
no una limitación.

### 2. Ámbito: dispositivo/sesión, no socket

Una clave de sesión asociada al kiosco, **no** al objeto de conexión. Compartida por todos los
clientes conectados y por la ruta de voz. Una reconexión de WebSocket **no** debe reiniciar la
memoria; un silencio mayor al TTL **sí**.

**Reset explícito** además del TTL, por dos motivos reales: el operador que empieza con un
visitante nuevo, y el cambio de tema detectado. Expuesto de forma que el frontend pueda
dispararlo, y ejecutado también cuando el evento pasa a otro modo.

### 3. Resolución de referencias

Cuando la pregunta contiene una referencia sin antecedente («¿y cuánto dura?», «¿cuánto
cuesta?», «¿dónde se estudia?»), se resuelve con la entidad activa **antes** de enrutar, para
que el router de WAVE-05 vea una consulta completa.

- Determinista, siguiendo la disciplina de WAVE-05: sin llamada de red para resolver un
  pronombre.
- **Cambio de tema limpia la entidad**: si la nueva pregunta nombra otra carrera u otro dominio,
  la entidad anterior se reemplaza. Una entidad rancia que se cuela en una pregunta nueva
  produce una respuesta segura de contenido equivocado — el peor modo de fallo posible.
- Si no hay entidad activa, el comportamiento es **el de hoy**: no inventes un antecedente.

### 4. Enhebrar el historial por las dos rutas

Añadir un parámetro de historial —**opcional, con default vacío**— a los seis símbolos de la
tabla del hallazgo A, y pasarlo hasta `_build_messages`, donde se convierte en mensajes
`user`/`assistant` **entre** los mensajes de sistema y la pregunta actual.

Que sea opcional con default vacío es lo que mantiene compatibles a los llamadores existentes y
a los tests (`FakeLLM` en `tests/test_app_services.py` ≈L47 implementa el Protocol; si cambiás
la firma sin default, lo rompés).

Al añadirlo al Protocol `_LLM` (≈L44), recordá que hay **implementaciones falsas en los tests**
además de `LLMService`. La forma de mantenerlas válidas es el default.

### Archivos
Módulo nuevo para el estado (sugerido bajo `app/services/`), `app/services/conversation.py`,
`app/services/llm.py`, `llm_backend.py`, `call.py`, el ensamblador de WAVE-05, `main.py`, más
tests.

---

## Fuera de alcance

- **Persistencia entre reinicios.** Nada de SQLite, JSON ni Redis. El estado muere con el
  proceso, a propósito.
- **Perfiles o identificación de visitantes.** No se guarda quién preguntó, no hay
  reconocimiento facial ligado a la memoria, no hay analítica por persona. Un kiosco en un
  campus con visitantes que no consintieron nada: la memoria es de la conversación, no de la
  persona.
- **Resumen del historial con el LLM.** Recorte por N turnos, no una llamada extra.
- **Memoria de largo plazo, RAG conversacional, embeddings.**
- El falso positivo de `"habla"` → **WAVE-05** (precondición, no trabajo de acá).
- La paridad completa CLI/web y el modo de evento → **WAVE-07**.
- La frescura del contexto de cámara → **WAVE-08**. La entidad activa es textual; no guardes
  descripciones de la cámara en la memoria conversacional: caducan en segundos y su política es
  otra WAVE.
- `max_tokens` — si el historial aprieta el presupuesto, **anotalo**, no lo subas acá →
  **WAVE-09**.

---

## Tests a añadir

Archivo: `tests/test_session_memory.py` (nuevo).

| Caso | Qué prueba | Debe fallar sin el fix porque… |
|---|---|---|
| `test_followup_duracion_ruta_voz` | «Háblame de Programación Web» → «¿Y cuánto dura?» responde **2 años** por la ruta síncrona. | No hay historial ni entidad activa. **Es el criterio de aceptación.** |
| `test_followup_duracion_ruta_web` | Lo mismo por `ConversationService.handle_prompt`. | Idem, y prueba que ambas rutas comparten el estado. |
| `test_cambio_de_tema_limpia_entidad` | Tras «Programación Web», preguntar por Enfermería no arrastra la anterior. | Sin lógica de reemplazo, la entidad rancia contamina. |
| `test_expiracion_por_inactividad` | Con el reloj adelantado más allá del TTL, la entidad se descarta. | Sin TTL, el visitante 2 hereda al visitante 1. **El test de privacidad.** |
| `test_reset_explicito` | El reset borra entidad e historial. | No existe. |
| `test_memoria_no_es_por_socket` | Dos conexiones simuladas ven la misma conversación; la reconexión no pierde el contexto. | Guardarraíl contra el error de diseño más tentador. |
| `test_historial_acotado_a_n_turnos` | Con 10 turnos, sólo van N al prompt. | Sin tope, el prompt crece sin límite y devuelve el problema que WAVE-05 acaba de resolver. |
| `test_sin_entidad_comportamiento_actual` | «¿Y cuánto dura?» como **primera** pregunta se comporta como hoy. | Guardarraíl anti-invención de antecedentes. |
| `test_firmas_retrocompatibles` | Llamar a los seis símbolos **sin** el parámetro de historial sigue funcionando. | Si quitaste el default, rompés `FakeLLM` y los llamadores. |
| `test_coste_del_historial` | El prompt con N turnos sigue bajo el tope total de WAVE-05. | Es lo que impide que esta WAVE deshaga la anterior. |

Para la expiración, **inyectá el reloj** (parámetro o función de tiempo sustituible). Un test
que duerme 3 minutos no es un test.

---

## Verificación

```bash
.venv/bin/python -m pytest tests/ -q
.venv/bin/python -m pytest tests/test_session_memory.py -v
git stash && .venv/bin/python -m pytest tests/test_session_memory.py -q ; git stash pop
.venv/bin/ruff check .

# El follow-up, de punta a punta y sin red (con el LLM sustituido por un doble)
.venv/bin/python -c "
# Sustituí por el import real del estado y del ensamblador:
from <modulo_estado> import <Estado>
st = <Estado>()
st.observe('Háblame de Programación Web', '<respuesta>')
print('entidad activa:', st.active_entity)
print('resuelta:', st.resolve('¿Y cuánto dura?'))
"
```

Pegá la última salida: debe mostrar la pregunta expandida con «Programación Web» dentro.

**Prueba manual obligatoria** — esta WAVE se rompe de formas que los tests no ven:

1. Por voz: «Háblame de Programación Web» → «¿Y cuánto dura?» → «¿Y cuánto cuesta?»
2. Cambio de tema en caliente: → «¿Y Enfermería?» → «¿Cuánto dura?» (debe hablar de Enfermería)
3. **Dos visitantes**: conversá, esperá más del TTL, preguntá «¿y cuánto dura?» en frío. **No
   debe** recordar nada.
4. Con dos pestañas abiertas: comprobá que las dos siguen la misma conversación.

El paso 3 es el importante. Anotá los cuatro resultados en `PROGRESS.md`.

---

## Criterios de aceptación

1. «Háblame de Programación Web» → «¿Y cuánto dura?» responde **2 años**, **en las dos rutas**.
2. El cambio de tema reemplaza la entidad activa; no hay arrastre.
3. Pasado el TTL de inactividad, el estado se descarta: el visitante siguiente empieza limpio.
   Verificado con reloj inyectado, no con `sleep`.
4. Existe un reset explícito y funciona.
5. La memoria es de dispositivo/sesión: **no** se aísla por socket y una reconexión no la pierde.
6. El historial está acotado a N turnos, y el prompt resultante sigue **bajo el tope total de
   WAVE-05**. Número pegado.
7. Sin entidad activa, el comportamiento es idéntico al actual.
8. Las seis firmas siguen siendo llamables sin el parámetro nuevo; `FakeLLM` de
   `tests/test_app_services.py` sigue satisfaciendo el Protocol sin tocarlo.
9. Cero persistencia en disco, cero dependencias nuevas, cero datos de identidad guardados.
10. Las 4 pruebas manuales ejecutadas y anotadas.
11. Las pruebas previas pasan.

---

## Checklist pre-commit

El compartido de `README.md`, más:

```
[ ] Precondición WAVE-05 verificada (el chequeo de «Háblame de…» impreso arriba)
[ ] Follow-up verde en AMBAS rutas
[ ] Test de expiración con reloj inyectado (sin sleep en la suite)
[ ] Test de "no es por socket" verde
[ ] Coste del historial medido: prompt con N turnos <= tope total de WAVE-05
[ ] Sin persistencia: git diff | grep -iE 'sqlite|redis|pickle|json.dump|open\(.*w' → revisado
[ ] Sin dependencias nuevas (requirements*.txt sin cambios)
[ ] Firmas retrocompatibles: los seis símbolos llamables sin el parámetro nuevo
[ ] tests/test_app_services.py NO modificado (si tuviste que tocarlo, rompiste el default)
[ ] Las 4 pruebas manuales hechas, con el resultado del caso "dos visitantes" anotado
[ ] TTL y N elegidos y justificados en PROGRESS.md
```

---

## Commit

```
feat(context): WAVE-06 memoria de sesión y preguntas de seguimiento

- estado de conversación con entidad activa e historial de N turnos, en memoria
  del proceso, con ámbito de dispositivo/sesión y expiración por inactividad
- ámbito de sesión, NO de socket: hay un único ConversationService que difunde a
  todos los clientes; aislar por conexión rompería el modelo de kiosco
- expiración por inactividad y reset explícito: el visitante siguiente no hereda
  la conversación anterior
- resolución determinista de referencias: «¿y cuánto dura?» se expande con la
  entidad activa antes de enrutar; el cambio de tema la reemplaza
- historial enhebrado por las dos rutas (parámetro opcional con default vacío,
  para no romper llamadores ni los dobles de los tests)
Cierra: hallazgos A, O
Métrica: pregunta 5 de las 11 obligatorias: fallaba → responde 2 años
         prompt con historial: <medido> chars (tope de WAVE-05: <n>)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

## Rollback

```bash
HOLOGRAM_SESSION_MEMORY=0    # sin memoria: comportamiento previo a esta WAVE
```
Con el flag apagado, cada turno vuelve a ser el primero. Probalo en un test.

```bash
git revert <sha>
```

---

## Handoff — volcar en `PROGRESS.md`

```markdown
### WAVE-06 — Memoria de sesión y follow-ups
- Commit: <sha> · Fecha: <YYYY-MM-DD>
- Archivos tocados: <...>
- Tests añadidos: tests/test_session_memory.py::<casos>
- Dónde vive el estado: <módulo y símbolo>
- N turnos: <n> · TTL de inactividad: <n> · por qué: <...>
- Clave de sesión: <cómo se deriva>
- Coste del historial: prompt <n> chars (tope WAVE-05: <n>)
- Pregunta 5 de las 11: fallaba → <resultado>
- Pruebas manuales:
  1. follow-up encadenado: <...>
  2. cambio de tema: <...>
  3. dos visitantes / expiración: <...>
  4. dos pestañas: <...>
- Criterios de aceptación: <1–11>
- Desvíos: <...>
- Hallazgos nuevos (NO arreglados): <...>
- Revisión humana: <OK, fecha>
```

**Después: PARAR.** Con esta WAVE termina la Fase 2. Las 11 preguntas obligatorias deberían
responderse correctamente **todas** por primera vez: volvé a pasarlas y dejá el resultado en
`PROGRESS.md` — es el cierre de la mitad sustantiva del plan y un punto de entrega válido.
