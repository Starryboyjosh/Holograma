# Graph Report - Holograma  (2026-07-10)

## Corpus Check
- 111 files · ~112,452 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1304 nodes · 2228 edges · 90 communities (75 shown, 15 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 157 edges (avg confidence: 0.69)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `447351d6`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Frontend Package Stack|Frontend Package Stack]]
- [[_COMMUNITY_CLI Voice Call Loop|CLI Voice Call Loop]]
- [[_COMMUNITY_Provider Config Tests|Provider Config Tests]]
- [[_COMMUNITY_Assistant Orb UI|Assistant Orb UI]]
- [[_COMMUNITY_FastAPI Main Server|FastAPI Main Server]]
- [[_COMMUNITY_STT Wakeword Listener|STT Wakeword Listener]]
- [[_COMMUNITY_WebSocket Connection Manager|WebSocket Connection Manager]]
- [[_COMMUNITY_Android Launcher Icons|Android Launcher Icons]]
- [[_COMMUNITY_WSL Audio Playback|WSL Audio Playback]]
- [[_COMMUNITY_Hologram Fan Controller|Hologram Fan Controller]]
- [[_COMMUNITY_Frontend Content Screens|Frontend Content Screens]]
- [[_COMMUNITY_LLM Backend Providers|LLM Backend Providers]]
- [[_COMMUNITY_Hologram Controller Tests|Hologram Controller Tests]]
- [[_COMMUNITY_YOLO Person Detector|YOLO Person Detector]]
- [[_COMMUNITY_Camera Capture Core|Camera Capture Core]]
- [[_COMMUNITY_Hologram State Clips|Hologram State Clips]]
- [[_COMMUNITY_TS App Compiler Config|TS App Compiler Config]]
- [[_COMMUNITY_iOS App Icons|iOS App Icons]]
- [[_COMMUNITY_LLM Unify Tests|LLM Unify Tests]]
- [[_COMMUNITY_YOLO Frame Analysis|YOLO Frame Analysis]]
- [[_COMMUNITY_Piper TTS Synthesis|Piper TTS Synthesis]]
- [[_COMMUNITY_Provider Config UI|Provider Config UI]]
- [[_COMMUNITY_Hologram State Manager|Hologram State Manager]]
- [[_COMMUNITY_Custom Object Interval Tests|Custom Object Interval Tests]]
- [[_COMMUNITY_TS Node Compiler Config|TS Node Compiler Config]]
- [[_COMMUNITY_Desktop Store Icons|Desktop Store Icons]]
- [[_COMMUNITY_UNEV Content Source|UNEV Content Source]]
- [[_COMMUNITY_Conversation Service Tests|Conversation Service Tests]]
- [[_COMMUNITY_Tauri App Config|Tauri App Config]]
- [[_COMMUNITY_Person Presence Tests|Person Presence Tests]]
- [[_COMMUNITY_Tauri Rust Backend|Tauri Rust Backend]]
- [[_COMMUNITY_Provider Config Core|Provider Config Core]]
- [[_COMMUNITY_Honduras Skill|Honduras Skill]]
- [[_COMMUNITY_Whisper STT Core|Whisper STT Core]]
- [[_COMMUNITY_AI Reply Generation|AI Reply Generation]]
- [[_COMMUNITY_Conversation Service|Conversation Service]]
- [[_COMMUNITY_YOLO Predict Opts Tests|YOLO Predict Opts Tests]]
- [[_COMMUNITY_Project Architecture|Project Architecture]]
- [[_COMMUNITY_Web Brand Asset SVGs|Web Brand Asset SVGs]]
- [[_COMMUNITY_Camera Feed Hooks|Camera Feed Hooks]]
- [[_COMMUNITY_Vision Service Layer|Vision Service Layer]]
- [[_COMMUNITY_Windows Packaging Plan|Windows Packaging Plan]]
- [[_COMMUNITY_LLM Service Layer|LLM Service Layer]]
- [[_COMMUNITY_LLM Backend Tests|LLM Backend Tests]]
- [[_COMMUNITY_Skills Router University|Skills Router University]]
- [[_COMMUNITY_Session Config Context|Session Config Context]]
- [[_COMMUNITY_Diagnose Hologram Script|Diagnose Hologram Script]]
- [[_COMMUNITY_Theme Toast Context|Theme Toast Context]]
- [[_COMMUNITY_Setup Hologram Wizard|Setup Hologram Wizard]]
- [[_COMMUNITY_Shutdown Disconnect Paths|Shutdown Disconnect Paths]]
- [[_COMMUNITY_AppShell Navigation|AppShell Navigation]]
- [[_COMMUNITY_Detachable Widget Windows|Detachable Widget Windows]]
- [[_COMMUNITY_UNEV Brand Manual|UNEV Brand Manual]]
- [[_COMMUNITY_Three-Panel Hologram Preview|Three-Panel Hologram Preview]]
- [[_COMMUNITY_Ollama Ready Cache Tests|Ollama Ready Cache Tests]]
- [[_COMMUNITY_Security Utility Tests|Security Utility Tests]]
- [[_COMMUNITY_Voice Trigger Modes|Voice Trigger Modes]]
- [[_COMMUNITY_UNEV Content Tests|UNEV Content Tests]]
- [[_COMMUNITY_Graphify Agent Pipeline|Graphify Agent Pipeline]]
- [[_COMMUNITY_Marketing Hero Asset|Marketing Hero Asset]]
- [[_COMMUNITY_Face Analyzer|Face Analyzer]]
- [[_COMMUNITY_Hologram Device Discovery|Hologram Device Discovery]]
- [[_COMMUNITY_Camera Feed Gate Tests|Camera Feed Gate Tests]]
- [[_COMMUNITY_Camera Stop Tests|Camera Stop Tests]]
- [[_COMMUNITY_Backend Selection Order|Backend Selection Order]]
- [[_COMMUNITY_Presence Manager|Presence Manager]]
- [[_COMMUNITY_App Layer Architecture|App Layer Architecture]]
- [[_COMMUNITY_Tauri Capabilities|Tauri Capabilities]]
- [[_COMMUNITY_Security Redaction Utils|Security Redaction Utils]]
- [[_COMMUNITY_Config API Security|Config API Security]]
- [[_COMMUNITY_LLM Test Provider API|LLM Test Provider API]]
- [[_COMMUNITY_Provider Model Contract|Provider Model Contract]]
- [[_COMMUNITY_Hotwords Cache Tests|Hotwords Cache Tests]]
- [[_COMMUNITY_TS Project References|TS Project References]]
- [[_COMMUNITY_Holograma Launch Script|Holograma Launch Script]]
- [[_COMMUNITY_Piper Wrapper Script|Piper Wrapper Script]]
- [[_COMMUNITY_App Package Init|App Package Init]]
- [[_COMMUNITY_Run Web Script|Run Web Script]]
- [[_COMMUNITY_Services Package Init|Services Package Init]]
- [[_COMMUNITY_Skills Package Init|Skills Package Init]]
- [[_COMMUNITY_STT Package Init|STT Package Init]]
- [[_COMMUNITY_Vision Package Init|Vision Package Init]]
- [[_COMMUNITY_Holograma UNEV Project|Holograma UNEV Project]]
- [[_COMMUNITY_Chat Command Help|Chat Command Help]]

