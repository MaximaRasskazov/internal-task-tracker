"""Snapshot reads use a dedicated repeatable-read transaction, independent of auth reads."""

from collections.abc import AsyncGenerator

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.session import Database


async def get_read_session(request: Request) -> AsyncGenerator[AsyncSession]:
    database: Database = request.app.state.database
    if database.engine is None:
        raise AppError(503, "TEMPORARILY_UNAVAILABLE", "Сервис временно недоступен")
    async with database.engine.connect() as connection:
        connection = await connection.execution_options(isolation_level="REPEATABLE READ")
        async with connection.begin():
            await connection.execute(text("SET TRANSACTION READ ONLY"))
            async with AsyncSession(bind=connection, expire_on_commit=False) as session:
                yield session
