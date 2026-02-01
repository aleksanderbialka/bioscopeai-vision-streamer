"""Pytest configuration and shared fixtures."""

import os
from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient

from bioscopeai_vision_streamer.app.main import create_app


def pytest_configure() -> None:
    """Setup test environment before Pydantic Settings initialization."""
    test_config_path = Path(__file__).parent / "test-config.yaml"
    os.environ["CONFIG_FILE"] = str(test_config_path)
    print(
        f"\n[pytest] CONFIG_FILE: {test_config_path} (exists: {test_config_path.exists()})"
    )


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    """Configure async backend for pytest-asyncio."""
    return "asyncio"


@pytest.fixture
def mock_lifespan() -> Any:
    """Mock lifespan context manager for testing."""
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
        yield

    return lifespan


@pytest.fixture
def app(mock_lifespan: Any) -> FastAPI:
    """Create FastAPI test application."""
    return create_app(lifespan=mock_lifespan)


@pytest.fixture
def client(app: FastAPI) -> Generator[TestClient]:
    """Create test client for synchronous requests."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
async def async_client(app: FastAPI) -> AsyncGenerator[AsyncClient]:
    """Create async test client for async requests."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_websocket() -> MagicMock:
    """Create mock WebSocket for testing."""
    ws = MagicMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    ws.send_text = AsyncMock()
    ws.receive_json = AsyncMock()
    ws.receive_text = AsyncMock()
    ws.close = AsyncMock()
    return ws
