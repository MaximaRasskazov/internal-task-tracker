from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings
from app.core.errors import AppError


class Database:
    def __init__(self, settings: Settings) -> None:
        self.engine: AsyncEngine | None = None
        self.sessions: async_sessionmaker[AsyncSession] | None = None
        if settings.database_url is not None:
            self.engine = create_async_engine(
                settings.database_url.get_secret_value(),
                pool_pre_ping=True,
                pool_timeout=settings.health_check_timeout_seconds,
                connect_args={
                    "timeout": settings.health_check_timeout_seconds,
                    "server_settings": {"lock_timeout": f"{settings.api_lock_timeout_ms}ms"},
                },
            )
            self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    async def dispose(self) -> None:
        if self.engine is not None:
            await self.engine.dispose()


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    database: Database = request.app.state.database
    if database.sessions is None:
        raise AppError(503, "TEMPORARILY_UNAVAILABLE", "Сервис временно недоступен")
    async with database.sessions() as session:
        # The owning service chooses its transaction boundary and commits explicitly.
        yield session
