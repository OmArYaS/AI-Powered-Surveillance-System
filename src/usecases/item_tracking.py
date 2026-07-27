import asyncio
import logging
import threading
import time as _time_mod
import uuid
from collections import deque
from dataclasses import dataclass, field
from time import time
from typing import Any

import cv2
import numpy as np

from src.adapters.tracking.io_tracker import IoUTracker
from src.adapters.tracking.ownership_engine import OwnershipEngine
from src.domain.entities.item import (
    BBox,
    ItemState,
    ItemType,
    OwnershipEvent,
    OwnershipType,
    PersonBox,
    TrackedItem,
)
from src.domain.entities.threat import ThreatEvent, ThreatLevel, ThreatType
from src.domain.interfaces.detection_repository import Detection, DetectionClass
from src.domain.interfaces.item_repository import ItemRepository
from src.presentation.realtime.ws_manager import WebSocketManager

logger = logging.getLogger(__name__)

SNAPSHOT_DIR = "data/alerts"
SNAPSHOT_QUALITY = 90
MAX_HISTORY = 200
ABANDON_CHECK_INTERVAL_S = 5.0
SAVE_INTERVAL_S = 3.0


@dataclass
class ItemStats:
    total_items: int = 0
    by_state: dict[str, int] = field(default_factory=lambda: {s.value: 0 for s in ItemState})
    by_type: dict[str, int] = field(default_factory=lambda: {t.value: 0 for t in ItemType})
    owned_items: int = 0
    thefts: int = 0
    abandons: int = 0
    last_event: OwnershipEvent | None = None

    def record_event(self, ev: OwnershipEvent) -> None:
        if ev.type == OwnershipType.THEFT:
            self.thefts += 1
        elif ev.type == OwnershipType.ABANDONED:
            self.abandons += 1
        self.last_event = ev


