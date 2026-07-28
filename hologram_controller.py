"""
=============================================================
 Controlador Python para Ventilador Holográfico MISSYOU
 Modelos: MSPJ65S4 / MSPJ70S4  (3 unidades en splicing)
 Protocolo: TCP - Puerto 50200
 Manual de referencia: Third-Party Control Protocol v1.1
=============================================================

CÓMO CONECTARSE:
  Opción A – WiFi directo del dispositivo:
    1. Conectar tu PC al WiFi "FXXXXXX" (contraseña: 12345678)
    2. La IP del holograma siempre es 10.10.10.1

  Opción B – Via router SpinDisplay (recomendado para 3 unidades):
    1. Conectar tu PC al WiFi "SpinDisplay" (contraseña: SpinDisplay)
    2. Descubrir la IP de cada unidad (ver función discover_devices())
    3. Usar esa IP en el constructor

ANTES DE USAR ESTE SCRIPT:
  1. En la APP HoloMissYou → Setting → Habilitar "Third party control"
  2. Asegurarte de estar en la misma red WiFi que el holograma
"""

import os
import queue
import socket
import threading
import time


class HologramFanController:
    """
    Controlador de ventilador holográfico MISSYOU via TCP.

    Reemplaza las funciones del control remoto IR y puede programar
    secuencias de videos automáticamente.

    Protocolo (del manual oficial, sección 3.14):
      - Cada comando es exactamente 3 bytes
      - Siempre empieza con 0x5B
      - Un solo comando por paquete TCP
    """

    # ── Comandos del protocolo oficial (página 61 del manual) ──────────
    CMD_START           = bytes([0x5B, 0x01, 0x00])  # Equivale a botón RUN
    CMD_SHUTDOWN        = bytes([0x5B, 0x02, 0x00])  # Equivale a botón STOP
    CMD_PAUSE           = bytes([0x5B, 0x03, 0x00])  # Equivale a botón Pause
    CMD_PLAY            = bytes([0x5B, 0x04, 0x00])  # Continuar reproducción
    CMD_LOOP_CURRENT    = bytes([0x5B, 0x05, 0x00])  # Repetir archivo actual
    # CMD_PLAY_FILE_N   = bytes([0x5B, 0x06, N])     # Ver método play_file()
    CMD_PREV_FILE       = bytes([0x5B, 0x07, 0x00])  # Archivo anterior
    CMD_NEXT_FILE       = bytes([0x5B, 0x08, 0x00])  # Archivo siguiente
    CMD_BRIGHTNESS_UP   = bytes([0x5B, 0x09, 0x00])  # Luminance+
    CMD_BRIGHTNESS_DOWN = bytes([0x5B, 0x0A, 0x00])  # Luminance-

    def __init__(
        self,
        ip: str = "10.10.10.1",
        port: int = 50200,
        timeout: float = 5.0,
        verbose: bool = True,
    ):
        """
        Args:
            ip:      IP del holograma. Default 10.10.10.1 (WiFi directo).
            port:    Puerto TCP. Siempre 50200 según el manual.
            timeout: Segundos de espera para la conexión.
            verbose: Si True, imprime cada comando enviado (útil para depurar
                     en consola; el manager lo desactiva para no llenar el log).
        """
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.verbose = verbose
        self._sock: socket.socket | None = None

    @property
    def is_connected(self) -> bool:
        """True si el socket TCP sigue abierto."""
        return self._sock is not None

    # ── Conexión ────────────────────────────────────────────────────────

    def connect(self) -> "HologramFanController":
        """Establece la conexión TCP con el holograma."""
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(self.timeout)
        try:
            self._sock.connect((self.ip, self.port))
            if self.verbose:
                print(f"✅ Conectado a {self.ip}:{self.port}")
        except (TimeoutError, ConnectionRefusedError, OSError) as e:
            self._sock = None
            raise ConnectionError(  # noqa: B904 - mensaje de usuario, traza original irrelevante
                f"No se pudo conectar a {self.ip}:{self.port}\n"
                f"  → Verifica que 'Third party control' esté ACTIVADO en la APP\n"
                f"  → Verifica que estés en la misma red WiFi\n"
                f"  Error original: {e}"
            )
        return self

    def disconnect(self):
        """Cierra la conexión TCP limpiamente."""
        if self._sock:
            self._sock.close()
            self._sock = None
            if self.verbose:
                print("🔌 Desconectado")

    def _send(self, command: bytes, label: str = ""):
        """
        Envía exactamente 3 bytes al dispositivo.
        El manual especifica: un solo comando por paquete TCP.
        """
        if not self._sock:
            raise ConnectionError("Sin conexión. Llama a connect() primero.")
        assert len(command) == 3, "Cada comando debe ser exactamente 3 bytes"
        self._sock.sendall(command)
        if self.verbose:
            hex_str = " ".join(f"0x{b:02X}" for b in command)
            print(f"  → Enviado [{hex_str}]  {label}")

    # ── Comandos de control (equivalentes al control remoto) ─────────────

    def start(self):
        """Enciende e inicia la rotación del holograma. [RUN]"""
        self._send(self.CMD_START, "START (RUN)")

    def shutdown(self):
        """Detiene la rotación y apaga el holograma. [STOP]"""
        self._send(self.CMD_SHUTDOWN, "SHUTDOWN (STOP)")

    def pause(self):
        """Pausa la reproducción del video. [Pause]"""
        self._send(self.CMD_PAUSE, "PAUSE")

    def play(self):
        """Reanuda la reproducción del video."""
        self._send(self.CMD_PLAY, "PLAY")

    def loop_current(self):
        """Activa el loop del archivo que está reproduciéndose actualmente."""
        self._send(self.CMD_LOOP_CURRENT, "LOOP CURRENT FILE")

    def play_file(self, index: int):
        """
        Salta directamente al video número N de la playlist.

        Args:
            index: Índice del archivo (0 = primer video, 1 = segundo, etc.)
                   Rango válido: 0–255.

        Ejemplo:
            fan.play_file(0)   # Primer video
            fan.play_file(2)   # Tercer video
        """
        if not 0 <= index <= 255:
            raise ValueError(f"El índice debe estar entre 0 y 255. Recibido: {index}")
        cmd = bytes([0x5B, 0x06, index])
        self._send(cmd, f"PLAY FILE #{index}")

    def next_file(self):
        """Avanza al siguiente archivo en la playlist. [▶|]"""
        self._send(self.CMD_NEXT_FILE, "NEXT FILE")

    def prev_file(self):
        """Regresa al archivo anterior en la playlist. [|◀]"""
        self._send(self.CMD_PREV_FILE, "PREV FILE")

    def brightness_up(self):
        """Aumenta el brillo de la pantalla. [+]"""
        self._send(self.CMD_BRIGHTNESS_UP, "BRIGHTNESS UP")

    def brightness_down(self):
        """Reduce el brillo de la pantalla. [-]"""
        self._send(self.CMD_BRIGHTNESS_DOWN, "BRIGHTNESS DOWN")

    # ── Context manager (with statement) ────────────────────────────────

    def __enter__(self):
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False  # No suprimir excepciones


