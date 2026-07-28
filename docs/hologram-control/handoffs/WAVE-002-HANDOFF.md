# WAVE-002 — Handoff

## Estado

COMPLETA

## Commit

Pendiente: la implementación está sobre `aeb4fa7`; esta ejecución no creó un commit nuevo.

## Requisitos cubiertos

- Rotación continua del ventilador inferior sin dependencia de LLM.
- Pausa, reanudación, stop, foco de medio/categoría y continuación desde el siguiente elemento.
- Reloj virtual inyectable y un único worker de rotación.
- Simulador reusable de tres unidades con fallos, latencia y eventos semánticos.
- CRUD administrativo de unidades, identidades y promociones.
- API de rotación, identificación y estado detallado.
- Compatibilidad con `/api/hologram/connect`, `/disconnect`, `/command` y campos históricos de `/status`.

## Implementado

- `PromotionRotationManager` ordena por prioridad descendente e ID, omite medios deshabilitados/no rotables, repite la lista y limpia contextos de forma idempotente.
- `RealClock` usa `Event.wait`; `VirtualClock` y `tick()` permiten pruebas sin `sleep` real.
- `HologramDirector` expone la API semántica de rotación y mantiene el director único del proceso.
- `HologramSimulator` registra timestamp, rol, IP, comando, ID semántico, índice resuelto, contexto, resultado y error.
- `main.py` administra el catálogo con `HologramConfigStore`, valida cuerpos y devuelve códigos `HOLOGRAM_*` sin stack traces.
- El middleware existente de `HOLOGRAM_API_TOKEN` protege las escrituras; no se introdujo autenticación paralela.

## Archivos creados

- `app/hologram/rotation.py`
- `app/hologram/simulator.py`
- `tests/test_promotion_rotation.py`
- `tests/test_hologram_api.py`
- `tests/test_hologram_simulator.py`

## Archivos modificados

- `app/hologram/models.py`
- `app/hologram/unit_manager.py`
- `app/hologram/director.py`
- `app/hologram/__init__.py`
- `main.py`
- `docs/hologram-control/implementation/STATUS.md`

## Decisiones tomadas

- La rotación no introduce un segundo transporte: envía solicitudes semánticas al `HologramUnitManager` inferior.
- La actualización administrativa reemplaza el catálogo de forma atómica y reconfigura el director, cerrando primero workers/rotación anteriores.
- `identify_index` es un campo configurable de unidad, con 255 como valor seguro por defecto; no se asignan IPs físicamente.
- Las rutas heredadas siguen usando el adaptador de `top`; en el lifespan web se reinyectan sobre el director único.

## Compatibilidad preservada

- Se mantienen los cuatro endpoints heredados y sus campos `connected`, `ip`, `port` y `ai_paused`.
- No se modificaron `call.py`, `ConversationService`, el frontend ni `HologramFanController`.
- No se añadió base de datos ni se expusieron índices a ninguna interfaz semántica.

## Rotación implementada

- Tres elementos: orden determinista, loop, omisión de deshabilitados, pausa/reanudación y cierre limpio.
- Foco de elemento y categoría con contexto; categorías con múltiples medios avanzan internamente.
- `finish_context()` es idempotente y vuelve al siguiente elemento general.
- Lista vacía y unidad inferior desconectada quedan en estado seguro.

## API implementada

- Unidades: listar, actualizar, conectar, desconectar, identificar y test.
- Identidades: listar, crear, actualizar, eliminar (protegiendo Holomind/default) y test.
- Promociones: listar, crear, actualizar, eliminar, test individual y test por categoría.
- Rotación: start, pause, resume, stop y status.
- Estado global con estado por unidad, rotación, contexto, actual/siguiente y modo.

## Simulador implementado

- Tres IP/roles independientes, conexión/desconexión, fallo de conexión, fallo de envío, latencia y registro ordenado.
- El reloj puede ser virtual para pruebas deterministas.

## Pruebas añadidas

- `tests/test_promotion_rotation.py`: loop, orden, pausa, contexto, categoría, lista vacía y cierre.
- `tests/test_hologram_api.py`: CRUD, validación de rol/default y ciclo de rotación.
- `tests/test_hologram_simulator.py`: tres roles, eventos semánticos, fallos y recuperación.

## Comandos ejecutados y resultados exactos

```text
.venv/bin/python -m pytest tests/test_hologram_controller.py tests/test_hologram_config_store.py tests/test_hologram_unit_manager.py tests/test_hologram_director.py
18 passed in 0.19s

.venv/bin/python -m pytest tests/test_promotion_rotation.py tests/test_hologram_simulator.py tests/test_hologram_api.py
7 passed in 0.28s (primera ejecución; después se corrigió la sincronización virtual)

.venv/bin/python -m pytest
168 passed in 0.77s

.venv/bin/python -m ruff check app/hologram tests/test_promotion_rotation.py tests/test_hologram_api.py tests/test_hologram_simulator.py main.py
All checks passed!

.venv/bin/python -m ruff check .
Exit 1: 21 incidencias preexistentes ajenas a WAVE-002 en call.py, skills/honduras.py, stt/listener.py, tests/test_custom_object_interval.py, tests/test_hotwords_cache.py, utils.py y vision/person_detector.py.

graphify update .
Exit 0: 2125 nodes, 3837 edges; Graphify mantuvo sus avisos existentes sobre cuatro archivos sin nodos y una arista sin `confidence`.

git diff --check
Exit 0
```

## Evidencia

- Todas las pruebas físicas usan simulador/fakes; no se probó hardware real.
- La suite completa de regresión permanece verde.
- No hay `sleep()` real en las pruebas de rotación.

## Limitaciones

- No se implementó MediaRouter, integración con LLM ni frontend administrativo.
- El simulador aún no sustituye automáticamente el `controller_factory` del manager TCP; sirve como fixture/event recorder reusable.
- Las escrituras concurrentes del catálogo heredan el lock por proceso de WAVE-001.

## Riesgos restantes

- `ruff check .` mantiene deuda histórica fuera del alcance.
- La correspondencia física de IP/rol debe confirmarse por el operador mediante `identify`.
- Debe validarse en hardware real el índice de identificación elegido por cada playlist.

## Trabajo pendiente

- Integrar MediaRouter y la decisión contextual de `ScenePlan` en WAVE-003.

## Instrucción exacta para WAVE-003

Implementa exclusivamente MediaRouter e integración contextual de `ScenePlan`; consume `HologramDirector` y `PromotionRotationManager` por IDs semánticos, pausa/reanuda el contexto inferior mediante sus APIs, y no expongas IP, puerto ni índice a la IA. Conserva los endpoints heredados y el simulador de WAVE-002.
