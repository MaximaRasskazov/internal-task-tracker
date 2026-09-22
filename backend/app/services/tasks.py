"""Task mutations share one locked transaction with ordering, audit, and revision.

Services never commit: HTTP commits before publishing, while the demo seed can reuse
the same rules with an explicit clock. Project/board locks serialize membership and
ordering changes; expected_version protects the user's task against lost updates.
"""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import String, cast, delete, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, ErrorDetail
from app.db.domain import (
    AuditEvent,
    Board,
    Column,
    Comment,
    ProjectMember,
    Tag,
    Task,
    TaskTag,
    User,
)
from app.schemas.domain import (
    AuditDto,
    CommentCreate,
    CommentDto,
    MutationResponse,
    PaginatedList,
    TaskCreate,
    TaskDto,
    TaskList,
    TaskMove,
    TaskPatch,
    TaskRead,
)
from app.services.access import load_board, load_task
from app.services.events import bump_board
from app.services.views import audits_dto, comment_dto, comments_dto, task_dto, tasks_dto

Event = dict[str, Any]
Change = dict[str, Any]


def invalid_reference(field_name: str) -> AppError:
    return AppError(
        422,
        "INVALID_REFERENCE",
        "Недопустимая ссылка на связанный ресурс",
        [ErrorDetail(field=field_name, message="Выберите доступный ресурс")],
    )


def _check_version(task: Task, expected_version: int) -> None:
    if task.version != expected_version:
        raise AppError(409, "VERSION_CONFLICT", "Задача уже изменена. Обновите данные")


def _change(field_name: str, old: Any, new: Any) -> Change:
    return {"field": field_name, "old_value": old, "new_value": new}


