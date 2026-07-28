# WAVE-006 — Fix Handoff

## Estado

CORRECCIONES PREPARADAS PARA REAUDITORÍA; sin commit ni push.

## Commit base

`5ebfee4 feat(hologram): harden zero-index diagnostics`

## Hallazgos bloqueantes

| Hallazgo | Causa | Corrección | Regresión |
|---|---|---|---|
| W6-B01 | `start()` solo creaba worker | `HologramUnitManager.connect()` intenta el socket y lo usan API/diagnóstico | `tests/test_hologram_unit_manager.py::test_explicit_connect_attempts_socket_without_a_play_request_and_is_idempotent`, `::test_explicit_connect_records_socket_failure_without_play_request`, `tests/test_hologram_api.py::test_connect_endpoint_attempts_real_manager_connection_and_reports_failure`, `tests/test_hologram_diagnostics.py::test_real_diagnostic_waits_for_connection_and_sends_zero_after_connect` |
| W6-B02 | `reconfigure()` perdía el estado de rotación | snapshot y restauración de active/paused/posición elegible | `tests/test_hologram_director.py::test_reconfigure_preserves_rotation_active_paused_and_stopped_state` |
| W6-B03 | el adaptador reemplazaba su director | `configure()`/`disable()` reconfiguran la misma instancia | `tests/test_hologram_api.py::test_identity_test_rejects_unknown_id_and_legacy_adapter_keeps_shared_director` |
| W6-B04 | frontend esperaba strings | `RotationMediaStatus` y render de título/índice | `frontend/src/components/hologram/__tests__/HologramControlPanel.test.tsx` |
| W6-B05 | prefijo holograma ausente | gate para todo `/api/hologram/*` si token está activo | `tests/test_auth_token.py::test_hologram_endpoints_require_token_for_reads_and_writes`, `tests/test_hologram_api.py::test_hologram_token_gate_protects_read_and_mutation_when_enabled` |

## Hallazgos secundarios resueltos

- `identify_index` se expone desde `FanUnitStatus` y la tarjeta inicializa el campo con el valor configurado.
- Probar una identidad inexistente devuelve `HOLOGRAM_NOT_FOUND` en vez de informar éxito tras el fallback conversacional.
- `small_model` usa el mismo camino opcional del proveedor ante ambigüedad que `hybrid`.

## Correcciones residuales

| Problema | Causa | Corrección | Regresión |
|---|---|---|---|
| Frontend token | `apiFetch` no añadía el header | `backend.ts` obtiene `VITE_HOLOGRAM_API_TOKEN` y lo añade solo a `/api/hologram/*` | `frontend/src/lib/backend.test.ts` |
| Connect heredado | `holo_connect` solo reconfiguraba | llama `top.connect()` y devuelve error si falla | `tests/test_hologram_api.py::test_legacy_connect_endpoint_reconfigures_the_shared_director`, `::test_legacy_connect_endpoint_returns_error_after_failed_real_attempt` |
| Pausa tras reconfigure | `restore_status()` hacía `start()` y despachaba | restauración pausada interna sin dispatch | `tests/test_promotion_rotation.py::test_restore_paused_state_preserves_current_and_never_dispatches_next_item`, `tests/test_hologram_director.py::test_reconfigure_paused_rotation_keeps_current_without_dispatching_next` |
| Router cacheado | conservaba la configuración del constructor | `start_turn()` reemplaza configuración solo si cambió la identidad del catálogo | `tests/test_hologram_conversation_orchestrator.py::test_new_turn_refreshes_router_config_after_director_reconfiguration` |
| Estado tras reconectar | persistían resultado/error/reintento de fallo | éxito de socket limpia error/reintentos sin tocar índices | `tests/test_hologram_unit_manager.py::test_successful_reconnect_clears_connection_error_without_sending_media` |
| Imagen tras pausa/reconfigure | el manager nuevo no recibía el medio actual después de `shutdown` | reenvía `current` una vez, sin `next` ni deadline | `tests/test_promotion_rotation.py::test_restore_paused_state_preserves_current_and_never_dispatches_next_item`, `tests/test_hologram_director.py::test_reconfigure_paused_rotation_keeps_current_without_dispatching_next` |

## Limitaciones restantes

- Editor de estados de mascota: **PENDIENTE**. No hay endpoint contractual para editar `idle`, `listening`, `thinking` y `speaking`; añadirlo implica ampliar API/UI y queda fuera de esta corrección puntual.
- Callback TTS heredado con `context_id`: **PENDIENTE**. `_host_tts_done()` aún no recibe `context_id`; el orquestador sí protege `finish_turn()` stale (`tests/test_hologram_conversation_orchestrator.py::test_orchestrator_lifecycle_is_idempotent_and_prevents_stale_close`), pero convertir el callback requiere cambiar su contrato.

## Archivos modificados

- `app/hologram/unit_manager.py`
- `app/hologram/models.py`
- `app/hologram/rotation.py`
- `app/hologram/director.py`
- `app/hologram/compatibility.py`
- `app/hologram/media_router.py`
- `auth_token.py`
- `main.py`
- `scripts/diagnose_hologram.py`
- `frontend/src/lib/hologramApi.ts`
- `frontend/src/lib/backend.ts`
- `frontend/src/components/hologram/FanUnitsPanel.tsx`
- `frontend/src/components/hologram/RotationControls.tsx`
- `docs/HOLOGRAM_SCHOOL_DEMO.md`
- `docs/HOLOGRAM_THREE_FAN_SETUP.md`
- `docs/HOLOGRAM_MEDIA_CATALOG.md`
- `docs/HOLOGRAM_TROUBLESHOOTING.md`
- `docs/hologram-control/operations/HARDWARE_VALIDATION.md`
- pruebas y documentación de esta wave.

## Resultados exactos

```text
.venv/bin/python -m pytest
209 passed, 1 warning in 0.72s

.venv/bin/python -m ruff check <archivos Python modificados y sus pruebas>
All checks passed!

cd frontend && npm run lint
Exit 0

cd frontend && npm run test
Test Files  6 passed (6)
Tests  21 passed (21)

cd frontend && npm run build
Exit 0

git diff --check
Exit 0
```

## Evidencia física

NO PROBADA.

## Demostración escolar

- Hardware físico: **NO PROBADO**.
- Correspondencia real de índices: **PENDIENTE**.
- Token para demo local: **DESACTIVADO / OPCIONAL**; `127.0.0.1` y las dos
  variables de token vacías.
- Editor de estados de mascota: **PENDIENTE**.
- La guía usa top `0,1,2,2`, center `0,0,1` y bottom `0,1,2`; HoloMissYou carga
  archivos manualmente y Holograma no modifica playlists.

## Commit y push

No se creó commit ni se hizo push.
