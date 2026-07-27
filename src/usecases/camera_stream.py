from src.domain.entities.camera import CameraConfig, CameraInfo, CameraStatus
from src.domain.interfaces.stream_repository import StreamRepository


class CameraStreamUseCase:
    def __init__(
        self,
        stream_repository: StreamRepository,
        camera_info: CameraInfo,
    ):
        self._stream = stream_repository
        self._camera = camera_info

    def start_stream(self) -> None:
        self._camera.status = CameraStatus.CONNECTING
        self._stream.start()
        self._camera.status = CameraStatus.ONLINE

    def stop_stream(self) -> None:
        self._stream.stop()
        self._camera.status = CameraStatus.OFFLINE

    def get_frame(self):
        return self._stream.get_frame()

    @property
    def is_connected(self) -> bool:
        return self._stream.is_connected

    @property
    def camera(self) -> CameraInfo:
        return self._camera
