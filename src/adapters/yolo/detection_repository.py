import cv2
import numpy as np
from ultralytics import YOLO

from src.domain.interfaces.detection_repository import (
    Detection,
    DetectionClass,
    DetectionRepository,
    DetectionResult,
    YOLO_CLASS_MAP,
    DETECTION_COLORS,
)

TARGET_CLASSES = list(YOLO_CLASS_MAP.keys())

WEAPON_CLASSES = {DetectionClass.KNIFE, DetectionClass.SCISSORS}

LABEL_DISPLAY = {
    DetectionClass.PERSON: "Person",
    DetectionClass.CELL_PHONE: "Phone",
    DetectionClass.BACKPACK: "Backpack",
    DetectionClass.HANDBAG: "Handbag",
    DetectionClass.KNIFE: "Knife",
    DetectionClass.SCISSORS: "Scissors",
}

CLASS_CONFIDENCE = {
    DetectionClass.PERSON: 0.45,
    DetectionClass.CELL_PHONE: 0.20,
    DetectionClass.BACKPACK: 0.25,
    DetectionClass.HANDBAG: 0.25,
    DetectionClass.KNIFE: 0.35,
    DetectionClass.SCISSORS: 0.35,
}

DEFAULT_IMGSZ = 1280


def _draw_rounded_rect(img, pt1, pt2, color, thickness, radius=8):
    x1, y1 = pt1
    x2, y2 = pt2
    r = min(radius, (x2 - x1) // 4, (y2 - y1) // 4)

    cv2.line(img, (x1 + r, y1), (x2 - r, y1), color, thickness)
    cv2.line(img, (x1 + r, y2), (x2 - r, y2), color, thickness)
    cv2.line(img, (x1, y1 + r), (x1, y2 - r), color, thickness)
    cv2.line(img, (x2, y1 + r), (x2, y2 - r), color, thickness)

    cv2.ellipse(img, (x1 + r, y1 + r), (r, r), 180, 0, 90, color, thickness)
    cv2.ellipse(img, (x2 - r, y1 + r), (r, r), 270, 0, 90, color, thickness)
    cv2.ellipse(img, (x1 + r, y2 - r), (r, r), 90, 0, 90, color, thickness)
    cv2.ellipse(img, (x2 - r, y2 - r), (r, r), 0, 0, 90, color, thickness)


def _draw_corner_brackets(img, pt1, pt2, color, length=20, thickness=2):
    x1, y1 = pt1
    x2, y2 = pt2

    cv2.line(img, (x1, y1), (x1 + length, y1), color, thickness)
    cv2.line(img, (x1, y1), (x1, y1 + length), color, thickness)

    cv2.line(img, (x2, y1), (x2 - length, y1), color, thickness)
    cv2.line(img, (x2, y1), (x2, y2 + length), color, thickness)

    cv2.line(img, (x1, y2), (x1 + length, y2), color, thickness)
    cv2.line(img, (x1, y2), (x1, y2 + length), color, thickness)

    cv2.line(img, (x2, y2), (x2 - length, y2), color, thickness)
    cv2.line(img, (x2, y2), (x2, y2 + length), color, thickness)


def _draw_label_pill(img, text, conf, x, y, color, is_threat=False):
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.55
    font_thick = 1

    (tw, th), baseline = cv2.getTextSize(text, font, font_scale, font_thick)
    conf_text = f" {conf:.0%}"
    (cw, ch), _ = cv2.getTextSize(conf_text, font, 0.45, 1)

    pad_x, pad_y = 10, 6
    pill_w = tw + cw + pad_x * 2 + 4
    pill_h = th + pad_y * 2
    pill_x = x
    pill_y = y - pill_h - 4

    overlay = img.copy()
    cv2.rectangle(overlay, (pill_x, pill_y), (pill_x + pill_w, pill_y + pill_h), color, -1)
    cv2.addWeighted(overlay, 0.85, img, 0.15, 0, img)

    cv2.putText(img, text, (pill_x + pad_x, pill_y + pad_y + th),
                font, font_scale, (255, 255, 255), font_thick, cv2.LINE_AA)

    conf_x = pill_x + pad_x + tw + 4
    cv2.putText(img, conf_text, (conf_x, pill_y + pad_y + th),
                font, 0.45, (200, 200, 200), 1, cv2.LINE_AA)

    if is_threat:
        badge_text = " ! THREAT "
        (bw, bh), _ = cv2.getTextSize(badge_text, font, 0.5, 1)
        bx = pill_x + pill_w + 6
        overlay2 = img.copy()
        cv2.rectangle(overlay2, (bx, pill_y), (bx + bw + pad_x * 2, pill_y + pill_h), (0, 0, 220), -1)
        cv2.addWeighted(overlay2, 0.9, img, 0.1, 0, img)
        cv2.putText(img, badge_text, (bx + pad_x, pill_y + pad_y + th),
                    font, 0.5, (255, 255, 255), 1, cv2.LINE_AA)


class YOLODetectionRepository(DetectionRepository):
    def __init__(
        self,
        model_path: str = "yolo11n.pt",
        imgsz: int = DEFAULT_IMGSZ,
    ):
        import torch
        self._model = YOLO(model_path)
        self._imgsz = imgsz
        self._device = "0" if torch.cuda.is_available() else "cpu"
        self._last_warmup = False

    def detect(self, frame: np.ndarray) -> DetectionResult | None:
        results = self._model.predict(
            frame,
            classes=TARGET_CLASSES,
            conf=min(CLASS_CONFIDENCE.values()),
            iou=0.5,
            imgsz=self._imgsz,
            device=self._device,
            verbose=False,
        )
        if not results:
            return None

        detections = []
        annotated = frame.copy()

        for r in results:
            if r.boxes is None:
                continue
            for box in r.boxes:
                cls_id = int(box.cls[0])
                if cls_id not in YOLO_CLASS_MAP:
                    continue

                label = YOLO_CLASS_MAP[cls_id]
                conf = float(box.conf[0])
                if conf < CLASS_CONFIDENCE.get(label, 0.5):
                    continue

                x1, y1, x2, y2 = map(int, box.xyxy[0])
                is_weapon = label in WEAPON_CLASSES

                color = DETECTION_COLORS.get(label, (255, 255, 255))

                overlay = annotated.copy()
                fill_color = color + (40,) if len(color) == 3 else color
                cv2.rectangle(overlay, (x1, y1), (x2, y2), fill_color, -1)
                cv2.addWeighted(overlay, 0.15, annotated, 0.85, 0, annotated)

                box_thickness = 3 if is_weapon else 2
                _draw_rounded_rect(annotated, (x1, y1), (x2, y2), color, box_thickness, radius=10)

                corner_len = min(25, (x2 - x1) // 3, (y2 - y1) // 3)
                _draw_corner_brackets(annotated, (x1, y1), (x2, y2), (255, 255, 255), corner_len, 2)

                display_text = LABEL_DISPLAY.get(label, label.value)
                _draw_label_pill(annotated, display_text, conf, x1, y1, color, is_weapon)

                detections.append(Detection(
                    label=label, confidence=conf,
                    x1=x1, y1=y1, x2=x2, y2=y2,
                ))

        return DetectionResult(detections=detections, frame=annotated)
