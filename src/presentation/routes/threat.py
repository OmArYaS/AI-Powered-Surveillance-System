import asyncio
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.usecases.threat import ThreatUseCase

logger = logging.getLogger(__name__)

router = APIRouter()

_threat_use_case: ThreatUseCase | None = None


def init_threat(threat: ThreatUseCase) -> None:
    global _threat_use_case
    _threat_use_case = threat


def get_threat_use_case() -> ThreatUseCase | None:
    return _threat_use_case


@router.get("/api/threats")
async def list_threats(limit: int = 50, level: str | None = None) -> dict[str, Any]:
    if _threat_use_case is None:
        return {"enabled": False, "events": [], "stats": {}, "signals": {}}
    history = _threat_use_case.history
    if level:
        history = [e for e in history if e.level.value == level]
    events = [e.to_dict() for e in history[:limit]]
    stats = _threat_use_case.stats
    return {
        "enabled": _threat_use_case.is_enabled,
        "events": events,
        "stats": {
            "total_alerts": stats.total_alerts,
            "by_level": stats.by_level,
            "last_alert_time": stats.last_alert_time,
            "last_level": stats.last_level.value if stats.last_level else None,
            "active_threats": stats.active_threats,
        },
        "signals": _threat_use_case.signals_snapshot(),
    }


@router.get("/api/threats/{event_id}/snapshot")
async def get_threat_snapshot(event_id: str):
    from fastapi.responses import Response
    if _threat_use_case is None:
        return Response(status_code=404)
    data = _threat_use_case.get_snapshot_bytes(event_id)
    if data is None:
        return Response(status_code=404)
    return Response(content=data, media_type="image/jpeg")


@router.delete("/api/threats")
async def clear_threats() -> dict[str, str]:
    if _threat_use_case is not None:
        _threat_use_case.clear_history()
    return {"status": "cleared"}


@router.websocket("/ws/threats")
async def ws_threats(ws: WebSocket) -> None:
    if _threat_use_case is None:
        await ws.close(code=1011)
        return
    await _threat_use_case.ws_manager.connect(ws)
    try:
        await ws.send_json({"type": "hello", "clients": _threat_use_case.ws_manager.client_count})
        while True:
            try:
                msg = await asyncio.wait_for(ws.receive_text(), timeout=30.0)
                if msg == "ping":
                    await ws.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                await ws.send_json({"type": "ping"})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning("WebSocket error: %s", e)
    finally:
        _threat_use_case.ws_manager.disconnect(ws)
