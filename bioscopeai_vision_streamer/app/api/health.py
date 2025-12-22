"""Health check endpoints."""

from fastapi import APIRouter


health_router = APIRouter()


@health_router.get("/", tags=["Health"])
async def health_check() -> dict[str, str]:
    """Health check endpoint to verify that the API is running."""
    return {"status": "ok"}
