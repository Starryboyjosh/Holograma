"""``/api/train/image/{id}`` (DELETE): borra un objeto entrenado del catálogo.

Dos cajas pueden compartir la misma foto (mismo ``thumbnail``); el archivo de
imagen solo debe borrarse del disco cuando ningún registro restante lo referencia.
"""

import json
from pathlib import Path

import main


def _seed_metadata(tmp_path: Path, items: list[dict]) -> Path:
    data_dir = tmp_path / "data"
    (data_dir / "images").mkdir(parents=True)
    meta_path = data_dir / "training_metadata.json"
    meta_path.write_text(json.dumps(items), encoding="utf-8")
    return data_dir


def test_delete_removes_item_and_orphaned_image(tmp_path, monkeypatch):
    data_dir = _seed_metadata(
        tmp_path,
        [
            {"id": 1, "label": "Carnet", "desc": "d", "thumbnail": "/data/images/a.jpg"},
            {"id": 2, "label": "Telescopio", "desc": "d", "thumbnail": "/data/images/b.jpg"},
        ],
    )
    (data_dir / "images" / "a.jpg").write_bytes(b"fake")
    monkeypatch.setattr(main, "DATA_DIR", str(data_dir))

    result = main.delete_train_image(1)

    assert result["status"] == "ok"
    assert [item["id"] for item in result["items"]] == [2]
    assert not (data_dir / "images" / "a.jpg").exists()
    assert json.loads((data_dir / "training_metadata.json").read_text())[0]["id"] == 2


def test_delete_keeps_image_shared_by_another_box(tmp_path, monkeypatch):
    data_dir = _seed_metadata(
        tmp_path,
        [
            {"id": 1, "label": "Carnet frontal", "desc": "d", "thumbnail": "/data/images/a.jpg"},
            {"id": 2, "label": "Carnet reverso", "desc": "d", "thumbnail": "/data/images/a.jpg"},
        ],
    )
    (data_dir / "images" / "a.jpg").write_bytes(b"fake")
    monkeypatch.setattr(main, "DATA_DIR", str(data_dir))

    result = main.delete_train_image(1)

    assert result["status"] == "ok"
    assert [item["id"] for item in result["items"]] == [2]
    assert (data_dir / "images" / "a.jpg").exists()


def test_delete_unknown_id_is_an_error(tmp_path, monkeypatch):
    data_dir = _seed_metadata(tmp_path, [{"id": 1, "label": "Carnet", "desc": "d", "thumbnail": ""}])
    monkeypatch.setattr(main, "DATA_DIR", str(data_dir))

    result = main.delete_train_image(999)

    assert result["status"] == "error"
    assert json.loads((data_dir / "training_metadata.json").read_text())[0]["id"] == 1
