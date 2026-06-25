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

## Verify Phases 1 + A (already done)
```bash
.venv/bin/pytest                                                  # 64 passing
.venv/bin/ruff check provider_config.py llm_backend.py main.py tests/   # clean
cd frontend && npx eslint . && npx tsc -p tsconfig.app.json --noEmit    # clean
cd frontend && npm test                                          # vitest (incl. AssistantScreen)
cd frontend && npm run build                                     # tsc -b + vite build OK
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

## Remaining phases (pick per priority)

### A. Settings UX + wire test buttons  ✅ DONE
The Settings AI-brain card is driven by the live contract:
- `components/ProviderConfigCard.tsx` renders ONE provider picker from
  `GET /api/providers` (7 providers, grouped cloud/local, friendly labels +
  descriptions, configured badge), a free-text model field (Ollama gets a
  datalist), a base-url field for `custom_openai`, a write-only API-key field
  (blank never wipes the stored key), and a **"Probar conexión"** button wired to
  `POST /api/llm/test`.
- `hooks/useProviders.ts` + rewritten `hooks/useConfig.ts` + pure
  `lib/providerForm.ts` (form→contract mapping, unit-tested). vitest+RTL added.
- **DEFERRED (follow-up): device pickers for mic/speaker/camera.** Browser
  `enumerateDevices()` IDs don't map to the backend OpenCV camera index /
  `sounddevice` index, and device consumption can't be validated in this env.
  Honest path: a numeric camera-index field bound to `HOLOGRAM_CAMERA_INDEX`
  (verify the backend reads it first) + backend audio-device selection, together.

### B. Cancellation + camera release + per-session events  (touches call.py, higher risk)
**Physical MISSYOU hologram — TCP state manager ✅ DONE:**
- `hologram_controller.py` has `HologramStateManager`: a thread-safe, fail-soft
  bridge that maps AI state → playlist clip index and sends `0x5B 0x06 N` (one
  command per packet, `min_send_gap`, dedupe, auto-reconnect w/ backoff). The IA
  runs identically with or without a device attached. `create_hologram_manager()`
  builds it from env; `call.py` already drives `set_state(idle/listening/speaking/
  thinking)`.
- The state→clip map is **configurable** (`resolve_state_clips` + `HOLOGRAM_CLIP_*`)
  so it matches whatever order the operator loaded clips in the HoloMissYou app —
  the one real fragility, since `N` is a playlist position, not a filename.
- `main.py`: the 4 `/api/hologram/*` endpoints share `call.hologram`; IP/port
  persist to config+`.env` and hot-reconfigure; manager started in the FastAPI
  lifespan. Frontend: `HologramConnection.tsx` + `useHologram.ts` (Settings card).
- Tests: `tests/test_hologram_controller.py` (state map, invalid settings, clip
  overrides). **Full guide + protocol + media rules: [`docs/HOLOGRAM.md`](HOLOGRAM.md).**
- Validate on hardware: splicing propagation to the 3 host units; no real lip-sync.

**Camera-off truly releases the device ✅ DONE:**
- `YoloPersonDetector` got a cooperative stop (`stop()` + `_stop_event`);
  `run_continuous` loops `while not self._stop_event.is_set()`, so the `Camera`
  context manager releases the device on exit (unit-tested with a fake Camera).
- `call.py`: `stop_camera_thread()` + double-start guard; `POST /api/camera
  {enabled}` wires it; the frontend camera toggle frees the camera (not just hides
  the `<img>`). Needs the running backend + a real camera for end-to-end proof.

**Still open (need the running backend — NOT done):**
- Pause/stop must cancel in-flight work: `pause_hologram` is a flag checked only
  between turns. Needs cooperative cancellation tokens through listen/LLM/TTS.
- TTS completion is faked: WS sends `completed` right after `speak(blocking=False)`
  returns. Signal real Piper playback end.
- Per-session WS: `send_to_web_client` broadcasts to all `active_connections`.
- Only encode MJPEG when a consumer is attached (`video_feed`).

### C. Windows-first sidecar packaging  (cannot finish here; needs Windows runner)
- **Documented with concrete steps + a starter PyInstaller `.spec` in
  [`docs/PACKAGING.md`](PACKAGING.md).** Tauri spawns `python3 main.py` (no
  `externalBin`); `kill_backend` does `child.kill()` only (orphans Piper/audio).
- Remaining (on a Windows+Linux runner): build the sidecar, wire `externalBin`,
  switch `spawn_backend` to it in release, kill the process **tree**, move
  config/cache to OS app-data, CI. **Pin Python ~3.11/3.12** for wheels.

### D. Security + operator auth
**D.1 — input hardening + secret hygiene ✅ DONE (fully testable here):**
- `security.py` (pure, tested): `redact_secrets` masks API-key-shaped tokens +
  known key envs; `clamp_text` strips control/zero-width/bidi chars + truncates.
- Wired in `main.py`: WS chat prompt clamped, `/api/speak` clamped, editable
  vision label/desc + vocabulary clamped, error responses redacted, atomic writes.
  CORS configurable via `CORS_ALLOW_ORIGINS` (default `*` preserved).

**D.2 — opt-in API-token gate ✅ PARTIAL:**
- `auth_token.py` (pure, tested): reads pass; privileged **writes** require
  `X-API-Token` (constant-time compare). `main.py` HTTP middleware gated on
  `HOLOGRAM_API_TOKEN` (empty = current behavior, no breakage).
- **Still open (needs the Tauri shell / running backend):** deliver the token from
  Rust → frontend on every privileged call; WS capability token; OS keyring for
  secrets instead of plaintext `.env`/`config.json`; rate limits; lock CORS to the
  validated WebView origin.

### E. De-monkey-patch into typed services  (refactor; INTENTIONALLY DEFERRED)
- Highest-risk item, **not safe blind**: rewriting startup monkey-patching +
  globals into services changes `call.py`/`main.py` hot paths that can't run in
  this env (no ML stack). `main.py` patches `call.speak`,
  `WhisperListener.listen_once`, `_camera_detection_callback` at startup. Migrate
  toward `application/` services + an event bus, strangler-style.

### F. Single editable UNEV content source  ✅ DONE
- `skills/unev_content.py` is the single authoritative source (canonical content +
  validated `load/save/get/reload`, atomic write, control-char clamp).
  `data/unev_info.json` regenerated complete; `university.py` reads everything from
  `get_unev_info()`. Editable via `GET/POST /api/unev-content` + a **Contenido**
  screen. `event_mode.py` is persona/behaviour (no facts — left alone).

### G. Legacy lint debt  ✅ DONE
- `ruff check .` is **clean** (was 36 issues). Behavior-preserving fixes only
  (import sort, unused imports, `Optional→| None`, relocated misplaced imports,
  `# noqa: B904` on a user-facing ConnectionError). Heavy modules compile + import.

## Reusable knobs already in the contract
Providers: openrouter, openai, claude_native, nvidia, custom_openai, ollama,
local_only. Model precedence: provider-specific env (`OPENAI_MODEL`…) > `LLM_MODEL`
> default (ollama never inherits `LLM_MODEL`). `LLM_BACKEND` is deprecated alias.
