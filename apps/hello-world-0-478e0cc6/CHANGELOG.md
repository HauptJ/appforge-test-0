# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] - 2025-01-01
### Added
- Initial FastAPI backend with a single `/api/v1/hello` endpoint.
- `/healthz` and `/readyz` probes.
- Structured JSON logging with per-request IDs and credential redaction.
- Security headers middleware and request-body size limit.
- Rootless container image and Docker/Podman compose file.
- Pytest suite covering success and health probes.
