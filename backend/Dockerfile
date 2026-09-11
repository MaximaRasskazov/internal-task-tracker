FROM ghcr.io/astral-sh/uv:0.12.3 AS uv
FROM python:3.13-slim-bookworm AS base
COPY --from=uv /uv /uvx /bin/
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/app/.venv/bin:$PATH"
WORKDIR /app

FROM base AS dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY app ./app
COPY alembic.ini ./
COPY migrations ./migrations
RUN uv sync --frozen --no-dev

FROM dependencies AS init-env
ENTRYPOINT ["python", "-m", "app.cli.init_env"]
CMD ["--output", "/workspace/.env"]

FROM base AS runtime
RUN groupadd --system app && useradd --system --gid app --home-dir /app app
COPY --from=dependencies --chown=app:app /app /app
USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log"]
