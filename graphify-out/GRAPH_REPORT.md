# Graph Report - Holograma  (2026-06-19)

## Corpus Check
- 115 files · ~191,171 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 880 nodes · 1212 edges · 76 communities (60 shown, 16 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 23 edges (avg confidence: 0.57)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `46ca35ac`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 66|Community 66]]
- [[_COMMUNITY_Community 67|Community 67]]
- [[_COMMUNITY_Community 68|Community 68]]
- [[_COMMUNITY_Community 69|Community 69]]
- [[_COMMUNITY_Community 70|Community 70]]
- [[_COMMUNITY_Community 71|Community 71]]
- [[_COMMUNITY_Community 72|Community 72]]
- [[_COMMUNITY_Community 73|Community 73]]
- [[_COMMUNITY_Community 78|Community 78]]
- [[_COMMUNITY_Community 79|Community 79]]
- [[_COMMUNITY_Community 82|Community 82]]
- [[_COMMUNITY_Community 83|Community 83]]
- [[_COMMUNITY_Community 84|Community 84]]
- [[_COMMUNITY_Community 87|Community 87]]
- [[_COMMUNITY_Community 89|Community 89]]
- [[_COMMUNITY_Community 90|Community 90]]
- [[_COMMUNITY_Community 92|Community 92]]
- [[_COMMUNITY_Community 93|Community 93]]
- [[_COMMUNITY_Community 103|Community 103]]
- [[_COMMUNITY_Community 109|Community 109]]

## God Nodes (most connected - your core abstractions)
1. `HologramFanController` - 30 edges
2. `_env()` - 23 edges
3. `YoloPersonDetector` - 22 edges
4. `WhisperListener` - 20 edges
5. `Camera` - 18 edges
6. `compilerOptions` - 17 edges
7. `compilerOptions` - 16 edges
8. `_is_quiet()` - 16 edges
9. `stream_llm_response()` - 15 edges
10. `voice_loop()` - 13 edges

## Surprising Connections (you probably didn't know these)
- `set_mode()` --calls--> `normalize_text()`  [INFERRED]
  call.py → skills/utils.py
- `handle_command()` --calls--> `normalize_text()`  [INFERRED]
  call.py → skills/utils.py
- `chat_to_voice()` --calls--> `normalize_text()`  [INFERRED]
  call.py → skills/utils.py
- `voice_loop()` --calls--> `normalize_text()`  [INFERRED]
  call.py → skills/utils.py
- `BoundingBoxModel` --uses--> `HologramFanController`  [INFERRED]
  main.py → hologram_controller.py

## Import Cycles
- None detected.

## Communities (76 total, 16 thin omitted)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (23): Camera, Release the camera resource., Return True if the camera is currently open., Capture one frame and save it to *output_path*.          Parameters         ----, Return True if OpenCV is importable., Cross-platform wrapper around OpenCV VideoCapture.      Supports both live camer, Open the camera or video source., Read a single frame.  Returns the frame or None on failure. (+15 more)

### Community 2 - "Community 2"
Cohesion: 0.06
Nodes (69): ask_ai(), _build_camera_context(), _camera_detection_callback(), chat_to_voice(), get_help_text(), handle_command(), _is_greeting(), _is_visual_question() (+61 more)

### Community 4 - "Community 4"
Cohesion: 0.15
Nodes (12): get_program_info(), get_university_context(), route_local_skill(), get_admission_info(), get_approval_info(), get_location_info(), get_program_info(), get_programs_summary() (+4 more)

### Community 5 - "Community 5"
Cohesion: 0.06
Nodes (49): claudeDir, {
  clearMode,
  isCodex,
  setMode,
  writeHookOutput,
}, fs, { getDefaultMode, getClaudeDir }, { getPonytailInstructions }, mode, output, path (+41 more)

