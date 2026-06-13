import json
import os
import re
import urllib.error
import urllib.request
from typing import AsyncGenerator
from dotenv import load_dotenv

load_dotenv()

DEFAULT_OLLAMA_MODEL = "gemma4:e4b"
VALID_BACKENDS = {"auto", "nvidia", "openai", "ollama", "local_only", "openrouter", "claude_native"}


class LLMBackendError(Exception):
    pass


def _env(name, default=None):
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return value.strip()


def _env_float(name, default):
    value = _env(name)
    if value is None:
        return default

    try:
        return float(value)
    except ValueError:
        return default


def _ollama_base_url():
    return _env("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")


def _ollama_model_name():
    return _env("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)


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


def _build_messages(user_input, system_prompt, university_context):
    # Reforzar idioma español en el mensaje del usuario para modelos débiles
    user_content = f"{user_input}\n\n[Instrucción: responde siempre en español.]"
    return [
        {
            "role": "system",
            "content": system_prompt,
        },
        {
            "role": "system",
            "content": university_context,
        },
        {
            "role": "user",
            "content": user_content,
        },
    ]


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
    """Remove Qwen3 thinking blocks so they are not spoken by TTS."""
    return re.sub(
        r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE
    ).strip()


def _chat_with_ollama(messages):
    model = _ollama_model_name()
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
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
            timeout=_env_float("OLLAMA_TIMEOUT_SECONDS", 120.0),
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
    """Heuristic: return True if text looks like it's mostly in English."""
    english_markers = [
        "welcome", "how can i help", "feel free", "let me know",
        "i'm here", "happy to help", "what would you like",
        "please let me", "don't hesitate", "i can help",
        "our programs", "we offer", "thank you",
    ]
    lower = text.lower()
    matches = sum(1 for marker in english_markers if marker in lower)
    # Si tiene 2+ marcadores de inglés, probablemente es inglés
    if matches >= 2:
        return True
    # Heurística por proporción de palabras con caracteres ASCII-only
    words = text.split()
    if not words:
        return False
    ascii_words = sum(1 for w in words if w.isascii())
    # Si >85% de las palabras son puro ASCII y no tiene acentos españoles
    spanish_chars = set("áéíóúñüÁÉÍÓÚÑÜ¿¡")
    has_spanish = any(c in text for c in spanish_chars)
    if not has_spanish and len(words) > 5 and ascii_words / len(words) > 0.85:
        return True
    return False


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


def generate_reply(user_input, system_prompt, university_context):
    backend = get_selected_backend()
    messages = _build_messages(user_input, system_prompt, university_context)

    if backend == "local_only":
        return (
            "Por ahora estoy en modo local. Puedo responder preguntas básicas sobre UNEV, "
            "sus carreras, admisiones, ubicación y aprobación oficial. Para conversación abierta, "
            "configura NVIDIA_API_KEY, OPENAI_API_KEY o instala Ollama con el modelo recomendado."
        )

    try:
        if backend == "openrouter":
            reply = _chat_with_openrouter(messages)
        elif backend == "claude_native":
            reply = _chat_with_claude_native(messages)
        elif backend == "nvidia":
            reply = _chat_with_nvidia(messages)
        elif backend == "openai":
            reply = _chat_with_openai(messages)
        elif backend == "ollama":
            reply = _chat_with_ollama(messages)
        else:
            raise LLMBackendError(f"Backend no soportado: {backend}")

        return _postprocess_reply(reply)
    except Exception as error:
        print(f"[LLM] Error usando backend '{backend}': {error}")
        return (
            "Tuve un problema conectándome con el modelo de lenguaje. "
            "Mientras tanto, puedes preguntarme por carreras, admisiones, ubicación o información oficial de UNEV."
        )


async def stream_llm_response(prompt: str) -> AsyncGenerator[str, None]:
    """Generador asíncrono para transmitir la respuesta del LLM en tiempo real."""
    provider = os.getenv("LLM_PROVIDER", "openrouter").lower().strip()
    model = os.getenv("LLM_MODEL", "meta-llama/llama-3.3-70b-instruct").strip()

    try:
        from skills.event_mode import get_system_prompt
        from skills.university import get_university_context
        system_prompt = get_system_prompt("normal")
        university_context = get_university_context()
    except ImportError:
        system_prompt = "Eres un asistente de la UNEV."
        university_context = ""

    messages = _build_messages(prompt, system_prompt, university_context)

    if provider == "openai":
        from openai import AsyncOpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise LLMBackendError("Falta la variable de entorno OPENAI_API_KEY.")
        client = AsyncOpenAI(api_key=api_key)
        
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.6,
            stream=True
        )
        async for chunk in response:
            content = chunk.choices[0].delta.content
            if content:
                yield content

    elif provider == "openrouter":
        from openai import AsyncOpenAI
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise LLMBackendError("Falta la variable de entorno OPENROUTER_API_KEY.")
        client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1"
        )
        
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.6,
            stream=True
        )
        async for chunk in response:
            content = chunk.choices[0].delta.content
            if content:
                yield content

    elif provider == "claude_native":
        from anthropic import AsyncAnthropic
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise LLMBackendError("Falta la variable de entorno ANTHROPIC_API_KEY.")
        client = AsyncAnthropic(api_key=api_key)
        
        # Anthropic maneja el system prompt por separado
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
            temperature=0.6
        ) as stream:
            async for text in stream.text_stream:
                yield text
    else:
        raise LLMBackendError(f"Proveedor no soportado: {provider}")

