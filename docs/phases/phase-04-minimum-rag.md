---
document_id: PHASE-04-MINIMUM-RAG
document_role: Phase 04 详细计划与执行记录
status: completed
phase: Phase 04
phase_name: 最小RAG闭环
plan_status: 已确认
execution_status: 已完成
last_updated_at: "2026-07-30"
ragflow_frozen_baseline_commit: "cd846cc9d4e32a19e684c59a1f302601027ef976"
---

# Phase 04：最小RAG闭环详细计划

## 0. 状态与导航

- **计划状态**：已确认。
- **执行状态**：已完成；P04-T01 至 P04-T12 均通过验证。
- Phase 03 基线、用户冻结的 O-002/O-004/O-006/O-007 决策和实际代码均已复核。
- 导航：[阶段索引](./README.md) · [Phase 03](./phase-03-knowledge-interface.md) · [Phase 05](./phase-05-parser-and-chunk.md) · [Phase 06](./phase-06-online-retrieval.md)

## 1. 阶段目标与必要性

完成首个真实垂直切片：tenant-scoped 文档上传→对象存储→持久 IngestionJob→Redis/ARQ→独立 Worker→基础解析→基础 Chunk→Embedding→Elasticsearch 索引→全文/向量/RRF 混合检索→Prompt→LLM 回答→Citation/来源，并建立最小 E2E 和检索基线。该阶段交付了真实闭环，不是只有抽象。

## 2. Phase 00 事实依据

RAGFlow 离线主链路为：

`document_api.upload_document` → `FileService.upload_document` → ObjectStorage/File/Document/File2Document → `DocumentService.run` → `TaskService.queue_tasks` → Redis Stream → `task_executor.collect/handle_task` → `TaskHandler._run_standard_chunking_impl` → `ChunkService.build_chunks` → `EmbeddingService.embed_chunks` → `ChunkService.insert_chunks` → DocStore。

固定问答链路为：

`chat_api.session_completion` → `dialog_service.rag_agent(reasoning off)` → `async_chat` → `Dealer.retrieval` → `kb_prompt` → `LLMBundle` → Citation。

上游提供能力与顺序证据，但其 Peewee、settings、Redis ACK 和 DocStore 耦合不直接采用。

## 3. 前置、进入条件和输入

- **前置阶段**：Phase 03。
- **进入条件（实际）**：Phase 03 DoD、Git/CI 基线和用户授权均已满足；O-002/O-006/O-007 已由 ADR-019 解决，O-004 以“Phase 04 不复制、抽取或改写 RAGFlow 源码”解决。
- **输入**：Phase 03 统一领域/Ports、API/Worker 骨架、PostgreSQL/Redis/MinIO 开发拓扑、固定 RAGFlow commit 源码依据和最小测试文档。

## 4. 范围、排除与交付物

**范围**：上传、哈希/MIME、安全校验、TXT/Markdown/PDF Parser、General Chunk、Embedding、Elasticsearch 全文/向量索引、BM25/KNN/RRF 混合检索、Prompt、LLM、Citation、任务状态/进度、tenant 隔离、E2E/评测基线。

**排除**：完整 OCR/版面和全格式、场景 Chunk 完整集、Reranker/跨语言/查询改写/复杂空结果降级、生命周期原子发布、Agent Tool、GraphRAG/RAPTOR/多模态/时序 RAG、多搜索引擎。

**交付物**：真实 Adapter、API、Worker pipeline、FixedRAGService/KnowledgeQueryService 最小实现、迁移、E2E 数据和报告。

## 5. 目标模块和文件

```text
src/ragflow_agent/knowledge/application/{upload,ingestion,fixed_rag}.py
src/ragflow_agent/knowledge/infrastructure/{database,object_store,queue,parsers,chunking,search,models,trace}/
src/ragflow_agent/api/routes/knowledge.py
src/ragflow_agent/worker/arq_worker.py
tests/{contract,integration,e2e,evaluation}/
```

## 6. RAGFlow 源码范围与采用

