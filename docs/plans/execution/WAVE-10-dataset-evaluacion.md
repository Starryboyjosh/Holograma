# WAVE-10 — Dataset de evaluación y cobertura de `skills/`

| | |
|---|---|
| **Fase** | 3 · Endurecer |
| **Riesgo** | Bajo — no toca código de producción salvo lo mínimo para poder evaluarlo |
| **Esfuerzo** | 1 sesión (el dataset crece después, la infraestructura se hace una vez) |
| **Modelo sugerido** | `scout` (brief) → Opus (arnés de evaluación) → `worker` (**el grueso: casos y tests**) |
| **Cierra** | El agujero de cobertura de la línea base: **0 tests** en `skills/` |
| **Depende de** | WAVE-05, WAVE-06, WAVE-07 |

> Antes de empezar: leé `README.md` y `PROGRESS.md`. Re-localizá los símbolos con
> `graphify query`. Las líneas de este documento son orientativas.

---

## Por qué

Nueve WAVEs cambiaron cómo se elige el contexto, cómo se recuerda un turno anterior, cuándo se
responde sin LLM y con qué presupuesto. Cada una se validó con **sus** tests y con las 11
preguntas obligatorias pegadas a mano en `PROGRESS.md`.

Eso alcanza para ejecutar el plan. **No alcanza para mantenerlo.**

### El agujero medido

De la línea base, textualmente:

```
0 tests cubren skills/router.py, skills/university.py, skills/honduras.py,
  skills/utils.py, skills/event_mode.py
```

Cinco módulos sin una sola prueba — y son exactamente los que deciden **qué sabe el holograma**.
WAVE-04 añadió los primeros de `university.py`, WAVE-05 los primeros de `router.py`, WAVE-07 el
primero de `event_mode.py`. Son tests **del cambio**, no del contenido: prueban que la máquina
funciona, no que las respuestas sean ciertas.

### Lo que hoy no tiene red

Un ejemplo concreto y barato de imaginar: alguien edita `data/unev_info.json` para actualizar la
duración de una carrera y se equivoca de campo. Los 209 tests siguen verdes. El router sigue
enrutando. El contexto sigue midiendo menos de 2.500 caracteres. Y el holograma le dice a un
aspirante, con total seguridad y en dos segundos, un dato falso.

**Las WAVEs anteriores hicieron al sistema rápido y preciso en su enrutado. Ninguna verifica que
lo que dice sea cierto.** Eso es lo que se construye acá.

### Y el otro agujero: las 11 preguntas no son un dataset

Once preguntas escritas a mano en un documento sirvieron para diagnosticar. Como criterio
permanente tienen tres problemas: se ejecutan a mano, se comparan a ojo, y no cubren nada de las
**970 entradas de `cultura_general`** ni de las 25 secciones institucionales que WAVE-04 expuso.
Son la **semilla**, no el conjunto.

---

## Precondiciones

```bash
git status --short                      # limpio
git log --oneline -1                    # WAVE-09 commiteada
.venv/bin/python -m pytest tests/ -q    # verde
```

**Dependencias duras.** El dataset describe el comportamiento que las WAVEs 05, 06 y 07
construyeron. Sin ellas, la mitad de los campos no tiene nada que evaluar:

| Necesita | De | Para poder afirmar |
|---|---|---|
| Router con confianza y umbral | WAVE-05 | `intent_esperado`, `confianza_minima` |
| Secciones seleccionables | WAVE-04/05 | `secciones_esperadas` |
| Memoria y entidad activa | WAVE-06 | los casos encadenados (pregunta 5) |
| Corte pre-LLM y modo de evento | WAVE-07 | `requiere_llm`, paridad de rutas |
| Métricas por turno | WAVE-03 | **todas** las métricas de aceptación |

Verificá que las tres estén commiteadas antes de empezar. Si falta una, esta WAVE se escribe a
medias y hay que reescribirla: es una Puerta 0.

---

## Alcance

### 1. El dataset, versionado y en datos

