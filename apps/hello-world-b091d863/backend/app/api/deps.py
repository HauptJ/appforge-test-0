"""FastAPI dependencies: current session / user."""

from __future__ import annotations

from fastapi import HTTPException, Request, status

from ..sessions import SessionData, SessionStore


def get_store(request: Request) -> SessionStore:
    return request.app.state.sessions


def current_session(request: Request) -> tuple[str, SessionData]:
    store = get_store(request)
    cookie_name = request.app.state.settings.session_cookie_name
    cookie_value = request.cookies.get(cookie_name, "")
    got = store.get(cookie_value)
    if got is None or not got[1].user_email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not authenticated")
    return got
