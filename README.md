# ragflow-agent

`ragflow-agent` 是一个可独立运行的 LangChain + LangGraph Agent + RAG 后端。项目以
RAGFlow 的知识库能力、职责划分和行为为功能蓝本，通过项目自己的领域模型、Ports、
Adapters 和服务实现整合；当前仓库没有复制、抽取或改写 RAGFlow 源码。

Phase 00 至 Phase 10 以及当前约定的后端源码范围已经完成。项目可在本地电脑或用户自行
管理的 Linux 云服务器上运行 API、Ingestion Worker、离线知识库构建、固定 RAG 和
Agentic RAG。高级 RAG 能力默认关闭或保持 `experimental`，不会影响普通 RAG 路径。

## 已实现能力

- FastAPI 模块化单体和独立 Redis/ARQ Ingestion Worker。
- PostgreSQL 权威元数据、MinIO/S3 对象、Elasticsearch 全文/向量/混合检索。
- PDF、DOCX、PPTX、XLSX、TXT、Markdown、HTML、图片解析，Tesseract OCR 和九种 Chunk 策略。
- 查询处理、RRF、可选 BGE Reranker、安全降级、Citation 和 Retrieval Trace。
- LangGraph Agent、直接 RAG、知识库 Tool、只读 SQL/API Tool、HITL、记忆、预算和 Agent Trace。
- 文档更新、删除、恢复、重解析、重建索引、Outbox、补偿与对账。
- 默认关闭的关键词、问题、摘要、TOC、父子 Chunk、多模态、GraphRAG、RAPTOR 和时序 RAG。
- 确定性评测、回归门禁、JSON/OTel/Prometheus 可观测性、安全、备份恢复和故障演练工具。

## 前置条件