### Community 6 - "Community 6"
Cohesion: 0.06
Nodes (27): create_hologram_manager(), discover_devices(), HologramFanController, HologramStateManager, =============================================================  Controlador Pytho, Cierra la conexión TCP limpiamente., Envía exactamente 3 bytes al dispositivo.         El manual especifica: un solo, Enciende e inicia la rotación del holograma. [RUN] (+19 more)

### Community 7 - "Community 7"
Cohesion: 0.08
Nodes (24): { checkPy, pyBlock, TASKS }, email, fs, kv, MODELS, path, skill, { checkPy, pyBlock, TASKS } (+16 more)

### Community 12 - "Community 12"
Cohesion: 0.07
Nodes (27): dependencies, react, react-dom, tailwindcss, @tailwindcss/vite, devDependencies, eslint, @eslint/js (+19 more)

### Community 13 - "Community 13"
Cohesion: 0.08
Nodes (22): Adapter Rule, Agent Portability, Portable Behavior, Supported Adapters, Ponytail, lazy senior dev mode, Ponytail, lazy senior dev mode, Antigravity CLI, Before / after (+14 more)

### Community 14 - "Community 14"
Cohesion: 0.08
Nodes (24): 1. Clonar e instalar dependencias:, 1. Núcleo y Orquestador (`call.py`), 2. Backend de Lenguaje (`llm_backend.py`), 2. Descargar Modelo Ollama (Recomendado para uso local):, 3. API y Servidor Web (`main.py`), 3. Ejecutar:, 3 Reglas de Oro (Compatibilidad Linux ↔ Windows), 4. Reconocimiento de Voz - STT (`stt/listener.py`) (+16 more)

### Community 16 - "Community 16"
Cohesion: 0.15
Nodes (20): clean_for_tts(), Remove characters that can sound awkward when read by a TTS engine., Divide el texto en fragmentos listos para TTS.     El primero usa cláusulas para, Speak text using Piper when possible, with OS-native fallbacks.     Utiliza segm, speak(), _split_into_chunks(), check_audio_devices(), check_dependencies() (+12 more)

### Community 17 - "Community 17"
Cohesion: 0.07
Nodes (34): BaseModel, Start YOLO person detection in a background daemon thread., start_camera_thread(), BoundingBoxModel, ConfigUpdate, _get_holo(), holo_command(), holo_connect() (+26 more)

### Community 18 - "Community 18"
Cohesion: 0.10
Nodes (16): CHECKS, exec(), { execSync }, fs, os, path, python(), assert (+8 more)

### Community 19 - "Community 19"
Cohesion: 0.10
Nodes (18): assert, claudeEnv, codexData, codexEnv, codexState, copilotData, customConfigDir, fs (+10 more)

### Community 20 - "Community 20"
Cohesion: 0.11
Nodes (18): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, jsx, lib, module, moduleDetection, moduleResolution (+10 more)

### Community 21 - "Community 21"
Cohesion: 0.11
Nodes (17): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, lib, module, moduleDetection, moduleResolution, noEmit (+9 more)

### Community 23 - "Community 23"
Cohesion: 0.21
Nodes (12): DESCRIPTIONS, fs, NAMES, outPath(), path, render(), ROOT, sourceBody() (+4 more)

### Community 24 - "Community 24"
Cohesion: 0.17
Nodes (9): agents, canonical, copies, fs, INVARIANTS, path, root, skill (+1 more)

### Community 25 - "Community 25"
Cohesion: 0.24
Nodes (11): configure_vision(), print_header(), Flujo interactivo para configurar el Cerebro (LLM local o Cloud)., Flujo interactivo para configurar los Oídos (Whisper)., Flujo interactivo para la Visión (YOLOv26 + OpenCV)., Ejecuta el asistente interactivo de configuración completo., Imprime el header estilo 'hermes setup'., run_setup() (+3 more)

### Community 26 - "Community 26"
Cohesion: 0.18
Nodes (11): assert, fs, loadManifest(), path, read(), REUSED_COMMANDS, REUSED_SKILLS, root (+3 more)