| 源码/调用 | 采用 |
|---|---|
| `document_api.py::upload_document/parse_documents` → `FileService.upload_document` → `DocumentService.run` | 上传/投递顺序参考，自研 |
| `TaskService.queue_tasks` → `RedisDB.queue_product` → `task_executor.collect/handle_task` | 消息边界参考；可靠语义自研 |
| `chunk_builder.py::get_parser/run_chunking` → `rag/app/naive.py::chunk` | 只参考职责和行为目标；Phase 04 General Chunk 独立实现 |
| `EmbeddingService.embed_chunks` → `ChunkService.insert_chunks` | 批处理/字段顺序参考，自研 |
| `Dealer.get_vector/search` | 向量检索用例参考，自研 SearchPort Adapter |
| `dialog_service.async_chat` → `kb_prompt` → `LLMBundle` | 固定回答顺序参考，自研 |
| `Dealer.insert_citations` | 引用算法思想可改造实验；目标 Citation 绑定 version |

- **直接复用**：无。
- **`ragflow_adapters` 改造复用**：无；Phase 04 未复制、抽取或改写任何 RAGFlow 源码。
- **参考后自研**：上传、任务、Embedding、索引、检索、Prompt、回答和 Citation 主链路。
- **明确不采用**：Peewee Service、Quart、全局 settings、异常后无条件 ACK。

## 7. 框架与自研职责

- **LangChain**：Embedding 与 ChatModel 的 OpenAI-compatible 标准适配；Prompt 由应用层版本化。
- **LangGraph**：不参与固定 RAG；不得用 Agent 图包装最小问答。
- **自研**：领域状态、API、Worker、队列协议、Parser/Chunk pipeline、Search Adapter、固定问答、Citation、权限、Trace。

## 8. 任务总表

| 任务 | 名称 | 状态 | 前置 |
|---|---|---|---|
| P04-T01 | 冻结最小技术选型与垂直切片 | 已完成 | Phase 03 |
| P04-T02 | 实现知识库/文档持久化与对象存储 | 已完成 | P04-T01 |
| P04-T03 | 实现上传 API 与 IngestionJob 投递 | 已完成 | P04-T02 |
| P04-T04 | 实现 Worker 与最小 ingestion pipeline | 已完成 | P04-T01、P04-T03 |
| P04-T05 | 实现基础 Parser | 已完成 | P04-T04 |
| P04-T06 | 实现 General Chunk | 已完成 | P04-T05 |
| P04-T07 | 实现 Embedding Adapter | 已完成 | P04-T01、P04-T06 |
| P04-T08 | 实现索引写入和最小检索 | 已完成 | P04-T01、P04-T07 |
| P04-T09 | 实现 Prompt 与 LLM 回答 | 已完成 | P04-T08 |
| P04-T10 | 实现 Citation、来源和最小 Trace | 已完成 | P04-T09 |
| P04-T11 | 建立最小 E2E 与评测基线 | 已完成 | P04-T02 至 P04-T10 |
| P04-T12 | 执行 Phase 04 出口审查 | 已完成 | P04-T01 至 P04-T11 |

## 9. 具体任务

### P04-T01：冻结最小技术选型与垂直切片

- **状态**：已完成
- **目标**：解决 O-002/O-006/O-007，必要时 O-004，固定一个最小格式/模型/后端组合。
- **为什么需要**：真实闭环不能靠未绑定端口验收。
- **输入**：Phase 03 端口、待决策登记、部署资源。
- **前置任务**：Phase 03 完成。
- **操作步骤**：比较搜索/队列/模型；验证 Python 3.13/许可；确定测试文档和指标；记录 ADR；复审端口。
- **涉及文件**：`docs/07-decisions-and-risks.md`、本文件、配置。
- **预期输出**：可执行最小 Profile。
- **RAGFlow 源码依据**：DocStore/Redis/LLMBundle 能力面只作比较。
- **实现或复用方式**：自研选择；不复制。
- **测试方法**：供应商冒烟、维度、BM25/KNN、ACK 能力验证。
- **验证命令**：`uv lock`；`uv sync --frozen --all-groups`；`uv pip check`；真实 Redis/Elasticsearch Adapter 测试。
- **验收标准**：O-002/O-006/O-007 Resolved；回退方案明确。
- **风险和回滚方法**：Adapter 可替换；选型失败不改领域协议。
- **实际执行结果**：ADR-019 冻结 PostgreSQL + S3/MinIO + Redis/ARQ 0.28 + Elasticsearch 8.19 + DeepSeek OpenAI-compatible + BGE-M3 1024 维；O-002/O-006/O-007 Resolved，O-004 以不抽取源码闭环；依赖和配置已进入 `pyproject.toml`、`uv.lock`、`settings.py`、`.env.example`。
- **实际验证结果**：锁文件解析、冻结同步和 `uv pip check` 通过；ARQ 0.28 与 Redis 5.3.1、Elasticsearch Client 8.19.3 在 Python 3.13 下通过真实后端测试。
- **计划偏差**：ARQ 0.28 要求 `redis<6`，初始依赖探测发现冲突后将 Redis 锁定为 `>=5.2,<6`；ARQ maintenance-only 风险登记为 R-028。

