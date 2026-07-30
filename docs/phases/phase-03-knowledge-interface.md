---
document_id: PHASE-03-KNOWLEDGE-INTERFACE
document_role: Phase 03 执行记录
status: completed
phase: Phase 03
phase_name: 知识库统一接口
plan_status: 已确认
execution_status: 已完成
last_updated_at: "2026-07-30"
ragflow_frozen_baseline_commit: "cd846cc9d4e32a19e684c59a1f302601027ef976"
---

# Phase 03：知识库统一接口详细计划

## 0. 状态与导航

- **计划状态**：已确认；用户授权在 Phase 02 闭环和准入满足后连续执行全部 Phase 03。
- **执行状态**：已完成；P03-T01 至 P03-T11 和完整阶段验收均通过。
- 已按 Phase 02 的 `AgentAuthorizationContext`、Tool/Checkpoint 边界和实际包结构复审；统一知识权限模型不会修改 AgentState v1，后续 Adapter 显式映射 `user_id → actor_id`。
- 导航：[阶段索引](./README.md) · [Phase 02](./phase-02-agent-foundation.md) · [Phase 04](./phase-04-minimum-rag.md) · [能力矩阵](../02-ragflow-capability-matrix.md)

## 1. 目标、背景与 Phase 00 依据

目标是建立固定 RAG、Agent Tool、API、Worker 和基础设施共同使用的知识库领域模型、服务、Repository/Storage/检索协议及第一版权限边界。

必要性与事实：

1. RAGFlow `Knowledgebase`、`Document`、`Task` 是 Peewee 产品模型，Document/Task 没有独立 `tenant_id`，Chunk 是搜索文档；不可复制为目标领域。
2. `Knowledgebase.permission=me|team`、`KnowledgebaseService.accessible` 和 `add_tenant_id_to_kwargs` 混合 tenant/user/owner 语义，目标必须自研。
3. `DocStoreConnection`、`MatchTextExpr`、`MatchDenseExpr`、`FusionExpr` 可提供 SearchPort 用例，但后端语义不同。
4. ADR-009 要求固定 RAG 与 KnowledgeBaseTool 共用 `KnowledgeQueryService`；ADR-012 要求 tenant 强隔离。

## 2. 前置阶段、进入条件和输入

- **前置阶段**：Phase 02。
- **进入条件**：Phase 02 DoD；Agent 侧 `AuthorizationContext` 传递和 Tool 边界稳定；本计划复审确认。
- **输入**：目标架构、工程标准、能力矩阵 CAP-03/CAP-16/CAP-41、Phase 00 源码地图、Phase 01 数据库基础和 Phase 02 Agent 契约。

## 3. 范围、排除和交付物

**范围**：

- KnowledgeBase、Document、DocumentVersion、ParsedDocument、ParsedBlock、ChunkRecord、IngestionTask/Job。
- Citation、RetrievalQuery/Result/Candidate/Trace、IndexRecord/IndexVersion。
- KnowledgeService、Repository、ObjectStorage、Parser、Chunker、Embedding、SearchIndex、Retriever、Reranker、TaskQueue、PermissionChecker、Trace Ports。
- `AuthorizationContext`、owner/visibility、tenant-scoped 不变量与状态机。

**不包含**：具体数据库表完成实现、Parser、Embedding、搜索 DSL、队列库、固定回答、真实 KB Tool、复杂 RBAC/部门/动态规则。

**交付物**：领域/端口源码、状态机、契约测试套件、`docs/08-domain-model-and-contracts.md`、错误和权限不变量。

## 4. 目标模块与文件

```text
src/ragflow_agent/knowledge/
  domain/{knowledge_base,document,chunk,ingestion,retrieval,authorization}.py
  application/{knowledge_service,permission_service}.py
  ports/{repositories,storage,parsing,chunking,embedding,search,queue,permission,trace}.py
tests/{unit,contract}/knowledge/
docs/08-domain-model-and-contracts.md
```

