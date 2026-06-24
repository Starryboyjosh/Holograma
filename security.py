"""Utilidades de seguridad para Holograma UNEV.

Funciones puras (sin red, sin estado de proceso) para:

* **Redacción de secretos** en logs y mensajes de error, para que una API key
  nunca aparezca en la consola del kiosko ni se devuelva al navegador.
* **Saneo / límite de tamaño** del texto que llega de fuera (prompt del chat,
  texto de TTS, etiquetas de visión editables): trunca y elimina caracteres de
  control, reduciendo el riesgo de abuso (coste/DoS) y de inyección de prompts.

Se mantienen sin dependencias del backend pesado (FastAPI/torch) para poder
probarlas con ``pytest`` en cualquier entorno.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping

# Límites de tamaño (caracteres). Generosos para uso real, pero acotados.
MAX_PROMPT_CHARS = 4000  # mensaje de chat del visitante → LLM
MAX_TTS_CHARS = 2000  # texto enviado al sintetizador de voz
MAX_LABEL_CHARS = 200  # etiqueta/descr. de un objeto de visión (editable)
MAX_VOCAB_CHARS = 4000  # vocabulario UNEV pegado por el operador

_REDACTED = "***REDACTED***"

# Variables de entorno que contienen secretos. Es deliberadamente un espejo
# pequeño y estable de provider_config.PROVIDERS[*].key_env: se mantiene aquí
# para que la redacción no dependa del registro de proveedores (módulo crítico
# de seguridad, sin acoplamientos).
SECRET_ENV_VARS: tuple[str, ...] = (
    "OPENROUTER_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "NVIDIA_API_KEY",
    "OPENAI_COMPAT_API_KEY",
)

# Tokens con forma de API key de los proveedores soportados (y prefijos comunes).
_KEY_PATTERNS = [
    re.compile(r"(?i)\b(?:sk-ant-|sk-or-v1-|sk-proj-|sk-|nvapi-|gsk_|xai-|AIza)[A-Za-z0-9_\-]{12,}"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._\-]{12,}"),
]

# Puntos de código a eliminar: controles C0 (excepto tab/newline/cr) y DEL, más
# caracteres de ancho cero y de anulación bidireccional usados para ocultar texto
# o inyecciones de prompt. Se construye la clase en tiempo de ejecución para no
# meter caracteres invisibles en el código fuente.
_STRIP_CODEPOINTS: tuple[int, ...] = (
    *range(0x00, 0x09),
    0x0B,
    0x0C,
    *range(0x0E, 0x20),
    0x7F,
    *range(0x200B, 0x2010),  # zero-width space/non-joiner/joiner, LRM/RLM, marcas
    *range(0x202A, 0x202F),  # incrustación/anulación bidireccional
    0x2060,  # word joiner
    0xFEFF,  # BOM / zero-width no-break space
)
_CONTROL_CHARS = re.compile("[" + "".join(re.escape(chr(c)) for c in _STRIP_CODEPOINTS) + "]")


def redact_secrets(text: object, env: Mapping[str, str] | None = None) -> str:
    """Devuelve ``text`` con cualquier secreto enmascarado.

    Enmascara (1) los valores exactos de las variables en :data:`SECRET_ENV_VARS`
    presentes en ``env`` y (2) cualquier token con forma de API key. Acepta no-str
    (por ejemplo una excepción) y lo convierte primero, para envolver con seguridad
    ``str(e)``.
    """
    s = text if isinstance(text, str) else str(text)

    if env:
        for name in SECRET_ENV_VARS:
            value = (env.get(name) or "").strip()
            # Evita enmascarar cadenas triviales que podrían coincidir por azar.
            if len(value) >= 8:
                s = s.replace(value, _REDACTED)

    for pattern in _KEY_PATTERNS:
        s = pattern.sub(_REDACTED, s)

    return s


def clamp_text(text: object, max_len: int) -> str:
    """Sanea texto no confiable: elimina caracteres de control y trunca a ``max_len``.

    No intenta "entender" el contenido (eso lo decide el prompt), solo acota el
    tamaño y quita caracteres invisibles usados para ofuscar inyecciones.
    """
    s = text if isinstance(text, str) else str(text)
    s = _CONTROL_CHARS.sub("", s)
    if max_len >= 0 and len(s) > max_len:
        s = s[:max_len]
    return s.strip()


def redact_iter(values: Iterable[object], env: Mapping[str, str] | None = None) -> list[str]:
    """Aplica :func:`redact_secrets` a una colección (útil para listas de logs)."""
    return [redact_secrets(v, env) for v in values]
