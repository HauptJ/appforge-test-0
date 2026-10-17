# Hello World 0

The simplest possible web application: a single HTTP endpoint that returns
`Hello World`.

## What it is

- A Python FastAPI backend (no frontend, no database, no authentication).
- Packaged as a rootless OCI container and run with Docker Compose or
  podman-compose.
- Ships with structured JSON logging, security headers, request-size limits,
  tests, and an application-inventory manifest.

## Endpoints

| Method | Path             | Description                               |
|--------|------------------|-------------------------------------------|
| GET    | `/api/v1/hello`  | Returns `{"message": "Hello World"}`      |
| GET    | `/healthz`       | Liveness probe                            |
| GET    | `/readyz`        | Readiness probe                           |

OpenAPI docs are served at `/docs` only when `DOCS_ENABLED=true`.

## Run it

Prerequisites: Docker (or Podman) with Compose.

```sh
cp .env.example .env       # no values needed for this app
make up                    # or: docker compose up --build
# then
curl http://127.0.0.1:8080/api/v1/hello
# -> {"message":"Hello World"}
make down
```

Other targets: `make logs`, `make test`, `make build`.

### Run locally without containers

```sh
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8080
```

## Tests

```sh
cd backend
pip install -r requirements.txt
pytest
```

## Assumptions and deviations from the organization baseline

The user explicitly requested "a simple as possible web application that only
displays hello world. Authentication and a front end are not necessary." That
conflicts with two preset skills; the following decisions were taken:

1. **No frontend.** The `react-python-webapp` skill mandates a React/Vite
   frontend. There is nothing to render beyond a static string, so this app
   ships the backend only. If a UI is wanted later, add a `frontend/` directory
   per that skill.
2. **No authentication.** The `secure-app-baseline` skill mandates OIDC on
   every route except health checks and login. The app exposes no data, has
   no users, and performs no state changes, so the single `/api/v1/hello`
   endpoint is treated as public (equivalent to a health/info endpoint). If
   this app ever starts handling data, OIDC must be added before that change
   ships.

All other baseline controls still apply (see "Security" below).

## Security

| Control                           | How it's implemented                                               |
|-----------------------------------|--------------------------------------------------------------------|
| Input validation                  | Pydantic response model; endpoint takes no input.                  |
| Parameterized queries             | N/A — no database.                                                 |
| Secrets handling                  | No credentials needed; none declared. See "Credentials" below.     |
| Structured logging                | JSON logs with per-request ID (`app.logging_config`).              |
| Credential redaction              | Log filter strips `authorization`, `cookie`, `token`, `password`.  |
| Security headers                  | CSP (no inline), `X-Content-Type-Options`, `Referrer-Policy`, `frame-ancestors 'none'`, HSTS. |
| CORS                              | Disabled (same-origin only).                                       |
| Request size & timeouts           | Uvicorn `--limit-max-requests`, body cap via middleware (1 MiB).   |
| Generic 5xx errors                | Error handler returns `{"error":"internal error","request_id":…}`. |
| Container hardening               | Non-root `USER 10001`, read-only FS, `cap_drop: ALL`, `no-new-privileges`, bound to `127.0.0.1`. |
| Dependency pinning                | `requirements.txt` with `==`; `pip-audit` command below.           |

Audit dependencies:

```sh
cd backend
pip install pip-audit==2.7.3
pip-audit -r requirements.txt
```

Generate an SBOM:

```sh
syft dir:. -o cyclonedx-json > sbom.cdx.json
```

## Credentials

This application needs **no credentials**. Nothing is declared in Vault.
If credentials are added later, declare each one with `declare_secret` and
load them via `app/vault_credentials.py` per the `vault-credentials` skill.

## Data handling

The app stores nothing, processes no personal data, and makes no outbound
calls. Classification: `public`.

## Project layout

```
hello-world-0/
├── app-inventory.yaml
├── CHANGELOG.md
├── Makefile
├── README.md
├── docker-compose.yml
├── .env.example
├── .dockerignore
├── .gitignore
└── backend/
    ├── Dockerfile
    ├── requirements.txt
    ├── app/
    │   ├── __init__.py
    │   ├── main.py
    │   ├── config.py
    │   ├── logging_config.py
    │   └── api/
    │       ├── __init__.py
    │       └── hello.py
    └── tests/
        ├── __init__.py
        ├── conftest.py
        └── test_hello.py
```