Un fichero de datos versionado en el repositorio — **no un módulo de Python con literales
dentro de asserts**. Que un profesor o un estudiante pueda añadir un caso sin escribir código es
parte del objetivo: este proyecto lo mantiene un equipo estudiantil.

Cada caso lleva, como mínimo:

| Campo | Qué es | Por qué |
|---|---|---|
| `id` | Identificador estable | Para citarlo en `PROGRESS.md` y en los fallos |
| `pregunta` | El enunciado, tal cual lo diría un visitante | |
| `intent_esperado` | La intención que debe detectar el router | Precisión del router |
| `entidades_esperadas` | Carrera, tema, lugar… | Resolución de referencias (WAVE-06) |
| `secciones_esperadas` | Qué secciones de contexto deben inyectarse | **Recall** de contexto relevante |
| `requiere_llm` | Si debe cortarse local o llegar al modelo | Corte pre-LLM (WAVE-07) |
| `requiere_camara` | Si el contexto visual es pertinente | Política de cámara (WAVE-08) |
| `requiere_web` | Si necesitaría búsqueda web | Hoy **siempre falso útil**: ver INFO-2 |
| `hechos_obligatorios` | Lo que la respuesta **tiene** que contener | Verdad factual |
| `hechos_prohibidos` | Lo que **no** puede aparecer | **Anti-alucinación** |
| `longitud_objetivo` | Rango de longitud de la respuesta | Es un holograma que habla: 400 palabras es un fallo |
| `turno_previo` | Opcional: el caso anterior del que depende | Follow-ups encadenados |

Sobre **`hechos_prohibidos`**: es el campo que más valor tiene y el que más cuesta escribir bien.
No es "cualquier cosa falsa" — es la lista corta de **confusiones plausibles**: la duración de
*otra* carrera, el nombre de otra universidad, una acreditación que la UNEV no tiene. Un caso con
`hechos_prohibidos` vacío es un caso a medio escribir.

`requiere_web` existe porque el prompt de auditoría lo pide y porque el campo documenta la
frontera. **La capa de herramientas web nunca existió** (INFO-2 en `PROGRESS.md`: `git log --all
-S` devuelve cero commits). Marcá los casos que la necesitarían y dejalos como `xfail`
documentado: son la especificación de un plan futuro, no deuda de éste.

### 2. Cobertura mínima del dataset

Las 11 obligatorias son la semilla, **con sus ids fijos y en orden**. Encima de eso:

- Al menos un caso por **cada una de las 25 secciones** institucionales de `_CONTEXT_FIELD_LABELS`.
  Si una sección no tiene ningún caso, nadie va a notar cuando deje de recuperarse.
- Una muestra de `cultura_general` (970 entradas): **no las 970**. Un muestreo representativo y
  estable — misma semilla, mismos casos, o el dataset deja de ser reproducible.
- Los cuatro modos de evento (`normal`, `judges`, `expo`, `admissions`).
- Casos **negativos**: preguntas que el router **no** debe enrutar, y que deben ir al LLM.
- Al menos una cadena de follow-ups de tres turnos.
- Los falsos positivos que WAVE-05 arregló, como **tests de regresión permanentes**: «Háblame de
  Programación Web» tiene que quedar en el dataset para siempre. Es el caso que documenta por qué
  existe el umbral.

### 3. El arnés de evaluación

Un ejecutor que recorre el dataset y produce un informe. Reglas:

- **Sin red por defecto.** Corre con el LLM sustituido por un doble y verifica lo que es
  determinista: intención, entidades, secciones, corte local, longitud del contexto, tiempos de
  enrutado. Eso es lo que entra en la suite de CI.
- **Modo "con LLM" opcional y explícito**, detrás de una variable de entorno, para verificar
  `hechos_obligatorios` / `hechos_prohibidos` contra respuestas reales. **Nunca por defecto, y
  nunca en la suite**: gasta cuota y tiene que ser una decisión de quien la paga.
