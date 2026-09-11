"""Request authentication, CSRF enforcement, and unsafe-request Origin checks."""

import hmac
from typing import Annotated

from fastapi import Depends, Header, Request, Security
from fastapi.security import APIKeyCookie
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import Settings
from app.core.errors import AppError, error_response
from app.core.security import SESSION_COOKIE, AuthContext, authenticate_token, csrf_digest
from app.db.domain import User
from app.db.session import get_session

WRITE_METHODS = frozenset({"POST", "PATCH", "PUT", "DELETE"})
SessionDependency = Annotated[AsyncSession, Depends(get_session)]
session_cookie = APIKeyCookie(
    name=SESSION_COOKIE,
    auto_error=False,
    scheme_name="SessionCookie",
    description=(
        "Выполните POST /auth/login: браузер сохранит HttpOnly cookie автоматически. "
        "JWT не нужно копировать или сохранять в JavaScript."
    ),
)


async def get_auth_context(
    request: Request,
    session: SessionDependency,
    token: Annotated[str | None, Security(session_cookie)],
    csrf_token: Annotated[
        str | None,
        Header(
            alias="X-CSRF-Token",
            description=(
                "Для POST/PATCH/PUT/DELETE укажите csrf_token из ответа /auth/login "
                "или /auth/me. Для GET не требуется."
            ),
        ),
    ] = None,
) -> AuthContext:
    cached: AuthContext | None = getattr(request.state, "auth_context", None)
    if cached is not None:
        return cached
    if token is None:
        raise AppError(401, "AUTH_REQUIRED", "Войдите в систему")
    settings: Settings = request.app.state.settings
    context = await authenticate_token(session, token, settings)
    if request.method in WRITE_METHODS:
        supplied = csrf_token or ""
        if not supplied or not hmac.compare_digest(
            csrf_digest(supplied), context.session.csrf_hash
        ):
            raise AppError(403, "CSRF_FAILED", "Не удалось проверить защитный токен")
    request.state.auth_context = context
    request.state.auth_session_id = context.session.id
    return context


async def get_current_user(
    context: Annotated[AuthContext, Depends(get_auth_context)],
) -> User:
    return context.user


CurrentUser = Annotated[User, Depends(get_current_user)]


class WriteGuardMiddleware:
    def __init__(self, app: ASGIApp, allowed_origins: list[str]) -> None:
        self.app = app
        self.allowed_origins = frozenset(allowed_origins)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] not in WRITE_METHODS:
            await self.app(scope, receive, send)
            return
        request = Request(scope)
        if request.headers.get("origin") not in self.allowed_origins:
            response = error_response(request, 403, "ORIGIN_DENIED", "Источник запроса не разрешён")
            await response(scope, receive, send)
            return

        if scope["method"] in {"POST", "PATCH", "PUT"}:
            # Peek one ASGI body frame and replay it, including chunked requests.
            first = await receive()
            # Empty intermediate frames do not imply a body: HTTPX and proxies may
            # emit them even for a bodyless logout. Discard only these empty frames.
            while (
                first["type"] == "http.request" and not first.get("body") and first.get("more_body")
            ):
                first = await receive()
            has_body = first["type"] == "http.request" and bool(first.get("body"))
            media_type = request.headers.get("content-type", "").split(";", 1)[0].lower().strip()
            if has_body and media_type != "application/json":
                response = error_response(
                    request, 415, "UNSUPPORTED_MEDIA_TYPE", "Отправьте тело в формате JSON"
                )
                await response(scope, receive, send)
                return
            pending: Message | None = first

            async def replay() -> Message:
                nonlocal pending
                if pending is not None:
                    message, pending = pending, None
                    return message
                return await receive()

            await self.app(scope, replay, send)
            return
        await self.app(scope, receive, send)