### Community 27 - "Community 27"
Cohesion: 0.18
Nodes (10): description, keywords, license, name, pi, extensions, skills, scripts (+2 more)

### Community 29 - "Community 29"
Cohesion: 0.20
Nodes (9): Acceptance criteria (brief §5.6), Addendum: same-model control arm (control2, added same day), Build phase — non-blank LOC / .py files (scorer-verified), Correctness, Extension phase (tasks C, D — surprise requests, git-measured), Ponytail v4 hardening — A–F benchmark vs Caveman (2026-06-12), Residual (honest notes), Safety — adversarial probes (independently executed) (+1 more)

### Community 30 - "Community 30"
Cohesion: 0.20
Nodes (8): assert, fs, os, path, { pathToFileURL }, statePath, test, tmp

### Community 31 - "Community 31"
Cohesion: 0.25
Nodes (5): CHECKS, assert, behavior, check(), test

### Community 32 - "Community 32"
Cohesion: 0.22
Nodes (8): Benchmark, Claude (Haiku / Sonnet / Opus), Local models via Ollama, Median results (10 runs, 2026-06-13), Metrics, Notes, Prerequisites, Reproduce

### Community 34 - "Community 34"
Cohesion: 0.09
Nodes (26): get_piper_command_args(), get_piper_install_hint(), get_piper_model_path(), get_piper_sample_rate(), get_powershell_command(), is_wsl(), play_wav_file(), play_wav_with_windows() (+18 more)

### Community 35 - "Community 35"
Cohesion: 0.22
Nodes (8): Boundaries, Intensity, Output, Persistence, Ponytail, Rules, The ladder, When NOT to be lazy

### Community 36 - "Community 36"
Cohesion: 0.22
Nodes (8): Boundaries, Intensity, Output, Persistence, Ponytail, Rules, The ladder, When NOT to be lazy

### Community 37 - "Community 37"
Cohesion: 0.22
Nodes (8): Conclusion, Edge-case traps (n=20/cell), Method, Reproduce, Robustness audit: does ponytail degrade weak models? (2026-06-16), The fix that wasn't, TL;DR, Validators: the email slip is provider-specific

### Community 38 - "Community 38"
Cohesion: 0.50
Nodes (7): Action, T, sendMessage(), submitPassword(), TestChatStreamingComplete(), TestUnlockSuccess(), TestWrongPasswordAlert()

### Community 39 - "Community 39"
Cohesion: 0.39
Nodes (7): call_ollama(), count_loc(), load_arms(), main(), Ponytail local benchmark — runs the same 5 tasks against any Ollama model. No pr, Non-blank, non-comment lines of code: fenced blocks, or the whole     response w, run()

### Community 40 - "Community 40"
Cohesion: 0.25
Nodes (7): description, name, owner, name, url, plugins, $schema

### Community 41 - "Community 41"
Cohesion: 0.25
Nodes (7): Configure Default Mode, Deactivate, Levels, More, Ponytail Help, Skills, Update

### Community 42 - "Community 42"
Cohesion: 0.25
Nodes (7): Configure Default Mode, Deactivate, Levels, More, Ponytail Help, Skills, Update

### Community 43 - "Community 43"
Cohesion: 0.25
Nodes (7): assert, commands, fs, path, piSource, root, test

### Community 44 - "Community 44"
Cohesion: 0.25
Nodes (6): assert, fs, path, REQUIRED_COMMAND_FILES, root, test

### Community 45 - "Community 45"
Cohesion: 0.29
Nodes (6): Caveman vs Ponytail — 2026-06-12, Ponytail v1 (before this benchmark), Ponytail v2 (after fixes), Ponytail v3 (skill file compressed), v1 findings, Verdict (v3)

### Community 46 - "Community 46"
Cohesion: 0.29
Nodes (5): assert, fs, path, root, test

