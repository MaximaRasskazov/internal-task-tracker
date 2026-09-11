import asyncio
import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import WebSocket
from starlette.types import Message, Scope

from app.api.realtime import AccessState, Connection, Hub, SocketRejected
from app.core.config import Settings
from app.db.domain import Board
from app.db.session import Database
from app.services.events import bump_board, make_event


class ControlledHub(Hub):
    """Only the DB authorization boundary is replaced; ASGI socket state is real."""

    def __init__(self, **options: Any) -> None:
        config = Settings(_env_file=None)
        super().__init__(Database(config), config, **options)
        self.board = Board(id=uuid4(), project_id=uuid4(), revision=1)
        self.user_id = uuid4()
        self.session_id = uuid4()
        self.rejected: int | None = None
        self.checks = 0

    async def _authorize(
        self,
        token: str,
        board_id: UUID,
        previous: AccessState | None = None,
        *,
        allow_deleted: bool = False,
    ) -> AccessState:
        self.checks += 1
        if self.rejected is not None:
            raise SocketRejected(self.rejected)
        return AccessState(self.board, self.user_id, self.session_id)


class Wire:
    def __init__(
        self,
        hub: Hub,
        board_id: UUID,
        *,
        origin: str | None = "http://localhost:5173",
        cookie: str | None = "itt_session=valid-test-cookie",
        query: bytes = b"",
    ) -> None:
        self.incoming: asyncio.Queue[Message] = asyncio.Queue()
        self.outgoing: asyncio.Queue[Message] = asyncio.Queue()
        headers = [(b"host", b"localhost")]
        if origin:
            headers.append((b"origin", origin.encode()))
        if cookie:
            headers.append((b"cookie", cookie.encode()))
        scope: Scope = {
            "type": "websocket",
            "path": f"/ws/v1/boards/{board_id}",
            "query_string": query,
            "headers": headers,
        }
        self.websocket = WebSocket(scope, self.incoming.get, self.outgoing.put)
        self.incoming.put_nowait({"type": "websocket.connect"})
        self.task = asyncio.create_task(hub.serve(self.websocket, board_id))

    async def receive(self) -> Message:
        return await asyncio.wait_for(self.outgoing.get(), timeout=1)

    async def event(self) -> dict[str, Any]:
        message = await self.receive()
        assert message["type"] == "websocket.send", message
        data: dict[str, Any] = json.loads(message["text"])
        return data

    async def disconnect(self) -> None:
        self.incoming.put_nowait({"type": "websocket.disconnect", "code": 1000})
        await asyncio.wait_for(self.task, timeout=1)


@pytest.mark.parametrize(
    ("origin", "cookie", "query", "code"),
    [
        (None, "itt_session=x", b"", 4403),
        ("https://evil.example", "itt_session=x", b"", 4403),
        ("http://localhost:5173", None, b"", 4401),
        ("http://localhost:5173", "itt_session=x", b"token=x", 4403),
    ],
)
async def test_handshake_rejects_before_accept_without_database(
    origin: str | None, cookie: str | None, query: bytes, code: int
) -> None:
    hub = ControlledHub()
    wire = Wire(hub, hub.board.id, origin=origin, cookie=cookie, query=query)
    message = await wire.receive()
    assert message["type"] == "websocket.close" and message["code"] == code
    await wire.task
    assert hub.checks == 0 and not hub.connections


async def test_ready_first_buffers_events_and_checks_access_per_send() -> None:
    hub = ControlledHub()
    wire = Wire(hub, hub.board.id)
    assert (await wire.receive())["type"] == "websocket.accept"
    event = bump_board(hub.board, "task.updated", hub.user_id, uuid4(), {"task_id": uuid4()})
    hub.publish([event])
    assert (await wire.event())["type"] == "connection.ready"
    assert await wire.event() == event
    assert hub.checks >= 3  # handshake, ready, event
    await wire.disconnect()
    assert not hub.connections and not hub._handlers


