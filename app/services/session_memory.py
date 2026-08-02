"""Memoria de conversación de sesión (WAVE-06).

Resuelve la pregunta 5 de las 11 obligatorias: «¿Y cuánto dura?» no tiene
sujeto, y sin memoria ninguna regla puede darle uno. Acá vive el estado que
WAVE-05 no pudo tener: la entidad activa y los últimos N turnos.

Reglas de diseño (hallazgos A y O del runbook):

* **Ámbito de dispositivo/sesión, NO de socket.** `main.py` tiene un único
  `ConversationService` que difunde a todos los clientes: es un kiosco, no un
  servidor multiusuario. Aislar por conexión rompería el modelo; este módulo
  expone un único estado a nivel de proceso, compartido por la ruta web y la de
  voz, y que sobrevive a reconexiones de WebSocket.
* **Expiración por inactividad.** Sin TTL, el visitante nº 2 heredaría la
  conversación del nº 1. El estado se descarta cuando pasa el TTL sin
  actividad, y hay además un reset explícito para el operador.
* **En memoria del proceso, con cero persistencia.** Nada de SQLite, JSON ni
  Redis: los datos de un visitante mueren con el proceso, a propósito. Sin
  dependencias nuevas.
* **Resolución determinista de referencias.** «¿Y cuánto dura?» se expande con
  la entidad activa **antes** de enrutar, sin llamada de red ni LLM. Si la
  pregunta nombra otra carrera u otro dominio, la entidad se reemplaza (cambio
  de tema). Sin entidad activa, el comportamiento es el de antes: no se
  inventa un antecedente.
* **Historial acotado a N turnos.** N = 3 por defecto, configurable; cada
  turno se recorta (pregunta y respuesta) para no devolverle al prompt el
  coste que WAVE-05 acaba de quitar.

El flag ``HOLOGRAM_SESSION_MEMORY=0`` apaga todo: `resolve` devuelve la
pregunta tal cual, `history` vacío y `observe` no-op (comportamiento previo a
esta WAVE).
"""

from __future__ import annotations

import os
import re
import time
from collections.abc import Callable

__all__ = [
    "SessionMemory",
    "get_session",
    "reset_session",
]

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
# N de turnos que van al prompt. El coste de tokens de esta WAVE debe medirse
# contra el presupuesto que ganó WAVE-05, no gastárselo entero: 3 turnos
# recortados son ~1.260 chars, muy por debajo del tope de contexto.
_MAX_TURNS_DEFAULT = 3

# TTL de inactividad: la escala de una conversación de feria. Pasados 3
# minutos en silencio, el visitante siguiente empieza limpio.
_TTL_SECONDS_DEFAULT = 180.0

# Recorte por turno: la respuesta completa de `get_program_info` puede superar
# los 1.000 chars; para el historial basta la esencia.
_QUESTION_CAP = 120
_ANSWER_CAP = 300

# ---------------------------------------------------------------------------
# Léxico de entidades: lo único que cuenta como "nombra un tema". Normalizado
# (sin acentos) → etiqueta canónica con la que se expande la pregunta.
# ---------------------------------------------------------------------------
_LEXICON: tuple[tuple[str, str], ...] = (
    ("programacion web", "Programación Web"),
    ("diseno grafico", "Diseño Gráfico"),
    ("administracion de empresas", "Administración de Empresas"),
    ("enfermeria", "Enfermería"),
    ("unev", "UNEV"),
)

# Marcadores de institución: una pregunta que los menciona NO se resuelve con
# la entidad activa, por más que parezca un follow-up. «¿Los títulos son
# válidos?» habla de la institución, no de la carrera; resolverlo mezclaría la
# entidad en una pregunta ajena (el peor modo de fallo de esta WAVE).
_INSTITUTION_MARKERS: frozenset[str] = frozenset(
    {
        "unev",
        "universidad",
        "universitario",
        "instituto",
        "institucion",
        "honduras",
        "campus",
        "sede",
        "facultad",
    }
)

