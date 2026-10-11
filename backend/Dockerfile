# One image for `api` and `worker` (ADR 0004).
FROM ghcr.io/astral-sh/uv:0.13.0 AS uv

FROM python:3.14.8-slim-trixie
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY src ./src
RUN uv sync --locked --no-dev
RUN useradd --system --uid 10001 tart
USER tart
EXPOSE 8000
CMD ["uvicorn", "tart.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
