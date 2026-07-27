from dataclasses import dataclass, field
from enum import Enum
from time import time
from typing import Any


class ItemType(Enum):
    PHONE = "phone"


class ItemState(Enum):
    NEW = "new"
    STATIONARY = "stationary"
    HELD = "held"
    ABANDONED = "abandoned"
    REMOVED = "removed"


class OwnershipType(Enum):
    CLAIM = "claim"
    DROP = "drop"
    THEFT = "theft"
    ABANDONED = "abandoned"
    RETURNED = "returned"


@dataclass
class BBox:
    x1: int
    y1: int
    x2: int
    y2: int

    def to_list(self) -> list[int]:
        return [self.x1, self.y1, self.x2, self.y2]

    @property
    def center(self) -> tuple[int, int]:
        return ((self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2)

    @property
    def area(self) -> int:
        return max(0, self.x2 - self.x1) * max(0, self.y2 - self.y1)

    def expanded(self, pad: int) -> "BBox":
        return BBox(
            x1=self.x1 - pad, y1=self.y1 - pad,
            x2=self.x2 + pad, y2=self.y2 + pad,
        )

    def distance_to(self, other: "BBox") -> float:
        ax1, ay1, ax2, ay2 = self.x1, self.y1, self.x2, self.y2
        bx1, by1, bx2, by2 = other.x1, other.y1, other.x2, other.y2
        dx = max(bx1 - ax2, ax1 - bx2, 0)
        dy = max(by1 - ay2, ay1 - by2, 0)
        import math
        return math.sqrt(dx * dx + dy * dy)


def iou(a: BBox, b: BBox) -> float:
    ax1, ay1, ax2, ay2 = a.x1, a.y1, a.x2, a.y2
    bx1, by1, bx2, by2 = b.x1, b.y1, b.x2, b.y2
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    if inter == 0:
        return 0.0
    union = a.area + b.area - inter
    return inter / union if union > 0 else 0.0


@dataclass
class TrackedItem:
    id: str
    type: ItemType
    state: ItemState = ItemState.NEW
    owner_id: str | None = None
    origin_bbox: BBox | None = None
    last_bbox: BBox | None = None
    first_seen: float = field(default_factory=time)
    last_seen: float = field(default_factory=time)
    last_state_change: float = field(default_factory=time)
    disappear_count: int = 0
    held_by_history: list[str] = field(default_factory=list)
    held_since: float | None = None
    stationary_since: float | None = None
    candidate_taker: str | None = None
    candidate_taker_since: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "state": self.state.value,
            "owner_id": self.owner_id,
            "origin_bbox": self.origin_bbox.to_list() if self.origin_bbox else None,
            "last_bbox": self.last_bbox.to_list() if self.last_bbox else None,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "last_state_change": self.last_state_change,
            "disappear_count": self.disappear_count,
            "held_by_history": list(self.held_by_history),
        }


@dataclass
class OwnershipEvent:
    id: str
    type: OwnershipType
    item_id: str
    person_id: str | None
    second_person_id: str | None = None
    description: str = ""
    confidence: float = 1.0
    timestamp: float = field(default_factory=time)
    bbox: BBox | None = None
    snapshot_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "item_id": self.item_id,
            "person_id": self.person_id,
            "second_person_id": self.second_person_id,
            "description": self.description,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "bbox": self.bbox.to_list() if self.bbox else None,
            "snapshot_url": f"/api/items/{self.id}/snapshot" if self.snapshot_path else None,
        }


@dataclass
class PersonBox:
    person_id: str | None
    bbox: BBox
    confidence: float = 1.0
    has_face: bool = False
