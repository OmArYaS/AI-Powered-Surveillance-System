import asyncio
import logging
import os
import threading
import time as _time_mod
import uuid
from collections import deque
from dataclasses import dataclass, field
from time import time
from typing import Any

import cv2
import numpy as np

from src.adapters.threat.rule_engine import RuleEngine, RuleHit
from src.domain.entities.threat import (
    THREAT_WEIGHTS,
    ActionPrediction,
    ThreatEvent,
    ThreatLevel,
    ThreatType,
)
from src.domain.interfaces.detection_repository import Detection, DetectionClass
from src.domain.interfaces.threat_repository import (
    ActionClassifierRepository,
    PoseRepository,
    WeaponRepository,
)
from src.presentation.realtime.ws_manager import WebSocketManager

logger = logging.getLogger(__name__)

ALERT_COOLDOWN_SECONDS = 5.0
SNAPSHOT_QUALITY = 90
SNAPSHOT_DIR = "data/alerts"
MAX_HISTORY = 200
ESCALATION_BONUS = 0.20
ESCALATION_THRESHOLD = 2


def _bbox_area(b: tuple[int, int, int, int]) -> int:
    return max(0, b[2] - b[0]) * max(0, b[3] - b[1])


def _bbox_intersect(a, b) -> int:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    return max(0, ix2 - ix1) * max(0, iy2 - iy1)


def _level_from_score(score: float) -> ThreatLevel:
    if score >= 0.85:
        return ThreatLevel.CRITICAL
    if score >= 0.65:
        return ThreatLevel.HIGH
    if score >= 0.40:
        return ThreatLevel.MEDIUM
    return ThreatLevel.LOW


@dataclass
class ThreatStats:
    total_alerts: int = 0
    by_level: dict[str, int] = field(default_factory=lambda: {l.value: 0 for l in ThreatLevel})
    last_alert_time: float = 0.0
    last_level: ThreatLevel | None = None
    active_threats: int = 0

    def record(self, level: ThreatLevel) -> None:
        self.total_alerts += 1
        self.by_level[level.value] = self.by_level.get(level.value, 0) + 1
        self.last_alert_time = time()
        self.last_level = level


