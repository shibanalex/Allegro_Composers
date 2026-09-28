"""Errors of the application layer and how they become HTTP responses.

Services raise these instead of HTTPException, so business rules stay independent of the web framework.
Every error response has the same shape: {"detail": "<human-readable text>", "code": "<machine code>"}
(`detail` is also what FastAPI uses, so the frontend reads one field for both).
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    status = 400
    code = "bad_request"

    def __init__(self, message: str, *, code: str | None = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code


class Unauthorized(AppError):
    status = 401
    code = "unauthorized"


class Forbidden(AppError):
    status = 403
    code = "forbidden"


class NotFound(AppError):
    status = 404
    code = "not_found"


class Conflict(AppError):
    status = 409
    code = "conflict"


class Invalid(AppError):
    status = 422
    code = "invalid"


class TooManyAttempts(AppError):
    status = 429
    code = "too_many_attempts"


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        return JSONResponse({"detail": exc.message, "code": exc.code}, status_code=exc.status)


class PayloadTooLarge(AppError):
    status = 413
    code = "too_large"


class UnsupportedMedia(AppError):
    status = 415
    code = "unsupported_media"
