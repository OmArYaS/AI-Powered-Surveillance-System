import json
import logging
import os
import threading
from collections import deque
from time import time
from typing import Any

from src.domain.entities.item import (
    BBox,
    ItemState,
    ItemType,
    OwnershipEvent,
    OwnershipType,
    TrackedItem,
)
from src.domain.interfaces.item_repository import ItemRepository

logger = logging.getLogger(__name__)

ITEMS_FILE = "data/items.json"
EVENTS_FILE = "data/items_log.json"
EVENTS_MAX = 500
SAVE_DEBOUNCE_S = 1.0


def _bbox_from_list(lst: list[int] | None) -> BBox | None:
    if not lst or len(lst) != 4:
        return None
    return BBox(int(lst[0]), int(lst[1]), int(lst[2]), int(lst[3]))


class JsonItemStore(ItemRepository):
    def __init__(self, items_path: str = ITEMS_FILE, events_path: str = EVENTS_FILE):
        self._items_path = items_path
        self._events_path = events_path
        self._lock = threading.Lock()
        self._dirty = False
        self._last_save = 0.0
        self._items: dict[str, TrackedItem] = {}
        self._events: deque[OwnershipEvent] = deque(maxlen=EVENTS_MAX)
        os.makedirs(os.path.dirname(items_path) or ".", exist_ok=True)
        self._load()

    def _load(self) -> None:
        if os.path.exists(self._items_path):
            try:
                with open(self._items_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for it in data.get("items", []):
                    item = self._deserialize_item(it)
                    if item is not None:
                        self._items[item.id] = item
            except Exception as e:
                logger.warning("Failed to load items: %s", e)

        if os.path.exists(self._events_path):
            try:
                with open(self._events_path, "r", encoding="utf-8") as f:
                    events = json.load(f)
                for e in events:
                    ev = self._deserialize_event(e)
                    if ev is not None:
                        self._events.append(ev)
            except Exception as e:
                logger.warning("Failed to load events: %s", e)

    def _deserialize_item(self, d: dict[str, Any]) -> TrackedItem | None:
        try:
            return TrackedItem(
                id=d["id"],
                type=ItemType(d.get("type", "phone")),
                state=ItemState(d.get("state", "new")),
                owner_id=d.get("owner_id"),
                origin_bbox=_bbox_from_list(d.get("origin_bbox")),
                last_bbox=_bbox_from_list(d.get("last_bbox")),
                first_seen=d.get("first_seen", time()),
                last_seen=d.get("last_seen", time()),
                last_state_change=d.get("last_state_change", time()),
                disappear_count=d.get("disappear_count", 0),
                held_by_history=list(d.get("held_by_history", [])),
            )
        except Exception as e:
            logger.warning("Failed to deserialize item: %s", e)
            return None

    def _deserialize_event(self, d: dict[str, Any]) -> OwnershipEvent | None:
        try:
            return OwnershipEvent(
                id=d["id"],
                type=OwnershipType(d["type"]),
                item_id=d["item_id"],
                person_id=d.get("person_id"),
                second_person_id=d.get("second_person_id"),
                description=d.get("description", ""),
                confidence=d.get("confidence", 1.0),
                timestamp=d.get("timestamp", time()),
                bbox=_bbox_from_list(d.get("bbox")),
            )
        except Exception as e:
            logger.warning("Failed to deserialize event: %s", e)
            return None

    def load(self) -> list[TrackedItem]:
        with self._lock:
            return list(self._items.values())

    def save(self, items: list[TrackedItem]) -> None:
        with self._lock:
            self._items = {it.id: it for it in items}
            self._dirty = True
            self._maybe_save_locked(force=True)

    def _maybe_save_locked(self, force: bool = False) -> None:
        now = time()
        if not self._dirty:
            return
        if not force and now - self._last_save < SAVE_DEBOUNCE_S:
            return
        try:
            payload = {
                "version": 1,
                "saved_at": now,
                "items": [it.to_dict() for it in self._items.values()],
            }
            tmp = self._items_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            os.replace(tmp, self._items_path)
            self._dirty = False
            self._last_save = now
        except Exception as e:
            logger.warning("Failed to save items: %s", e)

    def append_event(self, event: OwnershipEvent) -> None:
        with self._lock:
            self._events.append(event)
            try:
                events_list = [e.to_dict() for e in self._events]
                tmp = self._events_path + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(events_list, f, indent=2)
                os.replace(tmp, self._events_path)
            except Exception as e:
                logger.warning("Failed to save event: %s", e)

    def load_events(self, limit: int = 200) -> list[OwnershipEvent]:
        with self._lock:
            return list(self._events)[-limit:]

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
            self._events.clear()
            self._dirty = True
            self._maybe_save_locked(force=True)
            try:
                if os.path.exists(self._events_path):
                    with open(self._events_path, "w", encoding="utf-8") as f:
                        json.dump([], f)
            except Exception:
                pass
