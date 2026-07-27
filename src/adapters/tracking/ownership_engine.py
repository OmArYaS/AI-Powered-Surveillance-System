import logging
import uuid
from time import time
from typing import Iterable

from src.domain.entities.item import (
    BBox,
    ItemState,
    ItemType,
    OwnershipEvent,
    OwnershipType,
    PersonBox,
    TrackedItem,
)

logger = logging.getLogger(__name__)

PROXIMITY_PX = 100
HOLD_DURATION_S = 1.5
DISAPPEAR_THEFT_S = 3.0
ABANDON_S = 30.0
EVENT_COOLDOWN_S = 5.0
NEAR_FRAMES_TO_CLAIM = 5


class OwnershipEngine:
    def __init__(
        self,
        proximity_px: int = PROXIMITY_PX,
        hold_duration_s: float = HOLD_DURATION_S,
        disappear_theft_s: float = DISAPPEAR_THEFT_S,
        abandon_s: float = ABANDON_S,
    ):
        self._proximity_px = proximity_px
        self._hold_duration_s = hold_duration_s
        self._disappear_theft_s = disappear_theft_s
        self._abandon_s = abandon_s
        self._last_event_time: dict[str, float] = {}

    def _cooldown_ok(self, key: str) -> bool:
        now = time()
        last = self._last_event_time.get(key, 0.0)
        if now - last < EVENT_COOLDOWN_S:
            return False
        self._last_event_time[key] = now
        return True

    @staticmethod
    def _nearest_person(item: TrackedItem, persons: list[PersonBox]) -> PersonBox | None:
        if item.last_bbox is None or not persons:
            return None
        best: PersonBox | None = None
        best_dist = float("inf")
        for p in persons:
            d = item.last_bbox.distance_to(p.bbox)
            if d < best_dist:
                best_dist = d
                best = p
        if best is not None and best_dist <= OwnershipEngine._dyn_proximity_px_static():
            return best
        return None

    @staticmethod
    def _dyn_proximity_px_static() -> int:
        return PROXIMITY_PX

    def process(
        self,
        items: dict[str, TrackedItem],
        persons: list[PersonBox],
        now: float | None = None,
    ) -> list[OwnershipEvent]:
        now = now or time()
        events: list[OwnershipEvent] = []

        for item_id, item in items.items():
            if item.type != ItemType.PHONE:
                continue
            if item.state == ItemState.REMOVED:
                continue

            nearest = self._nearest_person(item, persons)
            ev = self._step_item(item, nearest, persons, now)
            if ev is not None:
                events.append(ev)

        return events

    def _step_item(
        self,
        item: TrackedItem,
        nearest: PersonBox | None,
        persons: list[PersonBox],
        now: float,
    ) -> OwnershipEvent | None:
        if item.state == ItemState.NEW:
            if nearest is None and item.disappear_count == 0:
                item.state = ItemState.STATIONARY
                item.stationary_since = now
                item.last_state_change = now
                return None
            return None

        if item.state == ItemState.STATIONARY:
            if nearest is not None:
                item.candidate_taker = nearest.person_id
                if item.candidate_taker != nearest.person_id or item.candidate_taker_since is None:
                    item.candidate_taker = nearest.person_id
                    item.candidate_taker_since = now
                if nearest.person_id is not None and nearest.person_id == item.owner_id:
                    if not item.held_by_history or item.held_by_history[-1] == nearest.person_id:
                        item.state = ItemState.HELD
                        item.held_since = now
                        item.last_state_change = now
                        return self._make_event(
                            OwnershipType.CLAIM,
                            item.id, nearest.person_id,
                            description=f"{self._item_label(item)} claimed by {self._person_label(nearest.person_id)}",
                            confidence=0.95, item=item,
                        )
                if self._held_long_enough(item, now) and item.owner_id is None:
                    item.owner_id = nearest.person_id
                    item.state = ItemState.HELD
                    item.held_since = now
                    item.last_state_change = now
                    item.held_by_history.append(nearest.person_id or "unknown")
                    return self._make_event(
                        OwnershipType.CLAIM,
                        item.id, nearest.person_id,
                        description=f"{self._item_label(item)} auto-registered to {self._person_label(nearest.person_id)}",
                        confidence=0.80, item=item,
                    )
                if self._held_long_enough(item, now) and item.owner_id is not None and nearest.person_id is not None and nearest.person_id != item.owner_id:
                    item.candidate_taker = nearest.person_id
                return None
            if item.disappear_count > 0 and (now - item.last_seen) >= self._disappear_theft_s:
                if item.owner_id is not None:
                    return self._make_event(
                        OwnershipType.THEFT,
                        item.id, item.owner_id,
                        second_person_id=item.candidate_taker,
                        description=f"{self._person_label(item.owner_id)}'s {self._item_label(item)} disappeared (possible theft)",
                        confidence=0.85, item=item,
                    )
                return self._make_event(
                    OwnershipType.THEFT,
                    item.id, None,
                    second_person_id=item.candidate_taker,
                    description=f"Unowned {self._item_label(item)} disappeared (possible theft)",
                    confidence=0.70, item=item,
                )
            return None

        if item.state == ItemState.HELD:
            if nearest is None or (nearest.person_id is not None and nearest.person_id != item.owner_id):
                if item.held_since is not None and (now - item.held_since) >= 0.5:
                    item.state = ItemState.STATIONARY
                    item.stationary_since = now
                    item.last_state_change = now
                    item.held_since = None
                    if nearest is not None and nearest.person_id is not None and item.owner_id is not None and nearest.person_id != item.owner_id:
                        return self._make_event(
                            OwnershipType.THEFT,
                            item.id, item.owner_id,
                            second_person_id=nearest.person_id,
                            description=f"{self._person_label(nearest.person_id)} took {self._person_label(item.owner_id)}'s {self._item_label(item)}",
                            confidence=0.92, item=item,
                        )
                    return self._make_event(
                        OwnershipType.DROP,
                        item.id, item.owner_id,
                        description=f"{self._person_label(item.owner_id)} dropped {self._item_label(item)}",
                        confidence=0.80, item=item,
                    )
                return None
            if item.owner_id is None and nearest is not None and nearest.person_id is not None:
                if item.held_since is not None and (now - item.held_since) >= 0.5:
                    item.owner_id = nearest.person_id
                    item.held_by_history.append(nearest.person_id)
                    return self._make_event(
                        OwnershipType.CLAIM,
                        item.id, nearest.person_id,
                        description=f"{self._item_label(item)} now owned by {self._person_label(nearest.person_id)}",
                        confidence=0.85, item=item,
                    )
            return None

        if item.state == ItemState.ABANDONED:
            if nearest is not None and nearest.person_id is not None and nearest.person_id == item.owner_id:
                item.state = ItemState.HELD
                item.held_since = now
                item.last_state_change = now
                return self._make_event(
                    OwnershipType.RETURNED,
                    item.id, nearest.person_id,
                    description=f"{self._person_label(nearest.person_id)} picked up their {self._item_label(item)}",
                    confidence=0.95, item=item,
                )
            if nearest is not None and nearest.person_id is not None and nearest.person_id != item.owner_id:
                return self._make_event(
                    OwnershipType.THEFT,
                    item.id, item.owner_id,
                    second_person_id=nearest.person_id,
                    description=f"{self._person_label(nearest.person_id)} took abandoned {self._item_label(item)} of {self._person_label(item.owner_id)}",
                    confidence=0.95, item=item,
                )
            return None

        return None

    def _held_long_enough(self, item: TrackedItem, now: float) -> bool:
        if item.candidate_taker_since is None:
            return False
        return (now - item.candidate_taker_since) >= self._hold_duration_s

    def _make_event(
        self,
        type_: OwnershipType,
        item_id: str,
        person_id: str | None,
        description: str,
        confidence: float,
        item: TrackedItem,
        second_person_id: str | None = None,
    ) -> OwnershipEvent | None:
        key = f"{type_.value}:{item_id}:{person_id or 'none'}:{second_person_id or 'none'}"
        if not self._cooldown_ok(key):
            return None
        return OwnershipEvent(
            id=uuid.uuid4().hex[:12],
            type=type_,
            item_id=item_id,
            person_id=person_id,
            second_person_id=second_person_id,
            description=description,
            confidence=confidence,
            bbox=item.last_bbox,
            timestamp=time(),
        )

    @staticmethod
    def _item_label(item: TrackedItem) -> str:
        return item.type.value.capitalize()

    @staticmethod
    def _person_label(pid: str | None) -> str:
        if not pid:
            return "Unknown person"
        if pid.startswith("person_"):
            return pid.replace("_", " #")
        return pid

    def check_abandoned(self, items: dict[str, TrackedItem], now: float | None = None) -> list[OwnershipEvent]:
        now = now or time()
        out: list[OwnershipEvent] = []
        for item in items.values():
            if item.state == ItemState.STATIONARY and item.stationary_since is not None:
                if (now - item.stationary_since) >= self._abandon_s and item.disappear_count == 0:
                    item.state = ItemState.ABANDONED
                    item.last_state_change = now
                    out.append(self._make_event(
                        OwnershipType.ABANDONED,
                        item.id, item.owner_id,
                        description=f"{self._item_label(item)} abandoned by {self._person_label(item.owner_id)}",
                        confidence=0.75, item=item,
                    ))
        return out
