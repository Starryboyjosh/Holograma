import json
import os
import re
import urllib.error
import urllib.request
from typing import AsyncGenerator
from dotenv import load_dotenv

load_dotenv()

DEFAULT_OLLAMA_MODEL = "gemma3:1b"
VALID_BACKENDS = {"auto", "nvidia", "openai", "ollama", "local_only", "openrouter", "claude_native"}


class LLMBackendError(Exception):
    pass


from utils import _env, _env_float


def _ollama_base_url():
    return _env("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")


def _ollama_model_name():
    return _env("OLLAMA_MODEL") or DEFAULT_OLLAMA_MODEL


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


def _ollama_ready():
    return _ollama_server_available() and _ollama_model_available()


def get_selected_backend():
    requested_backend = _env("LLM_BACKEND", "auto").lower()

    if requested_backend not in VALID_BACKENDS:
        print(f"[LLM] Backend inválido '{requested_backend}'. Usando 'auto'.")
        requested_backend = "auto"

    if requested_backend != "auto":
        return requested_backend

    # Check LLM_PROVIDER first if configured
    provider = _env("LLM_PROVIDER")
    if provider:
        provider = provider.lower()
        if provider == "openrouter" and _env("OPENROUTER_API_KEY"):
            return "openrouter"
        if provider == "claude_native" and _env("ANTHROPIC_API_KEY"):
            return "claude_native"
        if provider == "openai" and _env("OPENAI_API_KEY"):
            return "openai"
        if provider == "nvidia" and _env("NVIDIA_API_KEY"):
            return "nvidia"

    if _env("OPENROUTER_API_KEY"):
        return "openrouter"

    if _env("NVIDIA_API_KEY"):
        return "nvidia"

    if _env("OPENAI_API_KEY"):
        return "openai"

    if _env("ANTHROPIC_API_KEY"):
        return "claude_native"

    if _ollama_ready():
        return "ollama"

    return "local_only"


def get_backend_status():
    backend = get_selected_backend()

    if backend == "openrouter":
        model = _env("LLM_MODEL", "meta-llama/llama-3.3-70b-instruct")
        return f"Backend activo: OpenRouter API con modelo {model}."

    if backend == "claude_native":
        model = _env("LLM_MODEL", "claude-3-5-sonnet-latest")
        return f"Backend activo: Anthropic API con modelo {model}."

    if backend == "nvidia":
        model = _env("NVIDIA_MODEL", "moonshotai/kimi-k2.6")
        return f"Backend activo: NVIDIA NIM API con modelo {model}."

    if backend == "openai":
        model = _env("OPENAI_MODEL", "gpt-4o-mini")
        return f"Backend activo: OpenAI API con modelo {model}."

    if backend == "ollama":
        model = _ollama_model_name()
        if not _ollama_server_available():
            return (
                "Backend solicitado: Ollama, pero el servicio no está respondiendo. "
                "Inicia Ollama o usa LLM_BACKEND=local_only."
            )

        if not _ollama_model_available(model):
            return (
                f"Backend solicitado: Ollama, pero no encontré el modelo {model}. "
                f"Descárgalo con: ollama pull {model}"
            )

        return f"Backend activo: Ollama local con modelo {model}."

    return "Backend activo: local_only. Solo se responderán skills locales."


def _candidate_backends(primary_backend):
    candidates = []
    for backend in [primary_backend, "ollama" if _ollama_ready() else None, "local_only"]:
        if backend and backend not in candidates:
            candidates.append(backend)
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
    if backend == "openrouter":
        return _chat_with_openrouter(messages)
    if backend == "claude_native":
        return _chat_with_claude_native(messages)
    if backend == "nvidia":
        return _chat_with_nvidia(messages)
    if backend == "openai":
        return _chat_with_openai(messages)
    if backend == "ollama":
        return _chat_with_ollama(messages)
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


def _chat_with_nvidia(messages):
    from openai import OpenAI

    api_key = _env("NVIDIA_API_KEY")
    if not api_key:
        raise LLMBackendError("Falta NVIDIA_API_KEY.")

    model = _env("NVIDIA_MODEL", "moonshotai/kimi-k2.6")
    base_url = _env("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")

    client = OpenAI(api_key=api_key, base_url=base_url)
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.6,
        top_p=0.9,
        max_tokens=450,
    )

    return (response.choices[0].message.content or "").strip()


def _chat_with_openai(messages):
    from openai import OpenAI

    api_key = _env("OPENAI_API_KEY")
    if not api_key:
        raise LLMBackendError("Falta OPENAI_API_KEY.")

    model = _env("OPENAI_MODEL", "gpt-4o-mini")

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.6,
        max_tokens=450,
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
            "num_predict": 350,
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


