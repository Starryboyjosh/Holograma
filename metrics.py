"""Métrica por turno: una línea estructurada, un solo punto de emisión.

Por qué existe este módulo y no un `print` en cada ruta: el sistema tiene dos
caminos hacia el LLM —voz/CLI (`call` → `iter_reply_tokens`) y web/WebSocket
(`ConversationService` → `stream_llm_response`)— y hasta ahora ninguno dejaba
rastro de lo que costó el turno. Formatear la métrica en cada consumidor haría
que las dos rutas divergieran otra vez, que es justo el defecto de fondo que el
plan viene a cerrar. Acá el formato se define **una vez** y las dos rutas llaman
al mismo objeto.

Qué NO lleva la línea: claves, el prompt, el contexto institucional. Sólo
longitudes, tiempos y nombres de proveedor/modelo. La línea sale además por
:func:`security.redact_secrets`, el mismo saneado que usa el endpoint de
configuración de ``main.py``.

Sale por **stderr**, no por stdout. Dos razones: (1) stdout del kiosco es el log
humano —CoT, TTS, cámara— y mezclarle JSON lo vuelve incómodo de leer y de
parsear; con stderr se separan los dos flujos (``2> metrics.log``). (2) stdout es
además el canal del sidecar; meterle líneas estructuradas nuevas es pedir un
choque. Esto último no es teórico: al emitir por stdout se rompió
``test_llm_fallback.py::test_stream_vacio_registra_advertencia``, que afirma
sobre *todo* lo impreso.

Apagado: ``HOLOGRAM_METRICS=0``.

Uso (un objeto por turno)::

    m = TurnMetrics("voice", user_input=pregunta, event_mode=mode)
    m.note_prompt(messages, university_context)
    for backend in candidatos:
        m.note_attempt(backend)
        for token in stream:
            m.note_token(token)
    m.emit()          # idempotente: como mucho una línea por turno
"""

from __future__ import annotations

import json
import os
import sys
import time

from security import redact_secrets
from utils import _env, pop_ready_speech

# Prefijo de la línea. Elegido para poder aislarla con `grep '\[METRICS\]'` en el
# log del kiosco, que mezcla salida de TTS, cámara y LLM.
PREFIX = "[METRICS]"

# Divisor de la auditoría para estimar tokens a partir de caracteres. Es una
# **estimación**, no un conteo del tokenizador: el español acentuado y los
# nombres propios se apartan de esta media. Por eso el campo se llama
# `estimated_input_tokens` y no `input_tokens`.
CHARS_PER_TOKEN = 3.5


def metrics_enabled() -> bool:
    """¿Emitir la línea de métrica? Activo por defecto.

    Una línea por turno en un kiosco es volumen despreciable, así que el default
    es encendido; la variable existe para el rollback. Mismo patrón que
    ``_tts_stream_enabled()`` en `app/services/conversation.py`.
    """
    return _env("HOLOGRAM_METRICS", "1").lower() not in ("0", "false", "no", "off")


def _local_skill_would_answer(user_input: str) -> bool:
    """¿El router local tenía respuesta para esta pregunta?

    Se consulta **aparte** del turno: en la ruta normal el router sólo se
    invoca cuando el backend es ``local_only``, así que sin esto no habría forma
    de saber, tras un evento, qué proporción de preguntas podía resolverse sin
    salir a la nube — que es la pregunta que WAVE-05 tiene que responder.

    Devuelve un booleano, no el nombre de la skill: `route_local_skill` retorna
    el texto ya renderizado y no identifica cuál respondió. Sacarle el nombre
    exige tocar `skills/router.py`, y esta WAVE observa sin cambiar lo que mide.
    """
    try:
        from skills.router import route_local_skill

        return bool(route_local_skill(user_input))
    except Exception:
        # Una métrica nunca puede tumbar un turno.
        return False


def _model_for(backend: str | None) -> str | None:
    """Modelo efectivo del backend, sin claves. ``None`` si no aplica."""
    if not backend or backend == "local_only":
        return None
    try:
        import provider_config as pc

        return pc.resolve_model(backend) or None
    except Exception:
        return None


