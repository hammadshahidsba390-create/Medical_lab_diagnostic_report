"""One error format for the whole API: {"error": {"code": ..., "message": ...}}.

Messages are safe for users: no stack traces, SQL, secrets or file paths.
"""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

CODES = {
    400: "bad_request", 401: "unauthenticated", 403: "forbidden", 404: "not_found",
    405: "method_not_allowed", 409: "conflict", 413: "file_too_large", 415: "unsupported_type",
    422: "validation_error", 429: "rate_limited", 502: "upstream_failed", 503: "database_unavailable",
}
SAFE_MESSAGES = {
    401: "Please log in again.", 403: "You do not have access to this page.",
    404: "We could not find that.", 405: "That action is not allowed here.",
}


class AppError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        self.status_code, self.code, self.message = status_code, code, message


def error_response(status: int, code: str, message: str, details: list | None = None) -> JSONResponse:
    body: dict = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return JSONResponse(status_code=status, content=body)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error(_: Request, exc: AppError):
        return error_response(exc.status_code, exc.code, exc.message)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, exc: StarletteHTTPException):
        code = CODES.get(exc.status_code, "internal_error" if exc.status_code >= 500 else "bad_request")
        message = SAFE_MESSAGES.get(exc.status_code, "The request could not be completed.")
        return error_response(exc.status_code, code, message)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError):
        details = [
            {"field": ".".join(str(p) for p in e["loc"] if p != "body"), "message": e["msg"]}
            for e in exc.errors()
        ]
        return error_response(422, "validation_error", "Please check the highlighted fields.", details)

    @app.exception_handler(Exception)
    async def unexpected_error(_: Request, exc: Exception):
        return error_response(500, "internal_error", "Something went wrong. Please try again.")
