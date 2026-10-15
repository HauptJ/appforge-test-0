"""OIDC Authorization Code + PKCE login, logout, and session status."""

from __future__ import annotations

import base64
import hashlib
import logging
import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from ..config import Settings
from ..models.schemas import SessionStatus, UserInfo
from ..oidc import OidcClient, OidcError
from ..security import new_csrf_token
from ..sessions import SessionData, SessionStore

log = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


def _settings(request: Request) -> Settings:
    return request.app.state.settings


def _store(request: Request) -> SessionStore:
    return request.app.state.sessions


def _oidc(request: Request) -> OidcClient | None:
    return getattr(request.app.state, "oidc", None)


def _set_session_cookies(response, settings: Settings, signed_cookie: str, csrf_token: str) -> None:
    response.set_cookie(
        settings.session_cookie_name,
        signed_cookie,
        max_age=settings.session_absolute_minutes * 60,
        httponly=True,
        secure=settings.serve_over_tls,
        samesite="lax",
        path="/",
    )
    # Double-submit CSRF cookie: readable by JS so the frontend can echo it in a header.
    response.set_cookie(
        "csrf_token",
        csrf_token,
        max_age=settings.session_absolute_minutes * 60,
        httponly=False,
        secure=settings.serve_over_tls,
        samesite="lax",
        path="/",
    )


def _clear_session_cookies(response, settings: Settings) -> None:
    response.delete_cookie(settings.session_cookie_name, path="/")
    response.delete_cookie("csrf_token", path="/")


def _pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


def _safe_return_to(value: str) -> str:
    # Only allow local, path-only redirects to avoid open-redirect.
    if not value or not value.startswith("/") or value.startswith("//"):
        return "/"
    return value


@router.get("/status", response_model=SessionStatus)
async def status_endpoint(request: Request) -> SessionStatus:
    cookie = request.cookies.get(_settings(request).session_cookie_name, "")
    got = _store(request).get(cookie)
    if got is None or not got[1].user_email:
        return SessionStatus(authenticated=False)
    _, data = got
    return SessionStatus(authenticated=True, user=UserInfo(email=data.user_email, name=data.user_name))


@router.get("/login")
async def login(request: Request, return_to: str = "/") -> RedirectResponse:
    settings = _settings(request)
    return_to = _safe_return_to(return_to)

    # Development bypass: create a signed-in session immediately. Never enable in production.
    if settings.auth_dev_bypass:
        return _dev_bypass_login(request, settings, return_to)

    oidc = _oidc(request)
    if oidc is None:
        raise HTTPException(status_code=503, detail="OIDC not configured")

    verifier, challenge = _pkce_pair()
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)

    pre_data = SessionData(
        user_email="",
        user_name="",
        oidc_state=state,
        oidc_nonce=nonce,
        oidc_code_verifier=verifier,
        oidc_return_to=return_to,
    )
    _, cookie = _store(request).create(pre_data)

    params = {
        "response_type": "code",
        "client_id": settings.oidc_client_id,
        "redirect_uri": settings.oidc_redirect_url,
        "scope": settings.oidc_scopes,
        "state": state,
        "nonce": nonce,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    auth_endpoint = await oidc.authorization_endpoint()
    auth_url = f"{auth_endpoint}?{urlencode(params)}"
    resp = RedirectResponse(auth_url, status_code=302)
    resp.set_cookie(
        settings.session_cookie_name,
        cookie,
        max_age=600,
        httponly=True,
        secure=settings.serve_over_tls,
        samesite="lax",
        path="/",
    )
    return resp


def _dev_bypass_login(request: Request, settings: Settings, return_to: str) -> RedirectResponse:
    data = SessionData(
        user_email=settings.dev_user_email,
        user_name=settings.dev_user_name,
        csrf_token=new_csrf_token(),
    )
    _, cookie = _store(request).create(data)
    resp = RedirectResponse(return_to, status_code=302)
    _set_session_cookies(resp, settings, cookie, data.csrf_token)
    log.warning("auth_dev_bypass is enabled - do not use in production")
    return resp


@router.get("/callback")
async def callback(request: Request) -> RedirectResponse:
    settings = _settings(request)
    oidc = _oidc(request)
    if oidc is None:
        raise HTTPException(status_code=503, detail="OIDC not configured")

    cookie = request.cookies.get(settings.session_cookie_name, "")
    got = _store(request).get(cookie)
    if got is None or not got[1].oidc_state:
        raise HTTPException(status_code=400, detail="login session missing")
    old_sid, pre = got

    state = request.query_params.get("state", "")
    code = request.query_params.get("code", "")
    if not state or not code or not secrets.compare_digest(state, pre.oidc_state or ""):
        raise HTTPException(status_code=400, detail="invalid state")

    try:
        tokens = await oidc.exchange_code(
            code=code,
            code_verifier=pre.oidc_code_verifier or "",
            nonce=pre.oidc_nonce or "",
        )
    except OidcError:
        raise HTTPException(status_code=401, detail="authentication failed") from None

    email = str(tokens.claims.get("email") or "").strip()
    name = str(tokens.claims.get("name") or email or "User").strip()
    if not email:
        raise HTTPException(status_code=401, detail="idp did not return an email")

    # Rotate the session ID at login.
    _store(request).delete(old_sid)
    data = SessionData(user_email=email, user_name=name, csrf_token=new_csrf_token())
    _, new_cookie = _store(request).create(data)

    resp = RedirectResponse(_safe_return_to(pre.oidc_return_to), status_code=302)
    _set_session_cookies(resp, settings, new_cookie, data.csrf_token)
    return resp


@router.post("/logout")
async def logout(request: Request) -> RedirectResponse:
    settings = _settings(request)
    cookie = request.cookies.get(settings.session_cookie_name, "")
    got = _store(request).get(cookie)
    if got is not None:
        sid, _ = got
        _store(request).delete(sid)
    resp = RedirectResponse("/", status_code=303)
    _clear_session_cookies(resp, settings)
    return resp
