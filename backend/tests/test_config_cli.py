import os
import subprocess
import sys
from pathlib import Path

import pytest
from dotenv import dotenv_values
from pydantic import ValidationError

from app.cli.init_env import create_env
from app.core.config import Settings
from app.core.paths import BACKEND_DIR, PROJECT_ROOT


def test_env_creation_is_non_destructive_and_secrets_are_independent(tmp_path: Path) -> None:
    destination = tmp_path / ".env"
    assert create_env(destination)
    values = dotenv_values(destination)
    secrets = [values[key] for key in ["JWT_SECRET", "POSTGRES_PASSWORD", "DEMO_PASSWORD"]]
    assert len(set(secrets)) == 3
    assert all(value and len(value) >= 24 for value in secrets)
    assert "@localhost:5433/tracker" in str(values["DATABASE_URL"])
    assert values["POSTGRES_PASSWORD"] != values["POSTGRES_OWNER_PASSWORD"]
    before = destination.read_bytes()
    assert not create_env(destination)
    assert destination.read_bytes() == before
    assert Settings(_env_file=destination).session_ttl_seconds == 28800


def test_init_cli_does_not_print_generated_secrets(tmp_path: Path) -> None:
    destination = tmp_path / "generated.env"
    result = subprocess.run(
        [sys.executable, "-m", "app.cli.init_env", "--output", str(destination)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    values = dotenv_values(destination)
    for key in ["JWT_SECRET", "POSTGRES_PASSWORD", "POSTGRES_OWNER_PASSWORD", "DEMO_PASSWORD"]:
        assert values[key] not in result.stdout + result.stderr
    assert "Created local environment" in result.stdout


@pytest.mark.parametrize(
    "override",
    [
        {"database_url": "sqlite:///private"},
        {"jwt_secret": "short"},
        {"session_ttl_seconds": -1},
        {"allowed_origins": ["*"]},
        {"allowed_origins": ["http://localhost:8080/path"]},
        {"allowed_origins": ["http://user:pass@localhost:8080"]},
        {"allowed_origins": ["http://public.example.test"], "cookie_secure": False},
        {"app_env": "production", "cookie_secure": False},
    ],
)
def test_invalid_settings_are_rejected(override: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **override)


def test_settings_parse_json_and_comma_separated_origins() -> None:
    expected = ["http://localhost:8080", "http://localhost:5173"]
    assert Settings(_env_file=None, allowed_origins=",".join(expected)).allowed_origins == expected
    assert (
        Settings(
            _env_file=None,
            allowed_origins='["http://localhost:8080", "http://localhost:5173"]',
        ).allowed_origins
        == expected
    )


def test_default_env_path_is_repo_root_independent_of_cwd(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    assert Settings.model_config["env_file"] == PROJECT_ROOT / ".env"
    assert (BACKEND_DIR / "alembic.ini").is_file()


def test_openapi_export_and_check_from_another_directory(tmp_path: Path) -> None:
    output = tmp_path / "openapi.json"
    command = [sys.executable, "-m", "app.cli.export_openapi", "--output", str(output)]
    subprocess.run(command, cwd=tmp_path, capture_output=True, check=True)
    first = output.read_bytes()
    subprocess.run(command, cwd=tmp_path, capture_output=True, check=True)
    assert output.read_bytes() == first
    subprocess.run([*command, "--check"], cwd=tmp_path, capture_output=True, check=True)
    output.write_text("{}", encoding="utf-8")
    stale = subprocess.run([*command, "--check"], cwd=tmp_path, capture_output=True)
    assert stale.returncode == 1


def test_migration_sql_generation_from_repo_and_backend(tmp_path: Path) -> None:
    environment = dict(os.environ)
    environment["DATABASE_URL"] = (
        "postgresql+asyncpg://tracker:test-only@localhost:5433/tracker_test"
    )
    environment["MIGRATION_DATABASE_URL"] = environment["DATABASE_URL"]
    for directory, config in [(PROJECT_ROOT, "backend/alembic.ini"), (BACKEND_DIR, "alembic.ini")]:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "-c", config, "upgrade", "head", "--sql"],
            cwd=directory,
            env=environment,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "CREATE TABLE roles" in result.stdout
        assert "INSERT INTO roles" in result.stdout
        assert "test-only" not in result.stdout + result.stderr
