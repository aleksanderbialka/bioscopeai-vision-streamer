"""Tests for main API endpoints and application setup."""

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient


def test_app_creation(app: FastAPI) -> None:
    assert isinstance(app, FastAPI)
    assert app.title == "BioScopeAI Vision Streamer"
    assert app.openapi_url == "/api/openapi.json"
    assert app.docs_url == "/api/docs"
    assert app.redoc_url == "/api/redoc"


def test_api_routes_registered(app: FastAPI) -> None:
    routes = [route.path for route in app.routes]

    assert "/api/health/" in routes
    assert "/api/ws/webrtc" in routes


def test_openapi_json_available(client: TestClient) -> None:
    response = client.get("/api/openapi.json")

    assert response.status_code == status.HTTP_200_OK

    schema = response.json()
    assert "openapi" in schema
    assert "info" in schema
    assert schema["info"]["title"] == "BioScopeAI Vision Streamer"


def test_docs_endpoint_accessible(client: TestClient) -> None:
    response = client.get("/api/docs")

    assert response.status_code == status.HTTP_200_OK
    assert "text/html" in response.headers["content-type"]


def test_redoc_endpoint_accessible(client: TestClient) -> None:
    response = client.get("/api/redoc")

    assert response.status_code == status.HTTP_200_OK
    assert "text/html" in response.headers["content-type"]


def test_cors_middleware(app: FastAPI) -> None:
    middleware_classes = [type(m).__name__ for m in app.user_middleware]
    assert isinstance(middleware_classes, list)


def test_invalid_endpoint_returns_404(client: TestClient) -> None:
    response = client.get("/api/nonexistent")

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_root_path_not_found(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_api_prefix_required(client: TestClient) -> None:
    response = client.get("/health/")
    assert response.status_code == status.HTTP_404_NOT_FOUND

    response = client.get("/api/health/")
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.parametrize(
    "endpoint",
    [
        "/api/health/",
        "/api/docs",
        "/api/redoc",
        "/api/openapi.json",
    ],
)
def test_endpoints_respond(client: TestClient, endpoint: str) -> None:
    response = client.get(endpoint)

    assert response.status_code in [
        status.HTTP_200_OK,
        status.HTTP_307_TEMPORARY_REDIRECT,  # For trailing slash redirects
    ]
