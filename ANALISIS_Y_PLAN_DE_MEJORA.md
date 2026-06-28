# Holograma UNEV — Trabajo pendiente

> Actualizado 2026-06-28. Las Fases 0–4 del plan de mejora están **completas y en
> `main`** (event loop desbloqueado, ruta de LLM unificada, capa de servicios sin
> monkey-patches, rendimiento de visión). Estado verificado con `pytest`
> (**112 pruebas**) + `ruff` limpio. Este documento conserva **solo lo que falta**.

---

## Reorganización de carpetas (diferido)

La estructura actual mezcla orquestadores, subsistemas y scripts en la raíz. La
propuesta agrupa la capa web/orquestación bajo `app/` y los subsistemas "motor"
bajo `core/`.

```
Holograma/
├── app/                      # capa web + orquestación
│   ├── main.py               #   FastAPI: rutas async finas + lifespan limpio
│   ├── connection.py         #   ConnectionManager async (único emisor de eventos)
│   └── services/
│       ├── conversation.py   #   orquesta LLM→TTS→eventos
│       ├── llm.py            #   1 ruta async (envuelve provider_config)
│       ├── tts.py           #   TTS no bloqueante
│       ├── stt.py           #   envuelve stt/listener
│       ├── vision.py        #   envuelve vision/person_detector
│       └── hologram.py      #   envuelve hologram_controller
├── core/                     # subsistemas "motor" (ya buenos, casi sin tocar)
│   ├── provider_config.py
│   ├── hologram_controller.py
│   ├── vision/   stt/   skills/
│   └── security.py  utils.py
├── data/                     # JSON de contenido (UNEV/Honduras) + samples
├── frontend/                 # React/Tauri (sin cambios estructurales)
├── scripts/                  # diagnose/setup/run
├── tests/
├── docs/
├── models/  piper/           # binarios locales (gitignored)
├── .env.example  pyproject.toml  README.md
└── ANALISIS_Y_PLAN_DE_MEJORA.md   ← este documento
```

### Por qué está diferido

Se aplazó **a su propia sesión** por decisión (2026-06-27) porque es un cambio
invasivo:

- Rompe imports en todo el repo (hay que mover archivos y corregir imports a la
  vez para no dejar un estado intermedio roto).
- Cambia el punto de entrada del sidecar de Tauri (`main.py` → `app/main.py`).

### Cómo hacerlo cuando se retome

- Un commit por movimiento, corriendo `pytest` entre cada uno.
- Empezar por mover los subsistemas "motor" a `core/` (bajo riesgo, solo cambian
  rutas de import), luego la capa `app/`.
- Verificar que el `build`/empaquetado de Tauri apunte al nuevo entry point.