## God Nodes (most connected - your core abstractions)
1. `YoloPersonDetector` - 32 edges
2. `ConnectionManager` - 30 edges
3. `HologramStateManager` - 27 edges
4. `WhisperListener` - 26 edges
5. `_env()` - 26 edges
6. `ConversationService` - 25 edges
7. `CameraContextProvider` - 25 edges
8. `Holograma UNEV` - 24 edges
9. `_is_quiet()` - 23 edges
10. `LLMService` - 20 edges

## Surprising Connections (you probably didn't know these)
- `Holograma UNEV` --conceptually_related_to--> `Instituto Universitario de Educación Virtual UNEV`  [INFERRED]
  README.md → docs/Manual de Marca - UNEV 1920x1080 - 2025.pdf
- `skills/ local router UNEV Honduras` --conceptually_related_to--> `Instituto Universitario de Educación Virtual UNEV`  [INFERRED]
  README.md → docs/Manual de Marca - UNEV 1920x1080 - 2025.pdf
- `FastAPI + uvicorn API stack` --conceptually_related_to--> `main.py FastAPI + WebSocket`  [INFERRED]
  requirements.txt → README.md
- `Proposed app/ web orchestration layer` --semantically_similar_to--> `app/ services layer`  [INFERRED] [semantically similar]
  ANALISIS_Y_PLAN_DE_MEJORA.md → README.md
- `AI states idle listening speaking thinking` --semantically_similar_to--> `AI state machine maps to playlist clips`  [INFERRED] [semantically similar]
  docs/HOLOGRAM.md → docs/Holograma_MISSYOU_Referencia_IA.pdf

## Import Cycles
- 1-file cycle: `main.py -> main.py`
- 1-file cycle: `frontend/src-tauri/src/lib.rs -> frontend/src-tauri/src/lib.rs`

