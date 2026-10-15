# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] - initial

### Added
- FastAPI backend with `/api/v1/hello` returning a personalised greeting for the signed-in user.
- React + TypeScript (Vite) frontend showing the greeting and sign-in / sign-out controls.
- OIDC Authorization Code + PKCE login against the organization IdP, server-side sessions
  with signed cookies, idle + absolute timeouts, session rotation at login.
- Double-submit CSRF protection, Origin allowlist, strict security headers,
  structured JSON logging with request IDs and redaction.
- Vault AppRole credential loader; two credentials declared: `oidc-client-secret`
  (owner-set) and `session-signing-key` (generated).
- Rootless OCI containers for backend and frontend, compose file with health checks,
  read-only root FS, dropped capabilities and no-new-privileges.
- Pytest + Vitest test suites.
