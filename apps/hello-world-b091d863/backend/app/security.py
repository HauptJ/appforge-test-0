"""Security middleware: headers, CORS/origin check, request ID, size limit, CSRF."""

from __future__ import annotations

import logging
import secrets
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from .logging_setup import new_request_id, request_id_var

log = logging.getLogger(__name__)

MAX_BODY_BYTES = 64 * 1024  # 64 KiB is more than enough for this app


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("x-request-id") or new_request_id()
        token = request_id_var.set(rid)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            log.exception("unhandled error", extra={"extra_fields": {"path": request.url.path}})
            response = JSONResponse({"error": {"code": "internal", "message": "Internal server error"}}, status_code=500)
        duration_ms = int((time.perf_counter() - start) * 1000)
        response.headers["X-Request-ID"] = rid
        log.info(
            "request",
            extra={"extra_fields": {
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
            }},
        )
        request_id_var.reset(token)
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, *, serve_over_tls: bool) -> None:
        super().__init__(app)
        self.serve_over_tls = serve_over_tls

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self'; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        if self.serve_over_tls:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        cl = request.headers.get("content-length")
        if cl is not None:
            try:
                if int(cl) > MAX_BODY_BYTES:
                    return JSONResponse(
                        {"error": {"code": "payload_too_large", "message": "Request too large"}},
                        status_code=413,
                    )
            except ValueError:
                return JSONResponse(
                    {"error": {"code": "bad_request", "message": "Invalid Content-Length"}},
                    status_code=400,
                )
        return await call_next(request)


class OriginAndCsrfMiddleware(BaseHTTPMiddleware):
    """Allowlist Origin for state-changing requests and verify a double-submit CSRF token."""

    SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
    EXEMPT_PATHS = {"/api/v1/auth/callback"}  # IdP redirect; protected by OIDC state + PKCE

    def __init__(self, app: ASGIApp, *, allowed_origins: list[str], csrf_cookie: str) -> None:
        super().__init__(app)
        self.allowed = set(allowed_origins)
        self.csrf_cookie = csrf_cookie

    async def dispatch(self, request: Request, call_next):
        if request.method not in self.SAFE_METHODS and request.url.path not in self.EXEMPT_PATHS:
            origin = request.headers.get("origin")
            if origin and origin not in self.allowed:
                return JSONResponse(
                    {"error": {"code": "forbidden_origin", "message": "Origin not allowed"}},
                    status_code=403,
                )
            # Double-submit CSRF check for authenticated API paths
            if request.url.path.startswith("/api/"):
                cookie_token = request.cookies.get(self.csrf_cookie, "")
                header_token = request.headers.get("x-csrf-token", "")
                if not cookie_token or not header_token or not secrets.compare_digest(cookie_token, header_token):
                    return JSONResponse(
                        {"error": {"code": "csrf", "message": "CSRF token missing or invalid"}},
                        status_code=403,
                    )
        return await call_next(request)


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)
