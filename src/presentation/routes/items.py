import asyncio
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import Response

from src.usecases.item_tracking import ItemTrackingUseCase

logger = logging.getLogger(__name__)

router = APIRouter()

_item_use_case: ItemTrackingUseCase | None = None


def init_items(items: ItemTrackingUseCase) -> None:
    global _item_use_case
    _item_use_case = items


def get_item_use_case() -> ItemTrackingUseCase | None:
    return _item_use_case


@router.get("/api/items")
async def list_items() -> dict[str, Any]:
    if _item_use_case is None:
        return {"enabled": False, "items": [], "stats": {}}
    return _item_use_case.get_items_summary()


@router.get("/api/items/events")
async def list_item_events(limit: int = 50, type: str | None = None) -> dict[str, Any]:
    if _item_use_case is None:
        return {"enabled": False, "events": []}
    events = _item_use_case.history
    if type:
        events = [e for e in events if e.type.value == type]
    return {
        "enabled": _item_use_case.is_enabled,
        "events": [e.to_dict() for e in events[:limit]],
        "stats": {
            "thefts": _item_use_case.stats.thefts,
            "abandons": _item_use_case.stats.abandons,
        },
    }


@router.get("/api/items/stats")
async def get_item_stats() -> dict[str, Any]:
    if _item_use_case is None:
        return {"enabled": False}
    s = _item_use_case.stats
    return {
        "enabled": _item_use_case.is_enabled,
        "total_items": s.total_items,
        "by_state": s.by_state,
        "by_type": s.by_type,
        "owned_items": s.owned_items,
        "thefts": s.thefts,
        "abandons": s.abandons,
    }


@router.get("/api/items/{event_id}/snapshot")
async def get_item_snapshot(event_id: str):
    if _item_use_case is None:
        return Response(status_code=404)
    data = _item_use_case.get_snapshot_bytes(event_id)
    if data is None:
        return Response(status_code=404)
    return Response(content=data, media_type="image/jpeg")


@router.delete("/api/items")
async def clear_items() -> dict[str, str]:
    if _item_use_case is not None:
        _item_use_case.clear_history()
    return {"status": "cleared"}


@router.websocket("/ws/items")
async def ws_items(ws: WebSocket) -> None:
    if _item_use_case is None:
        await ws.close(code=1011)
        return
    await _item_use_case.ws_manager.connect(ws)
    try:
        await ws.send_json({"type": "hello", "clients": _item_use_case.ws_manager.client_count})
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
        _item_use_case.ws_manager.disconnect(ws)
