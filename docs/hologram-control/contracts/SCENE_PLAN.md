# Contrato ScenePlan

```json
{
  "center_identity": "unev",
  "promotion_action": "focus_category",
  "promotion_id": null,
  "promotion_category": "careers",
  "confidence": 0.93,
  "source": "local_rules",
  "reason_code": "DIRECT_MATCH",
  "context_id": "turn-uuid"
}
```

## Prohibido

- `index`
- `ip`
- `port`
- comandos TCP
- texto para TTS

## Fallback

```json
{
  "center_identity": "holomind",
  "promotion_action": "continue_rotation",
  "promotion_id": null,
  "promotion_category": null,
  "confidence": 0,
  "source": "fallback",
  "reason_code": "NO_RELIABLE_MATCH"
}
```
