---
document_id: DECISIONS-AND-RISKS
status: active
last_updated_at: "2026-07-30"
adr_mode: registry
---

# 决策、待决策事项与风险登记

## 文档导航

[项目总纲](./00-project-master.md) · [RAGFlow 架构](./01-ragflow-architecture.md) · [能力矩阵](./02-ragflow-capability-matrix.md) · [目标架构](./03-target-architecture.md) · [代码复用策略](./04-code-reuse-strategy.md) · [开发路线图](./05-development-roadmap.md) · [工程标准](./06-engineering-standards.md) · [领域契约](./08-domain-model-and-contracts.md)

## 1. ADR 规则

本文件在 `docs/adr/` 尚未建立前承担 ADR 注册表。后续每个重大决策可以拆成独立 ADR，本文件保留索引和最新状态。

状态：

- `Accepted`：用户已确认，必须遵守。
- `Proposed`：已有建议，用户未确认。
- `Deferred`：需要解释或等到特定阶段再决定。
- `Resolved`：原待决策事项已经由 Accepted ADR 解决，保留编号用于追溯。
- `Superseded`：被新 ADR 替代。
- `Rejected`：明确不采用。

每条决策必须包含 Context、Decision/Question、Consequences 和 References。不得把 `Proposed` 或 `Deferred` 写成已接受架构。

## 2. 已接受决策

### ADR-001：独立 Agent + RAG 系统

- **Status**：Accepted and implemented in Phase 04
- **Date**：2026-07-27

**Context**

目标不是 RAG Demo、RAGFlow 部署、RAGFlow 二次开发或 RAGFlow API 包装。

**Decision**

项目独立保存领域数据、原始文件、索引、Agent 状态和 API。RAGFlow 只承担功能蓝本、源码候选库、设计参考和差距证据。

**Consequences**

- 必须自行建设文档生命周期、检索服务、API、评测和生产治理。
- 可选择性复用 RAGFlow Python 代码，但不能依赖运行中的 RAGFlow。
- 集成测试不能以 RAGFlow 服务可用为前提。

**References**

[项目总纲第 2、4 节](./00-project-master.md)；[目标架构](./03-target-architecture.md)

### ADR-002：Agent 使用 LangChain + LangGraph

- **Status**：Accepted
- **Date**：2026-07-27

**Context**

RAGFlow 的主要 Agent 是 Canvas DSL，高级 Agentic RAG 才使用 LangGraph，且冻结基线未配置 Checkpointer。

**Decision**

LangGraph 负责状态、节点、路由、循环、重试、Checkpoint、HITL 和多 Agent；LangChain 负责模型、Embedding、Retriever、Tool、Prompt 和结构化输出。

**Consequences**

- 不复用 RAGFlow Canvas Runtime。
- `CAP-29` 至 `CAP-32`主要自行开发。
- Agent Tool 只能调用应用服务。

**References**

[RAGFlow 架构第 7 节](./01-ragflow-architecture.md)；[能力矩阵 CAP-28 至 CAP-32](./02-ragflow-capability-matrix.md)

### ADR-003：RAGFlow 四种定位

- **Status**：Accepted
- **Date**：2026-07-27

**Decision**

RAGFlow 同时作为功能蓝本、源码候选库、设计参考和差距证据。每项能力使用“直接复用、改造复用、参考重写、自行开发、暂缓”之一。

**Consequences**

- 采用分类必须进入能力矩阵。
- 复制代码前必须完成源码级复用登记。
- 当前没有直接复用批准项。

**References**

[能力矩阵](./02-ragflow-capability-matrix.md)；[代码复用策略](./04-code-reuse-strategy.md)

### ADR-004：RAGFlow 只分析 Python

- **Status**：Accepted
- **Date**：2026-07-27

**Decision**

不分析、不复现、不实现 RAGFlow Go 路径。

**Consequences**

- 文档和源码地图不得把 Go 作为待办。
- 上游 Python 被 Go 替代时，只记录对冻结 Python 基线的影响。
- 不创建 Python/Go 兼容层。

**References**

[项目总纲第 2 节](./00-project-master.md)

### ADR-005：RAGFlow 双基线

- **Status**：Accepted
- **Date**：2026-07-27

**Context**

本地源码没有 `.git`，部分文件与远程当前 commit 不同。

**Decision**

- 冻结事实基线：`cd846cc9d4e32a19e684c59a1f302601027ef976`。
- 滚动跟踪基线：`main`。
- 本地快照只辅助搜索。

**Consequences**

- 长期源码链接固定到完整 commit。
- 升级冻结基线需要独立 ADR 和差异审计。
- 本地差异不能覆盖固定上游事实。
- 2026-07-30 滚动 `main` 已前进至 `0cb4039be9c0691f89c391c5cc28ab40682a8163`；冻结基线保持不变。该次最新提交是 Go ingestion 修正，不改变本项目 Python-only 冻结结论。

**References**

[项目总纲第 3 节](./00-project-master.md)；[RAGFlow 架构第 1 节](./01-ragflow-architecture.md)；[双基线核验](./research/ragflow-baseline.md)

### ADR-006：时序 RAG 范围外

- **Status**：Superseded by ADR-014
- **Date**：2026-07-27

**Decision**

不建设时序 RAG。普通结构化数据分析、日志检索和工单检索不得被命名为时序 RAG。

**Consequences**

- 能力矩阵不含时序 RAG。
- 轨道交通时序指标不进入当前路线图。
- 将来新增必须由新 ADR 替代本决策。

### ADR-007：初始技术基线

- **Status**：Accepted
- **Date**：2026-07-27

**Decision**

Python 3.13、uv、FastAPI、LangChain、LangGraph、PostgreSQL、SQLAlchemy 2、Alembic、Redis、MinIO/S3。

**Consequences**

- Phase 01 以此建立骨架。
- RAGFlow Quart/Peewee 代码只能参考。
- 具体包版本在 Phase 01 兼容性验证后锁定。

**References**

[目标架构第 3 节](./03-target-architecture.md)；[开发路线图 Phase 01](./05-development-roadmap.md)

### ADR-008：搜索后端必须经 SearchPort

- **Status**：Accepted
- **Date**：2026-07-27

**Context**

RAGFlow 支持多个搜索后端，不同后端的 KNN、融合和过滤语义不同。

**Decision**

业务层不直接依赖 Elasticsearch 或 OpenSearch client。写入和查询通过 SearchIndexPort/RetrieverPort，并执行契约测试。

**Consequences**

- 首个具体后端仍是 `O-002`。
- 不承诺所有后端原生能力完全一致。
- 后端特有优化只能留在 Adapter。

### ADR-009：固定 RAG 与 KnowledgeBaseTool 共享知识查询核心

- **Status**：Accepted
- **Date**：2026-07-27

**Decision**

两条路径共同调用 `KnowledgeQueryService`，共享 RetrievalQuery、RetrievalResult、Citation 和 RetrievalTrace。

**Consequences**

- Agent 不复制检索。
- 固定 RAG 不必经过 Agent 图。
- 同一查询配置下两条路径的检索候选必须可对比。

**References**

[目标架构第 8 节](./03-target-architecture.md)；[能力矩阵 CAP-27、CAP-28](./02-ragflow-capability-matrix.md)

### ADR-010：事实、规划和实现状态分离

- **Status**：Accepted
- **Date**：2026-07-27

**Decision**

文档使用事实、决策、规划、待确认、范围外和风险状态。没有代码、迁移和测试的能力不能标记为已实现。

**Consequences**

- 当前所有能力为未实现。
- 文档状态更新必须有验证证据。
- 生成计划不能改变实现进度。

### ADR-011：模块化单体 FastAPI 与独立 Ingestion Worker

- **Status**：Accepted
- **Date**：2026-07-27

**Context**

