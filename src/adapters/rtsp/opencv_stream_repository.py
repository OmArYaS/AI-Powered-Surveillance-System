import threading
import time

import cv2
import numpy as np

from src.domain.interfaces.stream_repository import StreamRepository


class OpenCVStreamRepository(StreamRepository):
    def __init__(self, rtsp_url: str):
        self._url = rtsp_url
        self._frame: np.ndarray | None = None
        self._lock = threading.Lock()
        self._connected = False
        self._stop = False
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop = False
        self._thread = threading.Thread(target=self._reader, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop = True

    def get_frame(self) -> np.ndarray | None:
        with self._lock:
            return self._frame.copy() if self._frame is not None else None

    @property
    def is_connected(self) -> bool:
        return self._connected

    def _reader(self) -> None:
        while not self._stop:
            cap = cv2.VideoCapture(self._url, cv2.CAP_FFMPEG)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self._connected = True

            while not self._stop:
                ret, frame = cap.read()
                if not ret:
                    break
                with self._lock:
                    self._frame = frame

            cap.release()
            self._connected = False
            if not self._stop:
                time.sleep(1)
