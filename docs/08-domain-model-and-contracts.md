---
document_id: DOMAIN-MODEL-AND-CONTRACTS
document_role: Phase 03 领域契约与 Phase 04-06 Adapter 落地事实
status: active
schema_version: 2
last_updated_at: "2026-07-31"
ragflow_frozen_baseline_commit: "cd846cc9d4e32a19e684c59a1f302601027ef976"
---

# 领域模型与统一契约

本文件记录 Phase 03 实际落地的领域语言、不可变量、状态机和端口，以及 Phase 04-06 对这些端口的真实 Adapter 与在线检索落地。代码与本文冲突时，以已通过测试的源码为事实，并在同一任务内修正文档。

导航：[项目主文档](./00-project-master.md) · [目标架构](./03-target-architecture.md) · [决策与风险](./07-decisions-and-risks.md) · [Phase 03](./phases/phase-03-knowledge-interface.md) · [Phase 04](./phases/phase-04-minimum-rag.md)

## 1. 边界和术语

| 术语 | 本项目含义 | 明确不表示 |
|---|---|---|
| `tenant_id` | 所有知识资源不可绕过的第一隔离键 | RAGFlow 中把用户 ID 注入 `tenant_id` 的兼容语义 |
| `actor_id` | 当前可信调用主体 | tenant、owner 或模型生成的身份 |
| `owner_id` | 资源在 tenant 内的所有者 | 跨 tenant 授权依据 |
| `visibility` | v1 的 `private` 或 `tenant` 可见性 | 复杂 RBAC、部门继承、动态规则 |
| `KnowledgeBase` | tenant-scoped 知识库聚合 | RAGFlow Peewee `Knowledgebase` 表 |
| `Document` | 逻辑文档聚合，维护当前版本引用 | 文件内容或解析结果本身 |
| `DocumentVersion` | 不可变内容版本及其处理状态 | 对 `Document` 原地覆盖 |
| `ParsedDocument` | Parser 的版本化、结构化输出 | 无约束 `dict` |
| `ParsedBlock` | 带顺序和来源坐标的最小解析单元 | 最终检索 Chunk |
| `ChunkRecord` | 绑定文档版本和来源 Block 的索引输入 | 搜索引擎内部文档 |
| `IngestionJob` | 一次文档版本构建请求的业务事实 | 队列 delivery |
| `IngestionTask` | Job 内一个确定阶段及 attempt | Worker 进程或队列消息 |
| `RetrievalQuery` | 固定 RAG 与 KnowledgeBaseTool 共用的后端无关查询协议 | Elasticsearch/OpenSearch DSL |
| `Citation` | 绑定 tenant、知识库、文档版本、Chunk 和来源坐标的引用 | 生成后拼接的无来源文本 |
| `IndexVersion` | 可构建、激活和回退的索引版本元数据 | 搜索引擎索引名本身 |

## 2. 聚合和依赖规则

1. `KnowledgeBase`、`Document`、`DocumentVersion`、`IngestionJob` 和 `IngestionTask` 都显式保存 `tenant_id`。
2. `Document` 必须属于同 tenant 的 `KnowledgeBase`；`DocumentVersion` 必须属于同 tenant 的 `Document`。
3. `Document.current_version_id` 只能指向同一文档、已就绪的 `DocumentVersion`。
4. Parser、Chunker、Embedding、Search、Queue 和对象存储只能实现 Phase 03 Ports；领域层不导入 FastAPI、SQLAlchemy、Redis、boto3、LangChain、LangGraph 或 RAGFlow。
5. 固定 RAG 和 Agent Tool 只能调用同一 `KnowledgeQueryService`；Phase 04 固定 RAG 已遵守，未来 Tool 仍不得旁路。
6. RAGFlow 源码仅作为用例和缺口证据；Phase 03 不直接复用 Peewee 模型、Service、全局 `settings` 或搜索 DSL。

## 3. 第一版权限规则

1. `AuthorizationContext` 只能由可信边界创建，至少含 `tenant_id`、`actor_id` 和 `request_id`。
2. 资源 `tenant_id` 与 context 不一致时，无论 owner 或 visibility 为何都拒绝。
3. `private` 资源只有 owner 可读写。
4. `tenant` 资源允许同 tenant 主体读取，只有 owner 可写、删除或管理。
5. 缺失 context、空身份、伪造 tenant 或未知 action 默认拒绝。
6. Phase 02 的 `AgentAuthorizationContext.user_id` 在未来知识库 Adapter 中映射为 `actor_id`；不得修改已持久化的 AgentState v1 来伪装共享模型已经存在。
7. 复杂 RBAC、部门权限、共享列表和动态数据规则保留在 `PermissionChecker` 接口后，Phase 10 前另行决策。

## 4. RAGFlow 事实依据

冻结 RAGFlow commit 为 `cd846cc9d4e32a19e684c59a1f302601027ef976`，本地快照版本为 `0.26.4`：

