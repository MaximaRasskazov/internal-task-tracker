from datetime import UTC, datetime
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.domain import AuditEvent, Board, Column, Project, ProjectMember, Task, User
from app.services.analytics import project_analytics
from tests.support import login

pytestmark = pytest.mark.integration


async def make_project(db: AsyncSession, owner: User, timezone: str = "UTC") -> Project:
    project = Project(
        id=uuid4(),
        key="TEAM",
        name="Analytics",
        owner_id=owner.id,
        timezone=timezone,
        created_at=datetime(2026, 9, 1, tzinfo=UTC),
    )
    db.add(project)
    await db.flush()
    db.add(ProjectMember(project_id=project.id, user_id=owner.id))
    await db.commit()
    return project


async def add_history(
    db: AsyncSession,
    project: Project,
    board: Board,
    column: Column,
    *,
    number: int,
    completions: list[datetime],
    deleted: bool = False,
) -> Task:
    task = Task(
        id=uuid4(),
        project_id=project.id,
        board_id=board.id,
        column_id=column.id,
        number=number,
        position=number - 1,
        author_id=project.owner_id,
        title=f"Task {number}",
        deleted_at=datetime(2026, 9, 11, tzinfo=UTC) if deleted else None,
    )
    db.add(task)
    await db.flush()
    db.add_all(
        [
            AuditEvent(
                task_id=task.id,
                project_id=project.id,
                board_id=board.id,
                actor_id=project.owner_id,
                operation_id=uuid4(),
                event_type="task.completed",
                occurred_at=completed,
                changes=[],
            )
            for completed in completions
        ]
    )
    return task


async def test_first_completion_survives_reopening_recompletion_and_soft_delete(
    db: AsyncSession,
    users: dict[str, User],
) -> None:
    project = await make_project(db, users["pm"])
    board = Board(id=uuid4(), project_id=project.id, name="Board")
    db.add(board)
    await db.flush()
    column = Column(id=uuid4(), board_id=board.id, name="Done", category="done", position=0)
    db.add(column)
    await db.flush()
    await add_history(
        db,
        project,
        board,
        column,
        number=1,
        deleted=True,
        completions=[datetime(2026, 9, 1, 12, tzinfo=UTC), datetime(2026, 9, 3, 12, tzinfo=UTC)],
    )
    await add_history(
        db,
        project,
        board,
        column,
        number=2,
        completions=[datetime(2026, 9, 3, 12, tzinfo=UTC), datetime(2026, 9, 10, 12, tzinfo=UTC)],
    )
    await db.commit()
    report = await project_analytics(db, project, "week", now=datetime(2026, 9, 3, 18, tzinfo=UTC))
    values = {row.date.isoformat(): row.completed_count for row in report.completion_over_time}
    assert values["2026-09-01"] == 1
    assert values["2026-09-02"] == 0
    assert values["2026-09-03"] == 1
    assert sum(values.values()) == 2
    assert report.status_distribution[0].count == 1
    column.name = "Renamed completed"
    await db.commit()
    later = await project_analytics(db, project, "week", now=datetime(2026, 9, 11, 12, tzinfo=UTC))
    assert sum(row.completed_count for row in later.completion_over_time) == 0
    assert later.status_distribution[0].column_name == "Renamed completed"
    assert later.status_distribution[0].count == 1


async def test_timezone_midnight_and_zero_columns_are_distinct_per_board(
    db: AsyncSession,
    users: dict[str, User],
) -> None:
    project = await make_project(db, users["pm"], "Asia/Yekaterinburg")
    boards = [Board(id=uuid4(), project_id=project.id, name=f"Board {i}") for i in range(2)]
    db.add_all(boards)
    await db.flush()
    columns = [
        Column(id=uuid4(), board_id=board.id, name="Done", category="done", position=0)
        for board in boards
    ]
    db.add_all(columns)
    await db.flush()
    await add_history(
        db,
        project,
        boards[0],
        columns[0],
        number=1,
        completions=[datetime(2026, 9, 1, 18, 59, 59, tzinfo=UTC)],
    )
    await add_history(
        db,
        project,
        boards[0],
        columns[0],
        number=2,
        completions=[datetime(2026, 9, 1, 19, tzinfo=UTC)],
    )
    await db.commit()
    report = await project_analytics(db, project, "week", now=datetime(2026, 9, 2, 12, tzinfo=UTC))
    values = {row.date.isoformat(): row.completed_count for row in report.completion_over_time}
    assert values["2026-09-01"] == 1 and values["2026-09-02"] == 1
    assert len(report.status_distribution) == 2
    assert sorted(row.count for row in report.status_distribution) == [0, 2]
    assert len({row.column_id for row in report.status_distribution}) == 2
    assert {row.column_name for row in report.status_distribution} == {"Done"}


async def test_empty_project_api_default_alias_period_validation_and_access(
    client: AsyncClient,
    db: AsyncSession,
    users: dict[str, User],
) -> None:
    project = await make_project(db, users["pm"])
    await login(client, users["pm"])
    response = await client.get(f"/api/v1/projects/{project.id}/analytics")
    assert response.status_code == 200, response.text
    report = response.json()
    assert report["period"] == "month"
    assert "from" in report and "date_from" not in report
    assert report["status_distribution"] == []
    assert len(report["completion_over_time"]) == 30
    assert sum(row["completed_count"] for row in report["completion_over_time"]) == 0
    invalid = await client.get(f"/api/v1/projects/{project.id}/analytics?period=year")
    assert invalid.status_code == 422
    await login(client, users["outsider"])
    denied = await client.get(f"/api/v1/projects/{project.id}/analytics")
    assert denied.status_code == 404
    assert "Analytics" not in denied.text
