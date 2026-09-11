from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.exc import DBAPIError, DisconnectionError, SQLAlchemyError
from sqlalchemy.exc import TimeoutError as PoolTimeoutError
from starlette.exceptions import HTTPException


class ErrorDetail(BaseModel):
    field: str
    message: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)
    request_id: str


class ErrorResponse(BaseModel):
    error: ErrorBody


class AppError(Exception):
    """Only explicitly public messages may be passed to this exception."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: list[ErrorDetail] | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or []


HTTP_ERRORS: dict[int, tuple[str, str]] = {
    400: ("BAD_REQUEST", "Некорректный запрос"),
    401: ("AUTH_REQUIRED", "Войдите в систему"),
    403: ("FORBIDDEN", "Недостаточно прав"),
    404: ("NOT_FOUND", "Ресурс не найден"),
    405: ("METHOD_NOT_ALLOWED", "Метод запроса не поддерживается"),
    409: ("CONFLICT", "Изменения конфликтуют с текущим состоянием"),
    415: ("UNSUPPORTED_MEDIA_TYPE", "Отправьте тело в формате JSON"),
    422: ("VALIDATION_ERROR", "Проверьте заполнение полей"),
    429: ("RATE_LIMITED", "Слишком много запросов"),
    500: ("INTERNAL_ERROR", "Внутренняя ошибка сервера"),
    503: ("TEMPORARILY_UNAVAILABLE", "Сервис временно недоступен"),
}


def is_database_unavailable(exc: Exception) -> bool:
    """Classify transient failures by structured state, never by SQL or message text."""
    if isinstance(exc, (DisconnectionError, PoolTimeoutError)):
        return True
    original: BaseException | None = exc
    if isinstance(exc, DBAPIError):
        if exc.connection_invalidated or isinstance(exc.orig, (ConnectionError, TimeoutError)):
            return True
        original = exc.orig
    # Asyncpg connection establishment can raise raw driver errors before SQLAlchemy
    # creates its connection adapter; these still carry a structured SQLSTATE.
    state = getattr(original, "sqlstate", None) or getattr(original, "pgcode", None)
    return isinstance(state, str) and (
        state.startswith(("08", "53"))
        or state
        in {
            "28000",
            "28P01",
            "3D000",
            "40001",
            "40P01",
            "55P03",
            "57014",
            "57P01",
            "57P02",
            "57P03",
        }
    )


def error_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: list[ErrorDetail] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body = ErrorResponse(
        error=ErrorBody(
            code=code,
            message=message,
            details=details or [],
            request_id=request.state.request_id,
        )
    )
    return JSONResponse(body.model_dump(mode="json"), status_code=status_code, headers=headers)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(SQLAlchemyError)
    async def database_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        status = 503 if is_database_unavailable(exc) else 500
        code, message = HTTP_ERRORS[status]
        return error_response(request, status, code, message)

    @app.exception_handler(ConnectionError)
    @app.exception_handler(TimeoutError)
    async def connection_error_handler(request: Request, exc: Exception) -> JSONResponse:
        # Asyncpg can raise native connection/timeout exceptions before SQL execution.
        code, message = HTTP_ERRORS[503]
        return error_response(request, 503, code, message)

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return error_response(request, exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(HTTPException)
    async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
        code, message = HTTP_ERRORS.get(exc.status_code, ("HTTP_ERROR", "Ошибка запроса"))
        # Framework detail is not necessarily safe: it may contain internal values.
        safe_headers = {
            name: value
            for name, value in (exc.headers or {}).items()
            if name.lower() in {"allow", "www-authenticate", "retry-after"}
        }
        return error_response(request, exc.status_code, code, message, headers=safe_headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        messages = {
            "missing": "Обязательное поле",
            "int_parsing": "Введите целое число",
            "int_type": "Введите целое число",
            "json_invalid": "Некорректный JSON",
            "extra_forbidden": "Неизвестное поле",
        }
        details = [
            ErrorDetail(
                field=".".join(str(part) for part in error["loc"] if part != "body"),
                message=messages.get(error["type"], "Недопустимое значение"),
            )
            for error in exc.errors()
        ]
        return error_response(
            request, 422, "VALIDATION_ERROR", "Проверьте заполнение полей", details
        )


def error_responses(*statuses: int) -> dict[int | str, dict[str, Any]]:
    return {
        status: {"model": ErrorResponse, "description": HTTP_ERRORS[status][1]}
        for status in statuses
    }