# ── Utilidades ──────────────────────────────────────────────────────────

def discover_devices(subnet: str = "192.168.1", port: int = 50200, timeout: float = 0.5) -> list:
    """
    Escanea la red local buscando hologramas MISSYOU en el puerto 50200.

    Útil cuando el holograma está conectado al router SpinDisplay y
    no sabes su IP exacta.

    Args:
        subnet:  Los primeros 3 octetos de la subred (e.g. "192.168.1")
        port:    Puerto TCP a escanear (default 50200)
        timeout: Segundos de espera por host

    Returns:
        Lista de IPs que respondieron en el puerto 50200
    """
    import concurrent.futures
    print(f"🔍 Escaneando {subnet}.1-254 en puerto {port} de forma concurrente...")
    found = []

    def check_ip(ip):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            result = s.connect_ex((ip, port))
            s.close()
            if result == 0:
                print(f"  ✅ Holograma encontrado en {ip}")
                return ip
        except Exception:
            pass
        return None

    ips = [f"{subnet}.{i}" for i in range(1, 255)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        results = executor.map(check_ip, ips)
        for res in results:
            if res:
                found.append(res)

    if not found:
        print("  ❌ No se encontraron dispositivos en esa subred.")
    return found


class HologramArrayTester:
    """Envía un clip independiente a cada holograma de un arreglo.

    Este flujo es deliberadamente manual: cada unidad tiene su propia conexión
    TCP y su propio índice de playlist. Sirve para validar el cableado y el
    orden de videos antes de conectar el cambio de estado de la IA.
    """

    def __init__(
        self,
        assignments: list[tuple[str, int]],
        port: int = 50200,
        command_gap: float = 0.25,
        verbose: bool = True,
    ):
        if not assignments:
            raise ValueError("Se requiere al menos una asignación IP:índice.")
        self.assignments = assignments
        self.port = port
        self.command_gap = command_gap
        self.verbose = verbose
        self._fans: list[tuple[HologramFanController, int]] = []

    def run(self) -> list[dict[str, object]]:
        """Conecta cada unidad, reproduce su índice y devuelve el resultado."""
        results: list[dict[str, object]] = []
        try:
            for ip, index in self.assignments:
                fan = HologramFanController(ip=ip, port=self.port, verbose=self.verbose)
                try:
                    fan.connect()
                    fan.start()
                    time.sleep(self.command_gap)
                    fan.play_file(index)
                    self._fans.append((fan, index))
                    results.append({"ip": ip, "index": index, "status": "ok"})
                except (ConnectionError, OSError, ValueError) as error:
                    fan.disconnect()
                    results.append({"ip": ip, "index": index, "status": "error", "message": str(error)})
        finally:
            self.close()
        return results

    def close(self):
        """Cierra las conexiones abiertas sin apagar unidades ya probadas."""
        for fan, _index in self._fans:
            fan.disconnect()
        self._fans.clear()


# ══════════════════════════════════════════════════════════════════════════
#  INTEGRACIÓN CON LA IA — Manager de estados (thread-safe, fail-soft)
# ══════════════════════════════════════════════════════════════════════════

# Mapeo de estado de la IA → índice de clip en la playlist del holograma.
# (Ver Holograma_MISSYOU_Referencia_IA.pdf, sección 3 "Notas para el brainstorming")
#   Clip 0 — loop en espera        Clip 2 — boca / onda en movimiento
#   Clip 1 — animación de escucha   Clip 3 — animación de proceso
#
# IMPORTANTE: estos índices son el ORDEN en que cargaste los clips en la app
# HoloMissYou. El número N del comando `0x5B 0x06 N` es la posición del archivo
# en la playlist del dispositivo, no el nombre del archivo. Si cargas los clips
# en otro orden, redefine el mapeo con las variables HOLOGRAM_CLIP_* (ver
# resolve_state_clips) para que cada estado de la IA apunte al clip correcto.
DEFAULT_STATE_CLIPS = {
    "idle": 0,
    "listening": 1,
    "speaking": 2,
    "thinking": 3,
}


def resolve_state_clips(env: dict | None = None) -> dict:
    """
    Construye el mapeo estado→índice respetando el orden real de la playlist.

    Lee, por cada estado, una variable de entorno opcional que sobreescribe el
    índice por defecto. Así el operador alinea el mapeo con el ORDEN en que cargó
    los clips en la app HoloMissYou (que es lo que fija el N de `0x5B 0x06 N`):

        HOLOGRAM_CLIP_IDLE       (default 0)
        HOLOGRAM_CLIP_LISTENING  (default 1)
        HOLOGRAM_CLIP_SPEAKING   (default 2)
        HOLOGRAM_CLIP_THINKING   (default 3)

    Pura y env-inyectable (para tests): pasa un dict en `env` o usa os.environ.
    Un valor inválido (no entero o fuera de 0–255) se ignora y conserva el
    default, registrando un aviso — nunca rompe el arranque de la IA.
    """
    if env is None:
        env = os.environ
    clips = dict(DEFAULT_STATE_CLIPS)
    for state in clips:
        raw = str(env.get(f"HOLOGRAM_CLIP_{state.upper()}", "")).strip()
        if not raw:
            continue
        try:
            index = int(raw)
        except ValueError:
            print(f"[Holograma] HOLOGRAM_CLIP_{state.upper()}={raw!r} no es un entero; usando {clips[state]}.")
            continue
        if not 0 <= index <= 255:
            print(f"[Holograma] HOLOGRAM_CLIP_{state.upper()}={index} fuera de 0–255; usando {clips[state]}.")
            continue
        clips[state] = index
    return clips


class HologramStateManager:
    """
    Puente thread-safe entre los estados de la IA y los clips del holograma.

    La IA cambia de estado desde varios hilos a la vez (voice loop, worker de
    TTS, hilo de cámara). Este manager encola los cambios y un único hilo en
    segundo plano los aplica al dispositivo respetando la regla del protocolo:
    un comando por paquete TCP, con ~0.2 s de separación entre envíos.

    Es *fail-soft*: si no hay IP configurada o el dispositivo no responde,
    nunca bloquea ni propaga excepciones hacia la IA — solo registra avisos
    y reintenta la conexión en segundo plano. Así la IA corre idéntica con o
    sin holograma físico conectado.

    Uso:
        holo = create_hologram_manager()   # lee HOLOGRAM_TCP_IP del entorno
        holo.start()                       # conecta + RUN + clip idle
        holo.set_state("listening")        # no bloqueante, thread-safe
        ...
        holo.close()                       # apaga y desconecta
    """

    def __init__(
        self,
        ip: str | None = None,
        port: int = 50200,
        state_clips: dict | None = None,
        min_send_gap: float = 0.25,
        verbose: bool = False,
    ):
        self.ip = ip
        self.port = port
        self.state_clips = state_clips or DEFAULT_STATE_CLIPS
        self.min_send_gap = min_send_gap
        self.verbose = verbose
        self.enabled = bool(ip)

        self._queue: queue.Queue[str | None] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._fan: HologramFanController | None = None
        self._last_state: str | None = None
        self._desired_state: str | None = None
        self._last_send = 0.0
        self._reconnect_delay = 1.0
        self._next_reconnect = 0.0
        self._stop = threading.Event()
        self._fan_lock = threading.RLock()

    # ── API pública (la llama la IA desde cualquier hilo) ────────────────

    @property
    def is_connected(self) -> bool:
        """True cuando el gestor automático tiene un socket TCP activo."""
        with self._fan_lock:
            return self._fan is not None and self._fan.is_connected

    def configure(self, ip: str, port: int = 50200):
        """Aplica un destino TCP nuevo y activa el cambio automático de clips."""
        ip = ip.strip()
        if not ip:
            raise ValueError("La dirección IP del holograma es obligatoria.")
        if not 1 <= port <= 65535:
            raise ValueError("El puerto debe estar entre 1 y 65535.")

        if (
            self.enabled
            and self.ip == ip
            and self.port == port
            and self._thread is not None
            and self._thread.is_alive()
        ):
            self.set_state("idle")
            return

        self.close()
        self.ip = ip
        self.port = port
        self.enabled = True
        self._queue = queue.Queue()
        self._last_state = None
        self._desired_state = None
        self._last_send = 0.0
        self._reconnect_delay = 1.0
        self._next_reconnect = 0.0
        self.start()

    def disable(self):
        """Desconecta el dispositivo y desactiva los reintentos automáticos."""
        self.close()
        self.enabled = False
        self.ip = None
        self._queue = queue.Queue()

    def execute(self, command: str, index: int | None = None):
        """Compatibilidad con la API: ejecuta un comando usando la conexión compartida."""
        with self._fan_lock:
            if not self.enabled or not self._ensure_connected():
                raise ConnectionError("El holograma no está conectado.")

            commands = {
                "start": self._fan.start,
                "shutdown": self._fan.shutdown,
                "pause": self._fan.pause,
                "play": self._fan.play,
                "loop_current": self._fan.loop_current,
                "next_file": self._fan.next_file,
                "prev_file": self._fan.prev_file,
                "brightness_up": self._fan.brightness_up,
                "brightness_down": self._fan.brightness_down,
            }
            if command == "play_file":
                if index is None:
                    raise ValueError("Se requiere 'index' para play_file.")
                self._fan.play_file(index)
                self._last_state = None
            elif command in commands:
                commands[command]()
            else:
                raise ValueError(f"Comando desconocido: {command}")
            self._last_send = time.monotonic()

    def start(self):
        """Arranca el hilo de control y deja el holograma en idle. No-op si está deshabilitado."""
        if not self.enabled or (self._thread is not None and self._thread.is_alive()):
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name="hologram-state", daemon=True
        )
        self._thread.start()
        self.set_state("idle")

    def set_state(self, state: str):
        """Solicita un cambio de estado del holograma. No bloquea ni lanza excepciones."""
        if not self.enabled:
            return
        if state not in self.state_clips:
            if self.verbose:
                print(f"[Holograma] Estado desconocido ignorado: {state!r}")
            return
        self._desired_state = state
        self._queue.put(state)

    def close(self):
        """Detiene el hilo, apaga el giro y cierra la conexión limpiamente."""
        if self._thread is None and self._fan is None:
            return
        self._stop.set()
        self._queue.put(None)  # despierta al worker
        if self._thread is not None:
            self._thread.join(timeout=6.0)
            self._thread = None
        with self._fan_lock:
            if self._fan is not None:
                try:
                    self._fan.shutdown()
                except OSError:
                    pass
                self._fan.disconnect()
                self._fan = None
            self._last_state = None
            self._desired_state = None

    # ── Hilo en segundo plano ────────────────────────────────────────────

    def _run(self):
        while not self._stop.is_set():
            try:
                state = self._queue.get(timeout=0.5)
            except queue.Empty:
                # Si una conexión falló, volver a intentar el último estado
                # solicitado. _ensure_connected aplica el backoff exponencial.
                state = self._desired_state
            # Coalescer: si se acumularon varios cambios, quedarnos con el último.
            while True:
                try:
                    state = self._queue.get_nowait()
                except queue.Empty:
                    break
            if state is None:
                if self._stop.is_set():  # sentinela de cierre
                    break
                continue
            self._apply(state)

    def _apply(self, state: str):
        with self._fan_lock:
            if state == self._last_state:
                return  # dedupe: no reenviar el clip que ya está en pantalla
            if not self._ensure_connected():
                return  # sin conexión; se reintentará en el próximo cambio de estado
            clip = self.state_clips[state]
            # Respetar la separación mínima entre paquetes (regla del protocolo).
            gap = self.min_send_gap - (time.monotonic() - self._last_send)
            if gap > 0:
                time.sleep(gap)
            try:
                self._fan.play_file(clip)
                self._last_send = time.monotonic()
                self._last_state = state
                if self.verbose:
                    print(f"[Holograma] Estado → {state} (clip {clip})")
            except OSError as e:
                print(f"[Holograma] Error enviando estado '{state}': {e}. Reintentaré.")
                self._drop_connection()

    # ── Conexión con reintentos y backoff exponencial ────────────────────

    def _ensure_connected(self) -> bool:
        if self._fan is not None and self._fan.is_connected:
            return True
        now = time.monotonic()
        if now < self._next_reconnect:
            return False
        try:
            fan = HologramFanController(self.ip, self.port, verbose=self.verbose)
            fan.connect()
            fan.start()  # botón RUN: arranca el giro del ventilador
            self._fan = fan
            self._reconnect_delay = 1.0
            self._last_state = None  # forzar reenvío del estado al reconectar
            print(f"[Holograma] Conectado a {self.ip}:{self.port}")
            return True
        except (ConnectionError, OSError) as e:
            self._fan = None
            self._next_reconnect = now + self._reconnect_delay
            print(
                f"[Holograma] No se pudo conectar ({e}). "
                f"Reintento en {self._reconnect_delay:.0f}s."
            )
            self._reconnect_delay = min(self._reconnect_delay * 2, 30.0)
            return False

    def _drop_connection(self):
        if self._fan is not None:
            self._fan.disconnect()
            self._fan = None
        self._last_state = None
        self._next_reconnect = time.monotonic() + self._reconnect_delay
        self._reconnect_delay = min(self._reconnect_delay * 2, 30.0)


