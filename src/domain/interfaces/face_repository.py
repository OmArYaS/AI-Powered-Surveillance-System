from dataclasses import dataclass
from enum import Enum

import numpy as np


class FaceCategory(str, Enum):
    KNOWN = "known"
    AUTO = "auto"
    NEW = "new"


@dataclass
class FaceMatch:
    name: str
    confidence: float
    x1: int
    y1: int
    x2: int
    y2: int
    category: FaceCategory = FaceCategory.KNOWN
    snapshot_path: str | None = None

    @property
    def is_known(self) -> bool:
        return self.category == FaceCategory.KNOWN


@dataclass
class FaceResult:
    faces: list[FaceMatch]
    frame: np.ndarray

    @property
    def known_count(self) -> int:
        return sum(1 for f in self.faces if f.category == FaceCategory.KNOWN)

    @property
    def auto_count(self) -> int:
        return sum(1 for f in self.faces if f.category in (FaceCategory.AUTO, FaceCategory.NEW))


@dataclass
class DetectedPerson:
    person_id: str
    snapshot_path: str
    first_seen: float
    last_seen: float
    sample_count: int


class FaceRepository:
    def detect_and_recognize(self, frame: np.ndarray) -> FaceResult | None: ...
    def register_face(self, name: str, image: np.ndarray) -> bool: ...
    def get_registered_names(self) -> list[str]: ...
    def delete_face(self, name: str) -> bool: ...
    def get_detected_persons(self) -> list[DetectedPerson]: ...
    def delete_detected_person(self, person_id: str) -> bool: ...
    def promote_detected_person(self, person_id: str, real_name: str) -> bool: ...
