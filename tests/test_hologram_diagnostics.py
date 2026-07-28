from app.hologram.config_store import HologramConfigStore
from app.hologram.models import HologramConfig
from scripts import diagnose_hologram


def test_diagnostics_accepts_zero_in_simulation(tmp_path, monkeypatch, capsys):
    path = tmp_path / "hologram_media.json"
    HologramConfigStore(path).save(HologramConfig.default())
    monkeypatch.setattr(diagnose_hologram, "hologram_config_path", lambda: path)
    assert diagnose_hologram.diagnose_hologram(False, True, "center", 0, False) == 0
    assert "resolved_index': 0" in capsys.readouterr().out


def test_diagnostics_rejects_out_of_range(tmp_path, monkeypatch):
    path = tmp_path / "hologram_media.json"
    HologramConfigStore(path).save(HologramConfig.default())
    monkeypatch.setattr(diagnose_hologram, "hologram_config_path", lambda: path)
    assert diagnose_hologram.diagnose_hologram(False, True, "top", 256, False) == 2


def configured_path(tmp_path):
    path = tmp_path / "hologram_media.json"
    raw = HologramConfig.default().to_dict()
    raw["units"]["center"] = {"enabled": True, "ip": "10.0.0.2", "port": 50200}
    HologramConfigStore(path).save(HologramConfig.from_dict(raw))
    return path


def test_config_only_reports_valid_corrupt_and_missing_files(tmp_path, monkeypatch, capsys):
    path = configured_path(tmp_path)
    monkeypatch.setattr(diagnose_hologram, "hologram_config_path", lambda: path)
    assert diagnose_hologram.diagnose_hologram(True, False, None, None, False) == 0
    assert "original válido" in capsys.readouterr().out
    path.write_text("{corrupt", encoding="utf-8")
    assert diagnose_hologram.diagnose_hologram(True, False, None, None, False) == 1
    assert "corrupto" in capsys.readouterr().out
    path.unlink()
    assert diagnose_hologram.diagnose_hologram(True, False, None, None, False) == 0


def test_real_diagnostic_waits_for_connection_and_sends_zero_after_connect(tmp_path, monkeypatch, capsys):
    path = configured_path(tmp_path)
    monkeypatch.setattr(diagnose_hologram, "hologram_config_path", lambda: path)
    events = []

    class Manager:
        def __init__(self, role, unit):
            self.connected = False

        def connect(self):
            self.connected = True
            events.append("connect")

        def status(self):
            return type("Status", (), {"connected": self.connected})()

        def execute_legacy(self, command, index):
            events.append((command, index))
        def close(self): events.append("close")

    assert diagnose_hologram.diagnose_hologram(False, False, "center", 0, True, Manager) == 0
    assert events == ["connect", ("play_file", 0), "close"]
    assert "Conexión establecida" in capsys.readouterr().out


def test_real_diagnostic_returns_failure_when_connection_times_out(tmp_path, monkeypatch):
    path = configured_path(tmp_path)
    monkeypatch.setattr(diagnose_hologram, "hologram_config_path", lambda: path)

    class Manager:
        def __init__(self, role, unit): pass
        def connect(self): return False
        def status(self): return type("Status", (), {"connected": False})()
        def close(self): pass

    ticks = iter((0.0, 2.0))
    assert diagnose_hologram.diagnose_hologram(False, False, "center", None, True, Manager, 1, lambda: next(ticks), lambda _: None) == 1


def test_diagnostic_never_constructs_manager_without_connect(tmp_path, monkeypatch):
    path = configured_path(tmp_path)
    monkeypatch.setattr(diagnose_hologram, "hologram_config_path", lambda: path)

    def forbidden_manager(*args):
        raise AssertionError("no debe conectar sin --connect")

    assert diagnose_hologram.diagnose_hologram(False, False, "center", 0, False, forbidden_manager) == 0
