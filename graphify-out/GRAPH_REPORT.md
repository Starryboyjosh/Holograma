# Graph Report - .  (2026-06-15)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 238 nodes · 440 edges · 12 communities (8 shown, 4 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS · INFERRED: 2 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `bf79fe3c`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]

## God Nodes (most connected - your core abstractions)
1. `YoloPersonDetector` - 19 edges
2. `Camera` - 18 edges
3. `FaceAnalyzer` - 13 edges
4. `voice_loop()` - 11 edges
5. `generate_reply()` - 11 edges
6. `route_local_skill()` - 11 edges
7. `WhisperListener` - 11 edges
8. `_env()` - 10 edges
9. `get_backend_status()` - 10 edges
10. `handle_command()` - 9 edges

## Surprising Connections (you probably didn't know these)
- `test_speak()` --calls--> `speak()`  [EXTRACTED]
  diagnose_hologram.py → call.py
- `ask_ai()` --calls--> `generate_reply()`  [EXTRACTED]
  call.py → llm_backend.py
- `ask_ai()` --calls--> `get_selected_backend()`  [EXTRACTED]
  call.py → llm_backend.py
- `ask_ai()` --calls--> `route_local_skill()`  [EXTRACTED]
  call.py → skills/router.py
- `handle_command()` --calls--> `get_backend_status()`  [EXTRACTED]
  call.py → llm_backend.py

## Import Cycles
- None detected.

## Communities (12 total, 4 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (54): ask_ai(), _camera_detection_callback(), chat_to_voice(), clean_for_tts(), configure_utf8_stdio(), get_help_text(), get_piper_command_args(), get_piper_install_hint() (+46 more)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (27): Camera, _env_int(), Cross-platform OpenCV camera wrapper.  Regla de Oro A: Todas las rutas usan path, Release the camera resource., Return True if the camera is currently open., Capture one frame and save it to *output_path*.          Parameters         ----, Return True if OpenCV is importable., Read an integer environment variable or return a default. (+19 more)

### Community 2 - "Community 2"
Cohesion: 0.16
Nodes (28): Exception, _build_messages(), _chat_with_claude_native(), _chat_with_nvidia(), _chat_with_ollama(), _chat_with_openai(), _chat_with_openrouter(), _env() (+20 more)

### Community 3 - "Community 3"
Cohesion: 0.12
Nodes (17): configure_utf8_stdio(), _env(), _env_float(), _env_int(), get_stt_status(), Speech-to-text listener using Faster-Whisper and sounddevice.  Regla de Oro A: T, Load the Faster-Whisper model on first use., Record audio from the default microphone until silence is detected.          Ret (+9 more)

### Community 4 - "Community 4"
Cohesion: 0.15
Nodes (11): get_program_info(), get_university_context(), normalize_text(), route_local_skill(), get_admission_info(), get_approval_info(), get_location_info(), get_program_info() (+3 more)

### Community 5 - "Community 5"
Cohesion: 0.41
Nodes (11): check_audio_devices(), check_dependencies(), check_environment(), check_import(), fail(), main(), ok(), test_camera() (+3 more)

### Community 6 - "Community 6"
Cohesion: 0.22
Nodes (6): _env_float(), _env_int(), FaceAnalyzer, Safe face presence analysis with OpenCV.  This module only detects/counts visibl, Count visible frontal faces using OpenCV's bundled Haar cascade., Return a safe visual summary for a frame.

### Community 7 - "Community 7"
Cohesion: 0.24
Nodes (11): configure_vision(), print_header(), Flujo interactivo para configurar el Cerebro (LLM local o Cloud)., Flujo interactivo para configurar los Oídos (Whisper)., Flujo interactivo para la Visión (YOLOv26 + OpenCV)., Ejecuta el asistente interactivo de configuración completo., Imprime el header estilo 'hermes setup'., run_setup() (+3 more)

## Knowledge Gaps
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `YoloPersonDetector` connect `Community 1` to `Community 0`, `Community 5`, `Community 6`?**
  _High betweenness centrality (0.371) - this node is a cross-community bridge._
- **Why does `Camera` connect `Community 1` to `Community 5`?**
  _High betweenness centrality (0.153) - this node is a cross-community bridge._
- **Why does `WhisperListener` connect `Community 3` to `Community 0`?**
  _High betweenness centrality (0.123) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `YoloPersonDetector` (e.g. with `Camera` and `FaceAnalyzer`) actually correct?**
  _`YoloPersonDetector` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `UNEV Hologram — Main entry point.  Regla de Oro A: Todas las rutas usan pathlib.`, `Keep Windows consoles from crashing on non-ASCII output.`, `Remove characters that can sound awkward when read by a TTS engine.` to the rest of the system?**
  _67 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.05727644652250146 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.06292517006802721 - nodes in this community are weakly interconnected._