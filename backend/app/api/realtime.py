"""Single-worker board notifications with bounded, independently authorized recipients."""

import asyncio
import logging
from collections.abc import Iterable
from contextlib import suppress
from dataclasses import dataclass, field
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import SESSION_COOKIE, authenticate_token
from app.db.domain import Board
from app.db.session import Database
from app.services.access import load_project
from app.services.events import Event, make_event

logger = logging.getLogger(__name__)
router = APIRouter()


class SocketRejected(Exception):
    def __init__(self, code: int) -> None:
        self.code = code


@dataclass(frozen=True)
class AccessState:
    board: Board
    user_id: UUID
    session_id: UUID


@dataclass(eq=False)
class Connection:
    websocket: WebSocket
    token: str = field(repr=False)
    access: AccessState
    queue: asyncio.Queue[Event]
    close_requested: asyncio.Event = field(default_factory=asyncio.Event)
    close_code: int = 1000

    def request_close(self, code: int) -> None:
        if not self.close_requested.is_set():
            self.close_code = code
            self.close_requested.set()


class Hub:
    """One in-memory hub per ASGI app; use one Uvicorn worker until adding a broker."""

    def __init__(
        self,
        database: Database,
        settings: Settings,
        *,
        heartbeat_seconds: float = 15,
        queue_size: int = 128,
        send_timeout_seconds: float = 3,
    ) -> None:
        if heartbeat_seconds <= 0 or queue_size <= 0 or send_timeout_seconds <= 0:
            raise ValueError("Hub limits must be positive")
        self.database = database
        self.settings = settings
        self.heartbeat_seconds = heartbeat_seconds
        self.queue_size = queue_size
        self.send_timeout_seconds = send_timeout_seconds
        self.connections: set[Connection] = set()
        self._handlers: set[asyncio.Task[None]] = set()
        self._stopping = False

    async def start(self) -> None:
        self._stopping = False

    async def stop(self) -> None:
        self._stopping = True
        for connection in tuple(self.connections):
            connection.request_close(1001)
        handlers = tuple(self._handlers)
        if handlers:
            _, pending = await asyncio.wait(handlers, timeout=self.send_timeout_seconds + 1)
            for handler in pending:
                handler.cancel()
            await asyncio.gather(*handlers, return_exceptions=True)

    def publish(self, events: Iterable[Event]) -> None:
        """No socket or database waits here: failed delivery cannot fail a committed write."""
        for event in events:
            for connection in tuple(self.connections):
                if (
                    str(connection.access.board.id) != event["board_id"]
                    or str(connection.access.board.project_id) != event["project_id"]
                    or connection.close_requested.is_set()
                ):
                    continue
                try:
                    connection.queue.put_nowait(event)
                except asyncio.QueueFull:
                    # Reconnect + HTTP snapshot is safer than silently dropping queued events.
                    connection.request_close(1013)

    async def revoke_session(self, session_id: UUID) -> None:
        for connection in tuple(self.connections):
            if connection.access.session_id == session_id:
                connection.request_close(4401)

    async def revalidate_user(self, user_id: UUID) -> None:
        connections = [
            connection
            for connection in tuple(self.connections)
            if connection.access.user_id == user_id
        ]
        await asyncio.gather(*(self._revalidate(connection) for connection in connections))

    async def _revalidate(self, connection: Connection) -> None:
        try:
            connection.access = await self._check(connection)
        except SocketRejected as exc:
            connection.request_close(exc.code)

    async def _authorize(
        self,
        token: str,
        board_id: UUID,
        previous: AccessState | None = None,
        *,
        allow_deleted: bool = False,
    ) -> AccessState:
        if self.database.sessions is None:
            raise SocketRejected(1013)
        try:
            async with self.database.sessions() as session:
                context = await authenticate_token(session, token, self.settings)
                board = await session.get(Board, board_id)
                if board is None:
                    if not allow_deleted or previous is None:
                        raise SocketRejected(4404)
                    # A deleted board can still send its last invalidation, but only to
                    # recipients who retain access to the enclosing project after commit.
                    board = previous.board
                await load_project(session, board.project_id, context.user.id)
                return AccessState(board, context.user.id, context.session.id)
        except AppError as exc:
            code = 4401 if exc.status_code == 401 else 1013 if exc.status_code >= 500 else 4403
            raise SocketRejected(code) from exc

    async def _check(self, connection: Connection, *, deleted: bool = False) -> AccessState:
        try:
            async with asyncio.timeout(self.settings.health_check_timeout_seconds):
                return await self._authorize(
                    connection.token,
                    connection.access.board.id,
                    connection.access,
                    allow_deleted=deleted,
                )
        except SocketRejected:
            raise
        except Exception as exc:
            logger.warning("websocket_authorization_unavailable")
            raise SocketRejected(1013) from exc

    async def _send(self, connection: Connection, event: Event) -> None:
        if connection.close_requested.is_set():
            raise SocketRejected(connection.close_code)
        try:
            async with asyncio.timeout(self.send_timeout_seconds):
                await connection.websocket.send_json(event)
        except TimeoutError as exc:
            raise SocketRejected(1013) from exc

    async def _sender(self, connection: Connection) -> None:
        # The connection was registered before ready. A concurrent commit is either in
        # its queue or in this fresh database revision; the client's HTTP snapshot wins.
        connection.access = await self._check(connection)
        await self._send(
            connection,
            make_event(connection.access.board, "connection.ready", None, None, {}),
        )
        loop = asyncio.get_running_loop()
        next_heartbeat = loop.time() + self.heartbeat_seconds
        while not connection.close_requested.is_set():
            remaining = next_heartbeat - loop.time()
            try:
                if remaining <= 0:
                    raise TimeoutError
                event = await asyncio.wait_for(connection.queue.get(), timeout=remaining)
            except TimeoutError:
                connection.access = await self._check(connection)
                await self._send(
                    connection,
                    make_event(connection.access.board, "heartbeat", None, None, {}),
                )
                next_heartbeat = loop.time() + self.heartbeat_seconds
                continue
            deleted = event["type"] == "board.deleted"
            connection.access = await self._check(connection, deleted=deleted)
            await self._send(connection, event)
            if deleted:
                connection.request_close(4404)
                return

    async def _receiver(self, connection: Connection) -> None:
        while not connection.close_requested.is_set():
            message = await connection.websocket.receive()
            if message["type"] == "websocket.disconnect":
                connection.request_close(1000)
                return
            if message["type"] == "websocket.receive":
                # No client business messages, including alternate token transport.
                connection.request_close(1008)
                return

    async def serve(self, websocket: WebSocket, board_id: UUID) -> None:
        if self._stopping:
            await websocket.close(code=1013)
            return
        if websocket.headers.get("origin") not in self.settings.allowed_origins or bool(
            websocket.query_params
        ):
            await websocket.close(code=4403)
            return
        token = websocket.cookies.get(SESSION_COOKIE)
        if not token:
            await websocket.close(code=4401)
            return
        try:
            async with asyncio.timeout(self.settings.health_check_timeout_seconds):
                access = await self._authorize(token, board_id)
        except SocketRejected as exc:
            await websocket.close(code=exc.code)
            return
        except Exception:
            logger.warning("websocket_handshake_unavailable")
            await websocket.close(code=1013)
            return

        connection = Connection(websocket, token, access, asyncio.Queue(self.queue_size))
        self.connections.add(connection)
        handler = asyncio.current_task()
        if handler is not None:
            self._handlers.add(handler)
        pending: set[asyncio.Task[None]] = set()
        try:
            await websocket.accept()
            pending = {
                asyncio.create_task(self._sender(connection)),
                asyncio.create_task(self._receiver(connection)),
                asyncio.create_task(self._wait_close(connection)),
            }
            done, _ = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                task.result()
        except SocketRejected as exc:
            connection.request_close(exc.code)
        except (WebSocketDisconnect, RuntimeError):
            connection.request_close(1000)
        except asyncio.CancelledError:
            connection.request_close(1001)
            raise
        except Exception:
            logger.warning("websocket_connection_failed")
            connection.request_close(1011)
        finally:
            self.connections.discard(connection)
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            try:
                with suppress(WebSocketDisconnect, RuntimeError, TimeoutError):
                    async with asyncio.timeout(self.send_timeout_seconds):
                        await websocket.close(code=connection.close_code)
            finally:
                if handler is not None:
                    self._handlers.discard(handler)

    @staticmethod
    async def _wait_close(connection: Connection) -> None:
        await connection.close_requested.wait()


@router.websocket("/ws/v1/boards/{board_id}")
async def board_events(websocket: WebSocket, board_id: UUID) -> None:
    hub: Hub = websocket.app.state.event_hub
    await hub.serve(websocket, board_id)
