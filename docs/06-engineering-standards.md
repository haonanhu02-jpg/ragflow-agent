---
document_id: ENGINEERING-STANDARDS
status: active
last_updated_at: "2026-08-01"
applies_to: D:/download/ragflow-agent
---

# 工程标准

## 文档导航

[项目总纲](./00-project-master.md) · [RAGFlow 架构](./01-ragflow-architecture.md) · [能力矩阵](./02-ragflow-capability-matrix.md) · [目标架构](./03-target-architecture.md) · [代码复用策略](./04-code-reuse-strategy.md) · [开发路线图](./05-development-roadmap.md) · [决策与风险](./07-decisions-and-risks.md) · [领域契约](./08-domain-model-and-contracts.md) · [Agentic RAG](./10-agentic-rag.md)

## 1. 适用范围

本标准适用于源码、测试、数据库迁移、配置、Prompt、评测数据、部署文件和文档。当前项目已完成 Phase 01 至 Phase 09；Phase 10 生产候选实施继续受本文件约束。

冲突处理：

1. 用户最新明确指令。
2. 已接受 ADR。
3. [项目总纲](./00-project-master.md)。
4. 本标准。
5. 阶段文档和模块局部约定。

## 2. 事实与变更管理

1. 计划、实现、验证和发布必须是不同状态。
2. “已实现”要求同时存在代码、必要迁移和自动化测试。
3. 修改能力名称或阶段归属时同步更新[能力矩阵](./02-ragflow-capability-matrix.md)和[开发路线图](./05-development-roadmap.md)。
4. 修改模块边界时同步更新[目标架构](./03-target-architecture.md)。
5. 修改 RAGFlow 采用分类时同步更新[代码复用策略](./04-code-reuse-strategy.md)。
6. 新决策先记录到[决策与风险](./07-decisions-and-risks.md)，接受后再实施。
7. 禁止把浮动 RAGFlow `main` 的行为当成冻结基线事实。

## 3. Python 与依赖

### 3.1 语言和环境

- Python 3.13。
- `uv` 管理环境、依赖和 lock。
- 运行和测试不得依赖未写入项目依赖清单的本机包。
- 生产依赖、开发依赖和可选 Parser/模型依赖必须分组。

### 3.2 类型

1. 新增公共函数、方法、DTO 和端口必须有完整类型标注。
2. 禁止在领域接口使用无说明的 `dict[str, Any]` 代替稳定 DTO。
3. 外部 JSON 在接口边界验证后才能进入应用层。
4. Parser 原始字典必须在 Adapter 内转换为 ParsedDocument。
5. `Any` 只允许用于外部库边界，并要求就地收窄。

### 3.3 依赖引入

引入新依赖必须记录：

- 使用能力。
- 无该依赖的替代方案。
- 许可证。
- 包大小和原生依赖。
- Python 3.13 兼容性。
- 安全维护状态。
- 是否进入默认安装或可选 extra。

模型权重和原生二进制不等同于 Python 包，必须单独登记。

### 3.4 Phase 01 已落地的基础工具

- `pytest` 作为测试运行器。
- `ruff` 作为格式和 lint 工具。
- `mypy` 以 strict 模式作为类型检查器。
- `uv` 负责创建项目 `.venv`、同步依赖和维护 `uv.lock`。
- 当前规范命令为 `uv sync --frozen --all-groups`、`uv run pytest`、`uv run ruff check .`、`uv run mypy src/ragflow_agent tests` 和 `uv run python scripts/check_secret_hygiene.py`。
- 根 `AGENTS.md`、README 和 `.github/workflows/ci.yml` 已固化相同质量入口。

Phase 01 已在本地验证全部命令并创建 GitHub Actions 工作流；远程 CI 的实际结论必须以对应 commit 的运行结果为准。

### 3.5 Phase 02 已落地的 Agent 依赖

