import json
import logging
from uuid import UUID

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel
from pytest import LogCaptureFixture

from tests.support import ORIGIN


class InputPayload(BaseModel):
    quantity: int
    password: int


def test_unknown_route_and_wrong_method_share_error_contract(unit_client: TestClient) -> None:
    for method, url, status, code in [
        ("get", "/api/v1/missing", 404, "NOT_FOUND"),
        ("post", "/api/v1/health/live", 405, "METHOD_NOT_ALLOWED"),
    ]:
        response = getattr(unit_client, method)(url, headers={"Origin": ORIGIN})
        assert response.status_code == status
        assert response.json()["error"]["code"] == code
        assert response.json()["error"]["details"] == []
        assert response.json()["error"]["request_id"] == response.headers["x-request-id"]


def test_validation_strips_sensitive_inputs(application: FastAPI, unit_client: TestClient) -> None:
    @application.post("/test-validation/{identifier}")
    async def validate(identifier: int, payload: InputPayload, limit: int) -> None:
        return None

    response = unit_client.post(
        "/test-validation/not-an-id?limit=wrong",
        headers={"Origin": ORIGIN},
        json={"quantity": "invalid", "password": "my-secret-password"},
    )
    assert response.status_code == 422
    body = response.json()["error"]
    assert body["code"] == "VALIDATION_ERROR"
    assert {item["field"] for item in body["details"]} == {
        "path.identifier",
        "query.limit",
        "quantity",
        "password",
    }
    assert "my-secret-password" not in response.text
    assert "input" not in response.text


def test_uncaught_exception_does_not_leak_and_next_request_works(
    application: FastAPI, unit_client: TestClient, caplog: LogCaptureFixture
) -> None:
    @application.get("/test-failure")
    async def failure() -> None:
        raise RuntimeError("postgresql://owner:super-secret@db/private")

    with caplog.at_level(logging.INFO, logger="app.requests"):
        response = unit_client.get("/test-failure")
        next_response = unit_client.get("/api/v1/health/live")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert response.json()["error"]["request_id"] == response.headers["x-request-id"]
    assert "super-secret" not in response.text + caplog.text
    assert next_response.status_code == 200


def test_http_exception_detail_is_not_exposed(
    application: FastAPI, unit_client: TestClient
) -> None:
    @application.get("/test-http-error")
    async def failure() -> None:
        raise HTTPException(503, detail="private database hostname and password")

    response = unit_client.get("/test-http-error")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "TEMPORARILY_UNAVAILABLE"
    assert "password" not in response.text


def test_request_id_is_validated_and_metadata_logs_omit_query_and_cookies(
    unit_client: TestClient, caplog: LogCaptureFixture
) -> None:
    request_id = "ec9f9cdb-81ac-4e39-a9d3-78e69a1d27ae"
    with caplog.at_level(logging.INFO, logger="app.requests"):
        response = unit_client.get(
            "/api/v1/health/live?token=secret-query",
            headers={"X-Request-ID": request_id, "Cookie": "itt_session=secret-cookie"},
        )
        invalid = unit_client.get(
            "/unknown/private-path", headers={"X-Request-ID": "bad secret-id"}
        )
    assert response.headers["x-request-id"] == request_id
    UUID(invalid.headers["x-request-id"])
    assert invalid.headers["x-request-id"] != "bad secret-id"
    records = [
        json.loads(record.message) for record in caplog.records if record.name == "app.requests"
    ]
    assert records[0]["route"].endswith("/health/live")
    assert records[1]["route"] == "<unmatched>"
    assert {"request_id", "route", "status", "method", "duration_ms"} == records[0].keys()
    assert all(
        secret not in caplog.text for secret in ["secret-query", "secret-cookie", "secret-id"]
    )