def _chat_with_openrouter(messages):
    from openai import OpenAI

    api_key = _env("OPENROUTER_API_KEY")
    if not api_key:
        raise LLMBackendError("Falta OPENROUTER_API_KEY.")

    model = _env("LLM_MODEL", "meta-llama/llama-3.3-70b-instruct")
    base_url = "https://openrouter.ai/api/v1"

    client = OpenAI(api_key=api_key, base_url=base_url)
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.6,
        max_tokens=300,
    )

    return (response.choices[0].message.content or "").strip()


def _chat_with_claude_native(messages):
    from anthropic import Anthropic

    api_key = _env("ANTHROPIC_API_KEY")
    if not api_key:
        raise LLMBackendError("Falta ANTHROPIC_API_KEY.")

    model = _env("LLM_MODEL", "claude-3-5-sonnet-latest")

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
        max_tokens=450,
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
        print(f"[LLM] AVISO: Respuesta detectada en inglés, descartando: {text[:80]}...")
        return (
            "Disculpa, tuve un problema al generar mi respuesta. "
            "¿Podrías repetir tu pregunta?"
        )
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
    if backend == "openai":
        from openai import AsyncOpenAI
        api_key = _env("OPENAI_API_KEY")
        if not api_key:
            raise LLMBackendError("Falta la variable de entorno OPENAI_API_KEY.")
        model = _env("OPENAI_MODEL", "gpt-4o-mini")
        client = AsyncOpenAI(api_key=api_key)

    elif backend == "openrouter":
        from openai import AsyncOpenAI
        api_key = _env("OPENROUTER_API_KEY")
        if not api_key:
            raise LLMBackendError("Falta la variable de entorno OPENROUTER_API_KEY.")
        model = _env("LLM_MODEL", "meta-llama/llama-3.3-70b-instruct")
        client = AsyncOpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")

    elif backend == "nvidia":
        from openai import AsyncOpenAI
        api_key = _env("NVIDIA_API_KEY")
        if not api_key:
            raise LLMBackendError("Falta la variable de entorno NVIDIA_API_KEY.")
        model = _env("NVIDIA_MODEL", "moonshotai/kimi-k2.6")
        base_url = _env("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    elif backend == "ollama":
        from openai import AsyncOpenAI
        model = _ollama_model_name()
        base_url = f"{_ollama_base_url()}/v1"
        client = AsyncOpenAI(api_key="ollama", base_url=base_url)

    elif backend == "claude_native":
        from anthropic import AsyncAnthropic
        api_key = _env("ANTHROPIC_API_KEY")
        if not api_key:
            raise LLMBackendError("Falta la variable de entorno ANTHROPIC_API_KEY.")
        model = _env("LLM_MODEL", "claude-3-5-sonnet-latest")
        client = AsyncAnthropic(api_key=api_key)
        system_content = "\n".join([m["content"] for m in messages if m["role"] == "system"])
        user_messages = [m for m in messages if m["role"] != "system"]
        formatted_messages = []
        for m in user_messages:
            role = m["role"] if m["role"] in ["user", "assistant"] else "user"
            formatted_messages.append({"role": role, "content": m["content"]})

        async with client.messages.stream(
            model=model,
            max_tokens=1024,
            system=system_content,
            messages=formatted_messages,
            temperature=0.6,
        ) as stream:
            async for text in stream.text_stream:
                yield text
        return

    else:
        raise LLMBackendError(f"Backend no soportado para streaming: {backend}")

    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.6,
        stream=True,
    )
    async for chunk in response:
        content = chunk.choices[0].delta.content
        if content:
            yield content


async def stream_llm_response(prompt: str) -> AsyncGenerator[str, None]:
    """Generador asíncrono para transmitir la respuesta del LLM en tiempo real."""
    try:
        from skills.event_mode import get_system_prompt
        from skills.university import get_university_context
        system_prompt = get_system_prompt("normal")
        university_context = get_university_context()
    except ImportError:
        system_prompt = "Eres un asistente de la UNEV."
        university_context = ""

    # Obtener contexto de la cámara si hay una pregunta visual o un saludo
    camera_context = None
    try:
        from call import _last_camera_analysis, _build_camera_context
        if _last_camera_analysis:
            camera_context = _build_camera_context(_last_camera_analysis)
    except ImportError:
        pass

    messages = _build_messages(prompt, system_prompt, university_context, camera_context)

    for backend in _candidate_backends(get_selected_backend()):
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
