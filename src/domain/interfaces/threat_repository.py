import numpy as np

from src.domain.entities.threat import ActionPrediction, PoseKeypoints, WeaponDetection


class WeaponRepository:
    def detect(self, frame: np.ndarray) -> list[WeaponDetection]: ...


class PoseRepository:
    def estimate(self, frame: np.ndarray) -> list[PoseKeypoints]: ...


class ActionClassifierRepository:
    def push_frame(self, frame: np.ndarray) -> None: ...

    def predict(self) -> ActionPrediction | None: ...
