"""The hello endpoint - the one piece of actual application logic."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..models.schemas import HelloResponse
from ..services.hello_service import build_hello_message
from ..sessions import SessionData
from .deps import current_session

router = APIRouter(prefix="/hello", tags=["hello"])


@router.get("", response_model=HelloResponse)
async def hello(session: tuple[str, SessionData] = Depends(current_session)) -> HelloResponse:
    _, data = session
    return HelloResponse(message=build_hello_message(data.user_name or data.user_email or "world"))
