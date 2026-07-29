"""Detección de disponibilidad de la navegación web.

Responde a una sola pregunta: **¿tiene sentido ofrecerle `browse_web_page` al
modelo en este turno?** Si no, la herramienta ni siquiera se le presenta, de
modo que no puede intentar consultar internet.

Dos condiciones, ambas necesarias:

1. **Lightpanda responde** — el contenedor puede estar caído o reiniciándose.
2. **Hay internet** — el kiosko puede estar sin red.

El caso crítico es el segundo con un modelo local (Ollama): ahí el LLM sigue
funcionando perfectamente aunque no haya red, así que sin esta comprobación
intentaría navegar y solo conseguiría timeouts y una respuesta confusa. Con un
modelo en la nube el punto es discutible (sin red tampoco se alcanza el
proveedor), pero la comprobación es la misma y no estorba.

Se cachea con TTL para no sondear en cada turno. El TTL negativo es más corto
que el positivo: si vuelve la red, el kiosko debe notarlo rápido.
"""

from __future__ import annotations

import socket
import threading
import time
from urllib.parse import urlparse

from utils import _env, _env_float

# Destinos del sondeo de internet: DNS públicos por TCP/53. Se prefiere una IP
# literal a un dominio para que un DNS caído no se confunda con "sin internet".
DEFAULT_CONNECTIVITY_HOSTS = "1.1.1.1:53,8.8.8.8:53"

# Positivo largo (la red estable no necesita re-sondeo), negativo corto (para
# reaccionar pronto cuando la conexión vuelve).
DEFAULT_TTL_OK = 30.0
DEFAULT_TTL_FAIL = 10.0

_lock = threading.Lock()
_cache: dict[str, object] = {"checked_at": 0.0, "available": False, "reason": ""}


def _connectivity_hosts() -> list[tuple[str, int]]:
    raw = _env("HOLOGRAM_CONNECTIVITY_HOSTS", DEFAULT_CONNECTIVITY_HOSTS)
    hosts: list[tuple[str, int]] = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        host, _, port = item.rpartition(":")
        if not host:
            # Sin puerto explícito: se asume DNS.
            host, port = item, "53"
        try:
            hosts.append((host, int(port)))
        except ValueError:
            continue
    return hosts


def _probe_timeout() -> float:
    return _env_float("HOLOGRAM_CONNECTIVITY_TIMEOUT", 2.0)


def _tcp_reachable(host: str, port: int, timeout: float) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def internet_reachable(timeout: float | None = None) -> bool:
    """True si al menos uno de los destinos de sondeo acepta conexión TCP."""
    limit = timeout if timeout is not None else _probe_timeout()
    for host, port in _connectivity_hosts():
        if _tcp_reachable(host, port, limit):
            return True
    return False


def lightpanda_reachable(timeout: float | None = None) -> bool:
    """True si el puerto CDP de Lightpanda acepta conexión TCP.

    Solo comprueba el socket, no el handshake WebSocket: basta para descartar
    "contenedor caído" sin pagar el coste de abrir una sesión CDP.
    """
    limit = timeout if timeout is not None else _probe_timeout()
    parsed = urlparse(_env("LIGHTPANDA_CDP_URL", "ws://127.0.0.1:9222"))
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 9222
    return _tcp_reachable(host, port, limit)


def web_tools_available(force: bool = False) -> tuple[bool, str]:
    """¿Se le puede ofrecer la herramienta web al modelo?

    Devuelve ``(disponible, motivo)``. El motivo es texto corto para logs y
    para que el frontend pueda explicar por qué no hay navegación.
    """
    if _web_tools_disabled():
        return False, "deshabilitado por configuración (HOLOGRAM_WEB_TOOLS=off)"

    now = time.monotonic()
    with _lock:
        checked_at = float(_cache["checked_at"])  # type: ignore[arg-type]
        available = bool(_cache["available"])
        ttl = DEFAULT_TTL_OK if available else DEFAULT_TTL_FAIL
        if not force and checked_at and (now - checked_at) < ttl:
            return available, str(_cache["reason"])

    # El sondeo se hace FUERA del lock: son syscalls de red con timeout y no
    # deben serializar a otros turnos.
    if not lightpanda_reachable():
        result, reason = False, "Lightpanda no responde (¿contenedor caído?)"
    elif not internet_reachable():
        result, reason = False, "sin conexión a internet"
    else:
        result, reason = True, "ok"

    with _lock:
        _cache["checked_at"] = time.monotonic()
        _cache["available"] = result
        _cache["reason"] = reason
    return result, reason


def _web_tools_disabled() -> bool:
    return _web_tools_mode() == "off"


def _web_tools_mode() -> str:
    """``auto`` (default), ``always`` u ``off``.

    - ``auto``   : se ofrece la herramienta solo si el prompt parece pedir web.
    - ``always`` : se ofrece en todos los turnos (más latencia).
    - ``off``    : nunca.
    """
    mode = _env("HOLOGRAM_WEB_TOOLS", "auto").strip().lower()
    return mode if mode in ("auto", "always", "off") else "auto"


def reset_cache() -> None:
    """Invalida la caché del sondeo (tests y cambios de configuración en vivo)."""
    with _lock:
        _cache["checked_at"] = 0.0
        _cache["available"] = False
        _cache["reason"] = ""