- `langgraph-checkpoint-postgres` 是持久 Agent Checkpoint 的直接依赖，版本必须由 `uv.lock` 固定。
- `psycopg[binary,pool]` 仅安装在项目 `.venv`；Windows 异步 PostgreSQL 测试继续使用 Selector event loop。
- Checkpointer 升级必须运行真实 PostgreSQL 的 setup、list/delete、失败恢复、并发和跨租户回归；不得只运行内存 Saver 测试。

## 4. 包结构与导入边界

### 4.1 领域层

`src/ragflow_agent/knowledge/domain`：

- 只包含实体、值对象、状态规则和领域错误。
- 不导入 FastAPI、SQLAlchemy、LangChain、LangGraph、Redis、MinIO、Elasticsearch、OpenSearch 或 RAGFlow。
- 不读取环境变量。
- 不建立网络连接。

### 4.2 端口层

`src/ragflow_agent/knowledge/ports`：

- 定义 Protocol/ABC、请求和响应 DTO。
- 不包含具体客户端。
- 每个端口必须有契约测试套件。

### 4.3 应用层

- 编排领域对象和端口。
- 定义事务/补偿边界。
- 不构造供应商特有 DSL。
- 不通过 `common.settings` 或全局变量取连接。

### 4.4 基础设施层

- 实现端口。
- 负责外部异常到领域错误的转换。
- 负责连接池、序列化、重试和超时。
- RAGFlow 派生代码默认只允许在 `infrastructure/ragflow_adapters`。

### 4.5 Agent 层

- LangGraph State 不替代数据库实体。
- Tool 只调用应用服务。
- Agent 节点不访问 SQLAlchemy Session、Redis client 或 Search client。
- Agent 的循环、预算、超时和终止必须显式。

### 4.6 进程入口

- `src/ragflow_agent/bootstrap/api.py` 和 `src/ragflow_agent/bootstrap/ingestion_worker.py` 是同一模块化单体的两个入口。
- 两个入口共享领域模型、应用服务和端口，不复制代码、不建立内部 HTTP 调用。
- FastAPI 入口不得导入并直接运行 Parser/OCR/Embedding pipeline。
- Worker 入口不得导入 API 路由，也不得构造 HTTP request context。
- 进程特有 wiring 留在 bootstrap；业务模块不得根据“当前是 API 还是 Worker”分支执行不同领域规则。

## 5. 异步与并发

1. FastAPI 路径不得执行长时间 CPU/OCR/Embedding 工作。
2. 同步第三方库在明确线程池或任务 Worker 中执行。
3. 不在异步函数中调用无界阻塞 I/O。
4. 每个外部调用必须有超时。
5. 批处理必须有可配置上限。
6. 并发写索引必须按 IngestionJob/DocumentVersion 保证幂等。
7. 取消使用明确 CancellationToken 或任务状态，不能只依赖协程取消异常。
8. Worker 关闭时停止领取新任务并安全处理或退回当前任务。
9. Worker 必须在业务状态和任务结果持久化后按协议 ACK；异常后无条件 ACK 被禁止。
10. 队列消息只携带版本化任务 envelope 和稳定 ID；Worker 通过 `tenant_id + job_id` 重新加载状态。

## 6. 配置与密钥

配置分为：

- 应用配置。
- 数据库配置。
- 对象存储配置。
- 搜索配置。
- Redis/任务配置。
- 模型 Provider 配置。
- Parser/OCR 资源配置。
- Agent 限制。
- 评测配置。

规则：

1. 配置 Schema 必须验证。
2. `.env.example` 只包含占位符。
3. 密钥不得进入源码、文档、日志、Trace、AgentState、测试 fixture 或 Git 历史。
4. 环境变量只在 bootstrap 读取，业务模块使用注入后的配置对象。
5. 配置变化影响结果时，RetrievalTrace/IngestionTrace 记录配置版本或摘要。

## 7. API 标准

