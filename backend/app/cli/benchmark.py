"""Reproduce specification 14.2 against a fresh, isolated local benchmark database.

Run with the development dependencies installed. Never truncates, reuses, or drops
an existing database. Credentials are read from files/environment, never arguments.
"""

import argparse
import asyncio
import hashlib
import json
import math
import os
import platform
import re
import secrets
import socket
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from importlib.metadata import version
from pathlib import Path
from typing import Any
from uuid import UUID, uuid5

import asyncpg  # type: ignore[import-untyped]
import httpx
from dotenv import dotenv_values
from sqlalchemy import insert, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import Settings
from app.core.paths import PROJECT_ROOT
from app.core.security import hash_password
from app.db.domain import (
    AuditEvent,
    Board,
    Column,
    Comment,
    Project,
    ProjectMember,
    Tag,
    Task,
    TaskTag,
    User,
)

NAMESPACE = UUID("462346e0-23b1-4813-a3d7-3d9d899eb192")
CLIENTS = 10
RPS = 10
WARMUP_SECONDS = 30
MEASURE_SECONDS = 300


def identity(kind: str, index: int) -> UUID:
    return uuid5(NAMESPACE, f"{kind}:{index}")


def email(index: int) -> str:
    return f"benchmark-{index:02d}@example.test"


class BenchmarkError(RuntimeError):
    """A public explanation that contains no database credentials."""


@dataclass(frozen=True)
class Observation:
    sequence: int
    client: int
    route: str
    status: int | None
    elapsed_ms: float
    start_delay_ms: float
    error: str | None


def percentile(values: list[float], fraction: float) -> float:
    """Nearest-rank percentile, with no failed/slow observation discarded."""
    ordered = sorted(values)
    return round(ordered[max(0, math.ceil(fraction * len(ordered)) - 1)], 3)


def summarize(observations: list[Observation]) -> dict[str, Any]:
    elapsed = [item.elapsed_ms for item in observations]
    delayed = [item.start_delay_ms for item in observations]
    total_elapsed = [item.elapsed_ms + item.start_delay_ms for item in observations]
    errors = sum(item.error is not None for item in observations)
    return {
        "requests": len(observations),
        "errors": errors,
        "error_rate_percent": round(100 * errors / len(observations), 3),
        "p50_ms": percentile(elapsed, 0.50),
        "p95_ms": percentile(elapsed, 0.95),
        "max_ms": round(max(elapsed), 3),
        "schedule_delay_p95_ms": percentile(delayed, 0.95),
        "schedule_delay_max_ms": round(max(delayed), 3),
        "scheduled_response_p95_ms": percentile(total_elapsed, 0.95),
        "http_statuses": {
            str(status): sum(item.status == status for item in observations)
            for status in sorted({item.status for item in observations}, key=str)
        },
    }


def validate_target(name: str, runtime: URL, owner: URL) -> None:
    if not re.fullmatch(r"tracker_benchmark_[a-z0-9_]{1,40}", name):
        raise BenchmarkError("Database name must match tracker_benchmark_[a-z0-9_]{1,40}.")
    for target in (runtime, owner):
        if target.host not in {"localhost", "127.0.0.1", "::1"}:
            raise BenchmarkError("The reproducible benchmark only targets a local PostgreSQL host.")
        if target.drivername != "postgresql+asyncpg":
            raise BenchmarkError("An asyncpg PostgreSQL URL is required.")
    if runtime.host != owner.host or runtime.port != owner.port:
        raise BenchmarkError("Runtime and migration URLs must use the same PostgreSQL server.")
    for target in (owner, runtime):
        if not target.username or not re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]*", target.username):
            raise BenchmarkError("Database URL has an unsupported role name.")


