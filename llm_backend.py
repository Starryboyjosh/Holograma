import os
import re

DEFAULT_OLLAMA_MODEL = "qwen3:8b"
VALID_BACKENDS = {"auto", "nvidia", "openai", "ollama", "local_only"}


class LLMBackendError(Exception):
    pass


def _env(name, default=None):
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return value.strip()


def _ollama_python_package_available():
    try:
        import ollama  # noqa: F401
    except ImportError:
        return False

    return True


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

    if _ollama_python_package_available():
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
        model = _env("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
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
    import ollama

    model = _env("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
    response = ollama.chat(
        model=model,
        messages=messages,
        options={
            "temperature": 0.6,
            "top_p": 0.9,
            "num_predict": 350,
        },
    )
    return _strip_qwen_thinking(response["message"]["content"])


def generate_reply(user_input, system_prompt, university_context):
    backend = get_selected_backend()
    messages = _build_messages(user_input, system_prompt, university_context)

    if backend == "local_only":
        return (
            "Por ahora estoy en modo local. Puedo responder preguntas básicas sobre UNEV, "
            "sus carreras, admisiones, ubicación y aprobación oficial. Para conversación abierta, "
            "configura NVIDIA_API_KEY, OPENAI_API_KEY o un modelo de Ollama."
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
