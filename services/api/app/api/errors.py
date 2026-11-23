"""Uniform error envelope (docs/API_CONTRACTS.md): {"error": {"code", "message", "details"}}."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

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

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _envelope(exc.status_code, str(exc.detail))


ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    422: {"model": ErrorResponse, "description": "Validation error"},
    501: {"model": ErrorResponse, "description": "Declared in contract, not implemented yet"},
}
