from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Smart Surveillance System"
    host: str = "0.0.0.0"
    port: int = 8000

    rtsp_host: str = "192.168.1.7"
    rtsp_port: int = 554
    rtsp_username: str = "admin"
    rtsp_password: str = "Omar@2026"
    rtsp_channel: int = 101

    jpeg_quality: int = 85

    item_proximity_px: int = 100
    item_hold_duration_s: float = 1.5
    item_disappear_theft_s: float = 3.0
    item_abandon_s: float = 30.0
    item_iou_threshold: float = 0.30
    item_max_disappear_frames: int = 30

    model_config = {"env_prefix": "SS_"}


settings = Settings()
