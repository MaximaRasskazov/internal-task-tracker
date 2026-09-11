from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUser
from app.core.errors import error_responses
from app.db.reads import get_read_session
from app.services.access import load_project
from app.services.analytics import AnalyticsDto, Period, project_analytics

router = APIRouter(tags=["analytics"])


@router.get(
    "/projects/{project_id}/analytics",
    response_model=AnalyticsDto,
    responses=error_responses(401, 404, 503),
)
async def get_project_analytics(
    project_id: UUID,
    actor: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_read_session)],
    period: Annotated[Period, Query()] = "month",
) -> AnalyticsDto:
    project, _ = await load_project(session, project_id, actor.id)
    return await project_analytics(session, project, period)
