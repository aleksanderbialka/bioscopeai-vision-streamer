from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger

from bioscopeai_vision_streamer.app.webrtc.signaling import signaling_server


ws_router = APIRouter()


@ws_router.websocket("/webrtc")
async def webrtc_ws(websocket: WebSocket) -> None:
    """WebSocket endpoint for WebRTC signaling."""
    try:
        await signaling_server.handle_websocket(websocket)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected in /ws/webrtc")
    except OSError as exc:
        logger.exception("Network error in /ws/webrtc handler: %s", exc)
        try:
            await websocket.close()
        except OSError:
            logger.debug("WebSocket already closed")
