import asyncio
import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
from collections.abc import AsyncGenerator

from dotenv import load_dotenv

from provider_config import (
    PROVIDERS,
    VALID_BACKENDS,
    configured_cloud_providers,
    resolve_api_key,
    resolve_base_url,
    resolve_model,
    select_backend,
)
from security import redact_secrets
from utils import _env, _env_float

# Anclar .env a ESTE archivo (no al CWD): este módulo se importa antes de que
# main.py ancle nada, y al lanzarse como sidecar de Tauri el CWD es arbitrario.
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

DEFAULT_OLLAMA_MODEL = PROVIDERS["ollama"].default_model


class LLMBackendError(Exception):
    pass


def _ollama_base_url():
    return _env("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")


def _ollama_model_name():
    return _env("OLLAMA_MODEL") or DEFAULT_OLLAMA_MODEL


def _max_tokens() -> int:
    """Límite de tokens de salida, configurable y unificado para todos los backends.

    Antes cada backend traía su propio número mágico (350 / 450 / 1024 / sin
    límite), así que la longitud de la respuesta cambiaba según el proveedor —y
    entre voz y web. Ahora todos leen ``LLM_MAX_TOKENS`` (450 por defecto); un
    valor ausente o inválido cae al de por defecto.
    """
    raw = _env("LLM_MAX_TOKENS")
    if not raw:
        return 450
    try:
        value = int(raw)
    except ValueError:
        return 450
    return value if value > 0 else 450


def _request_timeout() -> float:
    """Timeout HTTP del cliente LLM (segundos). Evita colgarse sin fin en la nube.

    La ruta de voz usa chat no-stream (``generate_reply``). Sin timeout el SDK
    de OpenAI puede esperar indefinidamente a OpenRouter y la terminal solo
    muestra ``intento no-stream`` hasta que el usuario mata el proceso.
    """
    raw = _env("LLM_REQUEST_TIMEOUT")
    if not raw:
        return 90.0
    try:
        value = float(raw)
    except ValueError:
        return 90.0
    return value if value > 0 else 90.0


def _ollama_request(path, payload=None, timeout=30.0):
    url = f"{_ollama_base_url()}{path}"
    data = None
    method = "GET"

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        method = "POST"

    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )

    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")

    if not body.strip():
        return {}

    return json.loads(body)


def _ollama_tags(timeout=1.5):
    return _ollama_request("/api/tags", timeout=timeout)


def _ollama_server_available():
    try:
        _ollama_tags(timeout=_env_float("OLLAMA_STATUS_TIMEOUT_SECONDS", 1.5))
    except Exception:
        return False

    return True


def _ollama_model_available(model=None):
    model = model or _ollama_model_name()

    try:
        tags = _ollama_tags(timeout=_env_float("OLLAMA_STATUS_TIMEOUT_SECONDS", 1.5))
    except Exception:
        return False

    model_names = [item.get("name") for item in tags.get("models", [])]
    return model in model_names


def list_ollama_models(timeout: float | None = None) -> dict:
    """Modelos instalados en el Ollama local (equivalente a ``ollama list``).

    Devuelve un dict listo para la API:

    ``{"ok": bool, "models": [str, ...], "message": str}``

    Los nombres salen de ``GET /api/tags`` (campo ``name``, p. ej. ``gemma3:1b``).
    Si el servicio no responde, ``ok=False`` y ``models=[]`` con un mensaje
    accionable — la UI puede mostrar el error y seguir permitiendo texto libre.
    """
    t = (
        timeout
        if timeout is not None
        else _env_float("OLLAMA_STATUS_TIMEOUT_SECONDS", 1.5)
    )
    try:
        tags = _ollama_tags(timeout=t)
    except Exception:
        return {
            "ok": False,
            "models": [],
            "message": (
                "Ollama no responde. ¿Está iniciado el servicio? "
                "Prueba: ollama serve"
            ),
        }

    names: list[str] = []
    seen: set[str] = set()
    for item in tags.get("models", []) or []:
        name = (item.get("name") or "").strip()
        if name and name not in seen:
            seen.add(name)
            names.append(name)
    names.sort(key=str.lower)

    if not names:
        return {
            "ok": True,
            "models": [],
            "message": (
                "Ollama responde, pero no hay modelos instalados. "
                "Descarga uno con: ollama pull gemma3:1b"
            ),
        }
    return {
        "ok": True,
        "models": names,
        "message": f"{len(names)} modelo(s) instalado(s).",
    }


