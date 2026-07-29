"""Motor de navegación web de Holograma sobre Lightpanda (CDP).

Lightpanda es el motor **único y definitivo**: no hay fallback a ``requests``,
Playwright ni a otro navegador. Si el servicio no responde, la consulta falla
con un mensaje accionable que el orquestador entrega al LLM como resultado de
la herramienta; el modelo decide qué decirle al usuario.

Protocolo
---------
Se habla CDP (Chrome DevTools Protocol) directamente por WebSocket contra
``ws://127.0.0.1:9222``, sin Puppeteer ni dependencias de Node:

1. ``Target.createTarget``    -> abre una pestaña en blanco
2. ``Target.attachToTarget``  -> obtiene ``sessionId`` (modo *flatten*)
3. ``Page.navigate``          -> carga la URL
4. sondeo de ``document.readyState`` hasta ``interactive``/``complete``
5. ``Runtime.evaluate``       -> limpia el DOM y extrae el texto
6. ``Target.closeTarget``     -> cierra la pestaña (siempre, en ``finally``)

Se sondea ``readyState`` en lugar de esperar ``Page.loadEventFired`` porque la
entrega de eventos varía entre builds *nightly* de Lightpanda; el sondeo es
determinista y respeta el mismo deadline.

Timeouts agresivos (Lightpanda arranca en milisegundos, no en segundos): si
algo tarda, es un fallo real, no lentitud normal.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from urllib.parse import urlparse

from utils import _env, _env_float, _env_int

# Conexión CDP. En Docker Compose el host es el nombre del servicio
# (``ws://lightpanda:9222``); en local, el loopback.
DEFAULT_CDP_URL = "ws://127.0.0.1:9222"

# Recorte del texto extraído. ~8000 caracteres (~2000 tokens) mantienen sana la
# ventana de contexto de los modelos locales pequeños de Ollama.
DEFAULT_MAX_CHARS = 8000

# Etiquetas que nunca aportan contenido legible y sí mucho ruido de tokens.
_DROPPED_SELECTORS = (
    "script",
    "style",
    "noscript",
    "template",
    "iframe",
    "svg",
    "canvas",
    "nav",
    "footer",
    "header",
    "aside",
    "form",
)

# JS de extracción. Se ejecuta dentro de la página ya cargada:
#   1. elimina el ruido estructural
#   2. prefiere <main>/<article> (el cuerpo real del contenido)
#   3. normaliza espacios para no gastar tokens en whitespace
_EXTRACT_JS_TEMPLATE = """
(() => {
  const drop = __DROPPED_SELECTORS__;
  for (const sel of drop) {
    for (const el of document.querySelectorAll(sel)) el.remove();
  }
  const root =
    document.querySelector('main') ||
    document.querySelector('article') ||
    document.body;
  const raw = root ? (root.innerText || root.textContent || '') : '';
  const text = raw
    .replace(/[ \\t\\u00a0]+/g, ' ')
    .replace(/\\n{3,}/g, '\\n\\n')
    .trim();
  return JSON.stringify({
    title: document.title || '',
    url: document.location ? document.location.href : '',
    text: text,
  });
})()
"""

# Sustitución por token en vez de %/format: el JS está lleno de llaves y
# cualquiera de los dos mecanismos las interpretaría como campos de formato.
_EXTRACT_JS = _EXTRACT_JS_TEMPLATE.replace(
    "__DROPPED_SELECTORS__", json.dumps(_DROPPED_SELECTORS)
)


class LightpandaError(Exception):
    """Fallo al navegar con Lightpanda (conexión, CDP o página)."""


class LightpandaTimeout(LightpandaError):
    """Lightpanda no respondió dentro del tiempo permitido."""


@dataclass(frozen=True)
class PageContent:
    """Resultado de una navegación."""

    url: str
    title: str
    text: str
    truncated: bool

    def as_prompt_context(self) -> str:
        """Formatea el contenido para reinyectarlo al LLM."""
        header = f"Contenido extraído de {self.url}"
        if self.title:
            header += f"\nTítulo: {self.title}"
        body = self.text or "(la página no contenía texto legible)"
        if self.truncated:
            body += (
                f"\n\n[...contenido recortado a {len(self.text)} caracteres "
                "para preservar la ventana de contexto]"
            )
        return f"{header}\n\n{body}"


def _cdp_url() -> str:
    return _env("LIGHTPANDA_CDP_URL", DEFAULT_CDP_URL).rstrip("/")


def _max_chars() -> int:
    value = _env_int("LIGHTPANDA_MAX_CHARS", DEFAULT_MAX_CHARS)
    return value if value > 0 else DEFAULT_MAX_CHARS


def _connect_timeout() -> float:
    return _env_float("LIGHTPANDA_CONNECT_TIMEOUT", 5.0)


def _command_timeout() -> float:
    return _env_float("LIGHTPANDA_COMMAND_TIMEOUT", 10.0)


def _navigation_timeout() -> float:
    return _env_float("LIGHTPANDA_NAVIGATION_TIMEOUT", 15.0)


def _validate_url(url: str) -> str:
    """Acepta solo http/https absolutos; el LLM a veces alucina esquemas."""
    candidate = (url or "").strip()
    if not candidate:
        raise LightpandaError("La herramienta necesita una URL; llegó vacía.")
    parsed = urlparse(candidate)
    if parsed.scheme not in ("http", "https"):
        raise LightpandaError(
            f"Esquema de URL no permitido: '{parsed.scheme or 'sin esquema'}'. "
            "Usa una URL http:// o https:// completa."
        )
    if not parsed.netloc:
        raise LightpandaError(f"URL incompleta (falta el dominio): {candidate}")
    return candidate


class _CdpConnection:
    """Cliente CDP síncrono mínimo sobre ``websockets.sync``.

    Solo implementa lo que necesita el motor: envío de comandos con ``id`` y
    espera de la respuesta correspondiente, descartando los eventos que
    Lightpanda emite por el mismo socket.
    """

    def __init__(self, url: str, *, connect_timeout: float, command_timeout: float):
        try:
            from websockets.sync.client import connect
        except ImportError as error:  # pragma: no cover - dependencia declarada
            raise LightpandaError(
                "Falta la dependencia 'websockets'. Instálala con: "
                "pip install -r requirements.txt"
            ) from error

        self._command_timeout = command_timeout
        self._next_id = 0
        try:
            self._ws = connect(
                url,
                open_timeout=connect_timeout,
                close_timeout=2.0,
                max_size=None,
            )
        except Exception as error:
            raise LightpandaError(
                f"No pude conectar con Lightpanda en {url}: {error}. "
                "Verifica que el servicio esté arriba "
                "(docker compose up -d lightpanda)."
            ) from error

    def call(
        self,
        method: str,
        params: dict | None = None,
        *,
        session_id: str | None = None,
        timeout: float | None = None,
    ) -> dict:
        self._next_id += 1
        message_id = self._next_id
        payload: dict = {"id": message_id, "method": method, "params": params or {}}
        if session_id:
            payload["sessionId"] = session_id

        try:
            self._ws.send(json.dumps(payload))
        except Exception as error:
            raise LightpandaError(f"CDP {method}: se cortó el envío: {error}") from error

        deadline = time.monotonic() + (timeout or self._command_timeout)
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise LightpandaTimeout(
                    f"Lightpanda no respondió a {method} en "
                    f"{timeout or self._command_timeout:.0f}s."
                )
            try:
                raw = self._ws.recv(timeout=remaining)
            except TimeoutError as error:
                raise LightpandaTimeout(
                    f"Lightpanda no respondió a {method} en "
                    f"{timeout or self._command_timeout:.0f}s."
                ) from error
            except Exception as error:
                raise LightpandaError(
                    f"CDP {method}: conexión perdida: {error}"
                ) from error

            if isinstance(raw, bytes):
                raw = raw.decode("utf-8", errors="replace")
            try:
                data = json.loads(raw)
            except ValueError:
                continue

            # Los mensajes sin 'id' son eventos (Page.*, Runtime.*): se ignoran.
            if data.get("id") != message_id:
                continue
            if "error" in data:
                error_info = data["error"] or {}
                raise LightpandaError(
                    f"CDP {method} falló: {error_info.get('message', 'error desconocido')} "
                    f"(code={error_info.get('code')})"
                )
            return data.get("result", {}) or {}

    def close(self) -> None:
        try:
            self._ws.close()
        except Exception:
            # Cerrar es best-effort: si el socket ya murió no hay nada que hacer.
            pass


def _evaluate(
    connection: _CdpConnection,
    session_id: str,
    expression: str,
    *,
    timeout: float | None = None,
):
    """``Runtime.evaluate`` que propaga las excepciones de JS como error claro."""
    result = connection.call(
        "Runtime.evaluate",
        {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": False,
        },
        session_id=session_id,
        timeout=timeout,
    )
    if result.get("exceptionDetails"):
        details = result["exceptionDetails"]
        text = details.get("text") or ""
        exception = (details.get("exception") or {}).get("description") or ""
        raise LightpandaError(
            f"El JS de extracción falló en la página: {text} {exception}".strip()
        )
    return (result.get("result") or {}).get("value")


def fetch_page_text(url: str, *, max_chars: int | None = None) -> PageContent:
    """Navega a ``url`` con Lightpanda y devuelve el texto limpio.

    Lanza ``LightpandaError`` / ``LightpandaTimeout`` ante cualquier fallo: no
    hay motor de respaldo por diseño.
    """
    target_url = _validate_url(url)
    limit = max_chars if max_chars and max_chars > 0 else _max_chars()
    navigation_timeout = _navigation_timeout()

    connection = _CdpConnection(
        _cdp_url(),
        connect_timeout=_connect_timeout(),
        command_timeout=_command_timeout(),
    )
    target_id = None
    try:
        created = connection.call("Target.createTarget", {"url": "about:blank"})
        target_id = created.get("targetId")
        if not target_id:
            raise LightpandaError(
                "Lightpanda no devolvió un targetId al abrir la pestaña."
            )

        attached = connection.call(
            "Target.attachToTarget", {"targetId": target_id, "flatten": True}
        )
        session_id = attached.get("sessionId")
        if not session_id:
            raise LightpandaError(
                "Lightpanda no devolvió un sessionId al adjuntar la pestaña."
            )

        connection.call("Page.enable", session_id=session_id)

        navigation = connection.call(
            "Page.navigate",
            {"url": target_url},
            session_id=session_id,
            timeout=navigation_timeout,
        )
        if navigation.get("errorText"):
            raise LightpandaError(
                f"No pude cargar {target_url}: {navigation['errorText']}"
            )

        _await_ready(connection, session_id, navigation_timeout, target_url)

        payload = _evaluate(
            connection,
            session_id,
            _EXTRACT_JS,
            timeout=navigation_timeout,
        )
        return _build_content(payload, target_url, limit)
    finally:
        if target_id:
            try:
                connection.call(
                    "Target.closeTarget", {"targetId": target_id}, timeout=2.0
                )
            except Exception:
                # La pestaña muere con la conexión; no enmascarar el error real.
                pass
        connection.close()


def _await_ready(
    connection: _CdpConnection,
    session_id: str,
    timeout: float,
    target_url: str,
) -> None:
    """Sondea ``document.readyState`` hasta que la página sea utilizable."""
    deadline = time.monotonic() + timeout
    while True:
        state = _evaluate(
            connection,
            session_id,
            "document.readyState",
            timeout=max(deadline - time.monotonic(), 0.1),
        )
        if state in ("interactive", "complete"):
            return
        if time.monotonic() >= deadline:
            raise LightpandaTimeout(
                f"{target_url} no terminó de cargar en {timeout:.0f}s "
                f"(readyState='{state}')."
            )
        time.sleep(0.05)


def _build_content(payload, requested_url: str, limit: int) -> PageContent:
    """Normaliza la respuesta del JS de extracción a ``PageContent``."""
    data: dict = {}
    if isinstance(payload, str):
        try:
            parsed = json.loads(payload)
        except ValueError:
            # El JS devolvió texto plano en vez del JSON esperado.
            parsed = None
        # Ojo: json.loads("null") devuelve None sin lanzar, y un JSON válido
        # puede ser una lista o un número. Solo un objeto sirve como resultado.
        data = parsed if isinstance(parsed, dict) else {"text": payload}
    elif isinstance(payload, dict):
        data = payload

    text = (data.get("text") or "").strip()
    truncated = len(text) > limit
    if truncated:
        text = text[:limit].rstrip()

    return PageContent(
        url=data.get("url") or requested_url,
        title=(data.get("title") or "").strip(),
        text=text,
        truncated=truncated,
    )
