"""Projection cost and consistent snapshots against the actual PostgreSQL transaction model."""

from collections.abc import Sequence
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from sqlalchemy import Connection, event, select, text, update
from sqlalchemy.engine import ExecutionContext
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.db.domain import Board, Column, Project, ProjectMember, Tag, Task, TaskTag, User
from app.db.reads import get_read_session
from app.services.views import tasks_dto

pytestmark = pytest.mark.integration


async def _project(db: AsyncSession, users: dict[str, User]) -> Project:
    project = Project(id=uuid4(), key="VIEWS", name="Projection checks", owner_id=users["pm"].id)
    db.add(project)
    await db.flush()
    db.add(ProjectMember(project_id=project.id, user_id=users["pm"].id))
    await db.flush()
    return project


async def test_bulk_task_projection_keeps_membership_semantics_without_n_plus_one(
    db: AsyncSession,
    users: dict[str, User],
) -> None:
    project = await _project(db, users)
    board = Board(id=uuid4(), project_id=project.id, name="Board")
    db.add(board)
    await db.flush()
    column = Column(id=uuid4(), board_id=board.id, name="Done", category="done", position=0)
    db.add(column)
    db.add_all(
        [
            ProjectMember(project_id=project.id, user_id=users["developer"].id),
            ProjectMember(project_id=project.id, user_id=users["developer_b"].id),
        ]
    )
    users["developer_b"].is_active = False
    tags = [
        Tag(id=UUID(int=2), project_id=project.id, name="Later"),
        Tag(id=UUID(int=1), project_id=project.id, name="Earlier"),
    ]
    db.add_all(tags)
    await db.flush()
    assignees = [users["developer"].id, users["outsider"].id, users["developer_b"].id, None]
    tasks = [
        Task(
            id=uuid4(),
            project_id=project.id,
            board_id=board.id,
            column_id=column.id,
            number=index + 1,
            title=f"Task {index}",
            position=index,
            author_id=users["pm"].id,
            assignee_id=assignees[index % len(assignees)],
        )
        for index in range(24)
    ]
    db.add_all(tasks)
    await db.flush()
    db.add_all([TaskTag(task_id=task.id, tag_id=tag.id) for task in tasks for tag in tags])
    await db.commit()

    selects: list[str] = []

    def capture(
        connection: Connection,
        cursor: object,
        statement: str,
        parameters: object,
        context: ExecutionContext,
        executemany: bool,
    ) -> None:
        if statement.lstrip().upper().startswith("SELECT"):
            selects.append(statement)

    binding = db.sync_session.get_bind()
    event.listen(binding, "before_cursor_execute", capture)
    try:
        results = await tasks_dto(db, tasks)
    finally:
        event.remove(binding, "before_cursor_execute", capture)

    assert len(results) == len(tasks)
    assert len(selects) <= 5, "Serializing more tasks must not issue queries per task"
    expected_membership: Sequence[bool] = [True, False, False, False]
    for index, result in enumerate(results):
        assert result.key == f"VIEWS-{index + 1}"
        assert result.tag_ids == [UUID(int=1), UUID(int=2)]
        assert result.is_completed is True
        assert result.assignee_is_project_member is expected_membership[index % 4]
        assert (result.assignee is None) == (index % 4 == 3)


async def test_read_session_retains_one_snapshot_across_concurrent_commit(
    app: FastAPI,
    db: AsyncSession,
    users: dict[str, User],
) -> None:
    project = await _project(db, users)
    await db.commit()
    request = Request({"type": "http", "app": app})
    reads = get_read_session(request)
    snapshot = await anext(reads)
    try:
        assert await snapshot.scalar(text("SHOW transaction_isolation")) == "repeatable read"
        assert await snapshot.scalar(text("SHOW transaction_read_only")) == "on"
        assert (
            await snapshot.scalar(select(Project.name).where(Project.id == project.id))
            == "Projection checks"
        )
        await db.execute(
            update(Project).where(Project.id == project.id).values(name="Concurrent update")
        )
        await db.commit()
        assert (
            await snapshot.scalar(select(Project.name).where(Project.id == project.id))
            == "Projection checks"
        )
    finally:
        await reads.aclose()
    assert (
        await db.scalar(select(Project.name).where(Project.id == project.id)) == "Concurrent update"
    )