class ThreatUseCase:
    def __init__(
        self,
        weapon_repo: WeaponRepository | None = None,
        pose_repo: PoseRepository | None = None,
        action_repo: ActionClassifierRepository | None = None,
        ws_manager: WebSocketManager | None = None,
        snapshot_dir: str = SNAPSHOT_DIR,
    ):
        self._weapon_repo = weapon_repo
        self._pose_repo = pose_repo
        self._action_repo = action_repo
        self._ws = ws_manager or WebSocketManager()
        self._engine = RuleEngine()
        self._snapshot_dir = snapshot_dir
        os.makedirs(snapshot_dir, exist_ok=True)

        self._history: deque[ThreatEvent] = deque(maxlen=MAX_HISTORY)
        self._cooldowns: dict[str, float] = {}
        self._lock = threading.Lock()
        self._stats = ThreatStats()
        self._enabled = True
        self._last_signals: dict[str, Any] = {}

    @property
    def stats(self) -> ThreatStats:
        return self._stats

    @property
    def ws_manager(self) -> WebSocketManager:
        return self._ws

    @property
    def history(self) -> list[ThreatEvent]:
        with self._lock:
            return list(self._history)

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def evaluate(
        self,
        frame: np.ndarray,
        detections: list[Detection] | None = None,
    ) -> list[ThreatEvent]:
        if not self._enabled or frame is None:
            return []

        persons = [d for d in (detections or []) if d.label == DetectionClass.PERSON]

        weapons: list = []
        if self._weapon_repo is not None:
            try:
                weapons = self._weapon_repo.detect(frame)
            except Exception as e:
                logger.warning("Weapon detection failed: %s", e)

        poses: list = []
        if self._pose_repo is not None:
            try:
                poses = self._pose_repo.estimate(frame)
            except Exception as e:
                logger.warning("Pose estimation failed: %s", e)

        prediction: ActionPrediction | None = None
        if self._action_repo is not None:
            try:
                self._action_repo.push_frame(frame)
                prediction = self._action_repo.predict()
            except Exception as e:
                logger.warning("Action classification failed: %s", e)

        hits: list[RuleHit] = []
        hits.extend(self._engine.evaluate_weapon(weapons))
        hits.extend(self._engine.evaluate_violence(prediction))
        hits.extend(self._engine.evaluate_pose(poses, persons))

        self._last_signals = {
            "weapons": len(weapons),
            "poses": len(poses),
            "violent": bool(prediction and prediction.is_violent),
            "action_label": prediction.label if prediction else None,
            "action_conf": prediction.confidence if prediction else 0.0,
        }

        if not hits:
            self._stats.active_threats = 0
            return []

        events = self._build_events(frame, hits)
        return events

    def _build_events(self, frame: np.ndarray, hits: list[RuleHit]) -> list[ThreatEvent]:
        weapon_hits = [h for h in hits if h.type == ThreatType.WEAPON]
        violence_hits = [h for h in hits if h.type == ThreatType.VIOLENCE]
        proximity_hits = [h for h in hits if h.type == ThreatType.PROXIMITY]

        merged: list[ThreatEvent] = []

        for h in weapon_hits:
            score = THREAT_WEIGHTS[h.level]
            sources = list(h.source_labels)
            related_violence = self._find_overlapping(violence_hits, h.bbox)
            related_pose = self._find_overlapping(proximity_hits, h.bbox)
            if related_violence or related_pose:
                score = min(0.99, score + ESCALATION_BONUS)
                for extra in (related_violence, related_pose):
                    if extra:
                        sources.extend(extra.source_labels)
            level = _level_from_score(score)
            self._append_event(
                merged, frame, level=level, type_=ThreatType.WEAPON_AND_VIOLENCE if (related_violence or related_pose) else ThreatType.WEAPON,
                description=h.description + (" (with action context)" if (related_violence or related_pose) else ""),
                confidence=max(0.0, min(1.0, score)),
                bbox=h.bbox,
                source_labels=sources,
            )

        for h in violence_hits:
            if any(_bbox_intersect(h.bbox or (0, 0, 0, 0), e.bbox or (0, 0, 0, 0)) > 0 for e in merged if e.bbox):
                continue
            score = THREAT_WEIGHTS[h.level]
            sources = list(h.source_labels)
            related_pose = self._find_overlapping(proximity_hits, None)
            if related_pose:
                score = min(0.99, score + 0.10)
                sources.extend(related_pose.source_labels)
            level = _level_from_score(score)
            self._append_event(
                merged, frame, level=level, type_=ThreatType.VIOLENCE,
                description=h.description,
                confidence=max(0.0, min(1.0, score)),
                bbox=h.bbox,
                source_labels=sources,
            )

        for h in proximity_hits:
            already = any(_bbox_intersect(h.bbox or (0, 0, 0, 0), e.bbox or (0, 0, 0, 0)) > 0 for e in merged if e.bbox)
            if already:
                continue
            self._append_event(
                merged, frame, level=h.level, type_=ThreatType.PROXIMITY,
                description=h.description,
                confidence=h.confidence,
                bbox=h.bbox,
                source_labels=list(h.source_labels),
            )

        if merged:
            try:
                self._stats.active_threats = len(merged)
            except Exception:
                pass

        return merged

    def _find_overlapping(self, hits: list[RuleHit], bbox) -> RuleHit | None:
        if bbox is None:
            return None
        for h in hits:
            if h.bbox is None:
                continue
            if _bbox_intersect(bbox, h.bbox) > 0 or _boxes_within(bbox, h.bbox):
                return h
        return None

    def _append_event(
        self,
        out: list[ThreatEvent],
        frame: np.ndarray,
        level: ThreatLevel,
        type_: ThreatType,
        description: str,
        confidence: float,
        bbox,
        source_labels: list[str],
    ) -> None:
        key = f"{type_.value}:{level.value}:{int(bbox[0]//40) if bbox else 0}:{int(bbox[1]//40) if bbox else 0}"
        now = time()
        with self._lock:
            last = self._cooldowns.get(key, 0.0)
            if now - last < ALERT_COOLDOWN_SECONDS:
                return
            self._cooldowns[key] = now

        snapshot_path = self._save_snapshot(frame, level)
        event = ThreatEvent(
            id=uuid.uuid4().hex[:12],
            level=level,
            type=type_,
            description=description,
            confidence=confidence,
            bbox=bbox,
            snapshot_path=snapshot_path,
            source_labels=source_labels,
        )
        with self._lock:
            self._history.appendleft(event)
        self._stats.record(level)

        if self._ws.client_count > 0:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self._ws.broadcast({"type": "threat", "data": event.to_dict()}))
            except RuntimeError:
                pass

        out.append(event)

    def _save_snapshot(self, frame: np.ndarray, level: ThreatLevel) -> str:
        try:
            date_dir = os.path.join(self._snapshot_dir, _time_mod.strftime("%Y-%m-%d"))
            os.makedirs(date_dir, exist_ok=True)
            ts = _time_mod.strftime("%H-%M-%S")
            filename = f"{ts}-{level.value}-{uuid.uuid4().hex[:6]}.jpg"
            path = os.path.join(date_dir, filename)
            cv2.imwrite(path, frame, [cv2.IMWRITE_JPEG_QUALITY, SNAPSHOT_QUALITY])
            return path
        except Exception as e:
            logger.warning("Failed to save threat snapshot: %s", e)
            return ""

    def get_snapshot_bytes(self, event_id: str) -> bytes | None:
        with self._lock:
            for e in self._history:
                if e.id == event_id and e.snapshot_path and os.path.exists(e.snapshot_path):
                    with open(e.snapshot_path, "rb") as f:
                        return f.read()
        return None

    def clear_history(self) -> None:
        with self._lock:
            self._history.clear()

    def signals_snapshot(self) -> dict[str, Any]:
        return dict(self._last_signals)


def _boxes_within(a, b, pad: int = 60) -> bool:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    return (
        ax1 >= bx1 - pad and ay1 >= by1 - pad
        and ax2 <= bx2 + pad and ay2 <= by2 + pad
    )
