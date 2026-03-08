from __future__ import annotations


class AppError(Exception):
    code: str = "app_error"

    def __init__(self, message: str, details: object | None = None):
        super().__init__(message)
        self.message = message
        self.details = details


class NotFound(AppError):
    code = "not_found"


class Forbidden(AppError):
    code = "forbidden"


class ValidationError(AppError):
    code = "validation_error"


class Conflict(AppError):
    code = "conflict"