## 5. RAGFlow 源码、调用关系与复用方式

| 源码 | 事实/调用关系 | 采用 |
|---|---|---|
| `api/db/db_models.py` | `Tenant`、`UserTenant`、`Knowledgebase`、`Document`、`File`、`Task` | 产品用例参考；领域自行开发 |
| `api/db/services/knowledgebase_service.py` | `_visibility_and_status_filter`、`accessible` | 权限用例/反例参考 |
| `api/utils/api_utils.py::add_tenant_id_to_kwargs` | 将请求身份注入参数 | 明确不采用其 tenant=user 语义 |
| `common/doc_store/doc_store_base.py` | `DocStoreConnection` 和搜索表达式 | 参考 SearchPort 能力面 |
| `rag/nlp/search.py::index_name/Dealer.retrieval` | tenant_ids → index → KB 过滤 → candidates | 参考检索协议和 tenant 风险 |
| `FileService.upload_document` → `DocumentService.run` → `TaskService.queue_tasks` | 上传、文档、任务用例 | 参考状态与服务边界 |

- **直接复用**：无。
- **`ragflow_adapters` 改造复用**：本阶段无实现；只为未来 Adapter 定义端口。
- **参考后自研**：全部领域模型、状态机、权限和协议。
- **明确不采用**：Peewee 模型/Service、全局 settings、无 tenant 的通用 `get_by_id`。

## 6. LangGraph、LangChain和自研职责

- **LangGraph**：只消费版本化 Retrieval DTO/AuthorizationContext，不负责知识生命周期。
- **LangChain**：标准 Document/Embeddings/Retriever 接口只作适配参考，不替代领域模型。
- **自研**：所有实体、端口、状态机、权限、Citation/Trace/Index 协议和契约测试。

## 7. 任务总表

| 任务 | 名称 | 状态 | 前置 |
|---|---|---|---|
| P03-T01 | 复审领域语言与边界 | 已完成 | Phase 02 |
| P03-T02 | 定义 AuthorizationContext 与 PermissionChecker | 已完成 | P03-T01 |
| P03-T03 | 定义 KnowledgeBase、Document 与 Version | 已完成 | P03-T01、P03-T02 |
| P03-T04 | 定义 ParsedDocument、Block 与 ChunkRecord | 已完成 | P03-T03 |
| P03-T05 | 定义 IngestionTask/Job 状态机 | 已完成 | P03-T03 |
| P03-T06 | 定义检索、Citation、Trace 与索引协议 | 已完成 | P03-T02、P03-T04 |
| P03-T07 | 定义 Repository 与 UnitOfWork | 已完成 | P03-T02、P03-T03、P03-T05 |
| P03-T08 | 定义 Storage/Parser/Chunk/Embedding/Search/Queue Ports | 已完成 | P03-T04 至 P03-T07 |
| P03-T09 | 定义 KnowledgeService 应用边界 | 已完成 | P03-T02 至 P03-T08 |
| P03-T10 | 建立契约与权限负向测试 | 已完成 | P03-T02 至 P03-T09 |
| P03-T11 | 固化契约文档并执行出口审查 | 已完成 | P03-T01 至 P03-T10 |

## 8. 具体任务

### P03-T01：复审领域语言与边界

