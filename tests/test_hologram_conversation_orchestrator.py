from app.hologram.conversation_orchestrator import HologramConversationOrchestrator
from app.hologram.media_router import MediaRouter
from app.hologram.models import HologramConfig, ScenePlan
from app.hologram.simulator import HologramSimulator


class Router:
    def route(self, message, context, mode, skill, context_id):
        return ScenePlan("unev", "focus_category", promotion_category="careers", confidence=.9, context_id=context_id)
    def replace_config(self, config): pass


class Director:
    def __init__(self):
        raw = HologramConfig.default().to_dict()
        raw["identities"] = list(raw["identities"]) + [{"id": "unev", "title": "UNEV", "index": 1}]
        self.config, self.events = HologramConfig.from_dict(raw), []
    def set_mascot_state(self, state): self.events.append(("state", state))
    def apply_scene(self, plan): self.events.append(("plan", plan.context_id, plan.center_identity))
    def set_identity(self, identity): self.events.append(("identity", identity))
    def finish_promotion_context(self, context): self.events.append(("finish_context", context))
    def resume_rotation(self): self.events.append(("resume",))


def test_orchestrator_lifecycle_is_idempotent_and_prevents_stale_close():
    director = Director()
    orchestrator = HologramConversationOrchestrator(Router(), director)
    first = orchestrator.start_turn("carreras")
    second = orchestrator.start_turn("carreras nuevas")
    assert not orchestrator.finish_turn(first)
    assert orchestrator.finish_turn(second)
    assert not orchestrator.finish_turn(second)
    assert ("identity", "holomind") in director.events
    assert ("state", "idle") in director.events


def test_orchestrator_fails_soft_when_director_raises():
    director = Director()
    director.apply_scene = lambda plan: (_ for _ in ()).throw(RuntimeError("down"))
    orchestrator = HologramConversationOrchestrator(Router(), director)
    context = orchestrator.start_turn("hola")
    assert orchestrator.fail_turn(RuntimeError("llm"), context)


def test_simulated_e2e_careers_turn_controls_all_three_roles():
    raw = HologramConfig.default().to_dict()
    raw["identities"] = list(raw["identities"]) + [{"id": "unev", "title": "UNEV", "index": 5}]
    raw["promotions"] = [{"id": "systems-degree", "title": "Systems", "index": 8, "categories": ["careers"]}]
    config = HologramConfig.from_dict(raw)
    simulator = HologramSimulator()
    for role in simulator.fans:
        simulator.connect(role)

    class SimDirector:
        def __init__(self): self.config = config
        def set_mascot_state(self, state): simulator.play("top", {"idle": 0, "listening": 1, "thinking": 3, "speaking": 2}[state], f"mascot:{state}")
        def set_identity(self, identity): simulator.play("center", {"holomind": 0, "unev": 5}[identity], f"identity:{identity}")
        def apply_scene(self, plan):
            self.set_identity(plan.center_identity)
            simulator.play("bottom", 8, "promotion:systems-degree", plan.context_id)
        def finish_promotion_context(self, context): simulator.play("bottom", 8, "rotation:careers", context)
        def resume_rotation(self): pass

    director = SimDirector()
    orchestrator = HologramConversationOrchestrator(MediaRouter(config), director)
    orchestrator.mark_listening()
    context = orchestrator.start_turn("¿Qué carreras ofrece la UNEV?")
    orchestrator.mark_speaking()
    assert orchestrator.finish_turn(context)
    events = simulator.get_events()
    assert [(event["role"], event["semantic_id"]) for event in events if event["command"] == "play_file"] == [
        ("top", "mascot:listening"), ("top", "mascot:thinking"), ("center", "identity:unev"),
        ("bottom", "promotion:systems-degree"), ("top", "mascot:speaking"), ("bottom", "rotation:careers"),
        ("center", "identity:holomind"), ("top", "mascot:idle"),
    ]
    simulator.close()