1. API Schema 与领域 DTO 分开。
2. 路由只做验证、认证上下文、应用服务调用和响应映射。
3. 错误响应包含稳定 `error_code` 和 `trace_id`。
4. 不向客户端返回原始数据库、Redis、搜索或模型异常。
5. 文件上传验证 MIME、扩展名、大小和内容策略。
6. 流式响应定义开始、Token、Tool、Citation、错误和结束事件。
7. 幂等写操作接受或生成 idempotency key。
8. 分页参数和 TopK/TopN 有服务端上限。
9. OpenAPI 必须与实现同步。
10. `AuthorizationContext` 从可信认证信息构造；请求中的 `tenant_id` 只能作为业务目标候选，不能覆盖认证 tenant。
11. ingestion API 返回持久化 Job 标识和状态，不等待 Parser/OCR/Embedding 完成。

## 8. 领域数据与数据库

1. 数据库变化只通过 Alembic。
2. 迁移必须有升级和安全回滚/补偿说明。
3. ID 在应用层生成或使用明确数据库策略，不混用无约定方案。
4. 时间统一保存 UTC，API 显式转换。
5. JSON 字段必须有版本化 Schema，不能成为逃避建模的默认选择。
6. Document 与 DocumentVersion 分离。
7. IngestionJob 保留阶段、状态、attempt、错误和 Trace。
8. 删除默认先取消可见性，再回收物理数据。
9. 关系库是业务状态事实源；搜索索引可重建。
10. 数据库事务不能假装覆盖对象存储和搜索引擎，必须使用补偿或候选版本。
11. 所有 tenant-owned 聚合与跨进程 Job 必须显式存储 `tenant_id`；不得只通过父表联查或 ID 命名推断 tenant。
12. `KnowledgeBase` 和 `Document` 第一版至少存储 `owner_id` 与 `visibility`。

### 8.1 第一版多租户与权限标准

1. 第一层授权永远是 `resource.tenant_id == AuthorizationContext.tenant_id`；跨租户默认拒绝。
2. 应用层只能通过要求 `AuthorizationContext` 或显式 tenant 的 Repository 方法访问 tenant-owned 数据。
3. 禁止向应用层暴露无 tenant 条件的 `get_by_id`、`list_all`、`delete_by_id` 和批量更新方法。
4. `PermissionChecker` 集中处理 tenant、owner 和 visibility；路由、Service、Tool 和 Worker 不各自实现一套权限 if/else。
5. Search Adapter 必须把 tenant 条件作为不可删除的 AND 过滤；metadata filter 和用户请求只能进一步收窄范围。
6. IndexRecord 必须包含可过滤的 `tenant_id`；是否使用共享索引或每租户索引不能替代字段级校验。
7. 对象存储 key、Redis key、锁、队列消息、Checkpoint、Trace 和审计事件必须 tenant-scoped。
8. KnowledgeBaseTool 和子 Agent 继承调用者 `AuthorizationContext`，不得接受模型生成的新 tenant。
9. CitationBuilder 在生成前再次验证候选 tenant/visibility，不返回无权元数据。
10. 第一版不要求复杂 RBAC、部门权限和动态数据规则，但接口和 Schema 变化不得阻断这些能力后续接入。

### 8.2 Phase 03 已冻结契约

1. 知识 `AuthorizationContext` v1 字段为 `tenant_id + actor_id + request_id`；Phase 02 Agent 快照的 `user_id` 只能由 Adapter 显式映射为 `actor_id`。
2. visibility v1 只能是 `private|tenant`；同 tenant 非 owner 对 tenant-visible 资源只拥有 READ。
3. Repository `get` 必须要求 `tenant_id + resource_id`，`add` 必须要求 `tenant_id + entity` 并拒绝 scope 不一致；当前内存契约测试是所有未来 Adapter 的最低门禁。
4. DocumentVersion、ParsedDocument、ChunkRecord、Ingestion、Retrieval 和 Index DTO 的破坏性变化必须升级 schema/算法标识并更新 ADR-018。
5. 固定 RAG 与 KnowledgeBaseTool 必须调用 `KnowledgeQueryService.retrieve`，不得直接调用 `RetrieverPort` 或 Search 客户端。

