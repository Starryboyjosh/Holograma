---
id: HC-WAVE-005
model: Terra 5.6
status: pending
---

# WAVE-005 — Endurecimiento y preparación física

**Modelo:** Terra 5.6


## Objetivo

Cerrar resiliencia, docs y E2E.

## Alcance

- E2E simulados.
- Restart.
- JSON corrupto.
- Cancelación.
- Seguridad.
- Observabilidad.
- Diagnóstico.
- Procedimiento físico.

## Escenarios

Inicio, UNEV+carreras, ITEE, sin match, center caído, bottom caído, router caído, JSON corrupto, restart y cancelación.

## Checklist

- [ ] Pytest.
- [ ] Ruff.
- [ ] Frontend checks.
- [ ] Sin fugas.
- [ ] Sin secretos.
- [ ] Simulador reproducible.
- [ ] Docs.
- [ ] Handoff para Sol.

## Gate

Congelar features al finalizar.