# Readiness de Ollama cacheada con TTL. Antes `_ollama_ready()` se invocaba 2–4
# veces por mensaje (get_selected_backend + _candidate_backends) y cada
# invocación lanzaba DOS sondas HTTP bloqueantes a /api/tags (1.5 s c/u). Sobre
# el event loop, bajo carga, eso congelaba TODO el servidor. Ahora una sola sonda
# combinada se memoiza durante OLLAMA_READY_TTL_SECONDS.
_OLLAMA_READY_CACHE: dict[str, object] = {"value": None, "expires": 0.0}
_OLLAMA_READY_LOCK = threading.Lock()


def _ollama_ready(force: bool = False) -> bool:
    """¿Ollama está listo (servidor arriba + modelo instalado)?  Cacheado.

    El resultado se memoiza ``OLLAMA_READY_TTL_SECONDS`` (10 s por defecto) para
    no sondear en cada mensaje.  ``force=True`` ignora la caché.
    """
    now = time.monotonic()
    with _OLLAMA_READY_LOCK:
        cached = _OLLAMA_READY_CACHE["value"]
        expires = _OLLAMA_READY_CACHE["expires"]
        if not force and cached is not None and now < expires:
            return bool(cached)

    # Sonda única combinada (servidor + modelo) fuera del lock: una sola llamada
    # a /api/tags responde ambas preguntas, en vez de dos sondas separadas.
    model = _ollama_model_name()
    try:
        tags = _ollama_tags(timeout=_env_float("OLLAMA_STATUS_TIMEOUT_SECONDS", 1.5))
        model_names = [item.get("name") for item in tags.get("models", [])]
        ready = model in model_names
    except Exception:
        ready = False

    ttl = _env_float("OLLAMA_READY_TTL_SECONDS", 10.0)
    with _OLLAMA_READY_LOCK:
        _OLLAMA_READY_CACHE["value"] = ready
        _OLLAMA_READY_CACHE["expires"] = time.monotonic() + ttl
    return ready


def get_selected_backend():
    """Backend efectivo según la configuración actual.

    Delega en :func:`provider_config.select_backend`, que respeta una elección
    explícita de proveedor (incluido Ollama) y solo auto-detecta por API key
    cuando no se eligió nada. Esto corrige el caso en que elegir "Local" seguía
    usando la nube por una key vieja.
    """
    backend = _env("LLM_BACKEND", "auto").lower()
    if backend != "auto" and backend not in VALID_BACKENDS:
        print(f"[LLM] Backend inválido '{backend}'. Usando 'auto'.")
        os.environ.pop("LLM_BACKEND", None)
    return select_backend(os.environ, ollama_ready=_ollama_ready)


def get_backend_status():
    backend = get_selected_backend()

    if backend == "ollama":
        model = _ollama_model_name()
        if not _ollama_server_available():
            return (
                "Backend solicitado: Ollama, pero el servicio no está respondiendo. "
                "Inicia Ollama o cambia el proveedor a 'Solo skills locales'."
            )

        if not _ollama_model_available(model):
            return (
                f"Backend solicitado: Ollama, pero no encontré el modelo {model}. "
                f"Descárgalo con: ollama pull {model}"
            )

        return f"Backend activo: Ollama local con modelo {model}."

    if backend == "local_only":
        return "Backend activo: local_only. Solo se responderán skills locales."

    provider = PROVIDERS.get(backend)
    if provider is not None:
        model = resolve_model(backend)
        return f"Backend activo: {provider.label} con modelo {model}."

    return "Backend activo: local_only. Solo se responderán skills locales."


def _humanize_probe_error(provider, error):
    """Traduce errores de proveedor a un mensaje accionable para el operador."""
    label = PROVIDERS[provider].label
    text = str(error).lower()
    if any(s in text for s in ("401", "invalid api key", "incorrect api key", "unauthorized", "authentication")):
        return f"API key de {label} inválida o sin permisos."
    if any(s in text for s in ("404", "model_not_found", "does not exist", "no such model", "not found")):
        return f"El modelo no existe en {label} o no tienes acceso. Revisa el nombre."
    if any(s in text for s in ("429", "rate limit", "quota", "insufficient_quota")):
        return f"Límite o cuota agotada en {label}."
    if any(s in text for s in ("connection", "timed out", "timeout", "getaddrinfo", "name resolution", "refused")):
        return f"No se pudo conectar con {label}. Revisa internet o la URL base."
    # Fallback genérico: el error crudo del proveedor podría contener la key.
    return redact_secrets(f"Error con {label}: {error}", os.environ)