async def create_database(name: str, owner: URL, admin_password: str) -> str:
    connection = await asyncpg.connect(
        host=owner.host,
        port=owner.port or 5432,
        user="postgres",
        password=admin_password,
        database="postgres",
    )
    try:
        if await connection.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", name):
            raise BenchmarkError("Benchmark database already exists; choose a fresh name.")
        # Both identifiers are restricted by validate_target; no raw user text is interpolated.
        await connection.execute(f'CREATE DATABASE "{name}" OWNER "{owner.username}"')
        return str(await connection.fetchval("SELECT version()"))
    finally:
        await connection.close()


async def prepare_fixture(owner: URL, password: str) -> dict[str, int]:
    """Insert deterministic relational data; no API setup request enters timing."""
    engine = create_async_engine(owner)
    reference = datetime.now(UTC).replace(microsecond=0)
    first_day = reference - timedelta(days=80)
    password_hash = await asyncio.to_thread(hash_password, password)
    rows: dict[str, list[dict[str, Any]]] = {
        key: []
        for key in (
            "users",
            "projects",
            "members",
            "boards",
            "columns",
            "tags",
            "tasks",
            "task_tags",
            "comments",
            "audit_events",
        )
    }
    for index in range(20):
        rows["users"].append(
            {
                "id": identity("user", index),
                "email": email(index),
                "name": f"Нагрузочный пользователь {index + 1:02d}",
                "password_hash": password_hash,
                "role_code": "pm" if index < 2 else "developer",
                "is_active": True,
                "created_at": first_day,
            }
        )
    for project in range(2):
        rows["projects"].append(
            {
                "id": identity("project", project),
                "key": f"BENCH{project + 1}",
                "name": f"Нагрузочный проект {project + 1}",
                "description": "Контрольный набор §14.2",
                "owner_id": identity("user", project),
                "timezone": "Asia/Yekaterinburg",
                "next_task_number": 1001,
                "created_at": first_day,
                "updated_at": first_day,
            }
        )
        rows["members"].extend(
            {
                "project_id": identity("project", project),
                "user_id": identity("user", user),
                "joined_at": first_day,
            }
            for user in range(20)
        )
        rows["tags"].extend(
            {
                "id": identity("tag", project * 5 + tag),
                "project_id": identity("project", project),
                "name": ["API", "Интерфейс", "Качество", "Инфраструктура", "Документация"][tag],
                "color": ["#2563EB", "#7C3AED", "#059669", "#EA580C", "#64748B"][tag],
            }
            for tag in range(5)
        )
    for board in range(4):
        project = board // 2
        rows["boards"].append(
            {
                "id": identity("board", board),
                "project_id": identity("project", project),
                "name": f"Нагрузочная доска {board + 1}",
                "revision": 500,
                "created_at": first_day,
                "updated_at": reference,
            }
        )
        rows["columns"].extend(
            {
                "id": identity("column", board * 10 + column),
                "board_id": identity("board", board),
                "name": f"Этап {column + 1}",
                "category": ("todo" if column < 3 else "in_progress" if column < 8 else "done"),
                "position": column,
                "created_at": first_day,
            }
            for column in range(10)
        )
        for position in range(500):
            task_index = board * 500 + position
            task_id = identity("task", task_index)
            column = position // 50
            created = first_day + timedelta(days=position % 50)
            deadline = (reference + timedelta(days=position % 31 - 15)).date()
            rows["tasks"].append(
                {
                    "id": task_id,
                    "project_id": identity("project", project),
                    "board_id": identity("board", board),
                    "number": (board % 2) * 500 + position + 1,
                    "title": f"Задача {task_index + 1}: проверить рабочий процесс команды",
                    "description": "Проверка API, согласование решения и приемка результата. " * 8,
                    "column_id": identity("column", board * 10 + column),
                    "position": position % 50,
                    "priority": ("low", "medium", "high")[position % 3],
                    "author_id": identity("user", position % 20),
                    "assignee_id": identity("user", position % 20),
                    "deadline": deadline,
                    "story_points": (1, 2, 3, 5, 8)[position % 5],
                    "version": 1,
                    "created_at": created,
                    "updated_at": created,
                    "deleted_at": None,
                }
            )
            for tag in (position % 5, (position + 1) % 5):
                rows["task_tags"].append(
                    {
                        "task_id": task_id,
                        "tag_id": identity("tag", project * 5 + tag),
                    }
                )
            for comment in range(2):
                comment_id = identity("comment", task_index * 2 + comment)
                rows["comments"].append(
                    {
                        "id": comment_id,
                        "task_id": task_id,
                        "author_id": identity("user", (position + comment) % 20),
                        "text": "Проверка выполнена, результаты добавлены в рабочие материалы.",
                        "created_at": created + timedelta(hours=comment + 1),
                    }
                )
            event_types = ["task.created", "comment.created", "comment.created"]
            if column >= 8:
                event_types.append("task.completed")
            for event, kind in enumerate(event_types):
                changes: list[dict[str, Any]] = []
                if kind == "task.created":
                    changes = [
                        {
                            "field": "title",
                            "old_value": None,
                            "new_value": rows["tasks"][-1]["title"],
                        }
                    ]
                elif kind == "comment.created":
                    changes = [
                        {
                            "field": "comment_id",
                            "old_value": None,
                            "new_value": str(identity("comment", task_index * 2 + event - 1)),
                        }
                    ]
                elif kind == "task.completed":
                    changes = [{"field": "is_completed", "old_value": False, "new_value": True}]
                rows["audit_events"].append(
                    {
                        "id": identity("event", task_index * 4 + event),
                        "task_id": task_id,
                        "project_id": identity("project", project),
                        "board_id": identity("board", board),
                        "operation_id": identity("operation", task_index * 4 + event),
                        "event_type": kind,
                        "changes": changes,
                        "actor_id": identity("user", position % 20),
                        "occurred_at": created + timedelta(hours=event),
                    }
                )
    tables = (
        (User, "users"),
        (Project, "projects"),
        (ProjectMember, "members"),
        (Board, "boards"),
        (Column, "columns"),
        (Tag, "tags"),
        (Task, "tasks"),
        (TaskTag, "task_tags"),
        (Comment, "comments"),
        (AuditEvent, "audit_events"),
    )
    try:
        async with engine.begin() as connection:
            for model, key in tables:
                await connection.execute(insert(model), rows[key])
        async with engine.begin() as connection:
            await connection.execute(text("ANALYZE"))
        return {key: len(value) for key, value in rows.items()}
    finally:
        await engine.dispose()


