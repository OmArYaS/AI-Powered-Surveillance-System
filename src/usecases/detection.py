from dataclasses import dataclass, field
from time import time

from src.domain.interfaces.detection_repository import DetectionResult


@dataclass
class DetectionStats:
    total_detections: int = 0
    persons: int = 0
    phones: int = 0
    bags: int = 0
    threats: int = 0
    last_detection_time: float = field(default_factory=time)

    def update(self, result: DetectionResult) -> None:
        self.persons = result.person_count
        self.phones = result.phone_count
        self.bags = result.bag_count
        self.threats = result.threat_count
        self.total_detections = len(result.detections)
        if self.total_detections > 0:
            self.last_detection_time = time()

    @property
    def has_threat(self) -> bool:
        return self.threats > 0


class DetectionUseCase:
    def __init__(self, detection_repo):
        self._repo = detection_repo
        self.stats = DetectionStats()
        self._enabled = True
        self._last_result = None

    def detect(self, frame):
        if not self._enabled:
            return None
        result = self._repo.detect(frame)
        if result is not None:
            self.stats.update(result)
            self._last_result = result
        return result

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    @property
    def last_result(self):
        return self._last_result
