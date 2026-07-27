import numpy as np
from ultralytics import YOLO

from src.domain.entities.threat import PoseKeypoints
from src.domain.interfaces.threat_repository import PoseRepository

POSE_CONFIDENCE = 0.40
POSE_IMGSZ = 640
POSE_PERSON_CONF = 0.50
KEYPOINT_CONF_THRESHOLD = 0.30


class PoseEstimationRepository(PoseRepository):
    def __init__(self, model_path: str = "yolov8n-pose.pt", imgsz: int = POSE_IMGSZ):
        import torch
        self._model = YOLO(model_path)
        self._imgsz = imgsz
        self._device = "0" if torch.cuda.is_available() else "cpu"

    def estimate(self, frame: np.ndarray) -> list[PoseKeypoints]:
        results = self._model.predict(
            frame,
            conf=POSE_PERSON_CONF,
            imgsz=self._imgsz,
            device=self._device,
            verbose=False,
        )
        if not results:
            return []

        poses: list[PoseKeypoints] = []
        for r in results:
            if r.boxes is None or r.keypoints is None:
                continue
            for i, box in enumerate(r.boxes):
                conf = float(box.conf[0])
                if conf < POSE_CONFIDENCE:
                    continue
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                kpts_data = r.keypoints[i]
                if kpts_data is None or len(kpts_data.data) == 0:
                    continue
                kpts = kpts_data.data[0].cpu().numpy()
                kpts[:, 2] = np.where(kpts[:, 2] < KEYPOINT_CONF_THRESHOLD, 0, kpts[:, 2])
                poses.append(PoseKeypoints(
                    person_box=(x1, y1, x2, y2),
                    keypoints=kpts,
                    confidence=conf,
                ))
        return poses
