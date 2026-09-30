"""Errors of the application layer and how they become HTTP responses.

Services raise these instead of HTTPException, so business rules stay independent of the web framework.
Every error response has the same shape: {"detail": "<human-readable text>", "code": "<machine code>"}
(`detail` is also what FastAPI uses, so the frontend reads one field for both).
"""
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
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


FIELD_NAMES = {
    "title": "Название", "subtitle": "Подзаголовок", "display_name": "Имя", "pseudonym": "Псевдоним",
    "username": "Адрес зала", "password": "Пароль", "new_password": "Новый пароль", "email": "Почта",
    "content_md": "Текст", "body": "Текст", "excerpt": "Анонс", "bio": "Манифест", "about_md": "О себе",
    "description": "Описание", "description_md": "Описание", "url": "Ссылка", "epigraph": "Эпиграф",
}


def _human(error: dict) -> str:
    """A validation error in words: «Название: не длиннее 255 знаков»"""
    field = next((str(part) for part in reversed(error.get("loc", ())) if isinstance(part, str) and part != "body"), "")
    ctx = error.get("ctx") or {}
    kind = error.get("type", "")
    text = {
        "string_too_long": f"не длиннее {ctx.get('max_length')} знаков",
        "string_too_short": "не заполнено" if ctx.get("min_length") == 1 else f"не короче {ctx.get('min_length')} знаков",
        "missing": "обязательное поле",
        "too_long": (f"не длиннее {ctx.get('max_length')} знаков" if isinstance(error.get("input"), str)
                     else f"не больше {ctx.get('max_length')} элементов"),
        "greater_than_equal": f"не меньше {ctx.get('ge')}",
        "less_than_equal": f"не больше {ctx.get('le')}",
        "literal_error": "недопустимое значение",
        "enum": "недопустимое значение",
        "uuid_parsing": "неверный идентификатор",
        "int_parsing": "нужно число",
        "json_invalid": "запрос не разобран",
    }.get(kind) or str(error.get("msg", "")).removeprefix("Value error, ")
    name = FIELD_NAMES.get(field)
    return f"{name}: {text[:1].lower()}{text[1:]}" if name and text else text


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        return JSONResponse({"detail": exc.message, "code": exc.code}, status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def _invalid(_: Request, exc: RequestValidationError):
        """Checks of what was sent, in Russian and in one line (the site shows `detail` as it is)"""
        messages = list(dict.fromkeys(_human(e) for e in exc.errors()))
        return JSONResponse({"detail": "; ".join(messages), "code": "invalid", "errors": jsonable_encoder(exc.errors())},
                            status_code=422)


class PayloadTooLarge(AppError):
    status = 413
    code = "too_large"


class UnsupportedMedia(AppError):
    status = 415
    code = "unsupported_media"
