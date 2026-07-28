"""Token de capacidad (opt-in) para proteger los endpoints privilegiados.

El backend solo escucha en localhost, pero cualquier proceso local podría llamar
a los endpoints de escritura (cambiar proveedor/keys, editar contenido, prender la
cámara). Este módulo aporta la lógica **pura** de autorización por token:

* si no hay token configurado (``HOLOGRAM_API_TOKEN`` vacío) → todo pasa, igual que
  antes (comportamiento histórico, sin romper la app actual);
* si hay token, las rutas privilegiadas requieren el header ``X-API-Token``
  correcto (comparación en tiempo constante); el control físico del holograma
  protege tanto lectura como escritura.

La integración (middleware FastAPI + cómo la shell de Tauri entrega el token al
frontend) se hace en ``main.py`` / la capa Tauri; aquí va solo lo testeable.
"""

from __future__ import annotations

import hmac
import secrets

# Rutas que modifican configuración/estado y, por tanto, requieren token cuando
# la autorización está activada. El panel de holograma es una capacidad física:
# tanto lectura como escritura requieren token cuando está activado.
PRIVILEGED_PREFIXES: tuple[str, ...] = (
    "/api/config",
    "/api/unev-content",
    "/api/camera",
    "/api/llm/test",
    "/api/train",
    "/api/speak",
    "/api/hologram",
)

_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def generate_token(nbytes: int = 32) -> str:
    """Genera un token de capacidad aleatorio y url-safe."""
    return secrets.token_urlsafe(nbytes)


def tokens_match(provided: str | None, expected: str | None) -> bool:
    """Compara tokens en tiempo constante. Sin ``expected``, la auth está apagada."""
    if not expected:
        return True
    if not provided:
        return False
    return hmac.compare_digest(str(provided), str(expected))


def is_path_privileged(path: str, method: str) -> bool:
    """¿La petición pertenece a una ruta protegida?"""
    if path.startswith("/api/hologram"):
        return True
    if (method or "").upper() in _SAFE_METHODS:
        return False
    return any(path.startswith(prefix) for prefix in PRIVILEGED_PREFIXES)


def request_authorized(
    path: str, method: str, provided_token: str | None, expected_token: str | None
) -> bool:
    """Decisión final de autorización para una petición.

    Pasa si: la auth está apagada (sin ``expected_token``), o la ruta no es
    privilegiada, o el token coincide.
    """
    if not expected_token:
        return True
    if not is_path_privileged(path, method):
        return True
    return tokens_match(provided_token, expected_token)
