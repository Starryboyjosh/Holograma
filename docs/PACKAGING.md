# Empaquetado Windows-first (Fase C) — guía para el próximo agente

> **Estado: no completado en este entorno.** Requiere un runner Windows (y uno
> Linux) con la pila de ML instalada. Esta guía deja los pasos concretos y un
> `.spec` de partida; **todo debe validarse en el runner** antes de darlo por hecho.

## Objetivo
Hoy la shell de Tauri arranca el backend desde el código fuente:
`spawn_backend()` ejecuta `python3 main.py` (`frontend/src-tauri/src/lib.rs:57`),
sin `externalBin`. Una máquina Windows limpia necesitaría el repo + un venv. El
objetivo es un **sidecar PyInstaller** empaquetado por Tauri, para instalar y
arrancar sin repo ni Python manual.

## Restricción dura
**Fijar Python 3.11 o 3.12.** El entorno actual usa 3.14, donde `torch`,
`ultralytics`, `faster-whisper`, etc. pueden no tener wheels. Sin esto, ni el
backend ni PyInstaller funcionarán.

## Pasos
1. **Congelar el backend** con PyInstaller (modo `--onedir`, más fiable que
   `--onefile` para apps con `torch`/CUDA):
   ```bash
   pip install pyinstaller
   pyinstaller packaging/holograma.spec      # genera dist/holograma-backend/
   ```
   Incluir como *hidden imports* y *datas* lo que se carga dinámicamente:
   `uvicorn`, `fastapi`, `torch`, `ultralytics`, `faster_whisper`, `sounddevice`,
   `anthropic`, `openai`; y los datos `models/`, `static/`, `data/`, `skills/`,
   los `.onnx` de Piper y los `.pt` de YOLO.

2. **Renombrar el binario** al convenio de Tauri `externalBin` (sufijo del
   target-triple), p. ej. `holograma-backend-x86_64-pc-windows-msvc.exe` y
   `...-x86_64-unknown-linux-gnu`.

3. **Wire en `tauri.conf.json`** (`frontend/src-tauri/tauri.conf.json`):
   ```jsonc
   "bundle": {
     "active": true,
     "targets": "all",
     "externalBin": ["binaries/holograma-backend"],
     "resources": ["binaries/**/*"]
   }
   ```

4. **Cambiar `spawn_backend()`** (`lib.rs`) para lanzar el sidecar empaquetado
   (`tauri::process::Command::new_sidecar`) en producción y conservar
   `python3 main.py` solo en `dev` (`#[cfg(debug_assertions)]`). El backend ya
   acepta `--port`/CWD arbitrario (Regla de Oro A en `main.py`), así que no
   requiere cambios.

5. **Apagado limpio**: `kill_backend()` hoy hace `child.kill()` y deja huérfanos
   los subprocesos (Piper/audio). Matar el **árbol** de procesos (en Windows
   `taskkill /T /F /PID`, en Unix matar el grupo de proceso) o que el backend
   registre y cierre sus hijos al recibir SIGTERM.

6. **Directorios de datos del SO**: mover `config.json`, `.env`, caché de modelos
   y logs a `%APPDATA%`/XDG (no junto al `.exe`, que es de solo lectura tras
   instalar). Exponerlos vía `tauri::api::path`.

7. **Activos de modelos con checksum**: descargar/verificar `yolo26n.pt` y las
   voces Piper en el primer arranque si no vienen en el bundle (tamaño del
   instalador vs descarga diferida).

8. **CI Windows + Linux**: GitHub Actions que construya el sidecar + el instalador
   en ambos SO y corra los *smoke tests* de arranque.

## `.spec` de partida (validar en el runner)
Crear `packaging/holograma.spec` partiendo de esto (ajustar rutas/hiddenimports
según los errores reales de import en el runner):
```python
# packaging/holograma.spec  — PUNTO DE PARTIDA, requiere validación en Windows/Linux
# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

hidden = (
    collect_submodules("uvicorn")
    + collect_submodules("ultralytics")
    + ["torch", "faster_whisper", "sounddevice", "anthropic", "openai"]
)
datas = [("skills", "skills"), ("data", "data"), ("static", "static"), ("models", "models")]
datas += collect_data_files("ultralytics")

a = Analysis(["../main.py"], pathex=["."], hiddenimports=hidden, datas=datas)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, name="holograma-backend", console=True)
coll = COLLECT(exe, a.binaries, a.datas, name="holograma-backend")
```

## Aceptación
- Una máquina Windows limpia instala y arranca sin el repo ni un venv manual.
- Los desarrolladores Linux ejecutan el mismo comportamiento.
- Al cerrar la app no quedan procesos huérfanos (Piper/uvicorn/audio).
