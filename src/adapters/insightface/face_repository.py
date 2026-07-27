import os
import re
import shutil
import time

import cv2
import numpy as np
from insightface.app import FaceAnalysis

from src.domain.interfaces.face_repository import (
    DetectedPerson,
    FaceCategory,
    FaceMatch,
    FaceRepository,
    FaceResult,
)

DATASET_DIR = "face_dataset"
AUTO_DIR_NAME = "__unknowns__"
DET_SIZE = (640, 640)
KNOWN_THRESHOLD = 0.45
AUTO_THRESHOLD = 0.80
DETECTION_SCORE_THRESHOLD = 0.6
MIN_FACE_SIZE = 80
BLUR_THRESHOLD = 50.0
MAX_EMBEDDINGS_PER_PERSON = 8
EMBEDDING_DEDUP_THRESHOLD = 0.18
RECENT_REGISTER_COOLDOWN = 3.0
PERSON_ID_PATTERN = re.compile(r"^person_(\d+)$")
META_FILE = "meta.json"


def _ensure_cuda_runtime_on_path() -> None:
    import torch
    torch_lib = os.path.join(os.path.dirname(torch.__file__), "lib")
    if os.path.isdir(torch_lib) and torch_lib not in os.environ.get("PATH", ""):
        os.environ["PATH"] = torch_lib + os.pathsep + os.environ.get("PATH", "")


