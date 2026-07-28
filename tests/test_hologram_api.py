import json
from pathlib import Path

import main
from app.hologram.config_store import HologramConfigStore
from app.hologram.director import HologramDirector
from app.hologram.models import HologramConfig
from main import (
    HologramTestPayload,
    HologramUnitUpdate,
    IdentityPayload,
    PromotionPayload,
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