def probe_backend(provider, api_key=None, model=None, base_url=None, timeout=20.0):
    """Prueba real de conexión a un proveedor sin persistir nada.

    Devuelve ``{"ok": bool, "message": str}`` con un mensaje accionable. Los
    overrides (key/model/base_url) se aplican a un env temporal local, nunca al
    proceso, para que "Probar conexión" no cambie la configuración guardada.
    """
    provider = (provider or "").strip().lower()
    if provider not in PROVIDERS:
        return {"ok": False, "message": f"Proveedor desconocido: {provider}"}

    p = PROVIDERS[provider]
    env = dict(os.environ)
    if api_key and p.key_env:
        env[p.key_env] = api_key
    if model and p.model_env:
        env[p.model_env] = model
    if base_url and p.base_url_env:
        env[p.base_url_env] = base_url

    if provider == "local_only":
        return {"ok": True, "message": "Modo solo-skills: siempre disponible."}

    if provider == "ollama":
        if not _ollama_server_available():
            return {"ok": False, "message": "Ollama no responde. ¿Está iniciado el servicio?"}
        mdl = model or resolve_model("ollama", env)
        if not _ollama_model_available(mdl):
            return {
                "ok": False,
                "message": f"Modelo '{mdl}' no instalado. Ejecuta: ollama pull {mdl}",
            }
        return {"ok": True, "message": f"Ollama responde con el modelo {mdl}."}

    try:
        key, mdl, url = _require(provider, env)
    except LLMBackendError as error:
        return {"ok": False, "message": str(error)}

    try:
        if provider == "claude_native":
            from anthropic import Anthropic

            client = Anthropic(api_key=key, timeout=timeout)
            client.messages.create(
                model=mdl, max_tokens=1, messages=[{"role": "user", "content": "ping"}]
            )
        else:
            from openai import OpenAI

            client = OpenAI(api_key=key or "none", base_url=url or None, timeout=timeout)
            client.chat.completions.create(
                model=mdl, max_tokens=1, messages=[{"role": "user", "content": "ping"}]
            )
        return {"ok": True, "message": f"Conexión correcta con {p.label} ({mdl})."}
    except Exception as error:  # noqa: BLE001 - se traduce a mensaje accionable
        return {"ok": False, "message": _humanize_probe_error(provider, error)}


def _candidate_backends(primary_backend):
    """Orden de intentos del LLM, de más a menos preferente.

    primario -> otros proveedores en la nube con credenciales configuradas ->
    Ollama (si responde) -> local_only (último recurso, siempre presente).

    Antes era ``[primario, ollama, local_only]``: si el primario fallaba y había
    OTRA API key válida configurada, se saltaba directo a Ollama/local en vez de
    aprovechar el proveedor de respaldo. Ahora esos proveedores entran como
    fallback intermedio, en orden determinista, sin duplicar el primario.
    """
    candidates: list[str] = []

    def add(backend):
        if backend and backend not in candidates:
            candidates.append(backend)

    add(primary_backend)
    for provider in configured_cloud_providers():
        add(provider)
    add("ollama" if _ollama_ready() else None)
    add("local_only")
    return candidates


def _local_only_reply(user_input):
    try:
        from skills.router import route_local_skill
        local_response = route_local_skill(user_input)
    except Exception:
        local_response = None

    if local_response:
        return local_response

    return (
        "Por ahora estoy en modo local. Puedo responder preguntas básicas sobre UNEV, "
        "sus carreras, admisiones, ubicación y aprobación oficial. Para conversación abierta, "
        "configura una API válida o usa Ollama con un modelo instalado."
    )


def _chat_with_backend(backend, messages):
    if backend == "ollama":
        return _chat_with_ollama(messages)
    if backend == "claude_native":
        return _chat_with_claude_native(messages)
    if backend in PROVIDERS and PROVIDERS[backend].openai_compatible:
        # openrouter, openai, nvidia y custom_openai comparten el cliente OpenAI;
        # solo cambian key, base_url y modelo, resueltos por el contrato.
        return _chat_with_openai_compatible(backend, messages)
    raise LLMBackendError(f"Backend no soportado: {backend}")


