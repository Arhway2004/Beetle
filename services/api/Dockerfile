# Build from the repository root:  docker build -f services/api/Dockerfile .
FROM python:3.13-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /usr/local/bin/uv
WORKDIR /app

# Only the inputs the API needs: its own source, shared types, and migrations.
COPY packages/shared-types /app/packages/shared-types
COPY packages/api-contracts/schemas /app/packages/api-contracts/schemas
COPY database /app/database
COPY services/api /app/services/api

WORKDIR /app/services/api
RUN uv sync --frozen --no-dev
RUN useradd --system --uid 10001 app
USER app
EXPOSE 8000
CMD ["uv", "run", "--no-sync", "uvicorn", "beetle_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
