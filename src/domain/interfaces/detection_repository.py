from dataclasses import dataclass
from enum import Enum

import numpy as np


class DetectionClass(Enum):
    PERSON = "person"
    BACKPACK = "backpack"
    CELL_PHONE = "cell phone"
    KNIFE = "knife"
    SCISSORS = "scissors"
    HANDBAG = "handbag"


DETECTION_COLORS = {
    DetectionClass.PERSON: (0, 220, 120),
    DetectionClass.BACKPACK: (255, 180, 50),
    DetectionClass.CELL_PHONE: (180, 100, 255),
    DetectionClass.KNIFE: (0, 80, 255),
    DetectionClass.SCISSORS: (0, 80, 255),
    DetectionClass.HANDBAG: (100, 210, 255),
}

YOLO_CLASS_MAP = {
    0: DetectionClass.PERSON,
    24: DetectionClass.BACKPACK,
    26: DetectionClass.HANDBAG,
    43: DetectionClass.KNIFE,
    67: DetectionClass.CELL_PHONE,
    76: DetectionClass.SCISSORS,
}


@dataclass
class Detection:
    label: DetectionClass
    confidence: float
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def is_threat(self) -> bool:
        return self.label in (DetectionClass.KNIFE, DetectionClass.SCISSORS)


@dataclass
class DetectionResult:
    detections: list[Detection]
    frame: np.ndarray

    @property
    def person_count(self) -> int:
        return sum(1 for d in self.detections if d.label == DetectionClass.PERSON)

    @property
    def threat_count(self) -> int:
        return sum(1 for d in self.detections if d.is_threat)

    @property
    def phone_count(self) -> int:
        return sum(1 for d in self.detections if d.label == DetectionClass.CELL_PHONE)

    @property
    def bag_count(self) -> int:
        return sum(
            1 for d in self.detections
            if d.label in (DetectionClass.BACKPACK, DetectionClass.HANDBAG)
        )


class DetectionRepository:
    def detect(self, frame: np.ndarray) -> DetectionResult: ...
