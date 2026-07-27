from dataclasses import dataclass

from src.domain.entities.threat import (
    ActionPrediction,
    PoseKeypoints,
    ThreatLevel,
    ThreatType,
    WeaponDetection,
)
from src.domain.interfaces.detection_repository import Detection, DetectionClass

PROXIMITY_RADIUS = 200
PROXIMITY_RADIUS_SQ = PROXIMITY_RADIUS ** 2
FIGHTING_STANCE_CONFIDENCE = 0.40


@dataclass
class RuleHit:
    level: ThreatLevel
    type: ThreatType
    description: str
    confidence: float
    bbox: tuple[int, int, int, int] | None
    source_labels: list[str]


def _boxes_close(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> int:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    dx = max(bx1 - ax2, ax1 - bx2, 0)
    dy = max(by1 - ay2, ay1 - by2, 0)
    return dx * dx + dy * dy


class RuleEngine:
    def evaluate_weapon(self, weapons: list[WeaponDetection]) -> list[RuleHit]:
        hits: list[RuleHit] = []
        for w in weapons:
            level = ThreatLevel.HIGH if w.confidence >= 0.60 else ThreatLevel.MEDIUM
            hits.append(RuleHit(
                level=level,
                type=ThreatType.WEAPON,
                description=f"Weapon detected ({w.label}, {w.confidence:.0%})",
                confidence=w.confidence,
                bbox=w.bbox,
                source_labels=[f"weapon:{w.label}"],
            ))
        return hits

    def evaluate_violence(self, prediction: ActionPrediction | None) -> list[RuleHit]:
        if prediction is None or not prediction.is_violent:
            return []
        return [RuleHit(
            level=ThreatLevel.HIGH,
            type=ThreatType.VIOLENCE,
            description=f"Violent action detected: {prediction.label} ({prediction.confidence:.0%})",
            confidence=prediction.confidence,
            bbox=None,
            source_labels=[f"action:{prediction.label}"],
        )]

    def evaluate_pose(self, poses: list[PoseKeypoints], persons: list[Detection]) -> list[RuleHit]:
        if not persons or len(poses) < 2:
            return []
        hits: list[RuleHit] = []
        for p in poses:
            if p.confidence < FIGHTING_STANCE_CONFIDENCE:
                continue
            if not (p.is_fighting_stance or p.has_arms_raised):
                continue
            near = False
            for other in persons:
                d2 = _boxes_close(p.person_box, (other.x1, other.y1, other.x2, other.y2))
                if 0 < d2 < PROXIMITY_RADIUS_SQ:
                    near = True
                    break
            if not near:
                continue
            hits.append(RuleHit(
                level=ThreatLevel.MEDIUM,
                type=ThreatType.PROXIMITY,
                description="Fighting stance near another person",
                confidence=p.confidence,
                bbox=p.person_box,
                source_labels=["pose:fighting_stance", "proximity"],
            ))
        return hits

    def evaluate_proximity_only(self, persons: list[Detection], poses: list[PoseKeypoints]) -> list[RuleHit]:
        return self.evaluate_pose(poses, persons)
