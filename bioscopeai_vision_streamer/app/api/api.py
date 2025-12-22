from fastapi import APIRouter

from .health import health_router
from .routers import ws_router


api_router = APIRouter()


api_router.include_router(health_router, prefix="/health", tags=["Health"])
api_router.include_router(ws_router, prefix="/ws", tags=["WebSocket"])