async def provision_runtime(owner: URL, runtime: URL) -> None:
    """Reproduce database-local default grants before migrations narrow audit access."""
    engine = create_async_engine(owner)
    try:
        async with engine.begin() as connection:
            for statement in (
                "REVOKE CREATE ON SCHEMA public FROM PUBLIC",
                f'GRANT USAGE ON SCHEMA public TO "{runtime.username}"',
                f'ALTER DEFAULT PRIVILEGES FOR ROLE "{owner.username}" IN SCHEMA public '
                f'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "{runtime.username}"',
                f'ALTER DEFAULT PRIVILEGES FOR ROLE "{owner.username}" IN SCHEMA public '
                f'GRANT USAGE, SELECT ON SEQUENCES TO "{runtime.username}"',
            ):
                await connection.execute(text(statement))
    finally:
        await engine.dispose()


class Client:
    def __init__(self, number: int, base_url: str, password: str) -> None:
        self.number = number
        self.password = password
        self.client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Origin": base_url},
            timeout=10,
            limits=httpx.Limits(max_connections=1, max_keepalive_connections=1),
        )
        self.version = 1
        self.csrf = ""
        self.update_count = 0

    async def login(self) -> httpx.Response:
        response = await self.client.post(
            "/api/v1/auth/login", json={"email": email(self.number), "password": self.password}
        )
        if response.status_code == 200:
            self.csrf = str(response.json()["csrf_token"])
        return response

    async def request(self, sequence: int, scheduled: float) -> Observation:
        slot = sequence * 37 % 100  # Permutation: exact mix in every 100 requests.
        board = sequence // 100 % 4
        project = board // 2
        task_index = board * 500 + (sequence * 17 % 500)
        board_path = f"/api/v1/boards/{identity('board', board)}"
        task_path = f"/api/v1/tasks/{identity('task', task_index)}"
        route = ""
        error: str | None = None
        status: int | None = None
        started = time.perf_counter()
        try:
            if slot < 60:
                if slot % 2 == 0:
                    route = "GET /boards/{id}"
                    response = await self.client.get(board_path)
                else:
                    route = "GET /tasks/{id}"
                    response = await self.client.get(task_path)
            elif slot < 80:
                route = "GET /boards/{id}/tasks (combined filters)"
                response = await self.client.get(
                    board_path + "/tasks",
                    params={
                        "assignee_id": str(identity("user", sequence % 20)),
                        "priority": ("low", "medium", "high")[sequence % 3],
                        "tag_ids": str(identity("tag", project * 5 + sequence % 5)),
                        "deadline_from": (date.today() - timedelta(days=30)).isoformat(),
                        "deadline_to": (date.today() + timedelta(days=30)).isoformat(),
                        "q": "Задача",
                    },
                )
            elif slot < 90:
                route = "PATCH /tasks/{id}"
                # Each client changes its own fixed task, so conflicts are not expected.
                self.update_count += 1
                response = await self.client.patch(
                    f"/api/v1/tasks/{identity('task', self.number)}",
                    headers={"X-CSRF-Token": self.csrf},
                    json={
                        "expected_version": self.version,
                        "title": f"Нагрузочная задача {self.number}: редакция {self.update_count}",
                    },
                )
                if response.status_code == 200:
                    self.version = int(response.json()["data"]["version"])
            elif slot < 95:
                route = "GET /projects/{id}/analytics"
                response = await self.client.get(
                    f"/api/v1/projects/{identity('project', project)}/analytics",
                    params={"period": "all"},
                )
            elif (sequence // 100 + slot) % 2 == 0:
                route = "GET /auth/me"
                response = await self.client.get("/api/v1/auth/me")
            else:
                route = "POST /auth/login"
                response = await self.login()
            status = response.status_code
            if status != 200:
                error = f"HTTP_{status}"
        except httpx.HTTPError as exc:
            error = type(exc).__name__
        except (ValueError, KeyError, TypeError):
            error = "InvalidResponse"
        finished = time.perf_counter()
        return Observation(
            sequence,
            self.number,
            route,
            status,
            (finished - started) * 1000,
            max(0, (started - scheduled) * 1000),
            error,
        )


async def phase(clients: list[Client], seconds: int) -> tuple[list[Observation], float]:
    started = time.perf_counter()

    async def run_client(client: Client) -> list[Observation]:
        result = []
        for second in range(seconds):
            scheduled = started + second + client.number / RPS
            await asyncio.sleep(max(0, scheduled - time.perf_counter()))
            result.append(await client.request(second * CLIENTS + client.number, scheduled))
        return result

    per_client = await asyncio.gather(*(run_client(client) for client in clients))
    await asyncio.sleep(max(0, started + seconds - time.perf_counter()))
    elapsed = time.perf_counter() - started
    return sorted(
        (item for group in per_client for item in group), key=lambda item: item.sequence
    ), elapsed


async def wait_ready(url: str, server: subprocess.Popen[bytes]) -> None:
    async with httpx.AsyncClient(base_url=url, timeout=1) as client:
        for _ in range(100):
            if server.poll() is not None:
                raise BenchmarkError(
                    "Benchmark API exited before readiness; inspect its local log."
                )
            try:
                response = await client.get("/api/v1/health/ready")
                if response.status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            await asyncio.sleep(0.2)
    raise BenchmarkError("Benchmark API did not become ready in 20 seconds.")


def hardware() -> dict[str, Any]:
    result: dict[str, Any] = {
        "platform": platform.platform(),
        "processor": platform.processor(),
        "logical_cpus": os.cpu_count(),
        "python": platform.python_version(),
        "resource_limits": "None; native host, client and PostgreSQL share the machine",
    }
    if os.name == "nt":
        command = (
            "$cpu=Get-CimInstance Win32_Processor; $os=Get-CimInstance Win32_OperatingSystem; "
            "[PSCustomObject]@{cpu=($cpu.Name -join ', ');cores=($cpu.NumberOfCores | "
            "Measure-Object -Sum).Sum;ram_bytes=[long]$os.TotalVisibleMemorySize*1024} | "
            "ConvertTo-Json -Compress"
        )
        process = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if process.returncode == 0:
            result.update(json.loads(process.stdout))
    return result


def source_digest() -> str:
    digest = hashlib.sha256()
    backend = PROJECT_ROOT / "backend"
    for directory in (backend / "app", backend / "migrations"):
        for path in sorted(directory.rglob("*.py")):
            digest.update(path.relative_to(backend).as_posix().encode("utf-8"))
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
    digest.update((backend / "uv.lock").read_bytes())
    return digest.hexdigest()


def git_core_ref() -> str | None:
    """Identify the latest committed server change, excluding report-only commits."""
    try:
        result = subprocess.run(
            [
                "git",
                "log",
                "-1",
                "--format=%H",
                "--",
                "app/api",
                "app/core",
                "app/db",
                "app/services",
                "app/schemas",
                "migrations",
            ],
            cwd=PROJECT_ROOT / "backend",
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    value = result.stdout.strip()
    return value if result.returncode == 0 and re.fullmatch(r"[0-9a-f]{40,64}", value) else None


def acceptance(result: dict[str, Any]) -> dict[str, bool]:
    """Make a fast HTTP percentile insufficient when scheduled load was not met."""
    overall = result["overall"]
    return {
        "zero_errors": overall["errors"] == 0 and result["warmup"]["errors"] == 0,
        "overall_p95_within_1s": overall["p95_ms"] <= 1000,
        "every_route_p95_within_1s": all(
            route["p95_ms"] <= 1000 for route in result["by_route"].values()
        ),
        "load_profile_met": (
            overall["requests"] == MEASURE_SECONDS * RPS
            and result["actual_measurement_seconds"] <= MEASURE_SECONDS + 1
            and overall["schedule_delay_p95_ms"] <= 100
            and overall["schedule_delay_max_ms"] <= 1000
        ),
        "source_unchanged_during_run": (
            result["source_sha256_before"] == result["source_sha256_after"]
        ),
    }


async def run(args: argparse.Namespace) -> dict[str, Any]:
    settings = Settings()
    if settings.database_url is None or settings.migration_database_url is None:
        raise BenchmarkError("DATABASE_URL and MIGRATION_DATABASE_URL must be configured.")
    runtime = make_url(settings.database_url.get_secret_value())
    owner = make_url(settings.migration_database_url.get_secret_value())
    validate_target(args.database_name, runtime, owner)
    runtime = runtime.set(database=args.database_name)
    owner = owner.set(database=args.database_name)
    admin = dotenv_values(args.admin_env).get("POSTGRES_ADMIN_PASSWORD")
    if not admin:
        raise BenchmarkError("Admin env file needs POSTGRES_ADMIN_PASSWORD.")
    # Detect occupied port before creating a database or starting another process.
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", args.port))
    postgres_version = await create_database(args.database_name, owner, admin)
    await provision_runtime(owner, runtime)
    base_url = f"http://127.0.0.1:{args.port}"
    environment = os.environ | {
        "APP_ENV": "test",
        "DATABASE_URL": runtime.render_as_string(hide_password=False),
        "MIGRATION_DATABASE_URL": owner.render_as_string(hide_password=False),
        "ALLOWED_ORIGINS": base_url,
        "COOKIE_SECURE": "false",
        "LOG_LEVEL": "INFO",
        "JWT_SECRET": secrets.token_urlsafe(48),
    }
    backend = PROJECT_ROOT / "backend"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    log_path = args.output.with_suffix(".log")
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    with log_path.open("wb") as log:
        migrated = await asyncio.to_thread(
            subprocess.run,
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=backend,
            env=environment,
            stdout=log,
            stderr=log,
            creationflags=creationflags,
            check=False,
        )
        if migrated.returncode:
            raise BenchmarkError("Benchmark migration failed; inspect the local log.")
        password = secrets.token_urlsafe(24)
        counts = await prepare_fixture(owner, password)
        print(
            f"Prepared {args.database_name}: {counts['tasks']} active tasks; starting API.",
            flush=True,
        )
        core_ref = await asyncio.to_thread(git_core_ref)
        source_before = source_digest()
        server = await asyncio.to_thread(
            subprocess.Popen,
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(args.port),
                "--workers",
                "1",
                "--no-access-log",
            ],
            cwd=backend,
            env=environment,
            stdout=log,
            stderr=log,
            creationflags=creationflags,
        )
        clients = [Client(number, base_url, password) for number in range(CLIENTS)]
        try:
            await wait_ready(base_url, server)
            for client in clients:
                initial = await client.login()
                if initial.status_code != 200:
                    raise BenchmarkError(
                        f"Client authentication failed (HTTP {initial.status_code})."
                    )
            print("Warmup: 30 seconds, 10 authenticated clients, 10 requests/second.", flush=True)
            warmup, warmup_elapsed = await phase(clients, WARMUP_SECONDS)
            print("Measurement: 300 seconds, all outcomes included.", flush=True)
            started_at = datetime.now(UTC).isoformat()
            observations, elapsed = await phase(clients, MEASURE_SECONDS)
        finally:
            for client in clients:
                await client.client.aclose()
            server.terminate()
            try:
                await asyncio.to_thread(server.wait, timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                await asyncio.to_thread(server.wait, timeout=5)
    return {
        "database": args.database_name,
        "base_url": base_url,
        "started_at_utc": started_at,
        "git_core_ref": core_ref,
        "source_sha256_before": source_before,
        "source_sha256_after": source_digest(),
        "request_log_level": "INFO",
        "uvicorn_access_log": False,
        "hardware": hardware(),
        "postgresql": postgres_version,
        "packages": {
            name: version(name)
            for name in ("fastapi", "sqlalchemy", "asyncpg", "uvicorn", "httpx", "pwdlib")
        },
        "fixture": counts,
        "workers": 1,
        "authenticated_clients": CLIENTS,
        "target_rps": RPS,
        "warmup_seconds": WARMUP_SECONDS,
        "measurement_seconds": MEASURE_SECONDS,
        "actual_measurement_seconds": round(elapsed, 3),
        "achieved_rps": round(len(observations) / elapsed, 3),
        "warmup": summarize(warmup) | {"actual_seconds": round(warmup_elapsed, 3)},
        "overall": summarize(observations),
        "by_route": {
            route: summarize([item for item in observations if item.route == route])
            for route in sorted({item.route for item in observations})
        },
        "observations": [asdict(item) for item in observations],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-name", required=True, help="Fresh tracker_benchmark_* database")
    parser.add_argument(
        "--admin-env",
        required=True,
        type=Path,
        help="Ignored env file with POSTGRES_ADMIN_PASSWORD",
    )
    parser.add_argument(
        "--output", required=True, type=Path, help="JSON results; use ignored work/ directory"
    )
    parser.add_argument("--port", type=int, default=8010)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("Use an unprivileged TCP port between 1024 and 65535.")
    try:
        result = asyncio.run(run(args))
    except (BenchmarkError, OSError) as exc:
        print(
            str(exc) if isinstance(exc, BenchmarkError) else "Local file/port operation failed.",
            file=sys.stderr,
        )
        return 1
    except Exception as exc:
        # Database/network exceptions can embed connection data; never echo raw messages.
        print(f"Benchmark failed ({type(exc).__name__}); no database was deleted.", file=sys.stderr)
        return 1
    result["acceptance"] = acceptance(result)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps({"output": str(args.output), "overall": result["overall"]}, ensure_ascii=False)
    )
    return 0 if all(result["acceptance"].values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