## Hyperedges (group relationships)
- **Holograma UNEV multimodal stack** — readme_holograma_unev, readme_llm_backend, readme_vision_yolo, readme_stt, readme_hologram_controller, readme_frontend [EXTRACTED 1.00]
- **AI state to hologram clip TCP control flow** — docs_hologram_ai_states, docs_hologram_state_manager, docs_hologram_fan_controller, docs_hologram_play_file_command, docs_holograma_missyou_referencia_ia_one_cmd_packet [EXTRACTED 1.00]
- **Scout Build Worker model pipeline** — claude_scout_agent, claude_build_stage, claude_worker_agent, agents_graphify [EXTRACTED 1.00]
- **Desktop icon size ladder sharing identical bolt mark** — icons_icon_primary_app_icon, icons_32x32_tray_icon, icons_64x64_window_icon, icons_128x128_standard_icon, icons_128x128_2x_retina_icon [INFERRED 0.95]
- **Windows Store square logo size matrix** — icons_storelogo_ms_store_logo, icons_square30x30logo_small_tile, icons_square44x44logo_app_list, icons_square71x71logo_medium_tile, icons_square89x89logo_scaled_tile, icons_square107x107logo_scaled_tile, icons_square142x142logo_large_tile, icons_square150x150logo_medium_tile, icons_square284x284logo_large_tile, icons_square310x310logo_splash_tile [INFERRED 0.95]
- **Unified brand identity across all packaging assets** — icons_brand_lightning_bolt_mark, icons_brand_purple_blue_gradient, icons_tauri_packaging_icon_set, icons_icon_primary_app_icon [INFERRED 0.95]
- **Android launcher density ladder** — mipmap_mdpi_ic_launcher_density_bucket_mdpi, mipmap_hdpi_ic_launcher_density_bucket_hdpi, mipmap_xhdpi_ic_launcher_density_bucket_xhdpi, mipmap_xxhdpi_ic_launcher_density_bucket_xxhdpi, mipmap_xxxhdpi_ic_launcher_density_bucket_xxxhdpi [EXTRACTED 1.00]
- **Android launcher role trio (square/round/foreground)** — mipmap_mdpi_ic_launcher_standard_launcher_role, mipmap_mdpi_ic_launcher_round_round_launcher_role, mipmap_mdpi_ic_launcher_foreground_adaptive_foreground_role, mipmap_xxxhdpi_ic_launcher_foreground_adaptive_icon_packaging [EXTRACTED 1.00]
- **Shared bolt brand across mipmap launcher assets** — mipmap_xxxhdpi_ic_launcher_foreground_lightning_bolt_mark, mipmap_mdpi_ic_launcher_image, mipmap_xxxhdpi_ic_launcher_image, mipmap_xxxhdpi_ic_launcher_round_image, mipmap_xxxhdpi_ic_launcher_foreground_image [EXTRACTED 1.00]
- **Large iOS AppIcons sharing identical bolt mark (vision-extracted)** — ios_appicon_512_2x_image, ios_appicon_83_5x83_5_2x_image, ios_appicon_76x76_2x_image, ios_appicon_60x60_3x_image, ios_appicon_512_2x_lightning_bolt_mark [EXTRACTED 1.00]
- **iOS AppIcon platform role matrix (App Store / iPhone / iPad / iPad Pro)** — ios_appicon_512_2x_app_store_master_role, ios_appicon_60x60_3x_iphone_homescreen_role, ios_appicon_76x76_2x_ipad_homescreen_role, ios_appicon_83_5x83_5_2x_ipad_pro_settings_role [EXTRACTED 1.00]
- **Full iOS AppIcon density catalog (large + small packaging set)** — ios_appicon_512_2x_ios_appicon_asset_catalog, ios_appicon_small_density_set_packaging, ios_appicon_20x20_notification_slot, ios_appicon_29x29_settings_slot, ios_appicon_40x40_spotlight_slot, ios_appicon_60x60_2x_iphone_retina_slot, ios_appicon_76x76_1x_ipad_baseline_slot, ios_appicon_512_2x_retina_scale_factor [EXTRACTED 1.00]

## Communities (90 total, 15 thin omitted)

### Community 0 - "Frontend Package Stack"
Cohesion: 0.05
Nodes (38): dependencies, react, react-dom, react-router-dom, tailwindcss, @tailwindcss/vite, @tauri-apps/api, devDependencies (+30 more)

### Community 1 - "CLI Voice Call Loop"
Cohesion: 0.10
Nodes (21): _camera_detection_callback(), camera_feed_subscribe(), camera_feed_unsubscribe(), get_latest_camera_jpeg(), pause_hologram(), UNEV Hologram — Main entry point.  Regla de Oro A: Todas las rutas usan pathlib., Lee ENTER de la terminal y solicita una escucha (push-to-talk en CLI)., Attempt to terminate any running TTS or audio players on Linux. (+13 more)

### Community 2 - "Provider Config Tests"
Cohesion: 0.06
Nodes (15): Tests del contrato de proveedor/modelo (provider_config).  Cubren la lógica que, El proveedor 'custom_openai' lee key/modelo de las variables OPENAI_COMPAT_*., Regresión: proveedor explícito 'ollama' nunca cae a la nube por una key vieja., Con varias keys, el orden es determinista (AUTODETECT_ORDER), no el del dict., custom_openai necesita key, modelo y base-url; sin base-url no se encola., Si el operador elige openai, no se cambia en silencio a otro proveedor., El modelo de la interfaz (LLM_MODEL) aplica también a OpenAI/NVIDIA., Ollama no debe usar un modelo de la nube si solo está LLM_MODEL. (+7 more)

### Community 3 - "Assistant Orb UI"
Cohesion: 0.15
Nodes (18): Orb(), OrbProps, useToast(), useChatSocket(), AssistantScreen(), highlighted(), SUGGESTIONS, requestServerListen (+10 more)

