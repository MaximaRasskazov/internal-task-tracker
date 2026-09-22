"""Project container operations; the project lock serializes all related mutations."""

import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import Request
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.domain import Board, Column, Project, ProjectMember, Tag, Task, TaskTag, User
from app.schemas.domain import (
    BoardCreate,
    BoardPatch,
    ColumnCreate,
    ColumnOrder,
    ColumnPatch,
    MemberCreate,
    OwnerChange,
    ProjectCreate,
    ProjectPatch,
    TagCreate,
    TagPatch,
)
from app.services.access import load_board, load_project
from app.services.events import bump_board, bump_project, commit_and_publish

logger = logging.getLogger(__name__)


def now() -> datetime:
    return datetime.now(UTC)


async def create_project(session: AsyncSession, actor_id: UUID, data: ProjectCreate) -> Project:
    actor = await session.scalar(
        select(User)
        .where(User.id == actor_id)
        .with_for_update(read=True)
        .execution_options(populate_existing=True)
    )
    if actor is None or not actor.is_active:
        raise AppError(401, "AUTH_REQUIRED", "Войдите в систему")
    if actor.role_code not in {"admin", "pm"}:
        raise AppError(403, "FORBIDDEN", "Создавать проекты могут руководители и администраторы")
    project = await session.scalar(
        insert(Project)
        .values(id=uuid4(), owner_id=actor.id, **data.model_dump())
        .on_conflict_do_nothing(index_elements=[Project.key])
        .returning(Project)
    )
    if project is None:
        raise AppError(409, "DUPLICATE_KEY", "Этот ключ проекта уже используется")
    session.add(ProjectMember(project_id=project.id, user_id=actor.id))
    await session.flush()
    await session.commit()
    return project


async def update_project(
    session: AsyncSession,
    request: Request,
    actor_id: UUID,
    project_id: UUID,
    data: ProjectPatch,
) -> Project:
    project, _ = await load_project(session, project_id, actor_id, manage=True, lock=True)
    changes = data.model_dump(exclude_unset=True)
    if all(getattr(project, field) == value for field, value in changes.items()):
        return project
    for field, value in changes.items():
        setattr(project, field, value)
    project.updated_at = now()
    events = await bump_project(session, project, "project.updated", actor_id, uuid4(), {})
    await commit_and_publish(session, request, events)
    return project


async def delete_project(session: AsyncSession, actor_id: UUID, project_id: UUID) -> None:
    project, _ = await load_project(session, project_id, actor_id, manage=True, lock=True)
    boards_exist = await session.scalar(
        select(Board.id).where(Board.project_id == project_id).limit(1)
    )
    tags_exist = await session.scalar(select(Tag.id).where(Tag.project_id == project_id).limit(1))
    if boards_exist or tags_exist:
        raise AppError(409, "PROJECT_NOT_EMPTY", "Сначала удалите доски и теги проекта")
    await session.execute(delete(ProjectMember).where(ProjectMember.project_id == project_id))
    await session.delete(project)
    await session.commit()


async def change_owner(
    session: AsyncSession,
    request: Request,
    actor_id: UUID,
    project_id: UUID,
    data: OwnerChange,
) -> Project:
    project, _ = await load_project(session, project_id, actor_id, manage=True, lock=True)
    target = await session.scalar(
        select(User)
        .join(ProjectMember, ProjectMember.user_id == User.id)
        .where(
            ProjectMember.project_id == project_id,
            User.id == data.user_id,
            User.is_active.is_(True),
        )
    )
    if target is None:
        raise AppError(
            422, "INVALID_REFERENCE", "Новый руководитель должен быть активным участником"
        )
    if project.owner_id == target.id:
        return project
    project.owner_id = target.id
    project.updated_at = now()
    events = await bump_project(session, project, "project.updated", actor_id, uuid4(), {})
    await commit_and_publish(session, request, events)
    return project


async def add_member(
    session: AsyncSession,
    request: Request,
    actor_id: UUID,
    project_id: UUID,
    data: MemberCreate,
) -> tuple[Project, ProjectMember, bool]:
    project, _ = await load_project(session, project_id, actor_id, manage=True, lock=True)
    user = await session.scalar(
        select(User).where(User.email == str(data.email).strip().lower(), User.is_active.is_(True))
    )
    if user is None:
        raise AppError(422, "INVALID_REFERENCE", "Пользователь должен сначала зарегистрироваться")
    member = await session.get(ProjectMember, (project_id, user.id))
    if member is not None:
        return project, member, False
    member = ProjectMember(project_id=project_id, user_id=user.id)
    session.add(member)
    project.updated_at = now()
    events = await bump_project(session, project, "project.members_changed", actor_id, uuid4(), {})
    await commit_and_publish(session, request, events)
    return project, member, True