### P04-T02：实现知识库/文档持久化与对象存储

- **状态**：已完成
- **目标**：实现 tenant-scoped KB/Document/Version/Job Repository 和原始文件存储。
- **为什么需要**：上传和引用必须有业务事实源。
- **输入**：P04-T01、Phase 03 契约。
- **前置任务**：P04-T01。
- **操作步骤**：创建迁移；实现 SQLAlchemy Repository/UoW；实现 S3 Adapter；定义 object key/hash/MIME；运行契约测试。
- **涉及文件**：数据库/对象 Adapter、迁移、测试。
- **预期输出**：持久化和对象存储能力。
- **RAGFlow 源码依据**：`FileService.upload_document` 的对象/记录顺序参考。
- **实现或复用方式**：参考后自研。
- **测试方法**：CRUD、事务、tenant、重复哈希、对象失败。
- **验证命令**：`uv run alembic upgrade head`; `uv run pytest tests/contract/knowledge tests/integration/object_store -q`
- **验收标准**：跨租户拒绝；对象和记录失败可诊断。
- **风险和回滚方法**：迁移可降级；对象删除幂等。
- **实际执行结果**：新增 `20260730_0002` 迁移、五类 tenant 复合主键表、SQLAlchemy Repository/UoW 和 `S3ObjectStorage`；对象键强制 tenant namespace，写入校验 size/SHA-256。
- **实际验证结果**：真实 PostgreSQL Repository tenant 隔离、真实 MinIO 流式写读删与跨 tenant 拒绝通过；Alembic upgrade/downgrade/upgrade 通过。
- **计划偏差**：Phase 04 不实现 Document 生命周期删除与残留扫描；跨系统补偿保留到 Phase 07。

### P04-T03：实现上传 API 与 IngestionJob 投递

- **状态**：已完成
- **目标**：安全上传、持久化 Job 后投递版本化消息。
- **为什么需要**：API 不执行长耗时 ingestion。
- **输入**：P04-T02、TaskQueuePort。
- **前置任务**：P04-T02。
- **操作步骤**：实现路由/Schema；校验大小/MIME/扩展；构造 AuthorizationContext；事务记录；commit 后投递；返回 job_id。
- **涉及文件**：API route、upload service、queue Adapter、测试。
- **预期输出**：上传与任务查询 API。
- **RAGFlow 源码依据**：`upload_document` → `FileService.upload_document` → `DocumentService.run`。
- **实现或复用方式**：参考重写。
- **测试方法**：正常/恶意文件、幂等、队列失败、tenant。
- **验证命令**：`uv run pytest tests/integration/api/test_document_upload.py -q`
- **验收标准**：API 不等待解析；消息与数据库 tenant/job 一致。
- **风险和回滚方法**：投递失败保留可重投状态；不删除已存原件。
- **实际执行结果**：新增 KnowledgeBase 创建、multipart 文档上传、IngestionJob 查询和固定 RAG 查询路由；`UploadService` 在业务事实 commit 后发布版本化 JSON envelope，tenant + idempotency key 生成确定性 job ID，PENDING 重投可恢复提交后队列失败。
- **实际验证结果**：`tests/integration/api/test_document_upload.py` 验证 202、非阻塞、重复请求、tenant 身份和 envelope 一致性。
- **计划偏差**：Phase 04 校验 MIME、大小和安全文件名，不做深度文件内容嗅探或恶意宏扫描；后者属于 Phase 05/10。

### P04-T04：实现 Worker 与最小 ingestion pipeline

