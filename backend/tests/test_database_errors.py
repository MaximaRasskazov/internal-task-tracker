"""Database failures keep the common contract without disclosing SQL or credentials."""

import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.exc import TimeoutError as PoolTimeoutError


class DriverFailure(Exception):
    def __init__(self, state: str) -> None:
        self.sqlstate = state
        super().__init__("private-host user-password secret-column")


@pytest.mark.parametrize("state", ["08006", "53300", "40001", "40P01", "55P03", "57014", "57P01"])
def test_transient_database_errors_return_503_without_leaking(
    application: FastAPI,
    unit_client: TestClient,
    caplog: pytest.LogCaptureFixture,
    state: str,
) -> None:
    @application.get("/test-db-failure")
    async def failure() -> None:
        raise DBAPIError(
            "SELECT secret-column", {"password": "user-password"}, DriverFailure(state)
        )

    with caplog.at_level(logging.INFO, logger="app.requests"):
        response = unit_client.get("/test-db-failure")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "TEMPORARILY_UNAVAILABLE"
    assert response.json()["error"]["request_id"] == response.headers["x-request-id"]
    assert response.json()["error"]["details"] == []
    for secret in ["private-host", "user-password", "secret-column", "SELECT"]:
        assert secret not in response.text + caplog.text


@pytest.mark.parametrize(
    "error",
    [ConnectionRefusedError("private-host"), TimeoutError("private-host"), PoolTimeoutError("dsn")],
)
def test_connection_and_pool_failures_are_temporary(
    application: FastAPI, unit_client: TestClient, error: Exception
) -> None:
    @application.get("/test-connection-failure")
    async def failure() -> None:
        raise error

    response = unit_client.get("/test-connection-failure")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "TEMPORARILY_UNAVAILABLE"
    assert "private-host" not in response.text
    assert unit_client.get("/api/v1/health/live").status_code == 200


def test_unexpected_integrity_failure_is_sanitized_internal_error(
    application: FastAPI, unit_client: TestClient
) -> None:
    @application.get("/test-integrity-failure")
    async def failure() -> None:
        raise IntegrityError("INSERT secret-column", {}, DriverFailure("23514"))

    response = unit_client.get("/test-integrity-failure")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "secret-column" not in response.text


@pytest.mark.parametrize("state", ["28P01", "53300", "57P03"])
def test_raw_driver_connect_failure_is_temporary(
    application: FastAPI, unit_client: TestClient, state: str
) -> None:
    @application.get("/test-raw-driver-failure")
    async def failure() -> None:
        raise DriverFailure(state)

    response = unit_client.get("/test-raw-driver-failure")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "TEMPORARILY_UNAVAILABLE"
    assert "private-host" not in response.text
