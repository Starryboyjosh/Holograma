# Holograma UNEV — Análisis técnico y plan de mejora

## Estado de implementación (actualizado 2026-06-27)

Avance verificado con `pytest` (**91 pruebas**) + `ruff` limpio. El backend de ML
no corre en este entorno, por eso lo que requiere ejecutarlo queda marcado como
*pendiente de hardware*, no cerrado. Detalle para el próximo agente en
[`docs/HANDOFF.md`](docs/HANDOFF.md) → "Latest session".

| Fase | Estado | Qué se hizo |
|------|--------|-------------|
| **0 — Síntomas** | ✅ Hecho | Sin re-saludo por parpadeo (`vision/person_detector.py`); `custom_speak` ya no reemite eventos (atasco "hablando", síntoma B); `_ollama_ready` cacheado (`OLLAMA_READY_TTL_SECONDS`); watchdog de 20 s en `useChatSocket.ts`. |
| **1 — Event loop** | ◐ Parcial | Selección de backend en `asyncio.to_thread` (el sondeo ya no congela el loop). **Desvío deliberado:** la ruta async ya usa `AsyncOpenAI`/`AsyncAnthropic`, así que la reescritura urllib→httpx no aporta nada al loop y NO se hizo. |
| **2 — Calidad** | ◐ Parcial | `max_tokens` unificado vía `LLM_MAX_TOKENS` (450); el filtro anti-inglés ya no descarta respuestas (síntoma C "no puedo responder"). |
| **3 — De-monkey-patch** | ◐ Base hecha | Capa `app/` aditiva y testeada (`ConnectionManager`, `LLMService`, `CameraContextProvider`, `ConversationService`); corte del ciclo `call↔llm_backend` vía `stream_llm_response(camera_context=...)`. **Nada importa `app/` aún** → cero riesgo. Falta cablear en `main.py` y borrar el monkey-patching (requiere hardware). |
| **4 / §8 — Reorg** | ☐ Pendiente | Movimiento de carpetas (`app/` + `core/`) diferido: rompe imports y necesita el backend corriendo para validar. |

Pruebas nuevas de esta tanda: `tests/test_person_presence.py`,
`tests/test_ollama_ready_cache.py`, `tests/test_llm_unify.py`,
`tests/test_app_services.py`.

> Documento maestro. Reúne (1) el diagnóstico de cada síntoma reportado con la
> línea de código exacta que lo causa, (2) el catálogo completo de errores,
> (3) la decisión reescribir-vs-refactorizar, (4) la arquitectura objetivo,
> (5) el plan por fases, (6) la limpieza de repo y reorganización de carpetas.
>
> Fecha del análisis: 2026-06-27 · Commit base del grafo: `89e71f3c`
> Método: lectura completa de los orquestadores (`main.py`, `call.py`,
> `llm_backend.py`), los subsistemas (`vision/`, `stt/`, `skills/`,
> `hologram_controller.py`, `provider_config.py`), el frontend
> (`useChatSocket.ts`) y el reporte de grafo (`graphify-out/GRAPH_REPORT.md`),
> contrastado con la referencia que SÍ funciona (`Experimental/tutor_v3.py`).

---

## 0. TL;DR (resumen ejecutivo)

Los cuatro síntomas que reportaste no son cuatro bugs sueltos: son
**consecuencias de una sola decisión de arquitectura equivocada**. La app nació
como un programa de consola (`call.py`, con `voice_loop()` bloqueante) y después
se "envolvió" en un servidor web asíncrono (`main.py`) **parchando funciones en
tiempo de ejecución** (monkey-patching) y **compartiendo estado global mutable**
entre hilos. Eso produce, de forma encadenada:

| # | Síntoma que reportaste | Causa raíz (archivo:línea) | Tipo |
|---|------------------------|----------------------------|------|
| A | **Se congela / todo lento** | Sondas HTTP **bloqueantes** a Ollama (`urllib`) corriendo **sobre el event loop** dentro de `stream_llm_response` → congela TODO el servidor (video, otros mensajes). `llm_backend.py:38-60`, `:88`, `:212-214`, `:517` | Concurrencia |
| B | **Se queda en "hablando"** | El estado vuelve a `idle` **solo** con `audio_status: completed` (`useChatSocket.ts:79`). El `speak()` parchado (`custom_speak`) **re-emite** `streaming_started/text_chunk/text_done` por un canal *diferido* (`main.py:262`, `run_coroutine_threadsafe`) que llega **después** del `completed` → UI atascada en `speaking`. `main.py:84-90`, `:987` | Carrera de eventos |
| C | **A veces dice "no puedo responder"** | Fallback a `_local_only_reply` (mensaje enlatado) cuando la sonda de 1.5 s expira bajo carga de CPU; y filtro anti-inglés que descarta respuestas válidas. `llm_backend.py:220`, `:395`, `:414` | Lógica LLM |
| D | **Detección de personas rara** | `was_present = is_present` al final del bucle (`person_detector.py:444`) **pisa** la máquina de estados y **anula los 5 s de gracia** → cualquier parpadeo de YOLO vuelve a disparar `person_entered` → re-saluda. Además 2 inferencias por ciclo. | Bug de estado |
| E | **Lento en general** | TTS por subproceso Piper serializado tras un lock + `os.chdir` global + endpoints sync en el threadpool + JPEG por cuadro aunque nadie mire + binarios de 28 MB en git. Varias fuentes. | Rendimiento / higiene |

