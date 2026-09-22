"""Registration, finite cookie sessions, and revocation of individual sessions."""

import logging
import math
import secrets
import time
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse

from app.api.dependencies import SessionDependency, get_auth_context
from app.core.config import Settings
from app.core.errors import AppError, error_response, error_responses
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    SESSION_COOKIE,
    AuthContext,
    csrf_digest,
    encode_session_token,
    hash_password,
    signing_key,
    verify_password,
)
from app.db.domain import AuthSession, User
from app.schemas.domain import Email, SessionDto, UserDto

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    email: Email
    password: SecretStr = Field(min_length=12, max_length=128)


class RegisterRequest(Credentials):
    name: str = Field(min_length=1, max_length=80)

    @field_validator("name", mode="before")
    @classmethod
    def trim_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


def user_dto(user: User) -> UserDto:
    return UserDto.model_validate(
        {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role_code,
            "is_active": user.is_active,
            "created_at": user.created_at,
        }
    )


def session_dto(context: AuthContext) -> SessionDto:
    return SessionDto(
        user=user_dto(context.user),
        csrf_token=context.csrf_token,
        expires_at=context.session.expires_at,
    )


class LoginLimiter:
    """One-process failure window; pending verifications reserve capacity atomically."""

    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.attempts: dict[str, dict[UUID, float]] = {}

    def reserve(self, host: str) -> tuple[UUID | None, int]:
        now = time.monotonic()
        attempts = self.attempts.get(host, {})
        attempts = {key: started for key, started in attempts.items() if started > now - 60}
        if len(attempts) >= self.limit:
            self.attempts[host] = attempts
            return None, max(1, math.ceil(60 - (now - min(attempts.values()))))
        if host not in self.attempts and len(self.attempts) >= 10000:
            self.attempts = {
                key: bucket
                for key, bucket in self.attempts.items()
                if any(started > now - 60 for started in bucket.values())
            }
            if len(self.attempts) >= 10000:
                return None, 60
        token = uuid4()
        attempts[token] = now
        self.attempts[host] = attempts
        return token, 0

    def release(self, host: str, token: UUID) -> None:
        bucket = self.attempts.get(host)
        if bucket is not None:
            bucket.pop(token, None)
            if not bucket:
                self.attempts.pop(host, None)


@router.post(
    "/register", response_model=UserDto, status_code=201, responses=error_responses(403, 409)
)
async def register(body: RegisterRequest, session: SessionDependency) -> UserDto:
    password_hash = await run_in_threadpool(hash_password, body.password.get_secret_value())
    user = User(
        name=body.name,
        email=str(body.email),
        password_hash=password_hash,
        role_code="developer",
        is_active=True,
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        if getattr(exc.orig, "sqlstate", None) == "23505":
            raise AppError(409, "DUPLICATE_EMAIL", "Этот email уже зарегистрирован") from exc
        raise
    return user_dto(user)


@router.post("/login", response_model=SessionDto, responses=error_responses(401, 403, 429, 503))
async def login(
    body: Credentials, request: Request, response: Response, session: SessionDependency
) -> SessionDto | JSONResponse:
    settings: Settings = request.app.state.settings
    signing_key(settings)
    limiter: LoginLimiter | None = getattr(request.app.state, "login_limiter", None)
    if limiter is None:
        limiter = LoginLimiter(settings.login_rate_limit_per_minute)
        request.app.state.login_limiter = limiter
    host = request.client.host if request.client is not None else "unknown"
    attempt, retry_after = limiter.reserve(host)
    if attempt is None:
        return error_response(
            request,
            429,
            "RATE_LIMITED",
            "Слишком много попыток входа. Повторите позже",
            headers={"Retry-After": str(retry_after)},
        )
    try:
        user = await session.scalar(select(User).where(User.email == str(body.email)))
        encoded = user.password_hash if user is not None else DUMMY_PASSWORD_HASH
        valid = await run_in_threadpool(verify_password, body.password.get_secret_value(), encoded)
    except Exception:
        limiter.release(host, attempt)
        raise
    if user is None or not valid or not user.is_active:
        raise AppError(401, "INVALID_CREDENTIALS", "Неверный email или пароль")
    limiter.release(host, attempt)
    created_at = datetime.now(UTC).replace(microsecond=0)
    expires_at = created_at + timedelta(seconds=settings.session_ttl_seconds)
    csrf_token = secrets.token_urlsafe(32)
    auth_session = AuthSession(
        id=uuid4(),
        user_id=user.id,
        csrf_hash=csrf_digest(csrf_token),
        created_at=created_at,
        expires_at=expires_at,
    )
    token = encode_session_token(
        user.id, auth_session.id, csrf_token, created_at, expires_at, settings
    )
    session.add(auth_session)
    await session.commit()
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=settings.session_ttl_seconds,
        expires=expires_at,
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )
    response.headers["Cache-Control"] = "no-store"
    return session_dto(AuthContext(user=user, session=auth_session, csrf_token=csrf_token))


@router.get("/me", response_model=SessionDto, responses=error_responses(401))
async def me(
    response: Response, context: Annotated[AuthContext, Depends(get_auth_context)]
) -> SessionDto:
    response.headers["Cache-Control"] = "no-store"
    return session_dto(context)


@router.post("/logout", status_code=204, responses=error_responses(401, 403))
async def logout(
    request: Request,
    session: SessionDependency,
    context: Annotated[AuthContext, Depends(get_auth_context)],
) -> Response:
    context.session.revoked_at = datetime.now(UTC)
    await session.commit()
    hub = getattr(request.app.state, "event_hub", None)
    if hub is not None:
        try:
            await hub.revoke_session(context.session.id)
        except Exception:
            logger.error("WebSocket session notification failed after revocation")
    settings: Settings = request.app.state.settings
    response = Response(status_code=204, headers={"Cache-Control": "no-store"})
    response.delete_cookie(
        key=SESSION_COOKIE,
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )
    return response
