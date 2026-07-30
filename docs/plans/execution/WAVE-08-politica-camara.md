# WAVE-08 — Política de cámara: un solo gate, frescura explícita

| | |
|---|---|
| **Fase** | 3 · Endurecimiento |
| **Riesgo** | Medio — el fallo se ve en vivo, delante del visitante |
| **Esfuerzo** | 1 sesión |
| **Modelo sugerido** | `scout` (brief obligatorio) → Opus (código) → `worker` (tests) |
| **Cierra hallazgos** | J, K, N |

> Antes de empezar: leé `README.md` y `PROGRESS.md`. Re-localizá los símbolos con
> `graphify query`. Las líneas de este documento son orientativas.

---

## Por qué

### Hallazgo J · Dos listas de palabras visuales que no coinciden

Hay **dos** gates independientes para decidir si una pregunta es visual, y dan respuestas
distintas a la misma pregunta. Medido:

| Gate | Símbolo | Palabras |
|---|---|---|
| Ruta de voz | `call.py::_is_visual_question` ≈L910, sobre `_visual_keywords` ≈L~870–907 | **38** |
| Ruta web / neutra | `camera_context.py::is_visual_object_question` ≈L38, sobre `_VISUAL_OBJECT_HINTS` ≈L14 | **20** |

```
en ambas listas:        16
sólo en call:           22
sólo en camera_context:  4   → 'describeme', 'polo', 'que traigo', 'qué traigo'
```

La divergencia no es teórica. Misma pregunta, dos respuestas:

```
«¿Qué traigo puesto?»   call: False      camera_context: True
```

Un visitante que pregunta qué lleva puesto obtiene descripción por la web y **no** por voz.

Ambos gates usan `in` sobre la cadena completa, sin límites de palabra. Falsos positivos
verificados —idénticos en las dos listas, porque están entre las 16 compartidas:

| Consulta | Se toma por visual por… | Debería ser |
|---|---|---|
| «Háblame de Europa» | `"ropa"` ⊂ `"Europa"` | pregunta general |
| «¿Qué hay que estudiar para entrar?» | `"que hay"` | **pregunta de admisión** |
| «Sigamos adelante» | `"delante"` ⊂ `"adelante"` | ni siquiera es una pregunta |
| «Más adelante te pregunto» | `"delante"` | idem |

El caso de admisión es el que duele: una pregunta institucional legítima activa la inyección de
contexto visual, y el modelo empieza a hablar del uniforme del visitante.

*(Nota para quien venga con la hipótesis previa: `"ven"` **no** está en ninguna de las dos listas
— «¿Cuántos jóvenes estudian aquí?» da `False` en ambas. Los falsos positivos reales son los
cuatro de la tabla.)*

### Hallazgo K · El contexto de cámara nunca se invalida en la ruta web

Hay **dos almacenes distintos** del último análisis, y sólo uno se limpia:

| Almacén | Se limpia al parar la cámara |
|---|---|
| `call._last_camera_analysis` (global de módulo ≈L867) | **Sí** — `stop_camera_thread` lo pone a `{}` (≈L1303) |
| `CameraContextProvider._analysis` (`app/services/vision.py` ≈L19) | **No. Nunca.** |

`CameraContextProvider.update(analysis)` se llama en **un solo sitio**, `main.py` ≈L125, dentro
del callback de detección. `update` es un setter pelado:

```python
    def update(self, analysis: dict | None) -> None:
        """Registra el último análisis de la cámara (lo llamará VisionService)."""
        self._analysis = analysis
```

Sin marca de tiempo, sin TTL, sin invalidación. Y en `POST /api/camera` (`main.py` ≈L637) con
`enabled: false`, **ninguna** de las dos ramas toca `camera_provider`:

