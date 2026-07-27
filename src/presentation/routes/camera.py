import threading
import time

import cv2
from fastapi import APIRouter
from starlette.responses import StreamingResponse

from src.adapters.yolo.weapon_detection_repository import annotate_weapon
from src.domain.entities.item import BBox
from src.presentation.routes.settings import get_store
from src.usecases.camera_stream import CameraStreamUseCase
from src.usecases.detection import DetectionUseCase
from src.usecases.face import FaceUseCase
from src.usecases.item_tracking import ItemTrackingUseCase
from src.usecases.threat import ThreatUseCase

router = APIRouter()

_stream_use_case: CameraStreamUseCase | None = None
_detection_use_case: DetectionUseCase | None = None
_face_use_case: FaceUseCase | None = None
_threat_use_case: ThreatUseCase | None = None
_item_use_case: ItemTrackingUseCase | None = None
_shutdown_event = threading.Event()


def init_stream(
    stream: CameraStreamUseCase,
    detection: DetectionUseCase,
    face: FaceUseCase,
    threat: ThreatUseCase | None = None,
    items: ItemTrackingUseCase | None = None,
) -> None:
    global _stream_use_case, _detection_use_case, _face_use_case, _threat_use_case, _item_use_case
    _stream_use_case = stream
    _detection_use_case = detection
    _face_use_case = face
    _threat_use_case = threat
    _item_use_case = items
    _shutdown_event.clear()


def get_stream_use_case() -> CameraStreamUseCase | None:
    return _stream_use_case


def shutdown_stream() -> None:
    _shutdown_event.set()
    if _stream_use_case is not None:
        try:
            _stream_use_case.stop_stream()
        except Exception:
            pass


def generate_mjpeg():
    while not _shutdown_event.is_set():
        if _stream_use_case is None:
            break
        frame = _stream_use_case.get_frame()
        if frame is None:
            if _shutdown_event.wait(0.01):
                break
            continue

        if _detection_use_case and _detection_use_case.is_enabled:
            result = _detection_use_case.detect(frame)
            if result is not None:
                frame = result.frame
                if _threat_use_case is not None and _threat_use_case.is_enabled:
                    _threat_use_case.evaluate(frame, result.detections)
                    if _threat_use_case._weapon_repo is not None:
                        weapons = _threat_use_case._weapon_repo.detect(frame)
                        if weapons:
                            frame = annotate_weapon(frame, weapons)

        if _face_use_case and _face_use_case.is_enabled:
            face_result = _face_use_case.detect(frame)
            if face_result is not None:
                frame = face_result.frame

        if _item_use_case is not None and _item_use_case.is_enabled and _detection_use_case is not None:
            face_persons = None
            if _face_use_case is not None and _face_use_case.last_result is not None:
                face_persons = [
                    (f.name, BBox(f.x1, f.y1, f.x2, f.y2))
                    for f in _face_use_case.last_result.faces
                ]
            detection_result = _detection_use_case.stats
            if _detection_use_case._repo is not None:
                last_detection = getattr(_detection_use_case, "_last_result", None)
                if last_detection is not None:
                    _item_use_case.process_frame(frame, last_detection.detections, face_persons)

        quality = get_store()["jpeg_quality"]
        _, buffer = cv2.imencode(
            ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality]
        )
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n"
            + buffer.tobytes()
            + b"\r\n"
        )


@router.get("/stream")
async def stream():
    return StreamingResponse(
        generate_mjpeg(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@router.get("/api/detections")
async def get_detections():
    if _detection_use_case is None:
        return {"enabled": False, "persons": 0, "phones": 0, "bags": 0, "threats": 0}
    s = _detection_use_case.stats
    return {
        "enabled": _detection_use_case.is_enabled,
        "persons": s.persons,
        "phones": s.phones,
        "bags": s.bags,
        "threats": s.threats,
    }
