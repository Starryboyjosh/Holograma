# WAVE-006 — Auditoría final

## Snapshot auditado

- Commit declarado: `5ebfee4 feat(hologram): harden zero-index diagnostics`
- Fuente: `Holograma-5ebfee4.zip`
- Backend verificado en el entorno de auditoría: `196 passed in 4.90s`
- Hardware físico: no probado
- Frontend: resultados verdes reportados por el implementador; no se reinstalaron completamente las dependencias en el entorno de auditoría.

## Veredicto

**BLOQUEADA — requiere correcciones antes de declarar el sistema listo para hardware.**

La arquitectura semántica y el contrato base cero son correctos, pero existen fallos funcionales en conexión, reconfiguración, compatibilidad heredada, seguridad y representación del estado de rotación en la interfaz.

## Hallazgos bloqueantes

### W6-B01 — `connect` no inicia una conexión física

**Archivos:**

- `app/hologram/unit_manager.py:38-45,128-145`
- `main.py:1014-1020`
- `scripts/diagnose_hologram.py:269-278`

`HologramUnitManager.start()` solo crea el worker. El worker llama a `_ensure_connected()` únicamente cuando existe una solicitud. Sin una solicitud pendiente, `request` es `None` y el loop continúa sin intentar conexión.

Consecuencias:

- `POST /api/hologram/units/{role}/connect` puede responder `ok` sin intentar conexión.
- `diagnose_hologram.py --connect` con el manager real normalmente expira, porque espera una conexión que `start()` nunca inicia.
- El botón Reconectar no cumple su propósito después de `disconnect`, salvo que otra acción encole un índice.

### W6-B02 — Guardar configuración detiene la rotación

**Archivo:** `app/hologram/director.py:80-87`

`reconfigure()` conserva únicamente `_started`. Cierra la rotación, crea un manager nuevo y luego llama a `start()`, pero no restaura si la rotación estaba activa o pausada.

Consecuencia: cualquier edición desde Settings puede detener silenciosamente el ventilador inferior.

### W6-B03 — Endpoint heredado crea dos directores independientes

**Archivos:**

- `app/hologram/compatibility.py:44-60`
- `main.py:130-135,927-947`

En modo web, `call.hologram` recibe un adaptador del director global. Sin embargo, `LegacyHologramAdapter.configure()` y `disable()` reemplazan únicamente `self._director` por una instancia nueva. `main._hologram_director`, `ConversationService` y el orquestador conservan la instancia anterior.

Consecuencia: después de usar `/api/hologram/connect` o `/disconnect`, la API administrativa y la conversación pueden controlar un director distinto al adaptador heredado.

### W6-B04 — La interfaz recibe objetos, pero los tipa y renderiza como texto

**Archivos:**

- `app/hologram/rotation.py:179-194,300-304`
- `frontend/src/lib/hologramApi.ts:45-50`
- `frontend/src/components/hologram/RotationControls.tsx:5-6`
- `frontend/src/components/hologram/__tests__/HologramControlPanel.test.tsx:14`

El backend devuelve `rotation.current` y `rotation.next` como objetos con `id`, `index`, `title` y `duration_seconds`. El frontend los tipa como `string | null` y los inserta directamente como hijos de React.

Consecuencia: cuando la rotación tenga un elemento actual real, React puede lanzar “Objects are not valid as a React child” y romper Settings. La prueba usa strings y no refleja el contrato real.

### W6-B05 — El token administrativo no protege el control del holograma

**Archivo:** `auth_token.py:23-30`

`PRIVILEGED_PREFIXES` no incluye `/api/hologram`. Por ello, incluso con `HOLOGRAM_API_TOKEN` configurado, cualquier proceso local puede modificar IPs, enviar índices, detener la rotación o editar catálogos sin token.

Esto contradice la exigencia de que los endpoints administrativos existentes queden protegidos cuando la autenticación está activa.

## Hallazgos importantes no bloqueantes por sí solos

### W6-M01 — El índice de identificación no se carga desde el backend

**Archivos:**

- `app/hologram/models.py:142-158`
- `frontend/src/components/hologram/FanUnitsPanel.tsx:16-29`

`FanUnitStatus` no expone `identify_index`. La UI inicia siempre el campo en `255`; guardar una unidad puede sobrescribir un índice de identificación personalizado sin que el operador lo note.

### W6-M02 — Falta administración de los estados de mascota

No existe endpoint ni componente para editar `idle`, `listening`, `thinking` y `speaking`. El handoff de WAVE-004 afirma “configuración de mascota”, pero la interfaz solo muestra el estado actual de top.

### W6-M03 — Probar una identidad inexistente reporta éxito

**Archivos:**

- `app/hologram/director.py:44-48`
- `main.py:1113-1119`