- `api/db/db_models.py::Knowledgebase` 有 `tenant_id`、`created_by`、`permission=me|team`；`Document` 只有 `kb_id/created_by`，`Task` 只有 `doc_id`，两者没有独立 `tenant_id`。
- `api/db/services/knowledgebase_service.py::_visibility_and_status_filter/accessible` 把 user、joined tenant 和 owner 语义混合在查询中。
- `api/utils/api_utils.py::add_tenant_id_to_kwargs` 把 `current_user.id` 写为 `tenant_id`，本项目明确不采用。
- `rag/nlp/search.py::Dealer.retrieval` 以 `tenant_ids` 推导索引名，再传 `kb_ids` 搜索；目标协议必须在进入 SearchPort 前完成可信 tenant 和权限约束。
- `common/doc_store/doc_store_base.py::{DocStoreConnection,MatchTextExpr,MatchDenseExpr,FusionExpr}` 只提供能力面参考，不进入领域协议。

## 5. 实际领域模型

所有 DTO 继承 `knowledge/domain/base.py::KnowledgeModel`，配置为 `extra=forbid` 和 `frozen=True`。非空标识会去除首尾空白；时间戳必须携带时区。

| 文件 | 实际类型/函数 | 关键不变量 |
|---|---|---|
| `domain/authorization.py` | `AuthorizationContext`、`ResourceAuthorization`、`Visibility`、`PermissionAction`、`PermissionDecision` | tenant 优先；`private|tenant`；默认拒绝 |
| `domain/knowledge_base.py` | `KnowledgeBase`、`KnowledgeBaseStatus` | tenant/owner/visibility 显式；ACTIVE/ARCHIVED |
| `domain/document.py` | `Document`、`DocumentVersion`、`transition_document_version`、`activate_document_version` | Document/Version 分离；ready 且同范围版本才能激活；时间不回退 |
| `domain/chunk.py` | `ParsedDocument`、`ParsedBlock`、`BoundingBox`、`ChunkRecord`、`derive_chunk_id/derive_chunk_id_v2` | schema v2；block 顺序/来源唯一；bbox 坐标系显式；General `sha256-v1` 兼容、场景策略 `sha256-v2` |
| `domain/ingestion.py` | `IngestionJob`、`IngestionTask`、`IngestionEnvelope`、`transition_ingestion`、`retry_ingestion_task` | tenant/job/version/attempt/idempotency/trace 完整；进度和时间单调；终态受控 |
| `domain/retrieval.py` | `RetrievalQuery/Result/Candidate`、`Citation`、`RetrievalTrace/Event`、`IndexVersion/Record` | query/trace/candidate/citation tenant 与 KB 范围一致；空结果有明确原因；索引记录绑定版本 |
| `domain/errors.py` | `KnowledgeAuthorizationError`、`KnowledgeNotFoundError`、`KnowledgeConflictError` | 稳定错误码，不依赖 HTTP 框架 |

### 5.1 DocumentVersion 状态机

```text
REGISTERED -> INGESTING -> READY -> SUPERSEDED -> DELETED
                    |         \---------------> DELETED
                    +-> FAILED -> INGESTING
                    |       \------------------> DELETED
                    \--------------------------> DELETED
```

- 重复设置当前状态是幂等操作。
- 非法边拒绝并返回 `document_version_transition_invalid`。
- 任何状态变更时间早于当前 `updated_at` 时拒绝。
- Phase 07 才实现完整更新、删除、候选索引切换和补偿，不得把本状态函数描述为生命周期已完成。

### 5.2 Ingestion 状态机

```text
PENDING -> RUNNING -> SUCCEEDED
    |          |  \-> FAILED --retryable--> RUNNING(attempt+1)
    |          \----> CANCELLED
    \---------------> CANCELLED
```

- `progress` 范围为 `[0,1]`，只能单调增加；成功必须为 `1`。
- 失败必须携带结构化 `IngestionError`，非失败状态不得携带 error。
- 只有 retryable FAILED task 能开始新 attempt，已有进度不回退。
- 队列 envelope 是传输协议，不是状态事实源。

## 6. 实际 Ports

| 文件 | Port | 责任和边界 |
|---|---|---|
| `ports/permission.py` | `PermissionChecker` | 集中处理 tenant/owner/visibility；Service/Tool/Adapter 不复制策略 |
| `ports/repositories.py` | 五类聚合 Repository | 所有 `get` 强制 `tenant_id + resource_id`，所有 `add` 强制 `tenant_id + entity` 并校验一致；无 `get_by_id/list_all` |
| `ports/uow.py` | `KnowledgeUnitOfWork/Factory` | 一次应用操作的 Repository 与 commit/rollback 边界 |
| `ports/storage.py` | `ObjectStoragePort` | tenant-namespaced key、流式 bytes、size/SHA-256 完整性 |
| `ports/parsing.py` | `ParserPort` | `ParseRequest -> ParsedDocument`，不泄漏格式库 |
| `ports/chunking.py` | `ChunkerPort` | `ParsedDocument + strategy identity -> ChunkRecord[]` |
| `ports/embedding.py` | `EmbeddingPort` | batch input、model ID、维度和 normalized 语义 |
| `ports/search.py` | `SearchIndexPort`、`RetrieverPort`、`RerankerPort` | 版本化写入、结构化检索和身份保持；无供应商 DSL |
| `ports/queue.py` | `IngestionQueuePort` | 发布完整 `IngestionEnvelope`；不定义具体 ACK/DLQ 实现 |
| `ports/trace.py` | `KnowledgeTracePort` | tenant/actor/request/trace/resource 关联事件 |

