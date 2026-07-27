from dataclasses import dataclass, field
from enum import Enum
from time import time

import numpy as np


class ThreatLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


THREAT_COLORS = {
    ThreatLevel.LOW: (180, 180, 180),
    ThreatLevel.MEDIUM: (0, 165, 255),
    ThreatLevel.HIGH: (0, 80, 255),
    ThreatLevel.CRITICAL: (0, 0, 220),
}

THREAT_WEIGHTS = {
    ThreatLevel.LOW: 0.20,
    ThreatLevel.MEDIUM: 0.45,
    ThreatLevel.HIGH: 0.70,
    ThreatLevel.CRITICAL: 0.95,
}


class ThreatType(Enum):
    WEAPON = "weapon"
    VIOLENCE = "violence"
    PROXIMITY = "proximity"
    RAPID_MOTION = "rapid_motion"
    WEAPON_AND_VIOLENCE = "weapon_and_violence"


@dataclass
class ThreatEvent:
    id: str
    level: ThreatLevel
    type: ThreatType
    description: str
    confidence: float
    bbox: tuple[int, int, int, int] | None
    snapshot_path: str | None
    timestamp: float = field(default_factory=time)
    source_labels: list[str] = field(default_factory=list)
    frame: np.ndarray | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "level": self.level.value,
            "type": self.type.value,
            "description": self.description,
            "confidence": self.confidence,
            "bbox": list(self.bbox) if self.bbox else None,
            "snapshot_url": f"/api/threats/{self.id}/snapshot" if self.snapshot_path else None,
            "timestamp": self.timestamp,
            "source_labels": self.source_labels,
        }


@dataclass
class PoseKeypoints:
    person_box: tuple[int, int, int, int]
    keypoints: np.ndarray
    confidence: float

    @property
    def has_arms_raised(self) -> bool:
        if self.keypoints.shape[0] < 17:
            return False
        try:
            left_wrist = self.keypoints[9]
            right_wrist = self.keypoints[10]
            left_shoulder = self.keypoints[5]
            right_shoulder = self.keypoints[6]
            nose = self.keypoints[0]
            shoulder_y = min(left_shoulder[1], right_shoulder[1])
            return (
                left_wrist[1] < shoulder_y - 30
                and right_wrist[1] < shoulder_y - 30
                and left_wrist[1] < nose[1]
                and right_wrist[1] < nose[1]
            )
        except (IndexError, TypeError):
            return False

    @property
    def is_fighting_stance(self) -> bool:
        if self.keypoints.shape[0] < 17:
            return False
        try:
            left_wrist = self.keypoints[9]
            right_wrist = self.keypoints[10]
            left_hip = self.keypoints[11]
            right_hip = self.keypoints[12]
            hip_y = (left_hip[1] + right_hip[1]) / 2
            chest_y = (left_hip[1] + hip_y) / 2
            return (
                left_wrist[1] < chest_y
                and right_wrist[1] < chest_y
                and abs(left_wrist[1] - right_wrist[1]) < 50
            )
        except (IndexError, TypeError):
            return False


@dataclass
class WeaponDetection:
    label: str
    confidence: float
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def bbox(self) -> tuple[int, int, int, int]:
        return (self.x1, self.y1, self.x2, self.y2)

    @property
    def center(self) -> tuple[int, int]:
        return ((self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2)


@dataclass
class ActionPrediction:
    label: str
    confidence: float
    is_violent: bool
