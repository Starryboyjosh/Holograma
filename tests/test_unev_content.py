"""Tests de la fuente única de contenido UNEV (skills/unev_content).

Puras: usan rutas temporales para no tocar data/unev_info.json del repo.
"""

import json

import pytest

import skills.unev_content as uc


def test_load_defaults_when_file_missing(tmp_path):
    info = uc.load_unev_info(tmp_path / "no-existe.json")
    assert info["name"] == "UNEV"
    assert set(uc.TEXT_FIELDS).issubset(info)
    assert info["programs"], "debe rellenar programas por defecto"


def test_save_then_load_roundtrip(tmp_path):
    path = tmp_path / "unev.json"
    data = dict(uc.DEFAULT_UNEV_INFO)
    data["name"] = "UNEV Editado"
    uc.save_unev_info(data, path)
    assert json.loads(path.read_text(encoding="utf-8"))["name"] == "UNEV Editado"
    assert uc.load_unev_info(path)["name"] == "UNEV Editado"


def test_merge_fills_missing_keys_from_default(tmp_path):
    path = tmp_path / "partial.json"
    path.write_text(json.dumps({"name": "Solo Nombre"}), encoding="utf-8")
    info = uc.load_unev_info(path)
    assert info["name"] == "Solo Nombre"
    # los campos ausentes caen al respaldo, no quedan vacíos
    assert info["mission"] == uc.DEFAULT_UNEV_INFO["mission"]


def test_program_keys_are_lowercased(tmp_path):
    path = tmp_path / "p.json"
    path.write_text(json.dumps({"programs": {"Robótica": "desc"}}), encoding="utf-8")
    assert uc.load_unev_info(path)["programs"] == {"robótica": "desc"}


def test_validation_reports_actionable_errors():
    assert uc.validate_unev_info("no soy dict")
    assert any("texto" in e for e in uc.validate_unev_info({"mission": 123}))
    assert any("programs" in e for e in uc.validate_unev_info({"programs": "x"}))
    assert any("vacío" in e for e in uc.validate_unev_info({"name": "   ", "description": ""}))
    assert uc.validate_unev_info(uc.DEFAULT_UNEV_INFO) == []


def test_save_rejects_invalid(tmp_path):
    with pytest.raises(ValueError):
        uc.save_unev_info({"name": "", "description": ""}, tmp_path / "bad.json")


def test_save_updates_cache_and_university_reads_it(tmp_path):
    import skills.university as university

    try:
        uc.save_unev_info({**uc.DEFAULT_UNEV_INFO, "name": "UNEV-CACHE"}, tmp_path / "c.json")
        assert uc.get_unev_info()["name"] == "UNEV-CACHE"
        assert "UNEV-CACHE" in university.get_university_summary()
    finally:
        uc.reload()  # restaura la caché desde el archivo real del repo


def test_clamp_strips_control_chars_in_content(tmp_path):
    path = tmp_path / "ctrl.json"
    path.write_text(json.dumps({"name": "UNEV\x00\x07"}), encoding="utf-8")
    assert uc.load_unev_info(path)["name"] == "UNEV"
