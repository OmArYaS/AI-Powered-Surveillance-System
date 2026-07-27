import cv2
import numpy as np
from ultralytics import YOLO

from src.domain.entities.threat import WeaponDetection
from src.domain.interfaces.threat_repository import WeaponRepository

WEAPON_CONFIDENCE = 0.30
WEAPON_IMGSZ = 640

WEAPON_COLOR = (0, 0, 220)
WEAPON_LABEL = "WEAPON"


class WeaponDetectionRepository(WeaponRepository):
    def __init__(self, model_path: str = "gun.pt", imgsz: int = WEAPON_IMGSZ):
        import torch
        self._model = YOLO(model_path)
        self._imgsz = imgsz
        self._device = "0" if torch.cuda.is_available() else "cpu"
        self._names = self._model.names

    def detect(self, frame: np.ndarray) -> list[WeaponDetection]:
        results = self._model.predict(
            frame,
            conf=WEAPON_CONFIDENCE,
            iou=0.5,
            imgsz=self._imgsz,
            device=self._device,
            verbose=False,
        )
        if not results:
            return []

        detections: list[WeaponDetection] = []
        for r in results:
            if r.boxes is None:
                continue
            for box in r.boxes:
                cls_id = int(box.cls[0])
                label = self._names.get(cls_id, "weapon")
                conf = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                detections.append(WeaponDetection(
                    label=label,
                    confidence=conf,
                    x1=x1, y1=y1, x2=x2, y2=y2,
                ))
        return detections


def annotate_weapon(frame: np.ndarray, weapons: list[WeaponDetection]) -> np.ndarray:
    if not weapons:
        return frame
    out = frame.copy()
    for w in weapons:
        cv2.rectangle(out, (w.x1, w.y1), (w.x2, w.y2), WEAPON_COLOR, 3)
        label = f"{WEAPON_LABEL} {w.confidence:.0%}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
        cv2.rectangle(out, (w.x1, w.y1 - th - 10), (w.x1 + tw + 10, w.y1), WEAPON_COLOR, -1)
        cv2.putText(out, label, (w.x1 + 5, w.y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2, cv2.LINE_AA)
    return out
