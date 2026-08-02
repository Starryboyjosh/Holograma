"""Unified LLM provider/model configuration contract for Holograma UNEV.

Antes de este módulo, la selección de proveedor y modelo estaba dispersa y era
contradictoria:

* ``get_selected_backend`` se guiaba por ``LLM_BACKEND`` pero ``LLM_PROVIDER`` no
  tenía caso para ``ollama``; al elegir "Local" desde la interfaz, si quedaba una
  API key vieja, se seguía usando la nube en lugar de Ollama.
* Cada backend leía un nombre de modelo distinto (``LLM_MODEL``, ``OPENAI_MODEL``,
  ``NVIDIA_MODEL``, ``OLLAMA_MODEL``), pero la interfaz solo escribía ``LLM_MODEL``,
  así que el modelo elegido para OpenAI/NVIDIA se ignoraba.

Este módulo es la única fuente de verdad para:

* qué proveedores existen y cómo alcanzarlos (registro ``PROVIDERS``),
* qué backend usar según la configuración actual (``select_backend`` —
  *autoritativo*: una elección explícita nunca se sustituye en silencio por otro
  proveedor solo porque exista una key vieja),
* qué modelo / key / base-url aplica a un proveedor (``resolve_model`` y amigos).

Todas las funciones de resolución aceptan un ``env`` explícito (por defecto
``os.environ``) para ser puras y testeables sin parchear variables de proceso.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class Provider:
    """Descripción de un proveedor de LLM y cómo alcanzarlo."""

    id: str
    label: str
    description: str
    kind: str  # "cloud" | "local"
    key_env: str | None  # variable con la API key; None si no requiere key
    model_env: str | None  # variable de modelo específica del proveedor
    default_model: str
    base_url_env: str | None = None
    default_base_url: str | None = None
    openai_compatible: bool = False
    supports_discovery: bool = False
    # Los proveedores en la nube heredan LLM_MODEL si no tienen su propio override;
    # los locales (ollama) NO, para no usar por error un modelo de la nube.
    generic_model_fallback: bool = True
    # Forma de los ids que este proveedor sabe resolver, para no heredar de
    # LLM_MODEL un id imposible (ver resolve_model):
    #   "namespaced" → con barra ("meta/llama", "moonshotai/kimi-k2.6")
    #   "bare"       → sin barra ("gpt-4o-mini", "llama-3.3-70b-versatile")
    #   "any"        → sin restricción (endpoints propios: no se puede saber)
    model_id_style: str = "any"


# Registro único. El orden importa para la auto-detección (ver AUTODETECT_ORDER).
PROVIDERS: dict[str, Provider] = {
    "openrouter": Provider(
        id="openrouter",
        label="OpenRouter",
        description="Acceso unificado a muchos modelos (Llama, Gemma, etc.).",
        kind="cloud",
        key_env="OPENROUTER_API_KEY",
        model_env="LLM_MODEL",
        default_model="meta-llama/llama-3.3-70b-instruct",
        default_base_url="https://openrouter.ai/api/v1",
        openai_compatible=True,
        supports_discovery=True,
        model_id_style="namespaced",
    ),
    "openai": Provider(
        id="openai",
        label="OpenAI",
        description="Modelos GPT directamente de OpenAI.",
        kind="cloud",
        key_env="OPENAI_API_KEY",
        model_env="OPENAI_MODEL",
        default_model="gpt-4o-mini",
        base_url_env="OPENAI_BASE_URL",
        default_base_url="https://api.openai.com/v1",
        openai_compatible=True,
        supports_discovery=True,
        model_id_style="bare",
    ),
    "claude_native": Provider(
        id="claude_native",
        label="Anthropic (Claude)",
        description="Modelos Claude directamente de Anthropic.",
        kind="cloud",
        key_env="ANTHROPIC_API_KEY",
        model_env="ANTHROPIC_MODEL",
        default_model="claude-3-5-sonnet-latest",
        openai_compatible=False,
        supports_discovery=False,
        model_id_style="bare",
    ),
    "nvidia": Provider(
        id="nvidia",
        label="NVIDIA NIM",
        description="Modelos servidos por NVIDIA (endpoint compatible con OpenAI).",
        kind="cloud",
        key_env="NVIDIA_API_KEY",
        model_env="NVIDIA_MODEL",
        default_model="moonshotai/kimi-k2.6",
        base_url_env="NVIDIA_BASE_URL",
        default_base_url="https://integrate.api.nvidia.com/v1",
        openai_compatible=True,
        supports_discovery=True,
        model_id_style="namespaced",
    ),
    "groq": Provider(
        id="groq",
        label="Groq",
        description=(
            "LLM en la nube vía API key (console.groq.com). "
            "Rápido: Llama, Gemma, etc. Requiere GROQ_API_KEY."
        ),
        kind="cloud",
        key_env="GROQ_API_KEY",
        model_env="GROQ_MODEL",
        default_model="llama-3.3-70b-versatile",
        base_url_env="GROQ_BASE_URL",
        default_base_url="https://api.groq.com/openai/v1",
        openai_compatible=True,
        supports_discovery=True,
        model_id_style="bare",
    ),
    "opencode_zen": Provider(
        id="opencode_zen",
        label="OpenCode Zen",
        description=(
            "Gateway pay-per-use de OpenCode con modelos GPT/Claude/Gemini y "
            "modelos gratis (un solo API key). Requiere OPENCODE_API_KEY."
        ),
        kind="cloud",
        key_env="OPENCODE_API_KEY",
        model_env="OPENCODE_ZEN_MODEL",
        default_model="glm-4.7-free",
        base_url_env="OPENCODE_ZEN_BASE_URL",
        default_base_url="https://opencode.ai/zen/v1",
        openai_compatible=True,
        supports_discovery=True,
        model_id_style="bare",
    ),
    "custom_openai": Provider(
        id="custom_openai",
        label="Endpoint compatible con OpenAI",
        description="Servidor propio compatible con OpenAI (vLLM, LM Studio, gateway…).",
        kind="cloud",
        key_env="OPENAI_COMPAT_API_KEY",
        model_env="OPENAI_COMPAT_MODEL",
        default_model="",
        base_url_env="OPENAI_COMPAT_BASE_URL",
        default_base_url="",
        openai_compatible=True,
        supports_discovery=True,
    ),
    "ollama": Provider(
        id="ollama",
        label="Ollama local",
        description="Modelos que corren localmente con Ollama (sin internet).",
        kind="local",
        key_env=None,
        model_env="OLLAMA_MODEL",
        default_model="gemma3:1b",
        base_url_env="OLLAMA_BASE_URL",
        default_base_url="http://127.0.0.1:11434",
        openai_compatible=True,
        supports_discovery=True,
        generic_model_fallback=False,
    ),
    "local_only": Provider(
        id="local_only",
        label="Solo skills locales",
        description="Sin LLM: responde únicamente con las skills integradas de UNEV.",
        kind="local",
        key_env=None,
        model_env=None,
        default_model="",
        generic_model_fallback=False,
    ),
}

CLOUD_PROVIDERS: tuple[str, ...] = tuple(
    p.id for p in PROVIDERS.values() if p.kind == "cloud"
)

# Orden de auto-detección por key presente (solo cuando no hay elección explícita).
AUTODETECT_ORDER: tuple[str, ...] = (
    "openrouter",
    "nvidia",
    "openai",
    "groq",
    "claude_native",
    "opencode_zen",
)

# Alias históricos aceptados en LLM_PROVIDER / LLM_BACKEND.
_PROVIDER_ALIASES = {
    "local": "ollama",
    "anthropic": "claude_native",
    "claude": "claude_native",
}

# Conjunto válido para LLM_BACKEND (override explícito legado) + "auto".
VALID_BACKENDS: frozenset[str] = frozenset(set(PROVIDERS) | {"auto"})


def _norm(value: str | None) -> str:
    return (value or "").strip().lower()


def _canonical_provider(value: str | None) -> str:
    v = _norm(value)
    v = _PROVIDER_ALIASES.get(v, v)
    return v if v in PROVIDERS else ""


def select_backend(
    env: Mapping[str, str] | None = None,
    ollama_ready: Callable[[], bool] | None = None,
) -> str:
    """Devuelve el backend a usar según la configuración. Determinista.

    Reglas (en orden):

    1. ``LLM_BACKEND`` distinto de ``auto`` es un override explícito (legado).
    2. ``LLM_PROVIDER`` explícito es *autoritativo*: si el operador eligió un
       proveedor, se respeta aunque su key falte (el mensaje de error será veraz)
       y **nunca** se cambia en silencio a otro proveedor por una key vieja.
    3. Sin elección explícita: auto-detección por la primera API key presente.
    4. Sin keys: ``ollama`` si está listo (cuando se inyecta ``ollama_ready``),
       de lo contrario ``local_only``.
    """
    env = os.environ if env is None else env

    legacy = _norm(env.get("LLM_BACKEND"))
    if legacy and legacy != "auto":
        canon = _canonical_provider(legacy)
        if canon:
            return canon

    provider = _canonical_provider(env.get("LLM_PROVIDER"))
    if provider:
        return provider

    for pid in AUTODETECT_ORDER:
        key_env = PROVIDERS[pid].key_env
        if key_env and _norm(env.get(key_env)):
            return pid

    if ollama_ready is not None and not ollama_ready():
        return "local_only"
    return "ollama"


def _model_id_fits(provider: Provider, model_id: str) -> bool:
    """¿El id genérico tiene la forma que este proveedor sabe resolver?

    Sólo mira la forma del id (con o sin ``/``), nunca el catálogo remoto: no
    hay red en esta capa. ``model_id_style="any"`` acepta todo.
    """
    if provider.model_id_style == "namespaced":
        return "/" in model_id
    if provider.model_id_style == "bare":
        return "/" not in model_id
    return True


def resolve_model(provider: str, env: Mapping[str, str] | None = None) -> str:
    """Modelo efectivo para un proveedor.

    Precedencia: variable específica del proveedor (p. ej. ``OPENAI_MODEL``) >
    ``LLM_MODEL`` genérico (solo proveedores en la nube, y sólo si el id encaja
    con el proveedor) > modelo por defecto.

    Esto hace que el modelo elegido en la interfaz (``LLM_MODEL``) sí aplique a
    OpenAI/NVIDIA, sin romper a quien fije ``OPENAI_MODEL`` en ``.env``.

    El filtro por forma existe porque ``LLM_MODEL`` es *la* variable de
    OpenRouter (``openrouter.model_env == "LLM_MODEL"``), así que su valor se
    derramaba a toda la cadena de fallback: con
    ``LLM_MODEL=nvidia/nemotron-...:free``, Groq recibía un id que su API no
    conoce y fallaba tras el timeout completo, gastando el eslabón de respaldo
    sin poder responder nunca. Se descarta el id genérico cuando su forma no
    coincide con ``Provider.model_id_style`` y se cae al modelo por defecto del
    proveedor, que sí es válido; el proveedor sigue en la cadena, ahora como
    respaldo real. No se toca el override específico: si alguien fija
    ``GROQ_MODEL`` a mano, manda esa variable.
    """
    env = os.environ if env is None else env
    p = PROVIDERS.get(_canonical_provider(provider) or provider)
    if p is None:
        return ""

    if p.model_env:
        specific = (env.get(p.model_env) or "").strip()
        if specific:
            return specific

    if p.generic_model_fallback:
        generic = (env.get("LLM_MODEL") or "").strip()
        if generic and _model_id_fits(p, generic):
            return generic

    return p.default_model


def resolve_api_key(provider: str, env: Mapping[str, str] | None = None) -> str:
    env = os.environ if env is None else env
    p = PROVIDERS.get(_canonical_provider(provider) or provider)
    if p is None or not p.key_env:
        return ""
    return (env.get(p.key_env) or "").strip()


def resolve_base_url(provider: str, env: Mapping[str, str] | None = None) -> str:
    env = os.environ if env is None else env
    p = PROVIDERS.get(_canonical_provider(provider) or provider)
    if p is None:
        return ""
    if p.base_url_env:
        override = (env.get(p.base_url_env) or "").strip()
        if override:
            return override.rstrip("/")
    return (p.default_base_url or "").rstrip("/")


def configured_cloud_providers(env: Mapping[str, str] | None = None) -> list[str]:
    """IDs de proveedores en la nube con credenciales utilizables (key + modelo).

    Sirve para construir la cadena de fallback del LLM: si el proveedor primario
    falla (saldo agotado, red caída, 5xx) pero hay OTRA API key válida configurada,
    conviene intentar ese proveedor antes de degradar a Ollama/local. El orden
    sigue ``AUTODETECT_ORDER`` (determinista) y luego cualquier otro proveedor en la
    nube no listado allí, en el orden del registro.

    Un proveedor entra solo si su key y su modelo se resuelven a algo no vacío
    (``custom_openai`` además necesita base-url); así no se encolan intentos que de
    todos modos fallarían al resolver el backend.
    """
    env = os.environ if env is None else env
    ordered = list(AUTODETECT_ORDER) + [
        pid for pid in CLOUD_PROVIDERS if pid not in AUTODETECT_ORDER
    ]
    ready: list[str] = []
    for pid in ordered:
        provider = PROVIDERS.get(pid)
        if provider is None or provider.kind != "cloud":
            continue
        if not resolve_api_key(pid, env) or not resolve_model(pid, env):
            continue
        if pid == "custom_openai" and not resolve_base_url(pid, env):
            continue
        ready.append(pid)
    return ready


def provider_public_info(provider: str, env: Mapping[str, str] | None = None) -> dict:
    """Metadata segura para la interfaz (sin secretos)."""
    env = os.environ if env is None else env
    p = PROVIDERS[provider]
    return {
        "id": p.id,
        "label": p.label,
        "description": p.description,
        "kind": p.kind,
        "default_model": p.default_model,
        "current_model": resolve_model(p.id, env),
        "supports_discovery": p.supports_discovery,
        "needs_base_url": p.id == "custom_openai",
        "base_url": resolve_base_url(p.id, env),
        "requires_key": bool(p.key_env),
        "key_env": p.key_env,
        "key_configured": bool(resolve_api_key(p.id, env)) if p.key_env else True,
    }


def all_providers_public_info(env: Mapping[str, str] | None = None) -> list[dict]:
    return [provider_public_info(pid, env) for pid in PROVIDERS]
