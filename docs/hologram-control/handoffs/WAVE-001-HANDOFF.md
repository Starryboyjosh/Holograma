# WAVE-001 — Handoff

## Estado

COMPLETA

## Commit

Pendiente: esta ejecución no creó commits.

## Requisitos cubiertos

- Dominio validado para roles, catálogo, ScenePlan y estado.
- Catálogo JSON seguro, atómico y con backup.
- Un manager y worker aislado para cada unidad.
- Director semántico para top, center y bottom; Holomind como fallback.
- Adaptador de compatibilidad de una unidad sobre `top`.

## Implementado

- `HologramConfigStore` usa JSON validado, archivo temporal, `os.replace`, backup de la última configuración válida y lock por ruta en proceso.
- `HologramUnitManager` reutiliza `HologramFanController`, con cola, deduplicación, reconexión y cierre idempotente.
- `HologramDirector` resuelve IDs a índices internamente y aísla los fallos por unidad.
- `create_hologram_manager()` conserva el punto de entrada heredado mediante el adaptador, sin eliminar `HologramStateManager` ni los endpoints existentes.

## Archivos creados

- `app/hologram/__init__.py`
- `app/hologram/models.py`
- `app/hologram/config_store.py`
- `app/hologram/unit_manager.py`
- `app/hologram/director.py`
- `app/hologram/compatibility.py`
- `tests/test_hologram_config_store.py`
- `tests/test_hologram_unit_manager.py`
- `tests/test_hologram_director.py`

## Archivos modificados

- `hologram_controller.py`
- `docs/hologram-control/implementation/STATUS.md`

## Decisiones tomadas

- El JSON ausente o corrupto devuelve un catálogo seguro en memoria, sin sobrescribir el archivo dañado.
- El catálogo completo habilita tres unidades; el modo heredado configura exclusivamente `top` desde `HOLOGRAM_TCP_IP`, puerto y clips heredados.
- El endpoint manual heredado sigue siendo una vía explícita de operador; las rutas de IA usan únicamente métodos semánticos del director.

## Compatibilidad preservada

- `HOLOGRAM_TCP_IP`, `HOLOGRAM_TCP_PORT` y `HOLOGRAM_CLIP_*`.
- `HologramStateManager` sigue disponible.
- `create_hologram_manager`, `set_state`, `configure`, `disable`, `execute`, `start`, `close` y los endpoints existentes.

## Pruebas añadidas

- Configuración válida, ausente, corrupta, backup, escritura temporal y contratos inválidos.
- Dedupe, reconexión, concurrencia, cierre y workers de unidades.
- Enrutamiento correcto por rol, tres IP distintas, fallback Holomind y cierre del director.

## Comandos ejecutados y resultados exactos

```text
python -m pytest tests/test_hologram_controller.py tests/test_app_services.py
/usr/bin/python: No module named pytest

.venv/bin/python -m pytest tests/test_hologram_controller.py tests/test_app_services.py
20 passed in 0.15s

.venv/bin/python -m pytest tests/test_hologram_config_store.py tests/test_hologram_unit_manager.py tests/test_hologram_director.py tests/test_hologram_controller.py
18 passed in 0.20s

.venv/bin/python -m pytest
161 passed in 0.91s

.venv/bin/python -m ruff check .
Exit 1: 21 incidencias preexistentes. El alcance nuevo pasa `ruff check` focalizado. Persisten incidencias en call.py, skills/honduras.py, stt/listener.py, utils.py, vision/person_detector.py y pruebas ajenas.

.venv/bin/python -m ruff check app/hologram tests/test_hologram_config_store.py tests/test_hologram_unit_manager.py tests/test_hologram_director.py
All checks passed!

graphify update .
Exit 0: Code graph updated (con aviso del extractor sobre una arista sin `confidence`).

git diff --check
Exit 0
```

## Evidencia

- No se realizó ninguna prueba de hardware físico.
- Todas las pruebas ejecutadas usan fakes para el transporte de ventiladores.

## Limitaciones

- No se implementó MediaRouter, rotación promocional autónoma, API administrativa ni UI nueva.
- El lock de escritura es por proceso; no incorpora un bloqueo interproceso.

## Riesgos restantes

- El catálogo debe ser cargado e inyectado por el ciclo de vida de aplicación en la siguiente integración; el adaptador heredado continúa basado en entorno.
- El `ruff check .` global tiene deuda preexistente ajena a esta wave.

## Trabajo pendiente

- WAVE-002: MediaRouter y aplicación contextual de `ScenePlan`.

## Instrucción exacta para WAVE-002

Implementa exclusivamente el router semántico y la integración de ScenePlan indicada por WAVE-002; consume `HologramDirector` por IDs, no introduzcas IP, puertos o índices en IA, y conserva el adaptador heredado de WAVE-001.
