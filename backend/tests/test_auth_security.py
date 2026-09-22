from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import httpx
import jwt
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import auth
from app.api.auth import Credentials, LoginLimiter, RegisterRequest
from app.api.dependencies import WriteGuardMiddleware
from app.core.config import Settings
from app.core.errors import AppError
from app.core.middleware import RequestContextMiddleware
from app.core.security import (
    authenticate_token,
    csrf_digest,
    encode_session_token,
    hash_password,
    verify_password,
)

ORIGIN = "http://localhost:5173"
SECRET = "unit-test-session-secret-with-at-least-64-characters-for-HMAC-tests-only"
CSRF_TOKEN = "session-csrf-secret-at-least-32-characters"


@pytest.fixture
def security_settings() -> Settings:
    return Settings(_env_file=None, app_env="test", jwt_secret=SECRET)


@pytest.fixture
def write_client() -> Iterator[TestClient]:
    application = FastAPI()

    @application.api_route(
        "/write", methods=["GET", "HEAD", "OPTIONS", "POST", "PUT", "PATCH", "DELETE"]
    )
    async def endpoint(request: Request) -> dict[str, str]:
        return {"method": request.method}

    guarded = RequestContextMiddleware(WriteGuardMiddleware(application, allowed_origins=[ORIGIN]))
    with TestClient(guarded) as client:
        yield client


def test_password_hash_is_salted_and_verification_rejects_another_password() -> None:
    password = "Уникальный пароль! 128"
    first = hash_password(password)
    second = hash_password(password)
    assert password not in first
    assert first != second
    assert verify_password(password, first)
    assert verify_password(password, second)
    assert not verify_password("another password", first)


@pytest.mark.parametrize("encoded", ["", "not-a-password-hash", "$argon2id$malformed"])
def test_malformed_password_hash_fails_closed(encoded: str) -> None:
    assert not verify_password("valid user password", encoded)


def test_csrf_storage_uses_a_digest_that_distinguishes_tokens() -> None:
    token = "session-specific-random-csrf-value"
    assert csrf_digest(token) != token
    assert csrf_digest(token) == csrf_digest(token)
    assert csrf_digest(token) != csrf_digest(token + "changed")


def test_signed_session_token_contains_identity_lifetime_and_csrf(
    security_settings: Settings,
) -> None:
    user_id, session_id = uuid4(), uuid4()
    created_at = datetime.now(UTC).replace(microsecond=0)
    expires_at = created_at + timedelta(hours=8)
    token = encode_session_token(
        user_id, session_id, CSRF_TOKEN, created_at, expires_at, security_settings
    )
    payload = jwt.decode(
        token,
        SECRET,
        algorithms=["HS256"],
        issuer="internal-task-tracker",
        audience="web",
    )
    assert payload["sub"] == str(user_id)
    assert payload["sid"] == str(session_id)
    assert payload["csrf"] == CSRF_TOKEN
    assert payload["iat"] == int(created_at.timestamp())
    assert payload["exp"] == int(expires_at.timestamp())


