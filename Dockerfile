FROM python:3.13-alpine3.21 AS dependencies

# operate in "unbuffered" mode for stdout and stderr
ENV PYTHONUNBUFFERED=1
#  install uv by copying the binary from the official distroless
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /uvx /bin/
ENV UV_COMPILE_BYTE=1
ENV UV_LINK_MODE=copy

WORKDIR /src
ENV UV_PROJECT_ENVIRONMENT=/src/.venv
COPY ./pyproject.toml ./uv.lock ./.python-version ./

# INSTALL DEPS
RUN --mount=type=cache,target=/root/.cache/uv \
--mount=type=bind,source=uv.lock,target=uv.lock \
--mount=type=bind,source=pyproject.toml,target=pyproject.toml \
uv sync --frozen --no-install-project --no-dev

ENV PATH="/src/.venv/bin:$PATH"

FROM dependencies AS base

WORKDIR /src

# Copy the project into image
COPY ./ ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev


CMD ["uv", "run", "-m", "app"]


FROM dependencies AS test
RUN addgroup --system --gid 1001 appuser && \
    adduser --system --uid 1001 appuser

RUN chown -R appuser:appuser /src/.venv
USER appuser

WORKDIR /src
ENV UV_PROJECT_ENVIRONMENT=/src/.venv

RUN uv sync --frozen --no-editable

COPY --chown=appuser:appuser ./tests ./tests
COPY --chown=appuser:appuser ./app ./app
COPY --chown=appuser:appuser ./migrations ./migrations 
COPY --chown=appuser:appuser ./alembic.ini ./alembic.ini
COPY --chown=appuser:appuser ./pyproject.toml ./pyproject.toml

ENV PATH="/src/.venv/bin:$PATH"
CMD ["pytest", "-v"]

