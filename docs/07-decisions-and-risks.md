---
document_id: DECISIONS-AND-RISKS
status: active
last_updated_at: "2026-08-01"
adr_mode: registry
---

# 决策、待决策事项与风险登记

## 文档导航

[项目总纲](./00-project-master.md) · [RAGFlow 架构](./01-ragflow-architecture.md) · [能力矩阵](./02-ragflow-capability-matrix.md) · [目标架构](./03-target-architecture.md) · [代码复用策略](./04-code-reuse-strategy.md) · [开发路线图](./05-development-roadmap.md) · [工程标准](./06-engineering-standards.md) · [领域契约](./08-domain-model-and-contracts.md) · [Agentic RAG](./10-agentic-rag.md)

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
- 应用数据库、对象存储、搜索和外部 Trace 不是同一事务；可靠 Outbox、幂等和补偿已在 Phase 07 按 ADR-022 实现，仍需按 R-027 持续监控。

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

### ADR-022：Phase 07 文档生命周期与跨存储一致性基线

- **Status**：Accepted and implemented
- **Date**：2026-07-31

**Context**

PostgreSQL、MinIO、Redis 和 Elasticsearch 没有跨系统原子事务。RAGFlow 冻结基线的原地重解析、关系先删后 best-effort 清理、consumer-local pending 和异常后 ACK 不能直接满足本项目的版本连续性、租户隔离和可恢复性目标。

**Decision**

- PostgreSQL 是生命周期、活动版本、期望状态、操作、Outbox 和批次的唯一权威；MinIO 保存对象，Elasticsearch 是可重建投影，Redis/ARQ 只传递任务。
- 不使用 2PC；采用事务 Outbox、不可变 DocumentVersion、幂等任务、持久步骤、CAS revision/fencing、有限重试、补偿和周期对账。
- 新版本全部完成并验证后才切换 `current_version_id`；历史版本默认保留 30 天。回滚只允许健康且未物理清理的版本。
- 默认总尝试 6 次、并发冲突 3 次、指数退避和全抖动、退避上限 300 秒；未知/代码错误不自动重试，耗尽进入持久 dead-letter。
- 全量重建使用稳定读写别名、generation 物理索引、staging 验证和 Elasticsearch 原子 alias 切换；上一健康索引默认保留 7 天。
- 删除先在 PostgreSQL 置 `delete_pending` 并立即清空活动版本；默认保留 30 天，期满后 24 小时清理目标由维护任务保障。外部清理失败不得重新暴露文档。
- 普通批次为单 tenant/单知识库、单文档故障隔离；全量重建只有全部验证通过才切 alias。批次状态从子操作持久状态重算。
- Elasticsearch 候选在返回前必须重新通过 PostgreSQL 的 active/current-version/tenant/权限验证；权威读取错误传播并失败关闭。
- Alembic 管理业务生命周期表；LangGraph `AsyncPostgresSaver.setup()` 只管理 Checkpoint 内部表，两者职责和升级验证分离。
- Phase 07 继续不复制、抽取或改写 RAGFlow 源码；首次复制前必须重新许可证审查。

**Consequences**

- 更新、重解析、回滚、软删除/恢复/回收、Outbox、取消、死信、generation alias、对账和批次形成统一闭环。
- API 与独立 Worker 共享领域/应用服务；没有新增微服务或内部 HTTP。
- 自动跨全部 tenant 的生产调度、告警后端、长时间混沌和容量治理仍属于 Phase 10，不得由当前接口冒充。

**Verification**

- 迁移 `20260731_0004` 执行 `0003 -> 0004 -> 0003 -> 0004` 往返。
- 确定性测试覆盖状态、CAS、取消、重试上限、dead-letter、Outbox 去重、批次重算、删除和对账。
- 隔离真实 PostgreSQL/Redis/MinIO/Elasticsearch 验证更新、投递、发布、唯一活动版本、generation alias、删除不可见和物理回收。

**References**

[生命周期专项文档](./09-document-lifecycle.md)；[Phase 07 执行记录](./phases/phase-07-document-lifecycle.md)

### ADR-023：Phase 08 Agentic RAG 安全、证据、HITL、记忆与预算基线

- **Status**：Accepted; implemented in Phase 08
- **Date**：2026-07-31

**Context**

Phase 02 已提供 LangGraph、租户作用域 Checkpoint、模型/Tool 端口和有限技术重试；Phase 06 已提供唯一 `KnowledgeQueryService`、Citation 与 Retrieval Trace。Phase 08 需要把直接 RAG、知识库 Tool、多步检索、SQL/API、HITL、记忆和运行预算接入同一安全边界。模型输出、Tool 内容和外部数据均不可信，不能决定权限、风险等级、审批或预算。