def _build_messages(user_input, system_prompt, university_context, camera_context=None):
    # Reforzar idioma español en el mensaje del usuario para modelos débiles
    user_content = f"{user_input}\n\n[Instrucción: responde siempre en español.]"
    messages = [
        {
            "role": "system",
            "content": system_prompt,
        },
        {
            "role": "system",
            "content": university_context,
        },
    ]
    if camera_context:
        messages.append({
            "role": "system",
            "content": f"Contexto actual de la cámara:\n{camera_context}",
        })
    messages.append({
        "role": "user",
        "content": user_content,
    })
    return messages


def _require(provider, env=None):
    """Resuelve (api_key, model, base_url) o lanza un error claro y accionable."""
    p = PROVIDERS[provider]
    api_key = resolve_api_key(provider, env)
    if p.key_env and not api_key:
        raise LLMBackendError(
            f"Falta la API key de {p.label} ({p.key_env}). "
            f"Configúrala en la pantalla de ajustes."
        )
    model = resolve_model(provider, env)
    if not model:
        raise LLMBackendError(
            f"No hay modelo configurado para {p.label}. "
            f"Indica un nombre de modelo en los ajustes."
        )
    base_url = resolve_base_url(provider, env)
    if provider == "custom_openai" and not base_url:
        raise LLMBackendError(
            "El endpoint compatible con OpenAI necesita una URL base "
            "(OPENAI_COMPAT_BASE_URL)."
        )
    return api_key, model, base_url


def _chat_with_openai_compatible(provider, messages):
    """Chat OpenAI-compatible con stream interno + CoT en terminal + timeout.

    Aunque la API de voz pide una respuesta completa (``generate_reply``),
    streameamos por debajo para:
    1. Ver el CoT/tokens en vivo (antes solo aparecía al terminar o nunca).
    2. Aplicar timeout HTTP y no colgarse indefinidamente en OpenRouter.
    """
    from openai import OpenAI

    api_key, model, base_url = _require(provider)
    timeout = _request_timeout()
    if _cot_log_enabled():
        print(
            f"[LLM/CoT] request provider={provider} model={model} "
            f"timeout={timeout:.0f}s mode=stream-accumulate",
            flush=True,
        )
    client = OpenAI(
        api_key=api_key or "none",
        base_url=base_url or None,
        timeout=timeout,
    )
    mirror = _CotStreamMirror(provider, model)
    parts: list[str] = []
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.6,
            max_tokens=_max_tokens(),
            stream=True,
        )
        for chunk in response:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            reasoning = _delta_reasoning(delta)
            if reasoning:
                mirror.feed_reasoning(reasoning)
            content = delta.content if delta is not None else None
            if content:
                mirror.feed(content)
                parts.append(content)
        mirror.finish()
    except Exception as error:
        mirror.finish(error=str(error))
        raise LLMBackendError(
            f"{provider}/{model} falló o agotó timeout ({timeout:.0f}s): {error}"
        ) from error

    text = "".join(parts).strip()
    if not text and _cot_log_enabled():
        print(
            f"[LLM/CoT] AVISO: {provider}/{model} cerró el stream sin texto. "
            "Revisa API key, créditos/cuota y el nombre del modelo.",
            flush=True,
        )
    return text


