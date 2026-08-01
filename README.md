# ragflow-agent

Independent Agent + RAG backend built with FastAPI, LangChain and LangGraph.
The Phase 00-10 roadmap now includes tenant-scoped knowledge domains,
multi-format ingestion and OCR, Elasticsearch hybrid retrieval, fixed RAG,
Agentic RAG with governed Tools/HITL/memory/budgets, versioned lifecycle,
experimental advanced RAG, deterministic evaluation, observability and a Linux
Docker Compose production candidate.

This is not yet approved for real production. Advanced capabilities remain
experimental/off, real DeepSeek/BGE/Vision/ASR and representative business data
have not been validated, and production IdP, secrets, network, sustained SLO,
capacity and recovery evidence remain open. UI/admin console is not implemented.
See [`reports/phase10/release-report.json`](reports/phase10/release-report.json).

## Project entrypoints

Read [`AGENTS.md`](AGENTS.md), then
[`docs/00-project-master.md`](docs/00-project-master.md) and the current phase
plan before changing code.

## Local quality checks

```powershell
uv sync --frozen --all-groups
uv run ruff check .
uv run mypy src/ragflow_agent tests
uv run pytest
uv run python -m ragflow_agent.bootstrap.api --check
uv run python -m ragflow_agent.bootstrap.ingestion_worker --check
```

All dependencies are installed in the project `.venv`.

## Development containers

Copy `.env.example` to `.env`, replace every `change-me` value, then run:

```powershell
docker compose -f docker-compose.dev.yml config
docker compose -f docker-compose.dev.yml up -d postgres redis minio elasticsearch --wait
uv run alembic upgrade head
docker compose -f docker-compose.dev.yml up -d --build api worker --wait
docker compose -f docker-compose.dev.yml down
```

The topology contains PostgreSQL, Redis, MinIO, Elasticsearch, the API, and a
real ARQ ingestion Worker using the same application image. BGE-M3 is expected
at the configured OpenAI-compatible endpoint; DeepSeek credentials remain
optional until a fixed-RAG answer is requested. To remove development data, use
the explicit destructive command
`docker compose -f docker-compose.dev.yml down --volumes` only after confirming
that the named development volumes are no longer needed.