**Decision**

1. 首批场景固定为：简单问题直接 RAG；Agent 主动使用知识库 Tool；最多三轮的多步骤检索；知识库与只读 SQL/API 联合回答；`sufficient|partial_evidence|no_evidence|conflicting_evidence`；Fake 高风险 Tool 的 HITL；模型/检索/Tool/Checkpoint 故障安全失败或有限重试。直接 RAG 和 Tool RAG 必须分别测试。
2. Tool 采用默认拒绝、显式注册、执行及恢复前重新鉴权。Registry 固定名称/版本、输入输出 Schema、只读/副作用、风险、tenant/role/scope、超时/重试/返回量、幂等、HITL 和脱敏元数据。Shell、动态代码、文件系统、任意 URL、未登记 Tool、SQL 写入/DDL/多语句和密钥访问禁止。
3. SQL 只接受 AST 验证的单条 `SELECT`/只读 CTE，使用独立只读凭据、参数化、Schema/表/列 allowlist、服务端 tenant 条件、默认 5 秒/200 行限制。API 只调用登记的 base URL/path/method，禁止重定向/动态域名，服务端注入凭据和身份，验证请求响应并限制时延/大小。凭据不得进入 Prompt、State、Checkpoint、Memory、Trace 或日志。
4. HITL 状态固定为 `approval_required|approved|rejected|expired|cancelled|executing|succeeded|failed`，请求绑定 run/thread/tool call、Tool 版本、参数摘要、tenant/user、角色、原因、TTL 和幂等键；默认 TTL 30 分钟。模型不能批准；恢复重新检查权限、策略、参数、资源、预算和 TTL；原子 claim 与幂等结果阻止重复副作用。
5. Checkpoint、Trace 和长期记忆分离。长期记忆默认关闭，只保存用户明确同意的最小稳定信息，记录 consent，默认 TTL 90 天，tenant+user 双重隔离；支持查看、撤回、删除和 24 小时内可执行清理，不保存全文、Chunk、Tool 原响应、隐含偏好、凭据或高敏感数据，也不写回知识索引。
6. `EvidenceSufficiencyPolicy` 是服务端最终裁决者；检查授权/活动版本、Phase 06 阈值、关键子问题覆盖、冲突、Citation、SQL/API 范围和提示注入。关键子问题覆盖率为 100%，最多初次加两次补检；不得放宽硬过滤，证据不足或冲突时必须保守终止。
7. 默认单运行预算为：8 次 Agent iteration、6 次模型调用、3 轮检索、10 次 Tool 尝试、50,000 总 Token、8,000 生成 Token、1,500 finalization reserve、120 秒 active runtime、模型 45 秒、Tool 15 秒、已知费用 0.50 USD。HITL 等待不计 active runtime但 TTL 继续；恢复不重置消耗；模型不能提高限额。
8. 使用无敏感信息、可提交、确定性且机器可读的评测集。安全绕过必须 100% 通过且关键违规为零；总体通过率和 Tool 选择合法率至少 90%，no/partial 判断至少 95%，重要事实 Citation 覆盖至少 95%，有证据回答 groundedness 目标至少 90%。Fake 与真实模型报告严格分开。

**Consequences**

- LangGraph 继续作为唯一 Agent 编排；知识 Tool 和直接 RAG 都只调用现有 `KnowledgeQueryService`。
- Phase 08 为审批、长期记忆、运行/Trace 索引建立 Alembic 业务表；官方 LangGraph Checkpoint 表继续由 `AsyncPostgresSaver.setup()` 管理。
- SQL AST 采用独立依赖 `sqlglot>=27,<30`，基础设施执行仍经内部 Port；API/Secret 同样只经 Port。
- 多 Agent 默认关闭；P08-T12 只有可重复评测证明收益时才启用，否则记录暂缓结论。
- Phase 08 不复制、抽取或改写 RAGFlow 源码，不实现前端、GraphRAG、RAPTOR、生产写 Tool 或真实凭据集成。

**Verification**

- Unit 覆盖 State、Tool policy、Evidence、Budget、Memory、SQL/API；Contract/E2E 覆盖 LangGraph 两条路径、Registry、HITL、越权、注入、审批、预算和故障。
- 确定性评测 28/28，通过率、Tool 合法率、no/partial 准确率、Citation 覆盖和 groundedness 均为 100%，关键安全违规 0；这些指标只代表 `deterministic_fake`。
- 真实 PostgreSQL 验证审批/运行/记忆 Repository、租户隔离、CAS、清理、官方 Checkpoint 跨运行时恢复和只读 SQL Adapter；完整隔离四后端套件 286 passed、1 个既有 Tesseract 条件 skip。
- Alembic `20260731_0005 -> 0004 -> 0005` 往返、Ruff、strict mypy、API/Worker bootstrap 和锁文件检查通过。

