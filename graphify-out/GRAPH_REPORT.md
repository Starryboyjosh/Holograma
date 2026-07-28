# Graph Report - Holograma  (2026-07-27)

## Corpus Check
- 172 files · ~142,238 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1988 nodes · 3335 edges · 156 communities (124 shown, 32 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 178 edges (avg confidence: 0.66)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `bbea7450`
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
- websocket_chat_endpoint
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
- RecordingManager
- Navegación
- LegacyHologramAdapter
- FakeFan
- @testing-library/user-event
- HologramDirector
- Capas
- test_stt_audio_preprocess.py
- test_unev_content.py
- test_auth_token.py
- Reglas para agentes
- Contrato API
- Checklist de revisión
- Estrategia de pruebas
- Migración y compatibilidad
- Estado real del repositorio
- Inicio rápido
- Modelos de dominio
- Fuentes de verdad
- Asignación de modelos
- Validación física
- Visión y alcance
- Integración en el repositorio
- ._split_detections
- pause_hologram
- Contrato frontend
- Contrato ScenePlan
- Changelog documental
- Backlog
- Requisitos
- CONFIG_SCHEMA.md
- STATUS.md
- camera_feed_subscribe
- @types/react-dom

## God Nodes (most connected - your core abstractions)
1. `YoloPersonDetector` - 77 edges
2. `WhisperListener` - 38 edges
3. `_is_quiet()` - 32 edges
4. `ConnectionManager` - 30 edges
5. `HologramStateManager` - 29 edges
6. `HologramFanController` - 27 edges
7. `_env_float()` - 27 edges
8. `_env()` - 26 edges
9. `HologramDirector` - 25 edges
10. `ConversationService` - 24 edges

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

## Communities (156 total, 32 thin omitted)

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
Cohesion: 0.08
Nodes (42): ask_ai(), ask_ai_and_speak(), _camera_context_for_prompt(), _camera_detection_callback(), camera_feed_unsubscribe(), chat_to_voice(), ensure_camera_for_vision(), get_help_text() (+34 more)

### Community 4 - "YOLO Person Detector"
Cohesion: 0.08
Nodes (16): Calcula correlación de firma de color HSV (0.0 a 1.0) contra referencias del log, Mejor score TM_CCOEFF_NORMED vs plantillas de Entrenar (pirámide multi-escala de, Score 0–1 por coincidencias ORB con descriptores de Entrenar., Match firma HSV + plantilla multiescala + ORB de ``label`` en un ROI. → (score,, Comprueba que el parche de ``box`` se parece a la foto de Entrenar.          Ret, Visión del kiosco: un solo YOLOE open-vocab + logos Entrenar (ORB).      Un chec, Return the most recent annotated frame as JPEG bytes (or None)., Registra un cliente del feed MJPEG (activa la codificación JPEG). (+8 more)

### Community 5 - "Frontend Orb Chat UI"
Cohesion: 0.16
Nodes (19): Orb(), OrbProps, useToast(), ChatSocket, useChatSocket(), UseChatSocketOptions, AssistantScreen(), highlighted() (+11 more)

### Community 6 - "WebSocket Connection Manager"
Cohesion: 0.10
Nodes (13): AbstractEventLoop, ConnectionManager, Protocol, Emisor único de eventos hacia los clientes WebSocket.  El `main.py` actual mezcl, Lo único que el manager necesita de un WebSocket (FastAPI lo cumple)., Registro de conexiones + difusión async, seguro ante sockets caídos., Envía *message* a todas las conexiones; descarta las que fallen.          Se tom, Captura el event loop del servidor para emitir desde hilos no-async.          Se (+5 more)

### Community 7 - "Android Launcher Icons"
Cohesion: 0.11
Nodes (27): mipmap-hdpi density, ic_launcher_foreground.png (hdpi), ic_launcher.png (hdpi), ic_launcher_round.png (hdpi), mipmap-mdpi density, Adaptive icon foreground role, ic_launcher_foreground.png (mdpi), ic_launcher.png (mdpi) (+19 more)

### Community 8 - "iOS App Icon Assets"
Cohesion: 0.12
Nodes (21): Energy / power branding theme, Violet-to-cyan diagonal gradient, Purple–blue lightning bolt mark, iOS AppIcon 40pt@3x Spotlight slot, Transparent background, App Store / 1024 master AppIcon role, iOS AppIcon asset-catalog packaging, Purple–blue lightning bolt brand mark (+13 more)

### Community 9 - "LLM Backend Chat Paths"
Cohesion: 0.05
Nodes (83): _build_messages(), _candidate_backends(), _chat_with_backend(), _chat_with_claude_native(), _chat_with_ollama(), _chat_with_openai_compatible(), _cot_log_enabled(), _cot_print() (+75 more)

### Community 10 - "Hologram Fan Controller"
Cohesion: 0.09
Nodes (17): HologramFanController, Envía exactamente 3 bytes al dispositivo.         El manual especifica: un solo, Enciende e inicia la rotación del holograma. [RUN], Detiene la rotación y apaga el holograma. [STOP], Pausa la reproducción del video. [Pause], Reanuda la reproducción del video., Activa el loop del archivo que está reproduciéndose actualmente., Avanza al siguiente archivo en la playlist. [▶|] (+9 more)

### Community 11 - "FastAPI Main Routes"
Cohesion: 0.08
Nodes (31): BaseModel, Detén la detección y libera la cámara (apagar la cámara = liberarla).      Señal, stop_camera_thread(), FastAPI, BoundingBoxModel, CameraToggle, get_config(), _get_holo_manager() (+23 more)

### Community 12 - "Hologram UI UNEV Content"
Cohesion: 0.09
Nodes (22): app, security, windows, build, beforeBuildCommand, beforeDevCommand, devUrl, frontendDist (+14 more)

### Community 13 - "LLM Unify Tests"
Cohesion: 0.09
Nodes (12): _inject_fake_call(), Unificación de la ruta de LLM (Fases 1 y 2 del plan de mejora).  Cubre tres arre, Evita el import perezoso real de ``call`` (efectos globales: chdir, Qt…)., `_candidate_backends` debe ejecutarse en un hilo distinto al del loop.      El l, primario -> otros proveedores con key -> ollama (si responde) -> local_only., Un primario explícito sin key (p. ej. claude_native) sigue siendo el primer inte, Una respuesta en inglés debe entregarse, no convertirse en un error., test_backend_selection_runs_off_event_loop() (+4 more)

### Community 14 - "Provider Config Resolution"
Cohesion: 0.22
Nodes (10): generate_token(), is_path_privileged(), Token de capacidad (opt-in) para proteger los endpoints privilegiados.  El backe, Genera un token de capacidad aleatorio y url-safe., Compara tokens en tiempo constante. Sin ``expected``, la auth está apagada., ¿La petición modifica estado en una ruta protegida?, Decisión final de autorización para una petición.      Pasa si: la auth está apa, request_authorized() (+2 more)

### Community 15 - "Setup Wizard Scripts"
Cohesion: 0.16
Nodes (19): ConfigUpdate, update_config(), configure_vision(), print_header(), Flujo interactivo para configurar el Cerebro (LLM local o Cloud)., Flujo interactivo para configurar los Oídos (Whisper)., Flujo interactivo para la Visión (YOLOE-26n open-vocab + OpenCV)., Ejecuta el asistente interactivo de configuración completo. (+11 more)

### Community 16 - "Hologram Controller Tests"
Cohesion: 0.08
Nodes (16): HologramArrayTester, Envía un clip independiente a cada holograma de un arreglo.      Este flujo es d, Cierra las conexiones abiertas sin apagar unidades ya probadas., Construye el mapeo estado→índice respetando el orden real de la playlist.      L, resolve_state_clips(), main(), parse_assignment(), FakeFan (+8 more)

### Community 17 - "TS App Compiler Options"
Cohesion: 0.07
Nodes (26): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, jsx, lib, module, moduleDetection, moduleResolution (+18 more)

### Community 18 - "Ollama Backend Probes"
Cohesion: 0.04
Nodes (38): Waves, Alcance, Archivos esperados, Checklist, Fuera de alcance, Gate, Objetivo, Pruebas (+30 more)

### Community 19 - "Provider Config Card UI"
Cohesion: 0.31
Nodes (12): OLLAMA_FALLBACK_SUGGESTIONS, Props, ProviderConfigCard(), Harness(), PROVIDERS, apiKeyPlaceholder(), buildLlmTestInput(), LlmConfigForm (+4 more)

### Community 20 - "Hologram State Manager"
Cohesion: 0.20
Nodes (7): _Camera, _Connection, _LLM, Protocol, Orquestador de un turno de conversación (el corazón de la Fase 3).  Recibe un pr, Procesa un turno completo y devuelve el texto generado ("" si falló)., _tts_stream_enabled()

### Community 21 - "STT Hotwords Cache"
Cohesion: 0.18
Nodes (15): _fresh_listener(), Hotwords STT: caché por mtime, acotado y alineado al contexto UNEV/Honduras., Groq exige prompt ≤896; tildes no deben empujar el conteo del API., faster-whisper debe recibir language=es, task=transcribe y hotwords., La ruta Groq (config actual) debe inyectar prompt de contexto + español., Vocabulario del kiosco + UNEV + Honduras siempre presente., test_groq_receives_language_and_prompt(), test_hotwords_bounded() (+7 more)

### Community 22 - "Custom Object Interval Tests"
Cohesion: 0.10
Nodes (21): _FakeBox, _FakeModel, _FakeResult, _FakeXY, _make_detector(), Inferencia única YOLOE: personas + custom en el mismo predict.  Antes había un m, Open-vocab en el placket del cuello no debe dibujar el cuadro ahí., Open-vocab en cuello/hombro no cuenta como uniforme. (+13 more)

### Community 23 - "LLM ask_ai Pipeline"
Cohesion: 0.13
Nodes (31): get_unev_content(), Contenido institucional de UNEV (fuente única editable)., _build_search_index(), get_admission_info(), get_approval_info(), get_location_info(), get_proceres_info(), get_program_info() (+23 more)

### Community 24 - "TS Node Compiler Options"
Cohesion: 0.10
Nodes (20): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, lib, module, moduleDetection, moduleResolution, noEmit (+12 more)

### Community 25 - "Desktop Brand Icon Set"
Cohesion: 0.33
Nodes (18): 128x128@2x retina/high-DPI icon, 128x128 standard app icon, 32x32 desktop/tray icon variant, 64x64 window icon variant, Primary Tauri app icon (master PNG), Square 107x107 logo (scaled tile), Square 142x142 logo (large tile), Square 150x150 logo (medium start tile) (+10 more)

### Community 26 - "Conversation Service Tests"
Cohesion: 0.09
Nodes (26): ConversationService, LLMService, Servicio de LLM: envuelve la **única** ruta async de generación.  `llm_backend.s, CameraContextProvider, Registra el último análisis de la cámara (lo llamará VisionService)., ContextBuilder, StreamFn, FakeLLM (+18 more)

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
Cohesion: 0.13
Nodes (12): _FakeBox, _FakeBoxes, _FakeModel, _FakeResult, Opciones de inferencia YOLO local (imgsz / device / prepare_frame).  No cargan u, La sala vacía no debe saltarse la inferencia local., Custom a 0.12 no debe quedar filtrado por conf de persona 0.45., test_detect_labels_restores_prompts() (+4 more)

### Community 33 - "Config and Utils"
Cohesion: 0.12
Nodes (19): check_audio_devices(), check_dependencies(), check_environment(), check_import(), fail(), main(), ok(), test_camera() (+11 more)

### Community 34 - "Camera Feed Component"
Cohesion: 0.14
Nodes (12): Holograma / Vite-style purple brand mark, Brand purple #863bff, SVG vector favicon, Shared angular mark geometry with Vite, React cyan #00D8FF, React framework identity, Iconify logos React asset, React logo (+4 more)

### Community 35 - "Appearance Skill"
Cohesion: 0.24
Nodes (4): FaceAnalyzer, Safe face presence analysis with OpenCV.  This module only detects/counts visibl, Count visible frontal faces using OpenCV's bundled Haar cascade., Return a safe visual summary for a frame.

### Community 36 - "Vision Training Pipeline"
Cohesion: 0.15
Nodes (12): description, identifier, permissions, $schema, windows, core:default, core:webview:allow-create-webview-window, core:window:allow-close (+4 more)

### Community 37 - "Event Mode Skill"
Cohesion: 0.10
Nodes (14): Una entrada por label (mejor confianza)., Conf mínima de ``predict``: la más baja entre persona y custom.          Ultraly, Personas + custom en un solo predict YOLOE (+ logos ORB)., Objetos de clases entrenadas / vocabulario + logos ORB.          Preferir ``anal, Inferencia ad-hoc con prompts temporales (YOLOE ``set_classes``).          Resta, Personas + custom YOLOE (+ rostros opcional). Un solo predict., Un frame de cámara → ``analyze_frame`` completo (personas + custom)., Load model if it hasn't been loaded yet. (+6 more)

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
Cohesion: 0.24
Nodes (5): Resuelve un nombre corto a la ruta de un .onnx incluido (0.4.x).          Ej.: `, Bloquea hasta detectar la palabra clave.          Parameters         ----------, Return True if openwakeword and sounddevice are importable., Detecta una palabra clave en streaming con openWakeWord., WakeWordDetector

### Community 42 - "Detached Windows UI"
Cohesion: 0.10
Nodes (28): get_piper_install_hint(), get_powershell_command(), is_wsl(), play_wav_file(), play_wav_with_windows(), Cambia en caliente el modo de activación de voz. Devuelve el modo final., Return a short installation hint for the current platform., Return True when running inside Windows Subsystem for Linux. (+20 more)

### Community 43 - "University Skill"
Cohesion: 0.29
Nodes (9): DetachButton(), DetachButtonProps, isTauriRuntime(), openWidgetWindow(), WIDGET_META, widgetHash(), WidgetMeta, WidgetName (+1 more)

### Community 44 - "Hotwords Skill"
Cohesion: 0.25
Nodes (8): scripts, build, dev, lint, preview, tauri, test, test:watch

### Community 45 - "Presence Skill"
Cohesion: 0.05
Nodes (36): 10. Inventario de constantes clave (código), 11. Changelog breve (sesión de origen de este doc), 1. Objetivo del subsistema, 2. Mapa de archivos (qué tocar), 3. Arquitectura en runtime, 4.1 Un solo modelo: `yoloe-26n-seg.pt`, 4.2 Piso de confianza de `predict`, 4.3 Logos de Entrenar (ITEE y futuros colegios): imagen de referencia (+28 more)

### Community 46 - "Graphify Agent Pipeline"
Cohesion: 0.18
Nodes (6): Lista de personas en *frame* (``confidence``, ``box``).          Corre siempre:, True si hay al menos una persona en *frame*., Número de personas en *frame*., Abre la cámara un instante y devuelve un frame (o None)., Abre la cámara, lee un frame y devuelve True si hay persona., Abre la cámara, lee un frame y devuelve el conteo de personas.

### Community 47 - "Frontend Hooks Lib"
Cohesion: 0.07
Nodes (24): ADR-001 — Reutilizar el controlador TCP, Consecuencia, Decisión, Estado, Razón, ADR-002 — ScenePlan semántico, Consecuencia, Decisión (+16 more)

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
Cohesion: 0.15
Nodes (12): _looks_like_hallucination(), ndarray, Record from the microphone and return the transcribed text.          Returns an, Return True if sounddevice and faster-whisper (or groq if selected) are importab, Return True if *text* is empty or a known Whisper silence-hallucination., Record from the microphone and transcribe with Faster-Whisper.      Parameters, Índice/nombre de micrófono o ``None`` (default del sistema)., Filtro paso-alto de un polo (DC + rumble). Sin SciPy. (+4 more)

### Community 53 - "Training Metadata API"
Cohesion: 0.10
Nodes (26): _correct_kiosk_stt(), _hotword_priority(), _hotwords_sources_signature(), _normalize_hotword(), Speech-to-text listener using Faster-Whisper and sounddevice.  Regla de Oro A: T, Transcribe a WAV file using the Groq API with whisper-large-v3-turbo.          G, Transcribe a WAV file and return the text.          Parameters         ---------, Limpia un término de hotword (paréntesis rotos, puntuación, basura). (+18 more)

### Community 54 - "Listener Lifecycle"
Cohesion: 0.33
Nodes (10): _make_tags_counter(), Caché con TTL de `_ollama_ready()`.  Antes, cada mensaje sondeaba /api/tags 2–4, Sustituye `_ollama_tags` por uno que cuenta llamadas y reporta el modelo listo., El servidor responde, pero el modelo configurado no está instalado., _reset_cache(), test_force_bypasses_cache(), test_model_absent_returns_false(), test_probe_failure_returns_false() (+2 more)

### Community 55 - "Config Env Loading"
Cohesion: 0.13
Nodes (20): Valida y guarda el contenido de UNEV; recarga la fuente en caliente.      Devuel, train_image(), train_vocabulary(), TrainImagePayload, update_unev_content(), VocabularyPayload, clamp_text(), Utilidades de seguridad para Holograma UNEV.  Funciones puras (sin red, sin esta (+12 more)

### Community 56 - "Voice Loop Status"
Cohesion: 0.18
Nodes (12): create_legacy_hologram_manager(), Adaptador de la API de una unidad para los consumidores heredados., Director semántico único de top, center y bottom., Dominio y orquestación de las unidades holográficas., FanUnitConfig, Modelos validados del catálogo holográfico; no contienen transporte TCP., Worker aislado por ventilador, construido sobre el transporte existente., create_hologram_manager() (+4 more)

### Community 57 - "Piper TTS Discovery"
Cohesion: 0.11
Nodes (12): _collar_y_max(), _logo_roi_fractions(), Devuelve True si el recorte es principalmente luz blanca / ventana / destello (a, (y0, y1, x0, x1) del ROI logo en fracciones de la caja persona.      Vertical =, Detecta logos de Entrenar por **imagen de referencia** (template + ORB)., Filtra custom: logos de Entrenar = match a imagen de referencia.          - ``lo, ROI del pecho con logo: cuello + 2×(cabeza→cuello), lado del logo.          Geom, True si el centro (cx,cy) cae en el pecho-logo de la persona. (+4 more)

### Community 58 - "Piper Playback Paths"
Cohesion: 0.14
Nodes (9): Path, Fuerza el checkpoint canónico YOLOE; avisa si había un nombre legacy., Resuelve ``models/<name>`` o ruta absoluta/relativa al proyecto., Carga siempre con Ultralytics ``YOLOE`` (único backend soportado)., Carga YOLOE (personas + custom en una inferencia) y aplica prompts., Load custom classes from training_metadata.json and open_vocabulary.txt., Resuelve rutas tipo ``/data/images/x.jpg`` al fichero local., Recorta el bbox de Entrenar (x,y,w,h) si es válido; si no, imagen completa. (+1 more)

### Community 59 - ".detect_person_once"
Cohesion: 0.15
Nodes (16): get_piper_command_args(), get_piper_model_path(), _get_piper_voice(), _piper_available(), _piper_synth_to_wav(), _piper_synth_to_wav_cli(), _piper_synth_to_wav_python(), Return the command used to run Piper if it is available. (+8 more)

### Community 60 - "Detector Overlay Feed"
Cohesion: 0.12
Nodes (14): HologramConfigStore, Path, Persistencia JSON validada y atómica del catálogo holográfico., HologramConfig, IdentityMedia, _index(), PromotionMedia, RotationConfig (+6 more)

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
Cohesion: 0.12
Nodes (12): HologramStateManager, Cierra la conexión TCP limpiamente., Salta directamente al video número N de la playlist.          Args:, Conecta cada unidad, reproduce su índice y devuelve el resultado., Puente thread-safe entre los estados de la IA y los clips del holograma.      La, True cuando el gestor automático tiene un socket TCP activo., Aplica un destino TCP nuevo y activa el cambio automático de clips., Desconecta el dispositivo y desactiva los reintentos automáticos. (+4 more)

### Community 66 - "Voice Trigger WebSocket"
Cohesion: 0.20
Nodes (5): Draw person and custom-object boxes on a copy of *frame*., Encode *frame* (with overlay) to JPEG and cache it for streaming., ¿Hay al menos un cliente viendo el feed anotado?, Run a detection loop calling *callback(event, count)* on changes.          Param, Duerme hasta *seconds* o hasta ``stop()`` (no bloquea el apagado).

### Community 67 - "Hologram Discovery Factory"
Cohesion: 0.10
Nodes (11): Decisiones abiertas, Registro de decisiones, Riesgos, Handoffs, Plantilla, Prompt maestro, Dependencia, Roadmap (+3 more)

### Community 68 - "STT Record Transcribe"
Cohesion: 0.29
Nodes (8): clean_for_tts(), Remove characters that can sound awkward when read by a TTS engine., Divide texto limpio en fragmentos TTS (misma heurística que el stream).      Usa, Habla cláusulas en cuanto el LLM las produce (sin esperar al final).      Mantie, speak_streaming_from_llm(), _split_into_chunks(), pop_ready_speech(), Extrae cláusulas/oraciones listas para TTS desde un buffer de stream.      El pr

### Community 69 - "Face Analyzer OpenCV"
Cohesion: 0.12
Nodes (16): Archivos creados, Archivos modificados, Comandos ejecutados y resultados exactos, Commit, Compatibilidad preservada, Decisiones tomadas, Estado, Evidencia (+8 more)

### Community 70 - "Camera Context Prompt"
Cohesion: 0.24
Nodes (6): Proveedor del contexto de cámara para el LLM.  `llm_backend.stream_llm_response`, build_camera_context(), is_visual_object_question(), Construcción del contexto de cámara para el prompt del LLM.  Módulo neutro (sin, True si el visitante pregunta por lo visual / ropa (no un saludo genérico)., Convierte un análisis de cámara en texto para el prompt del LLM.      Si no hay

### Community 71 - "LLM Provider Selection"
Cohesion: 0.18
Nodes (16): _coerce(), _invalidate_skill_caches(), load_unev_info(), Path, Fuente única y editable de la información institucional de UNEV.  Antes, los dat, Normaliza ``data`` a la forma canónica, rellenando faltantes con el respaldo., Devuelve una lista de errores (vacía = válido) para mostrar al operador., Carga el contenido desde el JSON autoritativo; respaldo en código si falla. (+8 more)

### Community 72 - "README.md"
Cohesion: 0.24
Nodes (6): _count_stores(), Gating del feed MJPEG: el detector solo codifica JPEG si alguien mira.  Codifica, Corre run_continuous unos cuadros y cuenta cuántas veces guardó un JPEG., test_run_continuous_encodes_with_subscriber(), test_run_continuous_skips_encode_without_subscribers(), Cross-platform OpenCV camera wrapper.  Regla de Oro A: Todas las rutas usan path

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

### Community 90 - "Detect Person Once"
Cohesion: 0.25
Nodes (4): Ejecuta ``model.predict`` (YOLOE) y devuelve (label, conf, box) en coords origin, Argumentos comunes de inferencia local (latencia / recursos)., Opcional: reduce el frame grande antes de YOLO (sin apagar la cámara)., Una inferencia dummy para JIT/CUDA/CLIP tras el load.          Evita el primer f

### Community 96 - "websocket_chat_endpoint"
Cohesion: 0.50
Nodes (4): get_trigger_mode(), Devuelve el modo de activación de voz actual., websocket_chat_endpoint(), WebSocket

### Community 99 - "Services Package Init"
Cohesion: 0.12
Nodes (15): Archivos, Checklist, Contratos afectados, En alcance, Estado real, Evidencia, Fuera de alcance, Handoff (+7 more)

### Community 103 - "Vision Package Init"
Cohesion: 0.21
Nodes (3): HologramUnitManager, Mantiene los comandos manuales heredados fuera de la ruta de IA., FanRole

### Community 114 - "get_stt_status"
Cohesion: 0.14
Nodes (9): Test del mecanismo de parada/liberación de la cámara (Fase B).  No requiere cáma, Vision helpers for the UNEV hologram assistant., _compute_scale_back(), Detector de visión del holograma UNEV: un solo modelo open-vocab YOLOE.  Por def, Normaliza `box.xyxy[0]` de Ultralytics (tensor) o de fakes de test (list)., Factor para reescalar cajas del frame reducido al frame original., Reescala una caja ``(x1, y1, x2, y2)`` si ``scale_back != 1.0``., _scale_box() (+1 more)

### Community 122 - "RecordingManager"
Cohesion: 0.25
Nodes (6): FanUnitStatus, ScenePlan, config(), RecordingManager, test_director_routes_semantic_commands_to_the_correct_role(), test_three_units_keep_distinct_network_configuration()

### Community 123 - "Navegación"
Cohesion: 0.15
Nodes (13): Arquitectura, Calidad, Contratos, Control inteligente de Holograma, Definición de terminado, Empezar, Gobierno, Implementación (+5 more)

### Community 125 - "FakeFan"
Cohesion: 0.27
Nodes (5): FakeFan, manager(), test_concurrent_commands_are_serialized(), test_deduplication_reconnection_and_idempotent_shutdown(), test_disconnected_unit_reconnects_without_breaking_worker()

### Community 127 - "HologramDirector"
Cohesion: 0.29
Nodes (3): HologramDirector, HologramStatus, MascotState

### Community 128 - "Capas"
Cohesion: 0.20
Nodes (9): API/UI, Arquitectura del sistema, Capas, Ciclo de vida, Dominio, IA, Orquestación, Principios (+1 more)

### Community 129 - "test_stt_audio_preprocess.py"
Cohesion: 0.29
Nodes (9): ndarray, Preprocesado de audio STT (local + nube): DC, normalización, padding, WAV., Regresión: preprocess no rompe la ruta local de transcribe_file., _sine(), test_audio_to_wav_is_pcm16_mono_16k(), test_highpass_attenuates_dc_step(), test_local_transcribe_still_gets_spanish_kwargs(), test_preprocess_pads_edges() (+1 more)

### Community 132 - "Reglas para agentes"
Cohesion: 0.25
Nodes (7): Antes de modificar, Definition of Done, Protocolo de cierre, Protocolo de inicio, Regla para modelos débiles, Reglas para agentes, Restricciones duras

### Community 133 - "Contrato API"
Cohesion: 0.29
Nodes (6): Compatibilidad, Contrato API, Identidades, Promociones, Rotación, Unidades

### Community 134 - "Checklist de revisión"
Cohesion: 0.29
Nodes (6): API/UI, Arquitectura, Checklist de revisión, Concurrencia, IA, Operación

### Community 135 - "Estrategia de pruebas"
Cohesion: 0.29
Nodes (6): Comandos, E2E simulada, Estrategia de pruebas, Fakes, Integración, Unitarias

### Community 136 - "Migración y compatibilidad"
Cohesion: 0.33
Nodes (5): Endpoints heredados, Migración y compatibilidad, Regla, Reversión, Variables heredadas

### Community 137 - "Estado real del repositorio"
Cohesion: 0.33
Nodes (5): Brechas, Estado real del repositorio, Existente, IP históricas, Rutas de conversación

### Community 138 - "Inicio rápido"
Cohesion: 0.33
Nodes (5): Al terminar una wave, Inicio rápido, No comenzar con Sol, Para comenzar WAVE-001, Regla principal

### Community 139 - "Modelos de dominio"
Cohesion: 0.40
Nodes (4): Entidades, Invariantes, Modelos de dominio, Tipos

### Community 140 - "Fuentes de verdad"
Cohesion: 0.40
Nodes (4): Cambios de contrato, Conflictos, Fuentes de verdad, Orden

### Community 141 - "Asignación de modelos"
Cohesion: 0.40
Nodes (4): Asignación de modelos, Luna 5.6, Sol 5.6, Terra 5.6

### Community 142 - "Validación física"
Cohesion: 0.40
Nodes (4): Evidencia, IP históricas, Preparación, Validación física

### Community 143 - "Visión y alcance"
Cohesion: 0.40
Nodes (4): No objetivos, Objetivos v1, Visión, Visión y alcance

### Community 144 - "Integración en el repositorio"
Cohesion: 0.40
Nodes (4): Añadir a AGENTS.md, Añadir al README principal, Copiar, Integración en el repositorio

### Community 146 - "pause_hologram"
Cohesion: 0.50
Nodes (4): pause_hologram(), Attempt to terminate any running TTS or audio players on Linux., Pause hologram activity: stop speaking, listening and seeing., stop_all_tts_processes()

### Community 147 - "Contrato frontend"
Cohesion: 0.50
Nodes (3): Contrato frontend, Requisitos UX, Secciones

### Community 148 - "Contrato ScenePlan"
Cohesion: 0.50
Nodes (3): Contrato ScenePlan, Fallback, Prohibido

### Community 149 - "Changelog documental"
Cohesion: 0.50
Nodes (3): 2026-07-27 — V2, Changelog documental, V1

### Community 150 - "Backlog"
Cohesion: 0.50
Nodes (3): Backlog, MVP, Post-MVP

### Community 151 - "Requisitos"
Cohesion: 0.50
Nodes (3): Funcionales, No funcionales, Requisitos

## Knowledge Gaps
- **412 isolated node(s):** `name`, `private`, `version`, `type`, `dev` (+407 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **32 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `YoloPersonDetector` connect `YOLO Person Detector` to `Config and Utils`, `Voice Trigger WebSocket`, `Call Voice Camera Core`, `Appearance Skill`, `Event Mode Skill`, `Detect Person Once`, `Graphify Agent Pipeline`, `._split_detections`, `get_stt_status`, `Piper TTS Discovery`, `Piper Playback Paths`?**
  _High betweenness centrality (0.085) - this node is a cross-community bridge._
- **Why does `HologramFanController` connect `Hologram Fan Controller` to `Voice Loop Status`, `LLM Test Service`, `Vision Package Init`?**
  _High betweenness centrality (0.033) - this node is a cross-community bridge._
- **Why does `WhisperListener` connect `Backend URL Hooks` to `websocket_chat_endpoint`, `test_stt_audio_preprocess.py`, `Call Voice Camera Core`, `FastAPI Main Routes`, `Setup Wizard Scripts`, `Training Metadata API`, `STT Hotwords Cache`, `Config Env Loading`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `YoloPersonDetector` (e.g. with `Camera` and `FaceAnalyzer`) actually correct?**
  _`YoloPersonDetector` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `WhisperListener` (e.g. with `FastAPI` and `BoundingBoxModel`) actually correct?**
  _`WhisperListener` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `ConnectionManager` (e.g. with `FastAPI` and `BoundingBoxModel`) actually correct?**
  _`ConnectionManager` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `HologramStateManager` (e.g. with `FastAPI` and `BoundingBoxModel`) actually correct?**
  _`HologramStateManager` has 11 INFERRED edges - model-reasoned connections that need verification._