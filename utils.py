import os
import platform
import re
import sys
import json

# --- Segmentación de texto para TTS (fuente única) ---
# Fuente única de segmentación TTS: ``call._split_into_chunks``,
# ``call.speak_streaming_from_llm`` y ``app.services.conversation``.
_CLAUSE_RE = re.compile(r"(?<=[.!?;:—,])\s+")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
# Primer fragmento más corto → el TTS arranca antes (latencia a primer audio).
_MIN_FIRST_CHUNK_LEN = 16
_MIN_SENTENCE_LEN = 28


def pop_ready_speech(buf: str, first_chunk: bool) -> tuple[list[str], str, bool]:
    """Extrae cláusulas/oraciones listas para TTS desde un buffer de stream.

    El primer fragmento usa cláusulas (coma/punto) con umbral bajo; el resto
    oraciones. Devuelve ``(piezas, buffer_restante, first_chunk)``.

    Si el *primer* separador deja un trozo corto (p. ej. «Hola,»), se prueba el
    siguiente (p. ej. el punto de la oración) en lugar de bloquear el stream
    hasta el final del turno.
    """
    ready: list[str] = []
    while buf:
        sep = _CLAUSE_RE if first_chunk else _SENTENCE_RE
        min_len = _MIN_FIRST_CHUNK_LEN if first_chunk else _MIN_SENTENCE_LEN
        matches = list(sep.finditer(buf))
        if not matches:
            break
        chosen = None
        for match in matches:
            head = buf[: match.end()].strip()
            if len(head) >= min_len:
                chosen = match
                break
        if chosen is None:
            # Hay puntuación pero aún no hay suficiente texto; esperar más tokens.
            break
        head = buf[: chosen.end()].strip()
        ready.append(head)
        buf = buf[chosen.end() :]
        first_chunk = False
    return ready, buf, first_chunk


def _env(name: str, default: str = "") -> str:
    """Helper to retrieve string environment variables."""
    return os.environ.get(name, default)

def _env_float(name: str, default: float = 0.0) -> float:
    """Helper to retrieve float environment variables."""
    val = os.environ.get(name)
    if val is None:
        return default
    try:
        return float(val)
    except ValueError:
        return default

def _env_int(name: str, default: int = 0) -> int:
    """Helper to retrieve integer environment variables."""
    val = os.environ.get(name)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError:
        return default

def _is_quiet() -> bool:
    """Returns True if HOLOGRAM_QUIET env var is set to 1/true/yes."""
    return os.environ.get("HOLOGRAM_QUIET", "").lower() in ("1", "true", "yes")


def configure_utf8_stdio():
    """Configures standard input/output streams to use UTF-8 encoding across systems."""
    if platform.system() == "Windows":
        # Force UTF-8 on Windows
        try:
            sys.stdin.reconfigure(encoding='utf-8')
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except AttributeError:
            pass


# --- Configuración: lectura/escritura segura de config.json y .env ---

def _atomic_write_text(path: str, text: str) -> None:
    """Escritura atómica: archivo temporal + ``os.replace``.

    Evita ``config.json`` / ``.env`` truncados si el proceso muere a mitad de
    escritura (corte de luz en el kiosko, cierre de la app, etc.).
    """
    directory = os.path.dirname(os.path.abspath(path)) or "."
    tmp = os.path.join(directory, f".{os.path.basename(path)}.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def load_config(path) -> dict:
    """Lee ``config.json`` de forma segura; devuelve ``{}`` si no existe/inválido."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def read_dotenv(path) -> dict:
    """Lee un ``.env`` (``KEY=VALUE``, ignora comentarios) en un dict."""
    data: dict[str, str] = {}
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    key, _, val = line.partition("=")
                    data[key.strip()] = val.split("#", 1)[0].strip()
    except (OSError, ValueError):
        return {}
    return data


def write_dotenv(path, mapping) -> None:
    """Escribe el ``.env`` de forma atómica desde un mapping (conserva orden)."""
    _atomic_write_text(path, "".join(f"{k}={v}\n" for k, v in mapping.items()))


def apply_config_to_env(config_data: dict) -> None:
    """Vuelca ``config.json`` a ``os.environ`` solo donde la variable no exista ya.

    Precedencia: ``.env`` (ya en ``os.environ``) gana; ``config.json`` es fallback.
    """
    for key, val in config_data.items():
        if val is not None and str(val) != "" and not os.environ.get(key):
            os.environ[key] = str(val)