async def test_database_heartbeat_repairs_a_missed_publish() -> None:
    hub = ControlledHub(heartbeat_seconds=0.01)
    wire = Wire(hub, hub.board.id)
    await wire.receive()
    assert (await wire.event())["board_revision"] == 1
    hub.board.revision = 9  # Simulate a committed DB update whose push never arrived.
    heartbeat = await wire.event()
    assert heartbeat["type"] == "heartbeat" and heartbeat["board_revision"] == 9
    assert heartbeat["actor_id"] is None and heartbeat["operation_id"] is None
    await wire.disconnect()


async def test_revoked_access_never_releases_buffered_payload() -> None:
    hub = ControlledHub()
    wire = Wire(hub, hub.board.id)
    await wire.receive()
    await wire.event()
    hub.rejected = 4403
    hub.publish([make_event(hub.board, "task.created", hub.user_id, uuid4(), {"task_id": uuid4()})])
    message = await wire.receive()
    assert message["type"] == "websocket.close" and message["code"] == 4403
    await wire.task
    assert wire.outgoing.empty()


async def test_logout_closes_immediately_without_waiting_for_heartbeat() -> None:
    hub = ControlledHub()
    wire = Wire(hub, hub.board.id)
    await wire.receive()
    await wire.event()
    await hub.revoke_session(hub.session_id)
    assert (await wire.receive())["code"] == 4401
    await wire.task


async def test_shutdown_cleans_up_senders_receivers_and_connections() -> None:
    hub = ControlledHub()
    wires = [Wire(hub, hub.board.id) for _ in range(2)]
    for wire in wires:
        await wire.receive()
        await wire.event()
    await hub.stop()
    for wire in wires:
        assert (await wire.receive())["code"] == 1001
        assert wire.task.done()
    assert not hub.connections and not hub._handlers


async def test_client_cannot_send_business_commands() -> None:
    hub = ControlledHub()
    wire = Wire(hub, hub.board.id)
    await wire.receive()
    await wire.event()
    wire.incoming.put_nowait({"type": "websocket.receive", "text": '{"type":"task.create"}'})
    assert (await wire.receive())["code"] == 1008
    await wire.task


async def test_bounded_queue_does_not_hold_up_other_recipients() -> None:
    hub = ControlledHub(queue_size=1)
    scope: Scope = {"type": "websocket", "headers": [], "query_string": b""}
    incoming: asyncio.Queue[Message] = asyncio.Queue()
    outgoing: asyncio.Queue[Message] = asyncio.Queue()
    websocket = WebSocket(scope, incoming.get, outgoing.put)
    access = AccessState(hub.board, hub.user_id, hub.session_id)
    slow = Connection(websocket, "private-token", access, asyncio.Queue(1))
    fast = Connection(websocket, "private-token", access, asyncio.Queue(4))
    unrelated = Connection(
        websocket,
        "private-token",
        AccessState(
            Board(id=uuid4(), project_id=hub.board.project_id), hub.user_id, hub.session_id
        ),
        asyncio.Queue(4),
    )
    hub.connections.update([slow, fast, unrelated])
    event = make_event(hub.board, "board.updated", hub.user_id, uuid4(), {})
    hub.publish([event, event])
    assert slow.close_requested.is_set() and slow.close_code == 1013
    assert slow.queue.qsize() == 1 and fast.queue.qsize() == 2
    assert unrelated.queue.empty() and not fast.close_requested.is_set()
    assert "private-token" not in repr(slow)


def test_events_are_json_snapshots_and_multiple_events_share_one_revision() -> None:
    board = Board(id=uuid4(), project_id=uuid4(), revision=7)
    actor, operation = uuid4(), uuid4()
    task_id = uuid4()
    event = bump_board(board, "task.updated", actor, operation, {"task_id": task_id})
    second = make_event(board, "comment.created", actor, operation, {"task_id": task_id})
    assert board.revision == 8 and event["board_revision"] == second["board_revision"] == 8
    assert event["event_id"] != second["event_id"]
    assert event["operation_id"] == second["operation_id"] == str(operation)
    assert json.loads(json.dumps(event))["payload"]["task_id"] == str(task_id)
    assert datetime.fromisoformat(event["occurred_at"]).tzinfo == UTC
    board.revision = 10
    assert event["board_revision"] == 8
