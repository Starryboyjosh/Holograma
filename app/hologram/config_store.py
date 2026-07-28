"""Persistencia JSON validada y atómica del catálogo holográfico."""

from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path

from .models import HologramConfig

_LOCKS: dict[Path, threading.RLock] = {}
_LOCKS_GUARD = threading.Lock()


class HologramConfigStore:
    def __init__(self, path: str | Path = "data/hologram_media.json") -> None:
        self.path = Path(path)
        with _LOCKS_GUARD:
            self._lock = _LOCKS.setdefault(self.path.resolve(), threading.RLock())

    def load(self) -> HologramConfig:
        with self._lock:
            try:
                return self._read_valid(self.path)
            except (OSError, ValueError, json.JSONDecodeError, TypeError):
                return HologramConfig.default()

    def save(self, config: HologramConfig) -> None:
        if not isinstance(config, HologramConfig):
            raise ValueError("config debe ser HologramConfig validado.")
        payload = json.dumps(config.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            # Una configuración anterior corrupta nunca se convierte en backup válido.
            if self.path.exists():
                try:
                    self._read_valid(self.path)
                except (OSError, ValueError, json.JSONDecodeError, TypeError):
                    pass
                else:
                    backup = self.path.with_suffix(self.path.suffix + ".bak")
                    temp_backup = backup.with_suffix(backup.suffix + ".tmp")
                    temp_backup.write_bytes(self.path.read_bytes())
                    os.replace(temp_backup, backup)
            fd, temp_name = tempfile.mkstemp(prefix=f".{self.path.name}.", suffix=".tmp", dir=self.path.parent)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    handle.write(payload)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp_name, self.path)
            except Exception:
                try:
                    os.unlink(temp_name)
                except FileNotFoundError:
                    pass
                raise

    @staticmethod
    def _read_valid(path: Path) -> HologramConfig:
        with path.open(encoding="utf-8") as handle:
            return HologramConfig.from_dict(json.load(handle))
