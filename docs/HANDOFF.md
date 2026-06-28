# Holograma UNEV — Handoff for the next agent

UNEV-only product. **Do not** build multi-tenancy/white-label. Read `CLAUDE.md`
(graphify rules: run `graphify query "..."` before grepping; `graphify update .`
after code changes). This doc is the onboarding shortcut so you don't re-derive
the audit.

## Latest session (2026-06-27) — symptom fixes + Phase 3 foundation
Implemented `ANALISIS_Y_PLAN_DE_MEJORA.md` Phases 0–2 (the freeze / "stuck on
hablando" / "no puedo responder" symptoms) plus the **testable foundation of
Phase 3** (de-monkey-patch, see §E). Verified by `pytest` (**91 passing**) +
`ruff` clean. **Correction (verified 2026-06-27):** the backend DOES run on this
machine (full `.venv`, cameras + audio present, `main.py` boots) — the deferred
items below are NOT hardware-gated; they were left for a fresh session with budget
to do them safely, one-step-per-commit. Surgical plan:
[`PHASE3_WIRING.md`](PHASE3_WIRING.md).

- **Phase 0 — symptom fixes (DONE, tested):**
  - `vision/person_detector.py`: removed the `was_present` clobber so a 1-frame
    blink no longer re-greets; object-detection failure is logged + disabled once
    instead of `except: pass`. (`tests/test_person_presence.py`)
  - `call.py` `custom_speak` no longer re-emits `streaming_started/text_chunk/
    text_done` — that double-emit was the "hablando" stuck state (symptom B).
  - `llm_backend._ollama_ready()` is cached with a TTL (`OLLAMA_READY_TTL_SECONDS`,
    default 10s) so the readiness probe stops hammering the loop.
    (`tests/test_ollama_ready_cache.py`)
  - Frontend `hooks/useChatSocket.ts`: 20s watchdog forces `idle` if a busy state
    goes silent (failsafe for a dropped `completed`).
- **Phase 1 — event-loop relief (PARTIAL, tested):** backend selection inside
  `stream_llm_response` now runs via `asyncio.to_thread`, so the cached Ollama
  probe never blocks the loop (symptom A: freeze). **Deliberate deviation:** the
  async generation path *already* uses `AsyncOpenAI`/`AsyncAnthropic`, so the
  plan's wholesale urllib→httpx rewrite buys the loop nothing and was NOT done.
  (`tests/test_llm_unify.py` asserts selection runs off the loop thread.)
- **Phase 2 — answer quality (PARTIAL, tested):** unified `max_tokens` via
  `LLM_MAX_TOKENS` (default 450) across every backend (was a mix of 350/450/1024/
  unbounded); the anti-English filter no longer **discards** a valid reply — it
  logs a warning and returns the text (symptom C: "no puedo responder").
  (`tests/test_llm_unify.py`)
- **Phase 3 — de-monkey-patch (PARTIAL, tested): see §E below.** New additive
  `app/` service layer; nothing imports it yet, so it is zero-risk to the running
  server. (`tests/test_app_services.py`, 10 tests.)

**Still to do (next session — see [`PHASE3_WIRING.md`](PHASE3_WIRING.md)):** wire the
`app/` services into `main.py` and delete the `lifespan` monkey-patching; route the
voice loop through the async service and delete sync `generate_reply`; async
`video_feed`; §8 folder move (`app/` + `core/`). These CAN be validated here (the
backend boots); they were deferred only for session budget, and must go
one-step-per-commit with the smoke test between.

## Hard environment constraints (read first)
- `.venv` is **Python 3.14, zero runtime deps installed**. The ML/STT/TTS/vision
  backend (torch, ultralytics, faster-whisper, sounddevice, piper, fastapi) is
  NOT installed and likely lacks 3.14 wheels. **You cannot launch or profile the
  backend here.** Prefer pure functions + mocked adapters + `pytest`.
- Installed dev tools: `pytest`, `ruff`, `python-dotenv`. Node 22 / npm 11 / cargo
  1.96 present.
- Workflow: **commit whole working tree directly to `main` and push** (no PRs).

## Verify (already done)
```bash
.venv/bin/pytest                                                  # 91 passing
.venv/bin/ruff check .                                            # clean
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

### E. De-monkey-patch into typed services  ✅ FOUNDATION DONE (wiring is runtime-gated)
The strangler-fig foundation is built and **fully unit-tested** (`tests/
test_app_services.py`, 10 tests). It is **additive**: no existing module imports
`app/` yet, so the running server is untouched. What exists now:
- **`app/connection.py` — `ConnectionManager`:** one async event emitter
  (`register/unregister/broadcast`, async lock, auto-purges dead sockets). The
  target replacement for `send_to_web_client` + `run_coroutine_threadsafe`.
- **`app/services/llm.py` — `LLMService`:** injectable wrapper over the single
  async path (`stream_llm_response`); default is a lazy import so tests pass a fake
  stream.
- **`app/services/vision.py` — `CameraContextProvider`:** the one explicit, testable
  seam for the `call ↔ llm_backend` cycle. Holds the last analysis and builds
  context in one place; the orchestrator injects it into the LLM.
- **`app/services/conversation.py` — `ConversationService`:** the heart. One turn,
  one emitter, the exact frontend sequence (`streaming_started → text_chunk* →
  text_done → audio_status:processing → completed`). Encodes the structural fixes:
  **TTS never re-emits text** (kills symptom B), TTS runs via `asyncio.to_thread`,
  state is **injected not global**, errors → `error` event.
- **Cycle-break shipped in prod code:** `stream_llm_response(prompt,
  camera_context=None)` now takes an optional injected context; when given, it does
  NOT reach into `call` (test proves `call._build_camera_context` is never called).
  Default `None` preserves the legacy path, so this is backward-compatible.

**Still open (needs the running backend — NOT safe blind):** wire these into
`main.py`, delete the `lifespan` monkey-patching of `call.speak` /
`WhisperListener.listen_once` / `_camera_detection_callback`, remove `os.chdir`,
move the Qt env fix off import-time, route the voice loop through
`ConversationService`, then the §8 folder move (one move per commit, `pytest`
between). **Step-by-step grounded in the current `main.py`:
[`docs/PHASE3_WIRING.md`](PHASE3_WIRING.md).** The backend boots here — this is no
longer blind; start the server and validate each step.

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
