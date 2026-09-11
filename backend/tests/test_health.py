from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import health


def test_live_remains_available_when_database_is_unconfigured(unit_client: TestClient) -> None:
    response = unit_client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    UUID(response.headers["x-request-id"])


def test_readiness_fails_without_database(unit_client: TestClient) -> None:
    response = unit_client.get("/api/v1/health/ready")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "TEMPORARILY_UNAVAILABLE"
    assert response.json()["error"]["request_id"] == response.headers["x-request-id"]
    assert response.json()["error"]["details"] == []
    assert "configured" not in response.text


@pytest.mark.parametrize(
    "failure", [ConnectionError("password=secret"), TimeoutError("dsn=secret")]
)
def test_readiness_sanitizes_dependency_failures(
    unit_client: TestClient, application: FastAPI, failure: Exception
) -> None:
    async def broken_check() -> None:
        raise failure

    application.dependency_overrides[health.get_readiness_checker] = lambda: broken_check
    response = unit_client.get("/api/v1/health/ready")
    assert response.status_code == 503
    assert "secret" not in response.text


@pytest.mark.parametrize(
    ("current_heads", "expected_status"),
    [({"revision_a"}, 200), (set(), 503), ({"old_revision"}, 503), ({"a", "b"}, 503)],
)
def test_readiness_requires_actual_code_heads(
    unit_client: TestClient,
    application: FastAPI,
    monkeypatch: pytest.MonkeyPatch,
    current_heads: set[str],
    expected_status: int,
) -> None:
    connection = AsyncMock()
    connection.run_sync.return_value = current_heads
    manager = MagicMock()
    manager.__aenter__ = AsyncMock(return_value=connection)
    manager.__aexit__ = AsyncMock(return_value=False)
    engine = MagicMock()
    engine.connect.return_value = manager
    application.state.database = SimpleNamespace(engine=engine, dispose=AsyncMock())
    monkeypatch.setattr(health, "migration_heads", lambda: {"revision_a"})
    response = unit_client.get("/api/v1/health/ready")
    assert response.status_code == expected_status
    connection.execute.assert_awaited_once()
    connection.run_sync.assert_awaited_once()
    if expected_status == 200:
        assert response.json() == {"status": "ready"}


def test_code_has_a_nonempty_migration_chain() -> None:
    assert health.migration_heads()