**References**

[`phase-08-agentic-rag.md`](./phases/phase-08-agentic-rag.md)；[Agentic RAG运行时](./10-agentic-rag.md)；[目标架构](./03-target-architecture.md)

### ADR-024：Phase 09 高级 RAG、时序、多模态与兼容基线

- **Status**：Accepted; implemented in Phase 09
- **Date**：2026-08-01

**Context**

高级派生索引若默认启用或脱离 Phase 06/07 的权限、版本和生命周期边界，会造成越权、残留和不可恢复的数据分叉。GraphRAG、RAPTOR、Vision、ASR 与时序能力还没有真实 Provider 增益证据。

**Decision**

1. 九类高级 capability 按 tenant、knowledge base 和 capability 使用服务端开关，全部默认关闭。普通问题继续走 Phase 06；缺失、损坏、过期或不兼容的高级 manifest 自动回退，且不得放宽 tenant、ACL、知识库、活动版本、删除状态、Evidence、Agent Budget 或 Tool Policy。
2. GraphRAG/RAPTOR 构建异步语义为幂等、可取消、可恢复、可重建并绑定文档版本；PostgreSQL 保存权威元数据，S3/MinIO 保存构建产物，Elasticsearch 保存可检索派生记录，不引入图数据库。节点、边、社区和树节点必须保留源 Chunk、tenant、知识库、文档/构建版本与 provenance。
3. 时序同时覆盖事件时间线和连续数值窗口；不引入专用时序数据库。以 UTC 计算并保留原始时区，确定性服务处理乱序、缺失、窗口、统计、趋势、事件对齐和相似历史窗口；LLM 不负责数值计算。
4. 多模态首批只覆盖图片、图表/页面 Figure 及 Vision 描述，以及音频转写片段；Citation 保留 page/bbox 或时间段。视频明确不实现。Vision/ASR 只经 Provider Port，Fake 与真实报告分离。
5. 提交数据集必须合成或脱敏、授权、版本化、带 Schema/hash/source/license，并分 development/validation/regression。Phase 09 使用服务端硬预算：5000 Chunk、900 秒、500 Provider call、300000 生成 Token、图 20000 实体/50000 边、RAPTOR 4 层、图片 20MB/2500 万像素、音频 30 分钟、时序 100 万点；客户端和模型不能提高。
6. 不复制、抽取或改写 RAGFlow 源码；首次复制仍须重新许可审查。第三方算法必须经 Adapter、许可证和 provenance 登记。

**Consequences and verification**

- 新增 `knowledge/advanced` 独立能力包、统一 `AdvancedArtifact/AdvancedBuild/Manifest`、Alembic `20260801_0006` 和 Phase 07 清理 hook；高级候选仍转换成既有 `RetrievalCandidate/Citation` 并经 `KnowledgeQueryService` 权威校验。
- 确定性专项验证覆盖九类能力、默认关闭、scope/version、构建幂等/取消、RAPTOR 收敛、时区/缺失/乱序和生命周期清理。机器报告把九项全部判为 `no-go`，原因是没有真实模型增益证据；代码与负面结果保留。

**References**

[`phase-09-advanced-rag.md`](./phases/phase-09-advanced-rag.md)；[目标架构](./03-target-architecture.md)；[`datasets/phase09/v1/manifest.json`](../datasets/phase09/v1/manifest.json)

### ADR-025：Phase 10 生产候选、SLO、可观测性、恢复和发布基线

- **Status**：Accepted; implemented as a production candidate in Phase 10
- **Date**：2026-08-01

**Context**

代码和短时隔离测试不能证明月度 SLO 或真实生产上线。最终阶段必须形成可重复制品、供应商中立观测、硬安全门禁、隔离恢复证据与明确的发布结论。

**Decision**

1. 第一版平台为 Linux Docker Compose；保持模块化单体，同一不可变镜像以 API/Worker 命令运行，迁移为独立 one-shot Job。不拆微服务、不引入 Kubernetes。linux/amd64 为主要目标，arm64 仅在实际构建验证后报告。镜像多阶段、non-root、固定基础镜像、无默认密钥并生成 SBOM。
2. 采用 JSON 日志、OpenTelemetry/OTLP、Prometheus、OTel Collector 与 Grafana。观测故障不阻断业务；完整 Prompt/文档/SQL/API 响应、密码、Token、密钥和高敏字段禁止进入日志与 Trace。
3. SLO 目标为月度 99.5% 可用性、readiness p95 500ms、非 LLM API p95 1s、检索 p95 2s、固定 RAG p95 20s、内部错误率低于 1%、跨租户/严重安全违规为 0；积压超过 5 分钟告警。日志/Trace 默认 30 天，指标 90 天。短时测试只作为回归基线，不声称证明月度 SLO。
4. RPO 24 小时、RTO 4 小时，每日备份 PostgreSQL、对象存储、配置和必要 Secret 元数据，默认保留 30 天；搜索索引可重建。恢复只在隔离空环境演练，不覆盖唯一备份或生产数据。
5. 发布职责使用 `release_owner`、`security_approver`、`ops_oncall` 三种角色。TLS 终止、Secret 注入、出口限制、只读账号、依赖/镜像扫描、审计、速率限制和最小权限是生产门禁。
6. O-010 关闭为 Deferred：当前路线图只交付后端 API、Worker、评测和生产候选；UI/管理控制台不属于完成标准，后续必须由新 ADR 和新路线图授权。