def _strip_qwen_thinking(text):
    """Remove reasoning/thinking blocks so they are not spoken by TTS.

    Cubre varios formatos de modelos de razonamiento (qwen, nemotron, etc.):
    <think>, <thinking>, <reasoning>, <analysis>, <scratchpad>.
    """
    tags = r"(think|thinking|reasoning|analysis|scratchpad)"
    # Bloques completos <tag>...</tag>
    text = re.sub(
        rf"<\s*{tags}\s*>.*?<\s*/\s*\1\s*>",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    # Etiquetas sueltas que algún modelo deja sin cerrar.
    text = re.sub(rf"<\s*/?\s*{tags}\s*>", "", text, flags=re.IGNORECASE)
    return text.strip()


def _cot_log_enabled() -> bool:
    """¿Imprimir el CoT/razonamiento crudo en la terminal?

    Activo por defecto para diagnosticar atascos (modelos que piensan mucho
    y no emiten respuesta). Desactivar con ``LLM_LOG_COT=0``.
    """
    return _env("LLM_LOG_COT", "1").lower() not in ("0", "false", "no", "off")


def _cot_print(text: str, *, end: str = "", prefix: str | None = None) -> None:
    """Escribe en stdout con flush inmediato (imprescindible para ver el stream en vivo)."""
    if not _cot_log_enabled() or text is None:
        return
    if prefix:
        print(prefix, end="", flush=True)
    print(text, end=end, flush=True)


def _dump_raw_reply(label: str, text: str, *, extra: str | None = None) -> None:
    """Vuelca la respuesta cruda (CoT incluido) al terminar un turno no-streaming."""
    if not _cot_log_enabled():
        return
    print(f"\n[LLM/CoT] --- raw reply ({label}) ---", flush=True)
    if extra:
        print(extra, flush=True)
    if text:
        print(text, end="" if text.endswith("\n") else "\n", flush=True)
    else:
        print("(vacío)", flush=True)
    stripped = _strip_qwen_thinking(text or "")
    think_chars = max(0, len(text or "") - len(stripped))
    print(
        f"[LLM/CoT] --- fin raw | total={len(text or '')} chars, "
        f"~cot={think_chars}, respuesta={len(stripped)} ---",
        flush=True,
    )


class _CotStreamMirror:
    """Espejo del stream LLM en terminal: CoT + respuesta, en vivo.

    Detecta bloques ``<think>…</think>`` (y variantes) para etiquetar el
    tramo de razonamiento. Si el proveedor manda ``reasoning_content``
    aparte, también lo imprime. Sirve para ver *dónde* se traba el modelo
    cuando "no responde".
    """

    _OPEN_RE = re.compile(
        r"<\s*(think|thinking|reasoning|analysis|scratchpad)\s*>",
        re.IGNORECASE,
    )
    _CLOSE_RE = re.compile(
        r"<\s*/\s*(think|thinking|reasoning|analysis|scratchpad)\s*>",
        re.IGNORECASE,
    )

    def __init__(self, backend: str, model: str | None = None):
        self.backend = backend
        self.model = model or "?"
        self.t0 = time.monotonic()
        self.first_token_at: float | None = None
        self.in_think = False
        self.think_chars = 0
        self.answer_chars = 0
        self.reasoning_chars = 0  # campo separado (reasoning_content)
        self.chunks = 0
        self._header_done = False
        # Cola corta para no partir etiquetas a medias entre chunks.
        self._tail = ""

    def _ensure_header(self) -> None:
        if self._header_done or not _cot_log_enabled():
            return
        self._header_done = True
        print(
            f"\n[LLM/CoT] stream start backend={self.backend} model={self.model}",
            flush=True,
        )

    def _mark_first(self) -> None:
        if self.first_token_at is None:
            self.first_token_at = time.monotonic()
            latency = self.first_token_at - self.t0
            _cot_print(f"[LLM/CoT] primer token a {latency:.1f}s\n")

    def feed_reasoning(self, text: str) -> None:
        """Campo de razonamiento separado (OpenRouter/DeepSeek/Qwen, etc.)."""
        if not text:
            return
        self._ensure_header()
        self._mark_first()
        self.reasoning_chars += len(text)
        self.chunks += 1
        if not self.in_think:
            _cot_print("\n[CoT] ", end="")
            self.in_think = True  # visual: estamos en tramo de pensamiento
        _cot_print(text)

    def feed(self, text: str) -> None:
        """Trozo de ``delta.content`` (puede mezclar CoT etiquetado + respuesta)."""
        if not text:
            return
        self._ensure_header()
        self._mark_first()
        self.chunks += 1

        if not _cot_log_enabled():
            # Seguimos contando por si alguien habilita el log a mitad de turno.
            self.answer_chars += len(text)
            return

        buf = self._tail + text
        self._tail = ""
        i = 0
        while i < len(buf):
            if self.in_think:
                m = self._CLOSE_RE.search(buf, i)
                if not m:
                    # Puede estar cortada la etiqueta de cierre al final.
                    hold = min(24, len(buf) - i)
                    piece = buf[i : len(buf) - hold] if hold else buf[i:]
                    self._tail = buf[len(buf) - hold :] if hold else ""
                    if piece:
                        self.think_chars += len(piece)
                        _cot_print(piece)
                    return
                piece = buf[i : m.start()]
                if piece:
                    self.think_chars += len(piece)
                    _cot_print(piece)
                _cot_print(m.group(0))  # cierra etiqueta visible
                self.think_chars += len(m.group(0))
                self.in_think = False
                _cot_print("\n[LLM] ")
                i = m.end()
            else:
                m = self._OPEN_RE.search(buf, i)
                if not m:
                    hold = min(24, len(buf) - i)
                    piece = buf[i : len(buf) - hold] if hold else buf[i:]
                    self._tail = buf[len(buf) - hold :] if hold else ""
                    if piece:
                        self.answer_chars += len(piece)
                        _cot_print(piece)
                    return
                piece = buf[i : m.start()]
                if piece:
                    self.answer_chars += len(piece)
                    _cot_print(piece)
                _cot_print(f"\n[CoT] {m.group(0)}")
                self.think_chars += len(m.group(0))
                self.in_think = True
                i = m.end()

    def finish(self, *, error: str | None = None) -> None:
        if not _cot_log_enabled():
            return
        # Vaciar cola residual.
        if self._tail:
            if self.in_think:
                self.think_chars += len(self._tail)
            else:
                self.answer_chars += len(self._tail)
            _cot_print(self._tail)
            self._tail = ""
        elapsed = time.monotonic() - self.t0
        first = (
            f"{self.first_token_at - self.t0:.1f}s"
            if self.first_token_at is not None
            else "nunca"
        )
        print(
            f"\n[LLM/CoT] stream end backend={self.backend} "
            f"elapsed={elapsed:.1f}s first_token={first} "
            f"chunks={self.chunks} cot={self.think_chars + self.reasoning_chars} "
            f"respuesta={self.answer_chars}"
            + (f" error={error}" if error else ""),
            flush=True,
        )
        if self.first_token_at is None and not error:
            print(
                "[LLM/CoT] AVISO: el backend no emitió ningún token "
                "(timeout, modelo cargando, o respuesta vacía).",
                flush=True,
            )
        elif self.answer_chars == 0 and (self.think_chars + self.reasoning_chars) > 0:
            print(
                "[LLM/CoT] AVISO: solo hubo razonamiento (CoT), sin respuesta "
                "útil. Suele pasar si LLM_MAX_TOKENS se agota en el thinking.",
                flush=True,
            )


def _chat_with_ollama(messages):
    model = _ollama_model_name()
    timeout = _env_float("OLLAMA_TIMEOUT_SECONDS", 60.0)
    if _cot_log_enabled():
        print(
            f"[LLM/CoT] request provider=ollama model={model} "
            f"timeout={timeout:.0f}s mode=blocking",
            flush=True,
        )
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        # Mantener el modelo cargado en memoria entre turnos evita el costoso
        # tiempo de recarga (~60s en CPU) en cada pregunta.
        "keep_alive": _env("OLLAMA_KEEP_ALIVE", "30m"),
        "options": {
            "temperature": 0.6,
            "top_p": 0.9,
            "num_predict": _max_tokens(),
        },
    }

    try:
        response = _ollama_request(
            "/api/chat",
            payload=payload,
            # Timeout más corto: si el modelo local no responde a tiempo es
            # preferible caer al siguiente backend que dejar al usuario esperando.
            timeout=timeout,
        )
    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8", errors="replace")
        raise LLMBackendError(f"Ollama respondió {error.code}: {error_body}") from error
    except urllib.error.URLError as error:
        raise LLMBackendError(
            "No pude conectarme con Ollama. Verifica que el servicio esté iniciado."
        ) from error

    message = response.get("message", {}) or {}
    content = message.get("content", "") or ""
    # Algunos modelos (p. ej. razonadores en Ollama) devuelven thinking aparte.
    thinking = message.get("thinking") or message.get("reasoning") or ""
    extra = f"[thinking field]\n{thinking}" if thinking else None
    raw = f"{thinking}\n{content}".strip() if thinking else content
    _dump_raw_reply(f"ollama/{model}", raw, extra=extra)
    return _strip_qwen_thinking(content)


