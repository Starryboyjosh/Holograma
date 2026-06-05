import json
import os
import re
import urllib.error
import urllib.request

DEFAULT_OLLAMA_MODEL = "gemma4:e4b"
VALID_BACKENDS = {"auto", "nvidia", "openai", "ollama", "local_only"}


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

    if _env("NVIDIA_API_KEY"):
        return "nvidia"

    if _env("OPENAI_API_KEY"):
        return "openai"

    if _ollama_ready():
        return "ollama"

    return "local_only"


def get_backend_status():
    backend = get_selected_backend()

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
            "content": user_input,
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
        if backend == "nvidia":
            return _chat_with_nvidia(messages)

        if backend == "openai":
            return _chat_with_openai(messages)

        if backend == "ollama":
            return _chat_with_ollama(messages)

        raise LLMBackendError(f"Backend no soportado: {backend}")
    except Exception as error:
        print(f"[LLM] Error usando backend '{backend}': {error}")
        return (
            "Tuve un problema conectándome con el modelo de lenguaje. "
            "Mientras tanto, puedes preguntarme por carreras, admisiones, ubicación o información oficial de UNEV."
        )
