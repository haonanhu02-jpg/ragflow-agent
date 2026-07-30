---
document_id: DECISIONS-AND-RISKS
status: active
last_updated_at: "2026-07-30"
adr_mode: registry
---

# 决策、待决策事项与风险登记

## 文档导航

[项目总纲](./00-project-master.md) · [RAGFlow 架构](./01-ragflow-architecture.md) · [能力矩阵](./02-ragflow-capability-matrix.md) · [目标架构](./03-target-architecture.md) · [代码复用策略](./04-code-reuse-strategy.md) · [开发路线图](./05-development-roadmap.md) · [工程标准](./06-engineering-standards.md)

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

- **Status**：Accepted
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

## 3. 开放与已解决的待决策事项

### O-001：项目正式名称和 Python 包名

- **Status**：Deferred
- **Decision deadline**：Phase 01 开始前
- **Question**：项目、发行包和 import package 使用什么名称？
- **Current handling**：文档使用 `src/app` 占位，不创建包；ADR-013 已将其限定为 Phase 01 执行门禁，不再阻止 Phase 00 归档。
- **Impact**：目录、配置前缀、日志 service name、镜像名。

### O-002：首个搜索引擎

- **Status**：Deferred
- **Decision deadline**：Phase 04 开始前
- **Question**：首个 SearchPort Adapter 使用 Elasticsearch 还是 OpenSearch？
- **Options**：
  - Elasticsearch：与 RAGFlow 默认路径更接近。
  - OpenSearch：独立开源生态和相似 API。
- **Required evidence**：BM25、KNN、过滤、批量写入、索引别名、部署资源和许可证比较。
- **Current handling**：只定义端口，不写具体 DSL。

### O-003：API 与 Ingestion 物理拓扑

- **Status**：Resolved
- **Resolution**：ADR-011
- **Decision**：模块化单体；同仓库、FastAPI 与独立 Ingestion Worker 分进程、队列连接、第一版不拆微服务。

### O-004：RAGFlow 复用代码物理隔离

- **Status**：Deferred
- **Decision deadline**：首次抽取代码前
- **Question**：内部 Adapter 包、独立 Python 包或独立 Worker？
- **Current handling**：只做源码审计，不复制。
- **Required evidence**：依赖大小、模型资源、进程稳定性、许可证和部署影响。

### O-005：多租户和权限模型

- **Status**：Resolved
- **Resolution**：ADR-012
- **Decision**：第一版强制 tenant 隔离并实现 owner/visibility、AuthorizationContext 和 PermissionChecker；复杂 RBAC、部门权限与动态数据规则后置。
- **Remaining design detail**：visibility 枚举和继承、具体表约束在 Phase 03 详细设计中固化，但不得削弱已接受的最低边界。

### O-006：后台任务与可靠消息实现

- **Status**：Deferred
- **Decision deadline**：Phase 04 开始前
- **Question**：使用哪种任务库和消息语义？
- **Required capability**：ACK、重试、取消、延迟、积压、崩溃恢复、幂等、可观察。
- **Current handling**：TaskQueuePort 和 IngestionJob 契约优先。

### O-007：首批模型

- **Status**：Deferred
- **Decision deadline**：Phase 04 开始前
- **Question**：LLM、Embedding、Reranker、OCR、Vision、ASR 的首批 Provider/模型？
- **Current handling**：只定义模型能力和注册接口。
- **Required evidence**：语言、维度、上下文、成本、延迟、隐私、部署、许可证和回退。

### O-008：空结果降级默认策略

- **Status**：Deferred
- **Decision deadline**：Phase 06
- **Question**：降低阈值、去除改写、放宽 metadata、跨知识库还是直接空结果？
- **Current handling**：返回结构化 `empty_reason`，不默认扩大权限或知识库范围。
- **Security constraint**：任何降级不得放宽权限过滤。

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