- Reusa las métricas de WAVE-03. **No instrumentes de nuevo**: si el arnés necesita un dato que
  las métricas no emiten, el arreglo es emitirlo desde el punto único, no medirlo aparte.
- Salida legible: una tabla por métrica y la lista de casos que fallan con el motivo. Un informe
  que sólo dice "87 %" no sirve para arreglar nada.

### 4. Las métricas de aceptación

El arnés reporta, y `PROGRESS.md` recibe:

| Métrica | Cómo se calcula |
|---|---|
| Reducción de tamaño de contexto | chars medios por turno vs. la línea base (18.439) |
| Reducción de tokens de entrada | estimados a 3,5 ch/token, vs. ~5.340 |
| Tasa de acierto de skills locales | casos con `requiere_llm: false` resueltos sin LLM |
| Precisión del router | intención correcta / casos con intención esperada |
| **Recall de contexto relevante** | secciones esperadas que efectivamente se inyectaron |
| Respuestas sin contexto innecesario | casos donde no se inyectó nada de más |
| Paridad de rutas | casos con idéntica decisión por CLI y por WebSocket |
| Tiempo de enrutado | p50 / p95, contra el presupuesto de **≤ 1 ms** de WAVE-05 |
| TTFT | sólo en modo con LLM |
| Tasa de fallback | intentos de proveedor por turno |
| **Tasa de respuesta sin evidencia** | respuestas que afirman un dato que no estaba en el contexto inyectado |

> **No inventes números "bonitos".** Si el recall da 0,72, el informe dice 0,72 y se abre un
> hallazgo. Un dataset ajustado hasta que todo salga verde es peor que no tener dataset: da
> confianza falsa sobre el único componente que puede mentirle a un aspirante.

La última métrica —**respuesta sin evidencia**— es la que justifica toda la WAVE. Es la que
detecta que el modelo completó un dato de su memoria de entrenamiento en vez de leerlo del
contexto, y es el modo de fallo más caro que tiene un kiosco universitario.

### 5. Los primeros tests de contenido de `skills/`

Con el dataset ya existiendo, los cinco módulos sin cobertura dejan de estarlo:

- `skills/router.py` — enrutado sobre el dataset completo, no sobre 11 casos.
- `skills/university.py` — las 25 secciones existen, no están vacías, y respetan el tope.
- `skills/honduras.py` — la muestra de `cultura_general` responde; las entradas tienen contenido.
- `skills/utils.py` — `normalize_text` con acentos, mayúsculas, signos y cadena vacía. Es el
  cimiento del router: si se rompe, se rompe todo lo demás en silencio.
- `skills/event_mode.py` — los cuatro modos, más el inválido.

### 6. Integridad de los datos

Tests que fallan cuando alguien edita un `.json` y se equivoca:

- Los ficheros de `data/` cargan y tienen la forma esperada.
- Ningún campo institucional está vacío ni excede `MAX_FIELD_CHARS` (`skills/unev_content.py` ≈L28).
- `TEXT_FIELDS` y `_CONTEXT_FIELD_LABELS` **siguen sincronizados** (25 y 25). WAVE-04 dependía de
  esa sincronía y hoy no hay nada que la vigile.
- Cada `id` del dataset es único.

### Archivos
Fichero de dataset nuevo (sugerido `tests/data/` o `data/eval/`), arnés de evaluación, más tests.
Código de producción: **sólo** lo mínimo si falta un dato en las métricas de WAVE-03.

---

## Fuera de alcance

- **Arreglar lo que el dataset encuentre.** Es lo más difícil de esta WAVE y la regla es
  inequívoca: cada fallo se anota en `PROGRESS.md` como hallazgo nuevo, con su `id` de caso. Un
  dataset que se escribe *y* se satisface en el mismo commit es un dataset escrito para pasar.
- **Ajustar el dataset para que dé verde.** Si un caso falla porque el sistema está mal, el caso
  se queda como está. Si falla porque el caso está mal escrito, se corrige el caso **y se
  justifica en el commit**.
