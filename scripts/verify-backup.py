"""Verify a PostgreSQL custom-format backup in a newly created database.

Run with the backend Python environment. Credentials are read from ignored files
and are passed to PostgreSQL utilities through their subprocess environment.
The source database is only read, and no database is dropped or overwritten.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import secrets
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit

import asyncpg
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


def quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def utility(name: str, pg_bin: Path | None) -> str:
    executable = name + (".exe" if os.name == "nt" else "")
    candidate = str(pg_bin / executable) if pg_bin else shutil.which(executable)
    if not candidate or not Path(candidate).is_file():
        raise RuntimeError(f"{name} is unavailable; supply --pg-bin or update PATH")
    return candidate


def run_utility(command: list[str], password: str, log_path: Path) -> None:
    environment = os.environ.copy()
    environment["PGPASSWORD"] = password
    environment["PGCONNECT_TIMEOUT"] = "10"
    result = subprocess.run(command, env=environment, capture_output=True, check=False, timeout=180)
    # Utility diagnostics may contain schema names. Keep them in ignored work/.
    log_path.write_bytes(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(f"PostgreSQL utility exited with {result.returncode}; see {log_path}")


async def fingerprint(
    connection: asyncpg.Connection,
) -> dict[str, dict[str, int | str]]:
    tables = await connection.fetch(
        "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
    )
    result = {}
    for table in tables:
        name = table["tablename"]
        row = await connection.fetchrow(
            "SELECT count(*) AS rows, "
            "md5(coalesce(string_agg(md5(row_to_json(t)::text), '' "
            "ORDER BY md5(row_to_json(t)::text)), '')) AS fingerprint "
            f"FROM public.{quote_identifier(name)} t"
        )
        result[name] = dict(row)
    return result


async def verify(args: argparse.Namespace) -> None:
    configuration = dotenv_values(args.env_file)
    owner_url = configuration.get("MIGRATION_DATABASE_URL")
    runtime_url = configuration.get("DATABASE_URL")
    if not owner_url or not runtime_url:
        raise RuntimeError("DATABASE_URL and MIGRATION_DATABASE_URL must be set")
    owner = urlsplit(owner_url)
    runtime = urlsplit(runtime_url)
    database = unquote(owner.path.lstrip("/"))
    if not database or not owner.hostname or not owner.username or not owner.password:
        raise RuntimeError("MIGRATION_DATABASE_URL must have a host, database and credentials")
    owner_name = unquote(owner.username)
    owner_password = unquote(owner.password)
    runtime_name = unquote(runtime.username or "")
    runtime_password = unquote(runtime.password or "")
    if (runtime.hostname, runtime.port, runtime.path) != (
        owner.hostname,
        owner.port,
        owner.path,
    ):
        raise RuntimeError("Runtime and migration URLs must target the same database")
    admin = dotenv_values(args.admin_env_file)
    admin_password = admin.get("POSTGRES_ADMIN_PASSWORD")
    if not admin_password:
        raise RuntimeError("Admin env file must set POSTGRES_ADMIN_PASSWORD")

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    target = f"tracker_restore_{timestamp}_{secrets.token_hex(3)}"
    output = args.output_dir / target
    output.mkdir(parents=True, exist_ok=False)
    archive = output / "tracker.dump"
    pg_dump = utility("pg_dump", args.pg_bin)
    pg_restore = utility("pg_restore", args.pg_bin)
    host_arguments = ["--host", owner.hostname, "--port", str(owner.port or 5432)]
    connection_options = {
        "host": owner.hostname,
        "port": owner.port or 5432,
        "server_settings": {"timezone": "UTC"},
    }

    source = await asyncpg.connect(
        database=database,
        user=owner_name,
        password=owner_password,
        **connection_options,
    )
    try:
        async with source.transaction(isolation="repeatable_read", readonly=True):
            snapshot = await source.fetchval("SELECT pg_export_snapshot()")
            original = await fingerprint(source)
            revision = await source.fetch(
                "SELECT version_num FROM alembic_version ORDER BY version_num"
            )
            version = await source.fetchval("SHOW server_version")
            await asyncio.to_thread(
                run_utility,
                [
                    pg_dump,
                    *host_arguments,
                    "--username",
                    owner_name,
                    "--dbname",
                    database,
                    "--format=custom",
                    "--snapshot",
                    snapshot,
                    "--lock-wait-timeout=10s",
                    "--file",
                    str(archive),
                    "--no-password",
                ],
                owner_password,
                output / "dump.log",
            )
    finally:
        await source.close()

    administrator = await asyncpg.connect(
        database="postgres",
        user=args.admin_user,
        password=admin_password,
        **connection_options,
    )
    try:
        await administrator.execute(
            f"CREATE DATABASE {quote_identifier(target)} OWNER {quote_identifier(owner_name)} "
            "TEMPLATE template0 ENCODING 'UTF8' LC_COLLATE 'C' LC_CTYPE 'C'"
        )
        await administrator.execute(
            f"REVOKE ALL ON DATABASE {quote_identifier(target)} FROM PUBLIC"
        )
        await administrator.execute(
            f"GRANT CONNECT ON DATABASE {quote_identifier(target)} "
            f"TO {quote_identifier(runtime_name)}"
        )
    finally:
        await administrator.close()

    await asyncio.to_thread(
        run_utility,
        [
            pg_restore,
            *host_arguments,
            "--username",
            owner_name,
            "--dbname",
            target,
            "--exit-on-error",
            "--single-transaction",
            "--no-password",
            str(archive),
        ],
        owner_password,
        output / "restore.log",
    )
    restored = await asyncpg.connect(
        database=target, user=owner_name, password=owner_password, **connection_options
    )
    try:
        actual = await fingerprint(restored)
        if actual != original:
            raise RuntimeError("Restored rows differ from the source snapshot")
        actual_revision = await restored.fetch(
            "SELECT version_num FROM alembic_version ORDER BY version_num"
        )
        if actual_revision != revision:
            raise RuntimeError("Restored Alembic revisions differ")
        if original.get("audit_events", {}).get("rows", 0):
            transaction = restored.transaction()
            await transaction.start()
            try:
                await restored.execute(
                    "DELETE FROM audit_events WHERE id=(SELECT id FROM audit_events LIMIT 1)"
                )
            except asyncpg.InsufficientPrivilegeError as error:
                if error.message != "audit_events is append-only":
                    raise
                audit_owner_trigger = True
            else:
                raise RuntimeError("Audit delete trigger did not reject the owner mutation")
            finally:
                await transaction.rollback()
        else:
            audit_owner_trigger = "not exercised: no audit rows"
    finally:
        await restored.close()

    app_connection = await asyncpg.connect(
        database=target,
        user=runtime_name,
        password=runtime_password,
        **connection_options,
    )
    try:
        permissions = dict(
            await app_connection.fetchrow(
                "SELECT has_schema_privilege(current_user,'public','CREATE') "
                "AS can_create_schema_objects, "
                "has_table_privilege(current_user,'tasks','INSERT') AS can_insert_tasks, "
                "has_table_privilege(current_user,'tasks','UPDATE') AS can_update_tasks, "
                "has_table_privilege(current_user,'audit_events','INSERT') AS can_insert_audit, "
                "has_table_privilege(current_user,'audit_events','UPDATE') AS can_update_audit, "
                "has_table_privilege(current_user,'audit_events','DELETE') AS can_delete_audit, "
                "has_table_privilege(current_user,'alembic_version','UPDATE') "
                "AS can_update_migration_head"
            )
        )
        expected = {
            "can_create_schema_objects": False,
            "can_insert_tasks": True,
            "can_update_tasks": True,
            "can_insert_audit": True,
            "can_update_audit": False,
            "can_delete_audit": False,
            "can_update_migration_head": False,
        }
        if permissions != expected:
            raise RuntimeError("Restored runtime permissions differ from the expected policy")
        transaction = app_connection.transaction()
        await transaction.start()
        try:
            result = await app_connection.execute(
                "UPDATE tasks SET title=title WHERE id=(SELECT id FROM tasks LIMIT 1)"
            )
            if result != "UPDATE 1":
                raise RuntimeError("Runtime write check needs at least one restored task")
        finally:
            await transaction.rollback()
    finally:
        await app_connection.close()

    summary = {
        "verified_at_utc": datetime.now(UTC).isoformat(),
        "postgresql_version": version,
        "source_database": database,
        "restore_database": target,
        "archive": str(archive),
        "archive_bytes": archive.stat().st_size,
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "alembic_heads": [row["version_num"] for row in revision],
        "tables": original,
        "all_table_counts_and_fingerprints_match": True,
        "runtime_permissions": permissions,
        "runtime_task_write_rolled_back": True,
        "audit_owner_delete_rejected": audit_owner_trigger,
    }
    summary_path = output / "verification.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Backup verified. Restored database retained: {target}")
    print(f"Evidence: {summary_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    parser.add_argument(
        "--admin-env-file", type=Path, default=ROOT / "work/install/postgres-admin.env"
    )
    parser.add_argument("--admin-user", default="postgres")
    parser.add_argument("--pg-bin", type=Path)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "work/backups")
    args = parser.parse_args()
    try:
        asyncio.run(verify(args))
    except (
        asyncpg.PostgresError,
        OSError,
        RuntimeError,
        ValueError,
        subprocess.SubprocessError,
    ) as error:
        # PostgreSQL errors can echo SQL values. Print only safe local diagnostics.
        if isinstance(error, RuntimeError):
            parser.exit(1, f"Verification failed: {error}\n")
        parser.exit(
            1,
            f"Verification failed ({type(error).__name__}); no existing database was replaced.\n",
        )


if __name__ == "__main__":
    main()