**Veredicto:** **No empieces de cero.** ~70 % del código (los módulos "hoja":
`provider_config.py`, `hologram_controller.py`, `vision/`, `stt/`, `skills/`)
está bien escrito y documentado. La podredumbre está concentrada en **3 archivos
de orquestación** (`main.py`, `call.py`, `llm_backend.py`). El camino correcto es
**reescribir solo la capa de orquestación** detrás de una interfaz de servicios
limpia, conservando los subsistemas y la UI React/Tauri. Detalle en §5–§6.

---

## 1. Cómo está construido hoy (y por qué duele)

### 1.1 El pecado original: una CLI disfrazada de servidor web

`call.py` es un programa de consola completo: tiene `voice_loop()`,
`_wait_for_trigger()`, lee del micrófono, habla por TTS y mantiene **estado en
variables globales del módulo** (`ai_busy`, `speak_lock`, `hologram`).

`main.py` (FastAPI) **no reimplementa** esa lógica: **importa `call.py` y le
cambia las funciones por debajo en el arranque** (`lifespan`, `main.py:61-176`):

```python
# main.py (startup) — esto es el problema central
call.speak = custom_speak                       # parcha la función de voz
WhisperListener.listen_once = custom_listen_once # parcha el STT
call._camera_detection_callback = custom_callback
call.WEB_MODE = True
```

Esto se llama *monkey-patching*. El propio repo lo reconoce como deuda: el
`GRAPH_REPORT.md` (Community 26) lista la tarea **"E. De-monkey-patch into typed
services (refactor; INTENTIONALLY DEFERRED)"**. El refactor se difirió… y los
síntomas que reportas son exactamente lo que pasa cuando no se hace.

**Por qué es malo, en concreto:**

- Dos puntos de entrada (`call.py` para consola, `main.py` para web) comparten
  el **mismo estado global mutable** desde hilos distintos (voice loop, worker
  de TTS, hilo de cámara, handler async del WebSocket). Nadie coordina esos
  accesos más allá de un `speak_lock` y un par de booleanos.
- La web "habla" llamando a una función de consola parchada que, a su vez,
  re-emite eventos al navegador por un canal distinto al del handler → de ahí el
  síntoma B (§2.2).
- Importar `call` ejecuta **efectos colaterales globales** en import-time:
  `os.chdir(BASE_DIR)` (`main.py:41`), `os.environ["QT_QPA_PLATFORM"]="xcb"`
  (`call.py:44`), carga de `.env`, y `hologram = create_hologram_manager()`.

### 1.2 Dos caminos de LLM que divergen

`llm_backend.py` mantiene **dos** funciones que hacen lo mismo de forma distinta:

- `generate_reply()` (`:430`) — **síncrona**, la usa el `voice_loop` de consola.
- `stream_llm_response()` (`:495`) — **async**, la usa el WebSocket.

Divergen en límites de tokens, en el post-procesado (el filtro anti-inglés solo
existe en el camino síncrono) y en el manejo de errores. Mantener dos = el doble
de bugs y comportamiento distinto entre voz y web.

### 1.3 Importaciones circulares

`call.py:33` hace `import llm_backend`, y `llm_backend.py:509` hace
`from call import _build_camera_context, _last_camera_analysis`. Es un ciclo
`call ↔ llm_backend` resuelto con un import perezoso dentro de la función — un
parche que indica que las responsabilidades están mal repartidas. El grafo
también marca ciclos `main.py -> main.py` y `lib.rs -> lib.rs`.

---

## 2. Diagnóstico por síntoma (con evidencia exacta)

### 2.A — "Se congela" / todo lento  →  bloqueo del event loop

**Qué pasa:** cada vez que llega un mensaje por WebSocket, el servidor entero se
queda inmóvil unos segundos: el video se detiene, otros mensajes no responden.

**Causa raíz:** `stream_llm_response()` es `async`, pero adentro ejecuta
**llamadas de red bloqueantes** sin sacarlas del hilo del event loop.

1. `_ollama_request()` (`llm_backend.py:38-60`) usa
   `urllib.request.urlopen(...)` — **síncrono y bloqueante**.
2. `_ollama_ready()` (`:88`) = `_ollama_server_available()` +
   `_ollama_model_available()`, **dos** sondas HTTP a `/api/tags`, cada una con
   timeout de 1.5 s (`OLLAMA_STATUS_TIMEOUT_SECONDS`).
