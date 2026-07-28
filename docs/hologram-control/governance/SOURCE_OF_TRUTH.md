# Fuentes de verdad

## Orden

1. `contracts/`
2. `architecture/adrs/`
3. `product/REQUIREMENTS.md`
4. `architecture/SYSTEM_ARCHITECTURE.md`
5. `implementation/waves/WAVE-00X.md`
6. `implementation/STATUS.md`
7. `handoffs/`
8. `docs/HOLOGRAM.md`
9. Código existente
10. Comentarios antiguos

## Conflictos

Si una wave contradice un contrato, gana el contrato.

Si el código contradice un ADR aceptado, el agente debe:

- confirmar que el ADR sigue vigente;
- migrar de forma compatible;
- documentar el cambio.

## Cambios de contrato

Solo pueden hacerse con:

1. ADR nuevo o ADR reemplazado.
2. Actualización de requisitos.
3. Actualización de tests contractuales.
4. Entrada en `CHANGELOG.md`.
5. Nota en handoff.
