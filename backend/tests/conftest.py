import os
import subprocess
import sys
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr
from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import Settings
from app.main import create_app
from tests.support import ORIGIN, TEST_PASSWORD

if TYPE_CHECKING:
    from app.db.domain import User


@pytest.fixture
def application() -> FastAPI:
    return create_app(Settings(_env_file=None, app_env="test", database_url=None))


@pytest.fixture
def unit_client(application: FastAPI) -> Iterator[TestClient]:
    with TestClient(application) as test_client:
        yield test_client


@dataclass(frozen=True)
class DatabaseUrls:
    runtime: str
    owner: str


def _safe_test_urls(runtime: str, owner: str) -> DatabaseUrls:
    """Both URLs must explicitly address the same disposable PostgreSQL database."""
    try:
        runtime_url, owner_url = make_url(runtime), make_url(owner)
    except Exception:
        pytest.fail("Invalid test database URL; credentials are omitted", pytrace=False)
    for url in (runtime_url, owner_url):
        if (
            url.drivername != "postgresql+asyncpg"
            or not url.host
            or not url.database
            or not url.database.endswith("_test")
        ):
            pytest.fail(
                "Integration tests require explicit postgresql+asyncpg URLs to a *_test database",
                pytrace=False,
            )
    if (runtime_url.host, runtime_url.port or 5432, runtime_url.database) != (
        owner_url.host,
        owner_url.port or 5432,
        owner_url.database,
    ):
        pytest.fail(
            "Runtime and migration test URLs must identify the same database", pytrace=False
        )
    return DatabaseUrls(runtime, owner)


@pytest.fixture(scope="session")
def _test_database_urls() -> DatabaseUrls:
    runtime = os.environ.get("TEST_DATABASE_URL")
    owner = os.environ.get("TEST_MIGRATION_DATABASE_URL")
    if not runtime:
        pytest.skip("TEST_DATABASE_URL is unset; a real disposable PostgreSQL database is required")
    if not owner:
        pytest.fail("TEST_MIGRATION_DATABASE_URL must explicitly supply the test schema owner")
    if os.environ.get("PYTEST_XDIST_WORKER"):
        pytest.fail("Use a separate *_test database per pytest process; shared tests run serially")
    return _safe_test_urls(runtime, owner)


@pytest.fixture(scope="session")
def _migrated_database(_test_database_urls: DatabaseUrls) -> DatabaseUrls:
    env = os.environ.copy()
    env.update(
        APP_ENV="test",
        DATABASE_URL=_test_database_urls.runtime,
        MIGRATION_DATABASE_URL=_test_database_urls.owner,
        JWT_SECRET="integration-tests-only-secret-32-characters",
        DEMO_PASSWORD=TEST_PASSWORD,
        COOKIE_SECURE="false",
        ALLOWED_ORIGINS=ORIGIN,
    )
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode:
        # Driver failures can embed connection URLs; never put those into pytest reports.
        diagnostic = result.stderr + result.stdout
        for url in (_test_database_urls.runtime, _test_database_urls.owner):
            diagnostic = diagnostic.replace(url, "<test-database>")
            password = make_url(url).password
            if password:
                diagnostic = diagnostic.replace(password, "<redacted>")
        pytest.fail("Test database migration failed:\n" + diagnostic[-6000:], pytrace=False)
    return _test_database_urls


@pytest.fixture
async def _isolated_database(_migrated_database: DatabaseUrls) -> AsyncIterator[DatabaseUrls]:
    """Reset committed data, allowing API requests to use independent real transactions."""
    engine = create_async_engine(_migrated_database.owner, poolclass=NullPool)
    async with engine.connect() as connection:
        locked = await connection.scalar(text("SELECT pg_try_advisory_lock(1169367311)"))
        if not locked:
            await engine.dispose()
            pytest.fail("Another test process is using this database; choose a separate *_test DB")
        await connection.commit()
        tables = await connection.run_sync(lambda conn: inspect(conn).get_table_names("public"))
        tables = sorted(set(tables) - {"alembic_version", "roles"})
        quoted = [engine.dialect.identifier_preparer.quote_identifier(name) for name in tables]
        reset = text("TRUNCATE TABLE " + ", ".join(f"public.{name}" for name in quoted))

        async def truncate_test_data() -> None:
            if not tables:
                return
            # Only the explicitly supplied *_test schema owner can suspend this trigger.
            # It is restored in the same transaction before any application request runs.
            if "audit_events" in tables:
                await connection.execute(
                    text("ALTER TABLE audit_events DISABLE TRIGGER audit_events_append_only")
                )
            await connection.execute(reset)
            if "audit_events" in tables:
                await connection.execute(
                    text("ALTER TABLE audit_events ENABLE TRIGGER audit_events_append_only")
                )
            await connection.commit()

        try:
            await truncate_test_data()
            yield _migrated_database
        finally:
            await truncate_test_data()
            await connection.execute(text("SELECT pg_advisory_unlock(1169367311)"))
            await connection.commit()
    await engine.dispose()


@pytest.fixture
async def app(_isolated_database: DatabaseUrls) -> AsyncIterator[FastAPI]:
    settings = Settings(
        _env_file=None,
        app_env="test",
        database_url=SecretStr(_isolated_database.runtime),
        migration_database_url=SecretStr(_isolated_database.owner),
        jwt_secret=SecretStr("integration-tests-only-secret-32-characters"),
        demo_password=SecretStr(TEST_PASSWORD),
        allowed_origins=[ORIGIN],
        cookie_secure=False,
        login_rate_limit_per_minute=1000,
    )
    application = create_app(settings)
    async with application.router.lifespan_context(application):
        yield application


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url=ORIGIN,
        headers={"Origin": ORIGIN},
    ) as test_client:
        yield test_client


@pytest.fixture
async def db(app: FastAPI) -> AsyncIterator[AsyncSession]:
    async with app.state.database.sessions() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def users(db: AsyncSession) -> dict[str, "User"]:
    from app.core.security import hash_password
    from app.db.domain import User

    roles = {
        "admin": "admin",
        "pm": "pm",
        "developer": "developer",
        "developer_b": "developer",
        "outsider": "developer",
        "second_pm": "pm",
    }
    password_hash = hash_password(TEST_PASSWORD)
    result = {
        key: User(
            name=f"Fixture {key}",
            email=f"fixture-{key.replace('_', '-')}@example.test",
            role_code=role,
            password_hash=password_hash,
            is_active=True,
        )
        for key, role in roles.items()
    }
    db.add_all(result.values())
    await db.commit()
    return result
