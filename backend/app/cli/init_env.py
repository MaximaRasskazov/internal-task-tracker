import argparse
import os
import secrets
from pathlib import Path

from app.core.paths import PROJECT_ROOT


def create_env(output: Path) -> bool:
    """Create a local file exclusively; existing files and symlinks are never overwritten."""
    password = secrets.token_urlsafe(32)
    owner_password = secrets.token_urlsafe(32)
    content = (
        "# Local development only. Never commit or share this file.\n"
        "APP_ENV=local\n"
        "POSTGRES_USER=tracker\n"
        "POSTGRES_DB=tracker\n"
        f"POSTGRES_PASSWORD={password}\n"
        "POSTGRES_OWNER_USER=tracker_owner\n"
        f"POSTGRES_OWNER_PASSWORD={owner_password}\n"
        "POSTGRES_PORT=5433\n"
        f"DATABASE_URL=postgresql+asyncpg://tracker:{password}@localhost:5433/tracker\n"
        f"MIGRATION_DATABASE_URL=postgresql+asyncpg://tracker_owner:{owner_password}"
        "@localhost:5433/tracker\n"
        f"JWT_SECRET={secrets.token_urlsafe(48)}\n"
        f"DEMO_PASSWORD={secrets.token_urlsafe(24)}\n"
        "SESSION_TTL_SECONDS=28800\n"
        "ALLOWED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000,"
        "http://localhost:8080,http://localhost:5173,"
        "http://127.0.0.1:8080,http://127.0.0.1:5173\n"
        "COOKIE_SECURE=false\n"
        "LOG_LEVEL=INFO\n"
        "API_LOCK_TIMEOUT_MS=3000\n"
        "LOGIN_RATE_LIMIT_PER_MINUTE=10\n"
        "HEALTH_CHECK_TIMEOUT_SECONDS=3\n"
        "API_PORT=8000\n"
        "FRONTEND_PORT=8080\n"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return False
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate local secrets without overwriting .env")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / ".env")
    args = parser.parse_args()
    output: Path = args.output.absolute()
    if create_env(output):
        print(f"Created local environment: {output}. Secret values are not printed.")
    else:
        print(f"Preserved existing environment: {output}. No values were changed.")


if __name__ == "__main__":
    main()
