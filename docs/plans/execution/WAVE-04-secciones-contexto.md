# WAVE-04 — Secciones de contexto

| | |
|---|---|
| **Fase** | 2 · Contexto y memoria |
| **Riesgo** | Bajo — refactor con paridad exigida carácter por carácter |
| **Esfuerzo** | ~1 sesión |
| **Modelo sugerido** | `scout` (brief) → Opus (código) → `worker` (tests de paridad) |
| **Cierra hipótesis** | H2 (el contexto es divisible en secciones) |

> Antes de empezar: leé `README.md` y `PROGRESS.md`. Re-localizá los símbolos con
> `graphify query`.

---

## Por qué (hipótesis 2, confirmada)

Hoy el contexto institucional es **atómico**: `get_university_context()` devuelve un bloque de
**15.516 chars** o nada. No hay manera de pedir "sólo la dirección" o "sólo la aprobación del
CES". Cada turno paga los 15.516 chars completos, y la pregunta del visitante representa el
**0,3–0,4 %** del prompt.

La buena noticia es que el bloque **ya está estructurado internamente**. En
`skills/university.py`, `get_university_context` (≈L138) recorre `TEXT_FIELDS` y etiqueta cada
campo con `_CONTEXT_FIELD_LABELS` (≈L109):

```python
    for key in TEXT_FIELDS:
        value = (info.get(key) or "").strip()
        if not value:
            continue
        label = _CONTEXT_FIELD_LABELS.get(key, key)
        lines.append(f"- {label}: {value}")
```

Verificado hoy: **25 campos en `TEXT_FIELDS`, 25 etiquetas en `_CONTEXT_FIELD_LABELS`, en
sincronía perfecta** (cero campos sin etiqueta, cero etiquetas sin campo). Más:

| Pieza del bloque | Contenido |
|---|---|
| Cabecera | 2 líneas: aviso de fuente completa + nota de que la sigla es UNEV, «nunca UNED» |
| 25 campos etiquetados | `name`, `full_name`, `acronyms`, `main_claim`, `description`, `mission`, `vision`, `values`, `approval`, `governance`, `address`, `infrastructure`, `academic_model`, `faculty`, `student_support`, `admission_requirements`, `social_projection`, `virtual_library`, `international_presence`, `website`, `history`, `independence_note`, `itee_campus`, `expotech`, `common_questions` |
| Bloque de programas | 3 programas con descripción íntegra |
| Cierre | 1 línea: «si no está aquí, no inventes» |
| Honduras | 2.438 chars anexados con `"\n\n"` |

**No hay que inventar una taxonomía: ya existe.** El trabajo es exponerla como selector.

Esta WAVE **no cambia ningún comportamiento**. Construye la pieza que WAVE-05 necesita, con
paridad exigida, para que el cambio arriesgado (WAVE-05) llegue sobre una base ya probada. Es
deliberado: separar el refactor sin riesgo del cambio de comportamiento hace que, si algo se
rompe en WAVE-05, se sepa exactamente dónde.

---

## Precondiciones

```bash
git status --short                      # limpio
git log --oneline -1                    # WAVE-03 commiteada
.venv/bin/python -m pytest tests/ -q    # verde
```
WAVE-03 es obligatoria: sin sus métricas no se puede demostrar que esta WAVE no cambió el
tamaño del contexto.

---

## Alcance

### 1. `get_context_sections(keys)` en `skills/university.py`

Un selector que devuelve **sólo** las secciones pedidas, con el mismo formato y el mismo orden
de lectura que hoy.

- Entrada: iterable de claves (las de `_CONTEXT_FIELD_LABELS`) más pseudo-secciones para las
  partes que no son campos de texto: el bloque de programas, la cabecera, el cierre y Honduras.
  Nombralas explícitamente y documentalas (p. ej. `"programs"`, `"honduras"`); no las dejes
  implícitas.
- Salida: el mismo texto que hoy produciría ese subconjunto — mismo prefijo `- `, mismas
  etiquetas, mismo orden de `TEXT_FIELDS` (**el orden de `TEXT_FIELDS` es el orden de lectura;
  no lo reordenes por el orden en que llegan las `keys`**).
- Claves desconocidas: ignoradas silenciosamente o error explícito. Elegí una, documentala, y
  dejá constancia en `PROGRESS.md`. (Recomendación: ignorar, con advertencia en log — un router
  que pide una clave que ya no existe no debe tumbar un turno frente a un visitante.)