3. `_candidate_backends()` (`:212`) vuelve a llamar `_ollama_ready()` (`:214`),
   así que las sondas corren **varias veces por mensaje**.
4. `stream_llm_response()` (`:517`) llama
   `_candidate_backends(get_selected_backend())` **dentro del coroutine** →
   esas sondas bloqueantes corren **sobre el event loop**.

> En asyncio, una sola llamada bloqueante en el loop congela **todas** las demás
> tareas. Por eso no es "el LLM está lento": es que mientras Python espera el
> `urlopen`, el video MJPEG y cualquier otro frame del WebSocket quedan
> detenidos. Bajo carga de CPU (YOLO + Whisper + Piper compitiendo) los 1.5 s se
> agotan seguido, y el freeze se nota "siempre".

**Contraste con lo que SÍ funciona:** `Experimental/tutor_v3.py` corre el LLM
**en proceso** con `llama_cpp.Llama` (`tutor_v3.py:84`). No hay HTTP, no hay
sondas, no hay event loop que bloquear. Por eso "el experimento ligero" nunca se
congela.

**Arreglo (resumen, detalle en §6):** una sola ruta async; toda E/S bloqueante
(Ollama, Piper, YOLO, Whisper) va a `asyncio.to_thread(...)` o a un cliente
`httpx.AsyncClient`; las sondas de readiness se cachean (TTL ~10 s) en vez de
correr 2–4 veces por mensaje.

---

### 2.B — "Se queda en hablando" / el estado nunca vuelve a idle

**Qué pasa:** después de responder, la UI se queda con el orbe/estado en
"hablando" y ya no acepta nada más hasta recargar.

**Causa raíz: una carrera entre dos canales de envío + doble emisión.**

En el frontend (`useChatSocket.ts`), el estado **solo** vuelve a `idle` en dos
casos:

```ts
} else if (data.type === 'audio_status') {
  if (data.status === 'completed') { setAssistantState('idle'); }   // :79-81
...
} else if (data.type === 'error') { setAssistantState('idle'); }    // :99
```

Todo lo demás (`text_chunk`, `text_done`) deja el estado en `speaking`. Es decir:
**si falta un único `audio_status: completed`, la UI queda atascada en
"hablando" para siempre.**

Ahora mira el backend. El handler del WebSocket emite, en orden y **esperado con
`await`** (`main.py:962-990`):

```
streaming_started → text_chunk×N → text_done → audio_status:processing
→ speak(full_response, blocking=False) → audio_status:completed
```

Pero `speak` fue **parchado** a `custom_speak` (`main.py:84-90`), que reemite:

```python
def custom_speak(text, blocking=True):
    send_to_web_client("status", "streaming_started")  # ¡otra vez!
    send_to_web_client("text_chunk", text)             # ¡el texto completo otra vez!
    send_to_web_client("text_done", text)
    original_speak(text, blocking)
```

Y `send_to_web_client` **no** envía de inmediato: **agenda** el envío en el loop
y regresa (`main.py:254-262`):

```python
asyncio.run_coroutine_threadsafe(do_send(), running_loop)  # diferido, no await
```

**La carrera:** el handler manda su `audio_status: completed` con `await` (canal
inmediato), mientras que los tres eventos duplicados de `custom_speak` quedan
**encolados** para correr cuando el coroutine ceda el control. Resultado típico
de orden de llegada al navegador:

```
… → completed (→ idle) → streaming_started (→ thinking) → text_chunk (→ speaking)
   → text_done (→ speaking)        [y ya NO hay otro completed]
```

→ La UI termina en **`speaking`** y nadie la saca de ahí. **Atascada en
"hablando".** Es no determinista (depende del scheduler), por eso es
intermitente: "a veces" / "casi siempre".

**Bugs que se suman aquí:**

- `audio_status: completed` se emite en cuanto se **lanza** el hilo de TTS
  (`blocking=False`), no cuando el audio **termina** → el estado y el audio real
  van desfasados aun cuando no se atasca.
- El duplicado hace que el texto **aparezca, se borre y reaparezca** en pantalla
  (`custom_speak` reenvía `streaming_started` que limpia `aiSpokenText`,
  `useChatSocket.ts:65`).
- En `call.speak` (`call.py:658`), con `blocking=False` se hace
  `speak_lock.acquire(blocking=False)`; si el lock está tomado (el voice loop o
  un saludo de cámara está hablando) la función **regresa en silencio**
  ("Omitiendo habla para evitar traslape") y el `hologram.set_state("speaking")`
  puede quedar sin su `set_state("idle")` correspondiente.

**Arreglo:** el frontend y el backend deben compartir **una sola** máquina de
estados con eventos idempotentes; eliminar la doble emisión (que el WebSocket sea
el **único** emisor; TTS no reemite texto); enviar `idle`/`completed` cuando el
audio realmente termina; añadir un *timeout* de seguridad en el cliente que
fuerce `idle` si pasan N segundos sin `completed`.

