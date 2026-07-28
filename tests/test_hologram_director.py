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