class TurnMetrics:
    """Acumula lo medible de un turno y emite una sola línea al cerrarlo.

    Todos los `note_*` son tolerantes a fallos y baratos: si la instrumentación
    se rompe, el visitante igual recibe su respuesta.
    """

    def __init__(
        self,
        route: str,
        *,
        user_input: str = "",
        event_mode: str | None = None,
        enabled: bool | None = None,
    ):
        self.route = route
        self.event_mode = event_mode
        self._user_input = user_input
        self._enabled = metrics_enabled() if enabled is None else enabled

        self.context_chars = 0
        self.prompt_chars = 0
        self.provider: str | None = None
        self._attempts = 0

        self._t0 = time.monotonic()
        self._t_first_token: float | None = None
        self._t_first_clause: float | None = None

        # Espejo de lo que hace el consumidor con el mismo stream: así el tiempo
        # a primera cláusula sale igual en las dos rutas y no depende de que
        # cada una lo mida por su cuenta.
        self._speech_buf = ""
        self._first_speech = True
        self._saw_text = False

        self._emitted = False

    # -- captura ----------------------------------------------------------- #
    def note_prompt(self, messages, university_context: str = "") -> None:
        """Longitudes del prompt. Nunca guarda el contenido."""
        self.context_chars = len(university_context or "")
        try:
            self.prompt_chars = sum(len(m.get("content") or "") for m in messages)
        except Exception:
            self.prompt_chars = 0

    def note_attempt(self, backend: str) -> None:
        """Un backend más intentado. El último que se anota es el que respondió."""
        self._attempts += 1
        self.provider = backend

    def note_token(self, text: str) -> None:
        """Un trozo de respuesta visible; marca los dos hitos de latencia."""
        if not text:
            return
        self._saw_text = True
        if self._t_first_token is None:
            self._t_first_token = time.monotonic()
        if self._t_first_clause is not None:
            return
        self._speech_buf += text
        ready, self._speech_buf, self._first_speech = pop_ready_speech(
            self._speech_buf, self._first_speech
        )
        if ready:
            self._t_first_clause = time.monotonic()

    # -- emisión ----------------------------------------------------------- #
    def _ms(self, stamp: float | None) -> int | None:
        return None if stamp is None else round((stamp - self._t0) * 1000)

    def as_dict(self) -> dict:
        """La métrica ya resuelta. Separada de `emit` para poder testearla."""
        return {
            "route": self.route,
            "event_mode": self.event_mode,
            "provider": self.provider,
            "model": _model_for(self.provider),
            "context_chars": self.context_chars,
            "prompt_chars": self.prompt_chars,
            "estimated_input_tokens": round(self.prompt_chars / CHARS_PER_TOKEN),
            "local_skill_hit": _local_skill_would_answer(self._user_input),
            "time_to_first_token_ms": self._ms(self._t_first_token),
            "time_to_first_clause_ms": self._ms(self._t_first_clause),
            "fallback_count": max(self._attempts - 1, 0),
        }

    def emit(self) -> None:
        """Cierra el turno e imprime la línea. Llamarla dos veces no duplica.

        La idempotencia importa: el emisor vive en un `finally` de un generador,
        y un consumidor que abandona el stream a medias lo dispararía por
        `GeneratorExit` además de por el cierre normal.
        """
        if self._emitted:
            return
        self._emitted = True
        if not self._enabled:
            return

        # Sin frontera de cláusula en todo el turno, el consumidor habla el
        # resto al cerrar el stream: ese es el momento de la primera voz.
        if self._t_first_clause is None and self._saw_text:
            self._t_first_clause = time.monotonic()

        try:
            payload = json.dumps(self.as_dict(), ensure_ascii=False)
            # Mismo saneado y misma fuente de verdad que `main.py`: los valores
            # exactos del entorno además de las formas de API key conocidas.
            linea = redact_secrets(payload, os.environ)
        except Exception as error:  # pragma: no cover - blindaje
            # Una métrica rota no puede tumbar un turno ni ensuciar el log con
            # un traceback: se deja constancia en una línea y se sigue.
            linea = f'{{"error": "{type(error).__name__}"}}'
        print(f"{PREFIX} {linea}", file=sys.stderr, flush=True)
