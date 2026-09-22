"""Cookie session cryptography shared by HTTP and WebSocket authentication."""

import hashlib
import hmac
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

import jwt
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import AppError
from app.db.domain import AuthSession, User

SESSION_COOKIE = "itt_session"
JWT_ISSUER = "internal-task-tracker"
JWT_AUDIENCE = "web"
PASSWORD_HASHER = PasswordHash.recommended()
# Verifying a nonexistent account performs the same password algorithm as a real account.
DUMMY_PASSWORD_HASH = PASSWORD_HASHER.hash("non-account-placeholder-password")


@dataclass(frozen=True)
class AuthContext:
    user: User
    session: AuthSession
    csrf_token: str


def hash_password(password: str) -> str:
    return PASSWORD_HASHER.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    try:
        return PASSWORD_HASHER.verify(password, encoded)
    except (ValueError, TypeError, UnknownHashError):
        return False


def csrf_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def signing_key(settings: Settings) -> str:
    if settings.jwt_secret is None:
        raise AppError(503, "TEMPORARILY_UNAVAILABLE", "Сервис временно недоступен")
    return settings.jwt_secret.get_secret_value()


def encode_session_token(
    user_id: UUID,
    session_id: UUID,
    csrf_token: str,
    created_at: datetime,
    expires_at: datetime,
    settings: Settings,
) -> str:
    return jwt.encode(
        {
            "sub": str(user_id),
            "sid": str(session_id),
            "csrf": csrf_token,
            "iat": int(created_at.timestamp()),
            "exp": int(expires_at.timestamp()),
            "iss": JWT_ISSUER,
            "aud": JWT_AUDIENCE,
        },
        signing_key(settings),
        algorithm="HS256",
    )


async def authenticate_token(session: AsyncSession, token: str, settings: Settings) -> AuthContext:
    try:
        claims = jwt.decode(
            token,
            signing_key(settings),
            algorithms=["HS256"],
            issuer=JWT_ISSUER,
            audience=JWT_AUDIENCE,
            options={
                "require": ["sub", "sid", "csrf", "iat", "exp", "iss", "aud"],
                "strict_aud": True,
            },
        )
        user_id = UUID(claims["sub"])
        session_id = UUID(claims["sid"])
        csrf_token = claims["csrf"]
        if (
            not isinstance(csrf_token, str)
            or not 32 <= len(csrf_token) <= 256
            or type(claims["iat"]) is not int
            or type(claims["exp"]) is not int
            or claims["iat"] >= claims["exp"]
        ):
            raise ValueError("Invalid session claims")
    except jwt.ExpiredSignatureError as exc:
        raise AppError(401, "SESSION_EXPIRED", "Сессия истекла. Войдите снова") from exc
    except (jwt.InvalidTokenError, ValueError, TypeError, KeyError, AttributeError) as exc:
        raise AppError(401, "AUTH_REQUIRED", "Войдите в систему") from exc

    row = (
        await session.execute(
            select(AuthSession, User)
            .join(User, User.id == AuthSession.user_id)
            .where(AuthSession.id == session_id, User.id == user_id)
            .execution_options(populate_existing=True)
        )
    ).one_or_none()
    if row is None:
        raise AppError(401, "AUTH_REQUIRED", "Войдите в систему")
    auth_session, user = row
    if auth_session.revoked_at is not None or not user.is_active:
        raise AppError(401, "AUTH_REQUIRED", "Войдите в систему")
    if auth_session.expires_at <= datetime.now(UTC):
        raise AppError(401, "SESSION_EXPIRED", "Сессия истекла. Войдите снова")
    if not hmac.compare_digest(csrf_digest(csrf_token), auth_session.csrf_hash):
        raise AppError(401, "AUTH_REQUIRED", "Войдите в систему")
    return AuthContext(user=user, session=auth_session, csrf_token=csrf_token)
