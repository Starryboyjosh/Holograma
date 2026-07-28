import json
from pathlib import Path

from fastapi.testclient import TestClient

import main
from app.hologram.compatibility import LegacyHologramAdapter
from app.hologram.config_store import HologramConfigStore
from app.hologram.director import HologramDirector
from app.hologram.models import FanUnitStatus, HologramConfig
from main import (
    HologramTestPayload,
    HologramUnitUpdate,
    IdentityPayload,
    PromotionPayload,
    connect_hologram_unit,
    create_hologram_identity,
    create_hologram_promotion,
    delete_hologram_identity,
    hologram_rotation_status,
    hologram_units,
    list_hologram_identities,
    list_hologram_promotions,
    start_hologram_rotation,
    stop_hologram_rotation,
    update_hologram_unit,
)
from main import (
    test_hologram_identity as api_test_hologram_identity,
)
from main import (
    test_hologram_unit as api_test_hologram_unit,
)


def setup_runtime(tmp_path: Path, monkeypatch):
    config = HologramConfig.default()
    store = HologramConfigStore(tmp_path / "hologram_media.json")
    store.save(config)
    monkeypatch.setattr(main, "_hologram_store", store)
    monkeypatch.setattr(main, "_hologram_director", HologramDirector(config))


def test_admin_crud_units_catalog_and_rotation(tmp_path, monkeypatch):
    setup_runtime(tmp_path, monkeypatch)
    result = update_hologram_unit("bottom", HologramUnitUpdate(enabled=True, ip="10.0.0.3"))
    assert result["status"] == "ok"
    assert hologram_units()["units"][2]["ip"] == "10.0.0.3"
    identity = create_hologram_identity(IdentityPayload(id="unev", title="UNEV", index=5))
    assert identity["status"] == "ok"
    promotion = create_hologram_promotion(PromotionPayload(id="career", title="Career", index=8, categories=["careers"], duration_seconds=2))
    assert promotion["status"] == "ok"
    assert len(list_hologram_identities()["identities"]) == 2
    assert len(list_hologram_promotions()["promotions"]) == 1
    start_hologram_rotation()
    assert hologram_rotation_status()["rotation"]["active"] is True
    stop_hologram_rotation()
    assert hologram_rotation_status()["rotation"]["active"] is False


def test_admin_rejects_bad_role_and_default_deletion(tmp_path, monkeypatch):
    setup_runtime(tmp_path, monkeypatch)
    bad = update_hologram_unit("side", HologramUnitUpdate())
    assert bad.status_code == 400
    result = delete_hologram_identity("holomind")
    assert result.status_code == 409


def test_unit_test_validates_optional_index(tmp_path, monkeypatch):
    setup_runtime(tmp_path, monkeypatch)
    result = api_test_hologram_unit("top", HologramTestPayload(index=256))
    assert result.status_code == 400
    assert json.loads(result.body) == {
        "status": "error",
        "code": "HOLOGRAM_INVALID_INDEX",
        "message": "El índice debe estar entre 0 y 255.",
        "field": "index",
    }


def test_connect_endpoint_attempts_real_manager_connection_and_reports_failure(tmp_path, monkeypatch):
    setup_runtime(tmp_path, monkeypatch)
    director = main._hologram_director
    calls = []
    unit = director.units["top"]
    monkeypatch.setattr(unit, "connect", lambda: calls.append("connect") or True)
    assert connect_hologram_unit("top")["status"] == "ok"
    assert calls == ["connect"]
    monkeypatch.setattr(unit, "connect", lambda: False)
    failed = connect_hologram_unit("top")
    assert failed.status_code == 409


def test_identity_test_rejects_unknown_id_and_legacy_adapter_keeps_shared_director(tmp_path, monkeypatch):
    setup_runtime(tmp_path, monkeypatch)
    director = main._hologram_director
    missing = api_test_hologram_identity("missing")
    assert missing.status_code == 404
    adapter = LegacyHologramAdapter(director)
    adapter.configure("10.0.0.9")
    assert adapter._director is director
    assert main._hologram_director is director


def test_legacy_connect_endpoint_reconfigures_the_shared_director(tmp_path, monkeypatch):
    class ConnectManager:
        def __init__(self, role, config): self.role, self.config, self.connected, self.calls = role, config, False, []
        def start(self): pass
        def close(self): self.connected = False
        def connect(self):
            self.calls.append("connect")
            self.connected = True
            return True
        @property
        def is_connected(self): return self.connected
        def status(self): return FanUnitStatus(self.role, self.config.enabled, self.config.ip, self.config.port, self.connected, None, None, None, False)
        def request(self, *_args): pass

    director = HologramDirector(HologramConfig.default(), ConnectManager)
    monkeypatch.setattr(main, "_hologram_director", director)
    adapter = LegacyHologramAdapter(director)
    monkeypatch.setattr(main, "_get_holo_manager", lambda: adapter)
    result = main.holo_connect(main.HologramConnect(ip="10.0.0.9", port=50200))
    assert result["status"] == "ok"
    assert result["connected"] is True
    assert adapter._director is director
    assert director.units["top"].config.ip == "10.0.0.9"
    assert director.units["top"].calls == ["connect"]


def test_legacy_connect_endpoint_returns_error_after_failed_real_attempt(tmp_path, monkeypatch):
    setup_runtime(tmp_path, monkeypatch)
    director = main._hologram_director
    adapter = LegacyHologramAdapter(director)
    monkeypatch.setattr(main, "_get_holo_manager", lambda: adapter)
    original = adapter.configure

    def configure(ip, port):
        original(ip, port)
        monkeypatch.setattr(director.units["top"], "connect", lambda: False)

    monkeypatch.setattr(adapter, "configure", configure)
    result = main.holo_connect(main.HologramConnect(ip="10.0.0.9", port=50200))
    assert result["status"] == "error"


def test_hologram_token_gate_protects_read_and_mutation_when_enabled(tmp_path, monkeypatch):
    setup_runtime(tmp_path, monkeypatch)
    monkeypatch.setattr(main, "_API_TOKEN", "audit-token")
    client = TestClient(main.app)
    assert client.get("/api/hologram/status").status_code == 401
    assert client.post("/api/hologram/units/top/connect").status_code == 401
    assert client.get("/api/hologram/status", headers={"X-API-Token": "audit-token"}).status_code == 200