`set_identity()` convierte un ID desconocido en Holomind. El endpoint de prueba devuelve `status: ok` con el ID solicitado, aunque realmente se haya enviado Holomind.

### W6-M04 — Restauración de `idle` fuera del control de contexto

**Archivo:** `main.py:307-311`

`_host_tts_done()` pone top en `idle` directamente, sin `context_id`. En turnos solapados, el TTS de un turno viejo puede alterar el estado de la mascota del turno nuevo aunque `finish_turn()` rechace correctamente el cierre stale.

### W6-M05 — Los modos de routing declarados no están completamente implementados

**Archivos:**

- `app/hologram/models.py:98-115`
- `app/hologram/media_router.py:176-181`

El modelo acepta `small_model`, pero `_should_use_provider()` solo llama al proveedor en modo `hybrid`. El modo `small_model` se comporta como local.

## Aspectos aprobados

- Separación entre transporte, dominio, orquestación e IA.
- Tres managers independientes y una cola por unidad.
- Contrato de índice base cero `0..255`; `0` se conserva correctamente.
- IA y ScenePlan sin IP, puerto ni índices.
- Estado write-only correctamente expresado en modelos y UI.
- Fallback seguro del router.
- Protección contra cierre tardío de contextos.
- Cleanup de `ConversationService` mediante `finally`.
- Persistencia atómica y validada del catálogo.
- Simulador y reloj virtual.
- Compatibilidad de variables heredadas del top.
- Documentación honesta respecto a la falta de validación física.

## Cobertura

El backend completo pasó en el entorno de auditoría:

```text
196 passed in 4.90s
```

Las pruebas actuales no detectan los bloqueantes porque:

- el test de conexión solo comprueba que se invoca el endpoint;
- el diagnóstico usa un manager falso cuyo `start()` conecta inmediatamente;
- el test frontend simula `rotation.current` y `next` como strings;
- no existe prueba del director compartido después de usar endpoints heredados;
- no existe prueba de rotación activa durante una reconfiguración;
- no existe prueba de autorización para `/api/hologram`.

## Decisión final

No declarar WAVE-006 aprobada ni comenzar calibración física hasta corregir W6-B01 a W6-B05 y añadir pruebas de regresión.

## Correcciones preparadas posteriores a la auditoría

Las correcciones se encuentran sin commit para revisión sobre `5ebfee4`:

- W6-B01: `HologramUnitManager.connect()` inicia el worker idempotente y hace
  un intento de socket; el endpoint y el diagnóstico usan esa operación.
- W6-B02: `HologramDirector.reconfigure()` toma/restaura el estado de rotación
  activo, pausado y la siguiente posición válida.
- W6-B03: el adaptador heredado reconfigura el mismo director en vez de
  reemplazar su instancia.
- W6-B04: `rotation.current` y `rotation.next` se tipan/renderizan como medios
  estructurados en el panel.
- W6-B05: cuando hay `HOLOGRAM_API_TOKEN`, todo `/api/hologram/*`, incluidas
  lecturas, requiere `X-API-Token`.

La evidencia de regresión y los límites restantes están en
`handoffs/WAVE-006-FIX-HANDOFF.md`. Hardware físico: **NO PROBADA**.

## Correcciones residuales posteriores

- El frontend usa `VITE_HOLOGRAM_API_TOKEN` únicamente como header
  `X-API-Token` para `/api/hologram/*`; conserva headers existentes y nunca lo
  añade a URLs, logs o solicitudes no holográficas.
- `/api/hologram/connect` reconfigura el director compartido y luego intenta
  explícitamente conectar `top`; un fallo devuelve error en lugar de éxito.
- La restauración de una rotación pausada reconstituye su estado sin despachar
  el siguiente medio.
- `HologramConversationOrchestrator.start_turn()` sincroniza el router con la
  configuración actual del director una vez por turno cuando la instancia de
  catálogo cambió; esto cubre el orquestador cacheado de `call.py` y la ruta
  `ConversationService` compartida.
- Una reconexión correcta borra `last_error` y `retry_count`, informa
  `last_send_result="connected"` y no altera índices de reproducción.
- Una reconfiguración pausada reenvía exactamente una vez el medio `current` al
  manager nuevo para recuperar la imagen tras `shutdown`, sin enviar `next`,
  iniciar deadline ni avanzar la cola.

## Preparación operativa de demostración

La guía `docs/HOLOGRAM_SCHOOL_DEMO.md` documenta una instalación mínima de tres
ventiladores, carga manual con HoloMissYou, modo local sin token, modo de red
opcional, catálogo provisional y calibración observada. Hardware físico:
**NO PROBADO**; correspondencia de índices: **PENDIENTE**.