def create_hologram_manager(verbose: bool = False):
    """
    Construye un HologramStateManager a partir de variables de entorno.

    Variables:
        HOLOGRAM_TCP_IP      IP del holograma. Si NO está definida, el manager
                             queda deshabilitado (no-op) y la IA corre igual que
                             siempre, sin tocar ningún dispositivo físico.
        HOLOGRAM_TCP_PORT    Puerto TCP (default 50200).
        HOLOGRAM_TCP_VERBOSE "1" para registrar cada comando enviado.

    Returns:
        HologramStateManager (posiblemente deshabilitado / no-op).
    """
    # WAVE-001 mantiene esta fábrica como punto de compatibilidad, pero ahora
    # devuelve un adaptador cuyo "top" es gestionado por el director único.
    # HologramStateManager permanece público para scripts/consumidores antiguos.
    from app.hologram.compatibility import create_legacy_hologram_manager

    manager = create_legacy_hologram_manager(
        verbose=verbose or os.getenv("HOLOGRAM_TCP_VERBOSE", "").strip() == "1"
    )
    if not manager.enabled:
        print(
            "[Holograma] HOLOGRAM_TCP_IP no configurada; control del dispositivo "
            "físico DESACTIVADO (la IA corre en modo solo-software)."
        )
    return manager