async def remove_member(
    session: AsyncSession,
    request: Request,
    actor_id: UUID,
    project_id: UUID,
    user_id: UUID,
) -> None:
    project, _ = await load_project(session, project_id, actor_id, manage=True, lock=True)
    if project.owner_id == user_id:
        raise AppError(409, "OWNER_REQUIRED", "Сначала передайте руководство другому участнику")
    member = await session.get(ProjectMember, (project_id, user_id))
    if member is None:
        return
    await session.delete(member)
    project.updated_at = now()
    events = await bump_project(session, project, "project.members_changed", actor_id, uuid4(), {})
    await commit_and_publish(session, request, events)
    hub = getattr(request.app.state, "event_hub", None)
    if hub is not None:
        try:
            await hub.revalidate_user(user_id)
        except Exception:
            # The persisted removal remains successful. Per-send checks and heartbeat
            # still revoke stale sockets; no exception details or user data are logged.
            logger.error("membership_socket_revalidation_failed")


async def create_board(
    session: AsyncSession,
    request: Request,
    actor_id: UUID,
    project_id: UUID,
    data: BoardCreate,
) -> Board:
    project, _ = await load_project(session, project_id, actor_id, manage=True, lock=True)
    project.updated_at = now()
    # Lock and bump existing boards before inserting a new one; its initial revision is zero.
    events = await bump_project(session, project, "project.updated", actor_id, uuid4(), {})
    board = Board(project_id=project_id, name=data.name)
    session.add(board)
    await session.flush()
    for position, (name, category) in enumerate(
        [("К выполнению", "todo"), ("В работе", "in_progress"), ("Готово", "done")]
    ):
        session.add(Column(board_id=board.id, name=name, category=category, position=position))
    await commit_and_publish(session, request, events)
    return board


async def update_board(
    session: AsyncSession,
    request: Request,
    actor_id: UUID,
    board_id: UUID,
    data: BoardPatch,
) -> Board:
    _, board, _ = await load_board(session, board_id, actor_id, manage=True, lock=True)
    if board.name == data.name:
        return board
    board.name = data.name
    event = bump_board(board, "board.updated", actor_id, uuid4(), {})
    await commit_and_publish(session, request, [event])
    return board


