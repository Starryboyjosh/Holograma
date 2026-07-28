from app.hologram.director import HologramDirector
from app.hologram.models import HologramConfig, ScenePlan


class RecordingManager:
    all = {}
    def __init__(self, role, config):
        self.role, self.config, self.requests, self.alive = role, config, [], False
        RecordingManager.all[role] = self
    def start(self): self.alive = True
    def close(self): self.alive = False
    def request(self, index, media_id): self.requests.append((index, media_id))
    def status(self):
        from app.hologram.models import FanUnitStatus
        return FanUnitStatus(self.role, self.config.enabled, self.config.ip, self.config.port, False, None, None, None, self.alive)


def config():
    raw = HologramConfig.default().to_dict()
    raw["units"] = {role: {"enabled": True, "ip": f"10.0.0.{n}", "port": 50200} for n, role in enumerate(("top", "center", "bottom"), 1)}
    raw["identities"] = list(raw["identities"])
    raw["identities"].append({"id": "unev", "title": "UNEV", "index": 5})
    raw["promotions"] = [{"id": "careers", "title": "Careers", "index": 9, "categories": ["careers"]}]
    return HologramConfig.from_dict(raw)


def test_director_routes_semantic_commands_to_the_correct_role():
    RecordingManager.all = {}
    director = HologramDirector(config(), RecordingManager)
    director.start()
    director.set_mascot_state("thinking")
    director.set_identity("unev")
    director.apply_scene(ScenePlan(center_identity="unknown", promotion_action="focus_category", promotion_category="careers"))
    assert any(item == (3, "mascot:thinking") for item in RecordingManager.all["top"].requests)
    assert (5, "identity:unev") in RecordingManager.all["center"].requests
    assert (0, "identity:holomind") in RecordingManager.all["center"].requests
    assert RecordingManager.all["bottom"].requests == [(9, "promotion:careers")]
    director.close()
    director.close()
    assert not any(manager.alive for manager in RecordingManager.all.values())


def test_three_units_keep_distinct_network_configuration():
    director = HologramDirector(config(), RecordingManager)
    status = director.get_status()
    assert [status.units[role].ip for role in ("top", "center", "bottom")] == ["10.0.0.1", "10.0.0.2", "10.0.0.3"]


def test_reconfigure_preserves_rotation_active_paused_and_stopped_state():
    for action, expected_active, expected_paused in (("active", True, False), ("paused", True, True), ("stopped", False, False)):
        RecordingManager.all = {}
        director = HologramDirector(config(), RecordingManager)
        director.start()
        if action != "stopped":
            director.start_rotation()
        if action == "paused":
            director.pause_rotation()
        if action == "stopped":
            director.stop_rotation()
        director.reconfigure(config())
        status = director.get_status().rotation
        assert (status["active"], status["paused"]) == (expected_active, expected_paused)
        director.close()


def test_reconfigure_paused_rotation_keeps_current_without_dispatching_next():
    class HistoryManager(RecordingManager):
        history = []
        def request(self, index, media_id):
            self.requests.append((index, media_id))
            HistoryManager.history.append((self.role, index, media_id))

    raw = config().to_dict()
    raw["promotions"] = list(raw["promotions"])
    raw["promotions"][0]["priority"] = 1
    raw["promotions"].append({"id": "admissions", "title": "Admissions", "index": 10})
    catalog = HologramConfig.from_dict(raw)
    HistoryManager.all, HistoryManager.history = {}, []
    director = HologramDirector(catalog, HistoryManager)
    director.start_rotation()
    director.pause_rotation()
    before = list(HistoryManager.history)
    assert before[-1] == ("bottom", 9, "promotion:careers")
    director.reconfigure(catalog)
    status = director.get_status().rotation
    assert status["current"]["id"] == "careers"
    assert status["next"]["id"] == "admissions"
    assert (status["active"], status["paused"]) == (True, True)
    bottom_history = [event for event in HistoryManager.history if event[0] == "bottom"]
    assert bottom_history == [event for event in before if event[0] == "bottom"] + [("bottom", 9, "promotion:careers")]
    assert ("bottom", 10, "promotion:admissions") not in bottom_history
    director.close()
