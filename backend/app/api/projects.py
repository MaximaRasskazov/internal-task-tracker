"""Project and membership HTTP API."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.errors import AppError, error_responses
from app.db.domain import Project, ProjectMember, User
from app.db.reads import get_read_session
from app.db.session import get_session
from app.schemas.domain import (
    MemberCreate,
    MemberDto,
    OwnerChange,
    PaginatedList,
    ProjectCreate,
    ProjectDto,
    ProjectPatch,
)
from app.services import projects as service
from app.services.access import load_project
from app.services.views import member_dto, members_dto, project_dto, projects_dto

router = APIRouter(tags=["projects"], responses=error_responses(401, 403, 404, 409, 422, 503))
Session = Annotated[AsyncSession, Depends(get_session)]
ReadSession = Annotated[AsyncSession, Depends(get_read_session)]
Actor = Annotated[User, Depends(get_current_user)]
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


@router.get("/projects", response_model=PaginatedList[ProjectDto])
async def list_projects(
    session: ReadSession, actor: Actor, limit: Limit = 50, offset: Offset = 0
) -> PaginatedList[ProjectDto]:
    current_actor = await session.get(User, actor.id)
    if current_actor is None or not current_actor.is_active:
        raise AppError(401, "AUTH_REQUIRED", "Войдите в систему")
    statement = select(Project)
    if current_actor.role_code != "admin":
        statement = statement.join(ProjectMember, ProjectMember.project_id == Project.id).where(
            ProjectMember.user_id == actor.id
        )
    total = await session.scalar(select(func.count()).select_from(statement.subquery()))
    projects = list(
        await session.scalars(
            statement.order_by(Project.created_at.desc(), Project.id).limit(limit).offset(offset)
        )
    )
    return PaginatedList(
        items=await projects_dto(session, projects), total=total or 0, limit=limit, offset=offset
    )


@router.post("/projects", response_model=ProjectDto, status_code=201)
async def create_project(data: ProjectCreate, session: Session, actor: Actor) -> ProjectDto:
    project = await service.create_project(session, actor.id, data)
    return await project_dto(session, project)


@router.get("/projects/{project_id}", response_model=ProjectDto)
async def read_project(project_id: UUID, session: ReadSession, actor: Actor) -> ProjectDto:
    project, _ = await load_project(session, project_id, actor.id)
    return await project_dto(session, project)


@router.patch("/projects/{project_id}", response_model=ProjectDto)
async def update_project(
    project_id: UUID, data: ProjectPatch, request: Request, session: Session, actor: Actor
) -> ProjectDto:
    project = await service.update_project(session, request, actor.id, project_id, data)
    return await project_dto(session, project)


@router.delete("/projects/{project_id}", status_code=204)
async def delete_project(project_id: UUID, session: Session, actor: Actor) -> Response:
    await service.delete_project(session, actor.id, project_id)
    return Response(status_code=204)


@router.put("/projects/{project_id}/owner", response_model=ProjectDto)
async def change_owner(
    project_id: UUID, data: OwnerChange, request: Request, session: Session, actor: Actor
) -> ProjectDto:
    project = await service.change_owner(session, request, actor.id, project_id, data)
    return await project_dto(session, project)


@router.get("/projects/{project_id}/members", response_model=PaginatedList[MemberDto])
async def list_members(
    project_id: UUID, session: ReadSession, actor: Actor, limit: Limit = 50, offset: Offset = 0
) -> PaginatedList[MemberDto]:
    project, _ = await load_project(session, project_id, actor.id)
    total = await session.scalar(
        select(func.count())
        .select_from(ProjectMember)
        .where(ProjectMember.project_id == project_id)
    )
    members = list(
        await session.scalars(
            select(ProjectMember)
            .join(User, User.id == ProjectMember.user_id)
            .where(ProjectMember.project_id == project_id)
            .order_by(User.name, ProjectMember.user_id)
            .limit(limit)
            .offset(offset)
        )
    )
    return PaginatedList(
        items=await members_dto(session, members, project),
        total=total or 0,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/projects/{project_id}/members",
    response_model=MemberDto,
    status_code=201,
    responses={200: {"model": MemberDto, "description": "Пользователь уже состоит в проекте"}},
)
async def add_member(
    project_id: UUID,
    data: MemberCreate,
    request: Request,
    response: Response,
    session: Session,
    actor: Actor,
) -> MemberDto:
    project, member, created = await service.add_member(
        session, request, actor.id, project_id, data
    )
    if not created:
        response.status_code = 200
    return await member_dto(session, member, project)


@router.delete("/projects/{project_id}/members/{user_id}", status_code=204)
async def remove_member(
    project_id: UUID, user_id: UUID, request: Request, session: Session, actor: Actor
) -> Response:
    await service.remove_member(session, request, actor.id, project_id, user_id)
    return Response(status_code=204)