```python
        else:
            release = os.getenv("HOLOGRAM_CAMERA_RELEASE_ON_UI_OFF", "0")...
            if release:
                stop_camera_thread()      # limpia call._last_camera_analysis, NO el provider
            else:
                print("[Cámara] UI ocultó/apagó el visor; detección YOLO sigue activa...")
```

Resultado: se apaga la cámara, el visitante se va, llega otro, y **la ruta web sigue describiendo
a la persona del último frame**, indefinidamente. Al reiniciar el proceso desaparece; en una feria
de ocho horas, no.

### Hallazgo N · La frescura vive en globals de módulo con 60 s fijos

`camera_context.py` guarda estado en variables de módulo (≈L140–141) y lo muta dentro de
`build_camera_context` (≈L57–68):

```python
_last_person_time = 0.0
_cached_person_analysis: dict = {}
...
    global _last_person_time, _cached_person_analysis
    ...
        if time.time() - _last_person_time <= 60.0 and _cached_person_analysis:
            active_analysis = _cached_person_analysis
```

Tres problemas en cinco líneas: el **60.0 está fijado a mano** (no hay forma de ajustarlo para un
kiosco con mucho paso), el estado es **global de módulo** (las dos rutas lo comparten sin saberlo,
y ningún test puede aislarlo), y la reutilización es **silenciosa**: el prompt afirma que hay una
persona delante con la misma seguridad tanto si el dato es de hace 200 ms como de hace 59 s.

Un dato visual de hace 59 segundos, presentado como presente, es una alucinación con origen en el
código, no en el modelo.

---

## Precondiciones

```bash
git status --short                      # limpio
git log --oneline -1                    # WAVE-07 commiteada
.venv/bin/python -m pytest tests/ -q    # verde
```

Fase 2 completa. Esta WAVE es independiente del rediseño de contexto, pero el punto único donde
se decide el `camera_context` es el que creó WAVE-05: sin él habría que arreglar dos sitios.

**No hace falta cámara física para implementar ni testear esta WAVE**: todo se prueba con
análisis sintéticos y reloj inyectado. La cámara sólo se usa en la prueba manual final.

---

## Alcance

### 1. Un solo gate visual, con límites de palabra

- **Una** función compartida, en `camera_context.py` (ya es el módulo neutro, y su docstring
  explica que existe justamente para que `call` y `app/` usen la misma lógica: terminá ese
  trabajo).
- **Unión de las dos listas**, revisada: las 38 de `call` más las 4 propias de
  `camera_context`. No descartes ninguna sin anotarlo — cada palabra la puso alguien tras una
  demo.
- **Límites de palabra** en lugar de `in`, para matar `ropa`⊂`Europa` y `delante`⊂`adelante`.
- **`"que hay"` necesita cuidado aparte**: los límites de palabra no lo arreglan, porque «¿qué
  hay que estudiar?» contiene literalmente «que hay». Hace falta una regla más específica (por
  ejemplo exigir que no vaya seguido de «que»), o sacar el literal de la lista y confiar en «qué
  ves»/«qué hay delante». Decidí, documentá la decisión, y cubrila con un test.
- `call._is_visual_question` y `is_visual_object_question` pasan a delegar en la función
  compartida. Si conservás las dos por compatibilidad, que sean cáscaras finas.

### 2. Frescura explícita, configurable, sin globals

- El último análisis se guarda **con marca de tiempo**.
- **TTL configurable** por variable de entorno, con default explícito. **Decisión D3 de
  `PROGRESS.md`**: los 60 s actuales son largos para un kiosco con paso continuo; 10–15 s es más
  honesto. Presentá la recomendación en la puerta de revisión y anotá el valor elegido.
- El estado sale de los globals de módulo y pasa a vivir en un objeto (`CameraContextProvider` es
  el sitio natural: ya sostiene `_analysis`). El **reloj debe ser inyectable** para poder
  testear.
