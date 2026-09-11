from datetime import date, timedelta
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from pydantic import SecretStr
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cli import seed
from app.cli.seed import SeedError, seed_data, seed_database, seed_id
from app.core.config import Settings
from app.core.security import hash_password
from app.db.domain import AuditEvent, Board, Column, Comment, Project, ProjectMember, Task, User
from app.schemas.domain import TaskPatch
from app.services.tasks import update_task

REFERENCE_DATE = date(2026, 9, 11)


@pytest.mark.parametrize("invalid_env", ["production", "unknown"])
async def test_seed_refuses_unsafe_environment_before_accessing_database(invalid_env: str) -> None:
    settings = Settings(_env_file=None).model_copy(
        update={"app_env": invalid_env, "demo_password": SecretStr("test-password-long-enough")}
    )
    session = AsyncMock(spec=AsyncSession)
    with pytest.raises(SeedError, match="allowed only"):
        await seed_data(session, settings, REFERENCE_DATE)
    session.execute.assert_not_awaited()


@pytest.mark.parametrize("password", [None, SecretStr("too-short")])
async def test_seed_requires_explicit_sufficient_demo_password(password: SecretStr | None) -> None:
    settings = Settings(_env_file=None).model_copy(update={"demo_password": password})
    session = AsyncMock(spec=AsyncSession)
    with pytest.raises(SeedError, match="DEMO_PASSWORD"):
        await seed_data(session, settings, REFERENCE_DATE)
    session.execute.assert_not_awaited()


@pytest.mark.integration
async def test_seed_contains_acceptance_dataset_and_service_generated_history(
    db: AsyncSession, app: FastAPI
) -> None:
    summary = await seed_data(db, app.state.settings, REFERENCE_DATE)
    await db.commit()
    assert (summary.created_users, summary.created_projects, summary.created_tasks) == (6, 2, 22)
    assert not summary.preserved_existing_dataset
    assert await db.scalar(select(func.count()).select_from(User)) == 6
    assert await db.scalar(select(func.count()).select_from(Board)) == 3
    assert await db.scalar(select(func.count()).select_from(Comment)) == 6

    team_tasks = list(
        await db.scalars(select(Task).where(Task.project_id == seed_id("project:TEAM")))
    )
    assert len(team_tasks) == 20
    assert all(task.deleted_at is None and "Демо" in task.title for task in team_tasks)
    assert {task.priority for task in team_tasks} == {"low", "medium", "high"}
    assert {task.assignee_id for task in team_tasks} == {
        seed_id("user:dev-a"),
        seed_id("user:dev-b"),
        None,
    }
    assert {None, 0, 1, 2, 3, 5, 8} == {task.story_points for task in team_tasks}
    assert {None, REFERENCE_DATE, REFERENCE_DATE - timedelta(days=2)} <= {
        task.deadline for task in team_tasks
    }
    assert (
        await db.scalar(
            select(func.count())
            .select_from(Task)
            .join(Column, Column.id == Task.column_id)
            .where(Task.project_id == seed_id("project:TEAM"), Column.category == "done")
        )
        == 8
    )
    memberships = set(
        await db.scalars(
            select(ProjectMember.user_id).where(ProjectMember.project_id == seed_id("project:TEAM"))
        )
    )
    assert memberships == {seed_id(f"user:{handle}") for handle in ("pm", "dev-a", "dev-b")}
    assert seed_id("user:outsider") not in memberships

    events = list(await db.scalars(select(AuditEvent)))
    assert sum(event.event_type == "task.created" for event in events) == 22
    assert sum(event.event_type == "task.completed" for event in events) == 12
    assert sum(event.event_type == "task.reopened" for event in events) == 4
    assert any(event.event_type == "task.updated" for event in events)
    assert all(event.occurred_at.date() <= REFERENCE_DATE for event in events)
    repeated = [task.id for task in team_tasks if task.number % 5 == 4]
    for task_id in repeated:
        timeline = sorted(
            (
                event
                for event in events
                if event.task_id == task_id
                and event.event_type in {"task.completed", "task.reopened"}
            ),
            key=lambda event: event.occurred_at,
        )
        assert [event.event_type for event in timeline] == [
            "task.completed",
            "task.reopened",
            "task.completed",
        ]


@pytest.mark.integration
async def test_rerun_preserves_password_roles_edits_and_historical_dates(
    db: AsyncSession, app: FastAPI
) -> None:
    await seed_data(db, app.state.settings, REFERENCE_DATE)
    await db.commit()
    developer = await db.get(User, seed_id("user:dev-a"))
    assert developer is not None
    changed_password = hash_password("changed-demo-password-long-enough")
    developer.password_hash = changed_password
    developer.role_code = "pm"
    first_task = await db.scalar(select(Task).order_by(Task.id).limit(1))
    assert first_task is not None
    actor = "pm" if first_task.project_id == seed_id("project:TEAM") else "pm-private"
    await update_task(
        db,
        first_task.id,
        seed_id(f"user:{actor}"),
        TaskPatch(expected_version=first_task.version, title="Отредактировано участником команды"),
    )
    await db.commit()
    before_tasks = list(
        await db.execute(
            select(Task.id, Task.title, Task.version, Task.created_at, Task.updated_at)
        )
    )
    before_audit = list(await db.execute(select(AuditEvent.id, AuditEvent.occurred_at)))
    changed_settings = app.state.settings.model_copy(
        update={"demo_password": SecretStr("different-seed-password-long-enough")}
    )
    summary = await seed_data(db, changed_settings, REFERENCE_DATE + timedelta(days=100))
    await db.commit()
    assert summary.preserved_existing_dataset
    assert (summary.created_users, summary.created_projects, summary.created_tasks) == (0, 0, 0)
    assert set(before_tasks) == set(
        await db.execute(
            select(Task.id, Task.title, Task.version, Task.created_at, Task.updated_at)
        )
    )
    assert set(before_audit) == set(await db.execute(select(AuditEvent.id, AuditEvent.occurred_at)))
    await db.refresh(developer)
    assert developer.password_hash == changed_password
    assert developer.role_code == "pm"


@pytest.mark.integration
async def test_seed_refuses_to_take_over_an_existing_account(
    db: AsyncSession, app: FastAPI
) -> None:
    existing = User(
        name="Existing account",
        email="admin@example.test",
        role_code="developer",
        password_hash=hash_password("existing-account-password-long-enough"),
    )
    db.add(existing)
    await db.commit()
    identity = existing.id
    with pytest.raises(SeedError, match="outside this demo dataset"):
        await seed_data(db, app.state.settings, REFERENCE_DATE)
    await db.rollback()
    preserved = await db.get(User, identity)
    assert preserved is not None and preserved.role_code == "developer"
    assert await db.scalar(select(func.count()).select_from(User)) == 1
    assert await db.scalar(select(func.count()).select_from(Project)) == 0


@pytest.mark.integration
async def test_seed_rolls_back_users_projects_and_audit_if_task_service_fails(
    db: AsyncSession, app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_create = seed.create_task
    calls = 0

    async def fail_after_first_task(*args: object, **kwargs: object) -> object:
        nonlocal calls
        calls += 1
        if calls > 1:
            raise SeedError("Injected seed task failure")
        return await real_create(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(seed, "create_task", fail_after_first_task)
    with pytest.raises(SeedError, match="Injected"):
        await seed_database(app.state.settings, REFERENCE_DATE)
    assert calls == 2
    for model in (User, Project, Task, AuditEvent):
        assert await db.scalar(select(func.count()).select_from(model)) == 0