## 9. 对象存储

1. Object key 使用稳定 ID，并以 `tenants/{tenant_id}/` 开头。
2. 保存内容哈希、长度和 MIME。
3. 上传后验证写入结果。
4. 下载必须有大小和超时限制。
5. Parser 临时文件使用受控目录并保证清理。
6. 删除必须幂等。
7. 原始文件和派生工件采用不同前缀和生命周期策略。

## 10. Parser 与 Chunk 标准

对应 `CAP-01` 至 `CAP-07`。

### 10.1 Parser

1. 输入是 ParseRequest，输出是 ParsedDocument。
2. 保留页码、bbox、source_order、heading_path、表格和图片关系。
3. 每个 warning 和降级可观察。
4. Parser 不写数据库或搜索引擎。
5. OCR 和 Vision 模型由端口注入。
6. 文件类型不支持时返回稳定错误，不返回空成功。

### 10.2 Chunk

1. Chunker 输入统一 ParsedDocument。
2. Chunk ID 稳定算法必须版本化；General 的兼容算法为 `sha256-v1`，
   Phase 05 场景策略算法为包含 strategy id/version 的 `sha256-v2`。
3. 记录 source_block_ids。
4. Token 上限、重叠、父子关系和表图上下文必须配置化。
5. 自动关键词、自动问题、摘要、标题和 TOC 是独立增强步骤。
6. 增强失败默认不破坏基础 Chunk；例外必须由策略明确。
7. 每个 Chunk Method 有黄金样本和回归测试。
8. Parser 必须同时校验 MIME 与扩展名；显式 override 不兼容时失败关闭。
9. OOXML 条目/解压大小/压缩比、PDF 页数、图片像素和 XLSX
   sheet/row/cell 上限由配置控制，禁止静默绕过。
10. 本地无 Tesseract 可显式跳过真实 OCR 集成测试，但 CI 必须安装声明的
    language packs 并设置 required 开关；Static/Fake OCR 只验证集成契约。

## 11. Embedding 与索引标准

对应 `CAP-08`。

1. 每个向量记录模型、Provider、版本和维度。
2. 写入前校验维度。
3. Embedding 批处理有 Token/条数上限。
4. 文本规范化规则版本化。
5. 新 Embedding 模型写入新 index_version。
6. 索引写入使用稳定 document_version_id 和 chunk_id。
7. 候选索引完整性验证后才能激活。
8. 批量写入错误必须能定位失败记录。

## 12. 检索标准

对应 `CAP-09` 至 `CAP-22`。

1. RetrievalQuery 是唯一查询入口。
2. 查询改写、跨语言和关键词扩展必须记录变体类型、数量和 Provider；持久 Trace 只保存不可逆查询摘要，不保存完整原始/变体文本。
3. Metadata Filter 先解析为受控 AST。
4. 权限约束在检索前注入。
5. 全文、向量、Rerank 和最终分数分别保存。
6. 不同后端原始分数不得直接相加；当前唯一默认融合是按排名执行 RRF `k=60`，同时保留各通道原始分数和排名。
7. 候选清理记录淘汰原因。
8. TopK 是候选池，TopN 是最终结果，不混用。
9. 空结果与后端错误使用不同 `empty_reason/error_code`。
10. RetrievalTrace 足以审计每个阶段，但不得成为查询、正文、Prompt、密钥或 Authorization 的敏感副本；默认 30 天 TTL、tenant 隔离、角色读取和可执行清理。
11. SearchPort Adapter 必须运行相同契约测试。
12. 当前 Retrieval schema v2 强制 query、trace、candidate、citation 的 tenant 和知识库范围一致；`authorization_applied` 必须为真。
13. 有限空结果降级只能扩大候选、降低有下限的软阈值、移除系统推断软过滤或切换单通道；tenant、ACL、KB/index、文档状态和用户过滤永不放宽。
14. Reranker 必须通过内部 Port；超时、不可用、异常或候选身份变化时回退 RRF，并在 Trace 中记录，不能让检索整体失败。
15. Trace 写入失败不得阻断成功检索，但必须产生内容最小化日志和可观察失败计数。