@pytest.mark.parametrize(
    "fault",
    ["signature", "audience", "issuer", "algorithm", "missing_exp", "missing_sid", "expired"],
)
async def test_untrusted_jwt_is_rejected_before_database_access(
    security_settings: Settings, fault: str
) -> None:
    now = datetime.now(UTC)
    claims = {
        "sub": str(uuid4()),
        "sid": str(uuid4()),
        "csrf": CSRF_TOKEN,
        "iat": int((now - timedelta(minutes=2)).timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "iss": "internal-task-tracker",
        "aud": "web",
    }
    key = SECRET
    algorithm = "HS256"
    if fault == "signature":
        key = "different-signing-secret-at-least-32-characters"
    elif fault == "audience":
        claims["aud"] = "another-application"
    elif fault == "issuer":
        claims["iss"] = "another-issuer"
    elif fault == "algorithm":
        algorithm = "HS512"
    elif fault == "missing_exp":
        del claims["exp"]
    elif fault == "missing_sid":
        del claims["sid"]
    elif fault == "expired":
        claims["exp"] = int((now - timedelta(minutes=1)).timestamp())
    token = jwt.encode(claims, key, algorithm=algorithm)
    session = AsyncMock(spec=AsyncSession)

    with pytest.raises(AppError) as error:
        await authenticate_token(session, token, security_settings)

    assert error.value.status_code == 401
    assert error.value.code == ("SESSION_EXPIRED" if fault == "expired" else "AUTH_REQUIRED")
    assert not session.mock_calls


@pytest.mark.parametrize("method", ["POST", "PATCH", "PUT", "DELETE"])
@pytest.mark.parametrize(
    "origin",
    [None, "null", "https://evil.example", ORIGIN + ".evil.example", ORIGIN + "/"],
)
def test_write_guard_requires_an_exact_allowed_origin(
    write_client: TestClient, method: str, origin: str | None
) -> None:
    request_id = str(uuid4())
    headers = {"X-Request-ID": request_id}
    if origin is not None:
        headers["Origin"] = origin
    response = write_client.request(method, "/write", json={"title": "test"}, headers=headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ORIGIN_DENIED"
    assert response.json()["error"]["details"] == []
    assert response.json()["error"]["request_id"] == request_id
    assert response.headers["x-request-id"] == request_id


@pytest.mark.parametrize("method", ["POST", "PATCH", "PUT"])
@pytest.mark.parametrize("media_type", [None, "text/plain", "application/x-www-form-urlencoded"])
def test_write_guard_rejects_a_non_json_body(
    write_client: TestClient, method: str, media_type: str | None
) -> None:
    headers = {"Origin": ORIGIN}
    if media_type:
        headers["Content-Type"] = media_type
    response = write_client.request(method, "/write", content=b"title=value", headers=headers)
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"
    assert response.json()["error"]["request_id"] == response.headers["x-request-id"]
    UUID(response.headers["x-request-id"])


@pytest.mark.parametrize("method", ["POST", "PATCH", "PUT", "DELETE"])
def test_write_guard_accepts_json_from_an_allowed_origin(
    write_client: TestClient, method: str
) -> None:
    response = write_client.request(
        method,
        "/write",
        content=b'{"title":"test"}',
        headers={"Origin": ORIGIN, "Content-Type": "application/json; charset=utf-8"},
    )
    assert response.status_code == 200
    assert response.json() == {"method": method}


@pytest.mark.parametrize("method", ["GET", "HEAD", "OPTIONS"])
def test_write_guard_allows_reads_and_preflight_without_origin(
    write_client: TestClient, method: str
) -> None:
    response = write_client.request(method, "/write")
    assert response.status_code == 200


def test_bodyless_delete_only_needs_origin_at_transport_layer(write_client: TestClient) -> None:
    response = write_client.delete("/write", headers={"Origin": ORIGIN})
    assert response.status_code == 200


async def test_write_guard_preserves_a_chunked_json_request_body() -> None:
    application = FastAPI()

    @application.post("/echo")
    async def echo(request: Request) -> dict[str, str]:
        return {"body": (await request.body()).decode("utf-8")}

    async def chunks() -> AsyncIterator[bytes]:
        yield b'{"title":'
        yield b'"kept intact"}'

    guarded = RequestContextMiddleware(WriteGuardMiddleware(application, allowed_origins=[ORIGIN]))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=guarded), base_url="http://testserver"
    ) as client:
        response = await client.post(
            "/echo",
            content=chunks(),
            headers={"Origin": ORIGIN, "Content-Type": "application/json"},
        )
    assert response.status_code == 200
    assert response.json() == {"body": '{"title":"kept intact"}'}


@pytest.mark.parametrize("body", [b"", b"non-json"])
async def test_write_guard_distinguishes_empty_frames_from_a_body(body: bytes) -> None:
    application = FastAPI()

    @application.post("/logout")
    async def logout(request: Request) -> dict[str, str]:
        return {"body": (await request.body()).decode("utf-8")}

    async def chunks() -> AsyncIterator[bytes]:
        yield b""
        yield b""
        yield body

    guarded = RequestContextMiddleware(WriteGuardMiddleware(application, allowed_origins=[ORIGIN]))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=guarded), base_url="http://testserver"
    ) as client:
        response = await client.post("/logout", content=chunks(), headers={"Origin": ORIGIN})
    if body:
        assert response.status_code == 415
    else:
        assert response.status_code == 200
        assert response.json() == {"body": ""}


