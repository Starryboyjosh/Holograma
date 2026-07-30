# Runbook de ejecución — Contexto y modelos del Holograma UNEV

**Leé este archivo al inicio de cada WAVE. No lo saltes aunque creas que ya lo conocés.**

Este directorio contiene un plan de refactor partido en 10 WAVEs independientes. Cada WAVE se
ejecuta en su propia sesión, produce **un** commit y termina en una parada explícita.

El objetivo del formato es que un modelo sin contexto previo pueda tomar una WAVE, ejecutarla
con seguridad, y dejar constancia para el siguiente. No hace falta leer la auditoría completa
ni las otras WAVEs.

---

## Antes de tocar nada

1. Leé este README y `PROGRESS.md`. **Nada más.**
2. Abrí **sólo** el archivo de la WAVE que te toca (la siguiente pendiente en `PROGRESS.md`).
   No leas las otras WAVEs: es la principal fuente de scope creep en este plan.
3. Re-localizá el código con graphify:
   ```bash
   graphify query "<símbolos listados en la WAVE>"
   ```
   > **Los números de línea de los documentos son orientativos.** Fueron capturados antes de
   > que existiera cualquier WAVE y derivan con cada commit. **Los nombres de símbolo son la
   > verdad.** Si un símbolo no aparece, pará y anotalo en `PROGRESS.md` — no adivines.
4. Verificá las precondiciones de la WAVE:
   ```bash
   git status --short                      # working tree limpio
   git log --oneline -1                    # la WAVE anterior está commiteada
   .venv/bin/python -m pytest tests/ -q    # 203 pruebas en verde
   ```

---

## Implementación

Reparto de modelos según `CLAUDE.md`:

| Etapa | Agente | Para qué |
|---|---|---|
| Análisis | `scout` (Sonnet, read-only) | Brief de implementación: archivos, flujo de datos, superficie de test |
| Código | Opus (sesión principal) | El cambio en sí |
| Tests y mecánica | `worker` (Sonnet) | Tests, renombres, docstrings, lint |

Tocá **sólo** los archivos que la WAVE declara. Si necesitás uno que no está en la lista, eso
es una señal de que la WAVE está mal especificada → **Puerta 0**, abajo.

---

## Puerta 1 — antes del commit

No se commitea sin **todas** estas casillas verdes. Copiá esta lista al reporte y marcala de
verdad; el archivo de la WAVE añade filas propias.

```
[ ] .venv/bin/python -m pytest tests/ -q         → 203 pasando (o más, con los nuevos)
[ ] Los tests nuevos pasan
[ ] Los tests nuevos FALLAN si se revierte el cambio  ← verificado, no asumido
[ ] Criterios de aceptación de la WAVE cumplidos, con la salida real pegada
[ ] .venv/bin/ruff check .                       → limpio
[ ] git diff --stat  → sólo los archivos declarados en la WAVE
[ ] Releído "Fuera de alcance" de la WAVE: nada extra se colonizó
[ ] git diff | grep -iE 'sk-|gsk_|api[_-]?key'   → sin coincidencias
[ ] .env y config.json NO aparecen en el diff (están gitignored; que siga así)
[ ] Pase de revisión: agente `worker` fresco lee el diff contra el archivo de la WAVE
    y reporta desvíos                            ← asistencia, NO la puerta
[ ] REVISIÓN HUMANA: presentar checklist + resumen del diff y ESPERAR el OK explícito
```

**La última casilla es la puerta real.** El modelo no la marca por su cuenta, no la infiere de
un mensaje anterior, y no la da por hecha porque el checklist esté verde. Se espera un OK
humano nuevo, en este turno.

### Sobre el test que debe fallar
Un test que pasa antes y después del cambio no prueba nada. Verificalo así:

```bash
git stash                 # revierte el cambio, deja los tests
.venv/bin/python -m pytest tests/<archivo_nuevo> -q    # debe FALLAR
git stash pop
.venv/bin/python -m pytest tests/<archivo_nuevo> -q    # debe PASAR
```

---

## Commit

Un commit por WAVE, después del OK humano. Trabajo directo sobre `main` (workflow del
proyecto). Cada WAVE trae su mensaje ya redactado; el formato es:

```
<tipo>(<área>): WAVE-NN <título>

- <cambio 1>
- <cambio 2>
Cierra: hallazgo <letra(s)>
Métrica: <antes> → <después>

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

Incluí en el commit: el código, los tests, `PROGRESS.md` y `graphify-out/` regenerado.

---

## Puerta 2 — antes de la siguiente WAVE

```
[ ] graphify update .        (CLAUDE.md lo exige tras modificar código)
[ ] PROGRESS.md actualizado con: WAVE, SHA, métricas antes/después, desvíos,
    y cualquier hallazgo nuevo descubierto