- **Llamadas de pago.** El modo con LLM no corre en CI ni por defecto, y no se activa sin
  autorización explícita del usuario.
- **Búsqueda web.** INFO-2: nunca existió. Se marcan los casos, no se implementa.
- **Benchmarks de latencia contra proveedores reales.** El arnés mide lo determinista.
- **Evaluación con LLM-como-juez.** Hechos obligatorios y prohibidos son comprobaciones de
  contenido, deterministas y baratas. Un juez LLM añade coste, no determinismo y una segunda
  fuente de alucinación al arnés que existe para detectar alucinaciones.
- Refactorizar `skills/`. Acá se lo prueba, no se lo cambia.
- La reorganización de carpetas, **diferida por decisión explícita del proyecto**.

---

## Tests a añadir

Archivos: `tests/test_eval_dataset.py`, `tests/test_skills_content.py`, `tests/test_data_integrity.py`.

| Caso | Qué prueba | Debe fallar sin el fix porque… |
|---|---|---|
| `test_dataset_carga_y_valida_esquema` | Todo caso tiene los campos obligatorios y tipos correctos. | El dataset no existe. |
| `test_ids_unicos` | Sin `id` duplicados. | Idem; y un duplicado hace irreproducible el informe. |
| `test_las_11_obligatorias_estan` | Las 11 semilla están, con sus ids y en orden. | Es la continuidad con WAVE-03/05/06. |
| `test_todas_las_secciones_tienen_caso` | Las 25 secciones aparecen en algún `secciones_esperadas`. | Una sección sin caso es una sección que puede desaparecer sin que nadie lo note. |
| `test_hechos_prohibidos_no_vacios` | Ningún caso factual los deja vacíos. | Guardarraíl contra casos a medio escribir. |
| `test_enrutado_sobre_el_dataset` | Intención y entidades sobre **todos** los casos. | Primer test real de `skills/router.py` a escala. |
| `test_recall_de_secciones` | Las secciones esperadas se inyectan. | La métrica que nadie mide hoy. |
| `test_corte_local_donde_corresponde` | `requiere_llm: false` → sin LLM. | Verifica WAVE-07 sobre el dataset, no sobre 11 casos. |
| `test_paridad_sobre_el_dataset` | Misma decisión por ambas rutas, en todos los casos. | Extiende `test_paridad_cli_vs_web` de WAVE-07. |
| `test_falsos_positivos_de_wave_05_no_vuelven` | «Háblame de Programación Web» y compañía. | **Regresión permanente.** Es el test que impide que el bug de `"habla"` vuelva. |
| `test_follow_ups_encadenados` | La cadena de tres turnos resuelve las referencias. | Verifica WAVE-06 más allá de la pregunta 5. |
| `test_tiempo_de_enrutado_p95` | p95 bajo el presupuesto de ≤ 1 ms. | Guardarraíl: el router no puede engordar con el dataset. |
| `test_los_cuatro_modos_sobre_el_dataset` | Los cuatro modos, cobertura de `event_mode.py`. | Módulo con cobertura cero. |
| `test_normalize_text` | Acentos, mayúsculas, signos, cadena vacía, unicode raro. | `skills/utils.py` no tiene ni un test y **todo** el router depende de él. |
| `test_secciones_no_vacias_ni_desbordadas` | Las 25 secciones tienen contenido y respetan `MAX_FIELD_CHARS`. | Primer test de contenido de `university.py`. |
| `test_cultura_general_muestra` | La muestra de las 970 entradas responde con contenido. | `skills/honduras.py` sin tests. |
| `test_campos_y_etiquetas_sincronizados` | `TEXT_FIELDS` (25) y `_CONTEXT_FIELD_LABELS` (25) coinciden. | WAVE-04 asumió esta sincronía y **nada la vigila**. |
| `test_datos_json_cargan` | Los ficheros de `data/` cargan y tienen la forma esperada. | Un `.json` roto hoy se descubre en producción. |

El modo con LLM **no** aporta casos a esta tabla: vive en el arnés, detrás de su variable de
entorno, y su salida se pega a mano en `PROGRESS.md`.

