FROM ghcr.io/astral-sh/uv@sha256:ff07b86af50d4d9391d9daf4ff89ce427bc544f9aae87057e69a1cc0aa369946 AS uv

FROM python@sha256:9d7f287598e1a5a978c015ee176d8216435aaf335ed69ac3c38dd1bbb10e8d64 AS runtime

ARG VCS_REF=unknown
LABEL org.opencontainers.image.title="ragflow-agent" \
      org.opencontainers.image.source="https://github.com/haonanhu02-jpg/ragflow-agent" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.licenses="NOASSERTION"

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY --from=uv /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY alembic.ini ./
COPY migrations ./migrations
COPY src ./src
RUN uv sync --frozen --no-dev

RUN addgroup --system ragflow-agent \
    && adduser --system --ingroup ragflow-agent --home /app ragflow-agent \
    && chown -R ragflow-agent:ragflow-agent /app

USER ragflow-agent

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=2)" || exit 1

CMD ["python", "-m", "ragflow_agent.bootstrap.api"]
