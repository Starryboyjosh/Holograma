# Graph Report - Holograma  (2026-06-27)

## Corpus Check
- 112 files · ~119,200 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1186 nodes · 1967 edges · 99 communities (83 shown, 16 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 80 edges (avg confidence: 0.58)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `df5b9ce1`
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
- [[_COMMUNITY_Community 70|Community 70]]
- [[_COMMUNITY_Community 71|Community 71]]
- [[_COMMUNITY_Community 72|Community 72]]
- [[_COMMUNITY_Community 73|Community 73]]
- [[_COMMUNITY_Community 74|Community 74]]
- [[_COMMUNITY_Community 75|Community 75]]
- [[_COMMUNITY_Community 76|Community 76]]
- [[_COMMUNITY_Community 77|Community 77]]
- [[_COMMUNITY_Community 78|Community 78]]
- [[_COMMUNITY_Community 79|Community 79]]
- [[_COMMUNITY_Community 80|Community 80]]
- [[_COMMUNITY_Community 81|Community 81]]
- [[_COMMUNITY_Community 82|Community 82]]
- [[_COMMUNITY_Community 83|Community 83]]
- [[_COMMUNITY_Community 84|Community 84]]
- [[_COMMUNITY_Community 85|Community 85]]
- [[_COMMUNITY_Community 86|Community 86]]
- [[_COMMUNITY_Community 87|Community 87]]
- [[_COMMUNITY_Community 88|Community 88]]
- [[_COMMUNITY_Community 89|Community 89]]
- [[_COMMUNITY_Community 90|Community 90]]
- [[_COMMUNITY_Community 91|Community 91]]
- [[_COMMUNITY_Community 92|Community 92]]
- [[_COMMUNITY_Community 93|Community 93]]
- [[_COMMUNITY_Community 94|Community 94]]
- [[_COMMUNITY_Community 95|Community 95]]
- [[_COMMUNITY_Community 109|Community 109]]

## God Nodes (most connected - your core abstractions)
1. `HologramFanController` - 32 edges
2. `HologramStateManager` - 27 edges
3. `_env()` - 27 edges
4. `ConnectionManager` - 26 edges
5. `YoloPersonDetector` - 26 edges
6. `WhisperListener` - 23 edges
7. `_is_quiet()` - 22 edges
8. `stream_llm_response()` - 18 edges
9. `Camera` - 18 edges
10. `voice_loop()` - 17 edges

## Surprising Connections (you probably didn't know these)
- `BoundingBoxModel` --uses--> `ConnectionManager`  [INFERRED]
  main.py → app/connection.py
- `CameraToggle` --uses--> `ConnectionManager`  [INFERRED]
  main.py → app/connection.py
- `ConfigUpdate` --uses--> `ConnectionManager`  [INFERRED]
  main.py → app/connection.py
- `HologramCommand` --uses--> `ConnectionManager`  [INFERRED]
  main.py → app/connection.py
- `HologramConnect` --uses--> `ConnectionManager`  [INFERRED]
  main.py → app/connection.py

## Import Cycles
- 1-file cycle: `main.py -> main.py`
- 1-file cycle: `frontend/src-tauri/src/lib.rs -> frontend/src-tauri/src/lib.rs`

## Communities (99 total, 16 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.19
Nodes (23): _build_messages(), _candidate_backends(), _chat_with_backend(), _chat_with_claude_native(), _chat_with_ollama(), _chat_with_openai_compatible(), generate_reply(), _is_mostly_english() (+15 more)

### Community 1 - "Community 1"
Cohesion: 0.13
Nodes (12): Load the model if it hasn't been loaded yet., Load custom classes from training_metadata.json and open_vocabulary.txt., Combine custom classes and vocabulary into a single YOLOE text prompt., Detect custom objects using YOLOE text prompts from training data., Return a list of person detections in *frame*.          Each detection is a dict, Return person and custom object detections plus optional safe face count., Detect people using YOLOe26 via the Ultralytics library.      Parameters     ---, Return the most recent annotated frame as JPEG bytes (or None). (+4 more)

### Community 2 - "Community 2"
Cohesion: 0.12
Nodes (18): get_powershell_command(), is_wsl(), play_wav_file(), play_wav_with_windows(), Return True when running inside Windows Subsystem for Linux., Return a PowerShell executable path on Windows or WSL if available., Run a PowerShell script and return True when it succeeds., Play a WAV file with Windows' built-in SoundPlayer. (+10 more)

### Community 3 - "Community 3"
Cohesion: 0.41
Nodes (11): check_audio_devices(), check_dependencies(), check_environment(), check_import(), fail(), main(), ok(), test_camera() (+3 more)

### Community 4 - "Community 4"
Cohesion: 0.21
Nodes (13): clamp_text(), Sanea texto no confiable: elimina caracteres de control y trunca a ``max_len``., _coerce(), load_unev_info(), Fuente única y editable de la información institucional de UNEV.  Antes, los dat, Normaliza ``data`` a la forma canónica, rellenando faltantes con el respaldo., Devuelve una lista de errores (vacía = válido) para mostrar al operador., Carga el contenido desde el JSON autoritativo; respaldo en código si falla. (+5 more)

### Community 5 - "Community 5"
Cohesion: 0.12
Nodes (21): chat_to_voice(), get_help_text(), handle_command(), main(), Text input loop: keyboard → LLM → TTS., Bloquea hasta que toque escuchar, según el modo dinámico actual.      Devuelve `, Voice input loop: microphone → Whisper → LLM → TTS (Regla B: sounddevice)., Parse flags and run the appropriate loop. (+13 more)

### Community 6 - "Community 6"
Cohesion: 0.09
Nodes (15): HologramFanController, Envía exactamente 3 bytes al dispositivo.         El manual especifica: un solo, Enciende e inicia la rotación del holograma. [RUN], Detiene la rotación y apaga el holograma. [STOP], Pausa la reproducción del video. [Pause], Reanuda la reproducción del video., Activa el loop del archivo que está reproduciéndose actualmente., Avanza al siguiente archivo en la playlist. [▶|] (+7 more)

### Community 7 - "Community 7"
Cohesion: 0.08
Nodes (9): create_hologram_manager(), =============================================================  Controlador Pytho, Construye el mapeo estado→índice respetando el orden real de la playlist.      L, Construye un HologramStateManager a partir de variables de entorno.      Variabl, resolve_state_clips(), FakeFan, test_configured_manager_applies_ai_state_clips(), test_configured_manager_uses_custom_clip_map() (+1 more)

### Community 8 - "Community 8"
Cohesion: 0.05
Nodes (36): 0. TL;DR (resumen ejecutivo), 1.1 El pecado original: una CLI disfrazada de servidor web, 1.2 Dos caminos de LLM que divergen, 1.3 Importaciones circulares, 1. Cómo está construido hoy (y por qué duele), 2.A — "Se congela" / todo lento  →  bloqueo del event loop, 2.B — "Se queda en hablando" / el estado nunca vuelve a idle, 2.C — "A veces no responde / dice que no puede responder" (+28 more)

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
Cohesion: 0.07
Nodes (36): BaseModel, Detén la detección y libera la cámara (apagar la cámara = liberarla).      Señal, stop_camera_thread(), _atomic_write_text(), BoundingBoxModel, CameraToggle, ConfigUpdate, _get_holo_manager() (+28 more)

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
Cohesion: 0.16
Nodes (8): HologramStateManager, Salta directamente al video número N de la playlist.          Args:, Puente thread-safe entre los estados de la IA y los clips del holograma.      La, True cuando el gestor automático tiene un socket TCP activo., Aplica un destino TCP nuevo y activa el cambio automático de clips., Compatibilidad con la API: ejecuta un comando usando la conexión compartida., Arranca el hilo de control y deja el holograma en idle. No-op si está deshabilit, Solicita un cambio de estado del holograma. No bloquea ni lanza excepciones.

### Community 24 - "Community 24"
Cohesion: 0.07
Nodes (29): ContextBuilder, Protocol, _Camera, _Connection, ConversationService, _LLM, Orquestador de un turno de conversación (el corazón de la Fase 3).  Recibe un pr, Procesa un turno completo y devuelve el texto generado ("" si falló). (+21 more)

### Community 25 - "Community 25"
Cohesion: 0.24
Nodes (11): configure_vision(), print_header(), Flujo interactivo para configurar el Cerebro (LLM local o Cloud)., Flujo interactivo para configurar los Oídos (Whisper)., Flujo interactivo para la Visión (YOLOv26 + OpenCV)., Ejecuta el asistente interactivo de configuración completo., Imprime el header estilo 'hermes setup'., run_setup() (+3 more)

### Community 26 - "Community 26"
Cohesion: 0.13
Nodes (14): A. Settings UX + wire test buttons  ✅ DONE, B. Cancellation + camera release + per-session events  (touches call.py, higher risk), C. Windows-first sidecar packaging  (cannot finish here; needs Windows runner), D. Security + operator auth, E. De-monkey-patch into typed services  ✅ FOUNDATION DONE (wiring is runtime-gated), F. Single editable UNEV content source  ✅ DONE, G. Legacy lint debt  ✅ DONE, Hard environment constraints (read first) (+6 more)

### Community 27 - "Community 27"
Cohesion: 0.18
Nodes (9): get_piper_sample_rate(), Read Piper sample rate from the model JSON sidecar when available., _looks_like_hallucination(), Record audio from the default microphone until silence is detected.          Usa, Write a float32 numpy array to a temporary WAV file.          Returns a ``pathli, Record from the microphone and return the transcribed text.          Returns an, Return True if *text* is empty or a known Whisper silence-hallucination., _is_quiet() (+1 more)

### Community 28 - "Community 28"
Cohesion: 0.20
Nodes (9): Arquitectura del código, Autoría de los clips (condiciona toda la parte visual), Conexión, Endpoints (`main.py`), Holograma físico MISSYOU — integración por TCP, Mapeo estado de la IA → clip (y por qué se hizo configurable), Pendientes / opcional (no hechos a propósito), Reparto de responsabilidades: app HoloMissYou ↔ este controlador (+1 more)

### Community 29 - "Community 29"
Cohesion: 0.13
Nodes (14): anyOf, definitions, Number, Target, Value, description, anyOf, description (+6 more)

### Community 30 - "Community 30"
Cohesion: 0.15
Nodes (13): definitions, Number, PermissionEntry, Target, Value, anyOf, description, anyOf (+5 more)

### Community 31 - "Community 31"
Cohesion: 0.23
Nodes (10): Props, PROVIDERS, apiKeyPlaceholder(), buildLlmConfigPayload(), buildLlmTestInput(), LlmConfigForm, LlmTestInput, LlmTestResult (+2 more)

### Community 32 - "Community 32"
Cohesion: 0.29
Nodes (11): CameraFeed(), CameraFeedProps, useBackendUrl(), UseChatSocketOptions, apiUrl(), backendBase(), detectBase(), mediaUrl() (+3 more)

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
Cohesion: 0.18
Nodes (12): get_trigger_mode(), Solicita una escucha puntual (push-to-talk remoto, p. ej. la WebApp)., Cambia en caliente el modo de activación de voz. Devuelve el modo final., Devuelve el modo de activación de voz actual., Lee ENTER de la terminal y solicita una escucha (push-to-talk en CLI)., request_listen(), set_trigger_mode(), _stdin_ptt_reader() (+4 more)

### Community 46 - "Community 46"
Cohesion: 0.33
Nodes (3): Draw person and custom-object boxes on a copy of *frame*., Encode *frame* (with overlay) to JPEG and cache it for streaming., Run a detection loop calling *callback(event, count)* on changes.          Param

### Community 47 - "Community 47"
Cohesion: 0.13
Nodes (4): Utilidades de seguridad para Holograma UNEV.  Funciones puras (sin red, sin esta, Aplica :func:`redact_secrets` a una colección (útil para listas de logs)., redact_iter(), Tests de las utilidades de seguridad (redacción de secretos + saneo de texto).

### Community 48 - "Community 48"
Cohesion: 0.50
Nodes (4): description, required, type, Capability

### Community 49 - "Community 49"
Cohesion: 0.50
Nodes (4): default, description, type, description

### Community 50 - "Community 50"
Cohesion: 0.18
Nodes (6): Cierra y olvida todas las conexiones (apagado ordenado del servidor).          E, discover_devices(), Cierra la conexión TCP limpiamente., Escanea la red local buscando hologramas MISSYOU en el puerto 50200.      Útil c, Desconecta el dispositivo y desactiva los reintentos automáticos., Detiene el hilo, apaga el giro y cierra la conexión limpiamente.

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
Cohesion: 0.21
Nodes (15): Hologram, HologramConnection(), OLLAMA_SUGGESTIONS, ProviderConfigCard(), FIELD_LABELS, Card(), CardProps, SectionTitle() (+7 more)

### Community 58 - "Community 58"
Cohesion: 0.25
Nodes (9): useToast(), useChatSocket(), useUnevContent(), ContentScreen(), CameraWidget(), ChatWidget(), SUGGESTIONS, TranscriptWidget() (+1 more)

### Community 59 - "Community 59"
Cohesion: 0.50
Nodes (4): description, required, type, Capability

### Community 60 - "Community 60"
Cohesion: 0.22
Nodes (8): Configuración de IA — Contrato de proveedor y modelo, Cómo se elige el backend (`select_backend`), Endpoints relacionados, Endurecimiento de seguridad (Fase D.1), Interfaz de Ajustes, Límite de tokens y robustez de la respuesta, Proveedores soportados, Pruebas

### Community 61 - "Community 61"
Cohesion: 0.13
Nodes (24): ask_ai(), _build_camera_context(), _camera_detection_callback(), get_latest_camera_jpeg(), _is_greeting(), _is_visual_question(), pause_hologram(), UNEV Hologram — Main entry point.  Regla de Oro A: Todas las rutas usan pathlib. (+16 more)

### Community 62 - "Community 62"
Cohesion: 0.18
Nodes (10): Speech-to-text listener using Faster-Whisper and sounddevice.  Regla de Oro A: T, Detector de palabra clave (wake word) con openWakeWord.  Regla de Oro A: Todas l, configure_utf8_stdio(), _env_float(), _env_int(), Helper to retrieve float environment variables., Helper to retrieve integer environment variables., Configures standard input/output streams to use UTF-8 encoding across systems. (+2 more)

### Community 63 - "Community 63"
Cohesion: 0.22
Nodes (11): Orb(), OrbProps, AssistantScreen(), highlighted(), SUGGESTIONS, requestServerListen, AssistantState, COLORS (+3 more)

### Community 64 - "Community 64"
Cohesion: 0.40
Nodes (4): anyOf, description, $schema, title

### Community 65 - "Community 65"
Cohesion: 0.15
Nodes (8): _inject_fake_call(), Unificación de la ruta de LLM (Fases 1 y 2 del plan de mejora).  Cubre tres arre, Una respuesta en inglés debe entregarse, no convertirse en un error., Evita el import perezoso real de ``call`` (efectos globales: chdir, Qt…)., `_candidate_backends` debe ejecutarse en un hilo distinto al del loop.      El l, test_backend_selection_runs_off_event_loop(), test_postprocess_keeps_english_response(), test_stream_local_only_yields_canned_reply()

### Community 66 - "Community 66"
Cohesion: 0.50
Nodes (4): clean_for_tts(), Remove characters that can sound awkward when read by a TTS engine., Divide el texto en fragmentos listos para TTS.     El primero usa cláusulas para, _split_into_chunks()

### Community 69 - "Community 69"
Cohesion: 0.21
Nodes (8): AppearanceTheme, resolveDark(), ThemeCtx, ThemeProvider(), ThemeValue, ShowToast, ToastCtx, ToastProvider()

### Community 70 - "Community 70"
Cohesion: 0.21
Nodes (11): _analysis(), _drive(), Máquina de estados de presencia: parpadeos vs. ausencia real.  Estos tests blind, Análisis sintético con *count* personas (forma que devuelve analyze_frame)., Corre `run_continuous` sobre una secuencia de conteos y devuelve los eventos., Un cuadro perdido entre dos presencias NO debe re-disparar person_entered., Una ausencia sostenida (supera la gracia) sí cuenta como ida y vuelta., Un grupo (>3) dispara group_detected una sola vez mientras se mantiene. (+3 more)

### Community 71 - "Community 71"
Cohesion: 0.50
Nodes (3): Expanding the ESLint configuration, React Compiler, React + TypeScript + Vite

### Community 72 - "Community 72"
Cohesion: 0.25
Nodes (8): AppShell(), NAV_ITEMS, useSession(), useTheme(), useProviders(), SettingsScreen(), TeachingScreen(), BoundingBox

### Community 73 - "Community 73"
Cohesion: 0.27
Nodes (9): DetachButton(), DetachButtonProps, isTauriRuntime(), openWidgetWindow(), WIDGET_META, widgetHash(), WidgetMeta, WidgetName (+1 more)

### Community 74 - "Community 74"
Cohesion: 0.33
Nodes (10): _make_tags_counter(), Caché con TTL de `_ollama_ready()`.  Antes, cada mensaje sondeaba /api/tags 2–4, Sustituye `_ollama_tags` por uno que cuenta llamadas y reporta el modelo listo., El servidor responde, pero el modelo configurado no está instalado., _reset_cache(), test_force_bypasses_cache(), test_model_absent_returns_false(), test_probe_failure_returns_false() (+2 more)

### Community 75 - "Community 75"
Cohesion: 0.22
Nodes (11): CameraState, SessionCtx, SessionProvider(), SessionValue, ChatSocket, useConfig(), useHologram(), UseHologramOptions (+3 more)

### Community 80 - "Community 80"
Cohesion: 0.21
Nodes (16): Resuelve (api_key, model, base_url) o lanza un error claro y accionable., _require(), all_providers_public_info(), _canonical_provider(), _norm(), Provider, provider_public_info(), Unified LLM provider/model configuration contract for Holograma UNEV.  Antes de (+8 more)

### Community 81 - "Community 81"
Cohesion: 0.15
Nodes (9): ConnectionManager, Emisor único de eventos hacia los clientes WebSocket.  El `main.py` actual mezcl, Lo único que el manager necesita de un WebSocket (FastAPI lo cumple)., Registro de conexiones + difusión async, seguro ante sockets caídos., Envía *message* a todas las conexiones; descarta las que fallen.          Se tom, WebSocketLike, FastAPI, lifespan() (+1 more)

### Community 86 - "Community 86"
Cohesion: 0.41
Nodes (11): route_local_skill(), get_unev_info(), Contenido vigente (cacheado). Llamado por las skills en cada respuesta., get_admission_info(), get_approval_info(), get_location_info(), get_program_info(), get_programs_summary() (+3 more)

### Community 87 - "Community 87"
Cohesion: 0.29
Nodes (11): get_backend_status(), _humanize_probe_error(), _ollama_model_available(), _ollama_model_name(), _ollama_ready(), _ollama_server_available(), _ollama_tags(), probe_backend() (+3 more)

### Community 89 - "Community 89"
Cohesion: 0.25
Nodes (7): 0. READ FIRST — the backend RUNS on this machine, 1. What the monkey-patching actually does — DO NOT delete blindly, 2. Target wiring — strangler, smallest-risk first (one step = one commit), 3. §8 folder reorg — ONLY after A–D are green, 4. Don'ts, Phase 3 wiring — next-session execution plan, Validation recipe (run before AND after every step)

### Community 91 - "Community 91"
Cohesion: 0.29
Nodes (5): Load the Faster-Whisper model on first use., Transcribe a WAV file and return the text.          Parameters         ---------, Return True if sounddevice and faster-whisper are importable., Record from the microphone and transcribe with Faster-Whisper.      Parameters, WhisperListener

### Community 92 - "Community 92"
Cohesion: 0.25
Nodes (4): Test del mecanismo de parada/liberación de la cámara (Fase B).  No requiere cáma, get_vision_status(), YOLOv8/v11 person detector for the UNEV hologram.  Regla de Oro A: Todas las rut, Return a human-readable status string for the vision subsystem.

### Community 94 - "Community 94"
Cohesion: 0.67
Nodes (3): PermissionEntry, anyOf, description

## Knowledge Gaps
- **294 isolated node(s):** `StreamFn`, `ContextBuilder`, `name`, `private`, `version` (+289 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **16 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `YoloPersonDetector` connect `Community 1` to `Community 33`, `Community 3`, `Community 5`, `Community 76`, `Community 46`, `Community 15`, `Community 93`, `Community 92`, `Community 61`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **Why does `HologramFanController` connect `Community 6` to `Community 7`, `Community 45`, `Community 81`, `Community 50`, `Community 17`, `Community 23`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `HologramFanController` (e.g. with `FastAPI` and `BoundingBoxModel`) actually correct?**
  _`HologramFanController` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `HologramStateManager` (e.g. with `FastAPI` and `BoundingBoxModel`) actually correct?**
  _`HologramStateManager` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `ConnectionManager` (e.g. with `FastAPI` and `BoundingBoxModel`) actually correct?**
  _`ConnectionManager` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `YoloPersonDetector` (e.g. with `Camera` and `FaceAnalyzer`) actually correct?**
  _`YoloPersonDetector` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Capa web + orquestación del Holograma UNEV (refactor de Fase 3).  Esta es la **c`, `Emisor único de eventos hacia los clientes WebSocket.  El `main.py` actual mezcl`, `Lo único que el manager necesita de un WebSocket (FastAPI lo cumple).` to the rest of the system?**
  _491 weakly-connected nodes found - possible documentation gaps or missing edges._