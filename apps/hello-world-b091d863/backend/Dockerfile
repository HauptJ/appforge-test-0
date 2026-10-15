# syntax=docker/dockerfile:1.7
FROM docker.io/library/python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build
COPY requirements.txt ./
RUN pip install --prefix=/install -r requirements.txt


FROM docker.io/library/python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/install/bin:${PATH}" \
    PYTHONPATH="/install/lib/python3.12/site-packages"

LABEL org.opencontainers.image.title="hello-world-backend" \
      org.opencontainers.image.description="Hello World FastAPI backend" \
      org.opencontainers.image.version="0.1.0" \
      org.opencontainers.image.source="apps/hello-world-b091d863"

WORKDIR /app
COPY --from=builder /install /install
COPY app ./app

RUN useradd --system --uid 10001 --no-create-home appuser

USER 10001:10001

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.asgi:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "15"]
