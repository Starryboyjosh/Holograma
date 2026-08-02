"""Histéresis M-of-N sobre etiquetas (§13 I4).

Máquina ``NEW → TENTATIVE → CONFIRMED → INACTIVE``: un parpadeo de un ciclo
ya no re-dispara el evento. Un label solo se declara detectado cuando se ve en
``confirm_cycles`` ciclos consecutivos, y se olvida tras ``forget_seconds`` de
ausencia sostenida.

Módulo puro: no importa cv2, numpy ni time. Recibe ``now`` por parámetro para
que los tests sean deterministas. Tests en ``tests/test_tracking.py``.
"""

from __future__ import annotations

NEW = "NEW"
TENTATIVE = "TENTATIVE"
CONFIRMED = "CONFIRMED"
INACTIVE = "INACTIVE"


class LabelHysteresis:
    """Histéresis M-of-N sobre el conjunto de etiquetas detectadas.

    Un label nuevo arranca en ``TENTATIVE`` con 1 avistamiento. Con
    ``confirm_cycles`` avistamientos **consecutivos** pasa a ``CONFIRMED`` y el
    tracker emite el evento ``"detected"`` exactamente una vez. Si un label
    ``CONFIRMED`` deja de verse durante ``forget_seconds`` pasa a ``INACTIVE``
    y emite ``"forgotten"``. Un label ``TENTATIVE`` que se pierde un ciclo
    vuelve a ``NEW`` (el parpadeo no cuenta como evidencia), y al reaparecer
    debe volver a acumular avistamientos consecutivos. Los ``INACTIVE`` se
    purgan tras ``retain_seconds`` para no crecer sin límite.
    """

    def __init__(
        self,
        confirm_cycles: int = 2,
        forget_seconds: float = 10.0,
        retain_seconds: float = 60.0,
    ) -> None:
        self.confirm_cycles = max(1, int(confirm_cycles))
        self.forget_seconds = float(forget_seconds)
        self.retain_seconds = float(retain_seconds)
        self._labels: dict[str, dict] = {}

    def update(self, labels: set[str], now: float) -> list[dict]:
        """Registra el conjunto de labels vistos en el ciclo actual.

        Parameters
        ----------
        labels:
            Etiquetas detectadas en este ciclo (set).
        now:
            Instante del ciclo (segundos, monótono).

        Returns
        -------
        list[dict]
            Eventos emitidos en este ciclo:
            ``{"event": "detected", "label": label}`` cuando un label alcanza
            ``CONFIRMED``, y ``{"event": "forgotten", "label": label}`` cuando
            un ``CONFIRMED`` pasa a ``INACTIVE``.
        """
        labels = set(labels or set())
        events: list[dict] = []

        for label in labels:
            rec = self._labels.get(label)
            if rec is None:
                rec = {
                    "state": TENTATIVE,
                    "sightings": 1,
                    "last_seen": now,
                    "absent_since": None,
                }
                self._labels[label] = rec
                if self.confirm_cycles <= 1:
                    rec["state"] = CONFIRMED
                    events.append({"event": "detected", "label": label})
                continue
            if rec["state"] == INACTIVE:
                rec["state"] = TENTATIVE
                rec["sightings"] = 1
                rec["absent_since"] = None
                rec["last_seen"] = now
                continue
            rec["last_seen"] = now
            rec["absent_since"] = None
            rec["sightings"] = int(rec["sightings"]) + 1
            if rec["state"] in (NEW, TENTATIVE) and rec["sightings"] >= self.confirm_cycles:
                rec["state"] = CONFIRMED
                events.append({"event": "detected", "label": label})

        for label, rec in list(self._labels.items()):
            if label in labels:
                continue
            if rec["state"] == INACTIVE:
                if now - float(rec["last_seen"]) >= self.retain_seconds:
                    del self._labels[label]
                continue
            if rec["absent_since"] is None:
                rec["absent_since"] = now
            absent = now - float(rec["absent_since"])
            if rec["state"] == CONFIRMED:
                if absent >= self.forget_seconds:
                    rec["state"] = INACTIVE
                    events.append({"event": "forgotten", "label": label})
            elif rec["state"] == TENTATIVE:
                # Parpadeo: perder el progreso de confirmación y volver a NEW.
                rec["state"] = NEW
                rec["sightings"] = 0
            # NEW: espera a reaparecer; no emite nada hasta confirmar.

        return events

    def state(self, label: str) -> str | None:
        """Estado actual de un label (o ``None`` si no está en el tracker)."""
        rec = self._labels.get(label)
        return rec["state"] if rec is not None else None

    def confirmed(self) -> set[str]:
        """Labels actualmente en ``CONFIRMED``."""
        return {lbl for lbl, rec in self._labels.items() if rec["state"] == CONFIRMED}

    def __len__(self) -> int:
        return len(self._labels)
