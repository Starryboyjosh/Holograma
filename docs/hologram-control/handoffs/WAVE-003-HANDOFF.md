# WAVE-003 — Handoff

## Estado

COMPLETA

## Commit base

`bab1f14 feat(hologram): add rotation simulator and admin API` (con WAVE-001 en `aeb4fa7`). Esta ejecución no creó un commit nuevo.

## Requisitos cubiertos

- Routing local, ranking de catálogo, fallback y submodelo opcional limitado.
- ScenePlan validado, sin hardware ni texto TTS.
- Orquestación compartida para rutas sync y async.
- Observer de respuesta con máximo un cambio de identidad por turno.
- Cleanup idempotente, protección contra cierres tardíos y evidencia E2E simulada.

## Implementado

- Normalización de acentos, capitalización, puntuación y espacios.
- Reglas para Holomind, UNEV, ITEE, carreras, admisiones, becas y promociones por ID/título/categoría/keywords.
- Ranking determinista y máximo cinco candidatos para el submodelo.
- Protocolo de proveedor sin dependencia de SDK ni director/transporte.
- Timeout, validación de confianza/IDs/categorías y fallback seguro.
- `HologramConversationOrchestrator` con contextos UUID, generación activa y cierre fail-soft.

## Archivos creados

- `app/hologram/media_router.py`
- `app/hologram/router_provider.py`
- `app/hologram/router_prompts.py`
- `app/hologram/scene_observer.py`
- `app/hologram/conversation_orchestrator.py`
- `tests/test_media_router.py`
- `tests/test_scene_observer.py`
- `tests/test_hologram_conversation_orchestrator.py`
- `tests/test_hologram_conversation_integration.py`

## Archivos modificados

- `app/hologram/__init__.py`
- `app/hologram/models.py`
- `app/hologram/director.py`
- `app/hologram/rotation.py`
- `app/services/conversation.py`
- `call.py`
- `main.py`
- `docs/hologram-control/implementation/STATUS.md`

## Decisiones tomadas

- El submodelo es un protocolo inyectable; no se añadió un proveedor LLM nuevo ni se modificaron los principales.
- El router solo recibe texto corto y candidatos semánticos; no recibe catálogo físico, IP, puerto, índice ni sockets.
- La ruta async delega las llamadas síncronas del orquestador a `asyncio.to_thread`.
- El director aplica planes promocionales mediante el manager de rotación y su `context_id`, no mediante índices expuestos.

## MediaRouter

- `local`, `hybrid`, `disabled` y modos heredados de routing son compatibles.
- Coincidencias claras evitan al submodelo; empates o baja confianza pueden usarlo en `hybrid`.
- Respuestas inválidas, timeout, IDs inventados, promociones deshabilitadas y categorías inválidas terminan en fallback Holomind + rotación normal.

## Submodelo pequeño

- `MediaRouterProvider` recibe `MediaRouteRequest` limitado a mensaje/contexto breve/modo/candidatos.
- Se protege con `small_model_timeout_seconds` y un único executor por router, no por chunk.
- No se configuró un proveedor físico por defecto; debe inyectarse desde una futura configuración operacional.

## ScenePlan

- Todo resultado válido es un `ScenePlan` con identidad, acción, ID/categoría, confidence, source, reason code y context_id.
- Ningún ScenePlan contiene índice, IP, puerto, TCP o texto para TTS.

## SceneObserver

- Buffer corto y determinista del texto realmente generado.
- UNEV/ITEE se corrigen solo tras hold, respetan negación y máximo un cambio por contexto.
- No edita texto, no emite WebSocket ni manda metadata al TTS.

## Integración sync

- `call.ask_ai_and_speak()` usa el orquestador compartido y observa tokens sin alterar lo que se pronuncia.
- `chat_to_voice()` inicia/cierra contexto alrededor de la ruta no streaming.
- El estado listening se comunica al orquestador cuando el micrófono se abre.

## Integración async

- `ConversationService` acepta el orquestador por inyección.
- Conserva exactamente los eventos públicos existentes; no expone ScenePlan.
- Observa chunks internamente, marca speaking al iniciar audio, y limpia en fallo/fin/cancelación.

## Compatibilidad preservada

- Los endpoints, API administrativa, adaptador heredado y `HologramStateManager` se mantienen.
- No se modificaron protocolo TCP, STT, visión, proveedores LLM principales ni frontend.
- Los fakes heredados de managers con `request(index, media_id)` siguen funcionando.

## Pruebas añadidas

- Router: reglas, normalización, catálogo deshabilitado, candidatos, hybrid, timeout y fallback.
- Observer: chunks, hold, negación, stale context y máximo un cambio.
- Orquestador: lifecycle, fallos, turnos solapados y E2E con simulador.
- Integración: `call.py`, `ConversationService`, stream público y cleanup de error.

## Comandos ejecutados y resultados exactos

```text
.venv/bin/python -m pytest tests/test_app_services.py tests/test_llm_unify.py tests/test_llm_backend.py tests/test_hologram_controller.py tests/test_hologram_config_store.py tests/test_hologram_unit_manager.py tests/test_hologram_director.py tests/test_promotion_rotation.py tests/test_hologram_api.py tests/test_hologram_simulator.py
68 passed in 0.43s

.venv/bin/python -m pytest tests/test_media_router.py tests/test_scene_observer.py tests/test_hologram_conversation_orchestrator.py tests/test_hologram_conversation_integration.py tests/test_app_services.py
25 passed in 0.12s

.venv/bin/python -m pytest
180 passed in 0.83s

.venv/bin/python -m ruff check app/hologram call.py app/services/conversation.py tests/test_media_router.py tests/test_scene_observer.py tests/test_hologram_conversation_orchestrator.py tests/test_hologram_conversation_integration.py
All checks passed!

.venv/bin/python -m ruff check .
Exit 1: 18 incidencias preexistentes, tres menos que las 21 iniciales porque call.py fue corregido al modificarlo. No hay incidencias nuevas de WAVE-003. Persisten en skills/honduras.py, stt/listener.py, tests/test_custom_object_interval.py, tests/test_hotwords_cache.py, utils.py y vision/person_detector.py.

graphify update .
Exit 0: 2254 nodes, 4162 edges; se mantienen avisos del extractor sobre cuatro archivos sin nodos y una arista sin confidence.

git diff --check
Exit 0
```

## Evidencia E2E simulada

`test_simulated_e2e_careers_turn_controls_all_three_roles` verifica:

```text
top: listening → thinking → speaking → idle
center: unev → holomind
bottom: careers context → rotation
```

Todo se ejecuta con `HologramSimulator`, sin hardware físico.

## Limitaciones

- No se configuró un proveedor pequeño real por defecto.
- El observer solo corrige identidad, no promociones; es deliberadamente conservador.
- No se implementaron frontend ni MediaRouter basado en LLM completo.

## Riesgos restantes

- Un proveedor bloqueado que ignore cancelación puede terminar después de un timeout; su resultado se descarta.
- La configuración administrativa actualiza el router existente, pero un proveedor operacional deberá inyectarse explícitamente.
- Falta validación física de la secuencia de clips y la correspondencia IP/rol.

## Trabajo pendiente

- WAVE-004 según roadmap, después de aprobar WAVE-003.

## Instrucción exacta para WAVE-004

Implementa exclusivamente el alcance documentado para WAVE-004; conserva `MediaRouter`, `HologramConversationOrchestrator`, context_id y las barreras semánticas de WAVE-003. No expongas hardware a la IA ni alteres el stream público sin actualizar contratos y pruebas.