- **Tres estados, no dos**: fresco → se afirma; rancio pero dentro del TTL → se matiza («hace un
  momento había…»); vencido → **no se inyecta contexto visual**. La distinción entre los dos
  últimos es el punto de esta WAVE.

### 3. Invalidación al parar la cámara

- `CameraContextProvider` gana una invalidación explícita, y `POST /api/camera` con
  `enabled: false` la llama **en las dos ramas** (con y sin `HOLOGRAM_CAMERA_RELEASE_ON_UI_OFF`).
  Ojo: en la rama sin release el hilo YOLO sigue corriendo y volverá a alimentar el provider —
  correcto y deseable. Lo que se arregla es que al parar de verdad no quede un frame fósil.
- `stop_camera_thread` debe limpiar **los dos** almacenes, no sólo el suyo.
- Un `update(None)` debe **borrar**, no ser un no-op.

### 4. Estado degradado en la ruta web

Los mensajes de cámara no disponible / sin permisos / sin persona detectada que hoy sólo existen
en la ruta de voz deben llegar también a la web. Un «no te veo bien, ¿podés acercarte?» es mejor
producto que un silencio o una descripción inventada.

### 5. Reglas visuales sólo en preguntas visuales

Las instrucciones de sistema sobre lo visual (no mencionar el uniforme sin que lo pidan, etc.)
sólo entran en el prompt cuando el gate dio positivo. Encaja con el presupuesto de WAVE-05: son
chars que hoy se pagan en preguntas donde no aportan nada.

### Archivos
`camera_context.py`, `app/services/vision.py`, `call.py`, `main.py`, el ensamblador de WAVE-05,
más tests.

---

## Fuera de alcance

- **Cambiar la detección**: YOLO, `vision/person_detector.py`, umbrales de confianza del modelo
  de visión, reconocimiento de logos. Acá se decide **cuándo se usa** el resultado, no cómo se
  produce.
- **Reconocimiento facial, identificación o seguimiento de personas.** No se añade ninguna
  capacidad nueva de identificación, y el dato visual sigue siendo efímero y en memoria. Si algo,
  esta WAVE lo hace caducar antes.
- La política de encendido/apagado de la cámara y `HOLOGRAM_CAMERA_RELEASE_ON_UI_OFF`. Se
  respeta el comportamiento documentado en ≈L639–646; sólo se añade la invalidación.
- El feed MJPEG y sus suscriptores.
- Modelo, `max_tokens`, temperatura → **WAVE-09**.
- **Refactor de `call.py`.** Hay muchos globals de cámara ahí (`_last_camera_analysis`,
  `_person_present`, `_camera_detector`, `_camera_thread`). Tocá sólo lo que exige la
  invalidación.

---

## Tests a añadir

Archivo: `tests/test_camera_policy.py` (nuevo).

| Caso | Qué prueba | Debe fallar sin el fix porque… |
|---|---|---|
| `test_un_solo_gate` | Las 38+4 palabras dan **el mismo** resultado por las dos rutas; «¿Qué traigo puesto?» incluido. | Hoy `call`=False y `camera_context`=True. **Es el hallazgo J.** |
| `test_falsos_positivos_visuales` | «Háblame de Europa», «Sigamos adelante», «Más adelante te pregunto» → **no** visuales. | `in` sin límites de palabra. |
| `test_pregunta_de_admision_no_es_visual` | «¿Qué hay que estudiar para entrar?» → no visual. | `"que hay"`. **El falso positivo que más molesta.** |
| `test_preguntas_visuales_siguen_siendo_visuales` | «¿Qué ves?», «¿qué llevo puesto?», «descríbeme», «¿me ves?» → visuales. | Blindaje: el fix no debe pasarse de estricto. |
| `test_dato_fresco_se_afirma` | Análisis de hace 1 s → contexto en presente. | — |
| `test_dato_rancio_se_matiza` | Dentro del TTL pero viejo → el texto **no** afirma presencia actual. | Hoy afirma igual. **Es el hallazgo N.** |
| `test_dato_vencido_no_se_inyecta` | Pasado el TTL → **sin** contexto visual. | Hoy los 60 s son fijos y el corte es binario. |
| `test_ttl_configurable` | Cambiar el TTL cambia el corte. | `60.0` a mano. |
| `test_invalidacion_al_parar_camara` | Tras parar, `build_context` devuelve `None`. | **Es el hallazgo K: hoy describe gente que se fue.** |
| `test_update_none_borra` | `update(None)` limpia el estado. | Hoy asigna `None`… verificá que además no rompa `build_context`. |
| `test_sin_globals_de_modulo` | Dos instancias no comparten estado. | Hoy `_last_person_time` es global. |
| `test_estado_degradado_en_web` | Sin cámara, la ruta web emite el mensaje degradado. | Sólo existe por voz. |
| `test_reglas_visuales_solo_si_visual` | Una pregunta no visual no lleva las instrucciones visuales. | Hoy van siempre. |