# ══════════════════════════════════════════════════════════════════════════
#  EJEMPLOS DE USO
# ══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":

    # ── Paso 0: Configurar la IP ─────────────────────────────────────────
    #
    # OPCIÓN A: Conectado directo al WiFi del holograma (FXXXXXX)
    FAN_IP = "10.10.10.1"
    #
    # OPCIÓN B: Conectado al router SpinDisplay
    # Ejecuta primero: discover_devices("192.168.1")
    # y reemplaza con la IP encontrada:
    # FAN_IP = "192.168.1.105"

    print("=" * 55)
    print("  Controlador MISSYOU Holographic Fan")
    print("=" * 55)

    # ── Ejemplo 1: Operación básica ──────────────────────────────────────
    print("\n📌 Ejemplo 1: Control básico")
    with HologramFanController(ip=FAN_IP) as fan:
        time.sleep(0.3)

        fan.start()            # Encender (= botón RUN del control)
        time.sleep(1.0)

        fan.play_file(0)       # Reproducir primer video de la playlist
        time.sleep(5.0)

        fan.play_file(1)       # Cambiar al segundo video
        time.sleep(5.0)

        fan.next_file()        # Siguiente video
        time.sleep(5.0)

        fan.pause()            # Pausar (= botón Pause del control)
        time.sleep(2.0)

        fan.play()             # Reanudar
        time.sleep(3.0)

        fan.brightness_up()    # Subir brillo (= botón + del control)
        time.sleep(0.5)
        fan.brightness_up()

    # ── Ejemplo 2: Secuencia programada (playlist automática) ────────────
    print("\n📌 Ejemplo 2: Secuencia automática de 3 videos")

    PLAYLIST = [
        {"index": 0, "nombre": "intro_robot.mp4",    "duracion": 10},
        {"index": 1, "nombre": "proyecto_wro.mp4",   "duracion": 15},
        {"index": 2, "nombre": "logo_itee.mp4",      "duracion": 8},
    ]

    with HologramFanController(ip=FAN_IP) as fan:
        fan.start()
        time.sleep(1.0)

        for video in PLAYLIST:
            print(f"\n  🎬 Reproduciendo: {video['nombre']} ({video['duracion']}s)")
            fan.play_file(video["index"])
            time.sleep(video["duracion"])

        fan.shutdown()

    # ── Ejemplo 3: Descubrimiento de dispositivos en red ─────────────────
    # (descomenta para usar con el router SpinDisplay)
    #
    # print("\n📌 Ejemplo 3: Buscar hologramas en la red")
    # dispositivos = discover_devices(subnet="192.168.1")
    # if dispositivos:
    #     ip_principal = dispositivos[0]
    #     with HologramFanController(ip=ip_principal) as fan:
    #         fan.play_file(0)

    print("\n✅ Script finalizado.")