### Community 4 - "FastAPI Main Server"
Cohesion: 0.08
Nodes (29): BaseModel, Detén la detección y libera la cámara (apagar la cámara = liberarla).      Señal, stop_camera_thread(), HologramStateManager, Puente thread-safe entre los estados de la IA y los clips del holograma.      La, True cuando el gestor automático tiene un socket TCP activo., BoundingBoxModel, CameraToggle (+21 more)

### Community 5 - "STT Wakeword Listener"
Cohesion: 0.09
Nodes (24): _hotword_priority(), _hotwords_sources_signature(), _looks_like_hallucination(), _normalize_hotword(), Speech-to-text listener using Faster-Whisper and sounddevice.  Regla de Oro A: T, Limpia un término de hotword (paréntesis rotos, puntuación, basura)., Orden: siglas y nombres cortos primero; frases largas al final., Return True if *text* is empty or a known Whisper silence-hallucination. (+16 more)

### Community 6 - "WebSocket Connection Manager"
Cohesion: 0.09
Nodes (16): AbstractEventLoop, ConnectionManager, Emisor único de eventos hacia los clientes WebSocket.  El `main.py` actual mezcl, Lo único que el manager necesita de un WebSocket (FastAPI lo cumple)., Registro de conexiones + difusión async, seguro ante sockets caídos., Envía *message* a todas las conexiones; descarta las que fallen.          Se tom, Captura el event loop del servidor para emitir desde hilos no-async.          Se, Difunde *message* desde un hilo (voz/cámara) hacia el event loop.          Los p (+8 more)

### Community 7 - "Android Launcher Icons"
Cohesion: 0.11
Nodes (27): mipmap-hdpi density, ic_launcher_foreground.png (hdpi), ic_launcher.png (hdpi), ic_launcher_round.png (hdpi), mipmap-mdpi density, Adaptive icon foreground role, ic_launcher_foreground.png (mdpi), ic_launcher.png (mdpi) (+19 more)

### Community 8 - "WSL Audio Playback"
Cohesion: 0.17
Nodes (12): get_powershell_command(), is_wsl(), Return True when running inside Windows Subsystem for Linux., Return a PowerShell executable path on Windows or WSL if available., Run a PowerShell script and return True when it succeeds., Use Windows built-in speech synthesis when Piper is unavailable., Use lightweight Linux TTS fallbacks when Piper is unavailable., Reproduce un fragmento con el TTS nativo del SO (fallback sin Piper). (+4 more)

### Community 9 - "Hologram Fan Controller"
Cohesion: 0.05
Nodes (24): Cierra y olvida todas las conexiones (apagado ordenado del servidor).          E, HologramFanController, Cierra la conexión TCP limpiamente., Envía exactamente 3 bytes al dispositivo.         El manual especifica: un solo, Enciende e inicia la rotación del holograma. [RUN], Detiene la rotación y apaga el holograma. [STOP], Pausa la reproducción del video. [Pause], Reanuda la reproducción del video. (+16 more)

### Community 10 - "Frontend Content Screens"
Cohesion: 0.16
Nodes (17): Hologram, HologramConnection(), SaveResult, UnevProgram, useUnevContent(), ContentScreen(), FIELD_LABELS, Card() (+9 more)

### Community 11 - "LLM Backend Providers"
Cohesion: 0.07
Nodes (59): _build_camera_context(), _build_messages(), _candidate_backends(), _chat_with_backend(), _chat_with_claude_native(), _chat_with_ollama(), _chat_with_openai_compatible(), generate_reply() (+51 more)

### Community 12 - "Hologram Controller Tests"
Cohesion: 0.07
Nodes (11): create_hologram_manager(), discover_devices(), =============================================================  Controlador Pytho, Escanea la red local buscando hologramas MISSYOU en el puerto 50200.      Útil c, Construye el mapeo estado→índice respetando el orden real de la playlist.      L, Construye un HologramStateManager a partir de variables de entorno.      Variabl, resolve_state_clips(), FakeFan (+3 more)

### Community 13 - "YOLO Person Detector"
Cohesion: 0.20
Nodes (5): Draw person and custom-object boxes on a copy of *frame*., Encode *frame* (with overlay) to JPEG and cache it for streaming., ¿Hay al menos un cliente viendo el feed anotado?, Run a detection loop calling *callback(event, count)* on changes.          Param, Duerme hasta *seconds* o hasta ``stop()`` (no bloquea el apagado).

### Community 14 - "Camera Capture Core"
Cohesion: 0.09
Nodes (11): Camera, Cross-platform OpenCV camera wrapper.  Regla de Oro A: Todas las rutas usan path, Release the camera resource., Return True if the camera is currently open., Capture one frame and save it to *output_path*.          Parameters         ----, Return True if OpenCV is importable., Cross-platform wrapper around OpenCV VideoCapture.      Supports both live camer, Open the camera or video source. (+3 more)