Para todo lo temporal, **reloj inyectado**. Cero `sleep` en la suite.

---

## Verificación

```bash
.venv/bin/python -m pytest tests/ -q
.venv/bin/python -m pytest tests/test_camera_policy.py -v
git stash && .venv/bin/python -m pytest tests/test_camera_policy.py -q ; git stash pop
.venv/bin/ruff check .

# El gate, antes y después (sin cámara: es puro texto)
.venv/bin/python -c "
import call, camera_context as cc
qs = ['¿Qué traigo puesto?','Háblame de Europa','¿Qué hay que estudiar para entrar?',
      'Sigamos adelante','¿Qué ves frente a ti?','¿Qué llevo puesto?','Descríbeme',
      '¿Me ves?','Hola, buenos días','¿Cuántos jóvenes estudian aquí?']
print(f\"{'consulta':40} {'voz':6} {'web':6}\")
for q in qs:
    print(f'{q:40} {str(call._is_visual_question(q)):6} {str(cc.is_visual_object_question(q)):6}')
"

# Tamaño de las listas: debe ser UNA sola fuente
.venv/bin/python -c "
import camera_context as cc
print('palabras del gate compartido:', len(cc._VISUAL_OBJECT_HINTS))
"
```

Pegá la tabla: las dos columnas deben coincidir en las 10 filas, y las cuatro consultas no
visuales deben dar `False` en ambas.

**Prueba manual (requiere cámara):**

1. Ponete delante, preguntá «¿qué ves?» → debe describir.
2. Salí del cuadro, esperá más del TTL, volvé a preguntar → **no** debe describirte.
3. Apagá la cámara desde la UI y preguntá desde la web → **no** debe describir a nadie. *Es el
   hallazgo K; es la prueba que importa.*
4. Preguntá «¿qué hay que estudiar para entrar?» → respuesta de admisión, **sin** mención del
   uniforme.

---

## Criterios de aceptación

1. **Un solo gate**: mismo resultado por las dos rutas en las 42 palabras y en las 10 consultas
   de la tabla. «¿Qué traigo puesto?» ya no divide las rutas.
2. Los cuatro falsos positivos medidos (`Europa`, `que hay que estudiar`, `adelante` ×2) dan
   `False`; las preguntas visuales legítimas siguen dando `True`.
3. El último análisis tiene marca de tiempo; el TTL es configurable y su default está documentado
   (**decisión D3**).
4. Tres estados distinguibles: fresco afirma, rancio matiza, vencido no inyecta.
5. `CameraContextProvider` se invalida al parar la cámara, **en las dos ramas** de
   `POST /api/camera`; `update(None)` borra.
6. El estado de frescura ya no vive en globals de módulo; dos instancias son independientes.
7. La ruta web emite los mensajes de estado degradado.
8. Las instrucciones visuales sólo entran en preguntas visuales. Ahorro de chars medido con la
   métrica de WAVE-03.
