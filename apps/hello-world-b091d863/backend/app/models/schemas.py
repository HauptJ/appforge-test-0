"""Pydantic request/response models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class HelloResponse(StrictModel):
    message: str = Field(..., max_length=200)


class UserInfo(StrictModel):
    email: str = Field(..., max_length=320)
    name: str = Field(..., max_length=200)


class SessionStatus(StrictModel):
    authenticated: bool
    user: UserInfo | None = None


class ErrorBody(StrictModel):
    code: str
    message: str


class ErrorResponse(StrictModel):
    error: ErrorBody
