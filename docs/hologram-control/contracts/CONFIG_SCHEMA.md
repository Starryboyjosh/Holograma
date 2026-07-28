# Esquema de configuración

Ruta:

```text
data/hologram_media.json
```

```json
{
  "version": 1,
  "units": {
    "top": {"enabled": true, "ip": "", "port": 50200},
    "center": {"enabled": true, "ip": "", "port": 50200},
    "bottom": {"enabled": true, "ip": "", "port": 50200}
  },
  "mascot_states": {
    "idle": 0,
    "listening": 1,
    "thinking": 3,
    "speaking": 2
  },
  "identities": [
    {
      "id": "holomind",
      "title": "Holomind",
      "index": 0,
      "enabled": true,
      "default": true,
      "keywords": ["holomind"]
    }
  ],
  "promotions": [],
  "rotation": {
    "enabled": true,
    "resume_mode": "next",
    "minimum_context_seconds": 10,
    "maximum_context_seconds": 45
  },
  "routing": {
    "mode": "hybrid",
    "minimum_confidence": 0.75,
    "small_model_enabled": true,
    "small_model_timeout_seconds": 1.5,
    "identity_hold_seconds": 4,
    "max_identity_changes_per_turn": 1
  }
}
```

## Persistencia

- Validar antes de guardar.
- Archivo temporal.
- Reemplazo atómico.
- Backup `.bak`.
- Lock de escritura.
- Fallback seguro si está corrupto.
