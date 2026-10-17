# syntax=docker/dockerfile:1.7
# Build and run the Hello World 0 FastAPI service as a rootless container.

FROM docker.io/library/python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build

COPY requirements.txt ./
RUN pip install --prefix=/install -r requirements.txt


FROM docker.io/library/python:3.12-slim AS runtime

# OCI image metadata.
LABEL org.opencontainers.image.title="hello-world-0-backend" \
      org.opencontainers.image.description="Minimal FastAPI service that returns Hello World." \
      org.opencontainers.image.version="0.1.0" \
      org.opencontainers.image.source="https://example.invalid/apps/hello-world-0-478e0cc6"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Copy installed packages from the builder stage.
COPY --from=builder /install /usr/local

WORKDIR /app
COPY app ./app

# Non-root numeric user.
USER 10001:10001

EXPOSE 8080

CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8080", \
     "--proxy-headers", \
     "--timeout-keep-alive", "5"]
