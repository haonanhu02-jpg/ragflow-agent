# ragflow-agent

Independent Agent + RAG project. Phase 01 provides the Python package, typed
configuration, infrastructure boundaries, PostgreSQL migrations, FastAPI and
ingestion-worker process shells, tests, and a reproducible development
environment. Phase 02 adds a knowledge-independent LangGraph Agent runtime with
versioned state/events, structured model and Tool ports, bounded error handling,
tenant-scoped PostgreSQL checkpoints, trace events, and a deterministic minimal
Agent loop. Phase 03 adds versioned knowledge-domain contracts, first-version
tenant/owner/visibility authorization, tenant-scoped repositories and capability
ports, plus shared `KnowledgeService` and `KnowledgeQueryService` boundaries.
Phase 04 adds the minimum RAG vertical slice: PostgreSQL knowledge persistence,
S3/MinIO objects, Redis/ARQ ingestion, TXT/Markdown/PDF parsing, General
Chunking, provider-isolated DeepSeek/BGE-M3 adapters, Elasticsearch
BM25/KNN/RRF retrieval, fixed RAG, citations, retrieval trace, and real-backend
integration tests.

Complex parsing/OCR, full online retrieval and reranking, document lifecycle,
KnowledgeBaseTool, real-provider CI, HITL, memory, and multi-Agent behavior are
intentionally deferred to later phases.

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
