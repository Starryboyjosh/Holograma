import json
from pathlib import Path

import pytest

from app.hologram.config_store import HologramConfigStore
from app.hologram.models import HologramConfig


def valid_payload():
    return {
        "version": 1,
        "units": {role: {"enabled": True, "ip": f"10.0.0.{i}", "port": 50200} for i, role in enumerate(("top", "center", "bottom"), 1)},
        "mascot_states": {"idle": 0, "listening": 1, "thinking": 3, "speaking": 2},
        "identities": [{"id": "holomind", "title": "Holomind", "index": 0, "enabled": True, "default": True}],
        "promotions": [], "rotation": {}, "routing": {},
    }


def test_loads_valid_config_and_missing_or_corrupt_falls_back(tmp_path: Path):
    store = HologramConfigStore(tmp_path / "hologram_media.json")
    assert store.load().default_identity_id == "holomind"
    store.path.write_text("{corrupt", encoding="utf-8")
    assert store.load().units["top"].enabled is False
    store.path.write_text(json.dumps(valid_payload()), encoding="utf-8")
    assert store.load().units["bottom"].ip == "10.0.0.3"


def test_save_is_atomic_and_keeps_last_valid_backup(tmp_path: Path):
    store = HologramConfigStore(tmp_path / "hologram_media.json")
    first = HologramConfig.from_dict(valid_payload())
    store.save(first)
    store.save(first)
    backup = store.path.with_suffix(".json.bak")
    assert backup.exists()
    assert HologramConfig.from_dict(json.loads(backup.read_text(encoding="utf-8"))) == first
    assert not list(tmp_path.glob("*.tmp"))


@pytest.mark.parametrize(
    "mutate",
    [
        lambda raw: raw["identities"][0].update(index=256),
        lambda raw: raw["units"]["top"].update(port=0),
        lambda raw: raw.update(promotions=[{"id": "holomind", "title": "dup", "index": 1}]),
        lambda raw: raw["identities"][0].update(default=False),
    ],
)
def test_invalid_catalog_contracts_are_rejected(mutate):
    raw = valid_payload()
    mutate(raw)
    with pytest.raises(ValueError):
        HologramConfig.from_dict(raw)
