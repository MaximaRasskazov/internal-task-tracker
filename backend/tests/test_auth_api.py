"""Authentication and administrative role guarantees against real PostgreSQL."""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cli.bootstrap_admin import BootstrapSettings, bootstrap_admin
from app.core.security import SESSION_COOKIE, csrf_digest, verify_password
from app.db.domain import AuthSession, User
from tests.support import ORIGIN, TEST_PASSWORD, login

pytestmark = pytest.mark.integration


async def test_register_normalizes_without_login_or_role_escalation(
    client: AsyncClient, db: AsyncSession
) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "name": "  Тестовый участник  ",
            "email": "  REG@example.com  ",
            "password": TEST_PASSWORD,
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == "Тестовый участник"
    assert body["email"] == "reg@example.com"
    assert body["role"] == "developer"
    assert body["is_active"] is True
    assert set(body) == {"id", "name", "email", "role", "is_active", "created_at"}
    assert "set-cookie" not in response.headers
    assert (await client.get("/api/v1/auth/me")).status_code == 401
    user = await db.get(User, UUID(body["id"]))
    assert user is not None and user.password_hash.startswith("$argon2id$")
    assert verify_password(TEST_PASSWORD, user.password_hash)
    duplicate = await client.post(
        "/api/v1/auth/register",
        json={"name": "Another", "email": "REG@example.com", "password": TEST_PASSWORD},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "DUPLICATE_EMAIL"
    escalation = await client.post(
        "/api/v1/auth/register",
        json={
            "name": "Admin",
            "email": "other@example.com",
            "password": TEST_PASSWORD,
            "role": "admin",
        },
    )
    assert escalation.status_code == 422


async def test_login_cookie_session_and_me(
    client: AsyncClient, db: AsyncSession, users: dict[str, User]
) -> None:
    response = await client.post(
        "/api/v1/auth/login", json={"email": users["developer"].email, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200, response.text
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie and "Path=/" in cookie
    assert "Domain=" not in cookie
    assert "Secure" not in cookie
    assert "token" not in response.json()
    assert "no-store" in response.headers["cache-control"]
    stored = await db.scalar(
        select(AuthSession).where(AuthSession.user_id == users["developer"].id)
    )
    assert stored is not None
    assert stored.csrf_hash == csrf_digest(response.json()["csrf_token"])
    assert stored.csrf_hash != response.json()["csrf_token"]
    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json() == response.json()
    assert "no-store" in me.headers["cache-control"]


async def test_logout_revokes_only_this_session_and_replayed_cookie(
    client: AsyncClient, app: FastAPI, users: dict[str, User]
) -> None:
    await login(client, users["developer"])
    original = client.cookies[SESSION_COOKIE]
    async with AsyncClient(transport=ASGITransport(app=app), base_url=ORIGIN) as other:
        await login(other, users["developer"])
        result = await client.post("/api/v1/auth/logout")
        assert result.status_code == 204 and result.content == b""
        assert "Max-Age=0" in result.headers["set-cookie"]
        assert (await client.get("/api/v1/auth/me")).status_code == 401
        replay = await client.get("/api/v1/auth/me", headers={"Cookie": f"itt_session={original}"})
        assert replay.status_code == 401
        assert (await other.get("/api/v1/auth/me")).status_code == 200


async def test_csrf_and_origin_failures_do_not_revoke_session(
    client: AsyncClient, users: dict[str, User]
) -> None:
    headers = await login(client, users["developer"])
    client.headers.pop("X-CSRF-Token")
    for supplied in (None, "incorrect-token"):
        response = await client.post(
            "/api/v1/auth/logout", headers={"X-CSRF-Token": supplied} if supplied else {}
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "CSRF_FAILED"
    client.headers.update(headers)
    client.headers.pop("Origin")
    response = await client.post("/api/v1/auth/logout")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ORIGIN_DENIED"
    assert (await client.get("/api/v1/auth/me")).status_code == 200
    client.headers["Origin"] = ORIGIN
    assert (await client.post("/api/v1/auth/logout")).status_code == 204


async def test_failed_login_is_generic_and_limited(
    client: AsyncClient, app: FastAPI, users: dict[str, User]
) -> None:
    app.state.settings.login_rate_limit_per_minute = 2
    responses = []
    for email in (users["developer"].email, "does-not-exist@example.com"):
        responses.append(
            await client.post(
                "/api/v1/auth/login", json={"email": email, "password": "invalid-password-123"}
            )
        )
    assert [response.status_code for response in responses] == [401, 401]
    assert all(response.json()["error"]["code"] == "INVALID_CREDENTIALS" for response in responses)
    assert responses[0].json()["error"]["message"] == responses[1].json()["error"]["message"]
    limited = await client.post(
        "/api/v1/auth/login", json={"email": users["developer"].email, "password": TEST_PASSWORD}
    )
    assert limited.status_code == 429
    assert 1 <= int(limited.headers["retry-after"]) <= 60
    assert limited.json()["error"]["request_id"] == limited.headers["x-request-id"]


async def test_admin_directory_and_live_role_change(
    client: AsyncClient, app: FastAPI, users: dict[str, User]
) -> None:
    await login(client, users["admin"])
    page = await client.get("/api/v1/users", params={"q": "DEVELOPER", "limit": 1, "offset": 1})
    assert page.status_code == 200
    assert page.json()["total"] == 2
    assert len(page.json()["items"]) == 1
    assert (await client.get("/api/v1/users", params={"q": "%"})).json()["total"] == 0
    async with AsyncClient(transport=ASGITransport(app=app), base_url=ORIGIN) as member:
        await login(member, users["developer"])
        assert (await member.get("/api/v1/users")).status_code == 403
        changed = await client.patch(
            f"/api/v1/users/{users['developer'].id}/role", json={"role": "pm"}
        )
        assert changed.status_code == 200 and changed.json()["role"] == "pm"
        assert (await member.get("/api/v1/auth/me")).json()["user"]["role"] == "pm"
    self_change = await client.patch(
        f"/api/v1/users/{users['admin'].id}/role", json={"role": "developer"}
    )
    assert self_change.status_code == 403


async def test_concurrent_admin_demotions_preserve_active_admin(
    client: AsyncClient, app: FastAPI, db: AsyncSession, users: dict[str, User]
) -> None:
    users["pm"].role_code = "admin"
    await db.commit()
    await login(client, users["admin"])
    async with AsyncClient(transport=ASGITransport(app=app), base_url=ORIGIN) as other:
        await login(other, users["pm"])
        outcomes = await asyncio.gather(
            client.patch(f"/api/v1/users/{users['pm'].id}/role", json={"role": "developer"}),
            other.patch(f"/api/v1/users/{users['admin'].id}/role", json={"role": "developer"}),
        )
    assert sorted(response.status_code for response in outcomes) == [200, 403]
    assert (
        await db.scalar(
            select(func.count())
            .select_from(User)
            .where(User.role_code == "admin", User.is_active.is_(True))
        )
        == 1
    )


async def test_expired_database_session_is_rejected(
    client: AsyncClient, db: AsyncSession, users: dict[str, User]
) -> None:
    await login(client, users["developer"])
    stored = await db.scalar(
        select(AuthSession).where(AuthSession.user_id == users["developer"].id)
    )
    assert stored is not None
    stored.created_at = datetime.now(UTC) - timedelta(hours=10)
    stored.expires_at = datetime.now(UTC) - timedelta(hours=1)
    await db.commit()
    result = await client.get("/api/v1/auth/me")
    assert result.status_code == 401
    assert result.json()["error"]["code"] == "SESSION_EXPIRED"


async def test_inactive_user_loses_existing_session_and_cannot_login(
    client: AsyncClient, db: AsyncSession, users: dict[str, User]
) -> None:
    await login(client, users["developer"])
    users["developer"].is_active = False
    await db.commit()
    assert (await client.get("/api/v1/auth/me")).status_code == 401
    result = await client.post(
        "/api/v1/auth/login", json={"email": users["developer"].email, "password": TEST_PASSWORD}
    )
    assert result.status_code == 401
    assert result.json()["error"]["code"] == "INVALID_CREDENTIALS"


async def test_bootstrap_first_admin_is_idempotent_without_password_reset(
    app: FastAPI, db: AsyncSession
) -> None:
    options = BootstrapSettings(
        _env_file=None,
        name="First Admin",
        email="bootstrap@example.com",
        password=SecretStr(TEST_PASSWORD),
    )
    assert await bootstrap_admin(app.state.settings, options) is True
    options.password = SecretStr("different-password-that-must-not-replace")
    assert await bootstrap_admin(app.state.settings, options) is False
    admin = await db.scalar(select(User).where(User.email == "bootstrap@example.com"))
    assert admin is not None and admin.role_code == "admin"
    assert verify_password(TEST_PASSWORD, admin.password_hash)
    assert not verify_password(options.password.get_secret_value(), admin.password_hash)
