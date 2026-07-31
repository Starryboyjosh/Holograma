"""Esquema unificado de las herramientas expuestas al LLM.

El formato canónico es el de OpenAI (``{"type": "function", "function": {...}}``),
que Ollama, Groq, OpenRouter, OpenAI y NVIDIA aceptan tal cual. Gemini usa una
forma distinta (``functionDeclarations`` en camelCase), por eso existe el
conversor ``to_gemini_declarations``.
"""

from __future__ import annotations

BROWSE_WEB_PAGE_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "browse_web_page",
        "description": (
            "Accede a una URL específica en tiempo real usando el motor "
            "ultra-rápido Lightpanda para extraer el contenido de texto "
            "actualizado de una página web."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": (
                        "La URL completa de la página web que necesitas "
                        "consultar (ejemplo: https://sitio.com/noticia)."
                    ),
                }
            },
            "required": ["url"],
        },
    },
}

TOOLS: tuple[dict, ...] = (BROWSE_WEB_PAGE_TOOL,)

WEB_TOOL_SYSTEM_INSTRUCTION = """Tienes acceso a la herramienta `browse_web_page`, impulsada por el motor Lightpanda.

Reglas de uso:
1. Si el usuario te pide información en tiempo real, eventos recientes, datos de una URL específica o consultar contenido actualizado en la web, DEBES invocar la función `browse_web_page` pasando la URL correspondiente.
2. Si el usuario proporciona un enlace en su mensaje, usa `browse_web_page` para leer su contenido antes de responder.
3. Una vez que recibas el texto extraído por la herramienta, sintetiza la respuesta de manera clara y directa, citando la información obtenida.
4. No intentes inventar datos o URLs que no hayan sido verificados o solicitados."""

# Se inyecta cuando NO hay navegación disponible (sin internet o Lightpanda
# caído). Sin este bloque, un modelo local —que sigue funcionando perfectamente
# sin red— promete "voy a consultarlo" y luego no puede, o directamente inventa
# datos actuales. Aquí se le dice explícitamente que no lo intente.
NO_WEB_SYSTEM_INSTRUCTION = """No tienes acceso a internet en este momento.

Reglas en este modo:
1. NO afirmes que vas a consultar, buscar o abrir una página web: no es posible ahora.
2. Responde únicamente con tu conocimiento propio y con el contexto de la UNEV que ya tienes.
3. Si te piden datos en tiempo real (noticias, precios, clima, resultados, eventos de hoy) o el contenido de un enlace, di con naturalidad que ahora mismo no tienes conexión para consultarlo y ofrece lo que sí sepas.
4. Nunca inventes datos actuales ni el contenido de una página que no puedes leer."""


def to_openai_tools(tools=TOOLS) -> list[dict]:
    """Formato OpenAI/Groq/OpenRouter/NVIDIA (idéntico al canónico)."""
    return [dict(tool) for tool in tools]


def to_ollama_tools(tools=TOOLS) -> list[dict]:
    """Formato Ollama ``/api/chat``: mismo esquema que OpenAI."""
    return [dict(tool) for tool in tools]


def to_gemini_declarations(tools=TOOLS) -> list[dict]:
    """Formato Gemini: ``functionDeclarations`` sin el envoltorio ``function``.

    Gemini no acepta la clave ``type: function`` ni ``additionalProperties``.
    """
    declarations = []
    for tool in tools:
        function = tool.get("function", {})
        declarations.append(
            {
                "name": function.get("name"),
                "description": function.get("description"),
                "parameters": _strip_unsupported(function.get("parameters", {})),
            }
        )
    return [{"functionDeclarations": declarations}]


def _strip_unsupported(schema: dict) -> dict:
    """Poda recursiva de claves de JSON Schema que Gemini rechaza."""
    unsupported = {"additionalProperties", "$schema", "default", "examples"}
    cleaned = {}
    for key, value in (schema or {}).items():
        if key in unsupported:
            continue
        if isinstance(value, dict):
            cleaned[key] = _strip_unsupported(value)
        elif isinstance(value, list):
            cleaned[key] = [
                _strip_unsupported(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            cleaned[key] = value
    return cleaned