- **状态**：已完成
- **目标**：冻结术语、聚合、ID、时间和模块依赖。
- **为什么需要**：避免把 RAGFlow 数据库表或 LangChain Document 当领域模型。
- **输入**：Phase 02 产物、目标架构、RF-D01 至 RF-D07。
- **前置任务**：Phase 02 完成。
- **操作步骤**：检查源码；建立术语表；划分聚合/值对象；确认命名和包路径；修订本计划。
- **涉及文件**：`docs/08-domain-model-and-contracts.md`、本文件。
- **预期输出**：领域边界与术语清单。
- **RAGFlow 源码依据**：`db_models.py::{Knowledgebase,Document,Task}`；Chunk 非关系表。
- **实现或复用方式**：参考后自研。
- **测试方法**：架构/术语评审。
- **验证命令**：`uv run pytest tests/unit/import_boundaries -q`
- **验收标准**：领域层无框架/基础设施类型。
- **风险和回滚方法**：边界过大时拆值对象，不拆微服务。
- **实际执行结果**：读取 Phase 02 实际 AgentState/Tool/Checkpoint 契约和 RAGFlow 0.26.4 源码，冻结 `tenant_id`、`actor_id`、`owner_id`、`private|tenant` visibility、Document/Version 分离、Parsed/Chunk、Ingestion Job/Task、Retrieval/Citation/Trace/Index 术语及 `src/ragflow_agent/knowledge/{domain,application,ports}` 边界；创建 `docs/08-domain-model-and-contracts.md`。统一权限模型不会修改 AgentState v1，未来 Adapter 显式映射 `user_id → actor_id`。
- **实际验证结果**：通过。最终复核时 `uv run pytest tests/unit/import_boundaries -q` 为 `7 passed`；现有 Agent/共享/基础设施边界无回归。
- **计划偏差**：Phase 03 不把共享授权 DTO 放入 `shared/`，而在 `knowledge/domain` 定义知识资源授权语义；Agent 快照保持版本兼容。

### P03-T02：定义 AuthorizationContext 与 PermissionChecker

- **状态**：已完成
- **目标**：实现 tenant、actor、owner、visibility 的统一授权契约。
- **为什么需要**：权限必须先于 Repository、Search、Tool 和 Citation。
- **输入**：ADR-012、Phase 02 权限传递。
- **前置任务**：P03-T01。
- **操作步骤**：定义可信 context；确定 visibility v1 枚举；定义默认拒绝；建立 PermissionChecker Protocol 和决策结果；禁止模型/请求覆盖 tenant。
- **涉及文件**：`domain/authorization.py`、`ports/permission.py`、测试。
- **预期输出**：第一版授权契约。
- **RAGFlow 源码依据**：`Knowledgebase.permission`、`accessible`、`add_tenant_id_to_kwargs`。
- **实现或复用方式**：自行开发。
- **测试方法**：tenant/owner/visibility 组合、伪造 ID、缺 context。
- **验证命令**：`uv run pytest tests/unit/knowledge/test_authorization.py -q`
- **验收标准**：跨租户永远拒绝；复杂 RBAC 未伪实现。
- **风险和回滚方法**：策略错误默认拒绝；枚举变更走迁移/ADR。
- **实际执行结果**：实现严格不可变 `AuthorizationContext`、`ResourceAuthorization`、`Visibility(private|tenant)`、`PermissionAction`、`PermissionDecision`、`PermissionChecker` Protocol 和 `DefaultPermissionChecker`；跨租户优先拒绝，owner 在同 tenant 内可管理，tenant visibility 只向非 owner 开放读取，其他路径默认拒绝。
- **实际验证结果**：通过。`uv run pytest tests/unit/knowledge/test_authorization.py -q` 为 `8 passed`；专项 ruff 和 strict mypy 通过。
- **计划偏差**：第一版没有添加 role/RBAC 字段，避免把复杂权限伪实现为字符串列表；扩展保持在 `PermissionChecker` 端口后。

### P03-T03：定义 KnowledgeBase、Document 与 DocumentVersion

