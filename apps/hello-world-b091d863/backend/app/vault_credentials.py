"""Load this application's credentials from HashiCorp Vault (AppRole login, KV v2).

Standard library only. Usage at startup::

    from .vault_credentials import load_credentials

    CREDS = load_credentials({"db-password": "DB_PASSWORD"})
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping

log = logging.getLogger(__name__)


class CredentialError(RuntimeError):
    """Raised at startup when credentials cannot be loaded. Never contains a value."""


def _secret_id() -> str:
    path = os.environ.get("VAULT_SECRET_ID_FILE", "")
    if path:
        with open(path, encoding="utf-8") as f:
            return f.read().strip()
    return os.environ.get("VAULT_SECRET_ID", "")


class VaultCredentials:
    def __init__(self, addr: str, role_id: str, secret_id: str, mount: str, app_path: str, timeout: float = 10) -> None:
        if not (addr and role_id and secret_id and app_path):
            raise CredentialError("VAULT_ADDR, VAULT_ROLE_ID, VAULT_SECRET_ID(_FILE) and VAULT_APP_PATH are required")
        self.addr, self.mount, self.app_path, self.timeout = addr.rstrip("/"), mount, app_path.strip("/"), timeout
        self._role_id, self._secret_id = role_id, secret_id
        self._token = ""

    def _request(self, method: str, path: str, body: dict | None = None) -> dict:
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            f"{self.addr}/v1/{path}",
            data=data,
            method=method,
            headers={
                "Content-Type": "application/json",
                **({"X-Vault-Token": self._token} if self._token else {}),
            },
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310 - fixed scheme from config
            return json.loads(resp.read() or b"{}")

    def login(self) -> None:
        self._token = ""
        try:
            out = self._request(
                "POST",
                "auth/approle/login",
                {"role_id": self._role_id, "secret_id": self._secret_id},
            )
        except (urllib.error.URLError, OSError) as e:
            raise CredentialError(f"Vault login failed ({type(e).__name__})") from None
        self._token = out["auth"]["client_token"]

    def read(self, name: str) -> str:
        path = f"{self.mount}/data/{self.app_path}/{urllib.parse.quote(name)}"
        value = ""
        for attempt in (1, 2):
            if not self._token:
                self.login()
            try:
                value = self._request("GET", path)["data"]["data"].get("value", "")
                break
            except urllib.error.HTTPError as e:
                if e.code == 403 and attempt == 1:
                    self._token = ""
                    continue
                raise CredentialError(f"cannot read {path} (HTTP {e.code})") from None
            except (urllib.error.URLError, OSError, KeyError) as e:
                raise CredentialError(f"cannot read {path} ({type(e).__name__})") from None
        if not value:
            raise CredentialError(f"{path} has no value yet: the application owner must set it in Vault")
        return value


def load_credentials(names: Mapping[str, str]) -> dict[str, str]:
    """Load every credential (name -> env var used for local development). Fails closed."""
    addr = os.environ.get("VAULT_ADDR", "")
    if not addr:
        if os.environ.get("ALLOW_ENV_CREDENTIALS", "").lower() != "true":
            raise CredentialError(
                "VAULT_ADDR is not set (set ALLOW_ENV_CREDENTIALS=true for local development only)"
            )
        log.warning("Vault is not in use: reading credentials from environment variables (local development only)")
        missing = [env for env in names.values() if not os.environ.get(env)]
        if missing:
            raise CredentialError(f"missing environment variables: {', '.join(missing)}")
        return {name: os.environ[env] for name, env in names.items()}
    vault = VaultCredentials(
        addr,
        os.environ.get("VAULT_ROLE_ID", ""),
        _secret_id(),
        os.environ.get("VAULT_KV_MOUNT", "apps"),
        os.environ.get("VAULT_APP_PATH", ""),
    )
    values, problems = {}, []
    for name in names:
        try:
            values[name] = vault.read(name)
        except CredentialError as e:
            problems.append(str(e))
    if problems:
        raise CredentialError("; ".join(problems))
    log.info("loaded %d credentials from Vault", len(values))
    return values
