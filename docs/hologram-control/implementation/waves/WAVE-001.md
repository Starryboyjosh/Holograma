---
id: HC-WAVE-001
model: Terra 5.6
status: pending
---

# WAVE-001 — Dominio, configuración y director

**Modelo:** Terra 5.6


## Objetivo

Crear la base de tres unidades sin IA ni UI nueva.

## Alcance

- Modelos.
- Config store.
- UnitManager.
- Director.
- Compatibilidad.
- Start/close.
- Estado.

## Archivos esperados

```text
app/hologram/models.py
app/hologram/config_store.py
app/hologram/unit_manager.py
app/hologram/director.py
app/hologram/compatibility.py
```

## Checklist

- [ ] Tres managers.
- [ ] Cola separada.
- [ ] Falla aislada.
- [ ] Resolución semántica interna.
- [ ] JSON seguro.
- [ ] Compatibilidad.
- [ ] Shutdown limpio.
- [ ] Tests heredados verdes.

## Pruebas

- Config válida/inválida.
- Escritura atómica.
- Tres IP.
- Una unidad caída.
- Reconexión.
- Dedupe.
- Cierre.

## Fuera de alcance

Routing, rotación, API completa y UI.

## Gate

No avanzar si quedan threads vivos.