- **状态**：已完成
- **目标**：定义知识库、文档和不可变版本聚合及状态。
- **为什么需要**：更新、引用和索引激活必须绑定版本。
- **输入**：P03-T01、P03-T02。
- **前置任务**：P03-T01、P03-T02。
- **操作步骤**：定义 ID/tenant/owner/visibility；内容哈希/MIME；version 状态；current_version 规则；领域错误。
- **涉及文件**：`domain/{knowledge_base,document}.py`、测试。
- **预期输出**：领域实体 v1。
- **RAGFlow 源码依据**：RAGFlow Document 原地字段只作反例。
- **实现或复用方式**：自行开发。
- **测试方法**：构造不变量、状态转换、跨 tenant 关联。
- **验证命令**：`uv run pytest tests/unit/knowledge/test_document.py -q`
- **验收标准**：Document/Version 分离；所有聚合显式 tenant。
- **风险和回滚方法**：状态过细时保留兼容映射，不删除审计状态。
- **实际执行结果**：实现 tenant-scoped `KnowledgeBase`、逻辑 `Document`、不可变内容 `DocumentVersion`、显式 owner/visibility、时区时间、内容哈希/媒体类型/对象键，以及 REGISTERED→INGESTING→READY/FAILED→SUPERSEDED/DELETED 的受控版本状态转换和 ready 同范围版本激活规则。
- **实际验证结果**：通过。最终复核时 `uv run pytest tests/unit/knowledge/test_document.py -q` 为 `7 passed`；专项 ruff 和 strict mypy 通过。
- **计划偏差**：Phase 03 只建立必要状态和不变量；完整更新、删除、补偿和索引激活生命周期仍属于 Phase 07。

### P03-T04：定义 ParsedDocument、ParsedBlock 与 ChunkRecord

- **状态**：已完成
- **目标**：统一 Parser 输出、来源坐标和索引 Chunk。
- **为什么需要**：多格式、Citation 和稳定 Chunk ID 依赖同一协议。
- **输入**：P03-T03、CAP-03。
- **前置任务**：P03-T03。
- **操作步骤**：定义 block 类型、页码/bbox/order/heading/table/image；定义 Chunk/source_block_ids/parent；版本化 ID 算法接口。
- **涉及文件**：`domain/chunk.py`、`ports/parsing.py`、测试。
- **预期输出**：Parsed/Chunk DTO v1。
- **RAGFlow 源码依据**：DeepDOC sections/positions/tables/images 字段。
- **实现或复用方式**：自行开发，未来 Adapter 映射。
- **测试方法**：序列化、坐标、来源顺序、稳定 ID 样例。
- **验证命令**：`uv run pytest tests/unit/knowledge/test_chunk_contract.py -q`
- **验收标准**：不使用无约束 raw dict；来源字段完整。
- **风险和回滚方法**：扩展字段采用版本化可选结构。
- **实际执行结果**：实现 ParsedDocument/Chunk schema v1、六类 `BlockKind`、显式页码/坐标系/bbox、类型化表格与图片元数据、严格顺序/唯一来源约束、Chunk 来源 Block/父 Chunk/页范围元数据及 `sha256-v1` 稳定 Chunk ID；定义 ParserPort 和 tenant-scoped ParseRequest。
- **实际验证结果**：通过。`uv run pytest tests/unit/knowledge/test_chunk_contract.py -q` 为 `6 passed`；专项 ruff 和 strict mypy 通过。
- **计划偏差**：Phase 03 未实现具体 Parser 或 Chunk 策略；仅固化 Phase 05 Adapter 必须输出的协议。

### P03-T05：定义 IngestionTask/Job 状态机

