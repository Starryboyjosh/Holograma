# Graph Report - Holograma  (2026-07-23)

## Corpus Check
- 116 files · ~122,537 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1451 nodes · 2531 edges · 123 communities (89 shown, 34 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 173 edges (avg confidence: 0.69)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b6596470`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- UNEV Skills Content
- Frontend NPM Dependencies
- Provider Config Tests
- Call Voice Camera Core
- YOLO Person Detector
- Frontend Orb Chat UI
- WebSocket Connection Manager
- Android Launcher Icons
- iOS App Icon Assets
- LLM Backend Chat Paths
- Hologram Fan Controller
- FastAPI Main Routes
- Hologram UI UNEV Content
- LLM Unify Tests
- Provider Config Resolution
- Setup Wizard Scripts
- Hologram Controller Tests
- TS App Compiler Options
- Ollama Backend Probes
- Provider Config Card UI
- Hologram State Manager
- STT Hotwords Cache
- Custom Object Interval Tests
- LLM ask_ai Pipeline
- TS Node Compiler Options
- Desktop Brand Icon Set
- Conversation Service Tests
- Tauri App Config
- Person Presence Tests
- Tauri Rust Backend
- API Models Payloads
- App Services Layer
- Frontend Session Context
- Config and Utils
- Camera Feed Component
- Appearance Skill
- Vision Training Pipeline
- Event Mode Skill
- Whisper STT Models
- Honduras Skill Data
- Security Auth Token
- Frontend Theme Toast
- Detached Windows UI
- University Skill
- Hotwords Skill
- Presence Skill
- Graphify Agent Pipeline
- Frontend Hooks Lib
- UI Form Components
- Local Skills Router
- Voice Loop Orchestration
- package.json
- Backend URL Hooks
- Training Metadata API
- Listener Lifecycle
- Config Env Loading
- Voice Loop Status
- Piper TTS Discovery
- Piper Playback Paths
- .detect_person_once
- Detector Overlay Feed
- Graphify Workflow Docs
- Marketing Hero Asset
- Camera Context Builder
- MISSYOU Fan Protocol
- LLM Test Service
- Voice Trigger WebSocket
- Hologram Discovery Factory
- STT Record Transcribe
- Face Analyzer OpenCV
- Camera Context Prompt
- LLM Provider Selection
- README.md
- Tauri Capabilities
- iOS Icon 20@1x Brand
- iOS Icon 20@3x Lightning
- iOS Icon Crystal Motif
- Config Security Redaction
- iOS Icon 20@2x Purple
- iOS Icon Hexagon Teal
- iOS Icon Triangle Mark
- iOS Icon 29@3x Bolt
- iOS Icon 40@2x Bolt
- iOS Icon 60@2x Home
- Providers Settings API
- LLM Token Limit Contract
- iOS Icon 20@2x Brand
- iOS Icon Blank Placeholder
- iOS Icon 40@2x Lightning
- iOS Icon iPad 76pt
- Detect Person Once
- Count Persons Once
- TS Project References
- Holograma Launch Script
- Piper Wrapper Script
- App Package Init
- @types/node
- Run Web Script
- Services Package Init
- Skills Package Init
- Tauri Build Script
- STT Package Init
- Vision Package Init
- Project Package Metadata
- Chat Command Help
- Frontend Test Setup
- vite
- @vitejs/plugin-react
- get_stt_status
- apply_config_to_env
- graphify explain
- graphify path
- graphify query
- graphify update
- README.md
- eslint
- @testing-library/user-event

## God Nodes (most connected - your core abstractions)
1. `YoloPersonDetector` - 32 edges
2. `ConnectionManager` - 30 edges
3. `HologramStateManager` - 30 edges
4. `WhisperListener` - 29 edges
5. `_env()` - 27 edges
6. `HologramFanController` - 24 edges
7. `_is_quiet()` - 24 edges
8. `ConversationService` - 23 edges
9. `CameraContextProvider` - 23 edges
10. `route_local_skill()` - 23 edges

## Surprising Connections (you probably didn't know these)
- `skills/ local router UNEV Honduras` --conceptually_related_to--> `Instituto Universitario de Educación Virtual UNEV`  [INFERRED]
  README.md → docs/Manual de Marca - UNEV 1920x1080 - 2025.pdf
- `AI states idle listening speaking thinking` --semantically_similar_to--> `AI state machine maps to playlist clips`  [INFERRED] [semantically similar]
  docs/HOLOGRAM.md → docs/Holograma_MISSYOU_Referencia_IA.pdf
- `MP4/JPG black background 5:12 clips` --semantically_similar_to--> `Reproducible media MP4 JPG specs`  [INFERRED] [semantically similar]
  docs/HOLOGRAM.md → docs/Holograma_MISSYOU_Referencia_IA.pdf
- `spawn_backend production sidecar path` --semantically_similar_to--> `spawn_backend python3 main.py`  [INFERRED] [semantically similar]
  docs/PACKAGING.md → frontend/src-tauri/README.md
- `BoundingBoxModel` --uses--> `ConnectionManager`  [INFERRED]
  main.py → app/connection.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **AI state to hologram clip TCP control flow** — docs_hologram_ai_states, docs_hologram_state_manager, docs_hologram_fan_controller, docs_hologram_play_file_command, docs_holograma_missyou_referencia_ia_one_cmd_packet [EXTRACTED 1.00]
- **Windows Store square logo size matrix** — frontend_src_tauri_icons_storelogo_ms_store_logo, frontend_src_tauri_icons_square30x30logo_small_tile, frontend_src_tauri_icons_square44x44logo_app_list, frontend_src_tauri_icons_square71x71logo_medium_tile, frontend_src_tauri_icons_square89x89logo_scaled_tile, frontend_src_tauri_icons_square107x107logo_scaled_tile, frontend_src_tauri_icons_square142x142logo_large_tile, frontend_src_tauri_icons_square150x150logo_medium_tile, frontend_src_tauri_icons_square284x284logo_large_tile, frontend_src_tauri_icons_square310x310logo_splash_tile [INFERRED 0.95]
- **Android launcher role trio (square/round/foreground)** — frontend_src_tauri_icons_android_mipmap_mdpi_ic_launcher_standard_launcher_role, frontend_src_tauri_icons_android_mipmap_mdpi_ic_launcher_round_round_launcher_role, frontend_src_tauri_icons_android_mipmap_mdpi_ic_launcher_foreground_adaptive_foreground_role, frontend_src_tauri_icons_android_mipmap_xxxhdpi_ic_launcher_foreground_adaptive_icon_packaging [EXTRACTED 1.00]
- **Android launcher density ladder** — frontend_src_tauri_icons_android_mipmap_mdpi_ic_launcher_density_bucket_mdpi, frontend_src_tauri_icons_android_mipmap_hdpi_ic_launcher_density_bucket_hdpi, frontend_src_tauri_icons_android_mipmap_xhdpi_ic_launcher_density_bucket_xhdpi, frontend_src_tauri_icons_android_mipmap_xxhdpi_ic_launcher_density_bucket_xxhdpi, frontend_src_tauri_icons_android_mipmap_xxxhdpi_ic_launcher_density_bucket_xxxhdpi [EXTRACTED 1.00]
- **Shared bolt brand across mipmap launcher assets** — frontend_src_tauri_icons_android_mipmap_xxxhdpi_ic_launcher_foreground_lightning_bolt_mark, frontend_src_tauri_icons_android_mipmap_mdpi_ic_launcher_image, frontend_src_tauri_icons_android_mipmap_xxxhdpi_ic_launcher_image, frontend_src_tauri_icons_android_mipmap_xxxhdpi_ic_launcher_round_image, frontend_src_tauri_icons_android_mipmap_xxxhdpi_ic_launcher_foreground_image [EXTRACTED 1.00]
- **Desktop icon size ladder sharing identical bolt mark** — frontend_src_tauri_icons_icon_primary_app_icon, frontend_src_tauri_icons_32x32_tray_icon, frontend_src_tauri_icons_64x64_window_icon, frontend_src_tauri_icons_128x128_standard_icon, frontend_src_tauri_icons_128x128_2x_retina_icon [INFERRED 0.95]
- **Unified brand identity across all packaging assets** — icons_brand_lightning_bolt_mark, icons_brand_purple_blue_gradient, icons_tauri_packaging_icon_set, frontend_src_tauri_icons_icon_primary_app_icon [INFERRED 0.95]
- **Large iOS AppIcons sharing identical bolt mark (vision-extracted)** — frontend_src_tauri_icons_ios_appicon_512_2x_image, frontend_src_tauri_icons_ios_appicon_83_5x83_5_2x_image, frontend_src_tauri_icons_ios_appicon_76x76_2x_image, frontend_src_tauri_icons_ios_appicon_60x60_3x_image, frontend_src_tauri_icons_ios_appicon_512_2x_lightning_bolt_mark [EXTRACTED 1.00]
- **iOS AppIcon platform role matrix (App Store / iPhone / iPad / iPad Pro)** — frontend_src_tauri_icons_ios_appicon_512_2x_app_store_master_role, frontend_src_tauri_icons_ios_appicon_60x60_3x_iphone_homescreen_role, frontend_src_tauri_icons_ios_appicon_76x76_2x_ipad_homescreen_role, frontend_src_tauri_icons_ios_appicon_83_5x83_5_2x_ipad_pro_settings_role [EXTRACTED 1.00]
- **Full iOS AppIcon density catalog (large + small packaging set)** — frontend_src_tauri_icons_ios_appicon_512_2x_ios_appicon_asset_catalog, ios_appicon_small_density_set_packaging, ios_appicon_20x20_notification_slot, ios_appicon_29x29_settings_slot, ios_appicon_40x40_spotlight_slot, ios_appicon_60x60_2x_iphone_retina_slot, ios_appicon_76x76_1x_ipad_baseline_slot, frontend_src_tauri_icons_ios_appicon_512_2x_retina_scale_factor [EXTRACTED 1.00]
- **Holograma iOS Small Brand Mark System** — frontend_src_tauri_icons_ios_appicon_20x20_1x_app_icon, frontend_src_tauri_icons_ios_appicon_20x20_1x_lightning_bolt_mark, frontend_src_tauri_icons_ios_appicon_20x20_1x_purple_blue_gradient, frontend_src_tauri_icons_ios_appicon_20x20_1x_minimal_flat_style [INFERRED 0.85]

## Communities (123 total, 34 thin omitted)

### Community 0 - "UNEV Skills Content"
Cohesion: 0.14
Nodes (21): Hologram, HologramConnection(), Card(), CardProps, SectionTitle(), Field(), Select(), Textarea() (+13 more)

### Community 1 - "Frontend NPM Dependencies"
Cohesion: 0.12
Nodes (17): eslint, @eslint/js, eslint-plugin-react-hooks, devDependencies, eslint, @eslint/js, eslint-plugin-react-hooks, jsdom (+9 more)

### Community 2 - "Provider Config Tests"
Cohesion: 0.05
Nodes (15): Tests del contrato de proveedor/modelo (provider_config).  Cubren la lógica que, Ollama no debe usar un modelo de la nube si solo está LLM_MODEL., Regresión: proveedor explícito 'ollama' nunca cae a la nube por una key vieja., El proveedor 'custom_openai' lee key/modelo de las variables OPENAI_COMPAT_*., Con varias keys, el orden es determinista (AUTODETECT_ORDER), no el del dict., custom_openai necesita key, modelo y base-url; sin base-url no se encola., Si el operador elige openai, no se cambia en silencio a otro proveedor., El modelo de la interfaz (LLM_MODEL) aplica también a OpenAI/NVIDIA. (+7 more)

### Community 3 - "Call Voice Camera Core"
Cohesion: 0.12
Nodes (14): camera_feed_subscribe(), camera_feed_unsubscribe(), get_latest_camera_jpeg(), get_piper_install_hint(), UNEV Hologram — Main entry point.  Regla de Oro A: Todas las rutas usan pathlib., Return a short installation hint for the current platform., Return the latest annotated camera frame (JPEG bytes) or None., Registra un cliente del feed de video (activa la codificación JPEG).      El det (+6 more)

### Community 4 - "YOLO Person Detector"
Cohesion: 0.11
Nodes (11): Solicita que run_continuous termine y libere la cámara., Duerme hasta *seconds* o hasta ``stop()`` (no bloquea el apagado)., Draw person and custom-object boxes on a copy of *frame*., Encode *frame* (with overlay) to JPEG and cache it for streaming., Return the most recent annotated frame as JPEG bytes (or None)., Registra un cliente del feed MJPEG (activa la codificación JPEG)., Da de baja un cliente del feed MJPEG (el contador nunca baja de 0).          Al, ¿Hay al menos un cliente viendo el feed anotado? (+3 more)

### Community 5 - "Frontend Orb Chat UI"
Cohesion: 0.16
Nodes (19): Orb(), OrbProps, useToast(), ChatSocket, useChatSocket(), UseChatSocketOptions, AssistantScreen(), highlighted() (+11 more)

### Community 6 - "WebSocket Connection Manager"
Cohesion: 0.20
Nodes (5): Protocol, Lo único que el manager necesita de un WebSocket (FastAPI lo cumple)., Envía *message* a todas las conexiones; descarta las que fallen.          Se tom, Difunde *message* desde un hilo (voz/cámara) hacia el event loop.          Los p, WebSocketLike

### Community 7 - "Android Launcher Icons"
Cohesion: 0.11
Nodes (27): mipmap-hdpi density, ic_launcher_foreground.png (hdpi), ic_launcher.png (hdpi), ic_launcher_round.png (hdpi), mipmap-mdpi density, Adaptive icon foreground role, ic_launcher_foreground.png (mdpi), ic_launcher.png (mdpi) (+19 more)

### Community 8 - "iOS App Icon Assets"
Cohesion: 0.12
Nodes (21): Energy / power branding theme, Violet-to-cyan diagonal gradient, Purple–blue lightning bolt mark, iOS AppIcon 40pt@3x Spotlight slot, Transparent background, App Store / 1024 master AppIcon role, iOS AppIcon asset-catalog packaging, Purple–blue lightning bolt brand mark (+13 more)

### Community 9 - "LLM Backend Chat Paths"
Cohesion: 0.06
Nodes (68): _build_messages(), _candidate_backends(), _chat_with_backend(), _chat_with_claude_native(), _chat_with_ollama(), _chat_with_openai_compatible(), _cot_log_enabled(), _cot_print() (+60 more)

### Community 10 - "Hologram Fan Controller"
Cohesion: 0.11
Nodes (15): HologramFanController, Envía exactamente 3 bytes al dispositivo.         El manual especifica: un solo, Enciende e inicia la rotación del holograma. [RUN], Pausa la reproducción del video. [Pause], Reanuda la reproducción del video., Activa el loop del archivo que está reproduciéndose actualmente., Avanza al siguiente archivo en la playlist. [▶|], Regresa al archivo anterior en la playlist. [|◀] (+7 more)

### Community 11 - "FastAPI Main Routes"
Cohesion: 0.06
Nodes (34): Servicio de LLM: envuelve la **única** ruta async de generación.  `llm_backend.s, get_trigger_mode(), Cambia en caliente el modo de activación de voz. Devuelve el modo final., Devuelve el modo de activación de voz actual., Detén la detección y libera la cámara (apagar la cámara = liberarla).      Señal, set_trigger_mode(), stop_camera_thread(), FastAPI (+26 more)

### Community 12 - "Hologram UI UNEV Content"
Cohesion: 0.09
Nodes (22): app, security, windows, build, beforeBuildCommand, beforeDevCommand, devUrl, frontendDist (+14 more)

### Community 13 - "LLM Unify Tests"
Cohesion: 0.09
Nodes (12): _inject_fake_call(), Unificación de la ruta de LLM (Fases 1 y 2 del plan de mejora).  Cubre tres arre, Evita el import perezoso real de ``call`` (efectos globales: chdir, Qt…)., `_candidate_backends` debe ejecutarse en un hilo distinto al del loop.      El l, primario -> otros proveedores con key -> ollama (si responde) -> local_only., Un primario explícito sin key (p. ej. claude_native) sigue siendo el primer inte, Una respuesta en inglés debe entregarse, no convertirse en un error., test_backend_selection_runs_off_event_loop() (+4 more)

### Community 14 - "Provider Config Resolution"
Cohesion: 0.11
Nodes (11): generate_token(), is_path_privileged(), Token de capacidad (opt-in) para proteger los endpoints privilegiados.  El backe, Genera un token de capacidad aleatorio y url-safe., Compara tokens en tiempo constante. Sin ``expected``, la auth está apagada., ¿La petición modifica estado en una ruta protegida?, Decisión final de autorización para una petición.      Pasa si: la auth está apa, request_authorized() (+3 more)

### Community 15 - "Setup Wizard Scripts"
Cohesion: 0.17
Nodes (18): update_config(), configure_vision(), print_header(), Flujo interactivo para configurar el Cerebro (LLM local o Cloud)., Flujo interactivo para configurar los Oídos (Whisper)., Flujo interactivo para la Visión (YOLOv26 + OpenCV)., Ejecuta el asistente interactivo de configuración completo., Imprime el header estilo 'hermes setup'. (+10 more)

### Community 17 - "TS App Compiler Options"
Cohesion: 0.07
Nodes (26): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, jsx, lib, module, moduleDetection, moduleResolution (+18 more)

### Community 18 - "Ollama Backend Probes"
Cohesion: 0.09
Nodes (25): _hotword_priority(), _hotwords_sources_signature(), _looks_like_hallucination(), _normalize_hotword(), Speech-to-text listener using Faster-Whisper and sounddevice.  Regla de Oro A: T, Limpia un término de hotword (paréntesis rotos, puntuación, basura)., Orden: siglas y nombres cortos primero; frases largas al final., Return True if *text* is empty or a known Whisper silence-hallucination. (+17 more)

### Community 19 - "Provider Config Card UI"
Cohesion: 0.31
Nodes (12): OLLAMA_FALLBACK_SUGGESTIONS, Props, ProviderConfigCard(), Harness(), PROVIDERS, apiKeyPlaceholder(), buildLlmTestInput(), LlmConfigForm (+4 more)

### Community 20 - "Hologram State Manager"
Cohesion: 0.19
Nodes (9): _Camera, _Connection, _LLM, _pop_ready_speech(), Protocol, Orquestador de un turno de conversación (el corazón de la Fase 3).  Recibe un pr, Procesa un turno completo y devuelve el texto generado ("" si falló)., Extrae cláusulas/oraciones listas para TTS desde un buffer de stream.      Misma (+1 more)

### Community 21 - "STT Hotwords Cache"
Cohesion: 0.19
Nodes (14): _fresh_listener(), Hotwords STT: caché por mtime, acotado y alineado al contexto UNEV/Honduras., Groq exige prompt ≤896; tildes no deben empujar el conteo del API., faster-whisper debe recibir language=es, task=transcribe y hotwords., La ruta Groq (config actual) debe inyectar prompt de contexto + español., Vocabulario del kiosco + UNEV + Honduras siempre presente., test_groq_receives_language_and_prompt(), test_hotwords_bounded() (+6 more)

### Community 22 - "Custom Object Interval Tests"
Cohesion: 0.16
Nodes (12): _FakeBox, _FakeModel, _FakeResult, _FakeXY, _make_detector(), La inferencia de objetos personalizados (YOLOE) corre en su propio intervalo.  `, Modelo falso: cuenta cuántas veces se le pide inferencia., test_first_call_runs_inference() (+4 more)

### Community 23 - "LLM ask_ai Pipeline"
Cohesion: 0.06
Nodes (45): get_unev_content(), Contenido institucional de UNEV (fuente única editable)., _build_search_index(), get_admission_info(), get_approval_info(), get_location_info(), get_proceres_info(), get_program_info() (+37 more)

### Community 24 - "TS Node Compiler Options"
Cohesion: 0.10
Nodes (20): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, lib, module, moduleDetection, moduleResolution, noEmit (+12 more)

### Community 25 - "Desktop Brand Icon Set"
Cohesion: 0.33
Nodes (18): 128x128@2x retina/high-DPI icon, 128x128 standard app icon, 32x32 desktop/tray icon variant, 64x64 window icon variant, Primary Tauri app icon (master PNG), Square 107x107 logo (scaled tile), Square 142x142 logo (large tile), Square 150x150 logo (medium start tile) (+10 more)

### Community 26 - "Conversation Service Tests"
Cohesion: 0.10
Nodes (26): ConnectionManager, Emisor único de eventos hacia los clientes WebSocket.  El `main.py` actual mezcl, Registro de conexiones + difusión async, seguro ante sockets caídos., Cierra y olvida todas las conexiones (apagado ordenado del servidor).          E, ConversationService, FakeLLM, FakeWS, Capa de servicios de Fase 3 (`app/`).  Blinda los contratos del refactor sin nec (+18 more)

### Community 27 - "Tauri App Config"
Cohesion: 0.32
Nodes (10): CameraFeed(), CameraFeedProps, useBackendUrl(), apiUrl(), backendBase(), detectBase(), mediaUrl(), resolveBackendUrl() (+2 more)

### Community 28 - "Person Presence Tests"
Cohesion: 0.15
Nodes (17): _analysis(), _drive(), Máquina de estados de presencia: parpadeos vs. ausencia real.  Estos tests blind, Un grupo (>3) dispara group_detected una sola vez mientras se mantiene., Un único cuadro con persona (falso positivo de YOLO) NO debe saludar.      Con u, Una presencia sostenida supera el anti-rebote y confirma la entrada una vez., El anti-rebote de entrada también aplica a grupos: confirma una sola vez., Análisis sintético con *count* personas (forma que devuelve analyze_frame). (+9 more)

### Community 29 - "Tauri Rust Backend"
Cohesion: 0.21
Nodes (16): Child, Duration, backend_ready(), BackendState, free_port(), get_backend_url(), kill_backend(), project_root() (+8 more)

### Community 30 - "API Models Payloads"
Cohesion: 0.15
Nodes (13): dependencies, react, react-dom, react-router-dom, tailwindcss, @tailwindcss/vite, @tauri-apps/api, react (+5 more)

### Community 31 - "App Services Layer"
Cohesion: 0.23
Nodes (7): AppShell(), NAV_ITEMS, useSession(), useTheme(), TeachingScreen(), BoundingBox, CameraWidget()

### Community 32 - "Frontend Session Context"
Cohesion: 0.17
Nodes (8): _FakeBox, _FakeBoxes, _FakeModel, _FakeResult, Opciones de inferencia YOLO local (imgsz / device / prepare_frame).  No cargan u, La sala vacía no debe saltarse la inferencia local., test_detect_persons_passes_imgsz_and_conf(), test_empty_room_still_runs_predict()

### Community 33 - "Config and Utils"
Cohesion: 0.13
Nodes (8): Camera, Release the camera resource., Return True if the camera is currently open., Capture one frame and save it to *output_path*.          Parameters         ----, Return True if OpenCV is importable., Cross-platform wrapper around OpenCV VideoCapture.      Supports both live camer, Open the camera or video source., Read a single frame.  Returns the frame or None on failure.

### Community 34 - "Camera Feed Component"
Cohesion: 0.14
Nodes (12): Holograma / Vite-style purple brand mark, Brand purple #863bff, SVG vector favicon, Shared angular mark geometry with Vite, React cyan #00D8FF, React framework identity, Iconify logos React asset, React logo (+4 more)

### Community 35 - "Appearance Skill"
Cohesion: 0.41
Nodes (11): check_audio_devices(), check_dependencies(), check_environment(), check_import(), fail(), main(), ok(), test_camera() (+3 more)

### Community 36 - "Vision Training Pipeline"
Cohesion: 0.15
Nodes (12): description, identifier, permissions, $schema, windows, core:default, core:webview:allow-create-webview-window, core:window:allow-close (+4 more)

### Community 37 - "Event Mode Skill"
Cohesion: 0.11
Nodes (15): _compute_scale_back(), Argumentos comunes de inferencia local (latencia / recursos)., Opcional: reduce el frame grande antes de YOLO (sin apagar la cámara)., Load the YOLO model.  Downloads weights automatically on first run., Load the model if it hasn't been loaded yet., Load custom classes from training_metadata.json and open_vocabulary.txt., Combine custom classes and vocabulary into a single YOLOE text prompt., Detect custom objects using YOLOE text prompts from training data. (+7 more)

### Community 38 - "Whisper STT Models"
Cohesion: 0.12
Nodes (4): Exception, Tests de la integración de llm_backend con el contrato de proveedor.  No hacen l, test_humanize_probe_error_maps_common_cases(), test_humanize_probe_error_redacts_leaked_key_in_generic_branch()

### Community 39 - "Honduras Skill Data"
Cohesion: 0.26
Nodes (9): CameraState, SessionCtx, SessionProvider(), SessionValue, useConfig(), useHologram(), UseHologramOptions, provider() (+1 more)

### Community 40 - "Security Auth Token"
Cohesion: 0.23
Nodes (9): AppearanceTheme, initialAppearance(), resolveDark(), ThemeCtx, ThemeProvider(), ThemeValue, ShowToast, ToastCtx (+1 more)

### Community 41 - "Frontend Theme Toast"
Cohesion: 0.10
Nodes (23): get_piper_command_args(), get_piper_model_path(), _piper_available(), _piper_synth_to_wav(), play_wav_file(), play_wav_with_windows(), Return the command used to run Piper if it is available., Return the Piper voice model to use, preferring Spanish voices. (+15 more)

### Community 42 - "Detached Windows UI"
Cohesion: 0.17
Nodes (12): get_powershell_command(), is_wsl(), Return True when running inside Windows Subsystem for Linux., Return a PowerShell executable path on Windows or WSL if available., Run a PowerShell script and return True when it succeeds., Use Windows built-in speech synthesis when Piper is unavailable., Use lightweight Linux TTS fallbacks when Piper is unavailable., Reproduce un fragmento con el TTS nativo del SO (fallback sin Piper). (+4 more)

### Community 43 - "University Skill"
Cohesion: 0.29
Nodes (9): DetachButton(), DetachButtonProps, isTauriRuntime(), openWidgetWindow(), WIDGET_META, widgetHash(), WidgetMeta, WidgetName (+1 more)

### Community 44 - "Hotwords Skill"
Cohesion: 0.25
Nodes (8): scripts, build, dev, lint, preview, tauri, test, test:watch

### Community 47 - "Frontend Hooks Lib"
Cohesion: 0.22
Nodes (15): ask_ai(), chat_to_voice(), get_help_text(), handle_command(), main(), Text input loop: keyboard → LLM → TTS., Voice input loop: microphone → Whisper → LLM → TTS (Regla B: sounddevice)., Parse flags and run the appropriate loop. (+7 more)

### Community 48 - "UI Form Components"
Cohesion: 0.12
Nodes (22): AI states idle listening speaking thinking, Configurable HOLOGRAM_CLIP_* mapping, create_hologram_manager, Fail-soft hologram never blocks AI, HologramFanController, Device is pre-rendered file player not live 3D, HoloMissYou app playlist ownership, MP4/JPG black background 5:12 clips (+14 more)

### Community 49 - "Local Skills Router"
Cohesion: 0.08
Nodes (29): Hologram REST endpoints, Tauri externalBin holograma-backend, packaging/holograma.spec, Kill process tree on shutdown, PyInstaller backend sidecar, Pin Python 3.11 or 3.12, spawn_backend production sidecar path, Windows-first packaging Phase C (+21 more)

### Community 50 - "Voice Loop Orchestration"
Cohesion: 0.12
Nodes (18): Backend select off event loop, Supported LLM providers, local_only skills-only backend, Ollama local provider, Ollama not overridden by stale cloud keys, select_backend selection order, Brand colors #ff7208 #2e3a66, Constructivist connectivist educational model (+10 more)

### Community 51 - "package.json"
Cohesion: 0.40
Nodes (4): name, private, type, version

### Community 52 - "Backend URL Hooks"
Cohesion: 0.25
Nodes (10): Black background, Color-coded panel borders, Orange circle (center subject), PANEL 1, PANEL 2, PANEL 3, Three-panel hologram test preview (prueba), Three-panel hologram layout (+2 more)

### Community 53 - "Training Metadata API"
Cohesion: 0.15
Nodes (16): _correct_kiosk_stt(), Corrige confusiones frecuentes del STT en el dominio del kiosco UNEV.      Whisp, Record from the microphone and transcribe with Faster-Whisper.      Parameters, Load the Faster-Whisper model on first use., Record audio from the default microphone until silence is detected.          Usa, Write a float32 numpy array to a temporary WAV file.          Returns a ``pathli, Hotwords según el contexto del kiosco (cacheadas por mtime de data/).          F, Corta el prompt al tope, preferiblemente en un espacio (no parte un término). (+8 more)

### Community 54 - "Listener Lifecycle"
Cohesion: 0.33
Nodes (10): _make_tags_counter(), Caché con TTL de `_ollama_ready()`.  Antes, cada mensaje sondeaba /api/tags 2–4, Sustituye `_ollama_tags` por uno que cuenta llamadas y reporta el modelo listo., El servidor responde, pero el modelo configurado no está instalado., _reset_cache(), test_force_bypasses_cache(), test_model_absent_returns_false(), test_probe_failure_returns_false() (+2 more)

### Community 55 - "Config Env Loading"
Cohesion: 0.14
Nodes (19): play_speak(), Valida y guarda el contenido de UNEV; recarga la fuente en caliente.      Devuel, train_image(), train_vocabulary(), update_unev_content(), clamp_text(), Utilidades de seguridad para Holograma UNEV.  Funciones puras (sin red, sin esta, Devuelve ``text`` con cualquier secreto enmascarado.      Enmascara (1) los valo (+11 more)

### Community 56 - "Voice Loop Status"
Cohesion: 0.38
Nodes (5): HologramArrayTester, Envía un clip independiente a cada holograma de un arreglo.      Este flujo es d, main(), parse_assignment(), test_array_tester_sends_a_different_clip_to_each_hologram()

### Community 57 - "Piper TTS Discovery"
Cohesion: 0.50
Nodes (4): pause_hologram(), Attempt to terminate any running TTS or audio players on Linux., Pause hologram activity: stop speaking, listening and seeing., stop_all_tts_processes()

### Community 58 - "Piper Playback Paths"
Cohesion: 0.29
Nodes (7): _camera_detection_callback(), Handle YOLO detection events from the background camera thread., Start YOLO person detection in a background daemon thread., start_camera_thread(), get_greeting(), get_system_prompt(), _has_camera()

### Community 60 - "Detector Overlay Feed"
Cohesion: 0.13
Nodes (7): Cierra la conexión TCP limpiamente., Detiene la rotación y apaga el holograma. [STOP], Conecta cada unidad, reproduce su índice y devuelve el resultado., Cierra las conexiones abiertas sin apagar unidades ya probadas., Desconecta el dispositivo y desactiva los reintentos automáticos., Detiene el hilo, apaga el giro y cierra la conexión limpiamente., Establece la conexión TCP con el holograma.

### Community 61 - "Graphify Workflow Docs"
Cohesion: 0.50
Nodes (4): Build stage (Opus implementation), Model pipeline division of labor, Scout agent, Worker agent

### Community 62 - "Marketing Hero Asset"
Cohesion: 0.33
Nodes (8): Black background, Holographic aesthetic, Isometric projection, Lower purple platform, Marketing hero asset, Purple brand accent, Stacked dual-layer composition, Upper silver platform

### Community 63 - "Camera Context Builder"
Cohesion: 0.33
Nodes (6): _emit_voice_event(), Difunde un evento de voz a la WebApp si hay puente WS (main.py)., Solicita una escucha puntual (push-to-talk remoto, p. ej. la WebApp)., Lee ENTER de la terminal y solicita una escucha (push-to-talk en CLI)., request_listen(), _stdin_ptt_reader()

### Community 65 - "LLM Test Service"
Cohesion: 0.15
Nodes (9): HologramStateManager, Salta directamente al video número N de la playlist.          Args:, Puente thread-safe entre los estados de la IA y los clips del holograma.      La, True cuando el gestor automático tiene un socket TCP activo., Aplica un destino TCP nuevo y activa el cambio automático de clips., Compatibilidad con la API: ejecuta un comando usando la conexión compartida., Arranca el hilo de control y deja el holograma en idle. No-op si está deshabilit, Solicita un cambio de estado del holograma. No bloquea ni lanza excepciones. (+1 more)

### Community 66 - "Voice Trigger WebSocket"
Cohesion: 0.17
Nodes (15): LLMService, CameraContextProvider, Registra el último análisis de la cámara (lo llamará VisionService)., BaseModel, ContextBuilder, BoundingBoxModel, CameraToggle, ConfigUpdate (+7 more)

### Community 67 - "Hologram Discovery Factory"
Cohesion: 0.19
Nodes (13): create_hologram_manager(), discover_devices(), =============================================================  Controlador Pytho, Escanea la red local buscando hologramas MISSYOU en el puerto 50200.      Útil c, Construye el mapeo estado→índice respetando el orden real de la playlist.      L, Construye un HologramStateManager a partir de variables de entorno.      Variabl, resolve_state_clips(), test_configured_manager_applies_ai_state_clips() (+5 more)

### Community 68 - "STT Record Transcribe"
Cohesion: 0.33
Nodes (6): clean_for_tts(), Remove characters that can sound awkward when read by a TTS engine., Divide el texto en fragmentos listos para TTS.     El primero usa cláusulas para, Speak text using Piper when possible, with OS-native fallbacks.     Utiliza segm, speak(), _split_into_chunks()

### Community 69 - "Face Analyzer OpenCV"
Cohesion: 0.36
Nodes (3): FaceAnalyzer, Count visible frontal faces using OpenCV's bundled Haar cascade., Return a safe visual summary for a frame.

### Community 70 - "Camera Context Prompt"
Cohesion: 0.33
Nodes (4): Proveedor del contexto de cámara para el LLM.  `llm_backend.stream_llm_response`, build_camera_context(), Construcción del contexto de cámara para el prompt del LLM.  Módulo neutro (sin, Convierte un análisis de cámara en texto para el prompt del LLM.      Si no hay

### Community 72 - "README.md"
Cohesion: 0.32
Nodes (5): _count_stores(), Gating del feed MJPEG: el detector solo codifica JPEG si alguien mira.  Codifica, Corre run_continuous unos cuadros y cuenta cuántas veces guardó un JPEG., test_run_continuous_encodes_with_subscriber(), test_run_continuous_skips_encode_without_subscribers()

### Community 74 - "iOS Icon 20@1x Brand"
Cohesion: 0.53
Nodes (6): iOS App Icon 20x20@1x, Energy and Power Brand Identity, Lightning Bolt Brand Mark, Minimal Flat Icon Style, iOS 20pt Notification Icon Size, Purple-to-Blue Brand Gradient

### Community 75 - "iOS Icon 20@3x Lightning"
Cohesion: 0.53
Nodes (5): Energy / power branding theme, Purple-blue gradient background, iOS AppIcon 20x20@3x slot, White lightning bolt symbol, Square icon canvas

### Community 76 - "iOS Icon Crystal Motif"
Cohesion: 0.47
Nodes (5): Magenta-violet gradient background, Hologram / crystal visual motif, iOS rounded-square canvas, Tauri iOS icon set member, White geometric polyhedra

### Community 77 - "Config Security Redaction"
Cohesion: 0.40
Nodes (5): GET/POST /api/config, clamp_text, redact_secrets, Healthcheck GET /api/config, security.py / auth_token.py

### Community 78 - "iOS Icon 20@2x Purple"
Cohesion: 0.60
Nodes (5): iOS AppIcon 20x20@2x-1, White lightning bolt symbol, Solid purple/violet background, iOS rounded-square app icon shape, Tauri iOS app icon asset (20pt @2x)

### Community 79 - "iOS Icon Hexagon Teal"
Cohesion: 0.50
Nodes (4): Teal/cyan palette, Hexagon lattice motif, Holograma brand icon style, iOS AppIcon 29pt @1x slot

### Community 80 - "iOS Icon Triangle Mark"
Cohesion: 0.60
Nodes (4): App logo symbol, Solid black background, iOS 29pt @2x app icon, White geometric triangle mark

### Community 81 - "iOS Icon 29@3x Bolt"
Cohesion: 0.50
Nodes (5): AppIcon-29x29@3x, iOS 29pt @3x icon slot, Lightning bolt symbol, Purple-to-blue gradient, Transparent background

### Community 82 - "iOS Icon 40@2x Bolt"
Cohesion: 0.50
Nodes (4): Purple-blue vertical gradient, iOS 40pt @2x app icon, Lightning bolt symbol, White square background

### Community 83 - "iOS Icon 60@2x Home"
Cohesion: 0.50
Nodes (4): iOS home-screen app icon, Lightning bolt symbol, Purple-to-blue gradient fill, Transparent background

### Community 84 - "Providers Settings API"
Cohesion: 0.50
Nodes (4): POST /api/llm/test, GET /api/providers, providerForm.ts form mapping, Settings ProviderConfigCard UI

### Community 85 - "LLM Token Limit Contract"
Cohesion: 0.67
Nodes (4): LLM_MAX_TOKENS centralized limit, AI provider and model contract, llm_backend.py, provider_config.py

### Community 86 - "iOS Icon 20@2x Brand"
Cohesion: 0.83
Nodes (3): App brand mark (energy/speed motif), Purple-to-blue gradient background, White lightning bolt glyph

### Community 87 - "iOS Icon Blank Placeholder"
Cohesion: 0.50
Nodes (3): blank white square, iOS App Icon, 40x40 @1x

### Community 88 - "iOS Icon 40@2x Lightning"
Cohesion: 0.50
Nodes (3): Purple-to-blue gradient, iOS AppIcon 40pt@2x, Lightning bolt glyph

### Community 89 - "iOS Icon iPad 76pt"
Cohesion: 0.50
Nodes (3): Purple-blue gradient fill, 76x76@1x iPad AppIcon size, Lightning bolt icon glyph

## Knowledge Gaps
- **216 isolated node(s):** `name`, `private`, `version`, `type`, `dev` (+211 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **34 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `YoloPersonDetector` connect `YOLO Person Detector` to `Config and Utils`, `Appearance Skill`, `Call Voice Camera Core`, `Face Analyzer OpenCV`, `Event Mode Skill`, `Graphify Agent Pipeline`, `Ollama Backend Probes`, `Piper Playback Paths`, `.detect_person_once`?**
  _High betweenness centrality (0.039) - this node is a cross-community bridge._
- **Why does `HologramFanController` connect `Hologram Fan Controller` to `LLM Test Service`, `Hologram Discovery Factory`, `Detector Overlay Feed`?**
  _High betweenness centrality (0.025) - this node is a cross-community bridge._
- **Why does `WhisperListener` connect `Training Metadata API` to `Voice Trigger WebSocket`, `Call Voice Camera Core`, `FastAPI Main Routes`, `Frontend Hooks Lib`, `Ollama Backend Probes`, `STT Hotwords Cache`?**
  _High betweenness centrality (0.020) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `YoloPersonDetector` (e.g. with `Camera` and `FaceAnalyzer`) actually correct?**
  _`YoloPersonDetector` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `ConnectionManager` (e.g. with `FastAPI` and `BoundingBoxModel`) actually correct?**
  _`ConnectionManager` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `HologramStateManager` (e.g. with `FastAPI` and `BoundingBoxModel`) actually correct?**
  _`HologramStateManager` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `WhisperListener` (e.g. with `FastAPI` and `BoundingBoxModel`) actually correct?**
  _`WhisperListener` has 11 INFERRED edges - model-reasoned connections that need verification._