### Community 47 - "Community 47"
Cohesion: 0.33
Nodes (5): Auto-Clarity, Boundaries, Intensity, Persistence, Rules

### Community 49 - "Community 49"
Cohesion: 0.33
Nodes (5): name, private, scripts, test, type

### Community 50 - "Community 50"
Cohesion: 0.33
Nodes (5): Key findings, Local model benchmark: llama3.2 via Ollama — 2026-06-15, Reproduce, Results (n=5, median), Takeaway

### Community 51 - "Community 51"
Cohesion: 0.33
Nodes (5): Claude re-score of committed responses through the fixed gate, Correctness under Ponytail: gate fixes + GPT-mini reproduction (2026-06-16), GPT arms (needs OPENAI_API_KEY in ../.env), The gate bugs, TL;DR

### Community 52 - "Community 52"
Cohesion: 0.40
Nodes (4): Boundaries, Hunt, Output, Tags

### Community 53 - "Community 53"
Cohesion: 0.40
Nodes (4): Boundaries, Examples, Format, Scoring

### Community 54 - "Community 54"
Cohesion: 0.40
Nodes (4): Boundaries, Hunt, Output, Tags

### Community 55 - "Community 55"
Cohesion: 0.40
Nodes (4): Boundaries, Examples, Format, Scoring

### Community 57 - "Community 57"
Cohesion: 0.50
Nodes (3): fs, path, system

### Community 58 - "Community 58"
Cohesion: 0.50
Nodes (3): fs, path, system

### Community 66 - "Community 66"
Cohesion: 0.50
Nodes (3): API Endpoint, With Ponytail, Without Ponytail

### Community 67 - "Community 67"
Cohesion: 0.50
Nodes (3): Caching System, With Ponytail, Without Ponytail

### Community 68 - "Community 68"
Cohesion: 0.50
Nodes (3): Date Picker, With Ponytail, Without Ponytail

### Community 69 - "Community 69"
Cohesion: 0.50
Nodes (3): Email Validation, With Ponytail, Without Ponytail

### Community 70 - "Community 70"
Cohesion: 0.50
Nodes (3): Sorting, With Ponytail, Without Ponytail

### Community 71 - "Community 71"
Cohesion: 0.50
Nodes (3): Expanding the ESLint configuration, React Compiler, React + TypeScript + Vite

### Community 72 - "Community 72"
Cohesion: 0.50
Nodes (3): Boundaries, Output, Scan

### Community 73 - "Community 73"
Cohesion: 0.50
Nodes (3): Boundaries, Output, Scan

## Knowledge Gaps
- **370 isolated node(s):** `name`, `private`, `version`, `type`, `dev` (+365 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **16 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `YoloPersonDetector` connect `Community 1` to `Community 16`, `Community 17`, `Community 2`?**
  _High betweenness centrality (0.030) - this node is a cross-community bridge._
- **Why does `HologramFanController` connect `Community 6` to `Community 17`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **Why does `Camera` connect `Community 1` to `Community 16`, `Community 2`?**
  _High betweenness centrality (0.013) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `HologramFanController` (e.g. with `BoundingBoxModel` and `ConfigUpdate`) actually correct?**
  _`HologramFanController` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `YoloPersonDetector` (e.g. with `Camera` and `FaceAnalyzer`) actually correct?**
  _`YoloPersonDetector` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `WhisperListener` (e.g. with `BoundingBoxModel` and `ConfigUpdate`) actually correct?**
  _`WhisperListener` has 8 INFERRED edges - model-reasoned connections that need verification._
- **What connects `UNEV Hologram — Main entry point.  Regla de Oro A: Todas las rutas usan pathlib.`, `Attempt to terminate any running TTS or audio players on Linux.`, `Pause hologram activity: stop speaking, listening and seeing.` to the rest of the system?**
  _470 weakly-connected nodes found - possible documentation gaps or missing edges._