- **状态**：已完成
- **目标**：消费任务并按 parse→chunk→embed→index 更新进度。
- **为什么需要**：形成独立 Worker 数据面。
- **输入**：P04-T01、P04-T03。
- **前置任务**：P04-T01、P04-T03。
- **操作步骤**：校验 tenant/job；锁定任务；执行阶段；持久化进度/错误；安全 ACK；处理关闭。
- **涉及文件**：`worker/ingestion_pipeline.py`、queue Adapter、测试。
- **预期输出**：最小 pipeline 编排。
- **RAGFlow 源码依据**：`task_executor.collect/handle_task` → `TaskHandler`。
- **实现或复用方式**：参考后自研；禁止无条件 ACK。
- **测试方法**：重复消息、崩溃点、tenant mismatch、取消。
- **验证命令**：`uv run pytest tests/integration/worker/test_minimum_pipeline.py -q`
- **验收标准**：阶段可观察；ACK 时机正确；错误不伪成功。
- **风险和回滚方法**：失败保留 Job/attempt；手动重投可审计。
- **实际执行结果**：新增 Redis/ARQ JSON Queue Adapter、真实 Worker bootstrap 和 parse→chunk→embed→index pipeline；Job/Task 持久化阶段进度、attempt、retryable/permanent error，ARQ 只在应用处理成功后完成任务。
- **实际验证结果**：真实 Redis 发布与 job ID 去重通过；Worker pipeline 的第一次可重试失败、第二次终止失败、Job/Task/DocumentVersion 状态通过；Fake 和真实后端 E2E 的成功状态通过。
- **计划偏差**：复杂租约、死信、取消、批量调度和 stale-job reconciliation 仍按路线图留在 Phase 07；本阶段只实现最小可靠链路。

### P04-T05：实现基础 Parser

- **状态**：已完成
- **目标**：至少支持 TXT、Markdown 和一个复杂格式的真实 ParseRequest→ParsedDocument。
- **为什么需要**：验证统一文档结构可落地。
- **输入**：P04-T04、ParserPort、样本。
- **前置任务**：P04-T04。
- **操作步骤**：实现简单 Parser；选择复杂格式最低路径；限制大小/超时；保留来源；输出 warning。
- **涉及文件**：`infrastructure/parsers/`、fixtures、测试。
- **预期输出**：基础 Parser Adapter。
- **RAGFlow 源码依据**：`rag/app/naive.py::chunk`、`chunk_builder.get_parser`；复杂 Parser 只作参考。
- **实现或复用方式**：TXT、Markdown、PDF 全部独立实现；未复制或改写 RAGFlow。
- **测试方法**：黄金文本、编码、空/损坏文件、资源限制。
- **验证命令**：`uv run pytest tests/contract/parsers -q`
- **验收标准**：不支持格式返回稳定错误；来源字段完整。
- **风险和回滚方法**：复杂格式失败不阻塞 TXT/MD 闭环，但不得声称多格式完成。
- **实际执行结果**：`BasicObjectParser` 支持 UTF-8 TXT、Markdown heading path 和 pypdf PDF 页级文本；具备字节上限、PDF 超时、损坏/加密/无文本/编码错误稳定错误码和版本范围校验。
- **实际验证结果**：TXT/Markdown 顺序与 heading、真实生成 PDF 页码/文本、非法编码和不支持格式测试通过。
- **计划偏差**：没有 warning 集合；不可提取内容直接产生稳定失败。OCR、版面、表格和复杂 PDF 留 Phase 05。

### P04-T06：实现 General Chunk

- **状态**：已完成
- **目标**：产生稳定、受 Token 上限控制并可引用的基础 Chunk。
- **为什么需要**：Embedding/索引/引用共同依赖。
- **输入**：P04-T05、ChunkerPort。
- **前置任务**：P04-T05。
- **操作步骤**：文本规范化；Token 分割/重叠；稳定 ID v1；source_block_ids；配置版本；黄金测试。
- **涉及文件**：chunking Adapter、测试。
- **预期输出**：General Chunker。
- **RAGFlow 源码依据**：`rag/app/naive.py::chunk` 和 `chunk_builder.run_chunking`。
- **实现或复用方式**：优先参考重写；获批后才可经 `ragflow_adapters` 改造。
- **测试方法**：边界、Unicode、表格占位、稳定 ID。
- **验证命令**：`uv run pytest tests/unit/chunking/test_general.py -q`
- **验收标准**：相同输入/配置产生相同 ID；Token 不超限。
- **风险和回滚方法**：算法变更升级 chunker_version/index_version。
- **实际执行结果**：`GeneralChunker` 按统一 ParsedBlock 顺序生成稳定 SHA-256 v1 ID、重叠窗口、source_block_ids、heading/page 元数据和近似 token_count。
- **实际验证结果**：相同输入稳定 ID、窗口重叠、Unicode、页码/标题来源和最大窗口测试通过。
- **计划偏差**：Phase 04 使用确定性 Unicode token 近似器，不宣称等同 BGE/LLM tokenizer；模型专用 tokenizer 与场景策略在 Phase 05 复审。

