# WAVE-005 — Handoff

## Estado

COMPLETA

## Commit base

`6f44e17 feat(hologram): add three-fan admin interface`

## Requisitos cubiertos

Endurecimiento base cero, estado write-only, diagnóstico seguro, build frontend, regresiones de índice y documentación de calibración física.

## Contrato físico write-only

El sistema registra solicitud/envío, no reproducción confirmada. Cada unidad sigue aislada; al hardware solo llega el índice numérico resuelto internamente.

## Contrato de índices base cero

`0..255` inclusivo; cero no se trata como ausencia ni se desplaza. Los IDs semánticos siguen fuera del transporte físico.

## Pruebas del índice 0

Modelos, configuración/reinicio, manager, API `POST /units/top/test`, simulador, variables `HOLOGRAM_CLIP_IDLE=0` y diagnóstico simulado verifican explícitamente cero. Se cubren también 255, -1 y 256.

## Implementado

- `FanUnitStatus` expone `requested_index`, `last_sent_index`, resultado, hora, ID semántico y reintentos, manteniendo campos históricos.
- La UI nombra el estado como índice solicitado/comando enviado, no como reproducción confirmada.
- `/test` preserva el índice opcional cero hasta `play_file(0)`.
- Diagnóstico de catálogo, simulación y conexión real explícita; no manda hardware sin `--connect`.
- Corrección mínima de ProviderConfigCard para lint y build.
- Corrección puntual posterior: `last_send_at` usa epoch real; diagnóstico confirma socket antes de devolver éxito; carga Ollama conserva bloqueo y evita solicitudes duplicadas.

## Archivos creados

- `tests/test_hologram_zero_index.py`
- `tests/test_hologram_diagnostics.py`
- `docs/HOLOGRAM_THREE_FAN_SETUP.md`
- `docs/HOLOGRAM_MEDIA_CATALOG.md`
- `docs/HOLOGRAM_TROUBLESHOOTING.md`

## Archivos modificados

- `app/hologram/models.py`
- `app/hologram/unit_manager.py`
- `frontend/src/lib/hologramApi.ts`
- `frontend/src/components/hologram/LiveHologramStatus.tsx`
- `frontend/src/components/ProviderConfigCard.tsx`
- `scripts/diagnose_hologram.py`
- `tests/test_hologram_controller.py`
- `docs/hologram-control/operations/HARDWARE_VALIDATION.md`
- `docs/hologram-control/implementation/STATUS.md`

## Correcciones de lifecycle

- `tests/test_hologram_unit_manager.py::test_deduplication_reconnection_and_idempotent_shutdown` cubre cierre/worker idempotente.
- `tests/test_hologram_conversation_orchestrator.py::test_orchestrator_lifecycle_is_idempotent_and_prevents_stale_close` cubre contexto tardío.
- `tests/test_hologram_conversation_integration.py::test_async_service_cleans_orchestrator_after_llm_error` cubre cleanup ante fallo LLM.
- No se introdujeron loops, threads ni timers nuevos en producción.

## E2E simulados

- `tests/test_hologram_conversation_orchestrator.py::test_simulated_e2e_careers_turn_controls_all_three_roles` verifica top/center/bottom para UNEV y carreras.
- `tests/test_media_router.py::test_disabled_and_timeout_fall_back_safely` cubre timeout/fallback del submodelo.
- `tests/test_scene_observer.py::test_observer_handles_itee_negation_and_stale_turn` cubre ITEE y turno stale.
- `tests/test_hologram_config_store.py::test_loads_valid_config_and_missing_or_corrupt_falls_back` cubre JSON corrupto/fallback.
- `tests/test_hologram_zero_index.py::test_api_test_with_zero_sends_exact_zero_not_identify_index` y `::test_direct_legacy_failure_keeps_last_successful_index_and_requested_zero` cubren envío directo y fallo físico simulado.

## Aislamiento físico

El manager conserva cola, error, reintento y estado de envío por rol. La simulación registra `role`, IP, índice, resultado y error.

## Compatibilidad heredada

Se mantienen el adaptador de top, variables `HOLOGRAM_TCP_*`/`HOLOGRAM_CLIP_*`, endpoints heredados y el comportamiento sin payload de `/test`.

## Corrección del build frontend

Se eliminó el narrowing imposible de `ollamaStatus` y el setState síncrono en effect. `npm run lint` y `npm run build` ahora pasan.

## Revisión visual

Revisión visual manual: **NO REALIZADA**. Validación automatizada: **REALIZADA** mediante `frontend/src/components/hologram/__tests__/HologramControlPanel.test.tsx` y `frontend/src/components/ProviderConfigCard.test.tsx`.

## Observabilidad

Los valores de envío distinguen `requested_index=0` y `last_sent_index=0`; no se imprimen secretos, prompts ni conversaciones.

## Script de diagnóstico

`--config-only`, `--simulate`, `--role`, `--index` y `--connect` funcionan con `--index 0`. El modo real requiere `--connect` explícito.

## Documentación operativa

Setup independiente de tres fans, catálogo lógico, troubleshooting, calibración y advertencia de hardware write-only/base cero añadidos.

## Seguridad

Rango y roles validados; no hay rutas de archivo arbitrarias ni exposición de control físico a IA. El token API existente no fue reemplazado.

## Rendimiento

No se añadió polling, router, worker ni temporizador duplicado. La rotación conserva reloj inyectable.

## Comandos ejecutados y resultados exactos

```text
.venv/bin/python -m pytest
196 passed in 0.80s

cd frontend && npm run lint
Exit 0

cd frontend && npm run test
18 passed in 0.77s

cd frontend && npm run build
Exit 0

.venv/bin/python -m ruff check de archivos modificados
All checks passed!

.venv/bin/python -m ruff check .
Exit 1: 18 incidencias históricas fuera de los archivos modificados; no aumentaron.

.venv/bin/python scripts/diagnose_hologram.py --config-only
Exit 0

.venv/bin/python scripts/diagnose_hologram.py --simulate
Exit 0

.venv/bin/python scripts/diagnose_hologram.py --simulate --role center --index 0
Exit 0; evento play_file con resolved_index=0

Corrección puntual posterior: `tests/test_hologram_zero_index.py` cubre epoch real, error directo y conservación del último envío; `tests/test_hologram_diagnostics.py` cubre conexión, timeout y archivo corrupto; `ProviderConfigCard.test.tsx` cubre loading de Ollama.

graphify update .
Exit 0: 2394 nodes, 4445 edges, 167 communities; avisos existentes sobre cuatro archivos sin nodos y una arista sin confidence.

git diff --check
Exit 0
```

## Evidencia simulada

El diagnóstico y `test_api_test_with_zero_sends_exact_zero_not_identify_index` demuestran `play_file(0)` sin fallback a `identify_index=255`.

## Evidencia física

NO PROBADA

## Correspondencia de índices

PENDIENTE DE CALIBRACIÓN FÍSICA

## Limitaciones

El socket no entrega telemetría visual; duración/playlist/IP real requieren calibración del operador.

## Riesgos restantes

Las 18 incidencias Ruff globales históricas fuera de archivos modificados siguen pendientes de auditoría/mantenimiento.

## Working tree

Preservar `README.md` y `graphify-out/*` preexistentes/generados; no forzarlos al commit.

## Instrucción exacta para WAVE-006 con Sol

Realiza solo auditoría final: revisa contratos, commits, diff, seguridad, lifecycle, tests y documentación de WAVE-001 a WAVE-005; no construyas funciones nuevas ni declares validación física sin evidencia.
