# WAVE-05 — `PromptPackage` y router determinista

| | |
|---|---|
| **Fase** | 2 · Contexto y memoria |
| **Riesgo** | **Alto** — cambia qué información ve el modelo en cada turno |
| **Esfuerzo** | 1–2 sesiones. **Si se parte en dos, son dos commits y dos puertas** |
| **Modelo sugerido** | `scout` (brief obligatorio) → Opus (código) → `worker` (tests) |
| **Cierra hipótesis/hallazgos** | H1, H3, H4 · hallazgos I, L |

> Antes de empezar: leé `README.md` y `PROGRESS.md`. Re-localizá los símbolos con
> `graphify query`. Esta es la WAVE más peligrosa del plan: **un contexto recortado de más
> produce alucinaciones frente a visitantes reales.** Los criterios de aceptación están
> escritos para detectar exactamente eso.

---

## Por qué

### H1 · El prompt es monolítico y ciego a la pregunta

`llm_backend._build_messages` (≈L395) inyecta el contexto institucional **completo** como
segundo mensaje de sistema, **siempre**, sin mirar la pregunta. Medido:

| | |
|---|---|
| Prompt por turno | ~18.439–18.814 chars (~5.340 tokens estimados) |
| Variación según la pregunta | **0 %** |
| Peso de la pregunta del visitante | **0,3–0,4 %** |
| Reducción con recuperación selectiva | **90,1 % medio** (18.439 → 1.833; rango 83,6–95,1 %) |

Construir el contexto es gratis (0,129 ms en frío, ~0 cacheado). **El coste es enviarlo**:
~5.340 tokens de prefill por turno, cada turno, en un kiosco en vivo.

### H3/H4 · El router es una cascada de subcadenas sin umbral

`skills/router.py::route_local_skill` (≈L14) normaliza con `normalize_text` (que **quita
acentos**) y luego encadena `if any(word in text for word in [...])`. Sin confianza, sin umbral,
sin límites de palabra. El primer `if` que coincide gana.

**El defecto más grave, medido hoy** — el literal `"habla"` en la lista de vulgarismos (≈L21 y
≈L40):

```python
    if any(word in text for word in ["vulgarismo", "vulgarismos", "habla", "voseo", "leismo", "minimo"]):
        return honduras.get_vulgarismos_info()
```

`normalize_text("Háblame")` → `"hablame"`, que **contiene** `"habla"`. Y ese `if` está **antes**
de todo el enrutado UNEV. Resultado verificado en runtime:

```
Háblame de Programación Web        -> Vulgarismos y rasgos lingüísticos del habla hondureña
Háblame de UNEV                    -> Vulgarismos y rasgos lingüísticos del habla hondureña
Háblame de las carreras            -> Vulgarismos y rasgos lingüísticos del habla hondureña
Háblame de la lluvia de peces.     -> Vulgarismos y rasgos lingüísticos del habla hondureña
¿Cuál es el mínimo para entrar?    -> Vulgarismos y rasgos lingüísticos del habla hondureña
```

**«Háblame de…» es la forma más natural en que un visitante pide información**, y el sistema
responde con lingüística hondureña. Peor: `"minimo"` captura «¿cuál es el mínimo para entrar?»,
una pregunta de **admisión**, y la manda al mismo sitio.

**Línea base del router en las 11 preguntas obligatorias**, medida:

| # | Pregunta | Hoy | Correcto |
|---|---|---|---|
| 1 | ¿Cómo estás? | `None` | ✅ |
| 2 | ¿Qué significa UNEV? | `None` | ❌ omisión — debería dar siglas |
| 3 | ¿Qué carreras ofrecen? | resumen de programas | ✅ |
| 4 | ¿Cuánto dura Programación Web? | programa correcto | ✅ |
| 5 | ¿Y cuánto dura? | `None` | ❌ necesita memoria → **WAVE-06** |
| 6 | ¿Dónde queda la UNEV? | dirección | ✅ |
| 7 | ¿Está aprobada por el CES? | aprobación CES | ✅ |
| 8 | Háblame de la lluvia de peces. | **vulgarismos** | ❌ sección equivocada |
| 9 | ¿Qué ves frente a ti? | `None` | ✅ (va por cámara) |
| 10 | ¿Cuál es el precio actual…? | `None` | ✅ (sin capacidad web) |
| 11 | Cuéntame un chiste. | `None` | ✅ |

