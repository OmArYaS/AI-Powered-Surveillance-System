from dataclasses import dataclass
from enum import Enum


class CameraStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    CONNECTING = "connecting"


@dataclass(frozen=True)
class CameraConfig:
    host: str
    port: int
    username: str
    password: str
    channel: int = 101

    @property
    def rtsp_url(self) -> str:
        return (
            f"rtsp://{self.username}:{self.password}"
            f"@{self.host}:{self.port}/Streaming/Channels/{self.channel}"
        )

    @property
    def display_address(self) -> str:
        return f"{self.host}:{self.port}"


@dataclass
class CameraInfo:
    name: str
    location: str
    config: CameraConfig
    status: CameraStatus = CameraStatus.OFFLINE
