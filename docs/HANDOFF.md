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
.venv/bin/pytest                                                  # 58 passing
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
**Camera-off truly releases the device ✅ DONE (this commit):**
- `YoloPersonDetector` got a cooperative stop: `stop()` + `_stop_event`;
  `run_continuous` loops `while not self._stop_event.is_set()`, so the `Camera`
  context manager releases the device on exit. Unit-tested with a fake Camera
  (`tests/test_camera_stop.py`) — verifies the loop ends AND the device is released.
- `call.py`: `stop_camera_thread()` (signals stop + joins) and a double-start guard
  in `start_camera_thread()`. New `POST /api/camera {enabled}` wires it; the frontend
  camera toggle (`SessionContext`) now calls it, so "off" frees the camera (not just
  hides the `<img>`). Backend path is additive + compiles, but needs the running
  backend + a real camera to validate end-to-end.

**Still open (need the running backend — NOT done):**
- Pause/stop must cancel in-flight work: `pause_hologram` is a Linux-only `killall`
  flag; `voice_loop` checks `_hologram_paused` only between turns. Needs cooperative
  cancellation tokens threaded through listen/LLM/TTS (rewriting `voice_loop`/`speak`
  blind is too risky without being able to run it).
- TTS completion is faked: WS sends `completed` right after `speak(blocking=False)`
  returns. Signal real playback end (Piper subprocess completion callback).
- Per-session WS: `send_to_web_client` broadcasts to all `active_connections`; add
  request/session ids.
- Only encode MJPEG when a consumer is attached (`video_feed`).

### C. Windows-first sidecar packaging  (cannot finish here; needs Windows runner)
- **Documented with concrete steps + a starter PyInstaller `.spec` in
  [`docs/PACKAGING.md`](PACKAGING.md)** (this commit). Confirmed from source: Tauri
  spawns `python3 main.py` (`lib.rs:57`, no `externalBin`); `kill_backend` does
  `child.kill()` only (orphans Piper/audio); `tauri.conf.json` has no `externalBin`.
- Remaining (on a Windows+Linux runner): build the sidecar, wire `externalBin`,
  switch `spawn_backend` to the sidecar in release, kill the process **tree**, move
  config/cache to OS app-data, CI. **Pin Python ~3.11/3.12** for wheel availability.

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

**D.2 — opt-in API-token gate ✅ PARTIAL (this commit):**
- `auth_token.py` (pure, 7 tests): `request_authorized(path, method, provided, expected)`
  — auth off when no token; reads always pass; privileged **writes** (`/api/config`,
  `/api/unev-content`, `/api/camera`, `/api/llm/test`, `/api/train`, `/api/speak`)
  require `X-API-Token` (constant-time compare). `generate_token()` helper.
- `main.py`: opt-in HTTP middleware gated on `HOLOGRAM_API_TOKEN` (empty = current
  behavior, no breakage). When set, the **Tauri shell must deliver the token to the
  frontend** (Rust env → `get_backend_url`-style command → `X-API-Token` header) — that
  wiring + **WS auth** (query token) still need the running desktop app to validate.

**D.2 — still open (needs the Tauri shell / running backend):**
- Deliver the token from Rust to the frontend + send it on every privileged call; WS
  capability token. OS keyring for secrets (Windows Credential Manager / Linux Secret
  Service) instead of plaintext `.env`/`config.json`. Rate limits / concurrency caps.
- Lock down CORS to the validated WebView origin (set `CORS_ALLOW_ORIGINS`).

### E. De-monkey-patch into typed services  (refactor; INTENTIONALLY DEFERRED)
- Highest-risk item and **not safe to do blind**: rewriting the startup
  monkey-patching + globals into services means changing `call.py`/`main.py` hot
  paths that can't be run in this env (no ML stack). Left for an environment where
  the backend runs end-to-end.
- Plan when picked up: `main.py:38-78` patches `call.speak`,
  `WhisperListener.listen_once`, `_camera_detection_callback` at startup; globals
  everywhere. Migrate toward `application/` services (conversation/config/device) +
  an event bus, strangler-style (add seam, route through it, keep working).
  `call.py` (~1300 L) and `main.py` (~970 L) are the god-modules to split.

### F. Single editable UNEV content source  ✅ DONE (this commit)
- `skills/unev_content.py` is now the single authoritative source: holds the
  canonical content + a validated loader (`load/save/get/reload`, atomic write,
  control-char clamp) with the in-code dict as emergency fallback only.
- `data/unev_info.json` regenerated as the **complete** content (was a stale partial
  copy → the running content used to be an ambiguous JSON+code mix). `university.py`
  rewritten to read everything from `get_unev_info()` (8 tests; behaviour preserved).
- Editable via UI: `GET/POST /api/unev-content` + a new **Contenido** screen
  (`frontend/src/screens/ContentScreen.tsx` + `hooks/useUnevContent.ts`), nav wired.
- Note: `event_mode.py` is persona/behaviour (no facts — correctly left alone).
  Residual, separate concerns (not UNEV-fact duplication): `skills/honduras.py` is
  general Honduras context; `TeachingScreen.tsx` has its own vision-demo labels.

### G. Legacy lint debt  ✅ DONE (this commit)
- `ruff check .` is now **clean** (was 36 issues). Applied only behavior-preserving
  fixes: safe autofixes (import sort, unused imports, `Optional→| None`, empty
  f-strings) + manual (relocated 3 misplaced imports — verified leaf utils have no
  circular dep and that the modules still `import`; dropped an unused loop index and
  a dead assignment; `# noqa: B904` on a user-facing ConnectionError).
- The heavy modules still can't be *run* here (no ML stack), but they compile and
  import cleanly.

## Reusable knobs already in the contract
Providers: openrouter, openai, claude_native, nvidia, custom_openai, ollama,
local_only. Model precedence: provider-specific env (`OPENAI_MODEL`…) > `LLM_MODEL`
> default (ollama never inherits `LLM_MODEL`). `LLM_BACKEND` is deprecated alias.