# Frases de referencia sin antecedente: si la pregunta las usa y no nombra
# entidad ni institución, se expande con la entidad activa. Es la lista
# explícita de los follow-ups que esta WAVE resuelve; todo lo demás se queda
# como está (no se inventa un antecedente).
_REFERENCE_PHRASES: frozenset[str] = frozenset(
    {
        "cuanto dura",
        "cuanto tiempo",
        "cuantos anos",
        "cuantos meses",
        "cuantos ciclos",
        "cuanto cuesta",
        "cuanto vale",
        "cuanto pago",
        "forma de pago",
        "mensualidad",
        "arancel",
        "aranceles",
        "donde se estudia",
        "donde se puede estudiar",
        "donde estudiar",
        "como ingreso",
        "como entro",
        "como aplico",
        "para entrar",
        "proceso de ingreso",
        "requisito",
        "requisitos",
        "que materias",
        "cuantas materias",
        "que se estudia",
        "que se ve",
        "en que trabaja",
        "donde trabaja",
        "cuanto gana",
        "cuanto ganan",
        "salario",
        "sueldo",
        "beca",
        "becas",
        "horario",
        "horarios",
        "turno",
        "turnos",
        "semestre",
        "cuatrimestre",
    }
)

# ---------------------------------------------------------------------------
# Normalización local (espejo de `skills.router._terms`, sin acoplarse a él)
# ---------------------------------------------------------------------------
_ACCENTS = str.maketrans("áéíóúüñÁÉÍÓÚÜÑ", "aeiouunAEIOUUN")
_WORD_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> tuple[str, ...]:
    """Tokens normalizados (minúsculas, sin acentos), en orden."""
    return tuple(_WORD_RE.findall(text.lower().translate(_ACCENTS)))


def _contains(tokens: tuple[str, ...], phrase: str) -> bool:
    """¿La frase aparece como secuencia de tokens completa en el texto?"""
    if " " not in phrase:
        return phrase in tokens
    needle = tuple(phrase.split())
    width = len(needle)
    if width > len(tokens):
        return False
    return any(tokens[i : i + width] == needle for i in range(len(tokens) - width + 1))


def _match_entity(text: str | tuple[str, ...]) -> str | None:
    """Etiqueta de la entidad nombrada en el texto, o ``None``."""
    tokens = text if isinstance(text, tuple) else _tokens(text)
    for phrase, label in _LEXICON:
        if _contains(tokens, phrase):
            return label
    return None


def _is_reference(tokens: tuple[str, ...]) -> bool:
    return any(_contains(tokens, phrase) for phrase in _REFERENCE_PHRASES)


def _expand(user_input: str, label: str) -> str:
    """«¿Y cuánto dura?» + Programación Web → «¿Y cuánto dura sobre Programación Web?»"""
    base = user_input.strip().rstrip("?")
    return f"{base} sobre {label}?"


def _env_bool(name: str, default: bool = True) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() not in ("0", "false", "no", "off")


