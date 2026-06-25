# Holograma UNEV — Handoff for the next agent

UNEV-only product. **Do not** build multi-tenancy/white-label. Read `CLAUDE.md`
(graphify rules: run `graphify query "..."` before grepping; `graphify update .`
after code changes). This doc is the onboarding shortcut so you don't re-derive
the audit.

## Hard environment constraints (read first)
- `.venv` is **Python 3.14, zero runtime deps installed**. The ML/STT/TTS/vision
  backend (torch, ultralytics, faster-whisper, sounddevice, piper, fastapi) is
  NOT installed and likely lacks 3.14 wheels. **You cannot launch or profile the
  backend here.** Prefer pure functions + mocked adapters + `pytest`.
- Installed dev tools: `pytest`, `ruff`, `python-dotenv`. Node 22 / npm 11 / cargo
  1.96 present.
- Workflow: **commit whole working tree directly to `main` and push** (no PRs).

## Verify Phase 1 (already done)
```bash
.venv/bin/pytest                                                  # 29 passing
.venv/bin/ruff check provider_config.py llm_backend.py main.py tests/   # clean
cd frontend && npx eslint . && npx tsc -p tsconfig.app.json --noEmit    # clean
```

## Phase 1 result (DONE) — the config/provider contract
- **`provider_config.py`** is now the single source of truth: registry +
  `select_backend` (explicit provider is authoritative; the old Ollama-vs-stale-
  cloud-key bug is fixed) + `resolve_model/key/base_url`. Pure, env-injectable.
- `llm_backend.py` delegates to it; one OpenAI-compatible client for
  openrouter/openai/nvidia/custom_openai; `probe_backend()` gives actionable
  errors. `LLM_MODEL` now actually applies to OpenAI/NVIDIA.
- `main.py`: `GET /api/providers` (configured-state, no secrets) +
  `POST /api/llm/test` (non-persisting test-connection) + atomic config/.env
  writes + redacted config responses.
- Contract reference: **`docs/CONFIG.md`**. Env reference: `.env.example`.
- Removed obsolete `tests/holograma_test.go` (drove the dead vanilla-HTML UI).

## Remaining phases (pick per priority)

### A. Settings UX + wire test buttons  ← recommended next, fully doable here
Build `frontend/src/screens/SettingsScreen.tsx` (+ `hooks/useConfig.ts`) on the
NEW endpoints. Currently it hardcodes providers/models, blanks the key on every
change, never shows configured state (ignores `*_API_KEY_SET`), no test button,
no mic/speaker/camera selection.
- Use `GET /api/providers` to render the picker (friendly labels/descriptions,
  `key_configured`, `needs_base_url`, `supports_discovery`) and `POST /api/llm/test`
  for a "Probar conexión" button with the returned message.
- Add custom OpenAI endpoint (base_url field), model discovery where supported,
  and a free-text model field fallback.
- Add device pickers (`navigator.mediaDevices.enumerateDevices`) for mic/speaker/
  camera; persist selection.
- Validatable here: eslint/tsc + component tests (add vitest/RTL).
- Acceptance: non-technical operator configures/replaces provider+key+model from
  UI; invalid key/model explained; secrets never shown.

### B. Cancellation + camera release + per-session events  (touches call.py, higher risk)
- "Camera off" must release the device: there is NO stop path —
  `call.py:971 start_camera_thread` runs `run_continuous` forever;
  `vision/person_detector.py` needs a stop flag + capture release; only encode
  MJPEG when a consumer is attached (`main.py:654 video_feed`).
- Pause/stop must cancel in-flight work: `call.py:83 pause_hologram` is a Linux-
  only `killall` flag; `voice_loop` (`call.py:1140`) checks `_hologram_paused`
  only between turns. Add cooperative cancellation tokens to listen/LLM/TTS.
- TTS completion is faked: `main.py` WS sends `completed` right after
  `speak(blocking=False)` returns (`call.py:659`). Signal real playback end.
- Per-session WS: `send_to_web_client` broadcasts to all (`main.py` global
  `active_connections`); add request/session ids.
- Hard to validate without ML stack → lean on unit tests with mocked detector/
  listener/TTS.

### C. Windows-first sidecar packaging  (cannot finish here; needs Windows runner)
- Tauri still spawns `python3 main.py` from source (`frontend/src-tauri/src/lib.rs:57`);
  no `externalBin`. Build a PyInstaller sidecar, wire `tauri.conf.json` bundle,
  resource lookup post-install, OS app-data/config/cache dirs, model assets with
  checksums, clean child-process shutdown (current `kill_backend` orphans Piper/
  audio), Windows+Linux CI. **Pin Python ~3.11/3.12** for wheel availability.

### D. Security + operator auth  (mostly doable here)
- Auth for privileged settings; split visitor vs privileged APIs; per-process
  Tauri capability token for WS/REST; OS keyring for secrets (Windows Credential
  Manager / Linux Secret Service) instead of plaintext `.env`/`config.json`; log
  redaction; input size/schema validation; rate limits; prompt-injection guard on
  editable vision labels / UNEV content; tighten CORS (`main.py:154` allow_origins=*).

### E. De-monkey-patch into typed services  (refactor; do incrementally)
- `main.py:38-78` patches `call.speak`, `WhisperListener.listen_once`,
  `_camera_detection_callback` at startup; globals everywhere. Migrate toward
  `application/` services (conversation/config/device) + an event bus, using the
  strangler pattern (add seam, route through it, keep working). `call.py` (1265 L)
  and `main.py` (900 L) are the god-modules to split.

### F. Single editable UNEV content source
- Facts duplicated across `skills/university.py` (316 L), `data/unev_info.json`,
  `skills/honduras.py`, prompts in `skills/event_mode.py`, and
  `frontend/.../TeachingScreen.tsx`. Make one validated source (JSON + schema)
  editable via UI; everything else reads from it.

### G. Legacy lint debt
- `ruff check .` reports ~38 issues in untouched modules (call.py, vision/, stt/,
  scripts/). Sweep with `ruff check --fix` + review once those modules can be run.

## Reusable knobs already in the contract
Providers: openrouter, openai, claude_native, nvidia, custom_openai, ollama,
local_only. Model precedence: provider-specific env (`OPENAI_MODEL`…) > `LLM_MODEL`
> default (ollama never inherits `LLM_MODEL`). `LLM_BACKEND` is deprecated alias.

