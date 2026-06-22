// Shell de Tauri para Holograma UNEV.
//
// Responsabilidades (según TAURI_EJECUCION_TEMP.md):
//   1. Elegir un puerto TCP libre.
//   2. Arrancar el backend FastAPI (en dev: `python main.py --port <port>`).
//   3. Hacer healthcheck contra /api/config antes de mostrar la ventana.
//   4. Exponer al frontend el comando `get_backend_url`.
//   5. Cerrar el backend limpiamente al salir.
//
// El healthcheck usa únicamente la librería estándar (TcpStream + GET crudo) para
// no añadir dependencias HTTP pesadas a un prototipo.

use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::Mutex;
use std::time::{Duration, Instant};

use tauri::{Manager, RunEvent, State};

/// URL del backend + proceso hijo, gestionados por Tauri como estado compartido.
struct BackendState {
    url: String,
    child: Mutex<Option<Child>>,
}

/// El frontend (lib/backend.ts) llama a esto para construir todas las URLs de
/// API/WebSocket/medios apuntando al puerto real elegido en runtime.
#[tauri::command]
fn get_backend_url(state: State<BackendState>) -> String {
    state.url.clone()
}

/// Pide al SO un puerto efímero libre en localhost.
fn free_port() -> u16 {
    TcpListener::bind("127.0.0.1:0")
        .and_then(|l| l.local_addr())
        .map(|addr| addr.port())
        .unwrap_or(8000)
}

/// Directorio del proyecto (donde vive main.py). Permite override por entorno
/// para un futuro empaquetado; en dev se deduce desde el manifiesto del crate
/// (frontend/src-tauri -> ../.. = raíz del proyecto).
fn project_root() -> PathBuf {
    if let Ok(dir) = std::env::var("HOLOGRAM_BACKEND_DIR") {
        return PathBuf::from(dir);
    }
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
}

/// Arranca el backend de Python como proceso externo (modo desarrollo).
/// El binario PyInstaller (sidecar) será el camino de producción más adelante.
fn spawn_backend(port: u16) -> Option<Child> {
    let root = project_root();
    let python = std::env::var("HOLOGRAM_PYTHON").unwrap_or_else(|_| "python3".to_string());
    match Command::new(&python)
        .arg("main.py")
        .arg("--port")
        .arg(port.to_string())
        .current_dir(&root)
        .spawn()
    {
        Ok(child) => Some(child),
        Err(err) => {
            eprintln!("[holograma] no se pudo arrancar el backend ({python} main.py): {err}");
            None
        }
    }
}

/// GET /api/config crudo: ¿responde el backend con 200?
fn backend_ready(port: u16) -> bool {
    let Ok(mut stream) = TcpStream::connect(("127.0.0.1", port)) else {
        return false;
    };
    let _ = stream.set_read_timeout(Some(Duration::from_millis(800)));
    let req = "GET /api/config HTTP/1.0\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n";
    if stream.write_all(req.as_bytes()).is_err() {
        return false;
    }
    let mut buf = [0u8; 64];
    match stream.read(&mut buf) {
        Ok(n) if n > 0 => String::from_utf8_lossy(&buf[..n]).contains("200"),
        _ => false,
    }
}

/// Espera (con tope) a que el backend esté listo. Devuelve el control igualmente
/// al expirar: el frontend reintenta sus fetch/WebSocket si aún no responde.
fn wait_for_backend(port: u16, timeout: Duration) {
    let deadline = Instant::now() + timeout;
    while Instant::now() < deadline {
        if backend_ready(port) {
            return;
        }
        std::thread::sleep(Duration::from_millis(300));
    }
    eprintln!("[holograma] el backend no respondió a tiempo; mostrando la UI de todos modos");
}

/// Mata el proceso hijo del backend (cierre limpio al salir).
fn kill_backend(state: &BackendState) {
    if let Ok(mut guard) = state.child.lock() {
        if let Some(mut child) = guard.take() {
            let _ = child.kill();
            let _ = child.wait();
        }
    }
}

pub fn run() {
    let port = free_port();
    let child = spawn_backend(port);

    // Solo esperamos si el backend realmente arrancó.
    if child.is_some() {
        wait_for_backend(port, Duration::from_secs(20));
    }

    let url = format!("http://127.0.0.1:{port}");
    println!("[holograma] backend en {url}");

    tauri::Builder::default()
        .plugin(tauri_plugin_window_state::Builder::default().build())
        .manage(BackendState {
            url,
            child: Mutex::new(child),
        })
        .invoke_handler(tauri::generate_handler![get_backend_url])
        .build(tauri::generate_context!())
        .expect("error al construir la aplicación Tauri")
        .run(|app_handle, event| {
            if let RunEvent::ExitRequested { .. } = event {
                if let Some(state) = app_handle.try_state::<BackendState>() {
                    kill_backend(&state);
                }
            }
        });
}
