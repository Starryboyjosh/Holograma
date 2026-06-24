# Graph Report - Holograma  (2026-06-24)

## Corpus Check
- 100 files · ~113,574 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 984 nodes · 1685 edges · 74 communities (62 shown, 12 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 45 edges (avg confidence: 0.64)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d448e5d9`
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
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 71|Community 71]]
- [[_COMMUNITY_Community 78|Community 78]]
- [[_COMMUNITY_Community 79|Community 79]]
- [[_COMMUNITY_Community 83|Community 83]]
- [[_COMMUNITY_Community 84|Community 84]]
- [[_COMMUNITY_Community 90|Community 90]]
- [[_COMMUNITY_Community 109|Community 109]]

## God Nodes (most connected - your core abstractions)
1. `HologramFanController` - 33 edges
2. `_env()` - 26 edges
3. `YoloPersonDetector` - 26 edges
4. `WhisperListener` - 23 edges
5. `_is_quiet()` - 22 edges
6. `stream_llm_response()` - 18 edges
7. `Camera` - 18 edges
8. `voice_loop()` - 17 edges
9. `useToast()` - 17 edges
10. `compilerOptions` - 17 edges

## Surprising Connections (you probably didn't know these)
- `get_powershell_command()` --calls--> `Path`  [INFERRED]
  call.py → skills/unev_content.py
- `play_wav_with_windows()` --calls--> `Path`  [INFERRED]
  call.py → skills/unev_content.py
- `set_mode()` --calls--> `normalize_text()`  [INFERRED]
  call.py → skills/utils.py
- `handle_command()` --calls--> `normalize_text()`  [INFERRED]
  call.py → skills/utils.py
- `chat_to_voice()` --calls--> `normalize_text()`  [INFERRED]
  call.py → skills/utils.py

## Import Cycles
- 1-file cycle: `frontend/src-tauri/src/lib.rs -> frontend/src-tauri/src/lib.rs`
- 1-file cycle: `main.py -> main.py`

## Communities (74 total, 12 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.09
Nodes (51): _build_messages(), _candidate_backends(), _chat_with_backend(), _chat_with_claude_native(), _chat_with_ollama(), _chat_with_openai_compatible(), generate_reply(), get_backend_status() (+43 more)

### Community 1 - "Community 1"
Cohesion: 0.10
Nodes (15): Load custom classes from training_metadata.json and open_vocabulary.txt., Combine custom classes and vocabulary into a single YOLOE text prompt., Detect custom objects using YOLOE text prompts from training data., Return a list of person detections in *frame*.          Each detection is a dict, Return person and custom object detections plus optional safe face count., Return True if at least one person is detected in *frame*., Return the number of people detected in *frame*., Detect people using YOLOe26 via the Ultralytics library.      Parameters     --- (+7 more)

### Community 2 - "Community 2"
Cohesion: 0.12
Nodes (18): get_powershell_command(), is_wsl(), play_wav_file(), play_wav_with_windows(), Return True when running inside Windows Subsystem for Linux., Return a PowerShell executable path on Windows or WSL if available., Run a PowerShell script and return True when it succeeds., Play a WAV file with Windows' built-in SoundPlayer. (+10 more)

### Community 3 - "Community 3"
Cohesion: 0.41
Nodes (11): check_audio_devices(), check_dependencies(), check_environment(), check_import(), fail(), main(), ok(), test_camera() (+3 more)

### Community 4 - "Community 4"
Cohesion: 0.34
Nodes (13): get_university_context(), route_local_skill(), get_unev_info(), Contenido vigente (cacheado). Llamado por las skills en cada respuesta., get_admission_info(), get_approval_info(), get_location_info(), get_program_info() (+5 more)

### Community 5 - "Community 5"
Cohesion: 0.10
Nodes (32): ask_ai(), _build_camera_context(), _camera_detection_callback(), chat_to_voice(), clean_for_tts(), get_help_text(), get_latest_camera_jpeg(), handle_command() (+24 more)

### Community 6 - "Community 6"
Cohesion: 0.09
Nodes (16): HologramFanController, Envía exactamente 3 bytes al dispositivo.         El manual especifica: un solo, Enciende e inicia la rotación del holograma. [RUN], Detiene la rotación y apaga el holograma. [STOP], Pausa la reproducción del video. [Pause], Reanuda la reproducción del video., Activa el loop del archivo que está reproduciéndose actualmente., Salta directamente al video número N de la playlist.          Args: (+8 more)

### Community 7 - "Community 7"
Cohesion: 0.12
Nodes (19): get_stt_status(), _looks_like_hallucination(), Speech-to-text listener using Faster-Whisper and sounddevice.  Regla de Oro A: T, Return True if *text* is empty or a known Whisper silence-hallucination., Return a human-readable status string for the STT subsystem., get_wakeword_status(), Detector de palabra clave (wake word) con openWakeWord.  Regla de Oro A: Todas l, Return a human-readable status string for the wake-word subsystem. (+11 more)

### Community 8 - "Community 8"
Cohesion: 0.16
Nodes (15): _atomic_write_text(), Escritura atómica: archivo temporal + os.replace.      Evita config.json / .env, Valida y guarda el contenido de UNEV; recarga la fuente en caliente.      Devuel, train_image(), train_vocabulary(), TrainImagePayload, update_unev_content(), VocabularyPayload (+7 more)

### Community 12 - "Community 12"
Cohesion: 0.05
Nodes (38): dependencies, react, react-dom, react-router-dom, tailwindcss, @tailwindcss/vite, @tauri-apps/api, devDependencies (+30 more)

### Community 13 - "Community 13"
Cohesion: 0.10
Nodes (22): get_piper_command_args(), get_piper_install_hint(), get_piper_model_path(), get_piper_sample_rate(), _piper_available(), _piper_synth_to_wav(), Return the command used to run Piper if it is available., Return a short installation hint for the current platform. (+14 more)

### Community 14 - "Community 14"
Cohesion: 0.08
Nodes (25): 1. Clonar e instalar dependencias:, 1. Núcleo y Orquestador (`call.py`), 2. Backend de Lenguaje (`llm_backend.py`), 2. Descargar Modelo Ollama (Recomendado para uso local):, 3. API y Servidor Web (`main.py`), 3. Ejecutar:, 3 Reglas de Oro (Compatibilidad Linux ↔ Windows), 4. Reconocimiento de Voz - STT (`stt/listener.py`) (+17 more)

### Community 15 - "Community 15"
Cohesion: 0.16
Nodes (3): get_program_info(), normalize_text(), Normalizes text by removing accents, lowercasing, and stripping whitespace.

### Community 16 - "Community 16"
Cohesion: 0.20
Nodes (10): Detén la detección y libera la cámara (apagar la cámara = liberarla).      Señal, Start YOLO person detection in a background daemon thread., start_camera_thread(), stop_camera_thread(), FastAPI, CameraToggle, lifespan(), Enciende o **apaga** la cámara liberando el dispositivo.      Apagar no solo ocu (+2 more)

### Community 17 - "Community 17"
Cohesion: 0.09
Nodes (25): BaseModel, BoundingBoxModel, ConfigUpdate, _get_holo(), get_unev_content(), holo_command(), holo_connect(), holo_disconnect() (+17 more)

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
Cohesion: 0.12
Nodes (9): Camera, Release the camera resource., Return True if the camera is currently open., Capture one frame and save it to *output_path*.          Parameters         ----, Return True if OpenCV is importable., Cross-platform wrapper around OpenCV VideoCapture.      Supports both live camer, Open the camera or video source., Read a single frame.  Returns the frame or None on failure. (+1 more)

### Community 24 - "Community 24"
Cohesion: 0.25
Nodes (4): Test del mecanismo de parada/liberación de la cámara (Fase B).  No requiere cáma, get_vision_status(), YOLOv8/v11 person detector for the UNEV hologram.  Regla de Oro A: Todas las rut, Return a human-readable status string for the vision subsystem.

### Community 25 - "Community 25"
Cohesion: 0.24
Nodes (11): configure_vision(), print_header(), Flujo interactivo para configurar el Cerebro (LLM local o Cloud)., Flujo interactivo para configurar los Oídos (Whisper)., Flujo interactivo para la Visión (YOLOv26 + OpenCV)., Ejecuta el asistente interactivo de configuración completo., Imprime el header estilo 'hermes setup'., run_setup() (+3 more)

### Community 26 - "Community 26"
Cohesion: 0.14
Nodes (13): A. Settings UX + wire test buttons  ✅ DONE (this commit)  ← B or D recommended next, B. Cancellation + camera release + per-session events  (touches call.py, higher risk), C. Windows-first sidecar packaging  (cannot finish here; needs Windows runner), D. Security + operator auth, E. De-monkey-patch into typed services  (refactor; do incrementally), F. Single editable UNEV content source  ✅ DONE (this commit), G. Legacy lint debt  ✅ DONE (this commit), Hard environment constraints (read first) (+5 more)

### Community 27 - "Community 27"
Cohesion: 0.27
Nodes (6): Load the Faster-Whisper model on first use., Record audio from the default microphone until silence is detected.          Usa, Transcribe a WAV file and return the text.          Parameters         ---------, Record from the microphone and return the transcribed text.          Returns an, _is_quiet(), Returns True if HOLOGRAM_QUIET env var is set to 1/true/yes.

### Community 28 - "Community 28"
Cohesion: 0.40
Nodes (4): anyOf, description, $schema, title

### Community 29 - "Community 29"
Cohesion: 0.15
Nodes (13): definitions, Number, PermissionEntry, Target, Value, anyOf, description, anyOf (+5 more)

### Community 30 - "Community 30"
Cohesion: 0.15
Nodes (13): definitions, Number, PermissionEntry, Target, Value, anyOf, description, anyOf (+5 more)

### Community 31 - "Community 31"
Cohesion: 0.31
Nodes (3): FaceAnalyzer, Count visible frontal faces using OpenCV's bundled Haar cascade., Return a safe visual summary for a frame.

### Community 32 - "Community 32"
Cohesion: 0.05
Nodes (69): AppShell(), NAV_ITEMS, CameraFeed(), CameraFeedProps, DetachButton(), DetachButtonProps, HologramControls(), Orb() (+61 more)

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

### Community 46 - "Community 46"
Cohesion: 0.13
Nodes (11): create_hologram_manager(), discover_devices(), HologramStateManager, =============================================================  Controlador Pytho, Cierra la conexión TCP limpiamente., Escanea la red local buscando hologramas MISSYOU en el puerto 50200.      Útil c, Puente thread-safe entre los estados de la IA y los clips del holograma.      La, Arranca el hilo de control y deja el holograma en idle. No-op si está deshabilit (+3 more)

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
Cohesion: 0.11
Nodes (27): Hologram, QUICK_COMMANDS, OLLAMA_SUGGESTIONS, Props, ProviderConfigCard(), PROVIDERS, useProviders(), apiKeyPlaceholder() (+19 more)

### Community 59 - "Community 59"
Cohesion: 0.18
Nodes (12): get_trigger_mode(), Solicita una escucha puntual (push-to-talk remoto, p. ej. la WebApp)., Cambia en caliente el modo de activación de voz. Devuelve el modo final., Devuelve el modo de activación de voz actual., Lee ENTER de la terminal y solicita una escucha (push-to-talk en CLI)., request_listen(), set_trigger_mode(), _stdin_ptt_reader() (+4 more)

### Community 60 - "Community 60"
Cohesion: 0.25
Nodes (7): Configuración de IA — Contrato de proveedor y modelo, Cómo se elige el backend (`select_backend`), Endpoints relacionados, Endurecimiento de seguridad (Fase D.1), Interfaz de Ajustes, Proveedores soportados, Pruebas

### Community 61 - "Community 61"
Cohesion: 0.50
Nodes (4): pause_hologram(), Attempt to terminate any running TTS or audio players on Linux., Pause hologram activity: stop speaking, listening and seeing., stop_all_tts_processes()

### Community 62 - "Community 62"
Cohesion: 0.24
Nodes (11): _coerce(), load_unev_info(), Fuente única y editable de la información institucional de UNEV.  Antes, los dat, Normaliza ``data`` a la forma canónica, rellenando faltantes con el respaldo., Devuelve una lista de errores (vacía = válido) para mostrar al operador., Carga el contenido desde el JSON autoritativo; respaldo en código si falla., Recarga desde disco (tras una edición) y actualiza la caché., Valida, escribe atómicamente el JSON autoritativo y recarga la caché.      Lanza (+3 more)

### Community 65 - "Community 65"
Cohesion: 0.40
Nodes (4): anyOf, description, $schema, title

### Community 71 - "Community 71"
Cohesion: 0.50
Nodes (3): Expanding the ESLint configuration, React Compiler, React + TypeScript + Vite

## Knowledge Gaps
- **244 isolated node(s):** `name`, `private`, `version`, `type`, `dev` (+239 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **12 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `YoloPersonDetector` connect `Community 1` to `Community 3`, `Community 5`, `Community 7`, `Community 45`, `Community 16`, `Community 23`, `Community 24`, `Community 31`?**
  _High betweenness centrality (0.039) - this node is a cross-community bridge._
- **Why does `HologramFanController` connect `Community 6` to `Community 8`, `Community 46`, `Community 16`, `Community 17`, `Community 59`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **Why does `_env()` connect `Community 7` to `Community 0`, `Community 1`, `Community 5`, `Community 23`, `Community 24`, `Community 27`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `HologramFanController` (e.g. with `FastAPI` and `BoundingBoxModel`) actually correct?**
  _`HologramFanController` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `YoloPersonDetector` (e.g. with `Camera` and `FaceAnalyzer`) actually correct?**
  _`YoloPersonDetector` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `WhisperListener` (e.g. with `FastAPI` and `BoundingBoxModel`) actually correct?**
  _`WhisperListener` has 11 INFERRED edges - model-reasoned connections that need verification._
- **What connects `UNEV Hologram — Main entry point.  Regla de Oro A: Todas las rutas usan pathlib.`, `Attempt to terminate any running TTS or audio players on Linux.`, `Pause hologram activity: stop speaking, listening and seeing.` to the rest of the system?**
  _409 weakly-connected nodes found - possible documentation gaps or missing edges._