@pytest.fixture
def limiter_clock(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    clock = [100.0]
    monkeypatch.setattr(auth, "time", SimpleNamespace(monotonic=lambda: clock[0]))
    return clock


def test_login_limiter_counts_pending_attempts_and_isolates_hosts(
    limiter_clock: list[float],
) -> None:
    limiter = LoginLimiter(limit=2)
    first, first_retry = limiter.reserve("host-a")
    second, second_retry = limiter.reserve("host-a")
    denied, retry = limiter.reserve("host-a")
    other_host, other_retry = limiter.reserve("host-b")

    assert first is not None and second is not None and first != second
    assert first_retry == second_retry == other_retry == 0
    assert denied is None and retry == 60
    assert other_host is not None


def test_login_limiter_release_frees_only_the_matching_reservation(
    limiter_clock: list[float],
) -> None:
    limiter = LoginLimiter(limit=2)
    first, _ = limiter.reserve("host-a")
    second, _ = limiter.reserve("host-a")
    assert first is not None and second is not None

    limiter.release("another-host", first)
    limiter.release("host-a", uuid4())
    assert limiter.reserve("host-a")[0] is None

    limiter.release("host-a", first)
    limiter.release("host-a", first)
    replacement, _ = limiter.reserve("host-a")
    assert replacement is not None
    assert limiter.reserve("host-a")[0] is None

    limiter.release("host-a", second)
    limiter.release("host-a", replacement)
    assert limiter.reserve("host-a")[0] is not None
    assert limiter.reserve("host-a")[0] is not None


def test_login_limiter_expires_attempts_at_sixty_seconds_without_extending_failures(
    limiter_clock: list[float],
) -> None:
    limiter = LoginLimiter(limit=2)
    assert limiter.reserve("host")[0] is not None
    limiter_clock[0] = 110.0
    assert limiter.reserve("host")[0] is not None

    limiter_clock[0] = 159.2
    assert limiter.reserve("host") == (None, 1)
    limiter_clock[0] = 160.0
    renewed, retry = limiter.reserve("host")
    assert renewed is not None and retry == 0
    assert limiter.reserve("host") == (None, 10)

    limiter_clock[0] = 170.0
    assert limiter.reserve("host")[0] is not None
    assert limiter.reserve("host") == (None, 50)


@pytest.mark.parametrize("password", [None, 123456789012, True, [], {}, "", "s3cret!", "x" * 129])
def test_credentials_reject_malformed_or_out_of_range_passwords(password: object) -> None:
    with pytest.raises(ValidationError) as error:
        Credentials.model_validate({"email": "valid@example.com", "password": password})
    assert any(detail["loc"] == ("password",) for detail in error.value.errors(include_input=False))
    if isinstance(password, str) and password:
        assert password not in str(error.value)


@pytest.mark.parametrize("length", [12, 128])
def test_credentials_accept_password_boundaries_as_masked_secrets(length: int) -> None:
    password = "x" * length
    credentials = Credentials.model_validate({"email": "valid@example.com", "password": password})
    assert isinstance(credentials.password, SecretStr)
    assert credentials.password.get_secret_value() == password
    assert password not in repr(credentials)
    assert password not in credentials.model_dump_json()


def test_credentials_normalize_email_but_preserve_the_password() -> None:
    password = "  significant spaces  "
    credentials = Credentials.model_validate(
        {"email": "  User@EXAMPLE.com  ", "password": password}
    )
    assert credentials.email == "user@example.com"
    assert credentials.password.get_secret_value() == password


@pytest.mark.parametrize("email", [None, "", "missing-at-sign", "user@", 42])
def test_credentials_reject_invalid_email(email: object) -> None:
    password = "do-not-expose-this-password"
    with pytest.raises(ValidationError) as error:
        Credentials.model_validate({"email": email, "password": password})
    assert password not in str(error.value)
    assert any(detail["loc"] == ("email",) for detail in error.value.errors(include_input=False))


@pytest.mark.parametrize("extra", [{"role": "admin"}, {"role_code": "admin"}, {"is_active": False}])
def test_registration_rejects_client_supplied_privileges(extra: dict[str, object]) -> None:
    with pytest.raises(ValidationError) as error:
        RegisterRequest.model_validate(
            {
                "email": "valid@example.com",
                "password": "valid-long-password",
                "name": "User",
                **extra,
            }
        )
    assert any(
        detail["type"] == "extra_forbidden" for detail in error.value.errors(include_input=False)
    )


def test_registration_rejects_a_whitespace_only_name() -> None:
    with pytest.raises(ValidationError) as error:
        RegisterRequest.model_validate(
            {"email": "valid@example.com", "password": "valid-long-password", "name": "   "}
        )
    assert any(detail["loc"] == ("name",) for detail in error.value.errors(include_input=False))
