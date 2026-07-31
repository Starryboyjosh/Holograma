"""Herramientas (function calling) disponibles para el LLM de Holograma."""

from app.tools.lightpanda_engine import (
    LightpandaError,
    LightpandaTimeout,
    PageContent,
    fetch_page_text,
)
from app.tools.schema import (
    BROWSE_WEB_PAGE_TOOL,
    TOOLS,
    WEB_TOOL_SYSTEM_INSTRUCTION,
    to_gemini_declarations,
    to_ollama_tools,
    to_openai_tools,
)

__all__ = [
    "BROWSE_WEB_PAGE_TOOL",
    "LightpandaError",
    "LightpandaTimeout",
    "PageContent",
    "TOOLS",
    "WEB_TOOL_SYSTEM_INSTRUCTION",
    "fetch_page_text",
    "to_gemini_declarations",
    "to_ollama_tools",
    "to_openai_tools",
]