### Community 15 - "Hologram State Clips"
Cohesion: 0.13
Nodes (19): AI states idle listening speaking thinking, Configurable HOLOGRAM_CLIP_* mapping, create_hologram_manager, Fail-soft hologram never blocks AI, HologramFanController, Device is pre-rendered file player not live 3D, HoloMissYou app playlist ownership, MP4/JPG black background 5:12 clips (+11 more)

### Community 16 - "TS App Compiler Config"
Cohesion: 0.10
Nodes (19): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, jsx, lib, module, moduleDetection, moduleResolution (+11 more)

### Community 17 - "iOS App Icons"
Cohesion: 0.17
Nodes (16): AppIcon 20pt notification/settings slot, AppIcon 29pt Settings slot, AppIcon 40pt Spotlight slot, App Store / 1024 master AppIcon role, iOS AppIcon asset-catalog packaging, Purple–blue lightning bolt brand mark, Purple-to-blue brand gradient, iOS @1x/@2x/@3x retina scale factors (+8 more)

### Community 18 - "LLM Unify Tests"
Cohesion: 0.11
Nodes (12): _inject_fake_call(), Unificación de la ruta de LLM (Fases 1 y 2 del plan de mejora).  Cubre tres arre, primario -> otros proveedores con key -> ollama (si responde) -> local_only., Un primario explícito sin key (p. ej. claude_native) sigue siendo el primer inte, Una respuesta en inglés debe entregarse, no convertirse en un error., Evita el import perezoso real de ``call`` (efectos globales: chdir, Qt…)., `_candidate_backends` debe ejecutarse en un hilo distinto al del loop.      El l, test_backend_selection_runs_off_event_loop() (+4 more)

### Community 19 - "YOLO Frame Analysis"
Cohesion: 0.08
Nodes (20): Argumentos comunes de inferencia local (latencia / recursos)., Opcional: reduce el frame grande antes de YOLO (sin apagar la cámara)., Load the YOLO model.  Downloads weights automatically on first run., Load the model if it hasn't been loaded yet., Load custom classes from training_metadata.json and open_vocabulary.txt., Combine custom classes and vocabulary into a single YOLOE text prompt., Detect custom objects using YOLOE text prompts from training data., Normaliza `box.xyxy[0]` de Ultralytics (tensor) o de fakes de test (list). (+12 more)

### Community 20 - "Piper TTS Synthesis"
Cohesion: 0.11
Nodes (19): get_piper_command_args(), get_piper_model_path(), get_piper_sample_rate(), _piper_available(), _piper_synth_to_wav(), Return the command used to run Piper if it is available., Return the Piper voice model to use, preferring Spanish voices., Read Piper sample rate from the model JSON sidecar when available. (+11 more)

### Community 21 - "Provider Config UI"
Cohesion: 0.25
Nodes (11): OLLAMA_SUGGESTIONS, Props, ProviderConfigCard(), PROVIDERS, apiKeyPlaceholder(), buildLlmConfigPayload(), buildLlmTestInput(), LlmConfigForm (+3 more)

### Community 22 - "Hologram State Manager"
Cohesion: 0.10
Nodes (17): Configuración de IA — Contrato de proveedor y modelo, Cómo se elige el backend (`select_backend`), Endpoints relacionados, Endurecimiento de seguridad (Fase D.1), Interfaz de Ajustes, Límite de tokens y robustez de la respuesta, Proveedores soportados, Pruebas (+9 more)