**Consequences and verification**

- 生产 Compose、观测配置、版本化评测集、确定性指标/质量门禁、备份恢复/故障/发布工具和运行手册进入仓库。
- 缺少真实 DeepSeek/BGE/Vision/ASR、真实生产凭据、持续 SLO 和真实生产恢复证据时，最终发布结论必须为“不允许发布”，即使代码门禁通过。

**References**

[`phase-10-evaluation-and-production.md`](./phases/phase-10-evaluation-and-production.md)；[生产运行手册](./10-production-runbook.md)；[`deploy/docker-compose.prod.yml`](../deploy/docker-compose.prod.yml)

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

- **Status**：Resolved through Phase 07
- **Resolution**：ADR-019、ADR-020、ADR-021、ADR-022
- **Decision deadline**：首次抽取代码前
- **Question**：内部 Adapter 包、独立 Python 包或独立 Worker？
- **Decision**：Phase 04、Phase 05、Phase 06、Phase 07 均不复制、抽取或改写 RAGFlow 源码；不存在这些阶段的复用代码物理隔离问题。
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

- **Status**：Resolved
- **Resolution**：ADR-024
- **Decision deadline**：Phase 09
- **Question**：哪些知识库启用、构建触发、资源预算和查询路由？
- **Current handling**：能力保留但不默认启用。
- **Required evidence**：Phase 10 评测相对 Phase 06 的增益。

### O-010：前端或管理控制台

- **Status**：Resolved as Deferred scope
- **Resolution**：ADR-025
- **Decision deadline**：Phase 10 结束后另行修订路线图，或更早出现明确展示需求时
- **Question**：是否建设 UI，覆盖知识库、任务、检索 Trace、Agent 和评测中的哪些页面？
- **Current handling**：只规划 FastAPI，不假定 UI。

### O-011：时序 RAG 数据模型、存储与查询边界