9. Reloj inyectado: cero `sleep` en los tests nuevos.
10. Las 4 pruebas manuales hechas y anotadas (la 3 es la crítica).
11. Las pruebas previas pasan.

---

## Checklist pre-commit

El compartido de `README.md`, más:

```
[ ] Tabla de las 10 consultas pegada, con las dos columnas coincidiendo
[ ] Los 4 falsos positivos en False; las visuales legítimas en True
[ ] Decisión sobre "que hay" documentada y cubierta por un test
[ ] Ninguna de las 42 palabras descartada en silencio (las quitadas, anotadas y justificadas)
[ ] TTL configurable; valor elegido y motivo en PROGRESS.md (decisión D3)
[ ] Invalidación llamada en AMBAS ramas de POST /api/camera
[ ] stop_camera_thread limpia los DOS almacenes
[ ] Sin globals de módulo para la frescura (grep de 'global _last_person_time' → vacío)
[ ] Reloj inyectado; cero sleep en tests
[ ] Sin cambios en la detección (git diff --stat sin vision/person_detector.py)
[ ] Sin capacidad nueva de identificación de personas; el dato visual sigue efímero
[ ] Sin refactor oportunista de call.py
[ ] Prueba manual 3 (cámara apagada → la web no describe a nadie) verificada
```

---

## Commit

```
fix(camera): WAVE-08 un solo gate visual, frescura explícita e invalidación

- un único gate visual compartido por las dos rutas (38 palabras en call vs 20 en
  camera_context, sólo 16 en común): «¿Qué traigo puesto?» ya no se comporta
  distinto por voz y por web
- límites de palabra: «Háblame de Europa» (ropa⊂Europa), «Sigamos adelante»
  (delante⊂adelante) y «¿Qué hay que estudiar para entrar?» dejan de tomarse por
  preguntas visuales
- el último análisis lleva marca de tiempo y TTL configurable, con tres estados:
  fresco se afirma, rancio se matiza, vencido no se inyecta; el estado sale de los
  globals de módulo y el reloj es inyectable
- CameraContextProvider se invalida al parar la cámara, en las dos ramas de
  POST /api/camera: la ruta web ya no describe a una persona que se fue
- mensajes de estado degradado también en la ruta web; las instrucciones visuales
  sólo entran en preguntas visuales
Cierra: hallazgos J, K, N
Métrica: TTL 60 s fijos → <n> s configurable; chars ahorrados por turno no visual: <n>

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

## Rollback

```bash
HOLOGRAM_CAMERA_TTL=60          # vuelve al comportamiento temporal previo
HOLOGRAM_VISUAL_GATE=legacy     # vuelve a los dos gates separados
```

```bash
git revert <sha>
```

---

## Handoff — volcar en `PROGRESS.md`

```markdown
### WAVE-08 — Política de cámara
- Commit: <sha> · Fecha: <YYYY-MM-DD>
- Archivos tocados: <...>
- Tests añadidos: tests/test_camera_policy.py::<casos>
- Gate compartido: <módulo y símbolo> · palabras finales: <n>
- Palabras descartadas de las 42 y por qué: <...>
- Decisión sobre "que hay": <...>
- TTL elegido: <n> s (decisión D3) · por qué: <...>
- Umbral fresco/rancio: <...>
- Dónde se invalida el provider: <...>
- Chars ahorrados en turnos no visuales: <n>
- Pruebas manuales:
  1. «¿qué ves?» delante de la cámara: <...>
  2. fuera del cuadro pasado el TTL: <...>
  3. cámara apagada + pregunta por web: <...>
  4. «¿qué hay que estudiar para entrar?» sin mención del uniforme: <...>
- Criterios de aceptación: <1–11>
- Desvíos: <...>
- Hallazgos nuevos (NO arreglados): <...>
- Revisión humana: <OK, fecha>
```

**Después: PARAR.**