- Cabecera y cierre: la nota anti-invención del cierre y la nota «la sigla es UNEV, nunca UNED»
  de la cabecera son **guardarraíles**, no datos. Deben poder incluirse siempre, incluso con un
  subconjunto mínimo. Decidí y documentá si son opt-in u obligatorias.

### 2. `get_university_context()` se conserva, reimplementada encima

```
get_university_context()  ==  get_context_sections(todas las claves)
```
**Carácter por carácter.** No es un objetivo aproximado: es el test de paridad y el criterio de
aceptación de esta WAVE. Todas las llamadas actuales siguen funcionando sin tocarse.

### 3. Caché

`_CONTEXT_CACHE` (≈L24) e `invalidate_context_cache` (≈L27) ya existen y **se reutilizan**.
Ojo: hoy la caché guarda **un** string (el bloque completo). Con subconjuntos, la caché natural
es por sección, o el bloque completo cacheado más ensamblado en caliente. Cualquiera sirve —
construir el contexto cuesta **0,129 ms en frío** y ~0 cacheado, así que esto no es una
optimización, es sólo corrección de invalidación.

Regla: `invalidate_context_cache()` debe seguir limpiando **todo** lo que se cachee. Si añadís
un segundo diccionario de caché y te olvidás de limpiarlo ahí, el panel de administración
editará contenido que el LLM nunca verá. Es el error más probable de esta WAVE.

### 4. Honduras como sección condicional

Hoy Honduras (2.438 chars, ~16 % del bloque) se anexa **siempre**, incluso para «¿cuánto dura
Programación Web?». Pasa a ser una sección más, seleccionable. Acá sólo se hace
**seleccionable**; **quién la selecciona** es WAVE-05.

### Archivos
`skills/university.py` principalmente; `skills/unev_content.py` sólo si hace falta exportar
`TEXT_FIELDS` de otra forma (evitalo). Más tests.

---

## Fuera de alcance

- **Decidir qué secciones pide cada pregunta.** Eso es el router, y es **WAVE-05**. Al terminar
  esta WAVE, todos los llamadores siguen pidiendo *todo*. El contexto medio sigue en 18.439
  chars y **eso es correcto**: si bajó, cambiaste comportamiento y te salíste del alcance.
- `_build_messages` y el ensamblado del prompt → **WAVE-05**.
- Cualquier cambio a `data/unev_info.json` o al contenido institucional. Se refactoriza el
  acceso, no los datos.
- El presupuesto/truncado de contexto → **WAVE-05**.
- Memoria conversacional → **WAVE-06**.
- Tocar `skills/honduras.py` por dentro. Sólo cambia **cuándo** se pide su contexto, no cómo lo
  produce.

---

## Tests a añadir

Archivo: `tests/test_context_sections.py` (nuevo). **Serían los primeros tests directos sobre
`skills/university.py`** — hoy tiene cero.

| Caso | Qué prueba | Debe fallar sin el fix porque… |
|---|---|---|
| `test_todas_las_secciones_reproducen_el_bloque_actual` | `get_context_sections(<todas>) == get_university_context()`, **igualdad exacta de strings**. | `get_context_sections` no existe. **Es el test central.** |
| `test_subconjunto_contiene_solo_lo_pedido` | Pedir `{address}` → contiene la dirección, **no** contiene misión, visión ni programas. | Ídem. |
| `test_orden_de_lectura_estable` | Pedir las claves en orden inverso → salida en el orden de `TEXT_FIELDS`. | Un dict/set desordenado rompería el prompt de forma no determinista. |
| `test_campos_y_etiquetas_en_sincronia` | `set(TEXT_FIELDS) == set(_CONTEXT_FIELD_LABELS)`. | Guardarraíl permanente: hoy están sincronizados (25/25) y deben seguirlo. |
| `test_honduras_es_opcional` | Sin la clave de Honduras, el texto de Honduras no aparece; con ella, sí. | Hoy se anexa incondicionalmente. |
| `test_invalidar_cache_limpia_todo` | Poblar la caché con varios subconjuntos, invalidar, cambiar la fuente → todas las lecturas reflejan el cambio. | Con caché por sección, es el fallo probable. |
| `test_claves_desconocidas` | Comportamiento documentado (ignorar o error), consistente. | Ídem. |
| `test_seccion_vacia_se_omite` | Un campo vacío en la fuente no produce una línea `- Etiqueta: `. | Preserva el `continue` del bucle actual. |

---

## Verificación

