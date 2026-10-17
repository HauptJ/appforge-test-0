"""The one and only business endpoint: say hello."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1", tags=["hello"])


class HelloResponse(BaseModel):
    """Response schema for GET /api/v1/hello."""

    message: str = Field(..., examples=["Hello World"])


@router.get("/hello", response_model=HelloResponse)
def hello() -> HelloResponse:
    """Return the canonical greeting."""
    return HelloResponse(message="Hello World")
