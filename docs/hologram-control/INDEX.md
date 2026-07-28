---
id: HC-INDEX
status: accepted
owner: architecture
---

# Control inteligente de Holograma

## Resultado objetivo

```text
Superior → Mascota y estados reales
Centro   → Holomind / UNEV / ITEE según contexto
Inferior → Promociones continuas y contenido contextual
```

La IA decide **significados**, no índices físicos.

## Navegación

### Empezar

- [Inicio rápido](QUICK_START.md)
- [Reglas para agentes](governance/AGENT_RULES.md)
- [Estado actual](implementation/STATUS.md)
- [Roadmap](implementation/ROADMAP.md)

### Producto

- [Visión y alcance](product/VISION_AND_SCOPE.md)
- [Estado real del repositorio](product/CURRENT_STATE.md)
- [Requisitos](product/REQUIREMENTS.md)
- [Backlog](product/BACKLOG.md)

### Arquitectura

- [Arquitectura del sistema](architecture/SYSTEM_ARCHITECTURE.md)
- [ADRs](architecture/adrs/README.md)

### Contratos

- [Modelos de dominio](contracts/DOMAIN_MODELS.md)
- [Esquema de configuración](contracts/CONFIG_SCHEMA.md)
- [ScenePlan](contracts/SCENE_PLAN.md)
- [API](contracts/API.md)
- [Frontend](contracts/FRONTEND.md)

### Implementación

- [Roadmap y gates](implementation/ROADMAP.md)
- [Asignación de modelos](implementation/MODEL_ASSIGNMENT.md)
- [Prompt maestro](implementation/IMPLEMENTATION_PROMPT.md)
- [Plantilla de tarea](implementation/TASK_TEMPLATE.md)
- [Estado](implementation/STATUS.md)
- [Waves](implementation/waves/README.md)

### Calidad

- [Estrategia de pruebas](quality/TEST_STRATEGY.md)
- [Matriz de aceptación](quality/ACCEPTANCE_MATRIX.md)
- [Checklist de revisión](quality/REVIEW_CHECKLIST.md)

### Operación

- [Simulador](operations/SIMULATOR.md)
- [Validación física](operations/HARDWARE_VALIDATION.md)
- [Migración y compatibilidad](operations/MIGRATION_COMPATIBILITY.md)
- [Troubleshooting](operations/TROUBLESHOOTING.md)

### Gobierno

- [Fuentes de verdad](governance/SOURCE_OF_TRUTH.md)
- [Decisiones](governance/DECISIONS.md)
- [Riesgos](governance/RISKS.md)
- [Changelog](governance/CHANGELOG.md)
- [Handoffs](handoffs/README.md)

## Jerarquía de fuentes de verdad

1. Contratos.
2. ADRs aceptados.
3. Requisitos.
4. Arquitectura.
5. Wave activa.
6. Estado y handoffs.
7. Código existente.
8. Comentarios históricos.

## Definición de terminado

```text
Usuario habla
→ top escucha
→ top piensa
→ router crea ScenePlan
→ center muestra identidad
→ bottom muestra promoción contextual
→ top habla
→ top vuelve a idle
→ center vuelve a Holomind
→ bottom reanuda rotación
```

Todo debe seguir funcionando si una o varias unidades están desconectadas.
