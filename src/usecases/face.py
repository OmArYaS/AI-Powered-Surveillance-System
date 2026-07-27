from dataclasses import dataclass, field
from time import time

import numpy as np

from src.domain.interfaces.face_repository import (
    DetectedPerson,
    FaceCategory,
    FaceRepository,
    FaceResult,
)


@dataclass
class FaceStats:
    known_faces: list[str] = field(default_factory=list)
    auto_faces: list[str] = field(default_factory=list)
    new_visitors: list[str] = field(default_factory=list)
    total_unique_visitors: int = 0
    last_seen: dict[str, float] = field(default_factory=dict)

    def update(self, result: FaceResult) -> None:
        self.known_faces = [f.name for f in result.faces if f.category == FaceCategory.KNOWN]
        self.auto_faces = [f.name for f in result.faces if f.category == FaceCategory.AUTO]
        self.new_visitors = [f.name for f in result.faces if f.category == FaceCategory.NEW]
        now = time()
        for name in self.known_faces + self.auto_faces + self.new_visitors:
            self.last_seen[name] = now


class FaceUseCase:
    def __init__(self, face_repo: FaceRepository):
        self._repo = face_repo
        self.stats = FaceStats()
        self._enabled = True
        self._last_result: FaceResult | None = None

    def detect(self, frame: np.ndarray) -> FaceResult | None:
        if not self._enabled:
            return None
        result = self._repo.detect_and_recognize(frame)
        if result is not None:
            self.stats.update(result)
            self.stats.total_unique_visitors = len(self._repo.get_detected_persons())
            self._last_result = result
        return result

    @property
    def last_result(self) -> FaceResult | None:
        return self._last_result

    def register(self, name: str, image: np.ndarray) -> bool:
        return self._repo.register_face(name, image)

    def get_registered(self) -> list[str]:
        return self._repo.get_registered_names()

    def delete(self, name: str) -> bool:
        return self._repo.delete_face(name)

    def get_detected_persons(self) -> list[DetectedPerson]:
        return self._repo.get_detected_persons()

    def delete_detected_person(self, person_id: str) -> bool:
        return self._repo.delete_detected_person(person_id)

    def promote_detected_person(self, person_id: str, real_name: str) -> bool:
        return self._repo.promote_detected_person(person_id, real_name)

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False

    @property
    def is_enabled(self) -> bool:
        return self._enabled