**4 aciertos de las 7 preguntas que le corresponden**; 1 sección equivocada, 2 omisiones. En las
4 restantes el `None` es el comportamiento correcto.

**Literales inalcanzables** — `normalize_text` quita acentos, así que un literal con acento nunca
coincide. Verificado, **6 literales de test muertos sin equivalente sin acento**:

| Línea | Literal muerto | Consecuencia |
|---|---|---|
| ≈18 | `"hondureño"`, `"hondureña"`, `"hondureñismo"`, `"hondureñismos"` | «¿qué es un hondureñismo?» **no** entra en la rama Honduras |
| ≈37 | `"membreño"` | preguntar por Membreño no llega a próceres |
| ≈50 | `"investigación"` | la palabra sola no enruta |

Y 2 duplicados inofensivos (`"lingüística"` ≈48, `"contemporáneo"` ≈52), que sí tienen su
variante sin acento en la misma condición. Los literales con acento que se pasan **como
argumento** a `get_program_info(...)` son correctos: son claves de datos, no comparaciones. **No
los toques.**

### Hallazgo I · No hay tope al contexto ensamblado

`skills/unev_content.py` define `MAX_FIELD_CHARS = 8000` (≈L28) y lo aplica **por campo**
(≈L305, L313, L315). No hay ningún tope al bloque completo. Con 25 campos al máximo, el peor
caso es **~200 KB** en un solo prompt. Nadie lo ha alcanzado porque el contenido real es
moderado, pero el panel de administración permite editar esos campos: es una bomba de tiempo
operativa, no teórica.

### Hallazgo L · Dos rutas, dos ensamblados

`call.py` y `ConversationService` construyen su contexto por caminos distintos. Todo lo que se
arregle en uno hay que recordarlo en el otro. Esta WAVE crea **un solo** ensamblador; WAVE-07
termina de unificar el resto del pipeline.

### La pieza a reutilizar

`app/hologram/media_router.py` **ya resuelve el enrutado con confianza y umbral** en este mismo
repositorio, y **ya tiene tests**: `MediaRouter` (≈L36), `route` (≈L56), `route_local` (≈L85),
`minimum_confidence` (usado ≈L184). Seguí ese patrón. Inventar un esquema de confianza nuevo
cuando hay uno probado a tres archivos de distancia es un error de revisión.

---

## Precondiciones

```bash
git status --short                      # limpio
git log --oneline -1                    # WAVE-04 commiteada
.venv/bin/python -m pytest tests/ -q    # verde
```
Obligatorias: **WAVE-03** (para medir la reducción) y **WAVE-04** (`get_context_sections`, con
paridad ya probada). Sin ellas, esta WAVE no es verificable.

---

## Alcance

### 1. `build_prompt_package(...)` — un único ensamblador

Una función que reciba la pregunta y el estado disponible, y devuelva el paquete listo para
enviar: mensajes de sistema, contexto seleccionado, contexto de cámara si aplica, y metadatos
para las métricas de WAVE-03 (`context_chars`, `local_skill_hit`, secciones elegidas,
confianza).

Consumida por **`call.py` y `ConversationService`**. Al terminar, debe haber **un solo** lugar
donde se decide qué ve el modelo.

Ubicación sugerida: módulo nuevo bajo `app/` o junto a `llm_backend.py`. Que **no** importe
`call.py`: el docstring de `stream_llm_response` (≈L1066) advierte explícitamente que inyectar
`camera_context` desde el llamador es lo que rompe el ciclo `call ↔ llm_backend`. **Respetá esa
decisión de diseño.**

### 2. Router con confianza y umbral

- **Límites de palabra** en lugar de `in`. Mata `"habla"` dentro de `"hablame"` y `"minimo"`
  dentro de una pregunta de admisión.
- **Puntuación y umbral** siguiendo `minimum_confidence` de `media_router.py`. Bajo el umbral →
  sin sección específica, se recurre a un conjunto por defecto (definilo y documentalo: la
  cabecera con la nota de la sigla, `main_claim`, `description` es un punto de partida
  razonable).
- **Todas las reglas se evalúan** y gana la de mayor puntuación; se termina la semántica de
  "el primer `if` que pega". Es lo que hace que `Háblame de la lluvia de peces` prefiera
  Honduras/cultura sobre vulgarismos.
- **Arreglar los 6 literales muertos** añadiendo su forma sin acento (no borres el original si
  querés legibilidad, pero que exista la variante que sí coincide).