def _chat_with_claude_native(messages):
    from anthropic import Anthropic

    api_key, model, _ = _require("claude_native")
    timeout = _request_timeout()
    if _cot_log_enabled():
        print(
            f"[LLM/CoT] request provider=claude_native model={model} "
            f"timeout={timeout:.0f}s mode=stream-accumulate",
            flush=True,
        )
    client = Anthropic(api_key=api_key, timeout=timeout)

    # Format messages for Anthropic
    system_content = "\n".join([m["content"] for m in messages if m["role"] == "system"])
    user_messages = [m for m in messages if m["role"] != "system"]

    formatted_messages = []
    for m in user_messages:
        role = m["role"] if m["role"] in ["user", "assistant"] else "user"
        formatted_messages.append({"role": role, "content": m["content"]})

    mirror = _CotStreamMirror("claude_native", model)
    parts: list[str] = []
    try:
        with client.messages.stream(
            model=model,
            max_tokens=_max_tokens(),
            system=system_content,
            messages=formatted_messages,
            temperature=0.6,
        ) as stream:
            for text in stream.text_stream:
                mirror.feed(text)
                parts.append(text)
        mirror.finish()
    except Exception as error:
        mirror.finish(error=str(error))
        raise LLMBackendError(
            f"claude_native/{model} falló o agotó timeout ({timeout:.0f}s): {error}"
        ) from error

    return "".join(parts).strip()