- Python 3.13
- [uv](https://docs.astral.sh/uv/)
- Docker Engine 或 Docker Desktop（用于 PostgreSQL、Redis、MinIO、Elasticsearch，也可运行整个项目）
- 一个 OpenAI-compatible Chat 服务或 API，以及一个 OpenAI-compatible Embedding 服务
- 可选：BGE-compatible `/rerank` 服务、Tesseract OCR 运行时

仓库不保存模型密钥。Chat、Embedding 和 Reranker 都经过内部 Provider Port；没有配置
Reranker 时检索会明确降级到 RRF，不会把未配置状态冒充成真实重排。

## 配置模型

复制配置模板并替换所有 `change-me`：

```powershell
Copy-Item .env.example .env
```

Linux：

```bash
cp .env.example .env
```

至少检查以下变量：

```dotenv
RAGFLOW_AGENT_MODELS__CHAT_MODEL=deepseek-chat
RAGFLOW_AGENT_MODELS__CHAT_BASE_URL=https://api.deepseek.com
RAGFLOW_AGENT_MODELS__CHAT_API_KEY=your-runtime-secret
RAGFLOW_AGENT_MODELS__EMBEDDING_MODEL=BAAI/bge-m3
RAGFLOW_AGENT_MODELS__EMBEDDING_BASE_URL=http://localhost:8080/v1
RAGFLOW_AGENT_MODELS__EMBEDDING_DIMENSIONS=1024
RAGFLOW_AGENT_MODELS__RERANKER_MODEL=BAAI/bge-reranker-v2-m3
RAGFLOW_AGENT_MODELS__RERANKER_BASE_URL=http://localhost:8081/rerank
RAGFLOW_AGENT_MODELS__RERANKER_API_KEY=
```

DeepSeek 只是默认 Chat profile；可以把模型名、URL 和凭据改成自己的 OpenAI-compatible
服务。Embedding 返回维度必须与 `EMBEDDING_DIMENSIONS` 一致。容器访问宿主模型时使用
`http://host.docker.internal:<port>`；Compose 已为 Linux 添加 `host-gateway` 映射。

## 方式一：`.venv` 运行 API 和 Worker

安装依赖并启动基础设施：

```powershell
uv sync --frozen --all-groups
docker compose -f docker-compose.dev.yml up -d postgres redis minio elasticsearch --wait
uv run alembic upgrade head
```

分别打开两个终端：

```powershell
uv run python -m ragflow_agent.bootstrap.api
```

```powershell
uv run python -m ragflow_agent.bootstrap.ingestion_worker
```

检查 API：

```powershell
Invoke-RestMethod http://localhost:8000/health/live
Invoke-RestMethod http://localhost:8000/health/ready
```

## 方式二：Docker Compose 运行完整项目

`.env` 中的模型 URL 必须从容器内可达。然后执行：

```powershell
docker compose -f docker-compose.dev.yml config --quiet
docker compose -f docker-compose.dev.yml build api worker
docker compose -f docker-compose.dev.yml run --rm api alembic upgrade head
docker compose -f docker-compose.dev.yml up -d api worker --wait
docker compose -f docker-compose.dev.yml ps
```

Linux 使用同一组命令。停止服务但保留数据：

```bash
docker compose -f docker-compose.dev.yml down
```

只有确认开发数据不再需要时，才使用 `down --volumes` 删除命名卷。

## 从文件到问答

以下 PowerShell 示例使用开发环境受信身份头。生产模式必须由受信网关或身份适配器写入
同等身份上下文，不能信任来自公网的任意身份头。

```powershell
$BaseUrl = "http://localhost:8000"
$Headers = @{
  "X-Tenant-Id" = "tenant-demo"
  "X-Actor-Id" = "user-demo"
  "X-Roles" = "reader,retrieval_debug"
}

# 1. 创建知识库
$Kb = Invoke-RestMethod -Method Post -Uri "$BaseUrl/v1/knowledge-bases" `
  -Headers $Headers -ContentType "application/json" `
  -Body '{"name":"运维知识库","description":"本地示例","visibility":"tenant"}'
$KbId = $Kb.id

# 2. 上传自己的文件；支持 PDF/DOCX/PPTX/XLSX/TXT/Markdown/HTML/图片
$UploadJson = curl.exe -sS -X POST "$BaseUrl/v1/knowledge-bases/$KbId/documents" `
  -H "X-Tenant-Id: tenant-demo" -H "X-Actor-Id: user-demo" `
  -H "Idempotency-Key: upload-demo-001" -F "file=@D:\docs\manual.pdf"
$Upload = $UploadJson | ConvertFrom-Json
$JobId = $Upload.job_id

# 3. 等待 Worker 完成解析、Chunk、Embedding 和索引写入
do {
  Start-Sleep -Seconds 2
  $Job = Invoke-RestMethod -Uri "$BaseUrl/v1/ingestion-jobs/$JobId" -Headers $Headers
  $Job | Select-Object status, progress, error
} while ($Job.status -in @("pending", "running"))
if ($Job.status -ne "succeeded") { throw "Ingestion failed: $($Job | ConvertTo-Json -Depth 8)" }

# 4. 固定 RAG 问答
$Question = @{
  question = "该设备复位前需要检查什么？"
  knowledge_base_ids = @($KbId)
  top_k = 20
  top_n = 5
} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "$BaseUrl/v1/rag/query" `
  -Headers $Headers -ContentType "application/json" -Body $Question

# 5. Agentic RAG；Router 可走直接 RAG，也可选择知识库 Tool
$AgentRequest = @{
  question = "比较手册中的复位条件并给出带引用的检查步骤"
  knowledge_base_ids = @($KbId)
  thread_id = "demo-thread-001"
} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "$BaseUrl/v1/agentic-rag/runs" `
  -Headers $Headers -ContentType "application/json" -Body $AgentRequest
```

接口响应会保留 `citation`、`trace_id`、证据状态和错误类型。Swagger 文档位于
`http://localhost:8000/docs`。生命周期、HITL 恢复、长期记忆和 Trace 接口也可在该页面
直接查看 Schema。

## Linux 自有云部署

开发 Compose 可直接用于单机验证。需要 hardened 配置时，复制
`deploy/production.env.example` 到仓库外，填入自己的基础设施和模型配置，然后按
[`docs/10-production-runbook.md`](docs/10-production-runbook.md) 使用
`deploy/docker-compose.prod.yml`。生产候选使用同一镜像分别启动 API 和 Worker，并以一次性
`migrate` Job 执行 Alembic。Kubernetes、私有镜像仓库、ARM64 和前端不属于当前完成范围。

## 验证

```powershell
uv lock --check
uv sync --frozen --all-groups
uv pip check
uv run ruff check .
uv run mypy src/ragflow_agent tests
uv run pytest
uv run python -m ragflow_agent.bootstrap.api --check
uv run python -m ragflow_agent.bootstrap.ingestion_worker --check
docker compose -f docker-compose.dev.yml config --quiet
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/production.env.example config --quiet
```

CI 使用 Fake/Stub Provider 保持确定性；真实模型由用户在实际运行环境配置。Docker Scout
在线扫描需要外部账号，属于可选检查，不是本地或自有云运行门槛。项目有意不设置顶层
`LICENSE`；第三方依赖、数据集、模型和外部资源的许可证与 provenance 记录仍须保留。

## 项目状态与范围

Phase 00至Phase 10以及当前约定的Agent＋RAG后端源码范围已经完成。项目已达到本地或自有云部署运行条件。企业系统接入、真实业务效果验证和长期运营指标属于后续使用或可选扩展，不属于当前项目完成阻断项。机器可读结论见
[`reports/phase10/release-report.json`](reports/phase10/release-report.json)。真实企业系统接入、
真实业务效果验证、长期 SLO、正式运维组织、企业 SSO、UI/管理控制台和平台扩展属于后续
使用或可选范围，不是当前项目完成阻断项。

开发前先阅读 [`AGENTS.md`](AGENTS.md)、
[`docs/00-project-master.md`](docs/00-project-master.md) 和对应阶段记录。
