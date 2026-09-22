"""Create the first administrator once, using secret environment configuration."""

import asyncio

from pydantic import SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.api.auth import RegisterRequest
from app.core.config import Settings
from app.core.errors import AppError
from app.core.paths import PROJECT_ROOT
from app.core.security import hash_password
from app.db.domain import User
from app.db.models import Role
from app.db.session import Database


class BootstrapSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BOOTSTRAP_ADMIN_",
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )

    name: str = "Администратор"
    email: str | None = None
    password: SecretStr | None = None


async def bootstrap_admin(settings: Settings, bootstrap: BootstrapSettings) -> bool:
    database = Database(settings)
    try:
        if database.sessions is None:
            raise AppError(503, "TEMPORARILY_UNAVAILABLE", "Сначала настройте DATABASE_URL")
        async with database.sessions() as session:
            role = await session.scalar(select(Role).where(Role.code == "admin").with_for_update())
            if role is None:
                raise AppError(503, "TEMPORARILY_UNAVAILABLE", "Сначала примените миграции")
            existing = await session.scalar(
                select(User.id).where(User.role_code == "admin", User.is_active.is_(True)).limit(1)
            )
            if existing is not None:
                return False
            if bootstrap.email is None or bootstrap.password is None:
                raise AppError(
                    422,
                    "VALIDATION_ERROR",
                    "Укажите BOOTSTRAP_ADMIN_EMAIL и BOOTSTRAP_ADMIN_PASSWORD в окружении",
                )
            body = RegisterRequest(
                name=bootstrap.name,
                email=bootstrap.email,
                password=bootstrap.password,
            )
            if await session.scalar(select(User.id).where(User.email == str(body.email))):
                raise AppError(
                    409,
                    "DUPLICATE_EMAIL",
                    "Email уже занят. Укажите отдельный email администратора",
                )
            encoded = await asyncio.to_thread(hash_password, body.password.get_secret_value())
            session.add(
                User(
                    name=body.name,
                    email=str(body.email),
                    password_hash=encoded,
                    role_code="admin",
                    is_active=True,
                )
            )
            await session.commit()
            return True
    finally:
        await database.dispose()


def main() -> None:
    try:
        created = asyncio.run(bootstrap_admin(Settings(), BootstrapSettings()))
    except AppError as exc:
        raise SystemExit(exc.message) from None
    except ValidationError:
        raise SystemExit(
            "Проверьте настройки и поля администратора; пароль: 12–128 символов"
        ) from None
    except SQLAlchemyError:
        raise SystemExit(
            "Не удалось создать администратора. Проверьте подключение и миграции"
        ) from None
    print(
        "Первый администратор создан" if created else "Администратор уже существует; изменений нет"
    )


if __name__ == "__main__":
    main()
