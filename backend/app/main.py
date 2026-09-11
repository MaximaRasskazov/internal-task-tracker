import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import analytics, auth, boards, health, projects, realtime, tags, tasks, users
from app.api.dependencies import WriteGuardMiddleware
from app.api.realtime import Hub
from app.core.config import Settings
from app.core.errors import error_responses, install_error_handlers
from app.core.middleware import RequestContextMiddleware
from app.db.session import Database


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or Settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        logging.basicConfig(level=config.log_level, format="%(message)s")
        application.state.database = Database(config)
        application.state.event_hub = Hub(application.state.database, config)
        await application.state.event_hub.start()
        try:
            yield
        finally:
            await application.state.event_hub.stop()
            await application.state.database.dispose()

    application = FastAPI(
        title="Internal Task Tracker API",
        version="0.1.0",
        description="Корпоративный таск-трекер: сессии, проекты, Kanban, аудит и аналитика.",
        docs_url="/docs" if config.docs_enabled else None,
        redoc_url="/redoc" if config.docs_enabled else None,
        openapi_url="/openapi.json" if config.docs_enabled else None,
        lifespan=lifespan,
        responses=error_responses(422, 500),
    )
    application.state.settings = config
    install_error_handlers(application)
    for router in (
        health.router,
        auth.router,
        users.router,
        projects.router,
        boards.router,
        tags.router,
        tasks.router,
        analytics.router,
    ):
        application.include_router(router, prefix="/api/v1")
    application.include_router(realtime.router)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=config.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-CSRF-Token", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )
    application.add_middleware(WriteGuardMiddleware, allowed_origins=config.allowed_origins)
    application.add_middleware(RequestContextMiddleware)
    return application


app = create_app()
