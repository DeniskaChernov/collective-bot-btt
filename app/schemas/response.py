from __future__ import annotations

from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class APIError(BaseModel):
    code: str
    message: str
    details: Any | None = None


class APIResponse(BaseModel, Generic[T]):
    ok: Literal[True]
    result: T


class APIErrorResponse(BaseModel):
    ok: Literal[False]
    error: APIError


def ok(result: T) -> APIResponse[T]:
    return APIResponse(ok=True, result=result)


def err(code: str, message: str, details: Any | None = None) -> APIErrorResponse:
    return APIErrorResponse(ok=False, error=APIError(code=code, message=message, details=details))

