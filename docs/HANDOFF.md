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
.venv/bin/pytest                                                  # 32 passing
.venv/bin/ruff check provider_config.py llm_backend.py main.py tests/   # clean
cd frontend && npx eslint . && npx tsc -p tsconfig.app.json --noEmit    # clean
cd frontend && npm test                                          # 12 passing (vitest)
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
- Removed obsolete `tests/holograma_test.go` (drove the dead vanilla-HTML UI).

## Remaining phases (pick per priority)

### A. Settings UX + wire test buttons  ✅ DONE (this commit)  ← B or D recommended next
The Settings AI-brain card is now driven by the live contract:
- `components/ProviderConfigCard.tsx` renders ONE provider picker from
  `GET /api/providers` (7 providers, grouped cloud/local, friendly labels +
  descriptions, configured badge), a free-text model field (Ollama gets a
  datalist), a base-url field for `custom_openai`, a write-only API-key field
  (blank never wipes the stored key), and a **"Probar conexión"** button wired to
  `POST /api/llm/test` that shows the actionable message.
- `hooks/useProviders.ts` (catalogue + probe), rewritten `hooks/useConfig.ts`
  (unified `llmProvider`/`model`/`apiKey`/`baseUrl`), pure `lib/providerForm.ts`
  (form→contract mapping, unit-tested).
- Backend: `ConfigUpdate`/`update_config` now persist `OPENAI_COMPAT_API_KEY` +
  `OPENAI_COMPAT_BASE_URL`; `GET /api/config` round-trips the (non-secret) base URL.
- Tests: vitest+RTL added (`npm test`, 12 tests) + 3 new provider_config tests.
- **DEFERRED (do in a follow-up): device pickers for mic/speaker/camera.** Reason:
  browser `enumerateDevices()` IDs don't map to the backend's OpenCV camera index
  / `sounddevice` index, and the backend's device consumption can't be validated
  in this env — a picker writing IDs the backend ignores would be a fake control.
  Honest path: a numeric camera-index field bound to `HOLOGRAM_CAMERA_INDEX`
  (verify the backend reads it first) + backend audio-device selection, together.

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

### D. Security + operator auth
**D.1 — input hardening + secret hygiene ✅ DONE (this commit, fully testable here):**
- `security.py` (pure, 10 tests): `redact_secrets(text, env)` masks API-key-shaped
  tokens + exact values of known key envs; `clamp_text(text, max_len)` strips
  control/zero-width/bidi chars and truncates; size constants.
- Wired in `main.py`: WS chat `prompt` clamped (`MAX_PROMPT_CHARS`), `/api/speak`
  text clamped, editable vision `label`/`desc` + vocabulary clamped (prompt-injection
  surface), error responses (`update_config`, `speak`, train) redacted, atomic writes
  for training files. `llm_backend._humanize_probe_error` redacts the raw provider
  error. CORS is now configurable via `CORS_ALLOW_ORIGINS` (default `*` preserved).

**D.2 — auth + secret storage (NOT done; needs the Tauri shell + a running backend):**
- Per-process **Tauri capability token** for WS/REST (Rust passes it to backend env +
  frontend; frontend sends it). HIGH breakage risk — must be validated in the desktop
  app, can't be here. Split visitor vs privileged (settings/train) APIs behind it.
- OS keyring for secrets (Windows Credential Manager / Linux Secret Service) instead
  of plaintext `.env`/`config.json`.
- Rate limits / concurrency caps on WS + LLM calls.
- Lock down CORS to the validated WebView origin (set `CORS_ALLOW_ORIGINS`).

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