Phase 03 的 `tests/fakes/knowledge.py` 提供内存或 fixture Adapter，只证明契约可实现和可测试；它们不是生产基础设施。

## 7. 应用服务

`application/permission_service.py::DefaultPermissionChecker` 实现 ADR-018 的第一版权限矩阵。

`application/knowledge_service.py::KnowledgeService` 当前只提供：

1. `create_knowledge_base`：tenant 和 owner 只能来自可信 context。
2. `get_knowledge_base`：先执行 tenant-scoped Repository，再执行 READ 权限。
3. `register_document`：先验证 KB WRITE 权限，再在一个 UoW 中登记 Document 和首个 DocumentVersion。

`application/knowledge_service.py::KnowledgeQueryService.retrieve` 是固定 RAG 与未来 KnowledgeBaseTool 的唯一查询入口：

1. 拒绝 context/query tenant 不一致。
2. 逐一加载请求 KB 并执行 READ 权限。
3. 只在权限通过后调用 `RetrieverPort`。
4. 要求返回 Trace 明确记录 `authorization_applied=true`。

Phase 03 当时没有实现上传 API、对象存储 Adapter、Parser、Chunker、Embedding、搜索、Queue 消费、Prompt 或回答生成。Phase 04 随后在不修改领域协议的前提下落地这些能力的最小实现。

## 8. Agent 契约映射

Phase 02 Checkpoint 中的 `AgentAuthorizationContext` 仍是：

```text
tenant_id + user_id + request_id
```

知识领域 v1 使用：

```text
tenant_id + actor_id + request_id
```

未来 KnowledgeBaseTool Adapter 必须显式映射 `user_id -> actor_id`，保持 tenant/request 不变，并在每次调用及恢复后重新执行 `PermissionChecker`。禁止修改 AgentState v1 的已持久字段来绕过版本迁移。

## 9. 验证事实

Phase 03 已通过：

- Domain/Ports/Application 静态导入边界。
- tenant、owner、visibility 正负向矩阵。
- DocumentVersion 和 Ingestion Job/Task 合法/非法状态转换、进度/时间单调和重试。
- ParsedBlock/Chunk 稳定身份、来源、页码和坐标验证。
- Retrieval/Citation/Trace/Index schema 与 tenant/KB 范围验证。
- Repository/UoW commit、rollback、重复 ID 和跨 tenant 访问。
- Storage、Parser、Chunker、Embedding、SearchIndex、Retriever、Reranker、Queue、Trace 的可执行契约 Adapter。
- KnowledgeService 权限先行和 KnowledgeQueryService 不绕过 Retriever 权限。

完整命令与最终数量以 [Phase 03 执行记录](./phases/phase-03-knowledge-interface.md) 为准。

## 10. Phase 04/05/06 Adapter 落地与仍未实现

Phase 04 已实现：

- SQLAlchemy 五类知识业务表、Repository/UoW Adapter 和 Alembic `20260730_0002`。
- S3-compatible/MinIO ObjectStorage、Redis/ARQ Queue、TXT/Markdown/PDF Parser、General Chunker。
- BGE-M3 OpenAI-compatible Embedding Adapter、Elasticsearch 8.19 SearchIndex/Retriever、最小日志 Trace。
- 上传/Job API、Worker pipeline、BM25/KNN/RRF、固定 RAG、Citation/RetrievalTrace。
- Phase 05 的 `ParserRegistry`、八类 Binary Parser、`OcrEnginePort`/Tesseract、
  `ChunkerRegistry`、九种 Chunk Method、schema v2、资源门禁和
  Elasticsearch/Citation bbox 映射。
- Phase 06 的 Retrieval schema v2、`QueryTransformProviderPort`、`SearchChannelPort`、
  `RerankerPort`、`RetrievalTraceStorePort`、`OnlineRetrievalService`、递归 Filter AST、
  RRF/清理/有限降级、BGE Reranker HTTP Adapter、PostgreSQL Trace Store/清理和
  权限受限 Trace API。

仍未实现：

- KnowledgeBaseTool、完整 Agentic RAG。
- 模型型复杂多栏版面、GPU Vision、图片语义理解和模型型表格识别。
- 真实 DeepSeek、BGE-M3 和 BGE Reranker 服务/GPU 质量/性能验证。
- 文档更新、删除、重解析、索引版本原子切换、补偿和残留清理。
- 复杂 RBAC、部门权限、动态数据规则、可靠 outbox、跨存储补偿、取消/DLQ/批量与生命周期清理。
- 真实 DeepSeek/BGE-M3 smoke、模型注册/配额/降级；CI 只有 Fake/Stub Provider。
