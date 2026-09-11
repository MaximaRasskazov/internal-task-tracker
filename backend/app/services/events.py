"""Revision changes belong to the transaction; socket delivery begins only after commit."""

import logging
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.domain import Board, Project

logger = logging.getLogger(__name__)
type Event = dict[str, Any]


def make_event(
    board: Board,
    event_type: str,
    actor_id: UUID | None,
    operation_id: UUID | None,
    payload: dict[str, Any],
) -> Event:
    """Build an immutable wire snapshot; additional events may share one revision."""
    return {
        "event_id": str(uuid4()),
        "type": event_type,
        "project_id": str(board.project_id),
        "board_id": str(board.id),
        "board_revision": board.revision,
        "occurred_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "actor_id": str(actor_id) if actor_id else None,
        "operation_id": str(operation_id) if operation_id else None,
        "payload": jsonable_encoder(payload),
    }


def bump_board(
    board: Board,
    event_type: str,
    actor_id: UUID,
    operation_id: UUID,
    payload: dict[str, Any],
) -> Event:
    """The caller already holds Project → Board locks, exactly once per operation."""
    board.revision += 1
    board.updated_at = datetime.now(UTC)
    return make_event(board, event_type, actor_id, operation_id, payload)


async def bump_project(
    session: AsyncSession,
    project: Project,
    event_type: str,
    actor_id: UUID,
    operation_id: UUID,
    payload: dict[str, Any],
) -> list[Event]:
    """The project is locked by the caller; acquire all boards in one stable order."""
    project.updated_at = datetime.now(UTC)
    boards = await session.scalars(
        select(Board)
        .where(Board.project_id == project.id)
        .order_by(Board.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    return [bump_board(board, event_type, actor_id, operation_id, payload) for board in boards]


async def commit_and_publish(
    session: AsyncSession, request: Request, events: Iterable[Event]
) -> None:
    """Never hold the SQL transaction while waiting for a network recipient."""
    messages = list(events)
    await session.flush()
    await session.commit()
    hub = getattr(request.app.state, "event_hub", None)
    if hub is not None and messages:
        try:
            # publish only enqueues. A missed push is repaired by the database heartbeat.
            hub.publish(messages)
        except Exception:
            # Do not turn a committed write into a retryable HTTP error or log payloads.
            logger.error("event_publish_failed count=%d", len(messages))
