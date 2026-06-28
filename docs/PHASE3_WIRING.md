# Phase 3 wiring — next-session execution plan

Surgical, code-grounded plan to finish Phase 3 (de-monkey-patch `main.py` into the
tested `app/` service layer) and then §8 folder reorg. Written because 23% of a
session wasn't enough to do it **with validation** — and this item is the riskiest
in the whole plan, so it must not be rushed. Everything below is grounded in the
actual `main.py` as of commit on 2026-06-27.

## 0. READ FIRST — the backend RUNS on this machine
Earlier sessions wrongly believed the venv was empty and the backend couldn't run
here. **That was false** (see memory `backend-runs-locally`). Verified: `.venv`
(Python 3.14.5) has the full stack (torch 2.12+cpu, ultralytics, faster-whisper,
piper, fastapi, opencv, sounddevice); `/dev/video0` opens a real frame; audio
devices present; `main.py` imports and builds the FastAPI app; `OPENROUTER_API_KEY`
is set. **So you CAN start the server and validate each step — do not defer as
"hardware-gated".** Only the physical hologram fan (external TCP) and *hearing*
audio still need the operator.

### Validation recipe (run before AND after every step)
```bash
.venv/bin/python -m pytest -q            # expect 91 green
.venv/bin/ruff check .                   # clean
# Pure HTTP/WS smoke test WITHOUT grabbing camera/mic (set both off):
HOLOGRAM_CAMERA=0 HOLOGRAM_INPUT=keyboard .venv/bin/python main.py   # run_in_background
# then: curl -s localhost:8000/api/providers   (expect provider JSON)
#       open a WS to /ws (see frontend useChatSocket.ts), send a prompt,
#       assert sequence: streaming_started → text_chunk* → text_done
#                        → audio_status:processing → audio_status:completed
# stop the background server when done.
```
Full end-to-end (camera + voice): set `HOLOGRAM_CAMERA=1` / `HOLOGRAM_INPUT=voice`,
but the server then holds `/dev/video0` + the mic — make sure no other instance
(or the operator's own) is running first.

## 1. What the monkey-patching actually does — DO NOT delete blindly
`lifespan` (`main.py` L62-123) patches THREE things so the **voice loop**
(`call.voice_loop`, a background *thread*: mic→STT→LLM→TTS) can push events to the
web UI:
- **L95** `call.speak = custom_speak` — currently a NO-OP wrapper. It exists only to
  document "TTS must not re-emit text" (the symptom-B fix). The WS path is the sole
  text emitter.
- **L106** `WhisperListener.listen_once = custom_listen_once` — pushes
  `stt_transcript` to the web when the mic transcribes something.
- **L115** `call._camera_detection_callback = custom_callback` — pushes
  `camera_event` (+ count) to the web on detection.

The bridge is `send_to_web_client` (L235-267), which ends in
`asyncio.run_coroutine_threadsafe(do_send(), running_loop)` **because it is called
from a non-async thread** (the voice/camera threads). `active_connections` (L231)
is the global socket registry; the WS endpoint (L905 append / L934 iterate / L1013
remove) is the async producer.

> KEY SUBTLETY: there are **two** event producers — (a) the async WS chat endpoint
> (web text), already correct; (b) the voice/camera **threads**, which need a
> thread→loop hop. You **cannot** just delete `send_to_web_client`; the voice path
> still needs a thread-safe enqueue onto the loop.

## 2. Target wiring — strangler, smallest-risk first (one step = one commit)

**Step A — unify the socket registry (low risk).**
- `from app.connection import ConnectionManager; manager = ConnectionManager()`.
- WS endpoint: `await manager.register(ws)` / `unregister` / replace the ad-hoc
  broadcast loops (L934) with `await manager.broadcast(...)`.
- Re-implement `send_to_web_client`'s body as
  `asyncio.run_coroutine_threadsafe(manager.broadcast({...}), running_loop)` so the
  voice/camera threads keep working through the **same** manager.
- Now there is ONE registry. Delete the `active_connections` list once nothing
  references it. Validate (web chat streams; voice transcript still appears).

**Step B — route the WS turn through `ConversationService`.**
- Build once: `LLMService(stream_fn=llm_backend.stream_llm_response)`,
  `CameraContextProvider`, and a thin adapter exposing `async broadcast` over
  `manager`; then `ConversationService(llm, connection=adapter, camera=provider,
  speak=call.speak)`.
- In the WS endpoint, replace the manual stream/emit block with
  `await conversation.handle_prompt(prompt)` — the service already emits the exact
  sequence and runs TTS via `asyncio.to_thread`.
- Feed the camera: have `custom_callback` also call `provider.update(analysis)` so
  `build_context()` injects it into the LLM (cycle already broken via
  `stream_llm_response(camera_context=...)`). Validate end-to-end.

**Step C — retire the redundant patches.**
- `call.speak` patch (L95) is now redundant for web (the service owns TTS). Keep
  `call.speak` itself for the voice loop. Repoint the `listen_once`/camera patches
  to call `manager`/`provider` instead of the old global. Delete
  `send_to_web_client` + `running_loop` globals once unreferenced. Validate.

**Step D — drop `os.chdir(BASE_DIR)` (L41).**
- First anchor every relative path (`config.json`, `models/…`) to `BASE_DIR`, then
  remove the `chdir`. Also move the import-time Qt env fix into `lifespan`. Validate.

## 3. §8 folder reorg — ONLY after A–D are green
Move modules into `app/` + `core/`, **one move per commit**, with `pytest` + a
server boot between each. Highest churn, lowest urgency — do it last.

## 4. Don'ts
- Don't bundle A–D into one commit. One step, validate, commit, repeat.
- Don't remove the thread→loop bridge — the voice/camera producers are real threads.
- Don't build multi-tenancy/white-label. UNEV-only product.
