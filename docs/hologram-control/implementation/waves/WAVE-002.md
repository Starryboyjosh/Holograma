---
id: HC-WAVE-002
model: Luna 5.6
status: pending
---

# WAVE-002 — Rotación, API y simulador

**Modelo:** Luna 5.6


## Objetivo

Administrar el catálogo y probar tres unidades sin hardware.

## Alcance

- RotationManager.
- Reloj inyectable.
- Simulador.
- CRUD.
- Endpoints.
- Status.
- Identificación.

## Checklist

- [ ] Un loop de rotación.
- [ ] Sin sleeps reales.
- [ ] Pausa/reanuda.
- [ ] Contexto.
- [ ] Lista vacía.
- [ ] Omitir deshabilitados.
- [ ] API valida.
- [ ] Compatibilidad.

## Pruebas

- Tres elementos.
- Siguiente tras contexto.
- Lista vacía.
- Elemento inválido.
- API error/happy.
- Simulador con fan caído.

## Gate

Rotación pasa con tiempo virtual.
