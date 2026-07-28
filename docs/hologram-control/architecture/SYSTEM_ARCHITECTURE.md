# Arquitectura del sistema

```text
Conversation Orchestrator
├── Mascot state
├── MediaRouter
├── SceneObserver
└── HologramDirector
    ├── Top UnitManager
    ├── Center UnitManager
    └── Bottom UnitManager
        └── PromotionRotationManager
```

## Capas

### Transporte

`HologramFanController` conoce sockets y bytes.

### Dominio

Conoce roles, identidades, promociones, rotación y ScenePlan.

### Orquestación

Conecta conversación con escena.

### IA

Propone significado; nunca hardware.

### API/UI

Administra catálogo y estado.

## Ciclo de vida

- Un director por proceso.
- Un manager por unidad.
- Un loop de rotación.
- Inicio en lifespan.
- Cierre idempotente.
- No crear workers por request.

## Principios

- Compatibilidad.
- Fail-soft.
- Inyección de dependencias.
- Reloj virtual.
- Side-channel de control.
