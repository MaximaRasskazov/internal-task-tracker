"""Recheck database permissions and lock nested resources in Project → Board → Task order."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.domain import Board, Column, Project, ProjectMember, Task, User


def not_found() -> AppError:
    return AppError(404, "NOT_FOUND", "Ресурс не найден")


async def load_project(
    session: AsyncSession,
    project_id: UUID,
    actor_id: UUID,
    *,
    manage: bool = False,
    lock: bool = False,
) -> tuple[Project, User]:
    query = (
        select(Project).where(Project.id == project_id).execution_options(populate_existing=True)
    )
    if lock:
        query = query.with_for_update()
    project = await session.scalar(query)
    if project is None:
        raise not_found()

    actor_query = select(User).where(User.id == actor_id).execution_options(populate_existing=True)
    if lock:
        # Serialize current permissions against concurrent global role changes.
        actor_query = actor_query.with_for_update(read=True)
    actor = await session.scalar(actor_query)
    if actor is None or not actor.is_active:
        raise AppError(401, "AUTH_REQUIRED", "Войдите в систему")
    if actor.role_code != "admin":
        membership = await session.scalar(
            select(ProjectMember.user_id).where(
                ProjectMember.project_id == project_id, ProjectMember.user_id == actor_id
            )
        )
        if membership is None:
            raise not_found()
        if manage and project.owner_id != actor_id:
            raise AppError(403, "FORBIDDEN", "Недостаточно прав")
    return project, actor


async def load_board(
    session: AsyncSession,
    board_id: UUID,
    actor_id: UUID,
    *,
    manage: bool = False,
    lock: bool = False,
) -> tuple[Project, Board, User]:
    project_id = await session.scalar(select(Board.project_id).where(Board.id == board_id))
    if project_id is None:
        raise not_found()
    project, actor = await load_project(session, project_id, actor_id, manage=manage, lock=lock)
    query = select(Board).where(Board.id == board_id).execution_options(populate_existing=True)
    if lock:
        query = query.with_for_update()
    board = await session.scalar(query)
    if board is None or board.project_id != project.id:
        raise not_found()
    return project, board, actor


async def load_task(
    session: AsyncSession,
    task_id: UUID,
    actor_id: UUID,
    *,
    manage: bool = False,
    lock: bool = False,
    include_deleted: bool = False,
) -> tuple[Project, Board, Task, User]:
    board_id = await session.scalar(select(Task.board_id).where(Task.id == task_id))
    if board_id is None:
        raise not_found()
    project, board, actor = await load_board(session, board_id, actor_id, manage=manage, lock=lock)
    query = select(Task).where(Task.id == task_id).execution_options(populate_existing=True)
    if lock:
        query = query.with_for_update()
    task = await session.scalar(query)
    if (
        task is None
        or task.project_id != project.id
        or task.board_id != board.id
        or (task.deleted_at is not None and not include_deleted)
    ):
        raise not_found()
    column_board_id = await session.scalar(
        select(Column.board_id).where(Column.id == task.column_id)
    )
    if column_board_id != board.id:
        raise not_found()
    return project, board, task, actor