---

### 2.C — "A veces no responde / dice que no puede responder"

**Qué pasa:** en lugar de contestar, suelta el mensaje enlatado *"Por ahora estoy
en modo local. Puedo responder preguntas básicas sobre UNEV…"* o *"Disculpa, tuve
un problema al generar mi respuesta…"*.

**Causas raíz (dos):**

1. **Fallback a `local_only`** (`llm_backend.py:220`, `_local_only_reply`). Se
   dispara cuando el backend seleccionado es `local_only` **o cuando todos los
   backends fallan**. Como la selección de backend depende de `_ollama_ready()`
   (sondas de 1.5 s que expiran bajo carga, ver §2.A), un pico de CPU hace que
   Ollama "parezca" no disponible → cae a `local_only` → responde con el enlatado
   aunque Ollama esté perfectamente vivo. `select_backend` (`provider_config.py:203`)
   devuelve `local_only` precisamente cuando `ollama_ready()` da `False`.

2. **Filtro anti-inglés que descarta respuestas válidas.** `_postprocess_reply`
   (`:414`) usa `_is_mostly_english` (`:395`) y, si cree que la respuesta está en
   inglés, la **tira** y devuelve *"Disculpa, tuve un problema…"*. Este filtro
   solo vive en el camino **síncrono** (voz), así que voz y web se comportan
   distinto ante la misma respuesta.

**Nota:** las skills locales (`skills/router.py`) son razonables como *fallback*
de cortesía, pero hoy se activan por accidente (por timeout de sonda), no por
decisión. El usuario percibe "no me respondió".

**Arreglo:** elegir backend con readiness **cacheada** (no por mensaje); si el
backend primario falla, **reintentar** el siguiente backend con key antes de
caer a `local_only`; quitar (o suavizar mucho) el filtro anti-inglés y unificarlo
en la única ruta; que el enlatado de `local_only` sea explícitamente el último
recurso, con log claro de por qué se llegó ahí.

---

### 2.D — "La detección de personas funciona raro"

**Qué pasa:** la cámara saluda de más, vuelve a saludar a la misma persona, o
reacciona tarde/raro.

**Causa raíz #1 (el bug grande): `person_detector.py:444` rompe la máquina de
estados de presencia.** El bucle mantiene con cuidado `was_present` y un período
de gracia de 5 s (`absence_grace`, `:391`) para no cortar la conversación por un
cuadro perdido. Pero al final del ciclo hace, **incondicionalmente**:

```python
was_present = is_present     # :444  ← pisa todo lo decidido arriba
last_count = count           # :445
```

Recorrido del fallo:

1. Cuadro 1: hay persona → `event="person_entered"`, `was_present=True`. Línea
   444: `was_present = True`. OK.
2. Cuadro 2: YOLO parpadea y pierde a la persona 1 cuadro → `is_present=False`.
   Entra al `elif was_present:`, arranca el período de gracia, **no** declara
   `person_left` (correcto). Pero línea 444: `was_present = False` ← **anula la
   gracia**.
3. Cuadro 3: la persona reaparece → como `was_present` quedó en `False`, dispara
   **`person_entered` otra vez** → **vuelve a saludar**.

Con `yolo26n` en CPU los parpadeos de detección son constantes, así que la
persona recibe saludos repetidos. Ese es el "raro".

**Causa raíz #2: dos inferencias YOLO por ciclo.** `analyze_frame` (`:212`)
llama `detect_persons_in_frame` (`:220`, `self.model(frame)`) **y**
`detect_custom_objects` (`:221`, `self.model.predict(frame, text=prompt)`). En
CPU cada inferencia cuesta 100–500 ms; hacer dos por ciclo **duplica** la carga y
contribuye al freeze general (§2.A).

**Causa raíz #3: prompt de texto sobre un modelo que no es open-vocabulary.**
`detect_custom_objects` pasa `text=prompt` a `yolo26n.pt`. Los prompts de texto
son de YOLOE/YOLO-World; un `yolo26n` estándar no los soporta y el bloque está
envuelto en `except Exception: pass` (`:179-180`) que **oculta** el fallo. O no
detecta nada, o se comporta de forma impredecible, sin avisar.

**Causa raíz #4 (rendimiento): JPEG por cuadro siempre.** `run_continuous`
codifica un JPEG anotado cada ~30 ms (`_store_annotated_frame`, `:449`) **aunque
ningún navegador esté viendo el feed**. CPU desperdiciada.

**Causa raíz #5: sin gracia de entrada.** `person_entered` se dispara en el
**primer** cuadro positivo (`:418`), sin debounce, así que un falso positivo de
un cuadro ya saluda.

