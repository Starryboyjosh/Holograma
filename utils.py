import os
import platform
import sys


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