# ---------------------------------------------------------------------------
# Estado
# ---------------------------------------------------------------------------
class SessionMemory:
    """Estado de conversación de un kiosco: entidad activa + últimos N turnos.

    ``now`` es inyectable para poder testear la expiración sin dormir: los
    tests adelantan el reloj. Por defecto usa ``time.monotonic``, que no salta
    con cambios de hora del sistema.
    """

    def __init__(
        self,
        *,
        max_turns: int | None = None,
        ttl_seconds: float | None = None,
        now: Callable[[], float] | None = None,
        disabled: bool = False,
    ) -> None:
        self._max_turns = max(
            1, max_turns if max_turns is not None else _MAX_TURNS_DEFAULT
        )
        self._ttl = (
            ttl_seconds if ttl_seconds is not None else _TTL_SECONDS_DEFAULT
        )
        self._now = now or time.monotonic
        self._disabled = disabled

        self._entity: str | None = None
        self._turns: list[tuple[str, str]] = []
        self._last_activity: float | None = None

    # -- estado ---------------------------------------------------------
    @property
    def active_entity(self) -> str | None:
        self._expire_if_idle()
        return None if self._disabled else self._entity

    @property
    def is_expired(self) -> bool:
        if self._last_activity is None:
            return False
        return self._now() - self._last_activity > self._ttl

    @property
    def turn_count(self) -> int:
        return len(self._turns)

    # -- API pública ------------------------------------------------------
    def resolve(self, user_input: str) -> str:
        """La pregunta lista para enrutar, con la referencia expandida si toca.

        Expande **solo** cuando: hay entidad activa, la pregunta no nombra una
        entidad, no menciona la institución y usa una frase de referencia.
        Cualquier otro caso devuelve la pregunta tal cual (comportamiento
        actual).
        """
        if self._disabled:
            return user_input
        self._expire_if_idle()
        if self._entity is None:
            return user_input
        tokens = _tokens(user_input)
        if _match_entity(tokens) is not None:
            return user_input
        if set(tokens) & _INSTITUTION_MARKERS:
            return user_input
        if not _is_reference(tokens):
            return user_input
        return _expand(user_input, self._entity)

    def observe(self, user_input: str, reply: str) -> None:
        """Registra un turno y actualiza la entidad activa.

        El cambio de tema vive acá: si la pregunta (ya resuelta) nombra una
        entidad distinta, se reemplaza. Si no nombra ninguna, se conserva la
        anterior. Sin entidad activa, el historial se acumula igual.
        """
        if self._disabled:
            return
        self._expire_if_idle()
        entity = _match_entity(user_input)
        if entity is not None:
            self._entity = entity
        question = user_input.strip()[:_QUESTION_CAP]
        answer = reply.strip()[:_ANSWER_CAP]
        if question and answer:
            self._turns.append((question, answer))
            if len(self._turns) > self._max_turns:
                del self._turns[0]
        self._last_activity = self._now()

    def history(self) -> list[dict[str, str]]:
        """Los últimos N turnos como mensajes user/assistant para el prompt."""
        if self._disabled:
            return []
        self._expire_if_idle()
        messages: list[dict[str, str]] = []
        for question, answer in self._turns:
            messages.append({"role": "user", "content": question})
            messages.append({"role": "assistant", "content": answer})
        return messages

    def reset(self) -> None:
        """Reset explícito: operador nuevo, cambio de tema decidido a mano."""
        self._entity = None
        self._turns = []
        self._last_activity = None

    # -- interna ----------------------------------------------------------
    def _touch(self) -> None:
        self._last_activity = self._now()

    def _expire_if_idle(self) -> None:
        if self.is_expired:
            self.reset()


# ---------------------------------------------------------------------------
# Singleton de proceso: el estado del kiosco, compartido por ambas rutas.
# ---------------------------------------------------------------------------
_session: SessionMemory | None = None
_disabled_session: SessionMemory | None = None


def _session_enabled() -> bool:
    return _env_bool("HOLOGRAM_SESSION_MEMORY", True)


def get_session() -> SessionMemory:
    """El estado único del proceso (o un estado apagado con el flag en 0)."""
    global _session, _disabled_session
    if not _session_enabled():
        if _disabled_session is None:
            _disabled_session = SessionMemory(disabled=True)
        return _disabled_session
    if _session is None:
        _session = SessionMemory(
            max_turns=int(os.getenv("HOLOGRAM_SESSION_TURNS", _MAX_TURNS_DEFAULT)),
            ttl_seconds=float(os.getenv("HOLOGRAM_SESSION_TTL", _TTL_SECONDS_DEFAULT)),
        )
    return _session


def reset_session() -> None:
    """Descarta el estado del proceso (para tests y el reset del operador)."""
    global _session, _disabled_session
    _session = None
    _disabled_session = None