### P04-T07：实现 Embedding Adapter

- **状态**：已完成
- **目标**：批量生成带模型/维度/版本元数据的向量。
- **为什么需要**：向量索引和重建需要可追溯模型。
- **输入**：P04-T01、P04-T06。
- **前置任务**：P04-T01、P04-T06。
- **操作步骤**：LangChain Embeddings Adapter；Token/条数批次；维度校验；超时/限流/部分失败；usage。
- **涉及文件**：`infrastructure/embedding/`、测试。
- **预期输出**：EmbeddingPort 实现。
- **RAGFlow 源码依据**：`EmbeddingService.embed_chunks` 批处理关系。
- **实现或复用方式**：LangChain + 自研治理。
- **测试方法**：维度、批次、超时、空文本、确定性 stub。
- **验证命令**：`uv run pytest tests/contract/embedding -q`
- **验收标准**：错误定位到 chunk；模型元数据完整。
- **风险和回滚方法**：供应商失败回退 stub 仅测试，不伪生产。
- **实际执行结果**：`LangChainEmbeddingAdapter` 通过内部 `EmbeddingPort` 接入 OpenAI-compatible BGE-M3，校验 tenant、model、批量结果数量、每个 chunk 的维度并保留模型/维度/normalized 元数据；CI 使用 `KeywordEmbedding`。
- **实际验证结果**：确定性 LangChain Embeddings fake 的批量 identity、模型元数据、维度漂移及出错 input_id 验证通过。
- **计划偏差**：真实 BGE-M3 服务/GPU 按用户约束不作为 CI 前置；provider usage/限流治理不在本阶段实现。

### P04-T08：实现索引写入和最小检索

- **状态**：已完成
- **目标**：写入 IndexRecord 并提供 tenant-scoped 向量检索和基础全文检索。
- **为什么需要**：建立 SearchPort 真实 Adapter 和最小 Recall 基线。
- **输入**：P04-T01、P04-T07。
- **前置任务**：P04-T01、P04-T07。
- **操作步骤**：映射 schema；创建 index/version；bulk upsert；强制 tenant/KB/version filter；KNN/BM25 查询；契约测试。
- **涉及文件**：search Adapter、索引模板、测试。
- **预期输出**：最小搜索实现。
- **RAGFlow 源码依据**：`Dealer.search/get_vector`、`MatchDenseExpr`、`FulltextQueryer.question`。
- **实现或复用方式**：SearchPort 自研；全文分析候选后续再改造。
- **测试方法**：维度、tenant、过滤、批量部分失败、Recall@K。
- **验证命令**：`uv run pytest tests/integration/search -q`
- **验收标准**：跨租户零结果；记录可按版本重建。
- **风险和回滚方法**：后端 DSL 只在 Adapter；索引 alias 可回退。
- **实际执行结果**：Elasticsearch 8.19 Adapter 实现 strict mapping、维度兼容校验、bulk upsert、候选版本激活、BM25、KNN、tenant/KB/owner/visibility/metadata filter 和自研 RRF；DSL 仅存在于 infrastructure Adapter。
- **实际验证结果**：真实 Elasticsearch 的全文、向量、混合、Citation、Trace、active version 和跨 tenant 零结果测试通过。
- **计划偏差**：用户在准入时将全文/向量/混合都纳入 Phase 04，因此比原草案“混合留 Phase 06”多交付最小 RRF；复杂融合、阈值、Reranker 和空结果重试仍留 Phase 06。

### P04-T09：实现 Prompt 与 LLM 回答

