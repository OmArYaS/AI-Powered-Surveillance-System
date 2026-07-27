import base64
import os
import time

import cv2
import numpy as np
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from src.presentation.routes.camera import get_stream_use_case
from src.usecases.face import FaceUseCase

router = APIRouter(prefix="/api/faces", tags=["faces"])

_face_use_case: FaceUseCase | None = None


def init_face(use_case: FaceUseCase) -> None:
    global _face_use_case
    _face_use_case = use_case


def get_face_use_case() -> FaceUseCase | None:
    return _face_use_case


class RegisterRequest(BaseModel):
    name: str
    image: str


class PromoteRequest(BaseModel):
    name: str


@router.get("/snapshot")
async def snapshot():
    stream = get_stream_use_case()
    if stream is None:
        raise HTTPException(500, "Stream not ready")
    frame = stream.get_frame()
    if frame is None:
        raise HTTPException(503, "No frame available")
    _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
    return Response(content=buf.tobytes(), media_type="image/jpeg")


@router.get("")
async def list_faces():
    if _face_use_case is None:
        return {"faces": [], "enabled": False}
    return {
        "faces": _face_use_case.get_registered(),
        "enabled": _face_use_case.is_enabled,
    }


@router.post("/register")
async def register_face(req: RegisterRequest):
    if _face_use_case is None:
        raise HTTPException(500, "Face system not initialized")

    try:
        img_bytes = base64.b64decode(req.image)
        arr = np.frombuffer(img_bytes, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if frame is None:
            raise HTTPException(400, "Invalid image")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(400, "Invalid image data")

    ok = _face_use_case.register(req.name, frame)
    if not ok:
        raise HTTPException(400, "No face detected in image")

    return {"success": True, "name": req.name}


@router.delete("/{name}")
async def delete_face(name: str):
    if _face_use_case is None:
        raise HTTPException(500, "Face system not initialized")

    ok = _face_use_case.delete(name)
    if not ok:
        raise HTTPException(404, "Face not found")

    return {"success": True}


@router.get("/auto")
async def list_detected():
    if _face_use_case is None:
        return {"persons": []}
    persons = _face_use_case.get_detected_persons()
    return {
        "persons": [
            {
                "person_id": p.person_id,
                "snapshot_url": f"/api/faces/auto/{p.person_id}/snapshot",
                "first_seen": p.first_seen,
                "last_seen": p.last_seen,
                "sample_count": p.sample_count,
            }
            for p in persons
        ]
    }


@router.get("/auto/{person_id}/snapshot")
async def get_auto_snapshot(person_id: str):
    if _face_use_case is None:
        raise HTTPException(500, "Face system not initialized")
    for p in _face_use_case.get_detected_persons():
        if p.person_id == person_id and p.snapshot_path and os.path.exists(p.snapshot_path):
            return FileResponse(p.snapshot_path, media_type="image/jpeg")
    raise HTTPException(404, "Snapshot not found")


@router.delete("/auto/{person_id}")
async def delete_detected(person_id: str):
    if _face_use_case is None:
        raise HTTPException(500, "Face system not initialized")
    ok = _face_use_case.delete_detected_person(person_id)
    if not ok:
        raise HTTPException(404, "Person not found")
    return {"success": True}


@router.post("/auto/{person_id}/promote")
async def promote_detected(person_id: str, req: PromoteRequest):
    if _face_use_case is None:
        raise HTTPException(500, "Face system not initialized")
    name = (req.name or "").strip()
    if not name:
        raise HTTPException(400, "Name is required")
    if name in _face_use_case.get_registered():
        raise HTTPException(409, "Name already registered")
    ok = _face_use_case.promote_detected_person(person_id, name)
    if not ok:
        raise HTTPException(400, "Could not promote person")
    return {"success": True, "name": name}


@router.get("/stats")
async def face_stats():
    if _face_use_case is None:
        return {"known": [], "auto": [], "new": [], "total_visitors": 0}
    s = _face_use_case.stats
    return {
        "known": s.known_faces,
        "auto": s.auto_faces,
        "new": s.new_visitors,
        "total_visitors": s.total_unique_visitors,
    }
