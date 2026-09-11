"""Boards, consistent full-board snapshots, and column structure."""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.errors import error_responses
from app.db.domain import Board, Column, ProjectMember, Tag, Task, User
from app.db.reads import get_read_session
from app.db.session import get_session
from app.schemas.domain import (
    BoardCreate,
    BoardDto,
    BoardPatch,
    BoardSnapshot,
    ColumnCreate,
    ColumnDto,
    ColumnOrder,
    ColumnPatch,
    MutationResponse,
    PaginatedList,
)
from app.services import projects as service
from app.services.access import load_board, load_project
from app.services.views import (
    board_dto,
    column_dto,
    members_dto,
    project_dto,
    tag_dto,
    tasks_dto,
)

router = APIRouter(tags=["boards"], responses=error_responses(401, 403, 404, 409, 422, 503))
Session = Annotated[AsyncSession, Depends(get_session)]
ReadSession = Annotated[AsyncSession, Depends(get_read_session)]
Actor = Annotated[User, Depends(get_current_user)]
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


@router.get("/projects/{project_id}/boards", response_model=PaginatedList[BoardDto])
async def list_boards(
    project_id: UUID, session: ReadSession, actor: Actor, limit: Limit = 50, offset: Offset = 0
) -> PaginatedList[BoardDto]:
    await load_project(session, project_id, actor.id)
    total = await session.scalar(
        select(func.count()).select_from(Board).where(Board.project_id == project_id)
    )
    boards = await session.scalars(
        select(Board)
        .where(Board.project_id == project_id)
        .order_by(Board.created_at, Board.id)
        .limit(limit)
        .offset(offset)
    )
    return PaginatedList(
        items=[board_dto(board) for board in boards], total=total or 0, limit=limit, offset=offset
    )


@router.post("/projects/{project_id}/boards", response_model=BoardDto, status_code=201)
async def create_board(
    project_id: UUID, data: BoardCreate, request: Request, session: Session, actor: Actor
) -> BoardDto:
    return board_dto(await service.create_board(session, request, actor.id, project_id, data))


@router.get("/boards/{board_id}", response_model=BoardSnapshot)
async def read_board(board_id: UUID, session: ReadSession, actor: Actor) -> BoardSnapshot:
    project, board, _ = await load_board(session, board_id, actor.id)
    columns = list(
        await session.scalars(
            select(Column).where(Column.board_id == board_id).order_by(Column.position, Column.id)
        )
    )
    tasks = list(
        await session.scalars(
            select(Task)
            .join(Column, Column.id == Task.column_id)
            .where(Task.board_id == board_id, Task.deleted_at.is_(None))
            .order_by(Column.position, Task.position, Task.id)
        )
    )
    members = list(
        await session.scalars(
            select(ProjectMember)
            .join(User, User.id == ProjectMember.user_id)
            .where(ProjectMember.project_id == project.id)
            .order_by(User.name, ProjectMember.user_id)
        )
    )
    tags = await session.scalars(
        select(Tag).where(Tag.project_id == project.id).order_by(Tag.name, Tag.id)
    )
    return BoardSnapshot(
        board=board_dto(board),
        project=await project_dto(session, project),
        revision=board.revision,
        server_time=datetime.now(UTC),
        columns=[column_dto(column) for column in columns],
        tasks=await tasks_dto(session, tasks),
        members=await members_dto(session, members, project),
        tags=[tag_dto(tag) for tag in tags],
    )


@router.patch("/boards/{board_id}", response_model=MutationResponse[BoardDto])
async def update_board(
    board_id: UUID, data: BoardPatch, request: Request, session: Session, actor: Actor
) -> MutationResponse[BoardDto]:
    board = await service.update_board(session, request, actor.id, board_id, data)
    return MutationResponse(data=board_dto(board), board_id=board.id, board_revision=board.revision)


@router.delete("/boards/{board_id}", status_code=204)
async def delete_board(
    board_id: UUID, request: Request, session: Session, actor: Actor
) -> Response:
    await service.delete_board(session, request, actor.id, board_id)
    return Response(status_code=204)


@router.post(
    "/boards/{board_id}/columns", response_model=MutationResponse[ColumnDto], status_code=201
)
async def create_column(
    board_id: UUID, data: ColumnCreate, request: Request, session: Session, actor: Actor
) -> MutationResponse[ColumnDto]:
    board, column = await service.create_column(session, request, actor.id, board_id, data)
    return MutationResponse(
        data=column_dto(column), board_id=board.id, board_revision=board.revision
    )


@router.patch("/columns/{column_id}", response_model=MutationResponse[ColumnDto])
async def update_column(
    column_id: UUID, data: ColumnPatch, request: Request, session: Session, actor: Actor
) -> MutationResponse[ColumnDto]:
    board, column = await service.update_column(session, request, actor.id, column_id, data)
    return MutationResponse(
        data=column_dto(column), board_id=board.id, board_revision=board.revision
    )


@router.delete("/columns/{column_id}", status_code=204)
async def delete_column(
    column_id: UUID, request: Request, session: Session, actor: Actor
) -> Response:
    await service.delete_column(session, request, actor.id, column_id)
    return Response(status_code=204)


@router.put("/boards/{board_id}/columns/order", response_model=MutationResponse[list[ColumnDto]])
async def reorder_columns(
    board_id: UUID, data: ColumnOrder, request: Request, session: Session, actor: Actor
) -> MutationResponse[list[ColumnDto]]:
    board, columns = await service.reorder_columns(session, request, actor.id, board_id, data)
    return MutationResponse(
        data=[column_dto(column) for column in columns],
        board_id=board.id,
        board_revision=board.revision,
    )
