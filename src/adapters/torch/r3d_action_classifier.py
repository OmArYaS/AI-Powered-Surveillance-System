import threading
from collections import deque
from time import time

import cv2
import numpy as np
import torch
from torchvision.models.video import R3D_18_Weights, r3d_18

from src.domain.entities.threat import ActionPrediction
from src.domain.interfaces.threat_repository import ActionClassifierRepository

CLIP_LEN = 16
FRAME_SIZE = 112
STRIDE = 4

VIOLENT_KEYWORDS = (
    "punch", "kick", "fight", "box", "wrestle", "slap",
    "hit", "choke", "headbutt", "martial", "karate",
    "judo", "sword", "shoot", "gun", "pistol", "rifle",
    "shooting", "hunt", "arrest", "attack",
)

K400_VIOLENT_INDICES: list[int] = []


def _build_violent_index(weights: R3D_18_Weights) -> list[int]:
    meta = weights.meta
    categories = meta.get("categories", [])
    indices = []
    for i, cat in enumerate(categories):
        c = cat.lower()
        for kw in VIOLENT_KEYWORDS:
            if kw in c:
                indices.append(i)
                break
    return indices


class R3DActionClassifier(ActionClassifierRepository):
    def __init__(self, clip_len: int = CLIP_LEN, frame_size: int = FRAME_SIZE, stride: int = STRIDE):
        self._clip_len = clip_len
        self._frame_size = frame_size
        self._stride = stride

        weights = R3D_18_Weights.DEFAULT
        self._model = r3d_18(weights=weights)
        self._model.eval()
        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        self._model.to(self._device)

        self._categories = weights.meta.get("categories", [])
        global K400_VIOLENT_INDICES
        K400_VIOLENT_INDICES = _build_violent_index(weights)
        if not K400_VIOLENT_INDICES:
            K400_VIOLENT_INDICES = list(range(min(50, len(self._categories))))

        self._buffer: deque[np.ndarray] = deque(maxlen=clip_len)
        self._lock = threading.Lock()
        self._last_predict = 0.0
        self._min_interval = 0.5

    def push_frame(self, frame: np.ndarray) -> None:
        if frame is None or frame.size == 0:
            return
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(rgb, (self._frame_size, self._frame_size))
        tensor = resized.astype(np.float32) / 255.0
        mean = np.array([0.43216, 0.394666, 0.37645], dtype=np.float32)
        std = np.array([0.22803, 0.22145, 0.216989], dtype=np.float32)
        tensor = (tensor - mean) / std
        tensor = np.transpose(tensor, (2, 0, 1))
        with self._lock:
            self._buffer.append(tensor)

    def predict(self) -> ActionPrediction | None:
        now = time()
        if now - self._last_predict < self._min_interval:
            return None
        with self._lock:
            if len(self._buffer) < self._clip_len:
                return None
            frames = list(self._buffer)[-self._clip_len:]
        self._last_predict = now

        clip = np.stack(frames, axis=1)
        clip_t = torch.from_numpy(clip).unsqueeze(0).to(self._device).float()

        with torch.no_grad():
            logits = self._model(clip_t)
            probs = torch.softmax(logits, dim=1)[0]
            top_idx = int(torch.argmax(probs).item())
            top_conf = float(probs[top_idx].item())
            top_label = self._categories[top_idx] if top_idx < len(self._categories) else f"class_{top_idx}"

            violent_conf = 0.0
            if K400_VIOLENT_INDICES:
                violent_probs = probs[K400_VIOLENT_INDICES]
                violent_conf = float(violent_probs.max().item())

            is_violent = (
                top_idx in K400_VIOLENT_INDICES
                and top_conf > 0.30
            ) or violent_conf > 0.50

        return ActionPrediction(
            label=top_label,
            confidence=top_conf,
            is_violent=is_violent,
        )
