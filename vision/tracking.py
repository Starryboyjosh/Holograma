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


def _iou(a, b) -> float:
    """Intersección sobre unión de dos cajas (x1, y1, x2, y2)."""
    ax1, ay1, ax2, ay2 = (float(v) for v in a)
    bx1, by1, bx2, by2 = (float(v) for v in b)
    iw = max(0.0, min(ax2, bx2) - max(ax1, bx1))
    ih = max(0.0, min(ay2, by2) - max(ay1, by1))
    inter = iw * ih
    union = (ax2 - ax1) * (ay2 - ay1) + (bx2 - bx1) * (by2 - by1) - inter
    return inter / union if union > 0.0 else 0.0


class PersonAssociator:
    """Asociación locks → Hungarian → dummy adaptativo → veto de empate (§13 I6).

    Mantiene un conjunto de tracks (identidades) de personas y cada ciclo
    ``update(detections, now)`` los casa contra las detecciones nuevas:

      (a) **Locks**: un par track↔detección se compromete de una vez cuando el
          mejor score ``s1 ≥ s1_lock`` (0.90) y el margen sobre el segundo
          mejor es amplio (``lock_margin``). Greedy, antes del Hungarian.
      (b) **Hungarian** (scipy perezoso, fallback greedy si no está) con
          columnas dummy: una detección que no casa con ningún track crea una
          identidad nueva.
      (c) **Dummy adaptativo a la confianza**:
          ``dummy = clamp(0.05 + 0.20·(1−confianza), 0, 0.72)`` — cuanto menos
          confiado el mejor match, más atractivo es crear identidad nueva en
          vez de asignar mal.
      (d) **Veto de empate**: si el mejor y el segundo mejor score quedan a
          menos de ``tie_epsilon`` (0.05), no se compromete nada para esa
          detección y se arrastra sin asignar al siguiente ciclo. La pieza
          clave frente a uniformes idénticos: prefiere decir "no sé".

    Sin descriptor (``signature=None``) el canal de apariencia se descarta y la
    asociación queda solo con geometría (IoU) — con cajas idénticas converge al
    comportamiento de hoy (§13 I7). Módulo puro: numpy + scipy perezoso.
    """

    def __init__(
        self,
        s1_lock: float = 0.90,
        lock_margin: float = 0.05,
        tie_epsilon: float = 0.05,
        dummy_min: float = 0.05,
        dummy_slope: float = 0.20,
        dummy_cap: float = 0.72,
        geo_weight: float = 0.5,
        app_weight: float = 0.5,
        confirm_cycles: int = 2,
        forget_seconds: float = 10.0,
        retain_seconds: float = 60.0,
    ) -> None:
        self.s1_lock = float(s1_lock)
        self.lock_margin = float(lock_margin)
        self.tie_epsilon = float(tie_epsilon)
        self.dummy_min = float(dummy_min)
        self.dummy_slope = float(dummy_slope)
        self.dummy_cap = float(dummy_cap)
        self.geo_weight = float(geo_weight)
        self.app_weight = float(app_weight)
        self.confirm_cycles = max(1, int(confirm_cycles))
        self.forget_seconds = float(forget_seconds)
        self.retain_seconds = float(retain_seconds)
        self.tracks: dict[int, dict] = {}
        self._next_id = 1
        self._pending: list[dict] = []

    def adaptive_dummy(self, confidence: float) -> float:
        """Score dummy: qué tan atractivo es crear identidad nueva.

        A menor confianza del mejor match, mayor dummy (casa peor y prefiero
        una identidad nueva a asignar mal).
        """
        raw = self.dummy_min + self.dummy_slope * (1.0 - float(confidence))
        return max(0.0, min(self.dummy_cap, raw))

    def _similarity(self, track: dict, det: dict) -> float:
        """Score 0–1 entre un track y una detección.

        Geometría (IoU) siempre; apariencia (1 − distancia de descriptores)
        solo cuando ambos tienen descriptor. Sin descriptor, solo geometría.
        """
        iou = _iou(track["box"], det["box"])
        ts, ds = track.get("signature"), det.get("signature")
        if ts is None or ds is None:
            return iou
        from vision.person_signature import signature_distance

        app = 1.0 - signature_distance(ts, ds)
        return self.geo_weight * iou + self.app_weight * app

    def _hungarian(self, scores: list[list[float]]) -> list[tuple[int, int]]:
        """Casa filas↔columnas minimizando coste (1−score). Fallback greedy."""
        try:
            from scipy.optimize import linear_sum_assignment
            cost = [[1.0 - s for s in row] for row in scores]
            rows, cols = linear_sum_assignment(cost)
            return list(zip(rows.tolist(), cols.tolist()))
        except Exception:
            pairs: list[tuple[float, int, int]] = []
            for i, row in enumerate(scores):
                for j, s in enumerate(row):
                    pairs.append((float(s), i, j))
            pairs.sort(key=lambda p: p[0], reverse=True)
            used_r, used_c = set(), set()
            out = []
            for _s, i, j in pairs:
                if i in used_r or j in used_c:
                    continue
                used_r.add(i)
                used_c.add(j)
                out.append((i, j))
            return out

    def _new_track(self, det: dict, now: float) -> int:
        track_id = self._next_id
        self._next_id += 1
        self.tracks[track_id] = {
            "box": tuple(det["box"]),
            "signature": det.get("signature"),
            "confidence": float(det.get("confidence") or 0.0),
            "state": TENTATIVE,
            "sightings": 1,
            "last_seen": now,
            "absent_since": None,
        }
        return track_id

    def _refresh_track(self, track_id: int, det: dict, now: float) -> None:
        tr = self.tracks[track_id]
        tr["box"] = tuple(det["box"])
        tr["signature"] = det.get("signature")
        tr["confidence"] = float(det.get("confidence") or 0.0)
        tr["last_seen"] = now
        tr["absent_since"] = None
        tr["sightings"] = int(tr["sightings"]) + 1

    def update(self, detections: list[dict], now: float) -> list[dict]:
        """Asocia las detecciones del ciclo contra los tracks existentes.

        Parameters
        ----------
        detections:
            Lista de dicts con ``box`` (x1, y1, x2, y2), opcionalmente
            ``signature`` (descriptor I5) y ``confidence``.
        now:
            Instante del ciclo (segundos, monótono).

        Returns
        -------
        list[dict]
            Eventos del ciclo: ``{"event": "detected", "id": ...}`` cuando un
            track alcanza ``CONFIRMED`` y ``{"event": "forgotten", "id": ...}``
            cuando un ``CONFIRMED`` pasa a ``INACTIVE``.
        """
        detections = list(detections or [])
        # Las detecciones veteadas en ciclos anteriores se re-introducen como
        # candidatas sin crear track nuevo (veto de empate, §13 I6).
        detections = self._pending + detections
        self._pending = []
        events: list[dict] = []
        track_ids = list(self.tracks.keys())

        # Sólo se descartan tracks INACTIVE tras retain_seconds.
        for tid in list(self.tracks.keys()):
            if (
                self.tracks[tid]["state"] == INACTIVE
                and now - float(self.tracks[tid]["last_seen"]) >= self.retain_seconds
            ):
                del self.tracks[tid]

        if not track_ids:
            for det in detections:
                self._new_track(det, now)
            return events

        if not detections:
            # Ausencia general: envejecer los tracks.
            return self._age_tracks(set(), now)

        # Matriz de scores.
        scores = [
            [self._similarity(self.tracks[tid], det) for det in detections]
            for tid in track_ids
        ]

        # (a) Locks: pares seguros se comprometen antes del Hungarian.
        locked_pairs: list[tuple[int, int]] = []
        locked_dets: set[int] = set()
        locked_tracks: set[int] = set()
        while True:
            best = None  # (score, tid_idx, det_idx)
            for i, tid in enumerate(track_ids):
                if i in locked_tracks:
                    continue
                for j in range(len(detections)):
                    if j in locked_dets:
                        continue
                    s = scores[i][j]
                    if best is None or s > best[0]:
                        best = (s, i, j)
            if best is None or best[0] < self.s1_lock:
                break
            _s, i, j = best
            second = max(
                (
                    scores[ii][j]
                    for ii in range(len(track_ids))
                    if ii != i and ii not in locked_tracks
                ),
                default=0.0,
            )
            if best[0] - second >= self.lock_margin:
                locked_pairs.append((i, j))
                locked_dets.add(j)
                locked_tracks.add(i)
            else:
                break

        # (d) Veto de empate para el resto: si el mejor y el segundo mejor
        # quedan a menos de tie_epsilon, no comprometer nada este ciclo.
        vetoed: set[int] = set()
        for j in range(len(detections)):
            if j in locked_dets:
                continue
            ranked = sorted(
                (
                    scores[i][j]
                    for i in range(len(track_ids))
                    if i not in locked_tracks
                ),
                reverse=True,
            )
            if len(ranked) >= 2 and ranked[0] - ranked[1] < self.tie_epsilon:
                vetoed.add(j)

        # Hungarian sobre el resto con columnas dummy (crear identidad nueva).
        free_tracks = [i for i in range(len(track_ids)) if i not in locked_tracks]
        free_dets = [j for j in range(len(detections)) if j not in locked_dets and j not in vetoed]
        assignments: list[tuple[int, int]] = []
        if free_tracks and free_dets:
            sub_scores = [
                [scores[i][j] for j in free_dets] for i in free_tracks
            ]
            # Columnas dummy: cada detección puede crear identidad nueva.
            matrix = [
                row + [self.adaptive_dummy(detections[j]["confidence"]) for j in free_dets]
                for row in sub_scores
            ]
            for row_i, col_j in self._hungarian(matrix):
                if col_j < len(free_dets):
                    assignments.append((free_tracks[row_i], free_dets[col_j]))

        # Aplicar asignaciones.
        assignments = list(assignments) + [(i, j) for i, j in locked_pairs]
        for i, j in assignments:
            tid = track_ids[i]
            self._refresh_track(tid, detections[j], now)
            tr = self.tracks[tid]
            if tr["state"] in (NEW, TENTATIVE) and tr["sightings"] >= self.confirm_cycles:
                tr["state"] = CONFIRMED
                events.append({"event": "detected", "id": tid})

        assigned_track_idxs = {i for i, _j in assignments}
        assigned_det_idxs = {j for _i, j in assignments}

        # Tracks sin match: ausencia → inactivar/confirmar según aplique.
        for i, tid in enumerate(track_ids):
            if i in assigned_track_idxs:
                continue
            events.extend(self._age_track(tid, now))

        # Detecciones sin track: identidad nueva. Las veteadas se arrastran
        # sin asignar al siguiente ciclo (no crean identidad nueva).
        for j, det in enumerate(detections):
            if j in assigned_det_idxs or j in vetoed:
                continue
            self._new_track(det, now)
        self._pending = [detections[j] for j in vetoed]

        return events

    def _age_track(self, tid: int, now: float) -> list[dict]:
        """Envejece un track sin match en el ciclo actual."""
        events: list[dict] = []
        tr = self.tracks[tid]
        if tr["state"] == INACTIVE:
            if now - float(tr["last_seen"]) >= self.retain_seconds:
                del self.tracks[tid]
            return events
        if tr["absent_since"] is None:
            tr["absent_since"] = now
        absent = now - float(tr["absent_since"])
        if tr["state"] == CONFIRMED:
            if absent >= self.forget_seconds:
                tr["state"] = INACTIVE
                events.append({"event": "forgotten", "id": tid})
        elif tr["state"] == TENTATIVE:
            tr["state"] = NEW
            tr["sightings"] = 0
        return events

    def _age_tracks(self, absent_ids: set[int], now: float) -> list[dict]:
        """Envejece todos los tracks (sin detecciones este ciclo)."""
        events: list[dict] = []
        for tid in list(self.tracks.keys()):
            if tid in absent_ids:
                continue
            events.extend(self._age_track(tid, now))
        return events

    def confirmed(self) -> set[int]:
        """IDs de tracks actualmente en ``CONFIRMED``."""
        return {
            tid for tid, tr in self.tracks.items() if tr["state"] == CONFIRMED
        }

    def state(self, track_id: int) -> str | None:
        """Estado de un track (o ``None`` si no existe)."""
        tr = self.tracks.get(track_id)
        return tr["state"] if tr is not None else None

    def __len__(self) -> int:
        return len(self.tracks)