**Arreglo:** quitar la reasignación de `was_present` de la línea 444 (la máquina
de estados ya lo gestiona); añadir debounce de **entrada** simétrico al de
salida; correr la inferencia de objetos custom **solo** si hay clases custom y
**solo** con un modelo que de verdad las soporte (o separarla a otro intervalo);
codificar JPEG **solo** si hay suscriptores al feed; no tragar excepciones en
silencio.

---

### 2.E — "Lento en general" (fuentes acumuladas)

- **TTS por subproceso Piper, serializado tras un lock.** Cada respuesta lanza
  `piper` como subproceso (`call.py:_piper_synth_to_wav`, `:377`, timeout 120 s),
  escribe un WAV temporal y lo reproduce con otro subproceso (`aplay`). Todo
  detrás de `speak_lock`. La referencia que funciona usa TTS **en proceso**
  (Supertonic ONNX, `tutor_v3.py:339`) con reproducción no bloqueante
  `sd.play(...)`. El subproceso añade arranque de proceso + E/S de disco por
  cada frase.
- **`stop_all_tts_processes()` con `killall -9`** (`call.py:71`) mata **todos**
  los `aplay/paplay/piper/espeak` del sistema, no solo los suyos. Brutal y
  propenso a efectos colaterales.
- **Endpoints síncronos en el threadpool.** Varios `def` (no `async def`) como
  `get_config`, `update_config`, `set_camera`, `play_speak`, y sobre todo
  `video_feed` (`main.py:823`, un `while True` + `time.sleep` que **retiene un
  worker del threadpool de 40 para siempre por cada cliente**). Pocos clientes
  agotan el pool.
- **`os.chdir(BASE_DIR)` en import-time** (`main.py:41`): cambia el directorio de
  trabajo de **todo** el proceso; frágil con rutas relativas en cualquier otro
  punto.
- **Higiene de repo que pesa** (§7): un PDF de **28 MB** versionado en git,
  `graph.json`/`graph.html` (~1.7 MB) versionados, artefactos de build de Rust.

---

## 3. Catálogo completo de errores (lista numerada)

> "Señala cada error": aquí está la lista, agrupada. Cada uno con archivo:línea.

### Arquitectura
1. Monkey-patching de `call.speak`, `WhisperListener.listen_once`,
   `_camera_detection_callback` en el arranque del servidor. `main.py:82-110`.
2. Estado global mutable compartido entre hilos (`ai_busy`, `speak_lock`,
   `hologram`, `WEB_MODE`). `call.py` (módulo).
3. Dos puntos de entrada (CLI + web) sobre el mismo módulo. `call.py` / `main.py`.
4. Import circular `call ↔ llm_backend`. `call.py:33`, `llm_backend.py:509`.
5. Efectos colaterales en import-time: `os.chdir` (`main.py:41`),
   `os.environ["QT_QPA_PLATFORM"]` (`call.py:44`), carga de `.env`, creación del
   hologram manager.
6. Dos rutas de LLM divergentes (sync `generate_reply` `:430` vs async
   `stream_llm_response` `:495`).

### Concurrencia / asyncio
7. E/S bloqueante (`urllib`) sobre el event loop dentro de un `async`.
   `llm_backend.py:38-60`, `:517`.
8. Sondas de readiness Ollama ejecutadas 2–4 veces por mensaje.
   `:88`, `:212-214`.
9. `video_feed` síncrono con `while True` retiene un worker del threadpool por
   cliente. `main.py:823`.
10. Endpoints CRUD síncronos en vez de `async` (config, cámara, speak).
11. Envío al cliente por dos canales distintos (await directo vs
    `run_coroutine_threadsafe`) → carrera de orden. `main.py:262` vs `:963-990`.

### LLM
12. Doble emisión de `streaming_started/text_chunk/text_done` (handler + TTS
    parchado). `main.py:84-88` + `:963-975`.
13. `audio_status: completed` emitido al **lanzar** el hilo, no al terminar el
    audio. `main.py:987-990`.
14. Fallback a `local_only` por timeout de sonda, no por configuración.
    `llm_backend.py:220`.
15. Filtro anti-inglés descarta respuestas válidas, solo en la ruta sync.
    `:395`, `:414`.
16. Límites de tokens inconsistentes por proveedor (350 / 450 / 1024 / sin
    límite). `llm_backend.py`.

### Visión
17. `was_present = is_present` anula el período de gracia. `person_detector.py:444`.
18. Sin debounce de entrada → falsos saludos. `:418`.
19. Dos inferencias YOLO por ciclo. `:220-221`.
20. Prompt de texto YOLOE sobre modelo no compatible, error tragado.
    `:166`, `:179-180`.
21. JPEG por cuadro aunque nadie mire el feed. `:449`.

### TTS / STT
22. TTS por subproceso Piper + WAV temporal + `aplay`, serializado tras lock.
    `call.py:377`, `:605`.