### 12.1 时序 RAG 附加标准

对应 `CAP-43 时序 RAG`，仅在 Phase 09 能力开关开启时适用。

1. 时间戳必须显式携带时区或规范化时区，禁止以无时区字符串作为领域事实。
2. 时序记录至少携带 `tenant_id`、数据源、序列/实体标识、单位、质量标记和数据版本。
3. 时间窗口、采样、插值、降采样和聚合方法必须进入请求协议与 Retrieval Trace。
4. Citation 必须能够定位原始时间范围、查询条件、聚合规则和数据版本。
5. 普通知识索引不能依赖时序后端；关闭时序能力后，Phase 04/06 的普通 RAG 契约和索引仍可独立运行。
6. 不得把 RAGFlow timeline knowledge compilation、普通元数据时间过滤或日志文本向量检索描述成完整时序 RAG。
7. 时序存储后端、保留策略和第一批数据协议未经 ADR 确认前，只能标记为待验证。

## 13. Citation 标准

对应 `CAP-21 引用与来源定位`。

每个 Citation 至少包含：

- knowledge_base_id
- document_id
- document_version_id
- chunk_id
- page
- bbox
- quote
- source_uri

规则：

1. 引用必须来自最终允许证据。
2. quote 必须能在目标 Chunk 或规范化文本中验证。
3. 已删除或无权限文档不返回 Citation。
4. 模型生成的引用标记必须经过服务端验证。
5. 不用数组位置作为长期 Citation 身份。

## 14. Agent 与 LangGraph 标准

对应 `CAP-28` 至 `CAP-32`。

1. AgentState 字段稳定、可序列化、可版本化。
2. 每个节点只有清晰输入、输出和副作用。
3. 副作用节点必须可幂等恢复。
4. Checkpoint 物理 key 至少包含 state version、tenant 和 thread；持久状态内同时验证 run，恢复令牌不得改变 tenant/thread/run。
5. 技术递归、重试、业务循环、模型/检索/Tool 次数、Token、主动运行时间和费用预算必须由服务端限制且不可由模型提高；HITL 恢复沿用原剩余预算。
6. HITL interrupt 保存审批原因、待执行动作和上下文摘要。
7. 恢复时验证状态版本和权限。
8. Tool 返回结构化结果和稳定错误。
9. 多 Agent 默认关闭；启用前必须证明相对单 Agent 的可量化收益，并定义 supervisor、终止条件、权限传播、共享状态和预算边界。
10. Agent 不得绕过 KnowledgeQueryService。
11. 官方 PostgreSQL Checkpointer 内部表由其 `setup()` 管理，项目 Alembic 不手工接管；业务 AgentThread/AgentRun 表必须与内部表分离。
12. 内存 Saver 只用于快速测试，不得作为进程重启或持久恢复的验收证据。
13. Agent Trace sink 失败必须显式标记降级，事件 payload 不得保存密钥、认证头、原始文档全文或 Tool 凭据。
14. Tool 必须显式注册名称/版本、输入输出 Schema、副作用、风险、租户/角色/业务范围、超时/重试/返回量、幂等、HITL 和脱敏规则；未知 Tool 默认拒绝。
15. Tool 每次执行和 HITL 恢复后都必须重新执行服务端鉴权、风险、审批和预算检查；模型不能修改这些策略。
16. SQL Tool 必须使用 AST 或等效可靠解析，只允许单条只读语句、参数化输入、对象 allowlist 和服务端 tenant 条件；API Tool 只能访问已登记 base URL/path/method 且禁止重定向和动态凭据。
17. 证据充分性由服务端 Policy 最终裁决；LLM 不能把空结果、依赖故障、部分证据或冲突证据改写为确定性结论。
18. 重要事实必须能映射到 Citation；多轮检索不得放宽 tenant、ACL、知识库范围、活动版本和文档状态硬条件。
19. Checkpoint、Retrieval/Agent Trace 和长期记忆必须分离；长期记忆默认关闭，写入要求显式同意、tenant+user 双重隔离、最小内容、TTL、查看/撤回/删除和真实清理任务。
20. Tool/SQL/API/Memory 内容均是不可信数据；提示注入不得改变系统 Prompt、Tool Policy、权限、审批或预算。
21. 批准必须与 tenant、用户、Tool 名称/版本、参数摘要和 TTL 绑定；CAS 与幂等键防止重复副作用，批准不等于已经执行。
22. Fake/Stub Agent 评测与真实模型、真实 SQL/API 集成必须分开报告；未运行真实 Provider 时不得报告真实效果。

