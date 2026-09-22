"""Real app/auth/PostgreSQL with ASGI websocket frames on the fixture's event loop."""

import asyncio
import json
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.types import Message, Scope

from app.db.domain import AuthSession, Board, User
from tests.support import ORIGIN, login

pytestmark = pytest.mark.integration


class ApplicationWire:
    def __init__(
        self, app: FastAPI, board_id: str, cookie: str | None, origin: str = ORIGIN
    ) -> None:
        self.incoming: asyncio.Queue[Message] = asyncio.Queue()
        self.outgoing: asyncio.Queue[Message] = asyncio.Queue()
        headers = [(b"host", b"localhost:5173"), (b"origin", origin.encode())]
        if cookie:
            headers.append((b"cookie", f"itt_session={cookie}".encode()))
        scope: Scope = {
            "type": "websocket",
            "asgi": {"version": "3.0", "spec_version": "2.4"},
            "scheme": "ws",
            "http_version": "1.1",
            "path": f"/ws/v1/boards/{board_id}",
            "raw_path": f"/ws/v1/boards/{board_id}".encode(),
            "query_string": b"",
            "root_path": "",
            "headers": headers,
            "client": ("127.0.0.1", 12345),
            "server": ("localhost", 5173),
            "subprotocols": [],
        }
        self.incoming.put_nowait({"type": "websocket.connect"})
        self.task = asyncio.create_task(app(scope, self.incoming.get, self.outgoing.put))

    async def receive(self) -> Message:
        return await asyncio.wait_for(self.outgoing.get(), timeout=5)

    async def event(self) -> dict[str, Any]:
        message = await self.receive()
        assert message["type"] == "websocket.send", message
        return json.loads(message["text"])

    async def close(self) -> None:
        self.incoming.put_nowait({"type": "websocket.disconnect", "code": 1000})
        try:
            await asyncio.wait_for(self.task, timeout=5)
        finally:
            if not self.task.done():
                self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)


@asynccontextmanager
async def connected(app: FastAPI, board_id: str, cookie: str):
    wire = ApplicationWire(app, board_id, cookie)
    try:
        accepted = await wire.receive()
        assert accepted["type"] == "websocket.accept", accepted
        ready = await wire.event()
        assert ready["type"] == "connection.ready" and ready["board_id"] == board_id
        yield wire
    finally:
        await wire.close()


async def setup_board(client: AsyncClient, users: dict[str, User]) -> tuple[str, str, str]:
    await login(client, users["pm"])
    response = await client.post("/api/v1/projects", json={"key": "TEAM", "name": "Realtime"})
    assert response.status_code == 201, response.text
    project_id = response.json()["id"]
    response = await client.post(f"/api/v1/projects/{project_id}/boards", json={"name": "Board"})
    assert response.status_code == 201, response.text
    board_id = response.json()["id"]
    snapshot = await client.get(f"/api/v1/boards/{board_id}")
    assert snapshot.status_code == 200, snapshot.text
    return project_id, board_id, snapshot.json()["columns"][0]["id"]


async def test_authenticated_two_clients_receive_committed_event_then_membership_revocation(
    app: FastAPI,
    client: AsyncClient,
    users: dict[str, User],
) -> None:
    project_id, board_id, column_id = await setup_board(client, users)
    added = await client.post(
        f"/api/v1/projects/{project_id}/members", json={"email": users["developer"].email}
    )
    assert added.status_code == 201, added.text
    owner_cookie = client.cookies["itt_session"]
    await login(client, users["developer"])
    developer_cookie = client.cookies["itt_session"]
    async with (
        connected(app, board_id, owner_cookie) as owner,
        connected(app, board_id, developer_cookie) as developer,
    ):
        response = await client.post(
            f"/api/v1/boards/{board_id}/tasks",
            json={"title": "Committed before push", "column_id": column_id},
        )
        assert response.status_code == 201, response.text
        first, second = await owner.event(), await developer.event()
        assert first == second
        assert first["type"] == "task.created"
        assert first["board_revision"] == response.json()["board_revision"]
        snapshot = await client.get(f"/api/v1/boards/{board_id}")
        assert first["payload"]["task_id"] in {task["id"] for task in snapshot.json()["tasks"]}
        await login(client, users["pm"])
        removed = await client.delete(
            f"/api/v1/projects/{project_id}/members/{users['developer'].id}"
        )
        assert removed.status_code == 204, removed.text
        denied = await developer.receive()
        assert denied["type"] == "websocket.close" and denied["code"] == 4403
        assert (await owner.event())["type"] == "project.members_changed"


