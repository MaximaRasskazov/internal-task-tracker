import ipaddress
import json
from functools import lru_cache
from typing import Annotated, Literal, Self
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

from app.core.paths import PROJECT_ROOT


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        hide_input_in_errors=True,
    )

    app_env: Literal["local", "demo", "test", "production"] = "local"
    docs_enabled: bool = True
    database_url: SecretStr | None = None
    migration_database_url: SecretStr | None = None
    jwt_secret: SecretStr | None = None
    demo_password: SecretStr | None = None
    session_ttl_seconds: int = Field(default=28800, ge=60, le=604800)
    allowed_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8080",
        "http://localhost:5173",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:5173",
    ]
    cookie_secure: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    api_lock_timeout_ms: int = Field(default=3000, ge=100, le=60000)
    login_rate_limit_per_minute: int = Field(default=10, ge=1, le=1000)
    health_check_timeout_seconds: float = Field(default=3.0, ge=0.1, le=30)

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return json.loads(value) if value.lstrip().startswith("[") else value.split(",")
        return value

    @field_validator("allowed_origins")
    @classmethod
    def validate_origins(cls, origins: list[str]) -> list[str]:
        result = []
        for origin in origins:
            origin = origin.strip()
            parsed = urlsplit(origin)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
                or parsed.path
                or parsed.query
                or parsed.fragment
                or "*" in origin
            ):
                raise ValueError(
                    "ALLOWED_ORIGINS must contain explicit HTTP(S) origins without paths"
                )
            # Evaluating port also rejects malformed/non-numeric port values.
            _ = parsed.port
            result.append(origin)
        if not result:
            raise ValueError("At least one allowed origin is required")
        return list(dict.fromkeys(result))

    @field_validator("database_url", "migration_database_url")
    @classmethod
    def validate_database_url(cls, value: SecretStr | None) -> SecretStr | None:
        if value is None:
            return None
        try:
            url = make_url(value.get_secret_value())
            valid = url.drivername == "postgresql+asyncpg" and bool(url.host and url.database)
        except (ArgumentError, ValueError):
            valid = False
        if not valid:
            raise ValueError("DATABASE_URL must be a PostgreSQL URL using the asyncpg dialect")
        return value

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None and len(value.get_secret_value()) < 32:
            raise ValueError("JWT_SECRET must contain at least 32 characters")
        return value

    @field_validator("demo_password")
    @classmethod
    def validate_demo_password(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None and len(value.get_secret_value()) < 12:
            raise ValueError("DEMO_PASSWORD must contain at least 12 characters")
        return value

    @model_validator(mode="after")
    def validate_deployment(self) -> Self:
        if self.app_env == "production":
            if not self.cookie_secure or self.jwt_secret is None or self.database_url is None:
                raise ValueError("Production requires COOKIE_SECURE, JWT_SECRET, and DATABASE_URL")
            if self.demo_password is not None:
                raise ValueError("DEMO_PASSWORD is not allowed in production")
            if any(not origin.startswith("https://") for origin in self.allowed_origins):
                raise ValueError("Production origins must use HTTPS")
        if not self.cookie_secure:
            for origin in self.allowed_origins:
                host = urlsplit(origin).hostname
                try:
                    is_local = host == "localhost" or ipaddress.ip_address(host or "").is_loopback
                except ValueError:
                    is_local = False
                if not is_local:
                    raise ValueError("COOKIE_SECURE=false is permitted only for loopback origins")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