## 15. 后台任务标准

对应 `CAP-23` 至 `CAP-26`、`CAP-38`。

任务消息至少包含：

- job_id
- tenant_id
- job_type
- aggregate_id
- requested_stage
- attempt
- idempotency_key
- trace_id
- created_at

规则：

1. 数据库先记录业务任务，再投递。
2. 消费前检查任务当前状态。
3. ACK 只在安全持久化后发生。
4. retry 区分瞬时、永久和取消错误。
5. 取消不等于删除任务记录。
6. 进度必须单调或明确说明阶段切换。
7. 死信/最终失败必须可查询。
8. Worker 心跳和积压指标必须存在。
9. Worker 必须比较消息 tenant 与数据库 Job tenant；不一致时拒绝、审计且不执行。
10. API 和 Worker 对任务 envelope 使用同一版本化 Schema 和契约测试。

Phase 07 补充强制规则：

11. PostgreSQL 是文档、版本和生命周期操作的权威状态；消息或搜索结果不得反向覆盖该状态。
12. 数据库业务状态与待投递事件必须在同一事务写入 Outbox；跨 PostgreSQL、对象存储和搜索引擎禁止伪装成原子事务。
13. 新版本只在候选索引验证通过、alias 切换成功且文档 revision CAS 成功后成为 current；陈旧 fencing token 必须拒绝。
14. 删除先撤销可见性并留下墓碑，再按保留期幂等回收；查询返回前必须再次验证权威文档/版本状态。
15. retry 默认只接受显式 transient/concurrency 错误；未知代码错误不得自动无限重试，最终失败必须进入可查询 dead-letter 状态。
16. reconciliation 默认 tenant-scoped、有限批量且 dry-run；只有可证明安全的孤儿允许自动修复。
17. 项目业务表由 Alembic 管理；LangGraph Checkpoint 内部表仍只由官方 `AsyncPostgresSaver.setup()` 管理，两者不得混用迁移所有权。

## 16. 日志、指标与 Trace

每条结构化日志至少包含可用字段：

- timestamp
- level
- service/component
- trace_id
- tenant_id（仅作为内部隔离/审计标识，不输出敏感租户信息）
- request_id 或 job_id 或 run_id
- operation
- duration_ms
- outcome
- error_code

禁止记录：

- API key
- 数据库密码
- 完整授权头
- 无必要的原始文档全文
- 无必要的用户隐私数据

关键指标：

- API 请求数、错误率、延迟。
- 队列积压、任务阶段、重试、取消和失败。
- Parser 页数、耗时和错误。
- Embedding 条数、Token、延迟和费用。
- 搜索、Rerank、生成的延迟和错误。
- Agent 节点、循环、Tool、恢复和 HITL。

## 17. 测试标准