class ItemTrackingUseCase:
    def __init__(
        self,
        tracker: IoUTracker | None = None,
        engine: OwnershipEngine | None = None,
        repo: ItemRepository | None = None,
        ws_manager: WebSocketManager | None = None,
        snapshot_dir: str = SNAPSHOT_DIR,
    ):
        self._tracker = tracker if tracker is not None else IoUTracker()
        self._engine = engine if engine is not None else OwnershipEngine()
        self._repo = repo
        self._ws = ws_manager if ws_manager is not None else WebSocketManager()
        self._snapshot_dir = snapshot_dir

        import os
        os.makedirs(snapshot_dir, exist_ok=True)

        self._events_history: deque[OwnershipEvent] = deque(maxlen=MAX_HISTORY)
        self._lock = threading.Lock()
        self._stats = ItemStats()
        self._enabled = True
        self._last_abandon_check = 0.0
        self._last_save = 0.0

        if self._repo is not None:
            persisted = self._repo.load()
            if persisted:
                for it in persisted:
                    self._tracker._items[it.id] = it
            history = self._repo.load_events(MAX_HISTORY)
            for ev in history:
                self._events_history.append(ev)
                self._stats.record_event(ev)

    @property
    def stats(self) -> ItemStats:
        return self._stats

    @property
    def ws_manager(self) -> WebSocketManager:
        return self._ws

    @property
    def history(self) -> list[OwnershipEvent]:
        with self._lock:
            return list(self._events_history)

    @property
    def tracker(self) -> IoUTracker:
        return self._tracker

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def process_frame(
        self,
        frame: np.ndarray | None,
        detections: list[Detection] | None,
        face_persons: list[tuple[str | None, BBox]] | None = None,
    ) -> list[OwnershipEvent]:
        if not self._enabled:
            return []
        if not detections:
            detections = []

        persons: list[PersonBox] = []
        item_bboxes: list[tuple[BBox, ItemType, float]] = []
        for d in detections:
            if d.label == DetectionClass.PERSON:
                persons.append(PersonBox(
                    person_id=None,
                    bbox=BBox(d.x1, d.y1, d.x2, d.y2),
                    confidence=d.confidence,
                ))
            elif d.label == DetectionClass.CELL_PHONE:
                item_bboxes.append((BBox(d.x1, d.y1, d.x2, d.y2), ItemType.PHONE, d.confidence))

        if face_persons:
            for pid, fbbox in face_persons:
                best_person = None
                best_iou_val = 0.0
                for p in persons:
                    iou_val = self._iou(fbbox, p.bbox)
                    if iou_val > best_iou_val:
                        best_iou_val = iou_val
                        best_person = p
                if best_person is not None and best_iou_val > 0.05:
                    if best_person.person_id is None:
                        best_person.person_id = pid
                        best_person.has_face = True
                else:
                    persons.append(PersonBox(person_id=pid, bbox=fbbox, has_face=True))

        self._tracker.update(item_bboxes)
        events = self._engine.process(self._tracker._items, persons)

        now = time()
        if now - self._last_abandon_check >= ABANDON_CHECK_INTERVAL_S:
            abandon_events = self._engine.check_abandoned(self._tracker._items)
            events.extend(abandon_events)
            self._last_abandon_check = now

        if events:
            with self._lock:
                for ev in events:
                    self._events_history.appendleft(ev)
                    self._stats.record_event(ev)
                    if frame is not None and ev.type in (OwnershipType.THEFT, OwnershipType.ABANDONED):
                        ev.snapshot_path = self._save_snapshot(frame, ev)
                    if self._repo is not None:
                        self._repo.append_event(ev)

            self._save_items()

            for ev in events:
                if self._ws.client_count > 0:
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            asyncio.create_task(self._ws.broadcast({
                                "type": "item_event",
                                "data": ev.to_dict(),
                            }))
                    except RuntimeError:
                        pass

                if ev.type == OwnershipType.THEFT and self._ws.client_count > 0:
                    try:
                        threat = ThreatEvent(
                            id=uuid.uuid4().hex[:12],
                            level=ThreatLevel.HIGH,
                            type=ThreatType.WEAPON,
                            description=f"🚨 THEFT: {ev.description}",
                            confidence=ev.confidence,
                            bbox=(ev.bbox.x1, ev.bbox.y1, ev.bbox.x2, ev.bbox.y2) if ev.bbox else None,
                            snapshot_path=ev.snapshot_path,
                            source_labels=[f"theft:{ev.item_id}", f"owner:{ev.person_id}"],
                        )
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            asyncio.create_task(self._ws.broadcast({
                                "type": "threat",
                                "data": threat.to_dict(),
                            }))
                    except RuntimeError:
                        pass

        if now - self._last_save >= SAVE_INTERVAL_S:
            self._save_items()
            self._last_save = now

        return events

    def _save_items(self) -> None:
        if self._repo is None:
            return
        try:
            self._repo.save(list(self._tracker._items.values()))
        except Exception as e:
            logger.warning("Failed to persist items: %s", e)

    def _save_snapshot(self, frame: np.ndarray, ev: OwnershipEvent) -> str:
        try:
            date_dir = f"{self._snapshot_dir}/{_time_mod.strftime('%Y-%m-%d')}"
            import os
            os.makedirs(date_dir, exist_ok=True)
            ts = _time_mod.strftime("%H-%M-%S")
            filename = f"item-{ts}-{ev.type.value}-{uuid.uuid4().hex[:6]}.jpg"
            path = os.path.join(date_dir, filename)
            cv2.imwrite(path, frame, [cv2.IMWRITE_JPEG_QUALITY, SNAPSHOT_QUALITY])
            return path
        except Exception as e:
            logger.warning("Failed to save item snapshot: %s", e)
            return ""

    def get_snapshot_bytes(self, event_id: str) -> bytes | None:
        for ev in self._events_history:
            if ev.id == event_id and ev.snapshot_path:
                try:
                    with open(ev.snapshot_path, "rb") as f:
                        return f.read()
                except Exception:
                    pass
        if self._repo is not None:
            for ev in self._repo.load_events(500):
                if ev.id == event_id and ev.snapshot_path:
                    try:
                        with open(ev.snapshot_path, "rb") as f:
                            return f.read()
                    except Exception:
                        pass
        return None

    def clear_history(self) -> None:
        with self._lock:
            self._events_history.clear()
        if self._repo is not None:
            self._repo.clear()
        self._tracker.clear()

    def _iou(self, a: BBox, b: BBox) -> float:
        ax1, ay1, ax2, ay2 = a.x1, a.y1, a.x2, a.y2
        bx1, by1, bx2, by2 = b.x1, b.y1, b.x2, b.y2
        ix1, iy1 = max(ax1, bx1), max(ay1, by1)
        ix2, iy2 = min(ax2, bx2), min(ay2, by2)
        inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
        if inter == 0:
            return 0.0
        union = a.area + b.area - inter
        return inter / union if union > 0 else 0.0

    def get_items_summary(self) -> dict[str, Any]:
        items = self._tracker.get_active()
        by_state: dict[str, int] = {}
        by_type: dict[str, int] = {}
        owned = 0
        for it in items:
            by_state[it.state.value] = by_state.get(it.state.value, 0) + 1
            by_type[it.type.value] = by_type.get(it.type.value, 0) + 1
            if it.owner_id is not None:
                owned += 1
        self._stats.total_items = len(items)
        self._stats.by_state = by_state
        self._stats.by_type = by_type
        self._stats.owned_items = owned
        return {
            "enabled": self._enabled,
            "items": [it.to_dict() for it in items],
            "stats": {
                "total_items": self._stats.total_items,
                "by_state": self._stats.by_state,
                "by_type": self._stats.by_type,
                "owned_items": self._stats.owned_items,
                "thefts": self._stats.thefts,
                "abandons": self._stats.abandons,
            },
        }
