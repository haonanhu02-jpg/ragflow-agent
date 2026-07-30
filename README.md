# ragflow-agent

Independent Agent + RAG project. Phase 01 provides the Python package, typed
configuration, infrastructure boundaries, PostgreSQL migrations, FastAPI and
ingestion-worker process shells, tests, and a reproducible development
environment. Phase 02 adds a knowledge-independent LangGraph Agent runtime with
versioned state/events, structured model and Tool ports, bounded error handling,
tenant-scoped PostgreSQL checkpoints, trace events, and a deterministic minimal
Agent loop.

Knowledge-base domains, ingestion, parsing, chunking, embedding, indexing,
retrieval, fixed RAG, KnowledgeBaseTool, real model providers, HITL, memory, and
multi-Agent behavior are intentionally not implemented yet.

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
docker compose -f docker-compose.dev.yml up --build --wait
docker compose -f docker-compose.dev.yml down
```

The topology contains PostgreSQL, Redis, MinIO, the API, and a non-consuming
Worker shell using the same application image. The shell runs only through the
explicit development-only flag and cannot acknowledge or reject tasks. Phase 01
does not select a search backend and does not run an ingestion implementation. To remove
development data, use the explicit destructive command
`docker compose -f docker-compose.dev.yml down --volumes` only after confirming
that the named development volumes are no longer needed.
