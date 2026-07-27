from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsResponse(BaseModel):
    rtsp_host: str
    rtsp_port: int
    rtsp_username: str
    rtsp_password: str
    rtsp_channel: int
    jpeg_quality: int
    motion_detection: bool
    auto_recording: bool
    notifications: bool
    night_vision: bool


class SettingsUpdate(BaseModel):
    rtsp_host: str | None = None
    rtsp_port: int | None = None
    rtsp_username: str | None = None
    rtsp_password: str | None = None
    rtsp_channel: int | None = None
    jpeg_quality: int | None = None
    motion_detection: bool | None = None
    auto_recording: bool | None = None
    notifications: bool | None = None
    night_vision: bool | None = None


_store: dict = {
    "rtsp_host": "192.168.1.7",
    "rtsp_port": 554,
    "rtsp_username": "admin",
    "rtsp_password": "Omar@2026",
    "rtsp_channel": 101,
    "jpeg_quality": 85,
    "motion_detection": True,
    "auto_recording": False,
    "notifications": True,
    "night_vision": False,
}


def get_store() -> dict:
    return _store


@router.get("", response_model=SettingsResponse)
async def get_settings():
    return SettingsResponse(**_store)


@router.put("", response_model=SettingsResponse)
async def update_settings(payload: SettingsUpdate):
    updates = payload.model_dump(exclude_unset=True)
    _store.update(updates)
    return SettingsResponse(**_store)
