# Hello World

A deliberately simple web app that greets the signed-in user with
**"Hello, world!"** – wrapped in the organization's full security baseline so it
can be used as a reference template.

- **Backend:** Python 3.12, FastAPI, Pydantic v2
- **Frontend:** React 18 + TypeScript, built with Vite, served by nginx (unprivileged)
- **Auth:** OpenID Connect (Authorization Code + PKCE) against the organization IdP
- **Secrets:** HashiCorp Vault (AppRole), with an env-var fallback for local dev only
- **Delivery:** rootless OCI containers, works with both Docker Compose and podman-compose

## File tree

```
apps/hello-world-b091d863/
├── app-inventory.yaml
├── CHANGELOG.md
├── docker-compose.yml
├── .env.example
├── .gitignore
├── Makefile
├── README.md
├── backend/
│   ├── Dockerfile
│   ├── pytest.ini
│   ├── requirements.txt
│   ├── app/
│   │   ├── asgi.py            # uvicorn entry point
│   │   ├── main.py            # create_app() factory
│   │   ├── config.py          # pydantic-settings
│   │   ├── logging_setup.py   # JSON logs + redaction
│   │   ├── security.py        # headers, CSRF, origin, body-size, request ID
│   │   ├── sessions.py        # signed-cookie, server-side session store
│   │   ├── vault_credentials.py
│   │   ├── api/{auth,hello,deps}.py
│   │   ├── services/hello_service.py
│   │   └── models/schemas.py
│   └── tests/                 # pytest + httpx.TestClient
└── frontend/
    ├── Dockerfile
    ├── nginx.conf
    ├── package.json
    ├── tsconfig.json
    ├── vite.config.ts
    ├── index.html
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── styles.css
        ├── api/client.ts
        └── test/{setup,msw-server}.ts, App.test.tsx
```

## Run it locally

### Option A – `docker compose` / `podman-compose` with Vault

1. Copy `.env.example` to `.env` and fill in `OIDC_ISSUER`, `OIDC_CLIENT_ID`,
   `VAULT_ADDR`, `VAULT_ROLE_ID` and either `VAULT_SECRET_ID` or
   `VAULT_SECRET_ID_FILE`.
2. In Vault, make sure `apps/hello-world-b091d863/oidc-client-secret` and
   `apps/hello-world-b091d863/session-signing-key` have values (see **Credentials** below).
3. `make up` → open <http://localhost:8080>.

### Option B – quick local demo without Vault or an IdP

Use the development bypass. This creates a signed-in session for a fake user and
skips OIDC entirely. **Never** enable it in a shared environment.

```sh
cp .env.example .env
# edit .env:
# AUTH_DEV_BYPASS=true
# ALLOW_ENV_CREDENTIALS=true
# SESSION_SIGNING_KEY=$(python -c "import secrets;print(secrets.token_urlsafe(48))")
make up
```

Then visit <http://localhost:8080> and press **Sign in**.

## Test it

```sh
# Backend (pytest + coverage)
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
pytest

# Frontend (Vitest + Testing Library + MSW)
cd ../frontend
npm install
npm test
npm run build
```

## Credentials

Values are stored in HashiCorp Vault under
`apps/hello-world-b091d863/<name>`, field `value`. The application reads them at
startup using its AppRole and keeps them in memory only.

| Name                  | Kind                | Env var               | Vault path                                              | Who sets it            | Used by                              |
| --------------------- | ------------------- | --------------------- | ------------------------------------------------------- | ---------------------- | ------------------------------------ |
| `oidc-client-secret`  | oauth_client_secret | `OIDC_CLIENT_SECRET`  | `apps/hello-world-b091d863/oidc-client-secret`          | application owner      | backend (OIDC token exchange)        |
| `session-signing-key` | encryption_key      | `SESSION_SIGNING_KEY` | `apps/hello-world-b091d863/session-signing-key`         | AppForge (generated)   | backend (signs session cookie IDs)   |

Owner workflow (one-off):

```sh
vault login -method=oidc                                                   # Google sign-in
vault kv put apps/hello-world-b091d863/oidc-client-secret value=-          # paste the IdP client secret
vault read -field=role_id auth/approle/role/app-hello-world-b091d863/role-id
vault write -f -field=secret_id auth/approle/role/app-hello-world-b091d863/secret-id
```

Rotating a credential writes a new version of the same entry; restart the
backend (or wait for its next startup) to pick the new value up. The app's
Vault policy is read-only.

## Security

