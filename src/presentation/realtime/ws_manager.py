import asyncio
import json
import logging
import threading
from collections import deque
from time import time
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._lock = threading.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        with self._lock:
            self._clients.add(ws)
        logger.info("WebSocket client connected (total=%d)", len(self._clients))

    def disconnect(self, ws: WebSocket) -> None:
        with self._lock:
            self._clients.discard(ws)
        logger.info("WebSocket client disconnected (total=%d)", len(self._clients))

    @property
    def client_count(self) -> int:
        with self._lock:
            return len(self._clients)

    async def broadcast(self, payload: dict[str, Any]) -> None:
        if not self._clients:
            return
        message = json.dumps(payload, default=str)
        dead: list[WebSocket] = []
        with self._lock:
            clients = list(self._clients)
        for ws in clients:
            try:
                await ws.send_text(message)
            except Exception as e:
                logger.warning("WebSocket send failed: %s", e)
                dead.append(ws)
        if dead:
            with self._lock:
                for ws in dead:
                    self._clients.discard(ws)