- **状态**：已完成
- **目标**：定义请求、阶段、attempt、进度、取消、成功和失败。
- **为什么需要**：Worker 消息不能成为业务事实源。
- **输入**：P03-T03、工程标准第 15 节。
- **前置任务**：P03-T03。
- **操作步骤**：定义 Job/Task/envelope；状态转移；单调进度；错误分类；idempotency/trace/tenant 字段。
- **涉及文件**：`domain/ingestion.py`、测试。
- **预期输出**：任务协议 v1。
- **RAGFlow 源码依据**：`TaskService.queue_tasks/get_task` 及 Task 缺 tenant 的缺口。
- **实现或复用方式**：自行开发。
- **测试方法**：合法/非法转换、重复消息、取消竞态。
- **验证命令**：`uv run pytest tests/unit/knowledge/test_ingestion_state.py -q`
- **验收标准**：消息含 tenant/job/version；状态事实在数据库。
- **风险和回滚方法**：新增状态保持终态兼容；非法转换拒绝。
- **实际执行结果**：实现 schema v1 的 tenant-scoped `IngestionJob`、`IngestionTask`、五阶段枚举、PENDING/RUNNING/SUCCEEDED/FAILED/CANCELLED 状态机、单调进度、结构化 retryable error、attempt 重试和携带 tenant/job/task/version/idempotency/trace 的 `IngestionEnvelope`。
- **实际验证结果**：通过。最终复核时 `uv run pytest tests/unit/knowledge/test_ingestion_state.py -q` 为 `8 passed`；专项 ruff 和 strict mypy 通过。
- **计划偏差**：重试以同一 stage task 的递增 attempt 表示，进度不回退；队列仍不是事实源，真实 delivery/DLQ 策略保留后续阶段。

### P03-T06：定义检索、Citation、Trace 与索引协议

- **状态**：已完成
- **目标**：固定查询、候选、分数、结果、引用、Trace 和索引元数据。
- **为什么需要**：固定 RAG 和 KB Tool 必须共享。
- **输入**：P03-T02、P03-T04、ADR-009。
- **前置任务**：P03-T02、P03-T04。
- **操作步骤**：定义 RetrievalQuery/Filter AST 占位/Result；ScoreBreakdown；Citation；Trace event；IndexRecord/Version/embedding metadata。
- **涉及文件**：`domain/retrieval.py`、`ports/search.py`、文档。
- **预期输出**：查询/索引协议 v1。
- **RAGFlow 源码依据**：`DocStoreConnection` 表达式和 `Dealer.retrieval` 候选结构。
- **实现或复用方式**：参考后自研。
- **测试方法**：Schema、版本、tenant/citation 不变量。
- **验证命令**：`uv run pytest tests/unit/knowledge/test_retrieval_contract.py -q`
- **验收标准**：TopK/TopN、分数、版本和来源语义明确。
- **风险和回滚方法**：后端特有字段只能放 Adapter 扩展区。
- **实际执行结果**：实现 schema v1 的 `RetrievalQuery`、便携 MetadataFilter、ScoreBreakdown、Candidate、版本绑定 Citation、阶段化 RetrievalTrace、显式空结果原因、IndexVersion/EmbeddingMetadata/IndexRecord，以及 SearchIndex/Retriever/Reranker Ports；结果强制 query/trace/candidate/citation tenant 与 KB 范围一致。
- **实际验证结果**：通过。`uv run pytest tests/unit/knowledge/test_retrieval_contract.py -q` 为 `6 passed`；专项 ruff 和 strict mypy 通过。
- **计划偏差**：Filter 只开放五个可移植字段和四个操作符，不暴露 Elasticsearch/OpenSearch DSL；高级过滤在 Phase 06 按后端事实扩展。

### P03-T07：定义 Repository 与 UnitOfWork