How each item in the organization's **secure application baseline** is implemented:

| Control | Implementation |
| --- | --- |
| Sign-in required | Every `/api/v1/*` route except `/auth/*` goes through `current_session`; UI routes are static and only show data once the backend confirms a session. `/healthz` and `/readyz` are public. |
| OIDC + PKCE | `app/api/auth.py` builds the authorization URL with `code_challenge_method=S256`, generates a nonce, verifies state, and completes the token exchange with the stored `code_verifier`. |
| Server-side sessions | `app/sessions.py` keeps session data in process memory; the cookie carries only a signed opaque ID. `HttpOnly`, `SameSite=Lax`, and `Secure` when `SERVE_OVER_TLS=true`. Idle and absolute timeouts are configurable. |
| Session rotation + logout | New session ID generated after a successful OIDC callback; `/auth/logout` deletes the session server-side and clears both cookies. |
| CSRF | Double-submit token: a `csrf_token` cookie (readable by JS) and `X-CSRF-Token` header, verified with `secrets.compare_digest` for every state-changing request (`OriginAndCsrfMiddleware`). |
| Origin allowlist | Same middleware rejects state-changing requests whose `Origin` isn't in `ALLOWED_ORIGINS`. |
| Authorization | Deny-by-default. The hello endpoint uses the `current_session` dependency; a signed-in user only sees their own greeting. |
| Input validation | All responses are Pydantic v2 `StrictModel` (`extra="forbid"`, length caps). Request bodies are capped at 64 KiB by `BodySizeLimitMiddleware`. |
| Parameterized queries | No database in this app; nothing to parameterise. |
| File uploads | Not supported. |
| Generic 5xx errors | Global handler returns `{"error":{"code":"internal",...}}`; detail is logged with the request ID. |
| Secrets handling | `declare_secret` + Vault AppRole; no values in code, config, `.env.example`, tests, or docs. Startup fails closed if a credential is missing. |
| Structured logs | JSON lines with request ID (contextvar). Redaction by key (`password`, `token`, `authorization`, `cookie`, `set-cookie`, `x-csrf-token`, `secret`, …) and by pattern (card-like, SSN-like, Bearer tokens). |
| Security headers | `SecurityHeadersMiddleware` sets CSP without inline scripts, `X-Content-Type-Options`, `Referrer-Policy`, `X-Frame-Options: DENY`, `Permissions-Policy`; HSTS when TLS is on. nginx reinforces them for static responses. |
| CORS | Not enabled. UI and API are served same-origin through nginx. |
| Timeouts + size limits | Uvicorn keep-alive 15s, nginx `client_max_body_size 128k`, backend body limit 64 KiB. |
| Pinned dependencies | `requirements.txt` with `==`, exact npm versions, lock file created on first `npm install`. |

## Data handling

- **Classification:** `internal`.
- **Personal data:** yes — the user's email and display name come from the IdP and
  live inside the in-memory session for the length of a session. Nothing is written
  to disk.
- **Retention:** session lifetime (idle 30 min, absolute 8 h by default).
- **No analytics, telemetry, or external calls** besides the IdP and Vault.

## Supply chain / SBOM

Dependencies are pinned so an SBOM is reproducible.

```sh
# CycloneDX JSON SBOM for the backend
cyclonedx-py requirements -i backend/requirements.txt -o sbom-backend.json
# or
syft dir:backend -o cyclonedx-json=sbom-backend.json

# For the frontend (after `npm install` creates package-lock.json)
syft dir:frontend -o cyclonedx-json=sbom-frontend.json

# Vulnerability scans
cd backend && pip-audit -r requirements.txt
cd frontend && npm audit --omit=dev
```

Both commands are also wired into `make audit`.

## Assumptions

- Single-process deployment is fine for a "hello world"; the session store is
  in-memory. Swap in Redis before running more than one backend instance.
- The organization IdP speaks standard OIDC Discovery
  (`/.well-known/openid-configuration`) and returns `email` + `name` claims.
- No database is needed — nothing persistent is required by the user story.
- `package-lock.json` is produced on first `npm install`; commit it afterwards so
  future builds use `npm ci` and SBOMs are reproducible.

## Follow-ups

- Replace the in-memory session store with Redis once there is more than one
  backend replica.
- Add a GitHub Actions / GitLab CI pipeline that runs `pytest`, `vitest`,
  `pip-audit`, `npm audit`, and builds both images.
- Wire log output into the organization's log pipeline (structured JSON is ready).