23. `killall -9` global de procesos de audio. `call.py:71`.
24. Estado `speaking` puede no volver a `idle` si el hilo de `speak` falla o el
    lock estaba tomado. `call.py:676-689`.

### Frontend
25. Vuelta a `idle` depende de **un solo** evento (`audio_status: completed`),
    sin timeout de seguridad. `useChatSocket.ts:79-81`.
26. Sin idempotencia: eventos duplicados/desordenados rompen la máquina de
    estados. `useChatSocket.ts:60-104`.

### Higiene de repositorio
27. PDF de 28 MB versionado en git: `docs/Manual de Marca - UNEV … .pdf`.
28. `graphify-out/graph.json` (852 KB) y `graph.html` (816 KB) versionados.
29. Documentación duplicada/obsoleta en `docs/` (ver §8).
30. `pyproject.toml` + `requirements.txt` coexisten sin una sola fuente de
    verdad de dependencias.

---

## 4. ¿Reescribir desde cero o refactorizar?

Dijiste que estás dispuesto a empezar de cero. **Recomendación: NO desde cero.**

**Lo que está bien y hay que conservar (no lo toques):**

- `provider_config.py` — contrato de proveedores limpio, puro, testeable. Bien.
- `hologram_controller.py` — manager *fail-soft*, thread-safe, con backoff. Bien.
- `vision/person_detector.py` — sólido salvo el bug de la línea 444 y el doble
  inference (arreglos puntuales, no reescritura).
- `stt/listener.py` — robusto (umbral adaptativo, anti-alucinación). Bien.
- `skills/` + `data/*.json` — contenido de UNEV/Honduras, reusable como fallback.
- Todo el frontend React/Tauri — la UI no es el problema; solo la máquina de
  estados del socket necesita endurecerse.

**Lo que hay que reescribir (la capa podrida, ~3 archivos):**

- `main.py`, `call.py`, `llm_backend.py` → reemplazar por una **capa de
  servicios tipada** y **una sola ruta async**, sin monkey-patching ni globals.

Reescribir desde cero botaría también lo bueno y la UI, costaría semanas y
re-introduciría bugs ya resueltos (calibración de ruido del STT, fail-soft del
holograma, contrato de proveedores). El refactor dirigido es más rápido y de
menor riesgo. Si aun así prefieres "sensación de empezar de cero", hazlo como un
**paquete nuevo `holograma/` con módulos limpios** que **importan** los
subsistemas buenos — empiezas con orquestación nueva pero reciclas los motores.

---

## 5. Arquitectura objetivo

```
                         ┌────────────────────────────┐
   Frontend (React/Tauri)│   useChatSocket (1 FSM)     │
        WebSocket  ◄────►│   eventos idempotentes      │
                         └─────────────┬──────────────┘
                                       │  (un solo emisor de eventos)
                         ┌─────────────▼──────────────┐
                         │   app/  (FastAPI async)     │   ← reemplaza main.py
                         │   - rutas async finas       │
                         │   - 1 ConversationService   │
                         └─────────────┬──────────────┘
                                       │  (interfaces tipadas, sin monkey-patch)
        ┌───────────────┬──────────────┼───────────────┬───────────────┐
        ▼               ▼              ▼                ▼               ▼
   LLMService      TTSService     STTService     VisionService    HologramService
  (1 ruta async)  (en proceso    (stt/listener) (person_detector  (hologram_
   httpx/to_thread o to_thread)                  + fix 444)        controller, ya ok)
```

**Principios:**

1. **Una sola ruta async.** Borrar `generate_reply` sync; el voice loop (si se
   conserva) consume el mismo servicio async vía `asyncio.run`.
2. **Sin trabajo bloqueante en el loop.** Ollama vía `httpx.AsyncClient`; Piper,
   YOLO y Whisper vía `asyncio.to_thread`.
3. **Estado inyectado, no global.** Un objeto `AppState` (o el `app.state` de
   FastAPI) sostiene los servicios; nada de variables de módulo mutables ni
   monkey-patching.
4. **Un solo emisor de eventos al cliente**, con un `ConnectionManager` async
   (sin `run_coroutine_threadsafe` mezclado con `await`). El TTS **no** reemite
   texto; solo notifica progreso de audio.
5. **Readiness cacheada** con TTL (~10 s) y selección de backend determinista.

---

## 6. Plan por fases

> Cada fase es independiente y deja la app funcionando. Empieza por la Fase 0:
> son cambios pequeños que ya quitan los síntomas más molestos.

### Fase 0 — Quick wins (horas, alto impacto, bajo riesgo)
- [ ] **Arreglar detección de personas:** borrar `was_present = is_present` /
      `last_count = count` de `person_detector.py:444-445` (la máquina de estados
      ya los gestiona). Verificar con `tests/` que no se re-saluda en parpadeos.
- [ ] **Matar el atasco de "hablando":** que `custom_speak` **deje de** reemitir
      `streaming_started/text_chunk/text_done` (`main.py:85-87`). El WebSocket ya
      los envió. El TTS solo debe (eventualmente) notificar fin de audio.
