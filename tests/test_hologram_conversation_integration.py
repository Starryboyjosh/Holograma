import asyncio

from app.services.conversation import ConversationService


class Connection:
    def __init__(self): self.messages = []
    async def broadcast(self, message): self.messages.append(message)


class LLM:
    async def stream(self, prompt, camera_context=None):
        yield "La UNEV ofrece carreras."


class Orchestrator:
    def __init__(self): self.events = []
    def start_turn(self, prompt, context=None, mode=None, skill=None):
        self.events.append(("start", prompt))
        return "turn"
    def observe_response_text(self, text, context_id=None): self.events.append(("observe", text, context_id))
    def mark_speaking(self): self.events.append(("speaking",))
    def finish_turn(self, context_id=None):
        self.events.append(("finish", context_id))
        return True
    def fail_turn(self, error=None, context_id=None):
        self.events.append(("fail", context_id))
        return True


def test_async_service_uses_shared_orchestrator_without_public_metadata():
    conn, orchestrator, spoken = Connection(), Orchestrator(), []
    service = ConversationService(LLM(), conn, speak=spoken.append, hologram_orchestrator=orchestrator)
    assert asyncio.run(service.handle_prompt("carreras")) == "La UNEV ofrece carreras."
    assert ("start", "carreras") in orchestrator.events
    assert ("speaking",) in orchestrator.events
    assert ("finish", "turn") in orchestrator.events
    assert all("ScenePlan" not in str(message) for message in conn.messages)


def test_async_service_cleans_orchestrator_after_llm_error():
    class Broken:
        async def stream(self, prompt, camera_context=None):
            raise RuntimeError("bad llm")
            yield ""
    orchestrator = Orchestrator()
    asyncio.run(ConversationService(Broken(), Connection(), hologram_orchestrator=orchestrator).handle_prompt("x"))
    assert ("fail", "turn") in orchestrator.events


def test_sync_call_path_uses_the_shared_orchestrator(monkeypatch):
    import call

    orchestrator = Orchestrator()
    spoken = []
    monkeypatch.setattr(call, "_get_hologram_turn_orchestrator", lambda: orchestrator)
    monkeypatch.setattr(call, "get_selected_backend", lambda: "local_only")
    monkeypatch.setattr(call, "route_local_skill", lambda message: "Respuesta UNEV")
    monkeypatch.setattr(call, "speak", lambda text: spoken.append(text))

    assert call.ask_ai_and_speak("carreras", "normal") == "Respuesta UNEV"
    assert spoken == ["Respuesta UNEV"]
    assert ("start", "carreras") in orchestrator.events
    assert ("finish", "turn") in orchestrator.events