def _is_mostly_english(text):
    """Heuristic: return True only when the text is clearly English.

    Se exige evidencia fuerte (>=2 frases típicas en inglés). Antes había una
    regla por "proporción de palabras ASCII" que marcaba por error respuestas
    válidas en español sin tildes (p. ej. "Claro, con gusto te ayudo con eso"),
    devolviendo "no pude generar una respuesta". Esa regla se eliminó.
    """
    english_markers = [
        "welcome", "how can i help", "feel free", "let me know",
        "i'm here", "happy to help", "what would you like",
        "please let me", "don't hesitate", "i can help",
        "our programs", "we offer", "thank you", "i would", "you can",
    ]
    lower = text.lower()
    matches = sum(1 for marker in english_markers if marker in lower)
    return matches >= 2


def _postprocess_reply(text):
    """Clean up LLM response: strip thinking blocks and handle language issues."""
    # Limpiar bloques de razonamiento internos
    text = _strip_qwen_thinking(text)
    if not text.strip():
        return "Lo siento, no pude generar una respuesta. ¿Podrías repetir tu pregunta?"
    # Detectar respuestas en inglés y reemplazarlas
    if _is_mostly_english(text):
        # Antes esto DESCARTABA la respuesta y devolvía un "tuve un problema",
        # convirtiendo una respuesta válida en una no-respuesta (síntoma C). El
        # refuerzo de idioma ya vive en el prompt (`_build_messages`); aquí solo
        # registramos el aviso y entregamos el texto del modelo tal cual.
        print(f"[LLM] AVISO: respuesta posiblemente en inglés (se entrega igual): {text[:80]}...")
    return text


def generate_reply(user_input, system_prompt, university_context, camera_context=None):
    messages = _build_messages(user_input, system_prompt, university_context, camera_context)

    for backend in _candidate_backends(get_selected_backend()):
        if backend == "local_only":
            return _local_only_reply(user_input)

        try:
            if _cot_log_enabled():
                print(
                    f"[LLM/CoT] intento voice/blocking backend={backend} "
                    f"(tokens en vivo vía stream interno)",
                    flush=True,
                )
            reply = _chat_with_backend(backend, messages)
            return _postprocess_reply(reply)
        except Exception as error:
            print(f"[LLM] Error usando backend '{backend}', probando fallback: {error}")

    return _local_only_reply(user_input)


def _delta_reasoning(delta) -> str:
    """Extrae CoT de campos separados del delta (si el proveedor los manda)."""
    if delta is None:
        return ""
    for attr in ("reasoning_content", "reasoning", "thinking"):
        value = getattr(delta, attr, None)
        if isinstance(value, str) and value:
            return value
    # Algunos SDKs exponen model_extra / dict-like.
    extra = getattr(delta, "model_extra", None) or {}
    if isinstance(extra, dict):
        for key in ("reasoning_content", "reasoning", "thinking"):
            value = extra.get(key)
            if isinstance(value, str) and value:
                return value
    return ""


