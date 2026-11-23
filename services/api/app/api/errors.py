"""Uniform error envelope (docs/API_CONTRACTS.md): {"error": {"code", "message", "details"}}."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.domain.shared.errors import Conflict, DomainError, InvalidChange, NotFound

CODES = {
    400: "bad_request",
    404: "not_found",
    409: "conflict",
    422: "validation_error",
    501: "not_implemented",
    503: "provider_unavailable",
}


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[Any] = []


class ErrorResponse(BaseModel):
    error: ErrorBody


def _envelope(status: int, message: str, details: list | None = None) -> JSONResponse:
    body = ErrorResponse(error=ErrorBody(code=CODES.get(status, "error"), message=message, details=details or []))
    return JSONResponse(status_code=status, content=jsonable_encoder(body))


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = [{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
        return _envelope(422, "Request validation failed", details)

    @app.exception_handler(DomainError)
    async def _domain(_: Request, exc: DomainError) -> JSONResponse:
        status = {NotFound: 404, Conflict: 409, InvalidChange: 422}.get(type(exc), 400)
        return _envelope(status, exc.message, exc.details)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _envelope(exc.status_code, str(exc.detail))


ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse, "description": "Not found"},
    409: {"model": ErrorResponse, "description": "Conflicts with stored state"},
    422: {"model": ErrorResponse, "description": "Validation error or invalid change"},
}
