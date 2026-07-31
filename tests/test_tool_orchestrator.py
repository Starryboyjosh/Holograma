"""Tests del bucle de function calling y del esquema de herramientas."""


from app.tools import orchestrator, schema
from llm_backend import ToolCallRequest, ToolTurn

# --- Esquema ---


def test_browse_web_page_schema_shape():
    function = schema.BROWSE_WEB_PAGE_TOOL["function"]
    assert function["name"] == "browse_web_page"
    assert function["parameters"]["required"] == ["url"]
    assert function["parameters"]["properties"]["url"]["type"] == "string"


def test_openai_and_ollama_share_the_canonical_shape():
    assert schema.to_openai_tools() == schema.to_ollama_tools()


def test_gemini_declarations_drop_the_function_wrapper():
    declarations = schema.to_gemini_declarations()
    assert "functionDeclarations" in declarations[0]
    first = declarations[0]["functionDeclarations"][0]
    assert first["name"] == "browse_web_page"
    assert "type" not in first


def test_gemini_conversion_strips_unsupported_keys():
    tool = {
        "type": "function",
        "function": {
            "name": "x",
            "description": "d",
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "properties": {"a": {"type": "string", "default": "z"}},
            },
        },
    }
    params = schema.to_gemini_declarations([tool])[0]["functionDeclarations"][0]["parameters"]
    assert "additionalProperties" not in params
    assert "default" not in params["properties"]["a"]


# --- Ejecución de la herramienta ---


def test_browse_handler_returns_page_context(monkeypatch):
    from app.tools.lightpanda_engine import PageContent

    monkeypatch.setattr(
        orchestrator,
        "fetch_page_text",
        lambda url: PageContent(url=url, title="T", text="cuerpo", truncated=False),
    )
    result = orchestrator.execute_tool_call("browse_web_page", {"url": "https://x.com"})
    assert "cuerpo" in result


def test_browse_handler_converts_engine_error_into_tool_result(monkeypatch):
    from app.tools.lightpanda_engine import LightpandaError

    def boom(url):
        raise LightpandaError("motor caído")

    monkeypatch.setattr(orchestrator, "fetch_page_text", boom)
    result = orchestrator.execute_tool_call("browse_web_page", {"url": "https://x.com"})
    # El fallo llega al modelo como texto, no como excepción.
    assert result.startswith("ERROR al navegar")
    assert "motor caído" in result


def test_unknown_tool_is_reported():
    assert "no existe" in orchestrator.execute_tool_call("volar", {})


# --- Bucle ---


def _turn(content="", calls=None):
    return ToolTurn(content, calls or [], {"role": "assistant", "content": content})


def test_loop_returns_directly_when_no_tool_calls(monkeypatch):
    monkeypatch.setattr(
        orchestrator, "chat_with_tools", lambda b, m, t: _turn("respuesta directa")
    )
    assert orchestrator.run_with_tools([], backend="groq") == "respuesta directa"


def test_loop_executes_tool_and_reinjects_context(monkeypatch):
    turns = [
        _turn(calls=[ToolCallRequest("c1", "browse_web_page", {"url": "https://x.com"})]),
        _turn("según la página, X"),
    ]
    seen_histories = []

    def fake_chat(backend, messages, tools):
        seen_histories.append(list(messages))
        return turns.pop(0)

    monkeypatch.setattr(orchestrator, "chat_with_tools", fake_chat)
    monkeypatch.setattr(
        orchestrator, "execute_tool_call", lambda name, args: "TEXTO DE LA WEB"
    )

    result = orchestrator.run_with_tools([{"role": "user", "content": "hola"}], backend="groq")
    assert result == "según la página, X"

    # La segunda llamada al modelo debe incluir el resultado de la herramienta.
    second = seen_histories[1]
    assert second[-1]["role"] == "tool"
    assert second[-1]["content"] == "TEXTO DE LA WEB"
    assert second[-1]["tool_call_id"] == "c1"


def test_ollama_tool_result_uses_name_not_id(monkeypatch):
    turns = [
        _turn(calls=[ToolCallRequest("call_0", "browse_web_page", {"url": "https://x.com"})]),
        _turn("ok"),
    ]
    histories = []

    def fake_chat(backend, messages, tools):
        histories.append(list(messages))
        return turns.pop(0)

    monkeypatch.setattr(orchestrator, "chat_with_tools", fake_chat)
    monkeypatch.setattr(orchestrator, "execute_tool_call", lambda n, a: "texto")

    orchestrator.run_with_tools([], backend="ollama")
    tool_message = histories[1][-1]
    assert tool_message["name"] == "browse_web_page"
    assert "tool_call_id" not in tool_message


def test_loop_is_bounded_by_max_rounds(monkeypatch):
    calls = {"n": 0}

    def always_tools(backend, messages, tools):
        calls["n"] += 1
        if not tools:
            return _turn("cierre forzado")
        return _turn(calls=[ToolCallRequest("c", "browse_web_page", {"url": "https://x.com"})])

    monkeypatch.setattr(orchestrator, "chat_with_tools", always_tools)
    monkeypatch.setattr(orchestrator, "execute_tool_call", lambda n, a: "texto")

    result = orchestrator.run_with_tools([], backend="groq", max_rounds=2)
    assert result == "cierre forzado"
    # 2 rondas con herramientas + 1 cierre sin ellas.
    assert calls["n"] == 3


def test_on_tool_call_callback_fires(monkeypatch):
    seen = []
    turns = [
        _turn(calls=[ToolCallRequest("c", "browse_web_page", {"url": "https://x.com"})]),
        _turn("fin"),
    ]
    monkeypatch.setattr(orchestrator, "chat_with_tools", lambda b, m, t: turns.pop(0))
    monkeypatch.setattr(orchestrator, "execute_tool_call", lambda n, a: "texto")

    orchestrator.run_with_tools(
        [], backend="groq", on_tool_call=lambda name, args: seen.append((name, args))
    )
    assert seen == [("browse_web_page", {"url": "https://x.com"})]


def test_callback_failure_does_not_break_the_turn(monkeypatch):
    turns = [
        _turn(calls=[ToolCallRequest("c", "browse_web_page", {"url": "https://x.com"})]),
        _turn("fin"),
    ]
    monkeypatch.setattr(orchestrator, "chat_with_tools", lambda b, m, t: turns.pop(0))
    monkeypatch.setattr(orchestrator, "execute_tool_call", lambda n, a: "texto")

    def boom(name, args):
        raise RuntimeError("telemetría rota")

    assert orchestrator.run_with_tools([], backend="groq", on_tool_call=boom) == "fin"


# --- Construcción de mensajes ---


def test_messages_include_the_tool_system_instruction():
    messages = orchestrator.build_messages_with_tools("hola", "sys", "unev")
    contents = [m["content"] for m in messages]
    assert schema.WEB_TOOL_SYSTEM_INSTRUCTION in contents
    assert messages[-1]["role"] == "user"


def test_camera_context_is_injected_when_present():
    messages = orchestrator.build_messages_with_tools("hola", "sys", "unev", "una persona")
    assert any("una persona" in m["content"] for m in messages)