```bash
.venv/bin/python -m pytest tests/ -q
.venv/bin/python -m pytest tests/test_context_sections.py -v
git stash && .venv/bin/python -m pytest tests/test_context_sections.py -q ; git stash pop
.venv/bin/ruff check .

# Paridad exacta y ahorro potencial por sección
.venv/bin/python -c "
from skills.university import get_university_context, get_context_sections, _CONTEXT_FIELD_LABELS
full_old = get_university_context()
full_new = get_context_sections(list(_CONTEXT_FIELD_LABELS) + ['programs', 'honduras'])
print('paridad exacta:', full_old == full_new, '| chars:', len(full_old))
for combo in (['address'], ['approval','governance'], ['programs'], ['acronyms','full_name','independence_note']):
    n = len(get_context_sections(combo))
    print(f'{str(combo):48} {n:6} chars  ({100 - n*100//len(full_old)}% menos)')
"
```
Esa última salida es la evidencia de que la reducción de WAVE-05 es alcanzable, medida sobre
código real y no sobre una estimación. Pegala en el reporte.

---

## Criterios de aceptación

1. **`get_context_sections(<todas>)` es idéntico carácter por carácter a
   `get_university_context()`.** Sin excepciones ni "salvo espacios".
2. Un subconjunto contiene sólo lo pedido, con las etiquetas y el orden de lectura originales.
3. El orden de salida no depende del orden de las `keys` de entrada.
4. `TEXT_FIELDS` y `_CONTEXT_FIELD_LABELS` siguen en sincronía (25/25), con un test que lo
   vigile de aquí en adelante.
5. Honduras es opcional y, mientras nadie cambie los llamadores, **sigue incluyéndose**.
6. `invalidate_context_cache()` limpia todas las cachés nuevas (probado con la fuente cambiada).
7. **El contexto medido por WAVE-03 sigue siendo 15.516 chars.** Cero cambio observable. Si
   bajó, esta WAVE se pasó de alcance.
8. Las pruebas previas pasan sin modificarse.

---

## Checklist pre-commit

El compartido de `README.md`, más:

```
[ ] Test de paridad exacta presente y verde  ← el criterio central
[ ] Métrica context_chars de WAVE-03 SIN CAMBIOS (15.516)  ← prueba de no-regresión
[ ] Ningún llamador de get_university_context() fue modificado
    (git diff | grep get_university_context → sólo university.py)
[ ] invalidate_context_cache limpia toda caché nueva, verificado con test
[ ] data/unev_info.json NO está en el diff
[ ] Decisión sobre claves desconocidas y sobre cabecera/cierre documentada
    en el docstring y en PROGRESS.md
[ ] Tabla de ahorro por sección pegada en el reporte
```

---

## Commit

```
refactor(context): WAVE-04 exponer el contexto UNEV por secciones

- get_context_sections(keys) sobre las 25 secciones ya etiquetadas en
  _CONTEXT_FIELD_LABELS, más las pseudo-secciones de programas, cabecera,
  cierre y Honduras
- get_university_context() se reimplementa encima y es idéntica carácter
  por carácter (test de paridad)
- Honduras pasa a sección condicional; por ahora se sigue incluyendo siempre
- invalidate_context_cache limpia toda la caché nueva
- tests/test_context_sections.py: primeros tests directos de skills/university.py
Cierra: hipótesis 2
Métrica: contexto sin cambios (15.516 chars) — habilita la reducción de WAVE-05

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

## Rollback

```bash
git revert <sha>
```
Sin flag: no hay comportamiento nuevo que desactivar. Es la ventaja de haber exigido paridad.

---

## Handoff — volcar en `PROGRESS.md`

```markdown
### WAVE-04 — Secciones de contexto
- Commit: <sha> · Fecha: <YYYY-MM-DD>
- Archivos tocados: <...>
- Tests añadidos: tests/test_context_sections.py::<casos>
- Nombres de las pseudo-secciones: <programs / honduras / cabecera / cierre — los definitivos>
- Cabecera y cierre: <opt-in u obligatorias, y por qué>
- Claves desconocidas: <ignorar / error>
- Estrategia de caché: <por sección / bloque completo + ensamblado>
- Paridad exacta verificada: <sí>
- context_chars: 15.516 → 15.516 (sin cambio, esperado)
- Ahorro por sección medido: <tabla>
- Criterios de aceptación: <1–8>
- Desvíos: <...>
- Hallazgos nuevos (NO arreglados): <...>
- Revisión humana: <OK, fecha>
```

**Después: PARAR.** La siguiente, WAVE-05, es la de mayor riesgo del plan. Entrá con la suite
verde y el contexto intacto.