API 需要快速响应并避免 Parser、OCR、Embedding 和索引写入占用请求进程；第一版又不需要承担微服务的独立发布、重复模型和网络调用复杂度。RAGFlow Python 的 `docker/launch_backend_service.sh`、`TaskService.queue_tasks`、`RedisDB` 和 `task_executor.py` 证明同仓库 API/Worker 分进程与队列连接是可行边界，但其具体 Peewee/Redis/ACK 实现耦合过高。

**Decision**

第一版采用模块化单体：

- FastAPI API 与 Ingestion Worker 位于同一代码仓库和 Python 发行单元。
- 二者共享领域模型、应用服务和基础设施端口。
- 二者作为独立进程入口运行，通过版本化任务队列协议连接。
- API 持久化 IngestionJob 并投递任务；Worker 执行 ingestion。
- 第一版不拆微服务，也不通过内部 HTTP 调用 Worker。

**Consequences**

- API 与 Worker 可以独立启动、健康检查和扩缩容。
- TaskQueuePort 和 IngestionJob 是强制边界；具体任务库仍由 `O-006` 决定。
- Worker 崩溃、ACK、重试、死信、取消和幂等必须形成显式协议。
- 后续拆微服务必须新建 ADR，不得把“不同进程”自动解释成“不同服务”。

**References**

[`docker/launch_backend_service.sh`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/docker/launch_backend_service.sh)；[`api/db/services/task_service.py`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/api/db/services/task_service.py)；[`rag/utils/redis_conn.py`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/utils/redis_conn.py)；[`rag/svr/task_executor.py`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/svr/task_executor.py)

### ADR-012：第一版租户、所有者和可见性边界

- **Status**：Accepted
- **Date**：2026-07-27

**Context**

多租户和权限如果只在生产化阶段补做，会改变所有 Repository、搜索过滤、对象 key、任务、Tool、Citation 和 Trace。RAGFlow 提供 Tenant、UserTenant、`Knowledgebase.permission=me|team` 和 tenant index，但 `add_tenant_id_to_kwargs` 将当前用户 ID 作为 tenant 参数，tenant/user/owner 语义没有完全分离，不能直接复用。

**Decision**

- 第一版领域模型和接口保留多租户、ACL 与数据权限演进空间。
- 第一版至少实现强制 `tenant_id` 隔离、`owner_id`、`visibility`、`AuthorizationContext` 和 `PermissionChecker`。
- tenant 条件进入 Repository、任务、对象存储、搜索、缓存/锁、Tool、Citation 和 Trace。
- 跨租户默认拒绝，权限必须在检索前执行。
- 复杂 RBAC、部门权限和动态数据规则后续实现。

**Consequences**

- Phase 03 不再只保留权限占位，必须实现第一版隔离契约和负向测试；Phase 06/08/10 分别验证检索、Tool 和生产链路。
- 物理搜索索引布局不能替代 `tenant_id` 字段和校验。
- Worker 按 `tenant_id + job_id` 重新加载任务，不能只信任队列中的资源 ID。
- 后续复杂权限扩展 `PermissionChecker`，不得要求业务调用方绕开统一入口。

**References**

[`api/db/db_models.py`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/api/db/db_models.py)；[`api/db/services/knowledgebase_service.py`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/api/db/services/knowledgebase_service.py)；[`api/utils/api_utils.py`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/api/utils/api_utils.py)；[`rag/nlp/search.py`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/nlp/search.py)

### ADR-013：阶段计划生成与阶段执行门禁分离

- **Status**：Accepted
- **Date**：2026-07-30

**Context**

Phase 00 的 P00-T01 至 P00-T13 已全部执行并通过任务验收。此前把 O-001、下一阶段详细计划确认和用户出口确认同时作为 Phase 00 DoD 与 Phase 01 入口条件，造成研究阶段已完成但无法归档的循环依赖。用户在 2026-07-30 明确确认 Phase 00 已执行完成，并要求一次性生成 Phase 01 至 Phase 10 详细计划。

**Decision**

- Phase 00 按已完成标记。
- 阶段计划可以在前一阶段完成后预先生成，但生成计划不等于满足执行门禁。
- O-001 只阻止 Phase 01 任务执行，不再阻止 Phase 00 归档。
- Phase 01 标记“待确认/未执行”；Phase 02 至 Phase 10 标记“预规划草案/未执行”。
- 每个阶段开始前必须根据上一阶段实际结果重新审查其详细计划。

**Consequences**

- 本轮可以创建 Phase 01 至 Phase 10 计划，但不能执行任何 `P01-Txx` 或后续任务。
- 阶段状态索引必须区分计划状态和执行状态。
- 长期规划发生漂移时，以实际源码、上一阶段产物和新 ADR 修订计划。

### ADR-014：恢复时序 RAG 为 Phase 09 可选高级能力

- **Status**：Accepted
- **Date**：2026-07-30
- **Supersedes**：ADR-006

**Context**

用户最新范围明确要求 Phase 09 逐项规划时序 RAG。冻结 RAGFlow Python 基线提供 timeline 知识编译模板和结构图处理，但尚无证据证明它提供完整的数值时序摄取、窗口检索、时间对齐、聚合和文本证据融合链路。

**Decision**

- 时序 RAG 作为 `CAP-43 时序 RAG` 纳入 Phase 09，默认关闭并独立验收。
- RAGFlow timeline 编译只作为事件抽取和时间关系图的参考，不标记为完整时序 RAG。
- 目标实现采用自行开发；具体数据模型、时序存储和查询策略由 O-011 决定。
- 继续遵守 Python-only，不研究或复现 Go。

**Consequences**

- Phase 09 必须分别覆盖事件时间线与数值时序两类数据，且与普通文档索引保持兼容。
- 没有独立数据集、权限/版本语义和对照评测时不得启用。
- 能力矩阵、路线图、目标架构和 Phase 09 详细计划必须同步。

**References**

[`api/db/init_data/compilation_templates/timeline.yaml`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/api/db/init_data/compilation_templates/timeline.yaml)；[`runner.py::run_structure_compile_over_batches/_compile_batch/_flush`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/advanced_rag/knowlege_compile/runner.py)；[`structure.py::compile_structure_from_text/merge_compiled_structures/cleanup_timeline_isolated_entities`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/advanced_rag/knowlege_compile/structure.py)

### ADR-015：Phase 02/05 与 Phase 08/09 的能力边界校正

- **Status**：Accepted
- **Date**：2026-07-30

**Context**

Phase 00 后的旧总览曾把基础 HITL/预算放入 Phase 02，把自动关键词、自动问题、生成摘要和 TOC 放入 Phase 05。用户本轮明确指定：Phase 02 只建立 Agent 基础，HITL、记忆和预算属于 Phase 08；Phase 05 只建立 Parser/Chunk 数据面，生成式增强和父子 Chunk 属于 Phase 09。若不校正，会导致同一能力被两个阶段重复实现。

**Decision**

- Phase 02 负责 `AgentState`、Graph/Node/Edge/Router、Checkpoint、Tool/模型适配、Trace、错误处理和最小 Agent 闭环。
- Phase 08 负责 HITL、短期/长期记忆以及循环次数、Token、时间和费用预算。
- Phase 05 负责 PDF、DOCX、PPTX、XLSX、TXT、Markdown、HTML、图片、OCR、表格、Chunk Method、策略映射和元数据。
- Phase 09 负责自动关键词、自动问题、生成摘要、TOC、父子 Chunk及其独立评测。

**Consequences**

- CAP-31 只映射 Phase 08；Phase 02 的 Checkpoint 是 Phase 08 HITL 的前置而不是 HITL 实现。
- Phase 05 保留高级增强扩展点，但不得实现 Phase 09 的生成式能力。
- 详细计划、路线图、能力矩阵和阶段索引使用同一边界；执行前仍按 ADR-013 复审。

### ADR-016：项目身份、仓库与 Phase 01 质量平台

- **Status**：Accepted
- **Date**：2026-07-30

**Context**

Phase 01 的首个任务必须在创建 Python 包和质量配置前解决 O-001 与 O-012。用户已确认项目名称、Python 名称、Git 仓库、默认分支、远程仓库、首个 CI 平台和类型检查器；实际 Git 检查也确认 `main` 与 `origin/main` 指向同一个 Phase 00 基线 commit。

