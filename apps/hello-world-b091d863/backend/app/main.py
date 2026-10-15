"""FastAPI application factory."""

from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .api import auth as auth_api
from .api import hello as hello_api
from .config import Settings, get_settings
from .logging_setup import configure_logging
from .oidc import OidcClient
from .security import (
    BodySizeLimitMiddleware,
    OriginAndCsrfMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)
from .sessions import SessionStore
from .vault_credentials import load_credentials

log = logging.getLogger(__name__)

REQUIRED_CREDENTIALS = {
    "oidc-client-secret": "OIDC_CLIENT_SECRET",
    "session-signing-key": "SESSION_SIGNING_KEY",
}


def _load_creds(settings: Settings) -> dict[str, str]:
    if settings.auth_dev_bypass:
        key = os.environ.get("SESSION_SIGNING_KEY")
        if not key:
            raise RuntimeError("SESSION_SIGNING_KEY must be set when AUTH_DEV_BYPASS=true")
        return {"session-signing-key": key, "oidc-client-secret": "unused"}
    return load_credentials(REQUIRED_CREDENTIALS)


def create_app(settings: Settings | None = None) -> FastAPI:
    configure_logging(level=os.environ.get("LOG_LEVEL", "INFO"))
    settings = settings or get_settings()
    creds = _load_creds(settings)

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
    )
    app.state.settings = settings
    app.state.sessions = SessionStore(
        signing_key=creds["session-signing-key"],
        idle_minutes=settings.session_idle_minutes,
        absolute_minutes=settings.session_absolute_minutes,
    )

    # OIDC client (only when configured and not in dev bypass).
    if settings.oidc_issuer and settings.oidc_client_id and not settings.auth_dev_bypass:
        app.state.oidc = OidcClient(
            issuer=settings.oidc_issuer,
            client_id=settings.oidc_client_id,
            client_secret=creds["oidc-client-secret"],
            redirect_url=settings.oidc_redirect_url,
            scopes=settings.oidc_scopes,
        )
    else:
        app.state.oidc = None
        if not settings.auth_dev_bypass:
            log.warning("OIDC is not fully configured; /auth/login will return 503")

    # Middleware. Starlette applies them in reverse add order, so what we add
    # LAST is the outermost (first to see the request).
    app.add_middleware(
        OriginAndCsrfMiddleware,
        allowed_origins=settings.allowed_origin_list,
        csrf_cookie="csrf_token",
    )
    app.add_middleware(BodySizeLimitMiddleware)
    app.add_middleware(SecurityHeadersMiddleware, serve_over_tls=settings.serve_over_tls)
    app.add_middleware(RequestContextMiddleware)

    app.include_router(auth_api.router, prefix="/api/v1")
    app.include_router(hello_api.router, prefix="/api/v1")

    @app.get("/healthz", tags=["health"])
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz", tags=["health"])
    async def readyz() -> dict[str, str]:
        return {"status": "ready"}

    @app.exception_handler(StarletteHTTPException)
    async def http_exc_handler(_request, exc: StarletteHTTPException):
        code = {
            400: "bad_request", 401: "unauthorized", 403: "forbidden",
            404: "not_found", 405: "method_not_allowed", 413: "payload_too_large",
        }.get(exc.status_code, "error")
        message = exc.detail if exc.status_code < 500 else "Internal server error"
        return JSONResponse({"error": {"code": code, "message": str(message)}}, status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_request, exc: RequestValidationError):
        return JSONResponse(
            {"error": {"code": "validation_error", "message": "Invalid request"}},
            status_code=422,
        )

    return app