- **Sinónimos**: al menos `duración`/`dura`/`cuánto tiempo`/`años`, `precio`/`costo`/`cuánto
  cuesta`/`mensualidad`, `dirección`/`dónde queda`/`ubicación`/`cómo llego`.
- **Presupuesto de latencia: ≤ 1 ms.** Hoy son 0,0116 ms. Hay cuatro órdenes de magnitud de
  margen, y ese margen es exactamente la razón por la que **no** se usa un clasificador LLM:
  200–800 ms de red para resolver un problema de 0,01 ms. Si tu diseño necesita una llamada de
  red para enrutar, es el diseño equivocado — Puerta 0.

### 3. Presupuesto de contexto con truncado determinista

- Tope **por bloque** y tope **total**, configurables, con valores por defecto explícitos.
- Truncado **determinista**: mismo input → mismo output. Sin dependencia de orden de dict, hash
  ni tiempo.
- Prioridad declarada cuando hay que recortar: los guardarraíles (nota de la sigla, cierre
  anti-invención) **no** se recortan; las secciones de menor confianza sí, primero.
- Reutilizá el `clamp_text` / `MAX_FIELD_CHARS` de `skills/unev_content.py` en lugar de escribir
  otro truncador.

### 4. Migrar las dos rutas

`call.py` (`ask_ai`, `ask_ai_and_speak`) y `ConversationService` pasan a usar
`build_prompt_package`. El contrato de `_build_messages` puede quedarse; lo que cambia es
**quién decide qué contexto recibe**.

### Archivos
Módulo nuevo del ensamblador, `skills/router.py`, `llm_backend.py`, `call.py`,
`app/services/conversation.py`, más tests.

---

## Fuera de alcance

- **Memoria conversacional.** La pregunta 5 («¿Y cuánto dura?») **seguirá fallando** al terminar
  esta WAVE, y eso es lo esperado: es **WAVE-06**. No la cuentes como acierto ni improvises un
  estado de entidad acá.
- Llevar `route_local_skill` a la tubería común para que responda antes del LLM en todos los
  backends → **WAVE-07**. Acá el router **elige secciones**; allá decide si se llama al LLM.
- El modo de evento hardcodeado en `stream_llm_response` → **WAVE-07**.
- La política de cámara (los dos juegos de keywords, la frescura) → **WAVE-08**. Acá sólo pasás
  el `camera_context` que ya te dan.
- Modelo, `max_tokens`, temperatura → **WAVE-09**.
- El dataset de evaluación completo → **WAVE-10**. Acá alcanza con las 11 preguntas.
- **Nada de embeddings, vector store ni RAG.** La decisión arquitectónica del informe es
  recuperación determinista por secciones; 0,01 ms contra 200–800 ms. Si querés reabrirla,
  Puerta 0 — no la reabras en el código.
- Cambiar el contenido de `data/unev_info.json`.

---

## Tests a añadir

Archivos: `tests/test_router_confidence.py` y `tests/test_prompt_package.py` (nuevos).

### Router
| Caso | Qué prueba | Debe fallar sin el fix porque… |
|---|---|---|
| `test_hablame_de_no_cae_en_vulgarismos` | Las 5 consultas medidas arriba (`Háblame de Programación Web`, `de UNEV`, `de las carreras`, `de la lluvia de peces`, `¿cuál es el mínimo para entrar?`) **no** devuelven vulgarismos. | `"habla"` coincide por subcadena. **Es el test más importante del plan.** |
| `test_minimo_va_a_admision` | «¿cuál es el mínimo para entrar?» → sección de requisitos de admisión. | Hoy va a vulgarismos. |
| `test_vulgarismos_sigue_funcionando` | «¿qué vulgarismos se usan en Honduras?» → sí devuelve vulgarismos. | Blindaje: el fix no debe romper el caso legítimo. |
| `test_literales_acentuados_alcanzables` | «¿qué es un hondureñismo?», «háblame de Membreño» enrutan. | Los 6 literales muertos. |
| `test_umbral_de_confianza` | Bajo el umbral → conjunto por defecto, no una sección arbitraria. | No hay umbral hoy. |
| `test_router_bajo_1ms` | 100 consultas, promedio < 1 ms. | Guardarraíl contra un clasificador de red colado. |
| `test_las_11_preguntas_obligatorias` | Tabla parametrizada: pregunta → secciones esperadas. La 5 se marca `xfail` con motivo «memoria, WAVE-06». | Es el criterio de aceptación, ejecutable. |

