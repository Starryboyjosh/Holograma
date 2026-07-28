# WAVE-004 — Handoff

## Estado

COMPLETA

## Commit base

`41b846c feat(hologram): add semantic media routing` (incluye WAVE-001, WAVE-002 y WAVE-003). Esta ejecución no creó un commit nuevo.

## Requisitos cubiertos

- Panel administrativo conectado a los endpoints reales de WAVE-002.
- Configuración de tres unidades, mascota, identidades, promociones, rotación y estado en vivo.
- Validación de formularios, estados parciales/error/vacío, accesibilidad básica y polling cancelable.
- Compatibilidad con la pantalla de conversación y con el cliente HTTP/Tauri existente.

## Implementado

- Cliente tipado `hologramApi` con manejo uniforme de errores del backend.
- Hook `useHologramControl` con una carga inicial, polling cada cuatro segundos, guard contra solicitudes simultáneas y refresh posterior a mutaciones.
- Panel compuesto por tarjetas de unidades, catálogo de identidades, catálogo de promociones, controles de rotación y estado en vivo.
- Formularios CRUD con validación de índices, puertos, duración, campos requeridos, confirmación de borrado y botones deshabilitados durante operaciones.

## Archivos creados

- `frontend/src/lib/hologramApi.ts`
- `frontend/src/hooks/useHologramControl.ts`
- `frontend/src/components/hologram/HologramControlPanel.tsx`
- `frontend/src/components/hologram/FanUnitsPanel.tsx`
- `frontend/src/components/hologram/IdentityCatalog.tsx`
- `frontend/src/components/hologram/PromotionCatalog.tsx`
- `frontend/src/components/hologram/RotationControls.tsx`
- `frontend/src/components/hologram/LiveHologramStatus.tsx`
- `frontend/src/components/hologram/__tests__/HologramControlPanel.test.tsx`
- `frontend/src/hooks/__tests__/useHologramControl.test.ts`

## Archivos modificados

- `frontend/src/screens/SettingsScreen.tsx`
- `main.py` (corrección mínima del endpoint de prueba para aceptar un índice opcional)
- `tests/test_hologram_api.py` (regresión del índice de prueba)
- `docs/hologram-control/implementation/STATUS.md`
- `graphify-out/*` (salida generada por `graphify update .`; no forzar al commit)

## Decisiones tomadas

- Se reutiliza `apiFetch`, `Card`, `Field` y `ToastContext`; no se añade librería de estado ni de UI.
- El panel administrativo sustituye la tarjeta de conexión heredada en Settings para evitar dos superficies que controlen la misma unidad.
- La prueba de identificación usa el endpoint semántico de unidad y comunica el rol configurado/IP sin afirmar la posición física.
- Se mantuvieron los endpoints existentes; se amplió mínimamente `/test` para aceptar un índice opcional, manteniendo el comportamiento sin cuerpo.

## Tipos y cliente API

`hologramApi.ts` tipa roles, unidades, identidades, promociones, rotación, estado global y errores; codifica IDs en rutas y no realiza optimistic updates.

## Panel de unidades

Muestra Superior/Mascota, Central/Identidades e Inferior/Promociones, IP, puerto, conexión, contenido actual, errores, worker, habilitación, identificación, conexión y prueba.

## Estados de mascota

El estado actual y el índice se muestran en la tarjeta Superior. La UI conserva la automatización conversacional y no presenta estados como operación manual de IA.

## Identidades

CRUD real, keywords normalizadas, índice, default, habilitación, probar y confirmación de borrado; Holomind/default queda protegido por el backend y por el botón.

## Promociones

CRUD real, categorías, topics, duración, prioridad, habilitación, inclusión en rotación, prueba individual/categoría y estado vacío comprensible.

## Rotación

Controles start/pause/resume/stop con estados actual, siguiente, contexto y error; se distingue de las pruebas manuales.

## Estado en vivo

Polling de `/api/hologram/status` cada 4 segundos, cancelado al desmontar y protegido contra solapamiento; el error deja visible la configuración previa.

## Accesibilidad

Labels asociados, nombres de botones, `aria-live` para mensajes/actualizaciones, foco nativo de teclado, errores junto a controles y confirmación de borrado.

## Compatibilidad preservada

No se modificaron MediaRouter, SceneObserver, conversación, TCP, WebSocket, Tauri ni README. Solo se amplió el endpoint de prueba con un índice opcional; la pantalla de conversación y la configuración general permanecen en Settings/AppShell.

## Pruebas añadidas

- `HologramControlPanel.test.tsx`: tres roles, estado vivo, vacío y endpoint de conexión.
- `useHologramControl.test.ts`: carga inicial y desmontaje del polling.

## Comandos ejecutados y resultados exactos

```text
cd frontend && npm run lint
Exit 1: 1 error y 1 warning preexistentes en ProviderConfigCard.tsx (setState en effect y directiva no usada).

cd frontend && npm run test
17 passed in 0.81s

cd frontend && npm run build
Exit 2: tres errores TypeScript preexistentes en ProviderConfigCard.tsx (comparaciones de estado 'ok'/'loading').

cd frontend && npx eslint src/lib/hologramApi.ts src/hooks/useHologramControl.ts src/hooks/__tests__/useHologramControl.test.ts src/components/hologram src/screens/SettingsScreen.tsx
All checks passed!

cd frontend && npx tsc --noEmit --pretty false
Exit 0

.venv/bin/python -m pytest
181 passed in 0.80s

.venv/bin/python -m ruff check main.py tests/test_hologram_api.py
All checks passed!

graphify update .
Exit 0: 2329 nodes, 4326 edges, 169 communities; avisos existentes de cuatro archivos sin nodos y una arista sin confidence.

git diff --check
Exit 0
```

## Evidencia visual o funcional

Los tests renderizan las tres tarjetas con una unidad desconectada, estado actual y catálogo de promociones vacío. La prueba de interacción verifica la llamada real a `POST /api/hologram/units/center/connect`.

## Limitaciones

- El endpoint de prueba de unidad se amplió mínimamente para aceptar un índice opcional; el comportamiento sin cuerpo sigue siendo compatible.
- `npm run lint` y `npm run build` siguen bloqueados por deuda preexistente en `ProviderConfigCard.tsx`, fuera del alcance de esta wave.
- No se validó hardware físico.

## Riesgos restantes

- Debe corregirse la deuda de ProviderConfigCard antes de exigir un build frontend verde en CI.
- La correspondencia física rol/IP sigue requiriendo identificación operativa.

## Trabajo pendiente

- Corregir los errores preexistentes de ProviderConfigCard en una tarea de mantenimiento separada.
- Definir el alcance aprobado de WAVE-005.

## Instrucción exacta para WAVE-005

Implementa únicamente el alcance aprobado de WAVE-005 sobre la base de WAVE-004; conserva los contratos API, el cliente `hologramApi`, el polling cancelable, MediaRouter, SceneObserver y la integración conversacional, sin cambiar TCP ni introducir una nueva librería de estado.
