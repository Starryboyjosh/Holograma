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
    """Chat con cualquier backend compatible con OpenAI (openrouter/openai/nvidia/custom)."""
    from openai import OpenAI

    api_key, model, base_url = _require(provider)
    client = OpenAI(api_key=api_key or "none", base_url=base_url or None)
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.6,
        max_tokens=_max_tokens(),
    )
    return (response.choices[0].message.content or "").strip()


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


def _chat_with_ollama(messages):
    model = _ollama_model_name()
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
            timeout=_env_float("OLLAMA_TIMEOUT_SECONDS", 60.0),
        )
    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8", errors="replace")
        raise LLMBackendError(f"Ollama respondió {error.code}: {error_body}") from error
    except urllib.error.URLError as error:
        raise LLMBackendError(
            "No pude conectarme con Ollama. Verifica que el servicio esté iniciado."
        ) from error

    content = response.get("message", {}).get("content", "")
    return _strip_qwen_thinking(content)


def _chat_with_claude_native(messages):
    from anthropic import Anthropic

    api_key, model, _ = _require("claude_native")

    client = Anthropic(api_key=api_key)

    # Format messages for Anthropic
    system_content = "\n".join([m["content"] for m in messages if m["role"] == "system"])
    user_messages = [m for m in messages if m["role"] != "system"]

    formatted_messages = []
    for m in user_messages:
        role = m["role"] if m["role"] in ["user", "assistant"] else "user"
        formatted_messages.append({"role": role, "content": m["content"]})

    response = client.messages.create(
        model=model,
        max_tokens=_max_tokens(),
        system=system_content,
        messages=formatted_messages,
        temperature=0.6
    )

    return "".join([block.text for block in response.content if hasattr(block, 'text')]).strip()


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
            reply = _chat_with_backend(backend, messages)
            return _postprocess_reply(reply)
        except Exception as error:
            print(f"[LLM] Error usando backend '{backend}', probando fallback: {error}")

    return _local_only_reply(user_input)


async def _stream_backend_response(backend, messages):
    if backend == "ollama":
        from openai import AsyncOpenAI
        model = _ollama_model_name()
        base_url = f"{_ollama_base_url()}/v1"
        client = AsyncOpenAI(api_key="ollama", base_url=base_url)

    elif backend == "claude_native":
        from anthropic import AsyncAnthropic
        api_key, model, _ = _require("claude_native")
        client = AsyncAnthropic(api_key=api_key)
        system_content = "\n".join([m["content"] for m in messages if m["role"] == "system"])
        user_messages = [m for m in messages if m["role"] != "system"]
        formatted_messages = []
        for m in user_messages:
            role = m["role"] if m["role"] in ["user", "assistant"] else "user"
            formatted_messages.append({"role": role, "content": m["content"]})

        async with client.messages.stream(
            model=model,
            max_tokens=_max_tokens(),
            system=system_content,
            messages=formatted_messages,
            temperature=0.6,
        ) as stream:
            async for text in stream.text_stream:
                yield text
        return

    elif backend in PROVIDERS and PROVIDERS[backend].openai_compatible:
        from openai import AsyncOpenAI
        api_key, model, base_url = _require(backend)
        client = AsyncOpenAI(api_key=api_key or "none", base_url=base_url or None)

    else:
        raise LLMBackendError(f"Backend no soportado para streaming: {backend}")

    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.6,
        max_tokens=_max_tokens(),
        stream=True,
    )
    async for chunk in response:
        content = chunk.choices[0].delta.content
        if content:
            yield content


async def stream_llm_response(
    prompt: str, camera_context: str | None = None
) -> AsyncGenerator[str, None]:
    """Generador asíncrono para transmitir la respuesta del LLM en tiempo real.

    ``camera_context`` lo puede inyectar el llamador (p. ej. el
    ``ConversationService`` de ``app/``). Si llega como ``None`` se recurre al
    import perezoso de ``call`` por compatibilidad con la ruta heredada; inyectarlo
    rompe el ciclo ``call ↔ llm_backend``.
    """
    try:
        from skills.event_mode import get_system_prompt
        from skills.university import get_university_context
        system_prompt = get_system_prompt("normal")
        university_context = get_university_context()
    except ImportError:
        system_prompt = "Eres un asistente de la UNEV."
        university_context = ""

    # Contexto de cámara: si el llamador no lo inyectó, recurrimos al import
    # perezoso de `call` (ruta heredada). Mantener este fallback aquí evita romper
    # el voice loop actual mientras la nueva capa de servicios inyecta el contexto.
    if camera_context is None:
        try:
            from call import _build_camera_context, _last_camera_analysis
            if _last_camera_analysis:
                camera_context = _build_camera_context(_last_camera_analysis)
        except ImportError:
            pass

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
