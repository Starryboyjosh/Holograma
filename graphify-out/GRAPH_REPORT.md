# Graph Report - Holograma  (2026-06-24)

## Corpus Check
- 100 files · ~109,171 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1027 nodes · 1728 edges · 79 communities (66 shown, 13 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 56 edges (avg confidence: 0.61)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f6bf8ab9`
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
- [[_COMMUNITY_Community 66|Community 66]]
- [[_COMMUNITY_Community 69|Community 69]]
- [[_COMMUNITY_Community 71|Community 71]]
- [[_COMMUNITY_Community 78|Community 78]]
- [[_COMMUNITY_Community 79|Community 79]]
- [[_COMMUNITY_Community 83|Community 83]]
- [[_COMMUNITY_Community 84|Community 84]]
- [[_COMMUNITY_Community 90|Community 90]]
- [[_COMMUNITY_Community 109|Community 109]]

## God Nodes (most connected - your core abstractions)
1. `HologramFanController` - 32 edges
2. `HologramStateManager` - 27 edges
3. `_env()` - 26 edges
4. `YoloPersonDetector` - 26 edges
5. `WhisperListener` - 23 edges
6. `_is_quiet()` - 22 edges
7. `stream_llm_response()` - 18 edges
8. `Camera` - 18 edges
9. `voice_loop()` - 17 edges
10. `compilerOptions` - 17 edges

## Surprising Connections (you probably didn't know these)
- `get_piper_command_args()` --calls--> `Path`  [INFERRED]
  call.py → skills/unev_content.py
- `get_piper_model_path()` --calls--> `Path`  [INFERRED]
  call.py → skills/unev_content.py
- `get_piper_sample_rate()` --calls--> `Path`  [INFERRED]
  call.py → skills/unev_content.py
- `get_powershell_command()` --calls--> `Path`  [INFERRED]
  call.py → skills/unev_content.py
- `play_wav_with_windows()` --calls--> `Path`  [INFERRED]
  call.py → skills/unev_content.py

## Import Cycles
- 1-file cycle: `frontend/src-tauri/src/lib.rs -> frontend/src-tauri/src/lib.rs`
- 1-file cycle: `main.py -> main.py`

## Communities (79 total, 13 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.08
Nodes (57): ask_ai(), _build_camera_context(), _is_greeting(), _is_visual_question(), _build_messages(), _candidate_backends(), _chat_with_backend(), _chat_with_claude_native() (+49 more)

### Community 1 - "Community 1"
Cohesion: 0.13
Nodes (12): Load custom classes from training_metadata.json and open_vocabulary.txt., Combine custom classes and vocabulary into a single YOLOE text prompt., Detect custom objects using YOLOE text prompts from training data., Return a list of person detections in *frame*.          Each detection is a dict, Return person and custom object detections plus optional safe face count., Detect people using YOLOe26 via the Ultralytics library.      Parameters     ---, Return the most recent annotated frame as JPEG bytes (or None)., Return True if ultralytics and OpenCV are importable. (+4 more)

### Community 2 - "Community 2"
Cohesion: 0.12
Nodes (18): get_powershell_command(), is_wsl(), play_wav_file(), play_wav_with_windows(), Return True when running inside Windows Subsystem for Linux., Return a PowerShell executable path on Windows or WSL if available., Run a PowerShell script and return True when it succeeds., Play a WAV file with Windows' built-in SoundPlayer. (+10 more)

### Community 3 - "Community 3"
Cohesion: 0.41
Nodes (11): check_audio_devices(), check_dependencies(), check_environment(), check_import(), fail(), main(), ok(), test_camera() (+3 more)

### Community 4 - "Community 4"
Cohesion: 0.13
Nodes (18): get_unev_content(), Contenido institucional de UNEV (fuente única editable)., get_program_info(), get_university_context(), route_local_skill(), get_unev_info(), Contenido vigente (cacheado). Llamado por las skills en cada respuesta., get_admission_info() (+10 more)

### Community 5 - "Community 5"
Cohesion: 0.10
Nodes (30): _camera_detection_callback(), chat_to_voice(), clean_for_tts(), get_help_text(), get_latest_camera_jpeg(), handle_command(), main(), UNEV Hologram — Main entry point.  Regla de Oro A: Todas las rutas usan pathlib. (+22 more)

### Community 6 - "Community 6"
Cohesion: 0.09
Nodes (15): HologramFanController, Envía exactamente 3 bytes al dispositivo.         El manual especifica: un solo, Enciende e inicia la rotación del holograma. [RUN], Detiene la rotación y apaga el holograma. [STOP], Pausa la reproducción del video. [Pause], Reanuda la reproducción del video., Activa el loop del archivo que está reproduciéndose actualmente., Avanza al siguiente archivo en la playlist. [▶|] (+7 more)

### Community 7 - "Community 7"
Cohesion: 0.10
Nodes (4): FakeFan, test_configured_manager_applies_ai_state_clips(), test_configured_manager_uses_custom_clip_map(), wait_for_event()

### Community 8 - "Community 8"
Cohesion: 0.16
Nodes (16): clamp_text(), Utilidades de seguridad para Holograma UNEV.  Funciones puras (sin red, sin esta, Aplica :func:`redact_secrets` a una colección (útil para listas de logs)., Sanea texto no confiable: elimina caracteres de control y trunca a ``max_len``., redact_iter(), _coerce(), load_unev_info(), Fuente única y editable de la información institucional de UNEV.  Antes, los dat (+8 more)

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
Cohesion: 0.14
Nodes (8): Camera, Release the camera resource., Return True if the camera is currently open., Capture one frame and save it to *output_path*.          Parameters         ----, Return True if OpenCV is importable., Cross-platform wrapper around OpenCV VideoCapture.      Supports both live camer, Open the camera or video source., Read a single frame.  Returns the frame or None on failure.

### Community 16 - "Community 16"
Cohesion: 0.21
Nodes (7): get_voices(), Path, Resuelve un nombre corto a la ruta de un .onnx incluido (0.4.x).          Ej.: `, Bloquea hasta detectar la palabra clave.          Parameters         ----------, Return True if openwakeword and sounddevice are importable., Detecta una palabra clave en streaming con openWakeWord., WakeWordDetector

### Community 17 - "Community 17"
Cohesion: 0.08
Nodes (37): BaseModel, Detén la detección y libera la cámara (apagar la cámara = liberarla).      Señal, stop_camera_thread(), _atomic_write_text(), BoundingBoxModel, CameraToggle, ConfigUpdate, _get_holo_manager() (+29 more)

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
Nodes (11): HologramStateManager, Cierra la conexión TCP limpiamente., Salta directamente al video número N de la playlist.          Args:, Puente thread-safe entre los estados de la IA y los clips del holograma.      La, True cuando el gestor automático tiene un socket TCP activo., Aplica un destino TCP nuevo y activa el cambio automático de clips., Desconecta el dispositivo y desactiva los reintentos automáticos., Compatibilidad con la API: ejecuta un comando usando la conexión compartida. (+3 more)

### Community 24 - "Community 24"
Cohesion: 0.16
Nodes (12): Speech-to-text listener using Faster-Whisper and sounddevice.  Regla de Oro A: T, get_wakeword_status(), Detector de palabra clave (wake word) con openWakeWord.  Regla de Oro A: Todas l, Return a human-readable status string for the wake-word subsystem., configure_utf8_stdio(), _env_float(), _env_int(), Helper to retrieve float environment variables. (+4 more)

### Community 25 - "Community 25"
Cohesion: 0.24
Nodes (11): configure_vision(), print_header(), Flujo interactivo para configurar el Cerebro (LLM local o Cloud)., Flujo interactivo para configurar los Oídos (Whisper)., Flujo interactivo para la Visión (YOLOv26 + OpenCV)., Ejecuta el asistente interactivo de configuración completo., Imprime el header estilo 'hermes setup'., run_setup() (+3 more)

### Community 26 - "Community 26"
Cohesion: 0.14
Nodes (13): A. Settings UX + wire test buttons  ✅ DONE (this commit)  ← B or D recommended next, B. Cancellation + camera release + per-session events  (touches call.py, higher risk), C. Windows-first sidecar packaging  (cannot finish here; needs Windows runner), D. Security + operator auth, E. De-monkey-patch into typed services  (refactor; INTENTIONALLY DEFERRED), F. Single editable UNEV content source  ✅ DONE (this commit), G. Legacy lint debt  ✅ DONE (this commit), Hard environment constraints (read first) (+5 more)

### Community 27 - "Community 27"
Cohesion: 0.15
Nodes (11): get_piper_sample_rate(), Read Piper sample rate from the model JSON sidecar when available., _looks_like_hallucination(), Load the Faster-Whisper model on first use., Record audio from the default microphone until silence is detected.          Usa, Write a float32 numpy array to a temporary WAV file.          Returns a ``pathli, Transcribe a WAV file and return the text.          Parameters         ---------, Record from the microphone and return the transcribed text.          Returns an (+3 more)

### Community 28 - "Community 28"
Cohesion: 0.20
Nodes (9): Arquitectura del código, Autoría de los clips (condiciona toda la parte visual), Conexión, Endpoints (`main.py`), Holograma físico MISSYOU — integración por TCP, Mapeo estado de la IA → clip (y por qué se hizo configurable), Pendientes / opcional (no hechos a propósito), Reparto de responsabilidades: app HoloMissYou ↔ este controlador (+1 more)

### Community 29 - "Community 29"
Cohesion: 0.13
Nodes (14): anyOf, definitions, Number, Target, Value, description, anyOf, description (+6 more)

### Community 30 - "Community 30"
Cohesion: 0.13
Nodes (14): anyOf, definitions, Number, PermissionEntry, Target, description, anyOf, description (+6 more)

### Community 32 - "Community 32"
Cohesion: 0.05
Nodes (66): AppShell(), NAV_ITEMS, CameraFeed(), CameraFeedProps, DetachButton(), DetachButtonProps, Orb(), OrbProps (+58 more)

### Community 33 - "Community 33"
Cohesion: 0.36
Nodes (3): FaceAnalyzer, Count visible frontal faces using OpenCV's bundled Haar cascade., Return a safe visual summary for a frame.

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
Cohesion: 0.29
Nodes (8): get_trigger_mode(), Cambia en caliente el modo de activación de voz. Devuelve el modo final., Devuelve el modo de activación de voz actual., set_trigger_mode(), Send host-side TTS status updates to the web client., send_tts_status(), websocket_chat_endpoint(), WebSocket

### Community 46 - "Community 46"
Cohesion: 0.33
Nodes (3): Draw person and custom-object boxes on a copy of *frame*., Encode *frame* (with overlay) to JPEG and cache it for streaming., Run a detection loop calling *callback(event, count)* on changes.          Param

### Community 48 - "Community 48"
Cohesion: 0.50
Nodes (4): description, required, type, Capability

### Community 49 - "Community 49"
Cohesion: 0.50
Nodes (4): default, description, type, description

### Community 50 - "Community 50"
Cohesion: 0.29
Nodes (7): create_hologram_manager(), discover_devices(), =============================================================  Controlador Pytho, Escanea la red local buscando hologramas MISSYOU en el puerto 50200.      Útil c, Construye el mapeo estado→índice respetando el orden real de la playlist.      L, Construye un HologramStateManager a partir de variables de entorno.      Variabl, resolve_state_clips()

### Community 51 - "Community 51"
Cohesion: 0.50
Nodes (4): default, description, type, description

### Community 52 - "Community 52"
Cohesion: 0.29
Nodes (6): Aceptación, Empaquetado Windows-first (Fase C) — guía para el próximo agente, Objetivo, Pasos, Restricción dura, `.spec` de partida (validar en el runner)

### Community 53 - "Community 53"
Cohesion: 0.67
Nodes (3): Identifier, description, oneOf

### Community 54 - "Community 54"
Cohesion: 0.67
Nodes (3): Identifier, description, oneOf

### Community 56 - "Community 56"
Cohesion: 0.12
Nodes (26): Hologram, HologramConnection(), OLLAMA_SUGGESTIONS, Props, ProviderConfigCard(), PROVIDERS, useProviders(), apiKeyPlaceholder() (+18 more)

### Community 58 - "Community 58"
Cohesion: 0.40
Nodes (5): Start YOLO person detection in a background daemon thread., start_camera_thread(), FastAPI, lifespan(), Ciclo de vida de la aplicación (reemplaza @app.on_event, deprecado).      Arranc

### Community 59 - "Community 59"
Cohesion: 0.50
Nodes (4): description, required, type, Capability

### Community 60 - "Community 60"
Cohesion: 0.25
Nodes (7): Configuración de IA — Contrato de proveedor y modelo, Cómo se elige el backend (`select_backend`), Endpoints relacionados, Endurecimiento de seguridad (Fase D.1), Interfaz de Ajustes, Proveedores soportados, Pruebas

### Community 61 - "Community 61"
Cohesion: 0.50
Nodes (4): pause_hologram(), Attempt to terminate any running TTS or audio players on Linux., Pause hologram activity: stop speaking, listening and seeing., stop_all_tts_processes()

### Community 62 - "Community 62"
Cohesion: 0.25
Nodes (4): Test del mecanismo de parada/liberación de la cámara (Fase B).  No requiere cáma, get_vision_status(), YOLOv8/v11 person detector for the UNEV hologram.  Regla de Oro A: Todas las rut, Return a human-readable status string for the vision subsystem.

### Community 63 - "Community 63"
Cohesion: 0.50
Nodes (4): Solicita una escucha puntual (push-to-talk remoto, p. ej. la WebApp)., Lee ENTER de la terminal y solicita una escucha (push-to-talk en CLI)., request_listen(), _stdin_ptt_reader()

### Community 66 - "Community 66"
Cohesion: 0.67
Nodes (3): PermissionEntry, anyOf, description

### Community 69 - "Community 69"
Cohesion: 0.67
Nodes (3): Value, anyOf, description

### Community 71 - "Community 71"
Cohesion: 0.50
Nodes (3): Expanding the ESLint configuration, React Compiler, React + TypeScript + Vite

## Knowledge Gaps
- **255 isolated node(s):** `name`, `private`, `version`, `type`, `dev` (+250 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **13 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `YoloPersonDetector` connect `Community 1` to `Community 64`, `Community 33`, `Community 65`, `Community 3`, `Community 5`, `Community 46`, `Community 15`, `Community 58`, `Community 62`?**
  _High betweenness centrality (0.037) - this node is a cross-community bridge._
- **Why does `Camera` connect `Community 15` to `Community 64`, `Community 1`, `Community 65`, `Community 3`, `Community 46`, `Community 24`, `Community 62`?**
  _High betweenness centrality (0.022) - this node is a cross-community bridge._
- **Why does `HologramFanController` connect `Community 6` to `Community 45`, `Community 17`, `Community 50`, `Community 23`, `Community 58`?**
  _High betweenness centrality (0.020) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `HologramFanController` (e.g. with `FastAPI` and `BoundingBoxModel`) actually correct?**
  _`HologramFanController` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `HologramStateManager` (e.g. with `FastAPI` and `BoundingBoxModel`) actually correct?**
  _`HologramStateManager` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `YoloPersonDetector` (e.g. with `Camera` and `FaceAnalyzer`) actually correct?**
  _`YoloPersonDetector` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `WhisperListener` (e.g. with `FastAPI` and `BoundingBoxModel`) actually correct?**
  _`WhisperListener` has 11 INFERRED edges - model-reasoned connections that need verification._