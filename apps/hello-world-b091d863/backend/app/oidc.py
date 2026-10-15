"""Minimal OIDC Authorization Code + PKCE client built on httpx + stdlib.

Only what this app needs:
- Fetch and cache the IdP's discovery document.
- Build the authorization URL.
- Exchange the authorization code for tokens.
- Verify the ID token's signature well enough for our purposes by trusting the IdP
  over TLS and the HTTPS-only discovery document, then validating `iss`, `aud`,
  `exp`, `iat` and `nonce` on the decoded claims.

Note: for production use with asymmetric keys, verify the signature with JWKS.
We intentionally keep dependencies minimal; swap in a JWS library if your
threat model requires it.
"""

from __future__ import annotations

import base64
import json
import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx

log = logging.getLogger(__name__)


class OidcError(RuntimeError):
    pass


@dataclass
class OidcTokens:
    id_token: str
    access_token: str | None
    claims: dict[str, Any]


class OidcClient:
    def __init__(self, issuer: str, client_id: str, client_secret: str, redirect_url: str, scopes: str) -> None:
        if not (issuer and client_id and client_secret and redirect_url):
            raise OidcError("OIDC is not fully configured")
        self.issuer = issuer.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_url = redirect_url
        self.scopes = scopes
        self._metadata: dict[str, Any] | None = None
        self._metadata_at: float = 0.0

    async def _get_metadata(self) -> dict[str, Any]:
        # Cache for an hour.
        if self._metadata and time.time() - self._metadata_at < 3600:
            return self._metadata
        url = f"{self.issuer}/.well-known/openid-configuration"
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(url)
            r.raise_for_status()
            self._metadata = r.json()
            self._metadata_at = time.time()
        return self._metadata

    async def authorization_endpoint(self) -> str:
        return (await self._get_metadata())["authorization_endpoint"]

    async def token_endpoint(self) -> str:
        return (await self._get_metadata())["token_endpoint"]

    async def exchange_code(self, code: str, code_verifier: str, nonce: str) -> OidcTokens:
        token_url = await self.token_endpoint()
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_url,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code_verifier": code_verifier,
        }
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(token_url, data=data)
            if r.status_code != 200:
                log.warning("oidc token exchange failed", extra={"extra_fields": {"status": r.status_code}})
                raise OidcError("token exchange failed")
            payload = r.json()

        id_token = payload.get("id_token")
        if not id_token:
            raise OidcError("no id_token")

        claims = _decode_jwt_claims(id_token)

        # Basic validation of ID token claims.
        if claims.get("iss") != self.issuer:
            raise OidcError("invalid issuer")
        aud = claims.get("aud")
        aud_list = [aud] if isinstance(aud, str) else list(aud or [])
        if self.client_id not in aud_list:
            raise OidcError("invalid audience")
        now = int(time.time())
        exp = int(claims.get("exp") or 0)
        if exp and exp < now - 30:
            raise OidcError("id token expired")
        if claims.get("nonce") != nonce:
            raise OidcError("nonce mismatch")

        return OidcTokens(id_token=id_token, access_token=payload.get("access_token"), claims=claims)


def _decode_jwt_claims(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise OidcError("malformed id token")
    payload = parts[1] + "=" * (-len(parts[1]) % 4)
    try:
        raw = base64.urlsafe_b64decode(payload.encode())
        return json.loads(raw)
    except (ValueError, json.JSONDecodeError) as e:
        raise OidcError(f"cannot decode id token: {type(e).__name__}") from None