async def delete_board(
    session: AsyncSession, request: Request, actor_id: UUID, board_id: UUID
) -> None:
    project_id = await session.scalar(select(Board.project_id).where(Board.id == board_id))
    if project_id is None:
        raise AppError(404, "NOT_FOUND", "Доска не найдена")
    project, _ = await load_project(session, project_id, actor_id, manage=True, lock=True)
    # A board-count change touches all boards. Acquire them in one globally sorted order.
    boards = list(
        await session.scalars(
            select(Board)
            .where(Board.project_id == project.id)
            .order_by(Board.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    )
    board = next((item for item in boards if item.id == board_id), None)
    if board is None:
        raise AppError(404, "NOT_FOUND", "Доска не найдена")
    column_id = await session.scalar(select(Column.id).where(Column.board_id == board_id).limit(1))
    if column_id is not None:
        raise AppError(409, "BOARD_NOT_EMPTY", "Сначала удалите все колонки доски")
    project.updated_at = now()
    operation_id = uuid4()
    events = [
        bump_board(
            item,
            "board.deleted" if item.id == board_id else "project.updated",
            actor_id,
            operation_id,
            {},
        )
        for item in boards
    ]
    await session.delete(board)
    await commit_and_publish(session, request, events)


async def create_column(
    session: AsyncSession,
    request: Request,
    actor_id: UUID,
    board_id: UUID,
    data: ColumnCreate,
) -> tuple[Board, Column]:
    _, board, _ = await load_board(session, board_id, actor_id, manage=True, lock=True)
    count = await session.scalar(
        select(func.count()).select_from(Column).where(Column.board_id == board_id)
    )
    column = Column(board_id=board_id, position=count or 0, **data.model_dump())
    session.add(column)
    await session.flush()
    event = bump_board(board, "column.created", actor_id, uuid4(), {"column_id": str(column.id)})
    await commit_and_publish(session, request, [event])
    return board, column


async def load_column(
    session: AsyncSession, actor_id: UUID, column_id: UUID
) -> tuple[Board, Column]:
    board_id = await session.scalar(select(Column.board_id).where(Column.id == column_id))
    if board_id is None:
        raise AppError(404, "NOT_FOUND", "Колонка не найдена")
    _, board, _ = await load_board(session, board_id, actor_id, manage=True, lock=True)
    column = await session.scalar(
        select(Column)
        .where(Column.id == column_id, Column.board_id == board.id)
        .execution_options(populate_existing=True)
    )
    if column is None:
        raise AppError(404, "NOT_FOUND", "Колонка не найдена")
    return board, column


async def update_column(
    session: AsyncSession,
    request: Request,
    actor_id: UUID,
    column_id: UUID,
    data: ColumnPatch,
) -> tuple[Board, Column]:
    board, column = await load_column(session, actor_id, column_id)
    if column.name == data.name:
        return board, column
    column.name = data.name
    event = bump_board(board, "column.updated", actor_id, uuid4(), {"column_id": str(column.id)})
    await commit_and_publish(session, request, [event])
    return board, column


async def delete_column(
    session: AsyncSession, request: Request, actor_id: UUID, column_id: UUID
) -> None:
    board, column = await load_column(session, actor_id, column_id)
    task_id = await session.scalar(select(Task.id).where(Task.column_id == column_id).limit(1))
    if task_id is not None:
        raise AppError(
            409, "COLUMN_NOT_EMPTY", "Колонка содержит задачи или сохраненную историю задач"
        )
    await session.delete(column)
    remaining = await session.scalars(
        select(Column)
        .where(Column.board_id == board.id, Column.id != column_id)
        .order_by(Column.position, Column.id)
    )
    for position, item in enumerate(remaining):
        item.position = position
    event = bump_board(board, "column.deleted", actor_id, uuid4(), {"column_id": str(column_id)})
    await commit_and_publish(session, request, [event])


async def reorder_columns(
    session: AsyncSession,
    request: Request,
    actor_id: UUID,
    board_id: UUID,
    data: ColumnOrder,
) -> tuple[Board, list[Column]]:
    _, board, _ = await load_board(session, board_id, actor_id, manage=True, lock=True)
    if board.revision != data.expected_revision:
        raise AppError(
            409, "VERSION_CONFLICT", "Доска изменилась. Обновите ее и повторите действие"
        )
    columns = list(
        await session.scalars(
            select(Column).where(Column.board_id == board_id).order_by(Column.position, Column.id)
        )
    )
    by_id = {item.id: item for item in columns}
    if len(data.column_ids) != len(set(data.column_ids)) or set(data.column_ids) != set(by_id):
        raise AppError(
            422, "INVALID_REFERENCE", "Перечислите каждую текущую колонку доски один раз"
        )
    if [item.id for item in columns] == data.column_ids:
        return board, columns
    ordered = [by_id[column_id] for column_id in data.column_ids]
    for position, column in enumerate(ordered):
        column.position = position
    event = bump_board(
        board,
        "columns.reordered",
        actor_id,
        uuid4(),
        {"column_ids": [str(column_id) for column_id in data.column_ids]},
    )
    await commit_and_publish(session, request, [event])
    return board, ordered


async def create_tag(
    session: AsyncSession,
    request: Request,
    actor_id: UUID,
    project_id: UUID,
    data: TagCreate,
) -> Tag:
    project, _ = await load_project(session, project_id, actor_id, lock=True)
    await check_tag_name(session, project_id, data.name)
    tag = Tag(project_id=project_id, **data.model_dump())
    session.add(tag)
    await session.flush()
    project.updated_at = now()
    events = await bump_project(
        session, project, "tag.created", actor_id, uuid4(), {"tag_id": str(tag.id)}
    )
    await commit_and_publish(session, request, events)
    return tag


async def check_tag_name(
    session: AsyncSession, project_id: UUID, name: str, excluding_id: UUID | None = None
) -> None:
    # Use PostgreSQL lower() to match the computed uniqueness key for every Unicode name.
    statement = select(Tag.id).where(
        Tag.project_id == project_id, Tag.normalized_name == func.lower(func.btrim(name))
    )
    if excluding_id is not None:
        statement = statement.where(Tag.id != excluding_id)
    if await session.scalar(statement) is not None:
        raise AppError(409, "DUPLICATE_TAG", "Тег с таким именем уже существует в проекте")


async def load_tag(session: AsyncSession, actor_id: UUID, tag_id: UUID) -> tuple[Project, Tag]:
    project_id = await session.scalar(select(Tag.project_id).where(Tag.id == tag_id))
    if project_id is None:
        raise AppError(404, "NOT_FOUND", "Тег не найден")
    project, _ = await load_project(session, project_id, actor_id, manage=True, lock=True)
    tag = await session.scalar(
        select(Tag).where(Tag.id == tag_id).execution_options(populate_existing=True)
    )
    if tag is None:
        raise AppError(404, "NOT_FOUND", "Тег не найден")
    return project, tag


async def update_tag(
    session: AsyncSession,
    request: Request,
    actor_id: UUID,
    tag_id: UUID,
    data: TagPatch,
) -> Tag:
    project, tag = await load_tag(session, actor_id, tag_id)
    changes = data.model_dump(exclude_unset=True)
    if all(getattr(tag, field) == value for field, value in changes.items()):
        return tag
    if "name" in changes:
        await check_tag_name(session, project.id, changes["name"], excluding_id=tag.id)
    for field, value in changes.items():
        setattr(tag, field, value)
    project.updated_at = now()
    events = await bump_project(
        session, project, "tag.updated", actor_id, uuid4(), {"tag_id": str(tag.id)}
    )
    await commit_and_publish(session, request, events)
    return tag


async def delete_tag(session: AsyncSession, request: Request, actor_id: UUID, tag_id: UUID) -> None:
    project, tag = await load_tag(session, actor_id, tag_id)
    if await session.scalar(select(TaskTag.task_id).where(TaskTag.tag_id == tag_id).limit(1)):
        raise AppError(409, "TAG_IN_USE", "Тег используется задачами, включая удаленные")
    await session.delete(tag)
    project.updated_at = now()
    events = await bump_project(
        session, project, "tag.deleted", actor_id, uuid4(), {"tag_id": str(tag_id)}
    )
    await commit_and_publish(session, request, events)
