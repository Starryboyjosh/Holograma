# Graph Report - Holograma  (2026-06-24)

## Corpus Check
- 95 files · ~110,487 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 935 nodes · 1575 edges · 80 communities (68 shown, 12 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 29 edges (avg confidence: 0.57)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f9939ecb`
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
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
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
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 69|Community 69]]
- [[_COMMUNITY_Community 70|Community 70]]
- [[_COMMUNITY_Community 71|Community 71]]
- [[_COMMUNITY_Community 78|Community 78]]
- [[_COMMUNITY_Community 79|Community 79]]
- [[_COMMUNITY_Community 83|Community 83]]
- [[_COMMUNITY_Community 84|Community 84]]
- [[_COMMUNITY_Community 90|Community 90]]
- [[_COMMUNITY_Community 109|Community 109]]

## God Nodes (most connected - your core abstractions)
1. `HologramFanController` - 32 edges
2. `_env()` - 26 edges
3. `YoloPersonDetector` - 25 edges
4. `WhisperListener` - 22 edges
5. `_is_quiet()` - 22 edges
6. `stream_llm_response()` - 18 edges
7. `Camera` - 18 edges
8. `voice_loop()` - 17 edges
9. `compilerOptions` - 17 edges
10. `compilerOptions` - 16 edges

## Surprising Connections (you probably didn't know these)
- `set_mode()` --calls--> `normalize_text()`  [INFERRED]
  call.py → skills/utils.py
- `handle_command()` --calls--> `normalize_text()`  [INFERRED]
  call.py → skills/utils.py
- `chat_to_voice()` --calls--> `normalize_text()`  [INFERRED]
  call.py → skills/utils.py
- `voice_loop()` --calls--> `normalize_text()`  [INFERRED]
  call.py → skills/utils.py
- `FastAPI` --uses--> `HologramFanController`  [INFERRED]
  main.py → hologram_controller.py

## Import Cycles
- 1-file cycle: `frontend/src-tauri/src/lib.rs -> frontend/src-tauri/src/lib.rs`
- 1-file cycle: `main.py -> main.py`

## Communities (80 total, 12 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (66): _build_messages(), _candidate_backends(), _chat_with_backend(), _chat_with_claude_native(), _chat_with_ollama(), _chat_with_openai_compatible(), generate_reply(), get_backend_status() (+58 more)

### Community 1 - "Community 1"
Cohesion: 0.12
Nodes (13): Combine custom classes and vocabulary into a single YOLOE text prompt., Detect custom objects using YOLOE text prompts from training data., Return a list of person detections in *frame*.          Each detection is a dict, Return person and custom object detections plus optional safe face count., Return the number of people detected in *frame*., Open the camera, read one frame, and return the person count., Detect people using YOLOe26 via the Ultralytics library.      Parameters     ---, Return the most recent annotated frame as JPEG bytes (or None). (+5 more)

### Community 2 - "Community 2"
Cohesion: 0.17
Nodes (12): get_powershell_command(), is_wsl(), Return True when running inside Windows Subsystem for Linux., Return a PowerShell executable path on Windows or WSL if available., Run a PowerShell script and return True when it succeeds., Use Windows built-in speech synthesis when Piper is unavailable., Use lightweight Linux TTS fallbacks when Piper is unavailable., Reproduce un fragmento con el TTS nativo del SO (fallback sin Piper). (+4 more)

### Community 3 - "Community 3"
Cohesion: 0.41
Nodes (11): check_audio_devices(), check_dependencies(), check_environment(), check_import(), fail(), main(), ok(), test_camera() (+3 more)

### Community 4 - "Community 4"
Cohesion: 0.15
Nodes (12): get_program_info(), get_university_context(), route_local_skill(), get_admission_info(), get_approval_info(), get_location_info(), get_program_info(), get_programs_summary() (+4 more)

### Community 5 - "Community 5"
Cohesion: 0.18
Nodes (17): ask_ai(), _build_camera_context(), _camera_detection_callback(), get_help_text(), handle_command(), _is_greeting(), _is_visual_question(), UNEV Hologram — Main entry point.  Regla de Oro A: Todas las rutas usan pathlib. (+9 more)

### Community 6 - "Community 6"
Cohesion: 0.06
Nodes (27): create_hologram_manager(), discover_devices(), HologramFanController, HologramStateManager, =============================================================  Controlador Pytho, Cierra la conexión TCP limpiamente., Envía exactamente 3 bytes al dispositivo.         El manual especifica: un solo, Enciende e inicia la rotación del holograma. [RUN] (+19 more)

### Community 7 - "Community 7"
Cohesion: 0.16
Nodes (14): chat_to_voice(), main(), Text input loop: keyboard → LLM → TTS., Bloquea hasta que toque escuchar, según el modo dinámico actual.      Devuelve `, Voice input loop: microphone → Whisper → LLM → TTS (Regla B: sounddevice)., Parse flags and run the appropriate loop., Speak text using Piper when possible, with OS-native fallbacks.     Utiliza segm, Start YOLO person detection in a background daemon thread. (+6 more)

### Community 8 - "Community 8"
Cohesion: 0.16
Nodes (18): CameraState, SessionCtx, SessionProvider(), SessionValue, useToast(), ChatSocket, useChatSocket(), UseChatSocketOptions (+10 more)

### Community 12 - "Community 12"
Cohesion: 0.05
Nodes (38): dependencies, react, react-dom, react-router-dom, tailwindcss, @tailwindcss/vite, @tauri-apps/api, devDependencies (+30 more)

### Community 13 - "Community 13"
Cohesion: 0.21
Nodes (12): get_piper_command_args(), get_piper_install_hint(), get_piper_model_path(), _piper_available(), _piper_synth_to_wav(), Return the command used to run Piper if it is available., Return a short installation hint for the current platform., Return the Piper voice model to use, preferring Spanish voices. (+4 more)

### Community 14 - "Community 14"
Cohesion: 0.08
Nodes (25): 1. Clonar e instalar dependencias:, 1. Núcleo y Orquestador (`call.py`), 2. Backend de Lenguaje (`llm_backend.py`), 2. Descargar Modelo Ollama (Recomendado para uso local):, 3. API y Servidor Web (`main.py`), 3. Ejecutar:, 3 Reglas de Oro (Compatibilidad Linux ↔ Windows), 4. Reconocimiento de Voz - STT (`stt/listener.py`) (+17 more)

### Community 15 - "Community 15"
Cohesion: 0.15
Nodes (11): AppShell(), NAV_ITEMS, AppearanceTheme, resolveDark(), ThemeCtx, ThemeProvider(), ThemeValue, useTheme() (+3 more)

### Community 16 - "Community 16"
Cohesion: 0.16
Nodes (11): get_piper_sample_rate(), Cambia en caliente el modo de activación de voz. Devuelve el modo final., Read Piper sample rate from the model JSON sidecar when available., set_trigger_mode(), Resuelve un nombre corto a la ruta de un .onnx incluido (0.4.x).          Ej.: `, Bloquea hasta detectar la palabra clave.          Parameters         ----------, Return True if openwakeword and sounddevice are importable., Detecta una palabra clave en streaming con openWakeWord. (+3 more)

### Community 17 - "Community 17"
Cohesion: 0.13
Nodes (12): FastAPI, _get_holo(), get_providers(), holo_command(), holo_connect(), holo_disconnect(), holo_status(), HologramCommand (+4 more)

### Community 18 - "Community 18"
Cohesion: 0.07
Nodes (11): Tests del contrato de proveedor/modelo (provider_config).  Cubren la lógica que, El proveedor 'custom_openai' lee key/modelo de las variables OPENAI_COMPAT_*., Regresión: proveedor explícito 'ollama' nunca cae a la nube por una key vieja., Si el operador elige openai, no se cambia en silencio a otro proveedor., El modelo de la interfaz (LLM_MODEL) aplica también a OpenAI/NVIDIA., Ollama no debe usar un modelo de la nube si solo está LLM_MODEL., test_custom_openai_resolves_key_and_model_from_compat_env(), test_explicit_cloud_provider_is_authoritative_even_without_key() (+3 more)

### Community 19 - "Community 19"
Cohesion: 0.11
Nodes (17): app, security, windows, build, beforeBuildCommand, beforeDevCommand, devUrl, frontendDist (+9 more)

### Community 20 - "Community 20"
Cohesion: 0.10
Nodes (19): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, jsx, lib, module, moduleDetection, moduleResolution (+11 more)

### Community 21 - "Community 21"
Cohesion: 0.11
Nodes (17): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, lib, module, moduleDetection, moduleResolution, noEmit (+9 more)

### Community 22 - "Community 22"
Cohesion: 0.21
Nodes (16): Child, Duration, Mutex, Option, PathBuf, backend_ready(), BackendState, free_port() (+8 more)

### Community 23 - "Community 23"
Cohesion: 0.13
Nodes (8): Camera, Release the camera resource., Return True if the camera is currently open., Capture one frame and save it to *output_path*.          Parameters         ----, Return True if OpenCV is importable., Cross-platform wrapper around OpenCV VideoCapture.      Supports both live camer, Open the camera or video source., Read a single frame.  Returns the frame or None on failure.

### Community 24 - "Community 24"
Cohesion: 0.12
Nodes (25): Hologram, QUICK_COMMANDS, OLLAMA_SUGGESTIONS, Props, ProviderConfigCard(), PROVIDERS, useProviders(), apiKeyPlaceholder() (+17 more)

### Community 25 - "Community 25"
Cohesion: 0.24
Nodes (11): configure_vision(), print_header(), Flujo interactivo para configurar el Cerebro (LLM local o Cloud)., Flujo interactivo para configurar los Oídos (Whisper)., Flujo interactivo para la Visión (YOLOv26 + OpenCV)., Ejecuta el asistente interactivo de configuración completo., Imprime el header estilo 'hermes setup'., run_setup() (+3 more)

### Community 26 - "Community 26"
Cohesion: 0.14
Nodes (13): A. Settings UX + wire test buttons  ✅ DONE (this commit)  ← B or D recommended next, B. Cancellation + camera release + per-session events  (touches call.py, higher risk), C. Windows-first sidecar packaging  (cannot finish here; needs Windows runner), D. Security + operator auth, E. De-monkey-patch into typed services  (refactor; do incrementally), F. Single editable UNEV content source, G. Legacy lint debt, Hard environment constraints (read first) (+5 more)

### Community 27 - "Community 27"
Cohesion: 0.16
Nodes (10): _looks_like_hallucination(), Load the Faster-Whisper model on first use., Record audio from the default microphone until silence is detected.          Usa, Write a float32 numpy array to a temporary WAV file.          Returns a ``pathli, Transcribe a WAV file and return the text.          Parameters         ---------, Record from the microphone and return the transcribed text.          Returns an, Return True if sounddevice and faster-whisper are importable., Return True if *text* is empty or a known Whisper silence-hallucination. (+2 more)

### Community 28 - "Community 28"
Cohesion: 0.15
Nodes (19): BaseModel, _atomic_write_text(), BoundingBoxModel, ConfigUpdate, play_speak(), Escritura atómica: archivo temporal + os.replace.      Evita config.json / .env, SpeakPayload, train_image() (+11 more)

### Community 29 - "Community 29"
Cohesion: 0.13
Nodes (14): anyOf, definitions, Number, PermissionEntry, Target, description, anyOf, description (+6 more)

### Community 30 - "Community 30"
Cohesion: 0.13
Nodes (14): anyOf, definitions, Number, Target, Value, description, anyOf, description (+6 more)

### Community 31 - "Community 31"
Cohesion: 0.36
Nodes (3): FaceAnalyzer, Count visible frontal faces using OpenCV's bundled Haar cascade., Return a safe visual summary for a frame.

### Community 32 - "Community 32"
Cohesion: 0.32
Nodes (11): CameraFeed(), CameraFeedProps, useBackendUrl(), apiFetch(), apiUrl(), backendBase(), detectBase(), mediaUrl() (+3 more)

### Community 33 - "Community 33"
Cohesion: 0.21
Nodes (11): DetachButton(), DetachButtonProps, HologramControls(), isTauriRuntime(), openWidgetWindow(), WIDGET_META, widgetHash(), WidgetMeta (+3 more)

### Community 34 - "Community 34"
Cohesion: 0.20
Nodes (10): properties, type, default, description, type, identifier, local, remote (+2 more)

### Community 35 - "Community 35"
Cohesion: 0.20
Nodes (10): $ref, description, items, type, uniqueItems, description, items, type (+2 more)

### Community 36 - "Community 36"
Cohesion: 0.20
Nodes (10): type, webviews, windows, items, description, items, type, description (+2 more)

### Community 37 - "Community 37"
Cohesion: 0.20
Nodes (10): properties, type, default, description, type, identifier, local, remote (+2 more)

### Community 38 - "Community 38"
Cohesion: 0.15
Nodes (4): Exception, Tests de la integración de llm_backend con el contrato de proveedor.  No hacen l, test_humanize_probe_error_maps_common_cases(), test_humanize_probe_error_redacts_leaked_key_in_generic_branch()

### Community 39 - "Community 39"
Cohesion: 0.20
Nodes (10): $ref, description, items, type, uniqueItems, description, items, type (+2 more)

### Community 40 - "Community 40"
Cohesion: 0.20
Nodes (10): type, webviews, windows, items, description, items, type, description (+2 more)

### Community 41 - "Community 41"
Cohesion: 0.25
Nodes (8): description, properties, required, type, CapabilityRemote, urls, description, type

### Community 42 - "Community 42"
Cohesion: 0.25
Nodes (8): description, properties, required, type, CapabilityRemote, urls, description, type

### Community 43 - "Community 43"
Cohesion: 0.25
Nodes (7): Cómo funciona, Desarrollo, Empaquetado del backend (PENDIENTE — paso posterior), Holograma UNEV — Shell de escritorio (Tauri v2), Requisitos, Variables de entorno útiles, Widgets desprendibles

### Community 44 - "Community 44"
Cohesion: 0.33
Nodes (5): description, identifier, permissions, $schema, windows

### Community 45 - "Community 45"
Cohesion: 0.33
Nodes (3): Draw person and custom-object boxes on a copy of *frame*., Encode *frame* (with overlay) to JPEG and cache it for streaming., Run a detection loop calling *callback(event, count)* on changes.          Param

### Community 46 - "Community 46"
Cohesion: 0.27
Nodes (9): Orb(), OrbProps, AssistantScreen(), highlighted(), SUGGESTIONS, AssistantState, COLORS, ORB_RING (+1 more)

### Community 48 - "Community 48"
Cohesion: 0.50
Nodes (4): description, required, type, Capability

### Community 49 - "Community 49"
Cohesion: 0.50
Nodes (4): default, description, type, description

### Community 50 - "Community 50"
Cohesion: 0.50
Nodes (4): description, required, type, Capability

### Community 51 - "Community 51"
Cohesion: 0.50
Nodes (4): default, description, type, description

### Community 53 - "Community 53"
Cohesion: 0.67
Nodes (3): Identifier, description, oneOf

### Community 54 - "Community 54"
Cohesion: 0.67
Nodes (3): Identifier, description, oneOf

### Community 56 - "Community 56"
Cohesion: 0.50
Nodes (4): _placeholder_jpeg(), Build a simple 'no signal' JPEG so the <img> always shows something., Stream the annotated YOLO camera frames to the web interface as MJPEG., video_feed()

### Community 58 - "Community 58"
Cohesion: 0.38
Nodes (5): useSession(), CAPABILITIES, HomeScreen(), TeachingScreen(), BoundingBox

### Community 59 - "Community 59"
Cohesion: 0.22
Nodes (10): get_trigger_mode(), Solicita una escucha puntual (push-to-talk remoto, p. ej. la WebApp)., Devuelve el modo de activación de voz actual., Lee ENTER de la terminal y solicita una escucha (push-to-talk en CLI)., request_listen(), _stdin_ptt_reader(), Send host-side TTS status updates to the web client., send_tts_status() (+2 more)

### Community 60 - "Community 60"
Cohesion: 0.25
Nodes (7): Configuración de IA — Contrato de proveedor y modelo, Cómo se elige el backend (`select_backend`), Endpoints relacionados, Endurecimiento de seguridad (Fase D.1), Interfaz de Ajustes, Proveedores soportados, Pruebas

### Community 61 - "Community 61"
Cohesion: 0.50
Nodes (4): pause_hologram(), Attempt to terminate any running TTS or audio players on Linux., Pause hologram activity: stop speaking, listening and seeing., stop_all_tts_processes()

### Community 62 - "Community 62"
Cohesion: 0.33
Nodes (6): play_wav_file(), play_wav_with_windows(), Play a WAV file with Windows' built-in SoundPlayer., Play a WAV file on Windows, Linux, or macOS using available system tools., Sintetiza y reproduce los fragmentos de voz.      Con Piper usa un *pipeline*: u, _render_chunks()

### Community 63 - "Community 63"
Cohesion: 0.50
Nodes (4): clean_for_tts(), Remove characters that can sound awkward when read by a TTS engine., Divide el texto en fragmentos listos para TTS.     El primero usa cláusulas para, _split_into_chunks()

### Community 64 - "Community 64"
Cohesion: 0.67
Nodes (3): LlmTestPayload, Prueba real de proveedor/modelo/key/URL sin guardar nada.      Devuelve un mensa, test_llm()

### Community 65 - "Community 65"
Cohesion: 0.67
Nodes (3): Value, anyOf, description

### Community 69 - "Community 69"
Cohesion: 0.67
Nodes (3): PermissionEntry, anyOf, description

### Community 71 - "Community 71"
Cohesion: 0.50
Nodes (3): Expanding the ESLint configuration, React Compiler, React + TypeScript + Vite

## Knowledge Gaps
- **241 isolated node(s):** `name`, `private`, `version`, `type`, `dev` (+236 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **12 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `YoloPersonDetector` connect `Community 1` to `Community 0`, `Community 3`, `Community 5`, `Community 7`, `Community 45`, `Community 52`, `Community 23`, `Community 31`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._
- **Why does `HologramFanController` connect `Community 6` to `Community 64`, `Community 17`, `Community 59`, `Community 28`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **Why does `Camera` connect `Community 23` to `Community 0`, `Community 1`, `Community 3`, `Community 45`, `Community 52`?**
  _High betweenness centrality (0.016) - this node is a cross-community bridge._
- **Are the 10 inferred relationships involving `HologramFanController` (e.g. with `FastAPI` and `BoundingBoxModel`) actually correct?**
  _`HologramFanController` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `YoloPersonDetector` (e.g. with `Camera` and `FaceAnalyzer`) actually correct?**
  _`YoloPersonDetector` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 10 inferred relationships involving `WhisperListener` (e.g. with `FastAPI` and `BoundingBoxModel`) actually correct?**
  _`WhisperListener` has 10 INFERRED edges - model-reasoned connections that need verification._
- **What connects `UNEV Hologram — Main entry point.  Regla de Oro A: Todas las rutas usan pathlib.`, `Attempt to terminate any running TTS or audio players on Linux.`, `Pause hologram activity: stop speaking, listening and seeing.` to the rest of the system?**
  _388 weakly-connected nodes found - possible documentation gaps or missing edges._