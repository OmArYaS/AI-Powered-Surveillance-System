import asyncio
import logging

import uvicorn

from src.adapters.insightface.face_repository import InsightFaceRepository
from src.adapters.rtsp.opencv_stream_repository import OpenCVStreamRepository
from src.adapters.storage.json_item_store import JsonItemStore
from src.adapters.threat.rule_engine import RuleEngine
from src.adapters.torch.r3d_action_classifier import R3DActionClassifier
from src.adapters.tracking.io_tracker import IoUTracker
from src.adapters.tracking.ownership_engine import OwnershipEngine
from src.adapters.yolo.detection_repository import YOLODetectionRepository
from src.adapters.yolo.pose_estimation_repository import PoseEstimationRepository
from src.adapters.yolo.weapon_detection_repository import WeaponDetectionRepository
from src.config.settings import settings
from src.domain.entities.camera import CameraConfig, CameraInfo
from src.presentation.api.app import create_app
from src.presentation.realtime.ws_manager import WebSocketManager
from src.presentation.routes.camera import init_stream
from src.presentation.routes.face import init_face
from src.presentation.routes.items import init_items
from src.presentation.routes.threat import init_threat
from src.usecases.camera_stream import CameraStreamUseCase
from src.usecases.detection import DetectionUseCase
from src.usecases.face import FaceUseCase
from src.usecases.item_tracking import ItemTrackingUseCase
from src.usecases.threat import ThreatUseCase


class _CancelledErrorFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if record.exc_info:
            exc_type = record.exc_info[0]
            if exc_type is asyncio.CancelledError:
                return False
        return True


for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
    logging.getLogger(name).addFilter(_CancelledErrorFilter())


def create_camera_stream() -> CameraStreamUseCase:
    config = CameraConfig(
        host=settings.rtsp_host,
        port=settings.rtsp_port,
        username=settings.rtsp_username,
        password=settings.rtsp_password,
        channel=settings.rtsp_channel,
    )
    info = CameraInfo(name="Camera 01", location="Main Entrance", config=config)
    repo = OpenCVStreamRepository(rtsp_url=config.rtsp_url)
    return CameraStreamUseCase(stream_repository=repo, camera_info=info)


def main() -> None:
    camera_stream = create_camera_stream()
    camera_stream.start_stream()

    detection_repo = YOLODetectionRepository(model_path="yolo11s.pt", imgsz=1280)
    detection = DetectionUseCase(detection_repo=detection_repo)

    face_repo = InsightFaceRepository()
    face = FaceUseCase(face_repo=face_repo)

    ws_manager = WebSocketManager()
    weapon_repo = WeaponDetectionRepository(model_path="gun.pt")
    pose_repo = PoseEstimationRepository(model_path="yolov8n-pose.pt")
    action_repo = R3DActionClassifier()

    threat = ThreatUseCase(
        weapon_repo=weapon_repo,
        pose_repo=pose_repo,
        action_repo=action_repo,
        ws_manager=ws_manager,
    )

    item_repo = JsonItemStore()
    item_tracker = IoUTracker(
        iou_threshold=settings.item_iou_threshold,
        max_disappear_frames=settings.item_max_disappear_frames,
    )
    item_engine = OwnershipEngine(
        proximity_px=settings.item_proximity_px,
        hold_duration_s=settings.item_hold_duration_s,
        disappear_theft_s=settings.item_disappear_theft_s,
        abandon_s=settings.item_abandon_s,
    )
    items = ItemTrackingUseCase(
        tracker=item_tracker,
        engine=item_engine,
        repo=item_repo,
        ws_manager=ws_manager,
    )

    init_stream(camera_stream, detection, face, threat, items)
    init_face(face)
    init_threat(threat)
    init_items(items)

    app = create_app()
    uvicorn.run(app, host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
