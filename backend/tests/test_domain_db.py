"""Real PostgreSQL constraints and audit retention, independent of API validation."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import delete, select, text, update
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.db.domain import AuditEvent, Board, Column, Project, ProjectMember, Tag, Task, User

if TYPE_CHECKING:
    from tests.conftest import DatabaseUrls

pytestmark = pytest.mark.integration


@dataclass(frozen=True)
class DomainGraph:
    project: Project
    other_project: Project
    board: Board
    column: Column
    other_column: Column
    task: Task


async def _project(db: AsyncSession, owner: User, key: str) -> Project:
    project = Project(key=key, name=f"Project {key}", owner_id=owner.id)
    db.add(project)
    await db.flush()
    db.add(ProjectMember(project_id=project.id, user_id=owner.id))
    await db.flush()
    return project


@pytest.fixture
async def domain_graph(db: AsyncSession, users: dict[str, User]) -> DomainGraph:
    project = await _project(db, users["pm"], "DOMAIN")
    other_project = await _project(db, users["second_pm"], "OTHER")
    board = Board(project_id=project.id, name="Primary board")
    other_board = Board(project_id=project.id, name="Other board")
    db.add_all([board, other_board])
    await db.flush()
    column = Column(board_id=board.id, name="Todo", category="todo", position=0)
    other_column = Column(board_id=other_board.id, name="Todo", category="todo", position=0)
    db.add_all([column, other_column])
    await db.flush()
    task = Task(
        project_id=project.id,
        board_id=board.id,
        number=1,
        title="Constraint test",
        column_id=column.id,
        position=0,
        author_id=users["pm"].id,
    )
    db.add(task)
    await db.commit()
    return DomainGraph(project, other_project, board, column, other_column, task)


async def test_owner_membership_can_be_added_before_commit(
    db: AsyncSession, users: dict[str, User]
) -> None:
    project = await _project(db, users["pm"], "DEFER")
    await db.commit()
    assert await db.get(ProjectMember, (project.id, users["pm"].id)) is not None


async def test_owner_without_membership_is_rejected_at_commit(
    db: AsyncSession, users: dict[str, User]
) -> None:
    db.add(Project(key="ORPHAN", name="Missing owner membership", owner_id=users["pm"].id))
    await db.flush()
    with pytest.raises(IntegrityError) as failure:
        await db.commit()
    assert getattr(failure.value.orig, "sqlstate", None) == "23503"
    await db.rollback()


async def test_owner_membership_cannot_be_removed(
    db: AsyncSession, domain_graph: DomainGraph
) -> None:
    await db.execute(
        delete(ProjectMember).where(
            ProjectMember.project_id == domain_graph.project.id,
            ProjectMember.user_id == domain_graph.project.owner_id,
        )
    )
    with pytest.raises(IntegrityError) as failure:
        await db.commit()
    assert getattr(failure.value.orig, "sqlstate", None) == "23503"
    await db.rollback()


async def test_tag_names_are_normalized_and_unique_inside_project(
    db: AsyncSession, domain_graph: DomainGraph
) -> None:
    tag = Tag(project_id=domain_graph.project.id, name=" Planning ")
    db.add(tag)
    await db.commit()
    assert await db.scalar(select(Tag.normalized_name).where(Tag.id == tag.id)) == "planning"

    db.add(Tag(project_id=domain_graph.other_project.id, name="planning"))
    await db.commit()
    db.add(Tag(project_id=domain_graph.project.id, name="pLaNnInG"))
    with pytest.raises(IntegrityError) as failure:
        await db.flush()
    assert getattr(failure.value.orig, "sqlstate", None) == "23505"
    await db.rollback()


@pytest.mark.parametrize("mismatch", ["project", "column"])
async def test_task_references_must_belong_to_same_project_and_board(
    db: AsyncSession, domain_graph: DomainGraph, mismatch: str
) -> None:
    statement = update(Task).where(Task.id == domain_graph.task.id)
    if mismatch == "project":
        statement = statement.values(project_id=domain_graph.other_project.id)
    else:
        statement = statement.values(column_id=domain_graph.other_column.id)
    with pytest.raises(IntegrityError) as failure:
        await db.execute(statement)
    assert getattr(failure.value.orig, "sqlstate", None) == "23503"
    await db.rollback()


async def test_runtime_has_only_read_and_insert_privileges_for_audit(db: AsyncSession) -> None:
    privileges = (
        await db.execute(
            text(
                "SELECT "
                "has_table_privilege(current_user, 'audit_events', 'SELECT'), "
                "has_table_privilege(current_user, 'audit_events', 'INSERT'), "
                "has_table_privilege(current_user, 'audit_events', 'UPDATE'), "
                "has_table_privilege(current_user, 'audit_events', 'DELETE'), "
                "has_table_privilege(current_user, 'audit_events', 'TRUNCATE'), "
                "current_user = pg_get_userbyid(relowner) "
                "FROM pg_class WHERE oid = 'audit_events'::regclass"
            )
        )
    ).one()
    assert tuple(privileges) == (True, True, False, False, False, False)


@pytest.mark.parametrize("principal", ["runtime", "owner"])
@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE audit_events SET event_type = 'task.updated'",
        "DELETE FROM audit_events",
        "TRUNCATE TABLE audit_events",
    ],
    ids=["update", "delete", "truncate"],
)
async def test_audit_mutations_are_denied_even_for_table_owner(
    db: AsyncSession,
    domain_graph: DomainGraph,
    _isolated_database: "DatabaseUrls",
    principal: str,
    statement: str,
) -> None:
    event = AuditEvent(
        task_id=domain_graph.task.id,
        project_id=domain_graph.project.id,
        board_id=domain_graph.board.id,
        event_type="task.created",
        changes=[],
        actor_id=domain_graph.project.owner_id,
    )
    db.add(event)
    await db.commit()
    event_id = event.id
    url = _isolated_database.runtime if principal == "runtime" else _isolated_database.owner
    engine = create_async_engine(url, poolclass=NullPool)
    try:
        with pytest.raises(DBAPIError) as failure:
            async with engine.begin() as connection:
                await connection.execute(text(statement))
        assert getattr(failure.value.orig, "sqlstate", None) == "42501"
        if principal == "owner":
            assert "append-only" in str(failure.value.orig)
    finally:
        await engine.dispose()
    assert await db.scalar(select(AuditEvent.event_type).where(AuditEvent.id == event_id)) == (
        "task.created"
    )