[ ] PARAR
```

**PARAR significa parar.** No empieces la siguiente WAVE en la misma sesión sin una
instrucción explícita y nueva. El valor de este plan está en las puertas; encadenar dos WAVEs
"porque son parecidas" las anula.

---

## Puerta 0 — cuando la WAVE está mal especificada

Va a pasar: el plan se escribió sobre el código de hoy, y el código cambia. Si encontrás que
una WAVE describe algo que ya no existe, que se contradice, o que requiere tocar archivos no
declarados:

1. **Pará.** No improvises un rediseño a mitad de camino.
2. Anotá en `PROGRESS.md`, sección **Desvíos y hallazgos nuevos**: qué esperaba la WAVE, qué
   encontraste, qué opciones ves.
3. Preguntá. Una WAVE mal especificada corregida al inicio cuesta minutos; improvisada, cuesta
   la confianza en todo el resto del plan.

---

## Reglas transversales

Cada una corresponde a una trampa real de este repositorio, no a buenas prácticas genéricas.

1. **graphify primero, siempre.** Hay un hook `PreToolUse` que lo exige antes de leer o
   grepear fuente. Aplica también a los subagentes: incluí la regla en cada prompt.

2. **Las líneas derivan; los símbolos no.** Nunca edites por número de línea sin confirmar el
   símbolo.

3. **Reutilizá antes de escribir.** Este repo ya tiene las piezas que el refactor necesita.
   Escribir una versión nueva de cualquiera de estas es un error de revisión:

   | Pieza | Dónde | Para qué |
   |---|---|---|
   | `normalize_text` | `skills/utils.py` | Normalización de entrada (quita acentos) |
   | `_CONTEXT_FIELD_LABELS` | `skills/university.py` | Las 25 secciones ya etiquetadas |
   | `_CONTEXT_CACHE` + `invalidate_context_cache` | `skills/university.py` | Caché de contexto |
   | `_invalidate_skill_caches` | `skills/unev_content.py` | Invalidación al editar contenido |
   | `minimum_confidence` | `app/hologram/media_router.py` | Umbral de confianza ya testeado |
   | `_CotStreamMirror` (`in_think`, `.feed()`) | `llm_backend.py` | Rastreo de tags entre chunks |
   | `pop_ready_speech` | `utils.py` | Corte de cláusulas para TTS |
   | `clamp_text` / `MAX_FIELD_CHARS` | `skills/unev_content.py` | Truncado de campos |

4. **Nunca imprimas secretos.** Ni en logs, ni en tests, ni en informes, ni en mensajes de
   commit. Si un secreto aparece por accidente, enmascaralo. `config.json` contiene claves en
   texto plano: no lo pegues en ningún reporte.

5. **`skills/` no tiene red de seguridad.** De 203 pruebas, **cero** cubren `skills/router.py`,
   `university.py`, `honduras.py`, `utils.py`, `event_mode.py`. El único test que menciona
   `route_local_skill` lo reemplaza por un stub. Por eso los tests van **con** cada WAVE, no
   al final.

6. **Anotá, no arregles.** Vas a ver cosas rotas fuera del alcance de tu WAVE. Van a
   `PROGRESS.md`. Un parche oportunista contamina el diff y rompe la revisión.

7. **Una WAVE, un commit, una parada.**

---

## Mapa de WAVEs

| WAVE | Título | Fase | Riesgo | Depende de |
|---|---|---|---|---|
| 01 | Desbloquear el turno | 1 · demo | Bajo | — |
| 02 | Filtro de razonamiento en streaming | 1 · demo | Medio | — |
| 03 | Instrumentación y línea base | 1 · demo | Bajo | — |
| 04 | Secciones de contexto | 2 · contexto | Bajo | 03 |
| 05 | `PromptPackage` y router determinista | 2 · contexto | **Alto** | 03, 04 |
| 06 | Memoria de sesión y follow-ups | 2 · contexto | Medio-alto | 05 |
| 07 | Paridad de rutas y skills pre-LLM | 2 · contexto | Medio | 05 |
| 08 | Política de cámara | 3 · endurecer | Medio | 05 |
| 09 | Política de modelos y fallback | 3 · endurecer | Bajo | 01, 03 |
| 10 | Dataset de evaluación | 3 · endurecer | Bajo | 05, 06, 07 |

**La Fase 1 es entregable por sí sola.** Arregla los tres defectos que hoy rompen la demo y no
toca la arquitectura de contexto. Si sólo hay tiempo para una sesión, es esta.

Recomendación de arranque: WAVE-01 y WAVE-02 juntas en la primera sesión — dos commits, dos
puertas, riesgo contenido.

---

## Contexto mínimo del sistema

Para que no tengas que reconstruirlo cada vez:

**Dos rutas al LLM, que no comparten capa de contexto.**

- **Ruta A — voz/CLI (sincrónica):** `call.ask_ai` / `ask_ai_and_speak` → `llm_backend`
  (`generate_reply` o `iter_reply_tokens`) → Piper TTS vía `speak_streaming_from_llm`.
- **Ruta B — web/WebSocket (asíncrona):** `main.websocket_chat_endpoint` →
  `app.services.conversation.ConversationService.handle_prompt` → `LLMService.stream` →
  `llm_backend.stream_llm_response`.

Ambas terminan en `_build_messages`, que arma la lista de mensajes. Ambas mandan **todo** el
contexto institucional en cada turno (~18.400 chars). Ninguna tiene memoria conversacional.

**Un solo `ConversationService`** para todos los clientes web, que difunde a todos: un
holograma físico, varias vistas. Es intencional. No lo "arregles" aislando por socket.

**Comandos del proyecto:**
```bash
.venv/bin/python -m pytest tests/ -q     # suite
.venv/bin/ruff check .                   # lint
graphify update .                         # refrescar el grafo (sin coste de API)
```