---

## Verificación

```bash
.venv/bin/python -m pytest tests/ -q
.venv/bin/python -m pytest tests/test_eval_dataset.py tests/test_skills_content.py tests/test_data_integrity.py -v
.venv/bin/ruff check .

# Cobertura de los cinco módulos que estaban en cero
.venv/bin/python -m pytest tests/ -q --cov=skills --cov-report=term-missing 2>/dev/null \
  || echo "sin pytest-cov: contá los tests por módulo a mano y anotalo"

# El arnés, sin red
.venv/bin/python -m <arnes> --dataset <ruta> --sin-llm
```

Pegá el informe del arnés **entero** en `PROGRESS.md`. Es el entregable de esta WAVE: la primera
foto medida y reproducible del sistema completo.

```bash
# Sólo con autorización explícita del usuario, y nunca en CI:
# HOLOGRAM_EVAL_CON_LLM=1 .venv/bin/python -m <arnes> --dataset <ruta>
```

**Prueba manual obligatoria:**

1. Rompé un dato a propósito en un `.json` de `data/` (una duración, un nombre). Corré el arnés.
   **Tiene que fallar y decir qué caso.** Revertí el cambio. *Si no falla, el dataset no sirve.*
2. Añadí un caso nuevo al dataset **sin tocar código**. Debe entrar en la evaluación solo.
3. Corré el arnés dos veces seguidas: el mismo informe, sin variación en el muestreo.

El paso 1 es la prueba de que esta WAVE hizo lo que dice. Anotá los tres resultados.

---

## Criterios de aceptación

1. El dataset existe, versionado, en datos, y lo puede editar alguien que no programe.
2. Contiene las 11 obligatorias con sus ids, más cobertura de las 25 secciones, muestra de
   `cultura_general`, los cuatro modos, casos negativos y una cadena de follow-ups.
3. Todo caso factual tiene `hechos_obligatorios` **y** `hechos_prohibidos` no vacíos.
4. El arnés corre **sin red** por defecto y produce el informe completo de métricas.
5. El modo con LLM existe, está detrás de variable de entorno, **no** corre en la suite y no se
   usó sin autorización explícita.
6. Las 11 métricas de aceptación están calculadas y pegadas en `PROGRESS.md`, **con los números
   reales**, incluidos los que salieron mal.
7. Los cinco módulos de `skills/` que tenían **0 tests** ahora tienen tests de contenido.
8. `TEXT_FIELDS` y `_CONTEXT_FIELD_LABELS` tienen un test de sincronía.
9. Romper un dato en `data/` hace fallar el arnés, con el caso identificado (verificado a mano).
10. El arnés es reproducible: dos ejecuciones, el mismo informe.
11. **Todo fallo encontrado está anotado como hallazgo nuevo en `PROGRESS.md`, con su `id` de
    caso — y ninguno se arregló en este commit.**
12. Las pruebas previas pasan.

---

## Checklist pre-commit

El compartido de `README.md`, más:

```
[ ] Dataset en datos, no en asserts; editable sin escribir código
[ ] Las 11 obligatorias presentes con ids estables
[ ] Las 25 secciones cubiertas por al menos un caso
[ ] hechos_prohibidos no vacíos en los casos factuales
[ ] Arnés sin red por defecto; modo con LLM detrás de variable de entorno
[ ] Cero llamadas de pago hechas sin autorización explícita
[ ] Métricas pegadas en PROGRESS.md con los números REALES (incluidos los malos)
[ ] Ningún fallo del dataset arreglado en este commit; todos anotados con su id
[ ] Ningún caso "ajustado" para dar verde (y si se corrigió alguno, justificado en el commit)
[ ] Los 5 módulos de skills/ con tests de contenido
[ ] Test de sincronía TEXT_FIELDS <-> _CONTEXT_FIELD_LABELS verde
[ ] Prueba manual 1 hecha: romper un dato hace fallar el arnés
[ ] Arnés reproducible: dos corridas, mismo informe
[ ] Código de producción tocado: sólo lo imprescindible para las métricas (diff revisado)
[ ] Sin refactor de skills/
```