**Decision**

- 项目名和 Python 发行包名均为 `ragflow-agent`。
- Python import package 为 `ragflow_agent`，计划源码根目录为 `src/ragflow_agent`。
- API 服务标识为 `ragflow-agent-api`，Ingestion Worker 服务标识为 `ragflow-agent-ingestion-worker`；日志和 Trace 默认使用同名 service name。
- 配置环境变量前缀为 `RAGFLOW_AGENT_`。
- 项目 Git 根目录为 `D:/download/ragflow-agent`，默认分支为 `main`。
- `origin` 实际配置为 `https://github.com/haonanhu02-jpg/ragflow-agent.git`，与用户提供的不带 `.git` 后缀的仓库 URL 指向同一仓库。
- 首个 CI 平台使用 GitHub Actions；P01-T10 已创建 `.github/workflows/ci.yml`。
- Python 类型检查器使用 `mypy`；P01-T02 已写入项目开发依赖和 strict 质量配置。

**Consequences**

- O-001 与 O-012 已解决，Phase 01 计划已确认，P01-T01 可以完成。
- 所有目标模块路径必须使用 `src/ragflow_agent`，不得继续保留旧的包路径占位符。
- 本决策只冻结命名和工具选择，不表示 Python 包、服务入口、CI 或 mypy 配置已经实现。
- 后续若变更发行包、import package、服务标识、默认分支、CI 平台或类型检查器，必须新增 ADR 并执行全仓引用和迁移影响检查。

**References**

用户于 2026-07-30 对 O-001、O-012 和 Phase 01 计划的确认；项目仓库 `.git/config`、`refs/heads/main` 与 `refs/remotes/origin/main`；[`phase-01-project-skeleton.md`](./phases/phase-01-project-skeleton.md)

### ADR-017：Phase 02 Agent Runtime 与持久 Checkpoint 基线

- **Status**：Accepted
- **Date**：2026-07-30

**Context**

Phase 01 已提供 Python 3.13、PostgreSQL、类型化配置、Trace 和质量门禁。Phase 02 需要在不选择真实模型供应商、不创建知识库领域和不复用 RAGFlow Canvas 的前提下，完成可恢复的 LangGraph Agent 基础。冻结 RAGFlow `rag/advanced_rag/agentic_rag_graph.py::build_agentic_graph` 以无参数 `g.compile()` 编译，不能满足持久恢复要求。

**Decision**

- Agent Runtime 使用 LangGraph `StateGraph`；应用节点只依赖 Agent 领域、端口和应用服务。
- 持久 Checkpointer 使用官方 `langgraph-checkpoint-postgres::AsyncPostgresSaver`，由其 `setup()` 管理 Checkpoint 表；项目声明兼容范围为 `langgraph-checkpoint-postgres>=3.1,<4`、`psycopg[binary,pool]>=3.2,<4`，Phase 02 冻结锁定版本分别为 `3.1.0`、`psycopg 3.3.4` 和 `psycopg-pool 3.3.1`。本项目通过 `TenantScopedCheckpointStore` 组合 state version、`tenant_id` 和逻辑 `thread_id`，不把 Checkpoint 表建模为业务实体。
- `AgentState` 和 `AgentEvent` 从 v1 开始版本化；只持久化 JSON-safe 数据，禁止密钥、客户端和基础设施对象。
- 恢复必须同时验证 tenant、thread 和 run；跨租户 token 和状态失败关闭。
- Phase 02 使用确定性 `AgentModelPort`/Tool 测试替身作为门禁；真实 Chat Model 供应商继续由 O-007 在 Phase 04 前决定。
- Phase 02 只实现技术递归、重试和超时上限；HITL、记忆以及循环/Token/时间/费用业务预算仍属于 Phase 08。

**Consequences**

- 增加直接依赖 `langgraph-checkpoint-postgres` 和 `psycopg[pool]`；CI 的 PostgreSQL 服务同时验证官方 Checkpointer。
- 内存 Checkpointer 只允许 unit/E2E 快速测试，不得作为持久恢复验收证据。
- 官方 Checkpointer schema 的升级由依赖锁定、真实 PostgreSQL 回归和 R-025 管理；项目 Alembic 不接管其内部表。
- 依赖升级验证必须执行 `uv lock --check`、真实 PostgreSQL 上的 `tests/integration/agent/test_checkpoint.py` 与 `tests/integration/agent/test_runtime_recovery.py`，并验证 `setup()`、写入、恢复、list、delete、并发 thread、重复 resume 和跨租户拒绝；任一失败均阻止升级。
- Phase 03 可以复用 Agent 的最小授权快照传递，但仍必须建立统一 `AuthorizationContext` 和 `PermissionChecker`，不得把本决策误写成权限模型已完成。

**References**

[`phase-02-agent-foundation.md`](./phases/phase-02-agent-foundation.md)；[`agentic_rag_graph.py::build_agentic_graph`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/advanced_rag/agentic_rag_graph.py)

### ADR-018：Phase 03 知识领域、授权与统一查询契约 v1

- **Status**：Accepted
- **Date**：2026-07-30

**Context**

RAGFlow `api/db/db_models.py::{Knowledgebase,Document,Task}` 是 Peewee 产品表：只有 Knowledgebase 直接保存 `tenant_id`，Document/Task 通过父关系获得 tenant；`KnowledgebaseService._visibility_and_status_filter/accessible` 和 `add_tenant_id_to_kwargs` 混合 user、tenant、owner 与 team 语义。Phase 02 的 `AgentAuthorizationContext` 是 Checkpoint-safe 最小快照，不是知识资源权限模型。固定 RAG、Agent Tool、API、Worker 和未来 Adapter 需要同一套 provider-neutral 领域与查询协议。

**Decision**

- 知识领域位于 `src/ragflow_agent/knowledge/{domain,application,ports}`；领域和 Ports 禁止导入 FastAPI、SQLAlchemy、Redis、boto3、LangChain、LangGraph、Agent 或 RAGFlow。
- `AuthorizationContext` v1 固定为 `tenant_id + actor_id + request_id`；visibility v1 只含 `private` 和 `tenant`。跨 tenant 永远拒绝；private 只允许 owner；tenant visibility 只向同 tenant 非 owner 开放读取，写、删除和管理仍要求 owner。
- Phase 02 `AgentAuthorizationContext.user_id` 不做破坏性改名；未来知识库 Tool Adapter 显式映射为 `actor_id`，并重新执行 `PermissionChecker`。
- KnowledgeBase、Document、DocumentVersion、IngestionJob/Task、ParsedDocument/Block、ChunkRecord、Retrieval/Citation/Trace 和 IndexVersion/Record 使用严格、不可变、版本化 DTO；所有 tenant-owned 实体显式保存 `tenant_id`。
- Repository 的读取和写入都要求显式 tenant，写入实体必须与调用 tenant 一致；对象键固定使用 `tenants/{tenant_id}/...`；Queue envelope、Search record、Citation 和 Trace 均携带 tenant。
- Chunk ID v1 使用 `sha256-v1` 稳定算法；MetadataFilter 只暴露后端无关白名单字段/操作符，不暴露 Elasticsearch/OpenSearch DSL。
- `KnowledgeService` 统一处理创建/读取/文档登记，`KnowledgeQueryService` 是固定 RAG 与未来 KnowledgeBaseTool 的唯一权限先行检索入口。
- 本阶段只提供内存/fixture 契约 Adapter，不创建业务表、真实 Parser/Chunker/Embedding/Search/Queue 或回答流程。

**Consequences**

