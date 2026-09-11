"""Run checks; integration URLs target a separate *_test database, never the app DB."""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]


def local_environment() -> dict[str, str]:
    env = os.environ.copy()
    path = ROOT / ".env"
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.lstrip().startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env.setdefault(key.strip(), value.strip().strip("\"'"))
    return env


def test_url(url: str) -> str:
    parsed = urlsplit(url)
    database = parsed.path.removeprefix("/")
    if not database:
        raise ValueError("A database name is required")
    if not database.endswith("_test"):
        database += "_test"
    return urlunsplit(parsed._replace(path=f"/{database}"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--integration", action="store_true")
    parser.add_argument("pytest_args", nargs="*")
    args = parser.parse_args()
    env = local_environment()
    uv = shutil.which("uv")
    if uv is None:
        print("Install uv before running checks.", file=sys.stderr)
        return 2
    if args.integration:
        for test_key, source_key in (
            ("TEST_DATABASE_URL", "DATABASE_URL"),
            ("TEST_MIGRATION_DATABASE_URL", "MIGRATION_DATABASE_URL"),
        ):
            if not env.get(test_key):
                if not env.get(source_key):
                    print(f"Set {test_key} or {source_key}; no credentials were printed.")
                    return 2
                env[test_key] = test_url(env[source_key])
        env["APP_ENV"] = "test"
    selection = "integration" if args.integration else "not integration"
    command = [uv, "run", "--frozen", "pytest", "-m", selection, *args.pytest_args]
    return subprocess.call(command, cwd=ROOT / "backend", env=env)


if __name__ == "__main__":
    raise SystemExit(main())
