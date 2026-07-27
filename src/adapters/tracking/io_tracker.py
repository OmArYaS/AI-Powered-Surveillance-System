import uuid
from time import time
from typing import Iterable

from src.domain.entities.item import BBox, ItemState, ItemType, TrackedItem, iou


class IoUTracker:
    def __init__(self, iou_threshold: float = 0.30, max_disappear_frames: int = 30):
        self._iou_threshold = iou_threshold
        self._max_disappear_frames = max_disappear_frames
        self._items: dict[str, TrackedItem] = {}
        self._frame_idx = 0

    def update(
        self,
        detections: list[tuple[BBox, ItemType, float]],
        existing_items: dict[str, TrackedItem] | None = None,
    ) -> list[TrackedItem]:
        if existing_items is not None:
            for k, v in existing_items.items():
                if k not in self._items:
                    self._items[k] = v
        self._frame_idx += 1
        now = time()

        used_existing: set[str] = set()
        new_items: list[TrackedItem] = []

        for bbox, itype, conf in detections:
            best_id: str | None = None
            best_iou = 0.0
            for item_id, item in self._items.items():
                if item_id in used_existing:
                    continue
                if item.type != itype:
                    continue
                if item.last_bbox is None:
                    continue
                iou_val = iou(bbox, item.last_bbox)
                if iou_val > best_iou and iou_val >= self._iou_threshold:
                    best_iou = iou_val
                    best_id = item_id

            if best_id is not None:
                item = self._items[best_id]
                item.last_bbox = bbox
                item.last_seen = now
                item.disappear_count = 0
                used_existing.add(best_id)
            else:
                new_id = f"{itype.value}_{uuid.uuid4().hex[:8]}"
                new_item = TrackedItem(
                    id=new_id,
                    type=itype,
                    state=ItemState.NEW,
                    last_bbox=bbox,
                    origin_bbox=bbox,
                    first_seen=now,
                    last_seen=now,
                )
                self._items[new_id] = new_item
                new_items.append(new_item)
                used_existing.add(new_id)

        for item_id, item in self._items.items():
            if item_id not in used_existing:
                item.disappear_count += 1

        return new_items

    def get_active(self, max_disappear: int | None = None) -> list[TrackedItem]:
        max_d = max_disappear if max_disappear is not None else self._max_disappear_frames
        return [
            item for item in self._items.values()
            if item.disappear_count <= max_d
            and item.state.value not in ("removed",)
        ]

    def get_all(self) -> dict[str, TrackedItem]:
        return dict(self._items)

    def cleanup_stale(self) -> int:
        before = len(self._items)
        self._items = {
            k: v for k, v in self._items.items()
            if v.disappear_count <= self._max_disappear_frames * 5
        }
        return before - len(self._items)

    def remove(self, item_id: str) -> bool:
        return self._items.pop(item_id, None) is not None

    def clear(self) -> None:
        self._items.clear()

    def __len__(self) -> int:
        return len(self._items)