### Community 23 - "Custom Object Interval Tests"
Cohesion: 0.16
Nodes (12): _FakeBox, _FakeModel, _FakeResult, _FakeXY, _make_detector(), La inferencia de objetos personalizados (YOLOE) corre en su propio intervalo.  `, Modelo falso: cuenta cuántas veces se le pide inferencia., test_first_call_runs_inference() (+4 more)

### Community 24 - "TS Node Compiler Config"
Cohesion: 0.11
Nodes (17): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, lib, module, moduleDetection, moduleResolution, noEmit (+9 more)

### Community 25 - "Desktop Store Icons"
Cohesion: 0.33
Nodes (18): 128x128@2x retina/high-DPI icon, 128x128 standard app icon, 32x32 desktop/tray icon variant, 64x64 window icon variant, Lightning bolt / stylized Z brand mark, Purple-to-blue diagonal gradient identity, Primary Tauri app icon (master PNG), Square 107x107 logo (scaled tile) (+10 more)

### Community 26 - "UNEV Content Source"
Cohesion: 0.05
Nodes (36): get_unev_content(), Contenido institucional de UNEV (fuente única editable)., _build_search_index(), get_program_info(), get_university_context(), Pre-calcula índices de texto normalizados en el arranque del servidor/script., route_local_skill(), _coerce() (+28 more)

### Community 27 - "Conversation Service Tests"
Cohesion: 0.14
Nodes (18): ContextBuilder, ConversationService, CameraContextProvider, Registra el último análisis de la cámara (lo llamará VisionService)., FakeLLM, Capa de servicios de Fase 3 (`app/`).  Blinda los contratos del refactor sin nec, Con stream TTS, la primera cláusula se habla antes de text_done., Con `camera_context` inyectado, NO se construye contexto desde `call`. (+10 more)

### Community 28 - "Tauri App Config"
Cohesion: 0.11
Nodes (17): app, security, windows, build, beforeBuildCommand, beforeDevCommand, devUrl, frontendDist (+9 more)

### Community 29 - "Person Presence Tests"
Cohesion: 0.15
Nodes (17): _analysis(), _drive(), Máquina de estados de presencia: parpadeos vs. ausencia real.  Estos tests blind, Un grupo (>3) dispara group_detected una sola vez mientras se mantiene., Un único cuadro con persona (falso positivo de YOLO) NO debe saludar.      Con u, Una presencia sostenida supera el anti-rebote y confirma la entrada una vez., El anti-rebote de entrada también aplica a grupos: confirma una sola vez., Análisis sintético con *count* personas (forma que devuelve analyze_frame). (+9 more)

### Community 30 - "Tauri Rust Backend"
Cohesion: 0.21
Nodes (16): Child, Duration, Mutex, Option, PathBuf, backend_ready(), BackendState, free_port() (+8 more)

### Community 31 - "Provider Config Core"
Cohesion: 0.25
Nodes (8): get_piper_install_hint(), play_wav_file(), play_wav_with_windows(), Return a short installation hint for the current platform., Play a WAV file with Windows' built-in SoundPlayer., Play a WAV file on Windows, Linux, or macOS using available system tools., Use Piper TTS and play the generated WAV file on the current OS., speak_with_piper()

### Community 32 - "Honduras Skill"
Cohesion: 0.14
Nodes (20): ask_ai(), chat_to_voice(), get_help_text(), handle_command(), main(), Text input loop: keyboard → LLM → TTS., Bloquea hasta que toque escuchar, según el modo dinámico actual.      Devuelve `, Voice input loop: microphone → Whisper → LLM → TTS (Regla B: sounddevice). (+12 more)

### Community 33 - "Whisper STT Core"
Cohesion: 0.13
Nodes (12): Cambia en caliente el modo de activación de voz. Devuelve el modo final., set_trigger_mode(), Load the Faster-Whisper model on first use., Record audio from the default microphone until silence is detected.          Usa, Write a float32 numpy array to a temporary WAV file.          Returns a ``pathli, Hotwords según el contexto del kiosco (cacheadas por mtime de data/).          F, Prompt de contexto para Whisper (local ``initial_prompt`` y Groq ``prompt``)., Transcribe a WAV file using the Groq API with whisper-large-v3-turbo.          G (+4 more)

### Community 34 - "AI Reply Generation"
Cohesion: 0.25
Nodes (7): Cómo funciona, Desarrollo, Empaquetado del backend (PENDIENTE — paso posterior), Holograma UNEV — Shell de escritorio (Tauri v2), Requisitos, Variables de entorno útiles, Widgets desprendibles

### Community 35 - "Conversation Service"
Cohesion: 0.19
Nodes (9): Protocol, _Camera, _Connection, _LLM, _pop_ready_speech(), Orquestador de un turno de conversación (el corazón de la Fase 3).  Recibe un pr, Procesa un turno completo y devuelve el texto generado ("" si falló)., Extrae cláusulas/oraciones listas para TTS desde un buffer de stream.      Misma (+1 more)

### Community 36 - "YOLO Predict Opts Tests"
Cohesion: 0.17
Nodes (8): _FakeBox, _FakeBoxes, _FakeModel, _FakeResult, Opciones de inferencia YOLO local (imgsz / device / prepare_frame).  No cargan u, La sala vacía no debe saltarse la inferencia local., test_detect_persons_passes_imgsz_and_conf(), test_empty_room_still_runs_predict()

### Community 37 - "Project Architecture"
Cohesion: 0.20
Nodes (11): Linux ↔ Windows compatibility rules, Local vs cloud multimodal modes, stt/ Faster-Whisper + sounddevice, vision/ OpenCV + YOLO, requirements.txt dependency stack, FastAPI + uvicorn API stack, faster-whisper STT, openwakeword optional wake word (+3 more)

### Community 38 - "Web Brand Asset SVGs"
Cohesion: 0.14
Nodes (12): React cyan #00D8FF, React framework identity, Iconify logos React asset, React logo, Vite purple #9135ff, Dark-mode adaptive parentheses, Vite logo, Vite build-tool identity (+4 more)

### Community 39 - "Camera Feed Hooks"
Cohesion: 0.29
Nodes (11): CameraFeed(), CameraFeedProps, useBackendUrl(), UseChatSocketOptions, apiUrl(), backendBase(), detectBase(), mediaUrl() (+3 more)

### Community 40 - "Vision Service Layer"
Cohesion: 0.29
Nodes (6): Aceptación, Empaquetado Windows-first (Fase C) — guía para el próximo agente, Objetivo, Pasos, Restricción dura, `.spec` de partida (validar en el runner)

