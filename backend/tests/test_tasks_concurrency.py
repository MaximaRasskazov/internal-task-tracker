"""Real PostgreSQL lock contention, not only two sequential stale requests."""

import asyncio
from typing import Any
from uuid import UUID

import pytest
from fastapi import FastAPI
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.domain import AuditEvent, Board, Task, User
from app.schemas.domain import TaskCreate, TaskMove, TaskPatch
from app.services.tasks import create_task, move_task, update_task
from tests import test_tasks_service as task_support
from tests.test_tasks_service import TaskBoard

pytestmark = pytest.mark.integration
task_board = task_support.task_board


async def _observe_lock_wait(app: FastAPI, blocked_pid: int, blocking_pid: int) -> None:
    """Do not assume a sleep caused overlap: PostgreSQL must report the held lock."""
    async with asyncio.timeout(3):
        async with app.state.database.sessions() as observer:
            while True:
                blockers = await observer.scalar(
                    text("SELECT pg_blocking_pids(:pid)"), {"pid": blocked_pid}
                )
                if blocking_pid in blockers:
                    return
                await asyncio.sleep(0.01)


async def test_conflicting_edits_recheck_version_after_actual_project_lock_wait(
    app: FastAPI, db: AsyncSession, users: dict[str, User], task_board: TaskBoard
) -> None:
    actor_id = users["developer"].id
    created, _ = await create_task(
        db,
        task_board.board.id,
        actor_id,
        TaskCreate(title="Before either writer", column_id=task_board.todo.id),
    )
    await db.commit()
    task_id = created.data.id
    first_has_lock = asyncio.Event()
    release_first = asyncio.Event()
    second_pid_ready = asyncio.Event()
    pids: dict[str, int] = {}

    async def first_writer() -> None:
        async with app.state.database.sessions() as session:
            pids["first"] = await session.scalar(text("SELECT pg_backend_pid()"))
            await update_task(
                session, task_id, actor_id, TaskPatch(expected_version=1, title="First winner")
            )
            first_has_lock.set()
            await release_first.wait()
            await session.commit()

    async def second_writer() -> str:
        await first_has_lock.wait()
        async with app.state.database.sessions() as session:
            pids["second"] = await session.scalar(text("SELECT pg_backend_pid()"))
            second_pid_ready.set()
            try:
                await update_task(
                    session,
                    task_id,
                    actor_id,
                    TaskPatch(expected_version=1, title="Must not overwrite"),
                )
            except AppError as exc:
                await session.rollback()
                return exc.code
            await session.commit()
            return "unexpected success"

    first = asyncio.create_task(first_writer())
    second = asyncio.create_task(second_writer())
    try:
        async with asyncio.timeout(5):
            await second_pid_ready.wait()
            await _observe_lock_wait(app, pids["second"], pids["first"])
    finally:
        release_first.set()
        await first
    assert await second == "VERSION_CONFLICT"
    db.expire_all()
    stored = await db.get(Task, task_id)
    assert stored is not None
    assert stored.title == "First winner"
    assert stored.version == 2
    events = list((await db.scalars(select(AuditEvent).where(AuditEvent.task_id == task_id))).all())
    assert sorted(event.event_type for event in events) == ["task.created", "task.updated"]
    board = await db.get(Board, created.board_id)
    assert board is not None and board.revision == created.board_revision + 1


async def test_two_tasks_moving_to_same_anchor_serialize_without_neighbor_versions(
    app: FastAPI, db: AsyncSession, users: dict[str, User], task_board: TaskBoard
) -> None:
    actor_id = users["developer"].id
    created: dict[str, Any] = {}
    for title, column in (
        ("Moving A", task_board.todo),
        ("Moving B", task_board.todo),
        ("Hidden predecessor", task_board.doing),
        ("Visible anchor", task_board.doing),
        ("Hidden successor", task_board.doing),
    ):
        result, _ = await create_task(
            db, task_board.board.id, actor_id, TaskCreate(title=title, column_id=column.id)
        )
        created[title] = result.data
    await db.commit()
    first_has_lock = asyncio.Event()
    release_first = asyncio.Event()
    second_pid_ready = asyncio.Event()
    pids: dict[str, int] = {}

    async def writer(name: str, task_id: UUID, first: bool) -> None:
        if not first:
            await first_has_lock.wait()
        async with app.state.database.sessions() as session:
            pids[name] = await session.scalar(text("SELECT pg_backend_pid()"))
            if not first:
                second_pid_ready.set()
            await move_task(
                session,
                task_id,
                actor_id,
                TaskMove(
                    column_id=task_board.doing.id,
                    before_task_id=created["Visible anchor"].id,
                    expected_version=1,
                ),
            )
            if first:
                first_has_lock.set()
                await release_first.wait()
            await session.commit()

    first = asyncio.create_task(writer("first", created["Moving A"].id, True))
    second = asyncio.create_task(writer("second", created["Moving B"].id, False))
    try:
        async with asyncio.timeout(5):
            await second_pid_ready.wait()
            await _observe_lock_wait(app, pids["second"], pids["first"])
    finally:
        release_first.set()
        await asyncio.gather(first, second)
    db.expire_all()
    stored = list(
        (
            await db.scalars(
                select(Task)
                .where(Task.board_id == created["Moving A"].board_id)
                .order_by(Task.position, Task.id)
            )
        ).all()
    )
    assert [task.title for task in stored] == [
        "Hidden predecessor",
        "Moving A",
        "Moving B",
        "Visible anchor",
        "Hidden successor",
    ]
    assert [task.position for task in stored] == list(range(5))
    assert {task.column_id for task in stored} == {created["Visible anchor"].column_id}
    for task in stored:
        if task.title.startswith("Moving"):
            assert task.version == 2
        else:
            assert task.version == 1
            assert task.updated_at == created[task.title].updated_at
    moved = list(
        (await db.scalars(select(AuditEvent).where(AuditEvent.event_type == "task.moved"))).all()
    )
    assert len(moved) == 2
    assert {event.task_id for event in moved} == {created["Moving A"].id, created["Moving B"].id}
