"""Task routes; all user changes commit before any event reaches a websocket."""

from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.errors import error_responses
from app.db.domain import User
from app.db.reads import get_read_session
from app.db.session import get_session
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
from app.services import tasks
from app.services.events import commit_and_publish

router = APIRouter(tags=["tasks"], responses=error_responses(401, 403, 404, 409, 422, 503))
Session = Annotated[AsyncSession, Depends(get_session)]
ReadSession = Annotated[AsyncSession, Depends(get_read_session)]
Actor = Annotated[User, Depends(get_current_user)]
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


@router.get("/boards/{board_id}/tasks", response_model=TaskList)
async def list_board_tasks(
    board_id: UUID,
    session: ReadSession,
    actor: Actor,
    assignee_id: str | None = None,
    tag_ids: Annotated[list[UUID] | None, Query()] = None,
    deadline_from: date | None = None,
    deadline_to: date | None = None,
    priority: Annotated[list[Literal["low", "medium", "high"]] | None, Query()] = None,
    column_ids: Annotated[list[UUID] | None, Query()] = None,
    q: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
) -> TaskList:
    return await tasks.list_tasks(
        session,
        board_id,
        actor.id,
        tasks.TaskFilters(
            assignee_id,
            tag_ids or [],
            deadline_from,
            deadline_to,
            [str(value) for value in priority or []],
            column_ids or [],
            q,
        ),
    )


@router.post("/boards/{board_id}/tasks", response_model=MutationResponse[TaskDto], status_code=201)
async def create_board_task(
    board_id: UUID, data: TaskCreate, request: Request, session: Session, actor: Actor
) -> MutationResponse[TaskDto]:
    result, events = await tasks.create_task(session, board_id, actor.id, data)
    await commit_and_publish(session, request, events)
    return result


@router.get("/tasks/{task_id}", response_model=TaskRead)
async def get_task(task_id: UUID, session: ReadSession, actor: Actor) -> TaskRead:
    return await tasks.read_task(session, task_id, actor.id)


@router.patch("/tasks/{task_id}", response_model=MutationResponse[TaskDto])
async def patch_task(
    task_id: UUID, data: TaskPatch, request: Request, session: Session, actor: Actor
) -> MutationResponse[TaskDto]:
    result, events = await tasks.update_task(session, task_id, actor.id, data)
    await commit_and_publish(session, request, events)
    return result


@router.post("/tasks/{task_id}/move", response_model=MutationResponse[TaskDto])
async def move_task(
    task_id: UUID, data: TaskMove, request: Request, session: Session, actor: Actor
) -> MutationResponse[TaskDto]:
    result, events = await tasks.move_task(session, task_id, actor.id, data)
    await commit_and_publish(session, request, events)
    return result


@router.delete("/tasks/{task_id}", response_model=MutationResponse[None])
async def delete_task(
    task_id: UUID,
    request: Request,
    session: Session,
    actor: Actor,
    expected_version: Annotated[int, Query(ge=1)],
) -> MutationResponse[None]:
    result, events = await tasks.delete_task(session, task_id, actor.id, expected_version)
    await commit_and_publish(session, request, events)
    return result


@router.get("/tasks/{task_id}/comments", response_model=PaginatedList[CommentDto])
async def list_comments(
    task_id: UUID, session: ReadSession, actor: Actor, limit: Limit = 50, offset: Offset = 0
) -> PaginatedList[CommentDto]:
    return await tasks.list_comments(session, task_id, actor.id, limit, offset)


@router.post(
    "/tasks/{task_id}/comments", response_model=MutationResponse[CommentDto], status_code=201
)
async def create_comment(
    task_id: UUID, data: CommentCreate, request: Request, session: Session, actor: Actor
) -> MutationResponse[CommentDto]:
    result, events = await tasks.create_comment(session, task_id, actor.id, data)
    await commit_and_publish(session, request, events)
    return result


@router.get("/tasks/{task_id}/history", response_model=PaginatedList[AuditDto])
async def list_history(
    task_id: UUID, session: ReadSession, actor: Actor, limit: Limit = 50, offset: Offset = 0
) -> PaginatedList[AuditDto]:
    return await tasks.list_history(session, task_id, actor.id, limit, offset)