### `PromptPackage`
| Caso | Qué prueba | Debe fallar sin el fix porque… |
|---|---|---|
| `test_pregunta_general_no_lleva_contexto_unev` | «Cuéntame un chiste» → sin secciones institucionales. | Hoy lleva los 15.516 chars. |
| `test_contexto_medio_bajo_2500_chars` | Promedio de las 11 preguntas ≤ 2.500 chars. | Hoy 18.439. **El número del plan.** |
| `test_tope_total_respetado` | Campos infladas a `MAX_FIELD_CHARS` → el paquete no supera el tope total. | Hoy el peor caso es ~200 KB. |
| `test_truncado_determinista` | Mismo input 10 veces → salida idéntica. | Un dict/set desordenado lo rompe. |
| `test_guardarrailes_nunca_se_recortan` | Con presión de presupuesto extrema, la nota de la sigla y el cierre anti-invención sobreviven. | Es la protección contra alucinaciones. |
| `test_ambas_rutas_mismo_paquete` | Mismo enunciado por voz y por web → paquete equivalente. | Hoy son dos caminos distintos. |
| `test_datos_criticos_presentes` | Para cada una de las 11, el paquete **contiene** el dato necesario para responderla. | **Guardarraíl anti-alucinación: es el riesgo real de esta WAVE.** |

`test_datos_criticos_presentes` es tan importante como el de reducción. Un router que recorta el
90 % y deja fuera el dato que hacía falta no es una mejora: es una regresión peor que el
problema original. Escribí los dos tests **juntos**.

---

## Verificación

```bash
.venv/bin/python -m pytest tests/ -q
.venv/bin/python -m pytest tests/test_router_confidence.py tests/test_prompt_package.py -v
git stash && .venv/bin/python -m pytest tests/test_router_confidence.py -q ; git stash pop
.venv/bin/ruff check .

# Reducción real, contra la línea base de WAVE-03
.venv/bin/python -c "
qs = ['¿Cómo estás?','¿Qué significa UNEV?','¿Qué carreras ofrecen?',
      '¿Cuánto dura Programación Web?','¿Y cuánto dura?','¿Dónde queda la UNEV?',
      '¿Está aprobada por el CES?','Háblame de la lluvia de peces.',
      '¿Qué ves frente a ti?','¿Cuál es el precio actual de algo que requiere internet?',
      'Cuéntame un chiste.']
# Sustituí por el import real del ensamblador:
from <modulo> import build_prompt_package
tot = 0
for q in qs:
    pkg = build_prompt_package(q)
    n = pkg.context_chars
    tot += n
    print(f'{q[:50]:52} {n:6} chars')
print(f'{\"MEDIA\":52} {tot // len(qs):6} chars   (base 18.439, objetivo <=2.500)')
"

# El falso positivo, antes y después
.venv/bin/python -c "
from skills.router import route_local_skill
for q in ['Háblame de Programación Web','Háblame de UNEV','¿Cuál es el mínimo para entrar?']:
    r = route_local_skill(q)
    print(f'{q:34} -> {(r[:60]) if r else None}')
"
```
Pegá las tres salidas. La última es la más elocuente del plan entero.

---

## Criterios de aceptación

1. **Las 5 consultas de «Háblame de…» / «mínimo» ya no devuelven vulgarismos**, y las consultas
   legítimas de vulgarismos siguen funcionando.
2. Las 11 preguntas obligatorias seleccionan las secciones esperadas. La 5 sigue fallando y está
   marcada `xfail` con motivo explícito (WAVE-06).
3. **Contexto medio de las 11 preguntas ≤ 2.500 chars** (base 18.439). Salida pegada.
4. **Tokens de entrada estimados ≤ 750** (base ~5.340), medido con la métrica de WAVE-03.
5. Una pregunta general («Cuéntame un chiste») no lleva **ninguna** sección institucional.
6. `test_datos_criticos_presentes` verde: **cada** una de las 11 tiene en su paquete el dato con
   el que se responde. Sin esto, los criterios 3 y 4 no valen nada.
7. Router ≤ 1 ms promedio.
8. Tope total respetado con campos inflados a `MAX_FIELD_CHARS`; truncado determinista.
9. Guardarraíles presentes en todos los paquetes, incluso bajo presión de presupuesto.
10. Ambas rutas producen paquetes equivalentes para el mismo enunciado.
11. Los 6 literales muertos son alcanzables.
12. Las pruebas previas pasan.