- [ ] **Timeout de seguridad en el frontend:** en `useChatSocket.ts`, si pasan
      ~20 s en `speaking` sin `completed`, forzar `idle`. Red de seguridad.
- [ ] **Cachear readiness de Ollama:** memoizar `_ollama_ready()` con TTL 10 s
      para que no corra 2–4 veces por mensaje.
- [ ] **No tragar el error de objetos custom:** quitar `except Exception: pass`
      de `person_detector.py:179-180` (al menos loguear) y saltar
      `detect_custom_objects` si no hay clases custom.

### Fase 1 — Desbloquear el event loop (1–2 días)
- [ ] Reemplazar `urllib` por `httpx.AsyncClient` en `_ollama_request`
      (`llm_backend.py:38-60`); `await` real, sin bloquear el loop.
- [ ] Envolver Piper/YOLO/Whisper en `asyncio.to_thread(...)` cuando se invoquen
      desde rutas async.
- [ ] Convertir `video_feed` a `StreamingResponse` async (o servirlo desde el
      detector con backpressure) para no retener workers del threadpool.
- [ ] Convertir los endpoints CRUD a `async def`.

### Fase 2 — Unificar la ruta de LLM (2–3 días)
- [ ] Borrar `generate_reply` sync; dejar solo `stream_llm_response`.
- [ ] Mover el filtro anti-inglés a la única ruta y suavizarlo (o quitarlo).
- [ ] Selección de backend con reintento al siguiente proveedor con key antes de
      `local_only`; el enlatado pasa a ser último recurso con log explícito.
- [ ] Unificar `max_tokens` por configuración, no por proveedor hardcodeado.

### Fase 3 — Des-monkey-patchear hacia servicios (3–5 días) — el refactor grande
- [ ] Crear `app/services/{llm,tts,stt,vision,hologram}.py` con interfaces
      tipadas que **envuelven** los módulos buenos actuales.
- [ ] `ConversationService` orquesta: recibe prompt → LLM (stream) → TTS → emite
      eventos por **un solo** `ConnectionManager` async.
- [ ] `main.py` queda como rutas finas que delegan en los servicios. Borrar el
      monkey-patching del `lifespan`. Quitar `os.chdir` y mover el fix de Qt a un
      punto de entrada explícito, no a import-time.
- [ ] Romper el ciclo `call ↔ llm_backend` (mover `_build_camera_context` al
      `VisionService`/`ConversationService`).

### Fase 4 — Rendimiento y pulido (2–3 días)
- [ ] TTS en proceso (evaluar Supertonic ONNX como en `tutor_v3.py`, o Piper vía
      binding en proceso) con reproducción no bloqueante; reemplazar el
      `killall -9` por gestión de los procesos propios.
- [ ] JPEG del feed solo si hay suscriptores; inferencia de objetos custom en su
      propio intervalo.
- [ ] `audio_status: completed` cuando el audio **termina** de verdad.
- [ ] Debounce de entrada en la detección de personas.

---

## 7. Limpieza de repositorio

### 7.1 Sacar binarios pesados del control de versiones
- `docs/Manual de Marca - UNEV 1920x1080 - 2025.pdf` — **28 MB versionado**.
  Mover a almacenamiento externo (Drive/Releases) o a Git LFS. Quitarlo del árbol
  e idealmente purgar de la historia (`git filter-repo`) en un momento coordinado
  con el equipo.
- `graphify-out/graph.json` (852 KB) y `graph.html` (816 KB) — son artefactos
  **generados**. Añadir a `.gitignore` y dejar de versionarlos (se regeneran con
  `graphify update .`). Conservar solo `GRAPH_REPORT.md` si se quiere lectura
  humana.
- Confirmado que `*.pt`, `*.onnx`, `piper/`, `static/`, `.venv/` **ya** están en
  `.gitignore` (bien). Verificar que `frontend/src-tauri/target/` también lo esté.

### 7.2 `.md` a BORRAR o consolidar (lo pediste explícitamente)

| Archivo | Acción | Motivo |
|---------|--------|--------|
| `docs/HANDOFF.md` | **Borrar** | Notas de traspaso efímeras; su contenido útil (la lista de tareas diferidas, incl. el de-monkey-patch) queda recogido en **este** documento. |
| `docs/HOLOGRAM.md` | **Consolidar → borrar** | Se solapa con el docstring de `hologram_controller.py` (que ya es exhaustivo). Mover lo que falte al README y borrar. |
| `docs/CONFIG.md` | **Consolidar → borrar** | Duplica `.env.example` (que ya documenta cada variable). Dejar `.env.example` como fuente de verdad. |
| `docs/PACKAGING.md` | **Conservar** (o mover a `README`) | Info de empaquetado Tauri; útil pero cabe en el README. |
| `AGENTS.md` / `CLAUDE.md` / `.claude/CLAUDE.md` | **Conservar** | Reglas para agentes; vigentes. |
| `graphify-out/GRAPH_REPORT.md` | **Conservar** | Útil para revisión de arquitectura. |
| `.pytest_cache/README.md` | (auto) | Generado; ya ignorado por `.pytest_cache/`. |