- **状态**：已完成
- **目标**：建立 tenant-scoped 数据访问与事务边界。
- **为什么需要**：禁止应用层无 tenant `get_by_id`。
- **输入**：P03-T02、P03-T03、P03-T05。
- **前置任务**：P03-T02、P03-T03、P03-T05。
- **操作步骤**：定义 KB/Document/Version/Job Repository；所有方法要求 context/tenant；定义 UoW；创建内存契约 Adapter。
- **涉及文件**：`ports/repositories.py`、`ports/uow.py`、contract tests。
- **预期输出**：Repository 契约。
- **RAGFlow 源码依据**：Peewee Service 只作查询用例。
- **实现或复用方式**：自行开发。
- **测试方法**：跨租户、事务回滚、并发版本。
- **验证命令**：`uv run pytest tests/contract/knowledge/test_repositories.py -q`
- **验收标准**：不存在 tenant-free 通用方法。
- **风险和回滚方法**：接口过宽时按聚合拆分，不暴露 ORM。
- **实际执行结果**：定义 KnowledgeBase/Document/DocumentVersion/IngestionJob/IngestionTask Repository 和 KnowledgeUnitOfWork/Factory；所有读取和写入强制显式 `tenant_id`，写入 scope 不一致失败关闭，不存在 tenant-free `get_by_id`。建立 copy-on-enter 内存 UoW，覆盖 commit、无 commit/异常 rollback、重复 ID 冲突和 tenant-scoped version/job listing。
- **实际验证结果**：通过。`uv run pytest tests/contract/knowledge/test_repositories.py -q` 为 `6 passed`；专项 ruff 和 strict mypy 通过。
- **计划偏差**：Phase 03 仅提供内存契约 Adapter，不创建 SQLAlchemy 业务模型或数据库迁移；真实 Repository 属于 Phase 04 垂直切片。

### P03-T08：定义基础能力 Ports

- **状态**：已完成
- **目标**：定义 Storage、Parser、Chunker、Embedding、SearchIndex、Retriever、Reranker、TaskQueue、Trace Ports。
- **为什么需要**：Phase 04–09 必须通过稳定端口扩展。
- **输入**：P03-T04 至 P03-T07。
- **前置任务**：P03-T04 至 P03-T07。
- **操作步骤**：逐端口定义 typed request/result/error/lifecycle；区分写入和查询；设计契约测试 factory；不实现供应商 DSL。
- **涉及文件**：`knowledge/ports/*.py`、contract tests。
- **预期输出**：统一端口集合。
- **RAGFlow 源码依据**：`DocStoreConnection`、Parser/Chunk/Embedding/Queue 调用面。
- **实现或复用方式**：参考能力面后自研。
- **测试方法**：内存 Adapter 运行通用契约。
- **验证命令**：`uv run pytest tests/contract/knowledge -q`
- **验收标准**：字段完整、错误稳定、领域无具体客户端。
- **风险和回滚方法**：不为未知后端提前暴露特有能力。
- **实际执行结果**：定义 tenant-namespaced 流式 ObjectStorage、Parser、Chunker、Embedding、SearchIndex、Retriever、Reranker、IngestionQueue 和 KnowledgeTrace Ports 及严格 request/result DTO；建立真实可调用的内存/fixture Adapter，验证对象完整性、解析/Chunk 来源、Embedding 维度、IndexVersion 兼容、结构化检索、Queue envelope 和 Trace 关联。
- **实际验证结果**：通过。最终复核时 `uv run pytest tests/contract/knowledge -q` 为 `26 passed`；专项 ruff 和 strict mypy 通过。
- **计划偏差**：没有为未知后端设计 DSL、批处理限制或供应商错误码；这些由具体 Adapter 在不破坏 v1 契约的前提下扩展。

### P03-T09：定义 KnowledgeService 应用边界