---

## Checklist pre-commit

El compartido de `README.md`, más:

```
[ ] Test anti-alucinación (datos críticos presentes) verde  ← tan obligatorio como la reducción
[ ] Salida de reducción pegada: media <=2.500 chars sobre las 11 preguntas
[ ] Salida del falso positivo pegada: «Háblame de…» ya no da vulgarismos
[ ] La pregunta 5 sigue fallando, marcada xfail con motivo «WAVE-06» — NO se arregló acá
[ ] Cero embeddings, cero vector store, cero llamada de red en el enrutado
    (git diff | grep -iE 'embed|vector|faiss|chroma|sentence.transformer' → vacío)
[ ] El ensamblador NO importa call.py (no se reintrodujo el ciclo call ↔ llm_backend)
[ ] Reutilizado el patrón minimum_confidence de media_router.py, no uno nuevo
[ ] Reutilizado clamp_text/MAX_FIELD_CHARS, no otro truncador
[ ] Literales acentuados pasados como ARGUMENTO a get_program_info() intactos
[ ] Sin dependencias nuevas
[ ] Prueba de humo manual: 3 preguntas reales por voz y 3 por web, respuestas correctas
```

---

## Commit

```
feat(context): WAVE-05 recuperación selectiva de contexto y router con umbral

- build_prompt_package: un único ensamblador de prompt para la ruta de voz y la web
- router con límites de palabra, puntuación y umbral, siguiendo el patrón
  minimum_confidence de media_router.py; se evalúan todas las reglas y gana la mejor
- corregido el falso positivo de "habla": «Háblame de X» ya no cae en vulgarismos
  hondureños, y «¿cuál es el mínimo para entrar?» va a requisitos de admisión
- 6 literales acentuados inalcanzables (hondureño/-a/-ismo/-ismos, membreño,
  investigación) ahora tienen su variante sin acento
- presupuesto por bloque y total con truncado determinista; los guardarraíles
  (sigla UNEV, nota anti-invención) nunca se recortan
- tests: 11 preguntas obligatorias, reducción, y presencia de datos críticos
Cierra: hipótesis 1, 3, 4; hallazgos I, L (parcial — WAVE-07 completa la paridad)
Métrica: contexto medio 18.439 → <medido> chars; tokens estimados 5.340 → <medido>;
         router 4/7 → <medido>

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

## Rollback

Por la naturaleza del cambio, **el flag es obligatorio**:

```bash
HOLOGRAM_SELECTIVE_CONTEXT=0    # vuelve a enviar el contexto completo
```
Con el flag apagado el sistema debe comportarse **exactamente** como antes de esta WAVE
(contexto completo, router en su papel actual). Probalo en un test: es la red de seguridad para
un evento en vivo donde el holograma empieza a decir que no sabe algo que sí está en los datos.

```bash
git revert <sha>                # definitivo
```

---

## Handoff — volcar en `PROGRESS.md`

```markdown
### WAVE-05 — PromptPackage y router determinista
- Commit: <sha> · Fecha: <YYYY-MM-DD>
- Archivos tocados: <...>
- Tests añadidos: tests/test_router_confidence.py, tests/test_prompt_package.py::<casos>
- Dónde vive build_prompt_package: <módulo y símbolo>
- Umbral de confianza elegido: <valor y por qué>
- Conjunto de secciones por defecto (bajo umbral): <lista>
- Topes: por bloque <n>, total <n>
- Métricas antes → después:
  - contexto medio: 18.439 → <n> chars
  - tokens estimados: 5.340 → <n>
  - router en las 11 preguntas: 4/7 → <n>
  - latencia del router: 0,0116 ms → <n>
- Pregunta 5 (follow-up): sigue fallando, xfail, pendiente de WAVE-06
- Prueba de humo manual: <resultado>
- Criterios de aceptación: <1–12>
- Desvíos: <...>
- Hallazgos nuevos (NO arreglados): <...>
- Revisión humana: <OK, fecha>
```

**Después: PARAR.** Y si es posible, **usá el sistema un rato antes de seguir**. Esta WAVE cambia
qué sabe el modelo; los tests cubren las 11 preguntas, no las mil que hará un visitante real. Lo
que aparezca, a `PROGRESS.md`.