- **Status**：Resolved
- **Resolution**：ADR-024
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
| R-005 | PostgreSQL、对象存储、搜索索引不一致 | 中 | 严重 | 孤儿对象、孤儿 Chunk、错误 current version | ADR-022；DocumentVersion、候选索引、Outbox、补偿和对账 | Phase 07/10 | Monitoring |
| R-006 | 搜索后端分数和过滤语义不一致 | 高 | 高 | 相同数据不同排序/过滤结果 | O-002、SearchPort 契约、RRF、原始排名/分数 Trace、真实 ES 固定评测 | Phase 04/06/10 | Monitoring |
| R-007 | Embedding 变化使旧索引不可用 | 中 | 高 | 模型/维度更新 | 记录模型和维度；generation staging/验证/alias 切换；旧索引保留 | Phase 07/10 | Monitoring |
| R-008 | Citation 指向错误版本、页码或删除内容 | 中 | 严重 | quote 不存在、引用旧版或越权文档 | document_version_id；返回前 PostgreSQL active/current-version 验证；删除立即不可见 | Phase 04/06/07/10 | Monitoring |
| R-009 | Agent 循环失控、成本过高或不可恢复 | 高 | 高 | 循环增长、重复 Tool、Checkpoint 失败 | ADR-023；服务端多维预算、重复调用保护、持久 Checkpoint、恢复不重置和 Trace | Phase 02/08/10 | Monitoring |
| R-010 | 权限过滤遗漏导致数据泄露 | 中 | 严重 | 越权检索或 Citation | ADR-012/021；Repository/Search 强制 tenant/ACL/状态/范围；所有降级负向测试 | Phase 03/06/08/10 | Monitoring |
| R-011 | GraphRAG/RAPTOR 增加复杂度但无质量收益 | 高 | 高 | 成本上升、指标不升 | 默认关闭；Phase 10 对照评测 | Phase 09/10 | Open |
| R-012 | RAGFlow/第三方许可证或模型再分发不清楚 | 中 | 严重 | 缺许可证、权重限制、样本来源不明 | provenance、依赖清单、人工法律复核 | 所有复用阶段 | Open |
| R-013 | 文档规划过度，Minimum RAG 延迟 | 中 | 中 | Phase 00 持续扩大而无出口 | Phase 00 已归档；Phase 01 后按任务 DoD 推进 | Phase 00 | Mitigated |
| R-014 | 抽象过度导致 Phase 04 没有垂直切片 | 中 | 高 | 只有 Protocol/DTO，没有端到端请求 | Phase 04 已完成 Fake 与真实基础设施上传到回答 E2E | Phase 03/04 | Closed |
| R-015 | 测试数据不能代表复杂企业文档 | 高 | 高 | 黄金样本过于简单，线上质量差 | 多格式复杂样本、轨道交通脱敏集、错误样本 | Phase 05/10 | Open |
| R-016 | LLM/Embedding/Reranker 供应商波动 | 高 | 中 | 限流、价格、模型下线、响应变化 | 模型注册、契约测试、回退、版本锁定 | Phase 04/10 | Open |
| R-017 | Trace 记录敏感原文 | 中 | 严重 | 日志或 Trace 泄露文档内容 | 数据最小化、查询摘要、tenant/角色读取、30 天 TTL、真实 PG 清理测试 | Phase 01/06/10 | Monitoring |
| R-018 | 任务取消与重试竞态产生重复索引 | 中 | 高 | 已取消任务继续写入 | 协作取消边界、CAS/fencing、幂等 key、候选索引和最终检查 | Phase 07/10 | Monitoring |
| R-019 | 模块化单体退化为 API/Worker 两套重复实现 | 中 | 高 | 重复 DTO、内部 HTTP、行为漂移 | ADR-011；共享领域/应用层；导入边界与契约测试 | Phase 01 持续 | Open |
| R-020 | 队列消息 tenant 与数据库资源 tenant 不一致 | 中 | 严重 | 跨租户任务执行或索引污染 | tenant_id + job_id 加载、双重校验、安全审计、拒绝执行 | Phase 03/04/07 | Open |
| R-021 | 把搜索 Chunk 误建模为 RAGFlow 关系表或照搬缺 tenant 的 Task/Document | 中 | 高 | 领域模型与索引字段耦合、Worker 漏做租户过滤 | 采用 `ChunkRecord`；任务信封显式 tenant；数据库二次校验；参见源码证据 RF-D03/D05/D07 | Phase 03/04/07 | Open |
| R-022 | 文档关系行先删除而对象、索引或派生数据清理失败 | 中 | 高 | 外部 cleanup 留下孤儿数据 | PostgreSQL tombstone 先撤销可见性；幂等清理；reconciler；保留最小审计墓碑 | Phase 07/10 | Monitoring |
| R-023 | 预生成的后续阶段计划与上一阶段实际产物漂移 | 高 | 高 | 计划引用的接口、文件或决策已变化 | ADR-013；每阶段入口重新审查；未审查不得执行 | Phase 01–10 | Open |
| R-024 | 时序 RAG 范围和后端未定义导致 Phase 09 失控 | 高 | 高 | 同时引入新存储、算法和数据模型且无基线 | ADR-014；O-011；默认关闭；独立数据集和实验门禁 | Phase 09/10 | Open |
| R-025 | 官方 PostgreSQL Checkpointer 升级导致内部 schema 或恢复语义漂移 | 中 | 高 | 依赖升级后 setup、恢复、list/delete 或并发测试失败 | 锁定依赖；不手改上游表；真实 PostgreSQL 迁移/恢复回归；升级前审查 release notes | Phase 02 持续/Phase 10 | Monitoring |
| R-026 | Agent 最小授权快照与知识 AuthorizationContext 映射漂移 | 中 | 高 | Tool Adapter 错把 `user_id` 当 tenant、恢复后跳过权限重验或字段改名破坏 Checkpoint | AgentState v1 不破坏；显式 `user_id → actor_id` Adapter；tenant/thread/run 与 PermissionChecker 双重验证；跨租户 Tool 契约测试 | Phase 08/10 | Monitoring |
| R-027 | 数据库提交与对象存储、搜索、Queue、Trace 非原子导致部分成功 | 高 | 高 | 写入已提交但事件/索引/Trace 失败，重试产生重复或状态漂移 | ADR-022；Outbox、候选索引、CAS、补偿、残留扫描和故障注入 | Phase 04/07/10 | Monitoring |
| R-028 | ARQ maintenance-only 导致未来 Python/Redis 兼容或安全修复不足 | 中 | 高 | 新 Python/Redis 无法运行、关键缺陷长期无修复 | 锁定 0.28；只用最小接口；QueuePort 隔离；真实 Redis 回归；必要时替换 Adapter | Phase 04/10 | Monitoring |
| R-029 | Elasticsearch Client/Server 版本或 KNN 语义漂移 | 中 | 高 | mapping、查询参数、分数或过滤在升级后变化 | 锁定 8.19 系列；真实 BM25/KNN/混合/tenant 契约测试；DSL 限于 Adapter | Phase 04/06/10 | Monitoring |
| R-030 | Parser 格式库、PDFium、Tesseract 或语言数据跨平台漂移 | 中 | 高 | 同一文档输出结构变化、运行时缺失、语言包不可用或坐标漂移 | 锁定 Python 依赖；外部运行时能力检测；生成式黄金；Linux CI 真实 OCR；资源/错误契约；升级前基线比较 | Phase 05 持续/Phase 10 | Monitoring |
| R-031 | 查询改写/翻译/关键词扩展引入噪声或 Prompt 注入 | 中 | 高 | 召回下降、恶意历史改变查询范围、变体爆炸 | 结构化 Provider、变体上限/去重、可关闭开关、失败回 canonical、硬过滤不随变体变化 | Phase 06/08/10 | Monitoring |
| R-032 | Reranker 模型、端点或分数语义漂移 | 高 | 高 | 排名突变、超时、身份集合变化、GPU 不可用 | 内部 Port、超时、候选身份校验、RRF 回退、Fake 契约；真实模型回归后置 | Phase 06/10 | Monitoring |
| R-033 | 生命周期维护任务没有跨 tenant 生产调度与告警闭环 | 中 | 高 | 到期 Outbox、delete_pending 或 stale operation 积压 | Worker 暴露 tenant-scoped 调度函数；reconciler bounded/dry-run；Phase 10 接入调度、指标和告警 | Phase 07/10 | Open |
| R-034 | 长时间并发、Worker kill 或网络分区暴露单机故障注入未覆盖的竞态 | 中 | 严重 | fencing 冲突增长、alias/DB 长期不收敛、DLQ 积压 | CAS/fencing、实际状态对账、隔离真实后端测试；Phase 10 增加长时间混沌和容量门禁 | Phase 07/10 | Open |
| R-035 | 确定性 Fake Agent 评测高估真实模型的 Tool 选择、证据判断或成本表现 | 高 | 高 | 切换真实 DeepSeek/BGE/Reranker 后指标下降或预算估算失真 | Fake/真实报告分离；Phase 10 版本化真实模型集、阈值和费用回归 | Phase 08/10 | Open |
| R-036 | 生产 SQL/API catalog、只读账号、网络出口和凭据轮换尚未验证 | 中 | 严重 | allowlist 配错、数据越权、SSRF 或凭据泄漏 | 默认不注册；独立只读账号、固定网络目标、Secret Provider、上线前隔离集成/渗透测试 | Phase 08/10 | Open |
| R-037 | 高风险外部副作用在执行成功但结果持久化前崩溃，仍可能被重试 | 低 | 严重 | Tool 端已生效但 Agent 未记录 succeeded | Tool 必须接受幂等键并提供结果查询/幂等合同；生产写 Tool 在 Phase 10 前保持禁用 | Phase 08/10 | Open |
| R-038 | 长期记忆物理清理调度或积压没有生产 SLO | 中 | 高 | 撤回记录超过 24 小时仍物理存在 | 查询立即屏蔽；Worker 清理可执行；Phase 10 增加跨 tenant 调度、积压指标、告警和故障演练 | Phase 08/10 | Open |
| R-039 | 本地/Fake 生产候选证据被误报为真实上线完成 | 高 | 严重 | 用短时合成报告宣称月度 SLO、真实模型效果或生产恢复 | 证据分层；fail-closed release report；外部阻断项未关闭前不允许发布 | 生产接入 | Open |
| R-040 | 生产 IdP、Secret、TLS 或出口策略尚未接入 | 高 | 严重 | 业务接口无可信身份、凭据泄漏或任意网络出口 | internal 网络、TLS/限流配置、环境注入；真实接入和安全审批前保持阻断 | 生产接入 | Open |
| R-041 | 项目自身分发许可证尚未由所有者确认 | 中 | 严重 | 对外分发镜像/源码但仓库无正式 LICENSE | SBOM/provenance 分离；由所有者选择并提交 LICENSE 后重新审查 | 发布治理 | Open |
| R-042 | 生产容量、耐久、费用与月度 SLO 未由代表性负载证明 | 高 | 高 | 合成短测通过但真实峰值、积压或费用超限 | 目标环境阶梯/耐久测试、持续监控和有期限容量审批 | 生产接入 | Open |
| R-043 | 生产备份恢复、索引重建和回滚未用真实规模演练 | 中 | 严重 | 恢复超 RTO、权限/Citation 漂移或迁移无法回退 | 隔离生产快照演练、双人审批、恢复后安全与评测门禁 | 生产接入 | Open |