async def _stream_backend_response(backend, messages):
    if backend == "ollama":
        from openai import AsyncOpenAI
        model = _ollama_model_name()
        base_url = f"{_ollama_base_url()}/v1"
        client = AsyncOpenAI(
            api_key="ollama",
            base_url=base_url,
            timeout=_env_float("OLLAMA_TIMEOUT_SECONDS", 60.0),
        )

    elif backend == "claude_native":
        from anthropic import AsyncAnthropic
        api_key, model, _ = _require("claude_native")
        timeout = _request_timeout()
        client = AsyncAnthropic(api_key=api_key, timeout=timeout)
        system_content = "\n".join([m["content"] for m in messages if m["role"] == "system"])
        user_messages = [m for m in messages if m["role"] != "system"]
        formatted_messages = []
        for m in user_messages:
            role = m["role"] if m["role"] in ["user", "assistant"] else "user"
            formatted_messages.append({"role": role, "content": m["content"]})

        mirror = _CotStreamMirror("claude_native", model)
        try:
            if _cot_log_enabled():
                print(
                    f"[LLM/CoT] request provider=claude_native model={model} "
                    f"mode=async-stream",
                    flush=True,
                )
            async with client.messages.stream(
                model=model,
                max_tokens=_max_tokens(),
                system=system_content,
                messages=formatted_messages,
                temperature=0.6,
            ) as stream:
                async for text in stream.text_stream:
                    mirror.feed(text)
                    yield text
            mirror.finish()
        except Exception as error:
            mirror.finish(error=str(error))
            raise
        return

    elif backend in PROVIDERS and PROVIDERS[backend].openai_compatible:
        from openai import AsyncOpenAI
        api_key, model, base_url = _require(backend)
        timeout = _request_timeout()
        client = AsyncOpenAI(
            api_key=api_key or "none",
            base_url=base_url or None,
            timeout=timeout,
        )

    else:
        raise LLMBackendError(f"Backend no soportado para streaming: {backend}")

    mirror = _CotStreamMirror(backend, model)
    try:
        if _cot_log_enabled():
            print(
                f"[LLM/CoT] request provider={backend} model={model} mode=async-stream",
                flush=True,
            )
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.6,
            max_tokens=_max_tokens(),
            stream=True,
        )
        async for chunk in response:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            reasoning = _delta_reasoning(delta)
            if reasoning:
                mirror.feed_reasoning(reasoning)
            content = delta.content if delta is not None else None
            if content:
                mirror.feed(content)
                yield content
        mirror.finish()
    except Exception as error:
        mirror.finish(error=str(error))
        raise


async def stream_llm_response(
    prompt: str, camera_context: str | None = None
) -> AsyncGenerator[str, None]:
    """Generador asíncrono para transmitir la respuesta del LLM en tiempo real.

    ``camera_context`` debe inyectarlo el llamador (p. ej. el
    ``ConversationService`` vía ``CameraContextProvider``). No se recurre a
    ``call``: inyectarlo rompe el ciclo ``call ↔ llm_backend`` y evita que la
    capa de LLM dependa del estado global de la CLI.
    """
    try:
        from skills.event_mode import get_system_prompt
        from skills.university import get_university_context
        system_prompt = get_system_prompt("normal")
        university_context = get_university_context()
    except ImportError:
        system_prompt = "Eres un asistente de la UNEV."
        university_context = ""

    messages = _build_messages(prompt, system_prompt, university_context, camera_context)

    # La selección de backend sondea la readiness de Ollama (HTTP bloqueante, aun
    # estando cacheada con TTL). Sacarla del hilo del event loop con `to_thread`
    # evita que un sondeo ocasional congele el video y los demás mensajes mientras
    # Python espera el `urlopen` (síntoma A).
    backends = await asyncio.to_thread(
        lambda: _candidate_backends(get_selected_backend())
    )
    for backend in backends:
        if backend == "local_only":
            yield _local_only_reply(prompt)
            return

        produced = False
        try:
            if _cot_log_enabled():
                print(f"[LLM/CoT] intento stream backend={backend}", flush=True)
            async for chunk in _stream_backend_response(backend, messages):
                produced = True
                yield chunk
            return
        except Exception as error:
            print(f"[LLM] Error usando backend '{backend}', probando fallback: {error}")
            if produced:
                # Ya se emitió texto parcial de este backend; reiniciar con otro
                # mezclaría dos respuestas distintas. Cerramos el turno aquí.
                return

    yield _local_only_reply(prompt)
