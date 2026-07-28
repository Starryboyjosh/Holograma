# Inicio rápido

## Para comenzar WAVE-001

Lee en este orden:

1. `governance/AGENT_RULES.md`
2. `product/CURRENT_STATE.md`
3. `product/REQUIREMENTS.md`
4. `architecture/SYSTEM_ARCHITECTURE.md`
5. `contracts/DOMAIN_MODELS.md`
6. `contracts/CONFIG_SCHEMA.md`
7. `implementation/waves/WAVE-001.md`
8. `implementation/STATUS.md`

Después copia el prompt de:

```text
implementation/IMPLEMENTATION_PROMPT.md
```

y úsalo con **Terra 5.6**.

## Regla principal

No entregues el roadmap completo al agente como una única tarea de construcción.

Cada agente recibe:

- reglas;
- contratos;
- wave activa;
- último handoff;
- estado.

## Al terminar una wave

1. Ejecutar checks.
2. Revisar diff.
3. Crear `handoffs/WAVE-00X-HANDOFF.md`.
4. Actualizar `implementation/STATUS.md`.
5. Hacer un commit lógico.
6. Cambiar al modelo de la siguiente wave.

## No comenzar con Sol

Sol 5.6 es revisor final. No debe construir WAVE-001 a WAVE-005.