- **状态**：已完成
- **目标**：用最终候选组装上下文并生成固定 RAG 回答。
- **为什么需要**：完成检索到答案的真实闭环。
- **输入**：P04-T08、ChatModel Adapter。
- **前置任务**：P04-T08。
- **操作步骤**：实现 KnowledgeQueryService 最小查询；ContextBuilder；Prompt 模板；流式/非流式调用；空候选明确响应。
- **涉及文件**：`application/{query,fixed_rag}.py`、prompts、API。
- **预期输出**：固定 RAG 服务。
- **RAGFlow 源码依据**：`async_chat` → `kb_prompt` → `LLMBundle`。
- **实现或复用方式**：LangChain + 参考后自研。
- **测试方法**：Prompt 快照、上下文预算、模型超时、空结果。
- **验证命令**：`uv run pytest tests/unit/rag tests/e2e/minimum_rag -q`
- **验收标准**：固定 RAG 不经过 Agent；无证据不伪造来源。
- **风险和回滚方法**：Prompt 版本化；模型失败返回稳定错误。
- **实际执行结果**：`FixedRagService` 直接调用 `KnowledgeQueryService`，使用 `fixed-rag-v1` 限界上下文与 DeepSeek Provider Port；无证据返回固定拒答且不调用模型，业务层不依赖供应商 SDK。
- **实际验证结果**：无证据、prompt 证据编号、上下文到回答和固定 RAG 不经过 Agent 的测试通过；真实后端 E2E 使用 Stub Chat，未调用外部 API。
- **计划偏差**：Phase 04 只实现非流式回答；流式协议和完整模型调用治理留后续在线检索/生产化阶段。

### P04-T10：实现 Citation、来源和最小 Trace

- **状态**：已完成
- **目标**：为答案绑定 DocumentVersion/Chunk/page/quote/source，并记录最小检索链路。
- **为什么需要**：可验证来源是项目核心要求。
- **输入**：P04-T09、Citation/Trace 协议。
- **前置任务**：P04-T09。
- **操作步骤**：Context 标号；解析/校验模型引用；权限二次检查；quote 验证；记录候选/分数/延迟/模型。
- **涉及文件**：CitationBuilder、Trace sink、API Schema、测试。
- **预期输出**：基础 Citation 和 RetrievalTrace。
- **RAGFlow 源码依据**：`citation_prompt`、`Dealer.insert_citations`、`repair_bad_citation_formats`。
- **实现或复用方式**：算法思想参考/必要时改造实验，数据模型自研。
- **测试方法**：错误编号、无权/删除候选、quote 不存在、版本。
- **验证命令**：`uv run pytest tests/unit/rag/test_citations.py -q`
- **验收标准**：所有 Citation 可解析到允许版本；Trace 可关联 request/job。
- **风险和回滚方法**：校验失败删除引用而非猜测修复。
- **实际执行结果**：Search Adapter 从实际 IndexRecord 构建绑定 tenant/KB/document/document_version/chunk/page/quote/source_uri 的 Citation，并产生 Authorization/FULL_TEXT/VECTOR/FUSION/SELECT RetrievalTrace；FixedRAG 只返回进入 prompt 的证据来源。
- **实际验证结果**：版本绑定 Citation、source URI、页码、授权 Trace、真实 Elasticsearch 候选和跨 tenant 负向测试通过。
- **计划偏差**：没有猜测或自动修复模型输出中的引用编号；Phase 04 返回服务端证据清单，引用格式修复与引用准确率评测留 Phase 06/10。

### P04-T11：建立最小 E2E 与评测基线

- **状态**：已完成
- **目标**：验证上传到带引用回答的真实链路并建立基线指标。
- **为什么需要**：防止只验证模块、没有垂直可用性。
- **输入**：P04-T02 至 P04-T10。
- **前置任务**：P04-T02 至 P04-T10。
- **操作步骤**：准备脱敏小数据集；启动依赖/API/Worker；上传/轮询/查询；测 Recall@K、引用存在性、延迟；跨租户负向。
- **涉及文件**：E2E/evaluation tests、fixtures、报告。
- **预期输出**：Minimum RAG 基线。
- **RAGFlow 源码依据**：上游 benchmark 只作 HTTP 性能参考。
- **实现或复用方式**：自行开发评测。
- **测试方法**：真实后端 E2E、重复执行和故障注入。
- **验证命令**：`uv run pytest tests/e2e/minimum_rag tests/evaluation/minimum_rag -q`
- **验收标准**：真实数据可检索回答；跨租户拒绝；指标版本化。
- **风险和回滚方法**：供应商测试可分 opt-in，但发布门禁需真实环境。
- **实际执行结果**：新增 `minimum-rag-baseline-v1` Recall@1 基线、全内存上传到回答 E2E，以及 PostgreSQL + MinIO + Redis/ARQ + Elasticsearch 真实后端跨系统 E2E；模型/Embedding 仍为确定性 Fake。
- **实际验证结果**：真实后端 E2E 通过上传、对象、数据库、队列发布、Worker pipeline、全文/向量/混合检索、回答、Citation/Trace；全量真实后端测试 153 passed、0 skipped。
- **计划偏差**：真实后端 E2E 在同一测试进程调用 pipeline，独立 Worker 的 ARQ 入口和失败语义由独立集成测试覆盖；不伪称验证了外部 BGE/DeepSeek 或多进程故障恢复。