async def test_invalid_auth_origin_and_outsider_are_rejected_before_accept(
    app: FastAPI,
    client: AsyncClient,
    users: dict[str, User],
) -> None:
    _, board_id, _ = await setup_board(client, users)
    owner_cookie = client.cookies["itt_session"]
    await login(client, users["outsider"])
    for cookie, origin in [
        (None, ORIGIN),
        ("invalid.jwt.signature", ORIGIN),
        (owner_cookie, "https://untrusted.example"),
        (client.cookies["itt_session"], ORIGIN),
    ]:
        wire = ApplicationWire(app, board_id, cookie, origin)
        try:
            first = await wire.receive()
            assert first["type"] == "websocket.close"
            assert not wire.outgoing.qsize()
        finally:
            await wire.close()


async def test_logout_closes_current_authenticated_websocket(
    app: FastAPI,
    client: AsyncClient,
    users: dict[str, User],
) -> None:
    _, board_id, _ = await setup_board(client, users)
    async with connected(app, board_id, client.cookies["itt_session"]) as wire:
        response = await client.post("/api/v1/auth/logout")
        assert response.status_code == 204, response.text
        closed = await wire.receive()
        assert closed["type"] == "websocket.close" and closed["code"] == 4401


async def test_deleted_board_emits_final_revision_then_closes(
    app: FastAPI,
    client: AsyncClient,
    users: dict[str, User],
) -> None:
    _, board_id, _ = await setup_board(client, users)
    snapshot = await client.get(f"/api/v1/boards/{board_id}")
    for column in snapshot.json()["columns"]:
        removed = await client.delete(f"/api/v1/columns/{column['id']}")
        assert removed.status_code == 204, removed.text
    async with connected(app, board_id, client.cookies["itt_session"]) as wire:
        response = await client.delete(f"/api/v1/boards/{board_id}")
        assert response.status_code == 204, response.text
        event = await wire.event()
        assert event["type"] == "board.deleted" and event["board_revision"] >= 1
        assert event["payload"] == {}
        closed = await wire.receive()
        assert closed["type"] == "websocket.close" and closed["code"] == 4404
        assert (await client.get(f"/api/v1/boards/{board_id}")).status_code == 404


async def test_heartbeat_reads_committed_revision_and_database_session_expiry(
    app: FastAPI,
    client: AsyncClient,
    db: AsyncSession,
    users: dict[str, User],
) -> None:
    _, board_id, _ = await setup_board(client, users)
    app.state.event_hub.heartbeat_seconds = 0.03
    async with connected(app, board_id, client.cookies["itt_session"]) as wire:
        # Commit without publishing: the heartbeat must discover the database revision.
        await db.execute(update(Board).where(Board.id == UUID(board_id)).values(revision=11))
        await db.commit()
        async with asyncio.timeout(3):
            while True:
                event = await wire.event()
                assert event["type"] == "heartbeat"
                if event["board_revision"] == 11:
                    break
        session_id = next(iter(app.state.event_hub.connections)).access.session_id
        now = datetime.now(UTC)
        await db.execute(
            update(AuthSession)
            .where(AuthSession.id == session_id)
            .values(created_at=now - timedelta(hours=1), expires_at=now - timedelta(seconds=1))
        )
        await db.commit()
        async with asyncio.timeout(3):
            while True:
                message = await wire.receive()
                if message["type"] == "websocket.close":
                    assert message["code"] == 4401
                    break