---

## Commit

```
test(eval): WAVE-10 dataset de evaluación y cobertura de skills/

- dataset versionado en datos, editable sin programar: intención, entidades,
  secciones esperadas, hechos obligatorios y prohibidos, longitud objetivo
- semilla: las 11 preguntas obligatorias, más las 25 secciones institucionales,
  muestra de cultura_general, los cuatro modos de evento y casos negativos
- arnés de evaluación sin red por defecto, reutilizando las métricas de WAVE-03;
  el modo con LLM queda detrás de variable de entorno y fuera de la suite
- primeros tests de contenido de skills/router.py, university.py, honduras.py,
  utils.py y event_mode.py: los cinco pasan de 0 tests a cubiertos
- test de sincronía TEXT_FIELDS <-> _CONTEXT_FIELD_LABELS, del que WAVE-04
  dependía sin que nada lo vigilara
- los falsos positivos que cerró WAVE-05 quedan como regresión permanente
Cierra: el agujero de cobertura de la línea base (0 tests en skills/)
Métrica: contexto <n> chars · tokens <n> · router <n>% · recall de secciones <n>%
         paridad <n>/<n> · respuestas sin evidencia <n>%
         hallazgos nuevos abiertos: <n> (ver PROGRESS.md)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

## Rollback

Esta WAVE **no necesita flag**: no cambia comportamiento de producción. El rollback es borrar
tests.

```bash
git revert <sha>
```

Si un test nuevo falla en CI, la respuesta correcta **no** es borrarlo ni marcarlo `skip`: es
abrir el hallazgo. Un test rojo que dice la verdad vale más que una suite verde que no mira.

---

## Handoff — volcar en `PROGRESS.md`

```markdown
### WAVE-10 — Dataset de evaluación y cobertura de skills/
- Commit: <sha> · Fecha: <YYYY-MM-DD>
- Archivos tocados: <...>
- Dataset: <ruta> · <n> casos · versión <n>
- Arnés: <módulo y cómo se corre>
- Tests añadidos: <archivo::caso, ...>
- Cobertura de skills/: 0 → <n> tests en <n> módulos
- Informe del arnés (sin LLM):
  | Métrica | Base | Ahora |
  |---|---|---|
  | Contexto medio (chars) | 18.439 | <n> |
  | Tokens de entrada | ~5.340 | <n> |
  | Precisión del router | 4 de 7 aplicables | <n> |
  | Recall de secciones | — | <n> |
  | Tasa de skills locales | — | <n> |
  | Paridad de rutas | — | <n>/<n> |
  | Enrutado p50 / p95 | 0,0116 ms | <n> / <n> |
  | Respuestas sin evidencia | — | <n> |
- Modo con LLM ejecutado: <sí/no> · autorizado por: <quién> · resultados: <...>
- Pruebas manuales:
  1. dato roto detectado: <...>
  2. caso nuevo sin tocar código: <...>
  3. reproducibilidad: <...>
- HALLAZGOS NUEVOS (anotados, NO arreglados): <lista con id de caso>
- Criterios de aceptación: <1–12>
- Desvíos: <...>
- Revisión humana: <OK, fecha>
```

**Después: PARAR.** Acá termina el plan de diez WAVEs.

Lo que queda no es más ejecución de este runbook, es el trabajo que el runbook habilita: los
hallazgos que el dataset acaba de abrir, la reorganización de carpetas diferida por decisión
explícita del proyecto, SEC-1 (la rotación de la clave, que sigue siendo acción del operador) y,
si el equipo lo quiere, la capa de herramientas web — que **nunca existió** y necesita su propio
plan.

Antes de cerrar, actualizá la tabla de **Objetivos numéricos** de `PROGRESS.md` con la columna
"conseguido". Es la única forma de saber si este plan sirvió, y el número que no se alcanzó es
tan informativo como el que sí.
