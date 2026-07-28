# Estrategia de pruebas

## Unitarias

- Validación.
- Resolución.
- Reglas.
- Ranking.
- Rotación.
- Fallback.
- Compatibilidad.

## Integración

- Director + managers.
- Store + API.
- Router + director.
- ConversationService.
- Lifespan.

## E2E simulada

```text
prompt → ScenePlan → comandos → TTS → restore
```

## Fakes

- FakeFan.
- FakeClock.
- FakeScheduler.
- FakeRouter.
- FakeTTS.

## Comandos

```bash
python -m pytest
python -m ruff check .
cd frontend
npm run lint
npm run test
npm run build
```