- **状态**：已完成
- **目标**：定义知识库创建/读取、文档登记和统一查询入口的应用服务。
- **为什么需要**：API/Worker/Agent 不应直接组合 Repository。
- **输入**：P03-T02 至 P03-T08。
- **前置任务**：P03-T02 至 P03-T08。
- **操作步骤**：定义 command/query handler；在服务入口执行 PermissionChecker；定义事务和事件；建立 `KnowledgeQueryService` 空实现/Protocol。
- **涉及文件**：`application/knowledge_service.py`、测试。
- **预期输出**：应用服务边界。
- **RAGFlow 源码依据**：KB/Document Service 用例参考，不复制。
- **实现或复用方式**：自行开发。
- **测试方法**：调用顺序、权限先行、事务失败。
- **验证命令**：`uv run pytest tests/unit/knowledge/test_services.py -q`
- **验收标准**：固定 RAG/Tool 可共享查询服务；无伪检索。
- **风险和回滚方法**：服务过大时按用例拆 handler。
- **实际执行结果**：实现 permission-first `KnowledgeService` 的知识库创建/读取和文档+首版本原子登记，以及固定 RAG/未来 KnowledgeBaseTool 共用的 `KnowledgeQueryService`；服务只组合 PermissionChecker、tenant-scoped UoW、RetrieverPort、ID/Clock/Trace 端口，不导入 ORM、搜索客户端或 Agent。
- **实际验证结果**：通过。`uv run pytest tests/unit/knowledge/test_services.py -q` 为 `5 passed`；覆盖 context 生成 owner/tenant、跨租户隐藏、private/tenant write 拒绝、原子登记、权限先于 Retriever；专项 ruff 和 strict mypy 通过。
- **计划偏差**：服务只提供当前路线图明确的 create/get/register/retrieve 边界；上传、解析、索引和回答编排留 Phase 04。

### P03-T10：建立契约与权限负向测试

- **状态**：已完成
- **目标**：建立跨 Adapter 重用的契约和全链路 tenant 负向基线。
- **为什么需要**：后续具体实现不能改变领域语义。
- **输入**：P03-T02 至 P03-T09。
- **前置任务**：P03-T02 至 P03-T09。
- **操作步骤**：建立 factory-based contract suite；覆盖 tenant/owner/visibility；检查对象 key、queue、search、citation/trace 字段；导入边界。
- **涉及文件**：`tests/contract/knowledge/`、`tests/unit/import_boundaries/`。
- **预期输出**：可供 Phase 04 Adapter 复用的门禁。
- **RAGFlow 源码依据**：RF-P01 至 RF-P09 权限缺口。
- **实现或复用方式**：自行开发。
- **测试方法**：正/负向矩阵和属性测试。
- **验证命令**：`uv run pytest tests/contract/knowledge tests/unit/import_boundaries -q`
- **验收标准**：越权默认拒绝；所有端口 factory 可运行。
- **风险和回滚方法**：不删除失败用例适配实现。
- **实际执行结果**：建立跨 Adapter 复用的 Repository/UoW 与能力 Port 契约套件，补充 owner/visibility 权限矩阵、跨 tenant Storage/Queue/Search/Retriever 拒绝、对象键命名空间、Repository 方法签名和 Trace 身份负向测试；新增知识 domain/ports/application 静态导入边界。
- **实际验证结果**：通过。最终复核时 `uv run pytest tests/contract/knowledge tests/unit/import_boundaries -q` 为 `33 passed`；专项 ruff 和 strict mypy 通过。
- **计划偏差**：未引入属性测试依赖；当前用参数化矩阵和 factory/fixture Adapter 覆盖 Phase 03 明确的全部隔离不变量。

### P03-T11：固化契约文档并执行出口审查