- Phase 04 必须实现这些 Ports，而不能另建一套 DTO、权限 if/else 或 tenant-free Repository。
- `AuthorizationContext`、状态机、Chunk ID 和 Retrieval schema 的破坏性变更必须升级 schema/ADR，并提供迁移或兼容读。
- 在 ADR-018 作出时，O-002/O-006/O-007 仍阻止 Phase 04 执行；这些事项随后由 ADR-019 关闭。若未来首次复制 RAGFlow 源码，仍必须重新审查 O-004 边界。
- 应用数据库、对象存储、搜索和外部 Trace 不是同一事务；可靠 outbox、幂等和补偿仍按 Phase 07 完成，见 R-027。

**References**

[`docs/08-domain-model-and-contracts.md`](./08-domain-model-and-contracts.md)；[`phase-03-knowledge-interface.md`](./phases/phase-03-knowledge-interface.md)；[`Knowledgebase/Document/Task`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/api/db/db_models.py)

### ADR-019：Phase 04 最小 RAG 基础设施与 Provider Profile

- **Status**：Accepted
- **Date**：2026-07-30

**Context**

Phase 03 已冻结知识领域、租户隔离和基础能力 Ports，但 O-002、O-006、O-007 仍阻止真实垂直切片。Phase 04 需要一个可验证而不过度扩张的 PostgreSQL → 对象存储 → Queue → Worker → Parser → Chunker → Embedding → Search → 固定回答组合。

**Decision**

- 首个且本阶段唯一搜索后端为 Elasticsearch 8.19 系列，使用官方异步 Python Client；实现 BM25、KNN 和最小 RRF 混合检索。Elasticsearch DSL 只能存在于 Adapter，领域与应用层仍只依赖 `SearchIndexPort`/`RetrieverPort`。Infinity、OpenSearch、Milvus 和其他引擎不在 Phase 04 实现范围。
- Redis 是队列基础设施，Python 任务库选择 ARQ 0.28 系列，并将其兼容的 Python Redis Client 锁在 `redis>=5.2,<6`；Redis 服务端版本仍由部署配置独立管理。选择原因是 asyncio 原生、依赖面小、支持 Redis、唯一 Job ID、重试、延迟、取消和悲观执行，适合当前同仓库独立 Worker。Celery 功能和运维面超过本阶段；RQ/Dramatiq 以同步 Worker 为主；Taskiq 更灵活但会为最小单队列链路引入额外 Broker/Result Backend 选择。
- ARQ 当前处于 maintenance-only 模式，因此只使用 `create_pool`、`enqueue_job`、唯一 `_job_id`、Worker retry/abort 等稳定最小接口；ARQ 类型不得进入领域消息、应用服务或数据库。若其 Python/Redis 兼容性、修复响应或安全维护不能满足要求，通过 `IngestionQueuePort` 更换 Adapter。
- 默认 Chat Provider 为 DeepSeek OpenAI-compatible API，默认模型 `deepseek-chat`；默认 Embedding 为 `BAAI/bge-m3`，维度 1024。业务服务只依赖项目 Provider/Embedding Ports；LangChain OpenAI-compatible Adapter 位于基础设施层。
- CI 和默认测试只使用 Fake/Stub Provider，不需要 API Key、外部模型服务或 GPU。真实 Provider 为显式 opt-in，端点、模型和凭据只通过环境变量提供。
- Phase 04 不要求 Reranker；保留 `RerankerPort`，BGE Reranker 在后续阶段作为独立 Adapter 接入。
- 元数据和业务事实继续存 PostgreSQL；对象存储采用 S3-compatible Adapter，本地默认 MinIO；搜索使用 Elasticsearch；Queue 使用 Redis + ARQ。所有外部端点通过配置替换。
- Phase 04 不复制、抽取或改写任何 RAGFlow 源码，只参考冻结 commit 的公开架构、职责和行为目标并独立实现。若后续需要复制或修改 RAGFlow 源码，必须暂停、重新审查 Apache-2.0 notice、文件 provenance、内部依赖和分发义务，并形成新 ADR。
- Phase 04 的 CI 仅在工作流显式声明临时服务容器时运行 PostgreSQL、Redis、MinIO 和 Elasticsearch 集成测试；否则测试必须明确 skip，不能伪造成功。

**Consequences**

- P04-T01 的 O-002、O-006、O-007 和 Phase 04 范围内的 O-004 门禁解除。
- Phase 04 只验证一个最小 Profile，不承诺多引擎一致性、完整分布式调度、生产身份系统、复杂 Parser、Reranker 或 Provider 高可用。
- ARQ maintenance-only 和 Elasticsearch 版本升级分别由 R-028、R-029 监控。

**Verification**

- 锁定依赖并运行 `uv lock --check`、`uv sync --frozen --all-groups` 和 `uv pip check`。
- 使用真实临时 Redis 验证唯一消息 ID、入队、消费失败不伪成功和重试边界。
- 使用真实 Elasticsearch 验证 mapping、bulk upsert、tenant/KB 强制过滤、BM25、KNN 和混合检索。
- 使用 Fake BGE/Chat Provider 完成上传到带 Citation 回答的 E2E；真实 DeepSeek/BGE 只作本地 opt-in smoke。
- **实际结果**：Python 3.13 下 ARQ 0.28 + redis-py 5.3.1、Elasticsearch Client/Server 8.19.3、真实 PostgreSQL/MinIO/Redis/Elasticsearch 全量测试 153 passed、0 skipped；外部 DeepSeek/BGE 未执行，不得声称已验证。

**References**