### 17.1 测试层次

| 层次 | 目标 |
|---|---|
| Unit | 纯规则、状态机、分数、过滤、DTO |
| Contract | Port 的所有 Adapter 行为一致 |
| Integration | PostgreSQL、Redis、对象存储、搜索、模型 stub |
| E2E | 上传到回答、Agent 到 Tool |
| Evaluation | 检索、答案、引用、Agent 和性能指标 |

### 17.2 必测故障

- 重复任务。
- Worker 崩溃。
- Parser 超时。
- Embedding 部分失败。
- 搜索批量写入部分失败。
- 更新失败保留旧版本。
- 删除部分失败。
- 无权限检索。
- 跨租户 Repository、Search、ObjectStore、队列消息、Tool 和 Citation 访问。
- owner/visibility 组合和伪造 tenant/resource ID。
- Agent 循环上限。
- Checkpoint 恢复。
- HITL 重复提交。
- 模型超时和限流。

### 17.3 测试数据

1. fixture 必须说明来源和许可证。
2. 轨道交通样本脱敏。
3. 黄金输出版本化。
4. 评测集和开发集分离。
5. 不用生产敏感数据作为默认测试资源。

### 17.4 Phase 04 基础设施与 Provider 门禁

1. CI 必须显式启动临时 PostgreSQL、Redis、MinIO 和 Elasticsearch，设置 `RAGFLOW_AGENT_TEST_*` 后再运行完整 pytest；没有环境变量时，相关测试必须明确 skip，不能把 skip 报告成真实集成通过。
2. DeepSeek 和 BGE-M3 在 CI 中使用实现相同内部 Port 的 Fake/Stub；不得要求 API Key、GPU 或外部模型服务，也不得把 Fake 结果描述成真实供应商验证。
3. Elasticsearch Client/Server 固定 8.19 兼容线，mapping dimensions、BM25、KNN、RRF、active version 和 tenant filter 必须有真实后端测试。
4. ARQ 固定 0.28，redis-py 固定 `>=5.2,<6`；ARQ/Redis 类型不得进入领域或应用层，升级必须重跑唯一 job ID 和 retry/terminal failure 测试。
5. S3 测试必须覆盖 SHA-256/size、tenant namespace、流式读写、跨 tenant 拒绝和显式对象清理。
6. 跨后端 E2E 必须清楚记录真实组件与 Fake 组件，禁止用单一内存 Adapter 测试冒充真实闭环。

## 18. RAGFlow 复用标准

1. 严格执行[代码复用策略](./04-code-reuse-strategy.md)。
2. 每个复用文件记录上游完整 commit、路径、符号、许可证和修改。
3. 不导入 RAGFlow `common.settings`、Peewee Model、Quart Request 或 Canvas。
4. 上游行为先有测试，再改造。
5. 第三方模型和资源单独审计。
6. 直接复用必须获得明确批准；当前无批准项。

## 19. Definition of Done

一项能力只有同时满足下列条件才完成：

1. 能力矩阵条目和阶段一致。
2. 代码符合导入边界。
3. 数据库迁移存在并验证；无迁移需求时明确说明。
4. 单元、契约、集成或 E2E 测试按风险完成。
5. 错误、超时、取消和重试行为已测试。
6. 日志、指标和 Trace 足以诊断。
7. 安全和敏感信息检查通过。
8. 文档、ADR、源码 provenance 已更新。
9. 无计划项被误标为已实现。
10. 用户要求的验收方法通过。

## 20. Codex 交付规则

1. 修改前读取总纲、决策文档和对应专项文档。
2. 先检查工作树，不覆盖用户修改。
3. 只修改任务范围内文件。
4. 优先小步、可验证变更。
5. 验证命令与结果必须在交付说明中列出。
6. 未运行的测试必须明确说明原因。
7. 发现文档与代码冲突时先报告并修正文档状态。
8. 未经用户决定，不替待确认项做选择。