- **状态**：已完成
- **目标**：把真实 DTO、状态机、端口和权限规则写入长期文档并验收。
- **为什么需要**：Phase 04 必须按事实实现垂直切片。
- **输入**：P03-T01 至 P03-T10。
- **前置任务**：P03-T01 至 P03-T10。
- **操作步骤**：生成契约文档；运行全部测试；检查矩阵/路线图；记录开放项；更新阶段状态。
- **涉及文件**：`docs/08-domain-model-and-contracts.md`、总体文档、本文件。
- **预期输出**：Phase 03 验收记录。
- **RAGFlow 源码依据**：核查所有上游结论仍固定到 frozen commit。
- **实现或复用方式**：审计与文档。
- **测试方法**：结构、链接、Schema、契约、权限。
- **验证命令**：`uv run pytest tests/unit/knowledge tests/contract/knowledge -q`; `uv run ruff check .`
- **验收标准**：CAP-03/16/41 第一版边界达标；无规划项误标。
- **风险和回滚方法**：未决定的后端保持端口，不阻塞领域完成。
- **实际执行结果**：将真实 DTO、状态机、Ports、权限矩阵、Agent context 映射和未实现边界固化到 `docs/08-domain-model-and-contracts.md`；新增 ADR-018、R-026/R-027，同步总纲、矩阵、目标架构、路线图、工程标准、阶段索引、README 和 CI 名称；完成链接、阶段/任务编号、规划/事实状态和 diff 审查。
- **实际验证结果**：通过。真实 PostgreSQL 17 上全量 `uv run pytest` 为 `131 passed`；`uv lock --check`、`uv sync --frozen --all-groups`、`uv pip check`、包导入、`uv run ruff check .`、strict mypy（145 files）、密钥卫生、Alembic upgrade/downgrade/upgrade、API/Worker bootstrap、Compose config 和非 root Docker build 均通过；Markdown 本地链接和 P03 任务连续性检查通过。
- **计划偏差**：阶段出口额外保留 Phase 01/02 的数据库、进程、Compose 和镜像门禁；未新增依赖、迁移或 RAGFlow 复制代码。Phase 04 因 O-002/O-006/O-007 未解决而不具备执行准入。

## 9. 测试与阶段验收

- Unit：实体、值对象、状态机、权限、稳定 ID。
- Contract：所有 Ports 的内存/未来 Adapter 共用套件。
- Security：tenant/owner/visibility、伪造 resource、Citation/Trace 字段。
- Architecture：领域/端口不导入基础设施。

**DoD**：P03-T01 至 P03-T11 全完成；契约文档与代码一致；第一版权限负向测试通过；所有端口有契约套件；总文档同步；Phase 04 输入/门禁明确。

## 10. 风险、更新和下一阶段

| 风险 | 处理 |
|---|---|
| 抄用 RAGFlow 表结构 | 以目标不变量和 RF-D 缺口审查 |
| tenant/owner 混淆 | 统一 PermissionChecker，默认拒绝 |
| 端口过度抽象 | 只覆盖路线图明确能力 |
| JSON 逃避建模 | 稳定 DTO 和 Schema version |
| 预规划漂移 | Phase 02 完成后按 R-023 重审 |

阶段结束更新总纲、矩阵、目标架构、路线图、工程标准、决策风险、阶段索引和本文件。Phase 04 还必须解决 O-002/O-006/O-007；首次抽取 RAGFlow 前解决 O-004。

## 11. 实际执行结果

- **实际时间/文件/迁移**：2026-07-30 连续完成 P03-T01 至 P03-T11；新增 `src/ragflow_agent/knowledge/{domain,application,ports}`、知识 unit/contract/fake 测试和 `docs/08-domain-model-and-contracts.md`。没有新增 Python 依赖、业务数据库表或 Alembic revision。
- **实际测试命令和结果**：最终复核时任务级 P03-T01 至 P03-T10 分别为 7/8/7/6/8/6/6/26/5/33 项门禁通过；真实 PostgreSQL 17 上全量 `131 passed`，ruff、strict mypy（145 files）、锁文件/依赖/导入/密钥、迁移往返、bootstrap、Compose 和 Docker build 全部通过。
- **计划偏差与新增决策**：新增 ADR-018、R-026、R-027；Phase 02 AgentState v1 保持不变，未来以 Adapter 映射 `user_id → actor_id`；使用 `ChunkRecord` 而非计划占位名 `ChunkDraft`，使用发布语义明确的 `IngestionQueuePort` 而非承诺尚未选择的完整 TaskQueue 实现。
- **阶段出口结论**：Phase 03 满足 DoD 并完成。Phase 04 计划文件存在，但 O-002、O-006、O-007 尚未解决，因此只可进入准入决策，不能执行 Phase 04。
