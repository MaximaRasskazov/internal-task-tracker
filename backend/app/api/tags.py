"""Project tags shared by every board in a project."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.errors import error_responses
from app.db.domain import Tag, User
from app.db.reads import get_read_session
from app.db.session import get_session
from app.schemas.domain import PaginatedList, TagCreate, TagDto, TagPatch
from app.services import projects as service
from app.services.access import load_project
from app.services.views import tag_dto

router = APIRouter(tags=["tags"], responses=error_responses(401, 403, 404, 409, 422, 503))
Session = Annotated[AsyncSession, Depends(get_session)]
ReadSession = Annotated[AsyncSession, Depends(get_read_session)]
Actor = Annotated[User, Depends(get_current_user)]
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


@router.get("/projects/{project_id}/tags", response_model=PaginatedList[TagDto])
async def list_tags(
    project_id: UUID, session: ReadSession, actor: Actor, limit: Limit = 50, offset: Offset = 0
) -> PaginatedList[TagDto]:
    await load_project(session, project_id, actor.id)
    total = await session.scalar(
        select(func.count()).select_from(Tag).where(Tag.project_id == project_id)
    )
    tags = await session.scalars(
        select(Tag)
        .where(Tag.project_id == project_id)
        .order_by(Tag.name, Tag.id)
        .limit(limit)
        .offset(offset)
    )
    return PaginatedList(
        items=[tag_dto(tag) for tag in tags], total=total or 0, limit=limit, offset=offset
    )


@router.post("/projects/{project_id}/tags", response_model=TagDto, status_code=201)
async def create_tag(
    project_id: UUID, data: TagCreate, request: Request, session: Session, actor: Actor
) -> TagDto:
    return tag_dto(await service.create_tag(session, request, actor.id, project_id, data))


@router.patch("/tags/{tag_id}", response_model=TagDto)
async def update_tag(
    tag_id: UUID, data: TagPatch, request: Request, session: Session, actor: Actor
) -> TagDto:
    return tag_dto(await service.update_tag(session, request, actor.id, tag_id, data))


@router.delete("/tags/{tag_id}", status_code=204)
async def delete_tag(tag_id: UUID, request: Request, session: Session, actor: Actor) -> Response:
    await service.delete_tag(session, request, actor.id, tag_id)
    return Response(status_code=204)