def _json_value(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    return value


async def _column(session: AsyncSession, board_id: UUID, column_id: UUID) -> Column:
    column = await session.get(Column, column_id)
    if column is None or column.board_id != board_id:
        raise invalid_reference("column_id")
    return column


async def _tags(session: AsyncSession, project_id: UUID, tag_ids: list[UUID]) -> list[Tag]:
    if not tag_ids:
        return []
    tags = list((await session.scalars(select(Tag).where(Tag.id.in_(tag_ids)))).all())
    if len(tags) != len(set(tag_ids)) or any(tag.project_id != project_id for tag in tags):
        raise invalid_reference("tag_ids")
    return sorted(tags, key=lambda tag: str(tag.id))


async def _assigned_user(
    session: AsyncSession, project_id: UUID, assignee_id: UUID | None
) -> User | None:
    if assignee_id is None:
        return None
    user = await session.scalar(
        select(User)
        .join(ProjectMember, ProjectMember.user_id == User.id)
        .where(
            User.id == assignee_id,
            User.is_active.is_(True),
            ProjectMember.project_id == project_id,
        )
    )
    if user is None:
        raise invalid_reference("assignee_id")
    return user


async def _task_tags(session: AsyncSession, task_id: UUID) -> list[Tag]:
    return list(
        (
            await session.scalars(
                select(Tag)
                .join(TaskTag, TaskTag.tag_id == Tag.id)
                .where(TaskTag.task_id == task_id)
                .order_by(Tag.id)
            )
        ).all()
    )


def _tag_values(tags: list[Tag]) -> list[dict[str, str]]:
    return [{"id": str(tag.id), "name": tag.name} for tag in tags]


def _person_value(user: User | None) -> dict[str, str] | None:
    return {"id": str(user.id), "name": user.name} if user is not None else None


def _column_value(column: Column) -> dict[str, str]:
    return {"id": str(column.id), "name": column.name}


def _audit(
    session: AsyncSession,
    task: Task,
    actor_id: UUID,
    operation_id: UUID,
    event_type: str,
    changes: list[Change],
    now: datetime,
) -> None:
    session.add(
        AuditEvent(
            id=uuid4(),
            task_id=task.id,
            project_id=task.project_id,
            board_id=task.board_id,
            actor_id=actor_id,
            operation_id=operation_id,
            event_type=event_type,
            changes=changes,
            occurred_at=now,
        )
    )


def _task_event(
    board: Board,
    task: Task,
    actor_id: UUID,
    operation_id: UUID,
    event_type: str,
    now: datetime,
) -> Event:
    payload: dict[str, Any] = {"task_id": task.id, "task_version": task.version}
    if event_type == "task.moved":
        payload["column_id"] = task.column_id
    event = bump_board(board, event_type, actor_id, operation_id, payload)
    board.updated_at = now
    return event


async def _task_response(
    session: AsyncSession, board: Board, task: Task
) -> MutationResponse[TaskDto]:
    await session.flush()
    return MutationResponse[TaskDto](
        data=await task_dto(session, task), board_id=board.id, board_revision=board.revision
    )


async def _ordered_column(session: AsyncSession, column_id: UUID) -> list[Task]:
    return list(
        (
            await session.scalars(
                select(Task)
                .where(Task.column_id == column_id, Task.deleted_at.is_(None))
                .order_by(Task.position, Task.id)
                .execution_options(populate_existing=True)
            )
        ).all()
    )


def _renumber(tasks: list[Task]) -> None:
    for position, task in enumerate(tasks):
        task.position = position


async def create_task(
    session: AsyncSession,
    board_id: UUID,
    actor_id: UUID,
    data: TaskCreate,
    *,
    now: datetime | None = None,
) -> tuple[MutationResponse[TaskDto], list[Event]]:
    now = now or datetime.now(UTC)
    project, board, _actor = await load_board(session, board_id, actor_id, lock=True)
    column = await _column(session, board.id, data.column_id)
    tags = await _tags(session, project.id, data.tag_ids)
    assignee = await _assigned_user(session, project.id, data.assignee_id)
    ordered = await _ordered_column(session, column.id)
    _renumber(ordered)
    task = Task(
        id=uuid4(),
        project_id=project.id,
        board_id=board.id,
        number=project.next_task_number,
        title=data.title,
        description=data.description,
        column_id=column.id,
        position=len(ordered),
        priority=data.priority,
        author_id=actor_id,
        assignee_id=data.assignee_id,
        deadline=data.deadline,
        story_points=data.story_points,
        version=1,
        created_at=now,
        updated_at=now,
    )
    project.next_task_number += 1
    session.add(task)
    await session.flush()
    session.add_all(TaskTag(task_id=task.id, tag_id=tag.id) for tag in tags)
    operation_id = uuid4()
    values: dict[str, Any] = {
        "title": task.title,
        "description": task.description,
        "column_id": _column_value(column),
        "position": task.position,
        "category": column.category,
        "priority": task.priority,
        "assignee_id": _person_value(assignee),
        "deadline": _json_value(task.deadline),
        "story_points": task.story_points,
        "tag_ids": _tag_values(tags),
    }
    _audit(
        session,
        task,
        actor_id,
        operation_id,
        "task.created",
        [_change(name, None, value) for name, value in values.items()],
        now,
    )
    if column.category == "done":
        _audit(
            session,
            task,
            actor_id,
            operation_id,
            "task.completed",
            [_change("category", None, "done")],
            now,
        )
    event = _task_event(board, task, actor_id, operation_id, "task.created", now)
    return await _task_response(session, board, task), [event]


async def update_task(
    session: AsyncSession,
    task_id: UUID,
    actor_id: UUID,
    data: TaskPatch,
    *,
    now: datetime | None = None,
) -> tuple[MutationResponse[TaskDto], list[Event]]:
    now = now or datetime.now(UTC)
    project, board, task, _actor = await load_task(session, task_id, actor_id, lock=True)
    _check_version(task, data.expected_version)
    changes: list[Change] = []
    supplied = data.model_dump(exclude_unset=True, exclude={"expected_version"})
    for name, value in supplied.items():
        if name == "tag_ids":
            old_tags = await _task_tags(session, task.id)
            new_tags = await _tags(session, project.id, value)
            if {tag.id for tag in old_tags} != {tag.id for tag in new_tags}:
                changes.append(_change(name, _tag_values(old_tags), _tag_values(new_tags)))
                await session.execute(delete(TaskTag).where(TaskTag.task_id == task.id))
                session.add_all(TaskTag(task_id=task.id, tag_id=tag.id) for tag in new_tags)
            continue
        old_value = getattr(task, name)
        if old_value == value:
            continue
        if name == "assignee_id":
            old_user = await session.get(User, old_value) if old_value else None
            new_user = await _assigned_user(session, project.id, value)
            changes.append(_change(name, _person_value(old_user), _person_value(new_user)))
        else:
            changes.append(_change(name, _json_value(old_value), _json_value(value)))
        setattr(task, name, value)
    if not changes:
        return await _task_response(session, board, task), []
    task.version += 1
    task.updated_at = now
    operation_id = uuid4()
    _audit(session, task, actor_id, operation_id, "task.updated", changes, now)
    event = _task_event(board, task, actor_id, operation_id, "task.updated", now)
    return await _task_response(session, board, task), [event]


async def move_task(
    session: AsyncSession,
    task_id: UUID,
    actor_id: UUID,
    data: TaskMove,
    *,
    now: datetime | None = None,
) -> tuple[MutationResponse[TaskDto], list[Event]]:
    now = now or datetime.now(UTC)
    _project, board, task, _actor = await load_task(session, task_id, actor_id, lock=True)
    _check_version(task, data.expected_version)
    target = await _column(session, board.id, data.column_id)
    source = await _column(session, board.id, task.column_id)
    if data.before_task_id == task.id:
        raise invalid_reference("before_task_id")
    if data.before_task_id is not None:
        anchor = await session.get(Task, data.before_task_id)
        if anchor is None:
            raise AppError(409, "POSITION_CONFLICT", "Положение задачи изменилось. Обновите доску")
        if anchor.board_id != board.id:
            raise invalid_reference("before_task_id")
        if anchor.deleted_at is not None or anchor.column_id != target.id:
            raise AppError(409, "POSITION_CONFLICT", "Положение задачи изменилось. Обновите доску")
    source_tasks = await _ordered_column(session, source.id)
    old_order = [item.id for item in source_tasks]
    target_tasks = (
        source_tasks if source.id == target.id else await _ordered_column(session, target.id)
    )
    new_target = [item for item in target_tasks if item.id != task.id]
    insert_at = len(new_target)
    if data.before_task_id is not None:
        insert_at = next(i for i, item in enumerate(new_target) if item.id == data.before_task_id)
    new_target.insert(insert_at, task)
    if source.id == target.id and old_order == [item.id for item in new_target]:
        return await _task_response(session, board, task), []
    old_position = task.position
    if source.id != target.id:
        _renumber([item for item in source_tasks if item.id != task.id])
    task.column_id = target.id
    _renumber(new_target)
    task.version += 1
    task.updated_at = now
    changes = []
    if source.id != target.id:
        changes.append(_change("column_id", _column_value(source), _column_value(target)))
    if old_position != task.position:
        changes.append(_change("position", old_position, task.position))
    if source.category != target.category:
        changes.append(_change("category", source.category, target.category))
    operation_id = uuid4()
    _audit(session, task, actor_id, operation_id, "task.moved", changes, now)
    transition = None
    if source.category != "done" and target.category == "done":
        transition = "task.completed"
    elif source.category == "done" and target.category != "done":
        transition = "task.reopened"
    if transition:
        _audit(
            session,
            task,
            actor_id,
            operation_id,
            transition,
            [_change("category", source.category, target.category)],
            now,
        )
    event = _task_event(board, task, actor_id, operation_id, "task.moved", now)
    return await _task_response(session, board, task), [event]


async def delete_task(
    session: AsyncSession,
    task_id: UUID,
    actor_id: UUID,
    expected_version: int,
    *,
    now: datetime | None = None,
) -> tuple[MutationResponse[None], list[Event]]:
    now = now or datetime.now(UTC)
    project, board, task, actor = await load_task(session, task_id, actor_id, lock=True)
    if actor.role_code != "admin" and actor.id not in {project.owner_id, task.author_id}:
        raise AppError(403, "FORBIDDEN", "Удалять задачу может автор или владелец проекта")
    _check_version(task, expected_version)
    task.deleted_at = now
    task.updated_at = now
    task.version += 1
    _renumber(await _ordered_column(session, task.column_id))
    operation_id = uuid4()
    _audit(
        session,
        task,
        actor_id,
        operation_id,
        "task.deleted",
        [_change("deleted_at", None, now.isoformat())],
        now,
    )
    event = _task_event(board, task, actor_id, operation_id, "task.deleted", now)
    await session.flush()
    return MutationResponse[None](data=None, board_id=board.id, board_revision=board.revision), [
        event
    ]


async def create_comment(
    session: AsyncSession,
    task_id: UUID,
    actor_id: UUID,
    data: CommentCreate,
    *,
    now: datetime | None = None,
) -> tuple[MutationResponse[CommentDto], list[Event]]:
    now = now or datetime.now(UTC)
    _project, board, task, _actor = await load_task(session, task_id, actor_id, lock=True)
    comment = Comment(
        id=uuid4(), task_id=task.id, author_id=actor_id, text=data.text, created_at=now
    )
    session.add(comment)
    operation_id = uuid4()
    _audit(
        session,
        task,
        actor_id,
        operation_id,
        "comment.created",
        [_change("comment_id", None, str(comment.id))],
        now,
    )
    event = bump_board(
        board,
        "comment.created",
        actor_id,
        operation_id,
        {"task_id": task.id, "comment_id": comment.id},
    )
    board.updated_at = now
    await session.flush()
    response = MutationResponse[CommentDto](
        data=await comment_dto(session, comment), board_id=board.id, board_revision=board.revision
    )
    return response, [event]


@dataclass(frozen=True)
class TaskFilters:
    assignee_id: str | None = None
    tag_ids: list[UUID] = field(default_factory=list)
    deadline_from: date | None = None
    deadline_to: date | None = None
    priority: list[str] = field(default_factory=list)
    column_ids: list[UUID] = field(default_factory=list)
    q: str | None = None


async def read_task(session: AsyncSession, task_id: UUID, actor_id: UUID) -> TaskRead:
    _project, board, task, _actor = await load_task(session, task_id, actor_id)
    return TaskRead(
        data=await task_dto(session, task), board_id=board.id, board_revision=board.revision
    )


async def list_tasks(
    session: AsyncSession, board_id: UUID, actor_id: UUID, filters: TaskFilters
) -> TaskList:
    project, board, _actor = await load_board(session, board_id, actor_id)
    statement = (
        select(Task)
        .join(Column, Column.id == Task.column_id)
        .where(Task.board_id == board.id, Task.deleted_at.is_(None))
        .order_by(Column.position, Task.position, Task.id)
    )
    if (
        filters.deadline_from
        and filters.deadline_to
        and filters.deadline_to < filters.deadline_from
    ):
        raise AppError(
            422,
            "VALIDATION_ERROR",
            "Конец периода раньше начала",
            [ErrorDetail(field="deadline_to", message="Дата не раньше deadline_from")],
        )
    if filters.tag_ids:
        await _tags(session, project.id, filters.tag_ids)
        for tag_id in set(filters.tag_ids):
            statement = statement.where(
                exists(
                    select(TaskTag.task_id).where(
                        TaskTag.task_id == Task.id, TaskTag.tag_id == tag_id
                    )
                )
            )
    if filters.column_ids:
        columns = (
            await session.execute(
                select(Column.id, Column.board_id).where(Column.id.in_(filters.column_ids))
            )
        ).all()
        if len(columns) != len(set(filters.column_ids)) or any(
            row.board_id != board.id for row in columns
        ):
            raise invalid_reference("column_ids")
        statement = statement.where(Task.column_id.in_(filters.column_ids))
    if filters.assignee_id == "unassigned":
        statement = statement.where(Task.assignee_id.is_(None))
    elif filters.assignee_id is not None:
        try:
            assignee_id = UUID(filters.assignee_id)
        except ValueError as exc:
            raise AppError(422, "VALIDATION_ERROR", "Некорректный исполнитель") from exc
        membership = await session.scalar(
            select(ProjectMember.user_id).where(
                ProjectMember.project_id == project.id, ProjectMember.user_id == assignee_id
            )
        )
        previously_assigned = await session.scalar(
            select(Task.id)
            .where(Task.project_id == project.id, Task.assignee_id == assignee_id)
            .limit(1)
        )
        if membership is None and previously_assigned is None:
            raise invalid_reference("assignee_id")
        statement = statement.where(Task.assignee_id == assignee_id)
    if filters.priority:
        if not set(filters.priority) <= {"low", "medium", "high"}:
            raise AppError(422, "VALIDATION_ERROR", "Некорректный приоритет")
        statement = statement.where(Task.priority.in_(filters.priority))
    if filters.deadline_from:
        statement = statement.where(Task.deadline >= filters.deadline_from)
    if filters.deadline_to:
        statement = statement.where(Task.deadline <= filters.deadline_to)
    if filters.q is not None:
        if not 1 <= len(filters.q) <= 100:
            raise AppError(
                422, "VALIDATION_ERROR", "Поисковая строка должна содержать 1–100 символов"
            )
        # Escape SQL LIKE metacharacters; search is a literal substring, not a wildcard query.
        needle = "%" + filters.q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        key = project.key + "-" + cast(Task.number, String)
        statement = statement.where(
            or_(Task.title.ilike(needle, escape="\\"), key.ilike(needle, escape="\\"))
        )
    tasks = list((await session.scalars(statement)).all())
    return TaskList(
        items=await tasks_dto(session, tasks), total=len(tasks), board_revision=board.revision
    )


async def list_comments(
    session: AsyncSession, task_id: UUID, actor_id: UUID, limit: int = 50, offset: int = 0
) -> PaginatedList[CommentDto]:
    await load_task(session, task_id, actor_id)
    total = await session.scalar(
        select(func.count()).select_from(Comment).where(Comment.task_id == task_id)
    )
    comments = list(
        (
            await session.scalars(
                select(Comment)
                .where(Comment.task_id == task_id)
                .order_by(Comment.created_at, Comment.id)
                .limit(limit)
                .offset(offset)
            )
        ).all()
    )
    items = await comments_dto(session, comments)
    return PaginatedList[CommentDto](items=items, total=total or 0, limit=limit, offset=offset)


async def list_history(
    session: AsyncSession, task_id: UUID, actor_id: UUID, limit: int = 50, offset: int = 0
) -> PaginatedList[AuditDto]:
    await load_task(session, task_id, actor_id, include_deleted=True)
    total = await session.scalar(
        select(func.count()).select_from(AuditEvent).where(AuditEvent.task_id == task_id)
    )
    audits = list(
        (
            await session.scalars(
                select(AuditEvent)
                .where(AuditEvent.task_id == task_id)
                .order_by(AuditEvent.occurred_at, AuditEvent.id)
                .limit(limit)
                .offset(offset)
            )
        ).all()
    )
    items = await audits_dto(session, audits)
    return PaginatedList[AuditDto](items=items, total=total or 0, limit=limit, offset=offset)