## 5. 风险处理规则

1. 严重影响的 Open 风险必须在相关阶段入口检查。
2. 风险成为现实问题时，创建 issue/任务并保留风险 ID。
3. 接受风险必须说明接受期限和责任人。
4. 风险关闭需要证据，不以“代码已写”作为充分条件。
5. 新的架构选择如果改变多个风险，必须形成 ADR。

## 6. 当前决策摘要

- Accepted：ADR-001 至 ADR-005、ADR-007 至 ADR-025。
- Resolved：O-001 → ADR-016；O-002/O-006 → ADR-019；O-007 → ADR-019/020/021；O-003 → ADR-011；O-004（Phase 04–07 不抽取）→ ADR-019/020/021/022；O-005 → ADR-012；O-008 → ADR-021；O-012 → ADR-016。
- Resolved：O-009/O-011 → ADR-024；O-010 → ADR-025（UI 继续为范围外 Deferred）。
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
  密钥门禁通过。实现提交 `80e3d312e6dfc3b4ba0e66aa94ca01aa19109813`
  已推送到 `origin/main`，对应 [GitHub Actions 运行 #9](https://github.com/haonanhu02-jpg/ragflow-agent/actions/runs/30627535052)
  成功（2 分 22 秒）。
- **决策与合规**：ADR-021 已实施，O-008 已关闭；RAGFlow 直接复用和改造复用均为
  零，首次复制前仍需重新许可证审查。
- **计划偏差**：改写/翻译/扩展合并到 `transforms.py`，融合文件为 `fusion.py`；
  Citation/Context 沿用 Phase 04 主链路；没有建设 180 天聚合指标仓库或真实 BGE
  运行时，二者都没有被描述成已实现。
- **新增/持续风险**：R-031 监控查询变体噪声/注入，R-032 监控 Reranker 漂移；
  R-006、R-010、R-017 进入持续监控，未因单阶段测试而关闭。
- **下一门禁**：Phase 07 具备计划复审入口；必须冻结版本激活/回滚、重试分类与
  次数、索引切换、软删除/物理回收期限和跨存储补偿后，才可批准执行。

## 14. Phase 07 出口审查记录

### 2026-07-31 / P07-T11

- **结论**：P07-T01 至 P07-T11 已完成并通过本地阶段验收；不自动进入 Phase 08。
- **准入决策**：ADR-022 冻结 PostgreSQL 权威状态、事务 Outbox/幂等步骤/补偿对账、不可变版本及 CAS/fencing、6 次总尝试/3 次并发冲突、generation alias、30 天版本与软删除、7 天旧索引保留和 tenant/KB 批量隔离。
- **实现边界**：已实现更新/重解析、候选版本发布、回滚、删除/恢复/物理回收、generation staging/验证/alias、重试/取消/dead-letter/进度、Outbox、bounded reconciler、批次状态和 PostgreSQL 最终候选校验；没有实现跨 tenant 自动调度、生产告警、长时间混沌、复杂 RBAC 或 Phase 08 Agent Tool。
- **验证证据**：隔离 PostgreSQL/Redis/MinIO/Elasticsearch 全仓 `221 passed, 1 skipped`，唯一 skip 为本机没有 Tesseract；真实生命周期 E2E `1 passed`，前序真实后端回归 `11 passed`；Alembic `0003 -> 0004 -> 0003 -> 0004`、ruff、strict mypy、锁文件、bootstrap、Compose 和密钥门禁通过。实现提交 `71f15d5` 已推送到 `origin/main`，对应 [GitHub Actions 运行 `30634884467`](https://github.com/haonanhu02-jpg/ragflow-agent/actions/runs/30634884467) 成功。
- **决策与合规**：RAGFlow 直接复用和改造复用仍为零；`document_api`、`DocumentService`、`TaskService`、Redis pending/ACK 和 `_prune_deleted_chunks` 仅作行为/反例证据。
- **计划偏差**：Outbox 立即投递由 API best-effort 触发，Worker 同时暴露 tenant-scoped dispatch/reconcile 函数；生产级跨 tenant 周期调度和告警后置 Phase 10。真实模型仍未验证。
- **当时的下一门禁**：Phase 07 出口时，Phase 08 的代码依赖已满足但计划仍待复审；该门禁随后已由用户批准和 ADR-023 关闭，实际结果见第 15 节。

## 15. Phase 08 出口审查记录

### 2026-07-31 / P08-T13

- **结论**：P08-T01 至 P08-T13 已完成并通过本地阶段验收；不自动进入 Phase 09。
- **准入与实现决策**：ADR-023 冻结并实施直接/Tool RAG、默认拒绝 Tool Registry、SQL/API 安全、八态 HITL、显式同意长期记忆、服务端 Evidence、九维预算和确定性评测八项策略。
- **实现边界**：已实现 Agentic API/Runtime、两条 RAG 路径、结构化规划与最多三轮检索、Evidence Policy、受控 SQL/API、持久化审批/Checkpoint、长期记忆 TTL 清理、Agent/Retrieval Trace 关联和机器评测；未接入真实 DeepSeek/BGE-M3/BGE Reranker、生产 SQL/API、生产写 Tool或前端。
- **验证证据**：定向 Phase 08 套件 62 passed/3 个无 PostgreSQL 配置的条件 skip，Phase 08 PostgreSQL Repository/Checkpoint/只读 SQL Adapter 专项另行 3/3 通过；完整隔离 PostgreSQL/Redis/MinIO/Elasticsearch 套件 286 passed/1 个既有 Tesseract skip；28/28 Fake 评测通过且关键安全违规 0；Ruff、strict mypy、锁文件、迁移往返和 bootstrap 通过。
- **复用与合规**：Phase 08 没有复制、抽取或改写 RAGFlow 源码；RAGFlow Retrieval Tool、Agentic 图和 Canvas 人工输入只作为公开行为/职责依据。
- **计划偏差**：节点保持在内聚图文件，安全/故障测试沿用现有测试层级；P08-T12 依据无额外收益的单 Agent 基线暂缓多 Agent；真实模型和生产外部系统没有被 Fake 验证冒充。
- **新增风险**：R-035 至 R-038 分别记录真实模型评测、生产 SQL/API、外部副作用幂等和长期记忆清理 SLO 的剩余风险。
- **下一门禁**：Phase 09 的代码依赖已满足；正式执行前仍须复审计划并解决 O-009、O-011、数据集/资源预算和高级/普通索引兼容策略。

## 16. Phase 09 出口审查记录

### 2026-08-01 / P09-T12

- **结论**：P09-T01 至 P09-T12 已完成并通过本地阶段验收；按用户连续执行授权进入 Phase 10。
- **决策**：ADR-024 关闭 O-009/O-011；九类高级 capability 默认关闭，无 Neo4j/专用时序库，图片/图表/音频为多模态首批范围，视频不实现。
- **实现边界**：实现版本化派生物、关键词/问题/三层摘要/TOC/父子扩展、多模态、GraphRAG、RAPTOR、事件与数值时序、兼容回退和生命周期清理；RAGFlow 复制/抽取/改写为零。
- **验证证据**：隔离 PostgreSQL/Redis/MinIO/Elasticsearch 全仓 `324 passed, 1 skipped`，skip 为本机无 Tesseract；Alembic `0005 -> 0006 -> 0005 -> 0006`、Ruff、strict mypy、锁文件和专项评测通过。
- **go/no-go**：九项机器结果安全违规为 0，但因没有真实 DeepSeek/BGE/Vision/ASR 增益证据全部为 no-go，代码和负面报告保留，开关保持 off。
- **下一门禁**：Phase 10 已由 ADR-025 批准；生产发布仍受真实 Provider、生产凭据/网络、业务数据、持续 SLO 和真实恢复证据阻断。

## 17. Phase 10 出口审查记录

### 2026-08-01 / P10-T13

- **结论**：P10-T01 至 P10-T13 的规划内代码、数据集、测试、部署候选和文档已完成；机器报告结论为 `production_exit=not_allowed`。
- **实施事实**：版本化评测与不可豁免门禁、JSON/OTel/Prometheus/Grafana、Linux Docker Compose、同镜像 API/Worker、one-shot 迁移、TLS/限流配置、SBOM/依赖/Secret/provenance 扫描、内容 hash 备份恢复和隔离故障演练已落地。
- **实测边界**：Linux/amd64 镜像、PostgreSQL/Redis/MinIO/Elasticsearch、API/Worker 与本地观测栈实测；Fake/Stub 与真实基础设施分开报告。未运行的 arm64、真实 Provider、生产 IdP/凭据/业务数据、持续 SLO 和生产恢复/容量不标记通过。
- **许可证**：RAGFlow 源码复制/抽取/改写继续为零；依赖 SBOM 和审计已生成。项目自身分发 LICENSE 尚待所有者确认，记录为 R-041。
- **阻断项**：R-039 至 R-043 及真实 Provider/业务数据验证全部关闭前，`release_owner`、`security_approver`、`ops_oncall` 不得批准真实生产发布。
- **范围**：UI/管理控制台继续 Deferred；路线图没有 Phase 11，新增能力只能通过新 ADR 和下一轮路线图提出。