[`phase-04-minimum-rag.md`](./phases/phase-04-minimum-rag.md)；[ARQ documentation](https://arq-docs.helpmanual.io/)；[Elasticsearch async client](https://www.elastic.co/guide/en/elasticsearch/client/python-api/current/async.html)

### ADR-020：Phase 05 独立 Parser、Tesseract OCR 与样本资源 Profile

- **Status**：Accepted
- **Date**：2026-07-31

**Context**

Phase 04 已提供版本化 `ParsedDocument`、`ChunkRecord` 和真实 ingestion 闭环。RAGFlow DeepDOC
Parser/Vision 与 `common.settings`、RAG tokenizer、ONNX/OpenCV、模型权重和业务服务深度耦合；
用户明确要求 Phase 05 不复制、抽取或改写 RAGFlow 源码。

**Decision**

- 八类 Parser、Parser/Chunk Registry 和九种 Chunk Method 全部独立实现；RAGFlow 冻结源码只作职责和行为证据，Phase 05 的直接复用/改造复用数量均为零。
- TXT/Markdown/HTML 使用 charset-normalizer、markdown-it-py、BeautifulSoup；DOCX/PPTX/XLSX 使用 python-docx、python-pptx、openpyxl + defusedxml；PDF 使用 pdfplumber 提取文本/坐标/表格，使用 pypdfium2 渲染扫描页。
- OCR 通过项目内部 `OcrEnginePort` 隔离，首个 Adapter 调用外部 Tesseract 5.x。项目不捆绑 OCR 引擎、模型或语言权重；CI 安装并真实验证 `eng` 与 `chi_sim`。
- Parser 同时校验 MIME 与扩展名，输出 schema v2、结构化 warning、来源顺序、bbox、表格/图片引用和推荐 Chunk Method。所有策略继续使用稳定、版本化 ID。
- 测试样本必须人工创建、无敏感信息、小体积且有 provenance；Office/PDF/图片二进制样本在测试运行时确定性生成。
- 资源门禁固定 OOXML entries/解压大小/压缩比、PDF 页数、图片像素、XLSX sheet/row/cell、Parser 超时；解析器不得把临时路径或第三方对象泄漏进领域层。

**Consequences**

- O-004 在 Phase 05 继续按“零 RAGFlow 源码复制”关闭；若未来首次复制，必须新增 ADR 并重新许可证审查。
- O-007 的 Phase 05 OCR 基线解决为 Tesseract；真实 DeepSeek/BGE、Reranker 和模型型 Vision 仍不属于本阶段验收。
- Tesseract 不可用时图片或扫描 PDF 必须明确失败；本地可 skip 真实 OCR，但 CI 不允许 skip。
- 新增 R-030 监控格式库、PDFium/Tesseract 运行时、语言数据、资源上限和 Parser 输出漂移。

**Verification**

- `uv lock --check`、`uv sync --frozen --all-groups`、`uv pip check` 和全部 Parser import probe。
- 每种格式/策略的 golden/contract/resource test，以及 CI 的英文/中文真实 OCR。
- 导入边界与 provenance 扫描必须证明 `src/` 不导入 RAGFlow、DeepDOC、Peewee 或 `common.settings`。

**References**

[`phase-05-parser-license-and-resource-baseline.md`](./research/phase-05-parser-license-and-resource-baseline.md)；
[`phase-05-parser-and-chunk.md`](./phases/phase-05-parser-and-chunk.md)

### ADR-021：Phase 06 安全降级、RRF/Reranker 与 Retrieval Trace

- **Status**：Accepted
- **Date**：2026-07-31

**Context**

Phase 05 已提供 schema v2、Citation bbox 和多格式 Chunk，Phase 04 已提供 Elasticsearch
BM25/KNN/RRF 基线。Phase 06 必须在不创建第二套检索主链路、不放宽任何授权范围的前提下，
完成查询处理、双路召回、融合、重排、降级和可审计 Trace。

**Decision**

- 空结果采用有限、可配置重试：先扩大候选集并在安全下限内降低软阈值，再只移除系统推断的
  可选软过滤，必要时分别尝试全文或向量单通道；tenant、用户/角色 ACL、知识库/索引范围、
  文档启用/删除/可见状态和用户明确过滤永不放宽。所有尝试失败后返回结构化 `no_evidence`；
  搜索、Embedding 或 Reranker 系统错误不得伪装成空结果。
- 默认管线为全文与向量两路召回、按 `chunk_id` 去重、RRF（`k=60`）融合、融合 TopN
  调用内部 `RerankerPort`、最终阈值和 `top_k` 截断。保留两路原始排名/分数、融合分数和
  Reranker 分数；Reranker 超时、不可用或异常时显式回退 RRF，不让整个请求失败。
- Reranker 默认目标是经内部 Provider Adapter 调用 BGE Reranker；业务代码不绑定供应商 SDK，
  CI 使用 Fake/Stub。没有真实端点/GPU 结果时不得声称真实 BGE Reranker 已验证。
- 每次检索生成独立 `trace_id` 并关联 `request_id`。完整 Trace 默认保留 30 天，聚合指标可保留
  180 天；持久化内容不含完整原查询、Chunk 正文、Prompt、密钥或 Authorization，只保存摘要、
  哈希、ID、排名、分数、耗时、降级和错误。Trace 按 tenant 隔离，详细读取要求
  `retrieval_debug` 或 `operations` 角色；写入失败不阻断检索但必须形成可观察计数。
- Phase 06 继续零复制、零改写 RAGFlow 源码；公开源码只用于调用顺序和行为目标证据。

**Consequences**

- O-008 关闭；Phase 06 计划获准执行。复杂 RBAC、部门规则和生命周期补偿仍分别属于后续阶段。
- Trace 存储和过期清理需要 Alembic 表、租户/过期索引、权限服务与真实 PostgreSQL 测试。
- 查询改写、跨语言与关键词扩展按 Phase 06 正式计划实现为可关闭 Provider 能力；失败回退规范查询，
  不能改变硬过滤。

**Verification**

- 确定性验证 RRF、去重、阈值、Rerank/超时回退、真空与系统错误区分、有限重试终止。
- 负向验证所有降级步骤的 tenant、ACL、知识库、索引、状态和用户过滤不变。
- 真实 Elasticsearch 验证双路检索/过滤/排名，真实 PostgreSQL 验证 Trace 租户隔离、TTL 和清理；
  Fake Reranker/查询 Provider 不冒充真实模型。

**References**

[`phase-06-online-retrieval.md`](./phases/phase-06-online-retrieval.md)

## 3. 开放与已解决的待决策事项

### O-001：项目正式名称和 Python 包名

- **Status**：Resolved
- **Resolution**：ADR-016
- **Decision deadline**：Phase 01 开始前
- **Question**：项目、发行包和 import package 使用什么名称？
- **Decision**：项目名和发行包名为 `ragflow-agent`；import package 为 `ragflow_agent`；源码根目录为 `src/ragflow_agent`。
- **Current handling**：命名已冻结且 Python 包已由 Phase 01 创建；变更仍须新增 ADR。
- **Impact**：目录、配置前缀、日志 service name、镜像名。

### O-002：首个搜索引擎

- **Status**：Resolved
- **Resolution**：ADR-019
- **Decision deadline**：Phase 04 开始前
- **Question**：首个 SearchPort Adapter 使用 Elasticsearch 还是 OpenSearch？
- **Options**：
  - Elasticsearch：与 RAGFlow 默认路径更接近。
  - OpenSearch：独立开源生态和相似 API。
- **Required evidence**：BM25、KNN、过滤、批量写入、索引别名、部署资源和许可证比较。
- **Decision**：Phase 04 只实现 Elasticsearch 8.19 Adapter；保留 SearchPort，不并行实现其他引擎。
- **Current handling**：Elasticsearch DSL 只允许存在于基础设施 Adapter。

### O-003：API 与 Ingestion 物理拓扑

- **Status**：Resolved
- **Resolution**：ADR-011
- **Decision**：模块化单体；同仓库、FastAPI 与独立 Ingestion Worker 分进程、队列连接、第一版不拆微服务。

### O-004：RAGFlow 复用代码物理隔离

- **Status**：Resolved through Phase 06
- **Resolution**：ADR-019、ADR-020
- **Decision deadline**：首次抽取代码前
- **Question**：内部 Adapter 包、独立 Python 包或独立 Worker？
- **Decision**：Phase 04、Phase 05、Phase 06 均不复制、抽取或改写 RAGFlow 源码；不存在这三个阶段的复用代码物理隔离问题。
- **Current handling**：只保留固定 commit 源码依据和独立实现 provenance；后续首次复制前必须重新打开许可证审查并形成 ADR。
- **Required evidence**：依赖大小、模型资源、进程稳定性、许可证和部署影响。

### O-005：多租户和权限模型

- **Status**：Resolved
- **Resolution**：ADR-012、ADR-018
- **Decision**：第一版强制 tenant 隔离并实现 owner/visibility、AuthorizationContext 和 PermissionChecker；复杂 RBAC、部门权限与动态数据规则后置。
- **Resolved design detail**：visibility v1 为 `private|tenant`；同 tenant 非 owner 仅可读取 tenant-visible 资源，其他操作要求 owner；具体数据库约束在 Phase 04 Adapter 中按相同契约落地。

### O-006：后台任务与可靠消息实现

- **Status**：Resolved
- **Resolution**：ADR-019
- **Decision deadline**：Phase 04 开始前
- **Question**：使用哪种任务库和消息语义？
- **Required capability**：ACK、重试、取消、延迟、积压、崩溃恢复、幂等、可观察。
- **Decision**：Redis + ARQ 0.28；只实现 ingestion 所需最小可靠链路，领域和应用层只依赖 `IngestionQueuePort`。
- **Current handling**：唯一 Job ID、重试、失败状态和 Worker ACK 语义通过 Adapter/集成测试固化。

### O-007：首批模型

- **Status**：Resolved through Phase 06 for Chat/Embedding/OCR/Reranker
- **Resolution**：ADR-019、ADR-020、ADR-021
- **Decision deadline**：Phase 04 开始前
- **Question**：LLM、Embedding、Reranker、OCR、Vision、ASR 的首批 Provider/模型？
- **Decision**：Chat 默认 DeepSeek OpenAI-compatible `deepseek-chat`；Embedding 默认 `BAAI/bge-m3`、1024 维；OCR 默认通过内部 Port 调用外部 Tesseract；Reranker 默认目标为通过内部 `RerankerPort` 接入 BGE Reranker。
- **Current handling**：业务只依赖 Provider/Embedding/OCR/Reranker Ports；CI 使用 Fake Chat/Embedding/Reranker，并使用真实 Tesseract `eng`/`chi_sim`；真实 DeepSeek/BGE 端点和凭据仅来自环境变量。
- **Required evidence**：语言、维度、上下文、成本、延迟、隐私、部署、许可证和回退。

### O-008：空结果降级默认策略

- **Status**：Resolved
- **Resolution**：ADR-021
- **Decision deadline**：Phase 06
- **Question**：降低阈值、去除改写、放宽 metadata、跨知识库还是直接空结果？
- **Decision**：有限可配置重试，只能扩大候选、在下限内降低软阈值、移除系统推断软过滤或改单通道；任何硬过滤不放宽，最终允许结构化 `no_evidence`。
- **Current handling**：Phase 06 按 ADR-021 实施并记录每一步 Trace；后端/模型错误与真空分离。
- **Security constraint**：tenant、ACL、知识库/索引、文档状态/可见性和用户过滤在所有步骤保持。

### O-009：GraphRAG 和 RAPTOR 默认范围

- **Status**：Deferred
- **Decision deadline**：Phase 09
- **Question**：哪些知识库启用、构建触发、资源预算和查询路由？
- **Current handling**：能力保留但不默认启用。
- **Required evidence**：Phase 10 评测相对 Phase 06 的增益。

### O-010：前端或管理控制台

- **Status**：Deferred
- **Decision deadline**：Phase 10 结束后另行修订路线图，或更早出现明确展示需求时
- **Question**：是否建设 UI，覆盖知识库、任务、检索 Trace、Agent 和评测中的哪些页面？
- **Current handling**：只规划 FastAPI，不假定 UI。

### O-011：时序 RAG 数据模型、存储与查询边界

- **Status**：Deferred
- **Decision deadline**：Phase 09 开始前
- **Question**：首版只覆盖事件时间线，还是同时覆盖连续数值指标；是否引入专用时序存储；窗口、聚合、缺失值、时间对齐和文本证据融合采用什么协议？
- **Current handling**：Phase 09 只定义端口、数据集和对照实验，不预选 TimescaleDB、InfluxDB 或其他后端。
- **Required evidence**：轨道交通脱敏样本、查询类型、数据规模、保留周期、聚合精度、tenant 隔离、备份恢复、部署成本和相对普通检索的增益。

### O-012：Phase 01 仓库与质量工具选择

- **Status**：Resolved
- **Resolution**：ADR-016
- **Decision deadline**：P01-T01
- **Question**：是否在目标目录初始化 Git；首个 CI 平台和 Python 类型检查器采用什么？
- **Decision**：使用已初始化的 Git 仓库，默认分支 `main`，远程 `origin` 实际配置为 `https://github.com/haonanhu02-jpg/ragflow-agent.git`；首个 CI 平台为 GitHub Actions；类型检查器为 `mypy`。
- **Current handling**：仓库事实、GitHub Actions CI 与 `mypy` 配置均已由 Phase 01 实施并通过本地门禁；远程运行状态按提交记录。
- **Impact**：分支/提交事实源、质量命令、CI 文件路径、Phase 01 DoD。

## 4. 风险登记

等级定义：

- 可能性：低、中、高。
- 影响：低、中、高、严重。
- 状态：Open、Monitoring、Mitigated、Accepted。

| ID | 风险 | 可能性 | 影响 | 触发信号 | 控制措施 | 责任阶段 | 状态 |
|---|---|---|---|---|---|---|---|
| R-001 | RAGFlow `main` 变化导致结论漂移 | 高 | 中 | 路径、函数、字段或行为变化 | ADR-005；固定 commit；滚动差异报告 | Phase 00 持续 | Monitoring |
| R-002 | 本地 RAGFlow 无 Git 元数据导致错误归因 | 高 | 高 | 本地代码与固定链接不同 | 本地只辅助；结论固定到完整 commit | Phase 00 | Mitigated |
| R-003 | Parser/OCR 依赖模型、原生库、GPU 和资源文件 | 高 | 高 | 安装失败、内存过高、平台不兼容 | 可选依赖、隔离实验、容器 Profile、资源限制 | Phase 05 | Open |
| R-004 | 抽取代码残留 settings/Peewee/LLMBundle/Redis 全局依赖 | 高 | 高 | Adapter 导入上游 API/Service | import 边界、源码登记、契约测试 | Phase 04/05/06/09 | Open |
| R-005 | PostgreSQL、对象存储、搜索索引不一致 | 中 | 严重 | 孤儿对象、孤儿 Chunk、错误 current version | DocumentVersion、候选索引、补偿、幂等 | Phase 07 | Open |
| R-006 | 搜索后端分数和过滤语义不一致 | 高 | 高 | 相同数据不同排序/过滤结果 | O-002、SearchPort 契约、RRF、原始排名/分数 Trace、真实 ES 固定评测 | Phase 04/06/10 | Monitoring |
| R-007 | Embedding 变化使旧索引不可用 | 中 | 高 | 模型/维度更新 | 记录模型和维度；新 index_version；重建切换 | Phase 07 | Open |
| R-008 | Citation 指向错误版本、页码或删除内容 | 中 | 严重 | quote 不存在、引用旧版或越权文档 | document_version_id、验证器、删除可见性 | Phase 04/06/07 | Open |
| R-009 | Agent 循环失控、成本过高或不可恢复 | 高 | 高 | 循环增长、重复 Tool、Checkpoint 失败 | 上限、预算、超时、Checkpoint、取消、Trace | Phase 02/08 | Open |
| R-010 | 权限过滤遗漏导致数据泄露 | 中 | 严重 | 越权检索或 Citation | ADR-012/021；Repository/Search 强制 tenant/ACL/状态/范围；所有降级负向测试 | Phase 03/06/08/10 | Monitoring |
| R-011 | GraphRAG/RAPTOR 增加复杂度但无质量收益 | 高 | 高 | 成本上升、指标不升 | 默认关闭；Phase 10 对照评测 | Phase 09/10 | Open |
| R-012 | RAGFlow/第三方许可证或模型再分发不清楚 | 中 | 严重 | 缺许可证、权重限制、样本来源不明 | provenance、依赖清单、人工法律复核 | 所有复用阶段 | Open |
| R-013 | 文档规划过度，Minimum RAG 延迟 | 中 | 中 | Phase 00 持续扩大而无出口 | Phase 00 已归档；Phase 01 后按任务 DoD 推进 | Phase 00 | Mitigated |
| R-014 | 抽象过度导致 Phase 04 没有垂直切片 | 中 | 高 | 只有 Protocol/DTO，没有端到端请求 | Phase 04 已完成 Fake 与真实基础设施上传到回答 E2E | Phase 03/04 | Closed |
| R-015 | 测试数据不能代表复杂企业文档 | 高 | 高 | 黄金样本过于简单，线上质量差 | 多格式复杂样本、轨道交通脱敏集、错误样本 | Phase 05/10 | Open |
| R-016 | LLM/Embedding/Reranker 供应商波动 | 高 | 中 | 限流、价格、模型下线、响应变化 | 模型注册、契约测试、回退、版本锁定 | Phase 04/10 | Open |
| R-017 | Trace 记录敏感原文 | 中 | 严重 | 日志或 Trace 泄露文档内容 | 数据最小化、查询摘要、tenant/角色读取、30 天 TTL、真实 PG 清理测试 | Phase 01/06/10 | Monitoring |
| R-018 | 任务取消与重试竞态产生重复索引 | 中 | 高 | 已取消任务继续写入 | 状态比较、幂等 key、候选索引和最终检查 | Phase 07 | Open |
| R-019 | 模块化单体退化为 API/Worker 两套重复实现 | 中 | 高 | 重复 DTO、内部 HTTP、行为漂移 | ADR-011；共享领域/应用层；导入边界与契约测试 | Phase 01 持续 | Open |
| R-020 | 队列消息 tenant 与数据库资源 tenant 不一致 | 中 | 严重 | 跨租户任务执行或索引污染 | tenant_id + job_id 加载、双重校验、安全审计、拒绝执行 | Phase 03/04/07 | Open |
| R-021 | 把搜索 Chunk 误建模为 RAGFlow 关系表或照搬缺 tenant 的 Task/Document | 中 | 高 | 领域模型与索引字段耦合、Worker 漏做租户过滤 | 采用 `ChunkRecord`；任务信封显式 tenant；数据库二次校验；参见源码证据 RF-D03/D05/D07 | Phase 03/04/07 | Open |
| R-022 | 文档关系行先删除而对象、索引或派生数据清理失败 | 中 | 高 | `remove_document` 后续 best-effort cleanup 留下孤儿数据 | 删除先撤销可见性；补偿日志；幂等清理；reconciliation；保留审计墓碑 | Phase 07/10 | Open |
| R-023 | 预生成的后续阶段计划与上一阶段实际产物漂移 | 高 | 高 | 计划引用的接口、文件或决策已变化 | ADR-013；每阶段入口重新审查；未审查不得执行 | Phase 01–10 | Open |
| R-024 | 时序 RAG 范围和后端未定义导致 Phase 09 失控 | 高 | 高 | 同时引入新存储、算法和数据模型且无基线 | ADR-014；O-011；默认关闭；独立数据集和实验门禁 | Phase 09/10 | Open |
| R-025 | 官方 PostgreSQL Checkpointer 升级导致内部 schema 或恢复语义漂移 | 中 | 高 | 依赖升级后 setup、恢复、list/delete 或并发测试失败 | 锁定依赖；不手改上游表；真实 PostgreSQL 迁移/恢复回归；升级前审查 release notes | Phase 02 持续/Phase 10 | Monitoring |
| R-026 | Agent 最小授权快照与知识 AuthorizationContext 映射漂移 | 中 | 高 | Tool Adapter 错把 `user_id` 当 tenant、恢复后跳过权限重验或字段改名破坏 Checkpoint | AgentState v1 不破坏；显式 `user_id → actor_id` Adapter；tenant/thread/run 与 PermissionChecker 双重验证；跨租户 Tool 契约测试 | Phase 08 | Open |
| R-027 | 数据库提交与对象存储、搜索、Queue、Trace 非原子导致部分成功 | 高 | 高 | 写入已提交但事件/索引/Trace 失败，重试产生重复或状态漂移 | Phase 03 只定义端口；Phase 04 命令使用幂等键；Phase 07 落地 outbox、候选索引、补偿、残留扫描和故障注入 | Phase 04/07 | Open |
| R-028 | ARQ maintenance-only 导致未来 Python/Redis 兼容或安全修复不足 | 中 | 高 | 新 Python/Redis 无法运行、关键缺陷长期无修复 | 锁定 0.28；只用最小接口；QueuePort 隔离；真实 Redis 回归；必要时替换 Adapter | Phase 04/10 | Monitoring |
| R-029 | Elasticsearch Client/Server 版本或 KNN 语义漂移 | 中 | 高 | mapping、查询参数、分数或过滤在升级后变化 | 锁定 8.19 系列；真实 BM25/KNN/混合/tenant 契约测试；DSL 限于 Adapter | Phase 04/06/10 | Monitoring |
| R-030 | Parser 格式库、PDFium、Tesseract 或语言数据跨平台漂移 | 中 | 高 | 同一文档输出结构变化、运行时缺失、语言包不可用或坐标漂移 | 锁定 Python 依赖；外部运行时能力检测；生成式黄金；Linux CI 真实 OCR；资源/错误契约；升级前基线比较 | Phase 05 持续/Phase 10 | Monitoring |
| R-031 | 查询改写/翻译/关键词扩展引入噪声或 Prompt 注入 | 中 | 高 | 召回下降、恶意历史改变查询范围、变体爆炸 | 结构化 Provider、变体上限/去重、可关闭开关、失败回 canonical、硬过滤不随变体变化 | Phase 06/08/10 | Monitoring |
| R-032 | Reranker 模型、端点或分数语义漂移 | 高 | 高 | 排名突变、超时、身份集合变化、GPU 不可用 | 内部 Port、超时、候选身份校验、RRF 回退、Fake 契约；真实模型回归后置 | Phase 06/10 | Monitoring |

## 5. 风险处理规则

1. 严重影响的 Open 风险必须在相关阶段入口检查。
2. 风险成为现实问题时，创建 issue/任务并保留风险 ID。
3. 接受风险必须说明接受期限和责任人。
4. 风险关闭需要证据，不以“代码已写”作为充分条件。
5. 新的架构选择如果改变多个风险，必须形成 ADR。

## 6. 当前决策摘要

- Accepted：ADR-001 至 ADR-005、ADR-007 至 ADR-021。
- Resolved：O-001 → ADR-016；O-002/O-006 → ADR-019；O-007 → ADR-019/020/021；O-003 → ADR-011；O-004（Phase 04–06 不抽取）→ ADR-019/020/021；O-005 → ADR-012；O-008 → ADR-021；O-012 → ADR-016。
- Deferred：O-009、O-010、O-011。
- Rejected：RAGFlow 运行时依赖、Go 复现、RAGFlow Canvas 作为 Agent 核心。
- Superseded：ADR-006 → ADR-014。
- 当前没有通过待决策事项擅自形成的实现。

## 7. Phase 00 出口审查记录

### 2026-07-29 / P00-T13

- **结论**：不允许进入 Phase 01；Phase 00 保持进行中/出口阻塞。
- **已满足**：P00-T01 至 P00-T13 均有实际产出、验证和验收记录；42 项能力、46 行复用登记、冻结源码证据和一致性检查通过；没有业务代码或 Phase 01 详细计划。
- **未满足**：O-001 仍为 Deferred；七份辅助文档尚无最终整体确认；本次出口结论尚待用户确认；Phase 01 详细计划按本轮限制未创建。
- **处理**：不得为关闭阶段擅自选择项目名/包名，不得生成或执行 Phase 01；用户给出 O-001 和文档/出口确认后重新执行出口门禁。

### 2026-07-30 / 用户出口确认

- **结论**：用户明确确认 Phase 00 已执行完成；Phase 00 标记完成。
- **依据**：P00-T01 至 P00-T13 已有产出和验收；用户本次确认同时完成辅助文档整体结果与出口确认。
- **门禁调整**：按 ADR-013，O-001 保留为 Phase 01 执行门禁，不再阻止 Phase 00 归档。
- **Phase 01 状态**：允许生成详细计划，但在 O-001 和计划确认完成前仍不得执行。

## 8. Phase 01 出口审查记录

### 2026-07-30 / P01-T10

- **结论**：P01-T01 至 P01-T10 已完成，Phase 01 通过本地阶段验收；不自动进入 Phase 02。
- **实现边界**：已实现包、配置、日志/Trace、基础设施端口、SQLAlchemy/Alembic 空基线、FastAPI/Worker 空壳、Docker 开发拓扑和 GitHub Actions 门禁；未实现 Agent、知识库、ingestion、Parser、索引或检索。
- **待决策保持不变**：O-002 搜索后端、O-006 可靠消息、O-007 首批模型均未被 Phase 01 占位实现替代。
- **计划偏差**：Windows psycopg 使用 Selector loop；Docker Worker 以显式 development-only 非消费模式验证进程健康，默认入口仍 fail-fast；两者均不改变 ADR-011 架构。
- **下一门禁**：根据真实骨架复审并由用户确认 Phase 02 计划，之后才可从 P02-T01 开始。

## 9. Phase 02 出口审查记录

### 2026-07-30 / P02-T10

- **结论**：P02-T01 至 P02-T10 已完成；Phase 02 通过 Unit、Contract、Integration、E2E、真实 PostgreSQL 恢复、ruff、strict mypy、密钥卫生和完整 pytest 阶段门禁，不自动进入 Phase 03。
- **实现边界**：已实现 AgentState/Event v1、最小 LangGraph、模型/Tool 端口与 LangChain Adapter、Tool allowlist、错误/重试/超时/取消、官方 PostgreSQL Checkpointer 的租户作用域、run/resume 和 Agent Trace；未实现知识库、RAG、KnowledgeBaseTool、真实模型、HITL、记忆、多 Agent 或业务预算。
- **决策**：ADR-017 冻结官方异步 PostgreSQL Checkpointer、租户/版本作用域、确定性测试模型和 Checkpoint 表所有权；O-002、O-006、O-007 保持 Deferred。
- **计划偏差**：未创建 `budgets.py`，技术限额由 `RuntimeLimits` 承担；官方 Checkpointer 通过自身 `setup()` 管理内部表，不创建项目 Alembic 业务迁移；持久恢复由真实 PostgreSQL 验证，内存 Saver 只用于快速测试。
- **新增风险**：R-025 监控官方 Checkpointer schema 和恢复语义随依赖升级漂移。
- **下一门禁**：根据 Phase 02 的最小授权快照、Tool 和 Checkpoint 契约复审并确认 Phase 03 计划；Phase 03 必须建立统一 `AuthorizationContext`、`PermissionChecker` 和知识库领域接口，不得直接扩展 Agent 临时类型为知识模型。

## 10. Phase 03 出口审查记录

### 2026-07-30 / P03-T11

- **结论**：P03-T01 至 P03-T11 已完成并通过阶段验收；不自动进入 Phase 04。
- **实现边界**：已实现知识领域、状态机、统一 Ports、tenant-scoped Repository/UoW 契约、`AuthorizationContext`、`PermissionChecker`、`KnowledgeService` 和 `KnowledgeQueryService`；当时没有真实知识基础设施或 RAG。
- **决策**：ADR-018 冻结 `private|tenant`、显式 actor、稳定 Chunk/Index/Retrieval schema 和固定 RAG/Tool 共享查询入口。
- **下一门禁**：O-002/O-006/O-007 以及发生源码抽取时的 O-004 必须先解决。

## 11. Phase 04 出口审查记录

### 2026-07-30 / P04-T12

- **结论**：P04-T01 至 P04-T12 已完成；Phase 04 通过真实后端、Fake Provider、迁移、tenant、Citation/Trace、ruff、strict mypy、密钥卫生和完整 pytest 阶段门禁，不自动进入 Phase 05。
- **实现边界**：已实现 PostgreSQL 知识表、S3/MinIO、Redis/ARQ、TXT/Markdown/PDF、General Chunk、BGE-M3/DeepSeek Provider Adapter、Elasticsearch BM25/KNN/RRF、固定 RAG、Citation/Trace 和知识 API；未实现真实外部模型 smoke、OCR/版面、完整在线检索、生命周期或 Agent Tool。
- **验证证据**：本地临时 Compose 下 153 passed、0 skipped；Fake-only 默认环境 143 passed、10 个显式基础设施 skip；`ruff`、`mypy`、bootstrap、Compose config、Alembic round trip 和 secret hygiene 通过；代码提交 `0732d47` 的 [GitHub Actions](https://github.com/haonanhu02-jpg/ragflow-agent/actions/runs/30533783441) 成功。
- **决策与合规**：ADR-019 已实施；Phase 04 直接复用和改造复用 RAGFlow 源码均为零，后续首次复制前必须重新许可证审查。
- **计划偏差**：用户准入决策将最小 RRF 混合检索提前到 Phase 04；ARQ 要求 `redis<6`；复杂调度、补偿、流式回答和真实 Provider 验证仍按后续阶段处理。
- **下一门禁**：依据 Phase 04 实际 Parser/Chunk/provenance 复审 Phase 05 计划，确认复杂格式、OCR、资源、样本和许可证后才可执行。

## 12. Phase 05 出口审查记录

### 2026-07-31 / P05-T12

- **结论**：P05-T01 至 P05-T12 已完成；Phase 05 通过八格式/九策略、
  资源攻击、并发、内存 E2E、真实 PostgreSQL/MinIO/Redis/Elasticsearch、
  真实 Tesseract CI、ruff、strict mypy、锁文件、迁移、bootstrap 和密钥门禁；
  不自动进入 Phase 06。
- **实现边界**：已实现确定性 Parser/Chunk Registry、TXT/Markdown/HTML/
  DOCX/PPTX/XLSX/PDF/图片、Tesseract OCR、扫描 PDF fallback、原生表格、
  schema v2、bbox/Citation、九种 Chunk Method 和资源限制；未实现模型型
  多栏语义版面、GPU Vision、真实 DeepSeek/BGE-M3、Reranker 或 Phase 06
  查询处理。
- **验证证据**：默认无外部服务环境 169 passed、12 个条件 skip；隔离
  PostgreSQL/MinIO/Redis/Elasticsearch 环境 180 passed、仅本机缺少
  Tesseract 的 1 项显式 skip；Parser/Chunk 专项 25 passed；提交
  `0a4bca1` 的 [GitHub Actions](https://github.com/haonanhu02-jpg/ragflow-agent/actions/runs/30614252319)
  成功，并真实执行 Tesseract `eng`/`chi_sim`、bbox、全部测试、ruff、strict
  mypy、迁移往返、bootstrap、Compose 和密钥门禁。
- **决策与合规**：ADR-020 已实施；RAGFlow 直接复用和改造复用均为零，
  所以没有空 `ragflow_adapters` 包，也没有 RAGFlow 派生源码分发义务。
- **计划偏差**：二进制黄金样本在测试时生成；真实 OCR 由 Linux CI 强制，
  本机缺 Tesseract 时只允许显式 skip；General 保留 `sha256-v1` 兼容，
  场景策略使用 `sha256-v2`。
- **新增/持续风险**：R-030 监控 Parser/Tesseract/PDFium 平台漂移；
  R-015 的复杂企业文档代表性仍未关闭。
- **下一门禁**：Phase 06 预规划草案必须基于 schema v2、Citation bbox、
  现有 Elasticsearch BM25/KNN/RRF 和统一 SearchPort 复审；不得创建第二套
  检索主链路。

## 13. Phase 06 出口审查记录

### 2026-07-31 / P06-T12

- **结论**：P06-T01 至 P06-T12 已完成并通过本地阶段验收；不自动进入 Phase 07。
- **实现边界**：已实现查询规范化/可选改写/翻译/关键词变体、递归 Filter AST、
  Elasticsearch BM25/KNN 双路检索、RRF `k=60`、Provider 隔离 Reranker、阈值/
  TopN、有限安全降级、固定 RAG 统一接线和 PostgreSQL Retrieval Trace；未实现
  真实 DeepSeek/BGE-M3/BGE Reranker 质量/性能验证、生命周期或 Agent Tool。
- **验证证据**：隔离 PostgreSQL/MinIO/Redis/Elasticsearch 全仓回归
  `203 passed, 1 skipped`，唯一 skip 为本机缺 Tesseract；真实 ES+PG 检索/Trace
  专项 `4 passed`；ruff、strict mypy、锁文件、迁移往返、bootstrap、Compose 和
  密钥门禁通过。远程提交/CI 证据在推送闭环后补记。
- **决策与合规**：ADR-021 已实施，O-008 已关闭；RAGFlow 直接复用和改造复用均为
  零，首次复制前仍需重新许可证审查。
- **计划偏差**：改写/翻译/扩展合并到 `transforms.py`，融合文件为 `fusion.py`；
  Citation/Context 沿用 Phase 04 主链路；没有建设 180 天聚合指标仓库或真实 BGE
  运行时，二者都没有被描述成已实现。
- **新增/持续风险**：R-031 监控查询变体噪声/注入，R-032 监控 Reranker 漂移；
  R-006、R-010、R-017 进入持续监控，未因单阶段测试而关闭。
- **下一门禁**：Phase 07 具备计划复审入口；必须冻结版本激活/回滚、重试分类与
  次数、索引切换、软删除/物理回收期限和跨存储补偿后，才可批准执行。