- **Status**：Deferred
- **Decision deadline**：P01-T01
- **Question**：是否在目标目录初始化 Git；首个 CI 平台和 Python 类型检查器采用什么？
- **Current handling**：不执行 `git init`，不生成 CI 配置，不把任一类型检查器写成已确认技术栈；Phase 01 文档使用 `<type-checker>` 占位。
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
| R-006 | 搜索后端分数和过滤语义不一致 | 高 | 高 | 相同数据不同排序/过滤结果 | O-002、SearchPort 契约、固定评测集 | Phase 04/06 | Open |
| R-007 | Embedding 变化使旧索引不可用 | 中 | 高 | 模型/维度更新 | 记录模型和维度；新 index_version；重建切换 | Phase 07 | Open |
| R-008 | Citation 指向错误版本、页码或删除内容 | 中 | 严重 | quote 不存在、引用旧版或越权文档 | document_version_id、验证器、删除可见性 | Phase 04/06/07 | Open |
| R-009 | Agent 循环失控、成本过高或不可恢复 | 高 | 高 | 循环增长、重复 Tool、Checkpoint 失败 | 上限、预算、超时、Checkpoint、取消、Trace | Phase 02/08 | Open |
| R-010 | 权限过滤遗漏导致数据泄露 | 中 | 严重 | 越权检索或 Citation | ADR-012；AuthorizationContext、PermissionChecker、Repository/Search 强制 tenant 条件；负向测试 | Phase 03/06/08/10 | Open |
| R-011 | GraphRAG/RAPTOR 增加复杂度但无质量收益 | 高 | 高 | 成本上升、指标不升 | 默认关闭；Phase 10 对照评测 | Phase 09/10 | Open |
| R-012 | RAGFlow/第三方许可证或模型再分发不清楚 | 中 | 严重 | 缺许可证、权重限制、样本来源不明 | provenance、依赖清单、人工法律复核 | 所有复用阶段 | Open |
| R-013 | 文档规划过度，Minimum RAG 延迟 | 中 | 中 | Phase 00 持续扩大而无出口 | Phase 00 已归档；Phase 01 后按任务 DoD 推进 | Phase 00 | Mitigated |
| R-014 | 抽象过度导致 Phase 04 没有垂直切片 | 中 | 高 | 只有 Protocol/DTO，没有端到端请求 | Phase 04 出口必须完成上传到回答 | Phase 03/04 | Open |
| R-015 | 测试数据不能代表复杂企业文档 | 高 | 高 | 黄金样本过于简单，线上质量差 | 多格式复杂样本、轨道交通脱敏集、错误样本 | Phase 05/10 | Open |
| R-016 | LLM/Embedding/Reranker 供应商波动 | 高 | 中 | 限流、价格、模型下线、响应变化 | 模型注册、契约测试、回退、版本锁定 | Phase 04/10 | Open |
| R-017 | Trace 记录敏感原文 | 中 | 严重 | 日志或 Trace 泄露文档内容 | 数据最小化、脱敏、访问控制、保留策略 | Phase 01/06/10 | Open |
| R-018 | 任务取消与重试竞态产生重复索引 | 中 | 高 | 已取消任务继续写入 | 状态比较、幂等 key、候选索引和最终检查 | Phase 07 | Open |
| R-019 | 模块化单体退化为 API/Worker 两套重复实现 | 中 | 高 | 重复 DTO、内部 HTTP、行为漂移 | ADR-011；共享领域/应用层；导入边界与契约测试 | Phase 01 持续 | Open |
| R-020 | 队列消息 tenant 与数据库资源 tenant 不一致 | 中 | 严重 | 跨租户任务执行或索引污染 | tenant_id + job_id 加载、双重校验、安全审计、拒绝执行 | Phase 03/04/07 | Open |
| R-021 | 把搜索 Chunk 误建模为 RAGFlow 关系表或照搬缺 tenant 的 Task/Document | 中 | 高 | 领域模型与索引字段耦合、Worker 漏做租户过滤 | 采用 `ChunkRecord`；任务信封显式 tenant；数据库二次校验；参见源码证据 RF-D03/D05/D07 | Phase 03/04/07 | Open |
| R-022 | 文档关系行先删除而对象、索引或派生数据清理失败 | 中 | 高 | `remove_document` 后续 best-effort cleanup 留下孤儿数据 | 删除先撤销可见性；补偿日志；幂等清理；reconciliation；保留审计墓碑 | Phase 07/10 | Open |
| R-023 | 预生成的后续阶段计划与上一阶段实际产物漂移 | 高 | 高 | 计划引用的接口、文件或决策已变化 | ADR-013；每阶段入口重新审查；未审查不得执行 | Phase 01–10 | Open |
| R-024 | 时序 RAG 范围和后端未定义导致 Phase 09 失控 | 高 | 高 | 同时引入新存储、算法和数据模型且无基线 | ADR-014；O-011；默认关闭；独立数据集和实验门禁 | Phase 09/10 | Open |

## 5. 风险处理规则

1. 严重影响的 Open 风险必须在相关阶段入口检查。
2. 风险成为现实问题时，创建 issue/任务并保留风险 ID。
3. 接受风险必须说明接受期限和责任人。
4. 风险关闭需要证据，不以“代码已写”作为充分条件。
5. 新的架构选择如果改变多个风险，必须形成 ADR。

## 6. 当前决策摘要

- Accepted：ADR-001 至 ADR-005、ADR-007 至 ADR-015。
- Resolved：O-003 → ADR-011；O-005 → ADR-012。
- Deferred：O-001、O-002、O-004、O-006、O-007、O-008、O-009、O-010、O-011、O-012。
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
