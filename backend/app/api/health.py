import asyncio
from collections.abc import Awaitable, Callable
from typing import Annotated, Literal

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import text

from app.core.errors import AppError, error_responses
from app.core.paths import BACKEND_DIR
from app.db.session import Database

router = APIRouter(prefix="/health", tags=["health"])
ReadinessChecker = Callable[[], Awaitable[None]]


class LiveResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ReadyResponse(BaseModel):
    status: Literal["ready"] = "ready"


def migration_heads() -> set[str]:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    return set(ScriptDirectory.from_config(config).get_heads())


def get_readiness_checker(request: Request) -> ReadinessChecker:
    async def check() -> None:
        database: Database = request.app.state.database
        if database.engine is None:
            raise RuntimeError("Database is not configured")
        expected = migration_heads()
        if not expected:
            raise RuntimeError("No code migrations found")
        async with asyncio.timeout(request.app.state.settings.health_check_timeout_seconds):
            async with database.engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
                current = await connection.run_sync(
                    lambda sync: set(MigrationContext.configure(sync).get_current_heads())
                )
                if current != expected:
                    raise RuntimeError("Database migration revision differs from code")

    return check


@router.get("/live", response_model=LiveResponse, operation_id="health_live")
async def live() -> LiveResponse:
    """The HTTP process is serving requests; this does not imply database readiness."""
    return LiveResponse()


@router.get(
    "/ready",
    response_model=ReadyResponse,
    responses=error_responses(503),
    operation_id="health_ready",
)
async def ready(
    checker: Annotated[ReadinessChecker, Depends(get_readiness_checker)],
) -> ReadyResponse:
    """The database is reachable and its migration heads exactly match this build."""
    try:
        await checker()
    except Exception:
        raise AppError(503, "TEMPORARILY_UNAVAILABLE", "Сервис временно недоступен") from None
    return ReadyResponse()
