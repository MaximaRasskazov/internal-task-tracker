"""The migrated database is usable through the restricted runtime connection."""

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.integration


async def test_postgres_migrations_roles_and_readiness(
    client: AsyncClient, db: AsyncSession
) -> None:
    # Shared fixtures run migrations as the owner, then provide runtime-only sessions.
    response = await client.get("/api/v1/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
    roles = (await db.execute(text("SELECT code FROM roles ORDER BY code"))).scalars()
    assert list(roles) == ["admin", "developer", "pm"]
