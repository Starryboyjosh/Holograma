# Holograma UNEV — Shell de escritorio (Tauri v2)

Convierte la app FastAPI + React/Vite en una aplicación de escritorio que:

- Arranca el backend Python automáticamente (sin abrir `localhost` a mano).
- Muestra la UI React dentro de una ventana nativa.
- Permite **desprender widgets** (cámara, chat, transcripción, control) como
  ventanas independientes — útil en los monitores verticales del stand.

## Cómo funciona

1. El lado Rust (`src/lib.rs`) pide un **puerto TCP libre**.
2. Arranca el backend: en desarrollo ejecuta `python3 main.py --port <port>` con
   el directorio del proyecto como CWD.
3. Hace **healthcheck** contra `GET /api/config` (hasta 20 s) antes de seguir.
4. Expone el comando `get_backend_url`; el frontend (`src/lib/backend.ts`) lo usa
   para construir todas las URLs de API/WebSocket/medios apuntando a ese puerto.
5. Al salir, **mata el proceso** del backend (cierre limpio).

En el navegador (modo web de siempre) `get_backend_url` no existe, así que el
frontend usa rutas relativas al mismo origen — el flujo actual no cambia.

## Requisitos

- Rust stable + Cargo.
- Node/npm.
- **Linux:** WebKitGTK 4.1 y dependencias de Tauri (`webkit2gtk-4.1`,
  `libappindicator`, `librsvg`, `patchelf`).
- **Windows:** Microsoft Edge WebView2 Runtime + MSVC Build Tools.
- Python con las dependencias del backend instaladas en el entorno activo.

## Desarrollo

Desde `frontend/`:

```bash
npm install
npm run tauri dev
```

Esto levanta Vite en `http://localhost:5173`, compila el shell Rust, arranca el
backend en un puerto libre y muestra la ventana cuando responde.

### Variables de entorno útiles

| Variable                 | Para qué sirve                                             |
| ------------------------ | ---------------------------------------------------------- |
| `HOLOGRAM_PYTHON`        | Intérprete a usar (por defecto `python3`).                 |
| `HOLOGRAM_BACKEND_DIR`   | Carpeta donde está `main.py` (por defecto la raíz del repo).|
| `HOLOGRAM_PORT`          | Fuerza el puerto del backend si lo lanzas tú a mano.       |

## Widgets desprendibles

Rutas (hash) servidas por el mismo bundle:

- `#/widget/camera` — stream YOLO
- `#/widget/chat` — conversación
- `#/widget/transcript` — transcripción en vivo
- `#/widget/controls` — control del holograma

El botón "⧉" (`DetachButton`) abre una `WebviewWindow` real en Tauri y cae a
`window.open` en el navegador. Cada ventana abre su propio WebSocket; el backend
hace broadcast a todas las conexiones, así que se mantienen en sincronía.

## Empaquetado del backend (PENDIENTE — paso posterior)

El prototipo arranca `main.py` como proceso externo. Para un instalable final,
empaqueta el backend con PyInstaller y regístralo como **sidecar**:

```bash
pyinstaller --onefile --name holograma-backend main.py
# Copia el binario con el sufijo del target a src-tauri/binaries/, p. ej.:
#   holograma-backend-x86_64-unknown-linux-gnu
#   holograma-backend-x86_64-pc-windows-msvc.exe
```

Luego añade a `tauri.conf.json`:

```json
"bundle": {
  "externalBin": ["binaries/holograma-backend"]
}
```

y cambia `spawn_backend()` en `src/lib.rs` para usar el sidecar
(`tauri_plugin_shell` / `app.shell().sidecar(...)`) en builds release.

> ⚠️ Riesgos a validar temprano (ver `TAURI_EJECUCION_TEMP.md`): tamaño del
> instalador con `torch`/`opencv`/`faster-whisper`, acceso a cámara/micrófono por
> SO, y rutas a los modelos `.pt`/`.onnx`. Por eso el empaquetado queda fuera de
> este primer prototipo.
