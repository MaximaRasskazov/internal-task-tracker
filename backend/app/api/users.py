"""Administrative account directory and serialized global role changes."""

import logging
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, or_, select

from app.api.auth import user_dto
from app.api.dependencies import CurrentUser, SessionDependency
from app.core.errors import AppError, error_responses
from app.db.domain import User
from app.db.models import Role
from app.schemas.domain import PaginatedList, UserDto

router = APIRouter(prefix="/users", tags=["Users"])
logger = logging.getLogger(__name__)


class ChangeRoleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["admin", "pm", "developer"]


@router.get("", response_model=PaginatedList[UserDto], responses=error_responses(401, 403))
async def list_users(
    user: CurrentUser,
    session: SessionDependency,
    q: Annotated[str, Query(max_length=254)] = "",
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PaginatedList[UserDto]:
    if user.role_code != "admin":
        raise AppError(403, "FORBIDDEN", "Недостаточно прав")
    escaped = q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    criteria = or_(
        User.name.ilike(f"%{escaped}%", escape="\\"),
        User.email.ilike(f"%{escaped}%", escape="\\"),
    )
    total = await session.scalar(select(func.count()).select_from(User).where(criteria))
    users = await session.scalars(
        select(User).where(criteria).order_by(User.name, User.id).limit(limit).offset(offset)
    )
    return PaginatedList[UserDto](
        items=[user_dto(item) for item in users], total=total or 0, limit=limit, offset=offset
    )


@router.patch(
    "/{user_id}/role",
    response_model=UserDto,
    responses=error_responses(401, 403, 404, 409),
)
async def change_role(
    user_id: UUID,
    body: ChangeRoleRequest,
    request: Request,
    user: CurrentUser,
    session: SessionDependency,
) -> UserDto:
    # Every role mutation takes this single lock, including promotions and no-ops.
    await session.scalar(select(Role).where(Role.code == "admin").with_for_update())
    initiator = await session.scalar(
        select(User).where(User.id == user.id).execution_options(populate_existing=True)
    )
    if initiator is None or not initiator.is_active or initiator.role_code != "admin":
        raise AppError(403, "FORBIDDEN", "Недостаточно прав")
    if user_id == initiator.id:
        raise AppError(403, "FORBIDDEN", "Нельзя менять собственную роль")
    target = await session.scalar(
        select(User)
        .where(User.id == user_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if target is None:
        raise AppError(404, "NOT_FOUND", "Пользователь не найден")
    if target.role_code == body.role:
        await session.commit()
        return user_dto(target)
    if target.role_code == "admin" and target.is_active and body.role != "admin":
        others = await session.scalar(
            select(func.count())
            .select_from(User)
            .where(User.role_code == "admin", User.is_active.is_(True), User.id != target.id)
        )
        if not others:
            raise AppError(409, "LAST_ADMIN", "Нельзя убрать последнего администратора")
    target.role_code = body.role
    await session.commit()
    hub = getattr(request.app.state, "event_hub", None)
    if hub is not None:
        try:
            await hub.revalidate_user(target.id)
        except Exception:
            logger.error("WebSocket user notification failed after role change")
    return user_dto(target)
