"""FastAPI application factory, middleware, and routing."""
from __future__ import annotations

import logging
import uuid
from typing import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .api.hello import router as hello_router
from .config import Settings, get_settings
from .logging_config import configure_logging, request_id_var

logger = logging.getLogger("app")

# A strict CSP: no inline scripts, no third-party sources.
# `frame-ancestors 'none'` replaces the legacy X-Frame-Options.
_CSP = (
    "default-src 'none'; "
    "frame-ancestors 'none'; "
    "base-uri 'none'; "
    "form-action 'none'"
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach a conservative set of security headers to every response."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        response.headers.setdefault("Content-Security-Policy", _CSP)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Strict-Transport-Security",
            "max-age=63072000; includeSubDomains",
        )
        response.headers.setdefault("X-Frame-Options", "DENY")
        return response


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Assign/propagate an X-Request-ID and log one line per request."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        incoming = request.headers.get("x-request-id", "")
        # Keep caller-supplied IDs but cap length and strip control chars.
        rid = "".join(c for c in incoming if c.isalnum() or c in "-_")[:64]
        if not rid:
            rid = uuid.uuid4().hex
        token = request_id_var.set(rid)
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        response.headers["X-Request-ID"] = rid
        logger.info(
            "request",
            extra={
                "extra": {
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                }
            },
        )
        return response


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests whose Content-Length exceeds the configured cap."""

    def __init__(self, app: FastAPI, max_bytes: int) -> None:
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        length = request.headers.get("content-length")
        if length is not None:
            try:
                if int(length) > self.max_bytes:
                    return JSONResponse(
                        status_code=413,
                        content={"error": "request body too large"},
                    )
            except ValueError:
                return JSONResponse(
                    status_code=400,
                    content={"error": "invalid content-length"},
                )
        return await call_next(request)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory."""
    configure_logging()
    settings = settings or get_settings()

    app = FastAPI(
        title="Hello World 0",
        version=settings.app_version,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
    )

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_body_bytes)

    @app.get("/healthz", include_in_schema=False)
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz", include_in_schema=False)
    def readyz() -> dict[str, str]:
        # No external dependencies; always ready once the process is up.
        return {"status": "ready"}

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        # Log the detail; return a generic message with the request ID.
        logger.exception("unhandled error")
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal error",
                "request_id": request_id_var.get(),
            },
        )

    app.include_router(hello_router)
    return app


app = create_app()