class InsightFaceRepository(FaceRepository):
    def __init__(self, providers: list[str] | None = None):
        _ensure_cuda_runtime_on_path()
        os.makedirs(DATASET_DIR, exist_ok=True)
        os.makedirs(self._auto_dir, exist_ok=True)
        if providers is None:
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        self._app = FaceAnalysis(name="buffalo_l", providers=providers)
        self._app.prepare(ctx_id=0, det_size=DET_SIZE)
        self._known_cache: dict[str, list[np.ndarray]] = {}
        self._auto_cache: dict[str, list[np.ndarray]] = {}
        self._auto_meta: dict[str, DetectedPerson] = {}
        self._last_register_time: float = 0.0
        self._last_register_embedding: np.ndarray | None = None
        self._load_auto_meta_from_disk()

    def _load_auto_meta_from_disk(self) -> None:
        if not os.path.isdir(self._auto_dir):
            return
        for d in sorted(os.listdir(self._auto_dir)):
            if not PERSON_ID_PATTERN.match(d):
                continue
            person_dir = os.path.join(self._auto_dir, d)
            emb_count = len([f for f in os.listdir(person_dir) if f.endswith(".npy")])
            snap = os.path.join(person_dir, "0.jpg")
            try:
                stat = os.stat(snap)
            except OSError:
                stat = None
            ts = stat.st_mtime if stat else 0.0
            self._auto_meta[d] = DetectedPerson(
                person_id=d,
                snapshot_path=snap if os.path.exists(snap) else "",
                first_seen=ts,
                last_seen=ts,
                sample_count=emb_count,
            )

    @property
    def _auto_dir(self) -> str:
        return os.path.join(DATASET_DIR, AUTO_DIR_NAME)

    def detect_and_recognize(self, frame: np.ndarray) -> FaceResult | None:
        try:
            faces = self._app.get(frame)
        except Exception as e:
            print(f"[Face] inference error: {e}")
            return None

        valid = [f for f in faces if f.det_score >= DETECTION_SCORE_THRESHOLD]
        valid = [f for f in valid if self._bbox_size_ok(f.bbox)]
        if not valid:
            return None

        annotated = frame.copy()
        matches: list[FaceMatch] = []

        for face in valid:
            bbox = tuple(int(v) for v in face.bbox)
            x1, y1, x2, y2 = bbox
            embedding = face.normed_embedding

            category, name, conf = self._identify(embedding, frame, bbox, face.det_score)

            color = self._color_for(category)
            thickness = 2 if category == FaceCategory.KNOWN else 2

            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, thickness)

            label = name
            font = cv2.FONT_HERSHEY_SIMPLEX
            (tw, th), _ = cv2.getTextSize(label, font, 0.6, 1)
            pill_h = th + 12
            pill_y = max(0, y1 - pill_h - 4)

            overlay = annotated.copy()
            cv2.rectangle(overlay, (x1, pill_y), (x1 + tw + 14, pill_y + pill_h), color, -1)
            cv2.addWeighted(overlay, 0.85, annotated, 0.15, 0, annotated)
            cv2.putText(
                annotated, label, (x1 + 7, pill_y + pill_h - 5),
                font, 0.6, (255, 255, 255), 1, cv2.LINE_AA,
            )

            matches.append(FaceMatch(
                name=name, confidence=conf,
                x1=x1, y1=y1, x2=x2, y2=y2,
                category=category,
            ))

        return FaceResult(faces=matches, frame=annotated)

    @staticmethod
    def _bbox_size_ok(bbox) -> bool:
        w = float(bbox[2]) - float(bbox[0])
        h = float(bbox[3]) - float(bbox[1])
        return w >= MIN_FACE_SIZE and h >= MIN_FACE_SIZE

    def _color_for(self, category: FaceCategory) -> tuple[int, int, int]:
        if category == FaceCategory.KNOWN:
            return (0, 220, 120)
        if category == FaceCategory.AUTO:
            return (255, 165, 0)
        return (255, 200, 50)

    def _identify(
        self,
        embedding: np.ndarray,
        frame: np.ndarray,
        bbox: tuple[int, int, int, int],
        det_score: float,
    ) -> tuple[FaceCategory, str, float]:
        name, dist = self._best_match(embedding, self._load_known(), KNOWN_THRESHOLD)
        if name is not None:
            return FaceCategory.KNOWN, name, max(0.0, 1.0 - dist / KNOWN_THRESHOLD)

        name, dist = self._best_match(embedding, self._load_auto(), AUTO_THRESHOLD)
        if name is not None:
            self._touch_auto(name, embedding)
            return FaceCategory.AUTO, name, max(0.0, 1.0 - dist / AUTO_THRESHOLD)

        if not self._quality_ok(frame, bbox, det_score):
            return FaceCategory.NEW, "?", 0.0

        if self._is_recent_duplicate(embedding):
            return FaceCategory.NEW, "?", 0.0

        new_id = self._register_auto(embedding, frame, bbox)
        return FaceCategory.NEW, new_id, 1.0

    def _is_recent_duplicate(self, embedding: np.ndarray) -> bool:
        if self._last_register_embedding is None:
            return False
        elapsed = time.time() - self._last_register_time
        if elapsed > RECENT_REGISTER_COOLDOWN:
            return False
        dist = float(1.0 - np.dot(embedding, self._last_register_embedding))
        return dist < EMBEDDING_DEDUP_THRESHOLD

    @staticmethod
    def _quality_ok(frame: np.ndarray, bbox: tuple[int, int, int, int], det_score: float) -> bool:
        if det_score < DETECTION_SCORE_THRESHOLD:
            return False
        x1, y1, x2, y2 = bbox
        h, w = frame.shape[:2]
        x1c, y1c = max(0, x1), max(0, y1)
        x2c, y2c = min(w, x2), min(h, y2)
        if x2c - x1c < MIN_FACE_SIZE or y2c - y1c < MIN_FACE_SIZE:
            return False
        crop = frame[y1c:y2c, x1c:x2c]
        if crop.size == 0:
            return False
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        blur_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        return blur_var >= BLUR_THRESHOLD

    def _best_match(
        self,
        embedding: np.ndarray,
        candidates: dict[str, list[np.ndarray]],
        threshold: float,
    ) -> tuple[str | None, float]:
        best_name: str | None = None
        best_dist = float("inf")
        for name, embeddings in candidates.items():
            for stored in embeddings:
                dist = float(1.0 - np.dot(embedding, stored))
                if dist < best_dist:
                    best_dist = dist
                    best_name = name
        if best_name is not None and best_dist < threshold:
            return best_name, best_dist
        return None, best_dist

    def _next_person_id(self) -> str:
        existing = []
        for d in os.listdir(self._auto_dir):
            m = PERSON_ID_PATTERN.match(d)
            if m and os.path.isdir(os.path.join(self._auto_dir, d)):
                existing.append(int(m.group(1)))
        n = (max(existing) + 1) if existing else 1
        return f"person_{n:03d}"

    def _register_auto(
        self,
        embedding: np.ndarray,
        frame: np.ndarray,
        bbox: tuple[int, int, int, int],
    ) -> str:
        person_id = self._next_person_id()
        person_dir = os.path.join(self._auto_dir, person_id)
        os.makedirs(person_dir, exist_ok=True)

        x1, y1, x2, y2 = bbox
        h, w = frame.shape[:2]
        x1c, y1c = max(0, x1), max(0, y1)
        x2c, y2c = min(w, x2), min(h, y2)
        crop = frame[y1c:y2c, x1c:x2c]
        snap_path = os.path.join(person_dir, "0.jpg")
        if crop.size > 0:
            cv2.imwrite(snap_path, crop)
        else:
            cv2.imwrite(snap_path, frame)

        emb_path = os.path.join(person_dir, "embedding_0.npy")
        np.save(emb_path, embedding)

        now = time.time()
        self._auto_cache[person_id] = [embedding]
        self._auto_meta[person_id] = DetectedPerson(
            person_id=person_id,
            snapshot_path=snap_path,
            first_seen=now,
            last_seen=now,
            sample_count=1,
        )
        self._last_register_time = now
        self._last_register_embedding = embedding
        print(f"[Face] auto-registered new visitor: {person_id}")
        return person_id

    def _touch_auto(self, person_id: str, embedding: np.ndarray | None = None) -> None:
        if embedding is not None:
            self._maybe_add_embedding(person_id, embedding)
        meta = self._auto_meta.get(person_id)
        if meta is None:
            person_dir = os.path.join(self._auto_dir, person_id)
            emb_count = len([f for f in os.listdir(person_dir) if f.endswith(".npy")]) if os.path.isdir(person_dir) else 0
            meta = DetectedPerson(
                person_id=person_id,
                snapshot_path=os.path.join(person_dir, "0.jpg"),
                first_seen=time.time(),
                last_seen=time.time(),
                sample_count=emb_count,
            )
            self._auto_meta[person_id] = meta
        else:
            meta.last_seen = time.time()
            meta.sample_count += 1

    def _maybe_add_embedding(self, person_id: str, embedding: np.ndarray) -> None:
        person_dir = os.path.join(self._auto_dir, person_id)
        if not os.path.isdir(person_dir):
            return
        existing = sorted(f for f in os.listdir(person_dir) if f.endswith(".npy"))
        if len(existing) >= MAX_EMBEDDINGS_PER_PERSON:
            return
        for f in existing:
            stored = np.load(os.path.join(person_dir, f))
            dist = float(1.0 - np.dot(embedding, stored))
            if dist < EMBEDDING_DEDUP_THRESHOLD:
                return
        idx = len(existing)
        np.save(os.path.join(person_dir, f"embedding_{idx}.npy"), embedding)
        if person_id in self._auto_cache:
            self._auto_cache[person_id].append(embedding)

    def register_face(self, name: str, image: np.ndarray) -> bool:
        try:
            if len(image.shape) == 2:
                image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

            faces = self._app.get(image)
            valid = [f for f in faces if f.det_score >= DETECTION_SCORE_THRESHOLD]
            if not valid:
                print(f"[Face] No face detected in snapshot for '{name}'")
                return False

            face_dir = os.path.join(DATASET_DIR, name)
            os.makedirs(face_dir, exist_ok=True)

            idx = len(os.listdir(face_dir))
            cv2.imwrite(os.path.join(face_dir, f"{idx}.jpg"), image)

            embedding = valid[0].normed_embedding
            emb_path = os.path.join(face_dir, f"embedding_{idx}.npy")
            np.save(emb_path, embedding)

            self._known_cache.pop(name, None)
            return True
        except Exception as e:
            print(f"[Face] register_face error: {e}")
            return False

    def get_registered_names(self) -> list[str]:
        if not os.path.exists(DATASET_DIR):
            return []
        return sorted([
            d for d in os.listdir(DATASET_DIR)
            if d != AUTO_DIR_NAME
            and os.path.isdir(os.path.join(DATASET_DIR, d))
        ])

    def delete_face(self, name: str) -> bool:
        face_dir = os.path.join(DATASET_DIR, name)
        if os.path.exists(face_dir):
            shutil.rmtree(face_dir)
            self._known_cache.pop(name, None)
            return True
        return False

    def get_detected_persons(self) -> list[DetectedPerson]:
        persons = []
        if not os.path.isdir(self._auto_dir):
            return persons
        for d in sorted(os.listdir(self._auto_dir)):
            if not PERSON_ID_PATTERN.match(d):
                continue
            person_dir = os.path.join(self._auto_dir, d)
            embeddings = [
                np.load(os.path.join(person_dir, f))
                for f in sorted(os.listdir(person_dir))
                if f.endswith(".npy")
            ]
            if not embeddings:
                continue
            snap = os.path.join(person_dir, "0.jpg")
            try:
                stat = os.stat(snap)
            except OSError:
                stat = None
            ts = stat.st_mtime if stat else 0.0
            persons.append(DetectedPerson(
                person_id=d,
                snapshot_path=snap if os.path.exists(snap) else "",
                first_seen=ts,
                last_seen=ts,
                sample_count=len(embeddings),
            ))
        return persons

    def delete_detected_person(self, person_id: str) -> bool:
        if not PERSON_ID_PATTERN.match(person_id):
            return False
        person_dir = os.path.join(self._auto_dir, person_id)
        if os.path.isdir(person_dir):
            shutil.rmtree(person_dir)
            self._auto_cache.pop(person_id, None)
            self._auto_meta.pop(person_id, None)
            return True
        return False

    def promote_detected_person(self, person_id: str, real_name: str) -> bool:
        if not PERSON_ID_PATTERN.match(person_id):
            return False
        if not real_name or not real_name.strip():
            return False
        if real_name == AUTO_DIR_NAME:
            return False

        src_dir = os.path.join(self._auto_dir, person_id)
        dst_dir = os.path.join(DATASET_DIR, real_name)
        if not os.path.isdir(src_dir):
            return False
        if os.path.exists(dst_dir):
            return False

        os.makedirs(dst_dir, exist_ok=True)
        for f in os.listdir(src_dir):
            shutil.move(os.path.join(src_dir, f), os.path.join(dst_dir, f))
        shutil.rmtree(src_dir)

        self._auto_cache.pop(person_id, None)
        self._auto_meta.pop(person_id, None)
        self._known_cache.pop(real_name, None)
        return True

    def _load_known(self) -> dict[str, list[np.ndarray]]:
        out: dict[str, list[np.ndarray]] = {}
        for name in self.get_registered_names():
            face_dir = os.path.join(DATASET_DIR, name)
            embeddings = [
                np.load(os.path.join(face_dir, f))
                for f in sorted(os.listdir(face_dir))
                if f.endswith(".npy")
            ]
            if embeddings:
                out[name] = embeddings
        return out

    def _load_auto(self) -> dict[str, list[np.ndarray]]:
        out: dict[str, list[np.ndarray]] = {}
        if not os.path.isdir(self._auto_dir):
            return out
        for d in sorted(os.listdir(self._auto_dir)):
            if not PERSON_ID_PATTERN.match(d):
                continue
            person_dir = os.path.join(self._auto_dir, d)
            embeddings = [
                np.load(os.path.join(person_dir, f))
                for f in sorted(os.listdir(person_dir))
                if f.endswith(".npy")
            ]
            if embeddings:
                out[d] = embeddings
        return out
