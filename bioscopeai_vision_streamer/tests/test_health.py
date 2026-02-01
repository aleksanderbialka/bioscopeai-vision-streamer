"""Tests for health check endpoint."""

from fastapi import status
from fastapi.testclient import TestClient


def test_health_check_returns_ok(client: TestClient) -> None:
    response = client.get("/api/health/")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}


def test_health_check_response_format(client: TestClient) -> None:
    response = client.get("/api/health/")

    data = response.json()
    assert isinstance(data, dict)
    assert "status" in data
    assert isinstance(data["status"], str)


def test_health_check_multiple_calls(client: TestClient) -> None:
    responses = [client.get("/api/health/") for _ in range(5)]

    for response in responses:
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "ok"}


def test_health_check_methods(client: TestClient) -> None:
    response = client.get("/api/health/")
    assert response.status_code == status.HTTP_200_OK

    response = client.post("/api/health/")
    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    response = client.put("/api/health/")
    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    response = client.delete("/api/health/")
    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


def test_health_check_content_type(client: TestClient) -> None:
    response = client.get("/api/health/")

    assert "application/json" in response.headers["content-type"]
