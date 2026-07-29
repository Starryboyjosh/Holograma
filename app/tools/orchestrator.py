"""Bucle de ejecución de herramientas (function calling) de Holograma.

Flujo de un turno:

    usuario -> LLM -> ¿tool_calls? -> ejecutar Lightpanda -> reinyectar -> LLM
                          |                                                 |
                          +--------- no ------------------------------------+
                                                                            v
                                                                    respuesta final

El bucle está acotado por ``max_rounds``: un modelo que insista en navegar una
y otra vez no puede colgar el kiosko ni vaciar la cuota del proveedor.

Los errores de la herramienta **no** se lanzan hacia arriba: se devuelven al
modelo como resultado de la tool para que explique el fallo al usuario en
lenguaje natural. Lo que sí se propaga es un fallo del propio LLM.
"""

from __future__ import annotations

import json
import re

from app.tools.availability import _web_tools_mode, web_tools_available
from app.tools.lightpanda_engine import LightpandaError, fetch_page_text
from app.tools.schema import (
    TOOLS,
    WEB_TOOL_SYSTEM_INSTRUCTION,
    to_ollama_tools,
    to_openai_tools,
)
from llm_backend import chat_with_tools, get_selected_backend

# Tope de rondas modelo->herramienta->modelo por turno de usuario.
DEFAULT_MAX_ROUNDS = 3

# Pre-filtro del modo 'auto'. Sin él habría que gastar una llamada extra al LLM
# en CADA turno solo para descubrir que no hacía falta navegar, y en el kiosko
# la mayoría de preguntas son sobre la UNEV (conocimiento ya local).
_URL_RE = re.compile(r"https?://\S+|\bwww\.\S+", re.IGNORECASE)

_REALTIME_HINTS = (
    "hoy",
    "ahora",
    "actual",
    "actualmente",
    "reciente",
    "última hora",
    "ultima hora",
    "últimas noticias",
    "ultimas noticias",
    "noticia",
    "noticias",
    "clima",
    "pronóstico",
    "pronostico",
    "precio",
    "cotización",
    "cotizacion",
    "dólar",
    "dolar",
    "resultado",
    "marcador",
    "quién ganó",
    "quien gano",
    "en vivo",
    "esta semana",
    "este mes",
    "este año",
    "este ano",
    "busca en internet",
    "buscar en internet",
    "consulta la web",
    "en la web",
    "página web",
    "pagina web",
    "sitio web",
    "enlace",
    "link",
)


class ToolExecutionError(Exception):
    """Fallo irrecuperable del bucle de herramientas."""


def _handle_browse_web_page(arguments: dict) -> str:
    """Ejecuta la navegación y devuelve texto listo para el modelo."""
    url = (arguments or {}).get("url", "")
    try:
        page = fetch_page_text(url)
    except LightpandaError as error:
        # Se devuelve como resultado, no como excepción: el modelo debe poder
        # decir "no pude acceder a esa página" en vez de romper el turno.
        return f"ERROR al navegar: {error}"
    if not page.text:
        return (
            f"La página {page.url} cargó correctamente pero no contenía texto "
            "legible (puede ser contenido dinámico o multimedia)."
        )
    return page.as_prompt_context()


# Registro de handlers. Añadir una herramienta = añadir su schema en schema.py
# y su función aquí.
HANDLERS = {
    "browse_web_page": _handle_browse_web_page,
}


def execute_tool_call(name: str, arguments: dict) -> str:
    """Despacha una tool_call al handler correspondiente."""
    handler = HANDLERS.get(name)
    if handler is None:
        return f"ERROR: la herramienta '{name}' no existe en Holograma."
    return handler(arguments)


def _tools_for_backend(backend: str) -> list[dict]:
    return to_ollama_tools(TOOLS) if backend == "ollama" else to_openai_tools(TOOLS)


def _tool_result_message(backend: str, call, result: str) -> dict:
    """Formatea el resultado de la tool según lo que espera cada proveedor."""
    if backend == "ollama":
        # Ollama identifica el resultado por 'name', no por 'tool_call_id'.
        return {"role": "tool", "name": call.name, "content": result}
    return {"role": "tool", "tool_call_id": call.id, "content": result}


def run_with_tools(
    messages: list[dict],
    *,
    backend: str | None = None,
    max_rounds: int = DEFAULT_MAX_ROUNDS,
    on_tool_call=None,
) -> str:
    """Ejecuta un turno completo con herramientas y devuelve el texto final.

    ``messages`` es el historial en formato OpenAI. ``on_tool_call(name, args)``
    es un callback opcional para telemetría o para avisar por WebSocket a la UI
    ("consultando la web...").
    """
    target_backend = backend or get_selected_backend()
    if target_backend == "auto":
        # 'auto' no es un backend real; resolverlo aquí evita que chat_with_tools
        # lo rechace por no estar en PROVIDERS.
        from provider_config import select_backend

        target_backend = select_backend()

    tools = _tools_for_backend(target_backend)
    history = list(messages)

    for _ in range(max_rounds):
        turn = chat_with_tools(target_backend, history, tools)
        if not turn.tool_calls:
            return turn.content

        history.append(turn.assistant_message)
        for call in turn.tool_calls:
            if on_tool_call is not None:
                try:
                    on_tool_call(call.name, call.arguments)
                except Exception:
                    # La telemetría nunca debe tumbar el turno.
                    pass
            result = execute_tool_call(call.name, call.arguments)
            history.append(_tool_result_message(target_backend, call, result))

    # Agotadas las rondas: se pide un cierre sin herramientas para no devolver
    # una respuesta vacía al usuario.
    final = chat_with_tools(target_backend, history, [])
    if final.content:
        return final.content
    raise ToolExecutionError(
        f"El modelo siguió pidiendo herramientas tras {max_rounds} rondas "
        "sin producir una respuesta."
    )


