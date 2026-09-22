import json
import logging
import time
from uuid import UUID, uuid4

from starlette.datastructures import Headers, MutableHeaders
from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.errors import HTTP_ERRORS, error_response, is_database_unavailable

logger = logging.getLogger("app.requests")


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        supplied = Headers(scope=scope).get("x-request-id", "")
        try:
            request_id = str(UUID(supplied)) if len(supplied) == 36 else str(uuid4())
        except ValueError:
            request_id = str(uuid4())
        scope.setdefault("state", {})["request_id"] = request_id
        started_at = time.perf_counter()
        response_started = False
        status = 500

        async def send_with_context(message: Message) -> None:
            nonlocal response_started, status
            if message["type"] == "http.response.start":
                response_started = True
                status = message["status"]
                MutableHeaders(scope=message)["X-Request-ID"] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_context)
        except Exception as exc:
            if response_started:
                raise
            error_status = 503 if is_database_unavailable(exc) else 500
            code, public_message = HTTP_ERRORS[error_status]
            response = error_response(Request(scope), error_status, code, public_message)
            await response(scope, receive, send_with_context)
        finally:
            route = scope.get("route")
            # Log a route template, never a raw URL, query, body, cookie, or exception text.
            logger.info(
                json.dumps(
                    {
                        "request_id": request_id,
                        "method": scope["method"],
                        "route": getattr(route, "path", "<unmatched>"),
                        "status": status,
                        "duration_ms": round((time.perf_counter() - started_at) * 1000, 2),
                    }
                )
            )
