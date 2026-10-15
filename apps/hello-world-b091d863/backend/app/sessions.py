"""Server-side session store with signed opaque cookie IDs."""

from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

from itsdangerous import BadSignature, URLSafeSerializer


@dataclass
class SessionData:
    user_email: str
    user_name: str
    created_at: float = field(default_factory=time.time)
    last_seen_at: float = field(default_factory=time.time)
    csrf_token: str = ""
    # OIDC flow transient state (used during login only)
    oidc_state: Optional[str] = None
    oidc_nonce: Optional[str] = None
    oidc_code_verifier: Optional[str] = None
    oidc_return_to: str = "/"


class SessionStore:
    """In-memory session store, suitable for a single-process deployment.

    Replace with Redis for multi-instance deployments.
    """

    def __init__(self, signing_key: str, idle_minutes: int, absolute_minutes: int) -> None:
        self._serializer = URLSafeSerializer(signing_key, salt="hello-world-session")
        self._idle = idle_minutes * 60
        self._absolute = absolute_minutes * 60
        self._lock = threading.Lock()
        self._store: dict[str, SessionData] = {}

    def _sign(self, sid: str) -> str:
        return self._serializer.dumps(sid)

    def _unsign(self, token: str) -> Optional[str]:
        try:
            value = self._serializer.loads(token)
            return value if isinstance(value, str) else None
        except BadSignature:
            return None

    def create(self, data: SessionData) -> tuple[str, str]:
        """Create a new session; returns (sid, signed_cookie_value)."""
        sid = secrets.token_urlsafe(32)
        with self._lock:
            self._store[sid] = data
        return sid, self._sign(sid)

    def get(self, cookie_value: str) -> Optional[tuple[str, SessionData]]:
        sid = self._unsign(cookie_value) if cookie_value else None
        if not sid:
            return None
        now = time.time()
        with self._lock:
            data = self._store.get(sid)
            if data is None:
                return None
            if now - data.last_seen_at > self._idle or now - data.created_at > self._absolute:
                self._store.pop(sid, None)
                return None
            data.last_seen_at = now
            return sid, data

    def update(self, sid: str, data: SessionData) -> None:
        with self._lock:
            if sid in self._store:
                self._store[sid] = data

    def rotate(self, old_sid: str) -> tuple[str, str]:
        """Rotate the session ID (call at login). Returns (new_sid, signed_cookie)."""
        with self._lock:
            data = self._store.pop(old_sid, None)
        if data is None:
            data = SessionData(user_email="", user_name="")
        return self.create(data)

    def delete(self, sid: str) -> None:
        with self._lock:
            self._store.pop(sid, None)

    def sign(self, sid: str) -> str:
        return self._sign(sid)