def build_messages_with_tools(
    user_input: str,
    system_prompt: str,
    university_context: str,
    camera_context: str | None = None,
) -> list[dict]:
    """Historial inicial con la instrucción de uso de `browse_web_page`.

    Réplica de ``llm_backend._build_messages`` más el bloque de herramientas;
    se mantiene aparte para no alterar la ruta de voz existente.
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": university_context},
        {"role": "system", "content": WEB_TOOL_SYSTEM_INSTRUCTION},
    ]
    if camera_context:
        messages.append(
            {
                "role": "system",
                "content": f"Contexto actual de la cámara:\n{camera_context}",
            }
        )
    messages.append(
        {
            "role": "user",
            "content": f"{user_input}\n\n[Instrucción: responde siempre en español.]",
        }
    )
    return messages


def generate_reply_with_tools(
    user_input: str,
    system_prompt: str,
    university_context: str,
    camera_context: str | None = None,
    *,
    backend: str | None = None,
    on_tool_call=None,
) -> str:
    """Punto de entrada de alto nivel, equivalente a ``generate_reply``."""
    messages = build_messages_with_tools(
        user_input, system_prompt, university_context, camera_context
    )
    return run_with_tools(messages, backend=backend, on_tool_call=on_tool_call)


def prompt_suggests_web(prompt: str) -> bool:
    """Heurística del modo 'auto': ¿este prompt parece necesitar la web?

    Un falso positivo solo cuesta una llamada extra al LLM (que puede decidir
    no navegar); un falso negativo hace que no se ofrezca la herramienta. Por
    eso el listado es deliberadamente generoso.
    """
    text = (prompt or "").lower()
    if _URL_RE.search(text):
        return True
    return any(hint in text for hint in _REALTIME_HINTS)


def should_offer_web_tools(prompt: str) -> tuple[bool, str]:
    """Decide si este turno lleva herramienta web. Devuelve ``(sí/no, motivo)``.

    Orden barato→caro: primero el modo, luego la heurística de texto y solo al
    final el sondeo de red (que hace syscalls con timeout).
    """
    mode = _web_tools_mode()
    if mode == "off":
        return False, "deshabilitado por configuración (HOLOGRAM_WEB_TOOLS=off)"
    if mode == "auto" and not prompt_suggests_web(prompt):
        return False, "el prompt no requiere información de la web"
    return web_tools_available()


def gather_web_context(
    prompt: str,
    system_prompt: str,
    university_context: str,
    camera_context: str | None = None,
    *,
    backend: str | None = None,
    on_tool_call=None,
) -> str | None:
    """Fase de herramientas previa al streaming.

    Deja que el modelo decida si navega y, si lo hace, devuelve el texto
    extraído para inyectarlo como contexto del turno real. Devuelve ``None``
    cuando no hay nada que aportar, y entonces el turno sigue exactamente como
    antes de existir esta función.

    Se mantiene separado de ``run_with_tools`` a propósito: aquí NO se pide al
    modelo la respuesta final, solo el material. Así la respuesta que escucha
    el usuario se sigue generando en streaming y el TTS arranca en la primera
    cláusula, sin esperar al turno completo.
    """
    target_backend = backend or get_selected_backend()
    if target_backend == "auto":
        from provider_config import select_backend

        target_backend = select_backend()

    messages = build_messages_with_tools(
        prompt, system_prompt, university_context, camera_context
    )
    tools = _tools_for_backend(target_backend)

    try:
        turn = chat_with_tools(target_backend, messages, tools)
    except Exception as error:
        # Que falle la fase de herramientas no debe tumbar el turno: se sigue
        # sin contexto web y el usuario recibe la respuesta normal.
        print(f"[tools] fase de herramientas omitida ({target_backend}): {error}")
        return None

    if not turn.tool_calls:
        return None

    collected: list[str] = []
    for call in turn.tool_calls:
        if on_tool_call is not None:
            try:
                on_tool_call(call.name, call.arguments)
            except Exception:
                pass
        collected.append(execute_tool_call(call.name, call.arguments))

    if not collected:
        return None
    return "\n\n---\n\n".join(collected)


def describe_tool_call(name: str, arguments: dict) -> str:
    """Texto corto para logs/UI: 'browse_web_page(url=...)'."""
    try:
        rendered = json.dumps(arguments, ensure_ascii=False)
    except (TypeError, ValueError):
        rendered = str(arguments)
    return f"{name}({rendered})"