### P04-T12：执行 Phase 04 出口审查

- **状态**：已完成
- **目标**：验收垂直切片、状态、权限、测试、文档和后续接口稳定性。
- **为什么需要**：Phase 05/06 必须在真实基线上扩展。
- **输入**：P04-T01 至 P04-T11。
- **前置任务**：P04-T01 至 P04-T11。
- **操作步骤**：全量测试；检查迁移/日志/Trace/许可证；更新矩阵/风险；形成出口报告。
- **涉及文件**：总体文档、本文件、评测报告。
- **预期输出**：Phase 04 验收结论。
- **RAGFlow 源码依据**：核对 provenance 和冻结链接。
- **实现或复用方式**：审计。
- **测试方法**：Unit/Contract/Integration/E2E/Evaluation/Security。
- **验证命令**：`uv run pytest`; `uv run ruff check .`; `uv run mypy src/ragflow_agent tests`
- **验收标准**：CAP-08/10/21/23/27/38 基础路径通过；CAP-01/04/09 仅按实际最小范围标记。
- **风险和回滚方法**：任何越权、引用或索引一致性失败阻止出口。
- **实际执行结果**：完成源码/许可证、依赖、迁移、tenant、临时文件、敏感信息、Fake/真实测试和文档一致性审查；Phase 04 未引入任何 RAGFlow 派生文件。
- **实际验证结果**：`ruff check .`、`mypy src tests scripts/check_secret_hygiene.py`、真实后端 `pytest`（153 passed）、默认环境 `pytest`（143 passed、10 skipped）、bootstrap checks、Compose config、Alembic downgrade/upgrade、secret hygiene 均通过。
- **计划偏差**：完整验收使用本地临时 Compose 基础设施；密钥卫生扫描器原先将运行时 `settings.*` 引用误判为凭据，已收紧为仅检查字面量并新增 3 个回归测试；最终 GitHub Actions 结果在推送后回填。

## 10. 测试、验收与 DoD

测试覆盖 Unit、Port Contract、PostgreSQL/Redis/ObjectStore/Search/Model Integration、上传到回答 E2E、Recall/Citation 基线和跨租户安全。

**DoD**：P04-T01 至 P04-T12 完成；真实后端闭环通过；迁移/回滚、任务状态、Citation/Trace、tenant 隔离和基线评测有证据；所有上游复用有 provenance；总体文档同步。

## 11. 风险、更新和下一阶段

| 风险 | 处理 |
|---|---|
| 只有端口没有闭环 | P04-T11 是硬门禁 |
| 供应商选择锁定领域 | 所有 DSL/SDK 留 Adapter |
| ACK/重复任务污染索引 | tenant+job 校验、幂等 ID、安全 ACK |
| 引用不可靠 | 服务端 quote/版本/权限校验 |
| 复杂 Parser 拖延 | 最小格式闭环，完整能力留 Phase 05 |

阶段结束更新总纲、架构、矩阵、复用策略、路线图、工程标准、决策风险、阶段索引和本文件。Phase 05/06 计划必须依据真实 Chunk/Index/Trace 字段重审；两者可准备但 Phase 06 完整验收依赖 Phase 05。

## 12. 实际执行结果

- **技术选型/文件/迁移**：ADR-019、`20260730_0002`、Phase 04 application/infrastructure/API/Worker 模块和四类真实后端测试已落地。
- **E2E/评测/安全**：Fake 与真实后端垂直切片、Recall@1 基线、tenant/owner/visibility、Citation/Trace、失败重试和 provider-free CI 已验证。
- **复用 provenance**：只参考 RAGFlow 冻结 commit `cd846cc9d4e32a19e684c59a1f302601027ef976` 的公开职责/行为；直接复用和改造复用均为零。
- **阶段出口结论**：Phase 04 DoD 已满足；Phase 05 可进入计划复审门禁，但尚未准入执行。
