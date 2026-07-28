---
id: HC-WAVE-003
model: Terra 5.6
status: pending
---

# WAVE-003 — MediaRouter e integración conversacional

**Modelo:** Terra 5.6


## Objetivo

Control semántico sin exponer hardware.

## Alcance

- Reglas.
- Ranking.
- Submodelo opcional.
- Timeout.
- SceneObserver.
- Sync y async.
- Cleanup.

## Checklist

- [ ] Match claro evita submodelo.
- [ ] Máximo 5 candidatos.
- [ ] Salida validada.
- [ ] Cero índices.
- [ ] Cero metadata en TTS/UI.
- [ ] Misma lógica sync/async.
- [ ] Fallback.
- [ ] Restore en finally.

## Casos

Holomind, UNEV, ITEE, carreras, específico, ambiguo, timeout, JSON inválido y cancelación.

## Gate

E2E fake verifica las tres unidades.