> Los dos PDF de `docs/` no son `.md` pero entran en "docs viejos": el de **marca
> UNEV** (28 MB) fuera del repo (§7.1); el `Holograma_MISSYOU_Referencia_IA.pdf`
> (13 KB) puede quedarse o moverse junto a la doc de hardware.

### 7.3 Otros
- `media/UNEV_prueba_3_paneles.mp4` + `.png`: si son material de prueba, moverlos
  a `data/samples/` o sacarlos del repo.
- Unificar dependencias: elegir **una** fuente (`pyproject.toml`) y generar
  `requirements.txt` desde ahí, o viceversa. Hoy conviven sin sincronía clara.

---

## 8. Reorganización de carpetas propuesta

La estructura actual mezcla orquestadores, subsistemas y scripts en la raíz.
Propuesta (refactor de Fase 3; mover con cuidado porque rompe imports):

```
Holograma/
├── app/                      # NUEVO: capa web + orquestación (reemplaza main.py/call.py)
│   ├── main.py               #   FastAPI: rutas async finas + lifespan limpio
│   ├── connection.py         #   ConnectionManager async (único emisor de eventos)
│   └── services/
│       ├── conversation.py   #   orquesta LLM→TTS→eventos
│       ├── llm.py            #   1 ruta async (envuelve provider_config)
│       ├── tts.py           #   TTS en proceso, no bloqueante
│       ├── stt.py           #   envuelve stt/listener
│       ├── vision.py        #   envuelve vision/person_detector (con fix 444)
│       └── hologram.py      #   envuelve hologram_controller
├── core/                     # subsistemas "motor" (ya buenos, casi sin tocar)
│   ├── provider_config.py
│   ├── hologram_controller.py
│   ├── vision/   stt/   skills/
│   └── security.py  utils.py
├── data/                     # JSON de contenido (UNEV/Honduras) + samples
├── frontend/                 # React/Tauri (sin cambios estructurales)
├── scripts/                  # diagnose/setup/run
├── tests/
├── docs/                     # solo lo que sobreviva a §7.2 (sin PDFs pesados)
├── models/  piper/           # binarios locales (gitignored)
├── .env.example  pyproject.toml  README.md
└── ANALISIS_Y_PLAN_DE_MEJORA.md   ← este documento
```

> Hacer este movimiento **junto con** la Fase 3 (cuando ya existan los servicios),
> no antes: mover archivos y arreglar imports a la vez evita un estado intermedio
> roto. Un commit por movimiento, corriendo `pytest` entre cada uno.

---

## 9. Apéndice — veredicto por archivo

| Archivo | Veredicto | Nota |
|---------|-----------|------|
| `main.py` | **Reescribir** | Monkey-patching, dos canales de envío, `os.chdir`, endpoints sync. |
| `call.py` | **Reescribir** | CLI con estado global; origen del acople. Reciclar la lógica de chunking de TTS. |
| `llm_backend.py` | **Reescribir** | Bloqueo del loop, doble ruta, fallback frágil, filtro anti-inglés. |
| `provider_config.py` | **Conservar** | Contrato limpio y testeado. |
| `hologram_controller.py` | **Conservar** | Fail-soft, thread-safe. |
| `vision/person_detector.py` | **Arreglar** | Bug `:444`; doble inference; JPEG por cuadro. |
| `vision/camera.py`, `face_analyzer.py` | Revisar | No auditados a fondo; probablemente OK. |
| `stt/listener.py` | **Conservar** | Robusto. |
| `stt/wakeword.py` | Revisar | No auditado. |
| `skills/*` + `data/*.json` | **Conservar** | Contenido reusable como fallback. |
| `security.py`, `utils.py`, `auth_token.py` | **Conservar** | Utilidades pequeñas y correctas. |
| `frontend/**` | **Conservar** | Endurecer solo `useChatSocket.ts` (idempotencia + timeout). |
| `Experimental/tutor_v3.py` | **Referencia** | El patrón que SÍ funciona: modelo en proceso, sin event loop que bloquear. |

---

### Cierre

El sistema no está "podrido entero": está **mal cableado**. Tres archivos de
orquestación cargan con casi todos los síntomas, y la Fase 0 (unas horas) ya
elimina los dos más visibles —el atasco en "hablando" y los saludos repetidos—
sin tocar la arquitectura. El refactor de servicios (Fases 1–3) cierra la causa
de fondo: nunca volver a poner trabajo bloqueante sobre el event loop ni a
parchear funciones de una CLI para que finjan ser un servidor.