### Community 41 - "Windows Packaging Plan"
Cohesion: 0.14
Nodes (15): Tauri externalBin holograma-backend, packaging/holograma.spec, Kill process tree on shutdown, PyInstaller backend sidecar, Pin Python 3.11 or 3.12, spawn_backend production sidecar path, Windows-first packaging Phase C, frontend SPA root index.html (+7 more)

### Community 42 - "LLM Service Layer"
Cohesion: 0.22
Nodes (6): FastAPI, lifespan(), Ciclo de vida de la aplicación (reemplaza @app.on_event, deprecado).      Arranc, LLMService, Servicio de LLM: envuelve la **única** ruta async de generación.  `llm_backend.s, StreamFn

### Community 43 - "LLM Backend Tests"
Cohesion: 0.15
Nodes (4): Exception, Tests de la integración de llm_backend con el contrato de proveedor.  No hacen l, test_humanize_probe_error_maps_common_cases(), test_humanize_probe_error_redacts_leaked_key_in_generic_branch()

### Community 44 - "Skills Router University"
Cohesion: 0.40
Nodes (4): Cómo hacerlo cuando se retome, Holograma UNEV — Trabajo pendiente, Por qué está diferido, Reorganización de carpetas (diferido)

### Community 45 - "Session Config Context"
Cohesion: 0.27
Nodes (10): CameraState, SessionCtx, SessionProvider(), SessionValue, ChatSocket, useConfig(), useHologram(), UseHologramOptions (+2 more)

### Community 46 - "Diagnose Hologram Script"
Cohesion: 0.41
Nodes (11): check_audio_devices(), check_dependencies(), check_environment(), check_import(), fail(), main(), ok(), test_camera() (+3 more)

### Community 47 - "Theme Toast Context"
Cohesion: 0.21
Nodes (8): AppearanceTheme, resolveDark(), ThemeCtx, ThemeProvider(), ThemeValue, ShowToast, ToastCtx, ToastProvider()

### Community 48 - "Setup Hologram Wizard"
Cohesion: 0.24
Nodes (11): configure_vision(), print_header(), Flujo interactivo para configurar el Cerebro (LLM local o Cloud)., Flujo interactivo para configurar los Oídos (Whisper)., Flujo interactivo para la Visión (YOLOv26 + OpenCV)., Ejecuta el asistente interactivo de configuración completo., Imprime el header estilo 'hermes setup'., run_setup() (+3 more)

### Community 49 - "Shutdown Disconnect Paths"
Cohesion: 0.50
Nodes (4): clean_for_tts(), Remove characters that can sound awkward when read by a TTS engine., Divide el texto en fragmentos listos para TTS.     El primero usa cláusulas para, _split_into_chunks()

### Community 50 - "AppShell Navigation"
Cohesion: 0.25
Nodes (8): AppShell(), NAV_ITEMS, useSession(), useTheme(), useProviders(), SettingsScreen(), TeachingScreen(), BoundingBox

### Community 51 - "Detachable Widget Windows"
Cohesion: 0.27
Nodes (9): DetachButton(), DetachButtonProps, isTauriRuntime(), openWidgetWindow(), WIDGET_META, widgetHash(), WidgetMeta, WidgetName (+1 more)

### Community 52 - "UNEV Brand Manual"
Cohesion: 0.18
Nodes (11): Brand colors #ff7208 #2e3a66, Constructivist connectivist educational model, Founder Raúl Peña Moreno, UNEV logo orange blue V emphasis, UNEV manifesto democratize virtual education, UNEV mission, Custom logo type + Montserrat secondary, UNEV brand identity manual 2025 (+3 more)

### Community 53 - "Three-Panel Hologram Preview"
Cohesion: 0.25
Nodes (10): Black background, Color-coded panel borders, Orange circle (center subject), PANEL 1, PANEL 2, PANEL 3, Three-panel hologram test preview (prueba), Three-panel hologram layout (+2 more)

### Community 54 - "Ollama Ready Cache Tests"
Cohesion: 0.33
Nodes (10): _make_tags_counter(), Caché con TTL de `_ollama_ready()`.  Antes, cada mensaje sondeaba /api/tags 2–4, Sustituye `_ollama_tags` por uno que cuenta llamadas y reporta el modelo listo., El servidor responde, pero el modelo configurado no está instalado., _reset_cache(), test_force_bypasses_cache(), test_model_absent_returns_false(), test_probe_failure_returns_false() (+2 more)

### Community 56 - "Voice Trigger Modes"
Cohesion: 0.33
Nodes (6): get_trigger_mode(), Solicita una escucha puntual (push-to-talk remoto, p. ej. la WebApp)., Devuelve el modo de activación de voz actual., request_listen(), websocket_chat_endpoint(), WebSocket

### Community 57 - "UNEV Content Tests"
Cohesion: 0.50
Nodes (3): Expanding the ESLint configuration, React Compiler, React + TypeScript + Vite

### Community 58 - "Graphify Agent Pipeline"
Cohesion: 0.22
Nodes (9): graphify, graphify explain, graphify path, graphify query, graphify update, Build stage (Opus implementation), Model pipeline division of labor, Scout agent (+1 more)

### Community 59 - "Marketing Hero Asset"
Cohesion: 0.33
Nodes (8): Black background, Holographic aesthetic, Isometric projection, Lower purple platform, Marketing hero asset, Purple brand accent, Stacked dual-layer composition, Upper silver platform

### Community 60 - "Face Analyzer"
Cohesion: 0.36
Nodes (3): FaceAnalyzer, Count visible frontal faces using OpenCV's bundled Haar cascade., Return a safe visual summary for a frame.

### Community 62 - "Camera Feed Gate Tests"
Cohesion: 0.32
Nodes (5): _count_stores(), Gating del feed MJPEG: el detector solo codifica JPEG si alguien mira.  Codifica, Corre run_continuous unos cuadros y cuenta cuántas veces guardó un JPEG., test_run_continuous_encodes_with_subscriber(), test_run_continuous_skips_encode_without_subscribers()

### Community 64 - "Backend Selection Order"
Cohesion: 0.33
Nodes (7): Backend select off event loop, Supported LLM providers, local_only skills-only backend, Ollama local provider, Ollama not overridden by stale cloud keys, select_backend selection order, skills/ local router UNEV Honduras

### Community 66 - "App Layer Architecture"
Cohesion: 0.40
Nodes (6): Proposed app/ web orchestration layer, Proposed core/ motor subsystems, Deferred folder reorganization app/core, Hologram REST endpoints, app/ services layer, main.py FastAPI + WebSocket

### Community 67 - "Tauri Capabilities"
Cohesion: 0.33
Nodes (5): description, identifier, permissions, $schema, windows

### Community 69 - "Security Redaction Utils"
Cohesion: 0.14
Nodes (17): _atomic_write_text(), ConfigUpdate, Valida y guarda el contenido de UNEV; recarga la fuente en caliente.      Devuel, Escritura atómica: archivo temporal + os.replace.      Evita config.json / .env, train_image(), train_vocabulary(), TrainImagePayload, update_config() (+9 more)

### Community 71 - "Config API Security"
Cohesion: 0.40
Nodes (5): GET/POST /api/config, clamp_text, redact_secrets, security.py / auth_token.py, Healthcheck GET /api/config

### Community 74 - "LLM Test Provider API"
Cohesion: 0.50
Nodes (4): POST /api/llm/test, GET /api/providers, providerForm.ts form mapping, Settings ProviderConfigCard UI

### Community 75 - "Provider Model Contract"
Cohesion: 0.14
Nodes (17): Fases 0–4 complete on main, LLM_MAX_TOKENS centralized limit, AI provider and model contract, MISSYOU holographic fan TCP integration, call.py CLI, Comandos de chat, Configuración esencial, Ejecutar (+9 more)

### Community 76 - "Hotwords Cache Tests"
Cohesion: 0.29
Nodes (10): _fresh_listener(), Hotwords STT: caché por mtime, acotado y alineado al contexto UNEV/Honduras., Vocabulario del kiosco + UNEV + Honduras siempre presente., La ruta Groq (config actual) debe inyectar prompt de contexto., test_groq_receives_language_and_prompt(), test_hotwords_bounded(), test_hotwords_cached_on_second_call(), test_hotwords_include_context_domain() (+2 more)

## Knowledge Gaps
- **226 isolated node(s):** `AbstractEventLoop`, `StreamFn`, `ContextBuilder`, `name`, `private` (+221 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **15 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `YoloPersonDetector` connect `YOLO Frame Analysis` to `Honduras Skill`, `CLI Voice Call Loop`, `STT Wakeword Listener`, `YOLO Person Detector`, `Diagnose Hologram Script`, `Camera Capture Core`, `Face Analyzer`?**
  _High betweenness centrality (0.046) - this node is a cross-community bridge._
- **Why does `HologramFanController` connect `Hologram Fan Controller` to `Hologram Controller Tests`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **Why does `_env()` connect `STT Wakeword Listener` to `Honduras Skill`, `Whisper STT Core`, `LLM Backend Providers`, `YOLO Person Detector`, `Camera Capture Core`, `YOLO Frame Analysis`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `YoloPersonDetector` (e.g. with `Camera` and `FaceAnalyzer`) actually correct?**
  _`YoloPersonDetector` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `ConnectionManager` (e.g. with `FastAPI` and `BoundingBoxModel`) actually correct?**
  _`ConnectionManager` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `HologramStateManager` (e.g. with `FastAPI` and `BoundingBoxModel`) actually correct?**
  _`HologramStateManager` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `WhisperListener` (e.g. with `FastAPI` and `BoundingBoxModel`) actually correct?**
  _`WhisperListener` has 11 INFERRED edges - model-reasoned connections that need verification._