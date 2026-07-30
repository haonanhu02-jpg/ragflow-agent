---
document_id: PHASE-04-MINIMUM-RAG
document_role: Phase 04 预规划详细计划
status: draft
phase: Phase 04
phase_name: 最小RAG闭环
plan_status: 预规划草案
execution_status: 未执行
last_updated_at: "2026-07-30"
ragflow_frozen_baseline_commit: "cd846cc9d4e32a19e684c59a1f302601027ef976"
---

# Phase 04：最小RAG闭环详细计划

## 0. 状态与导航

- **计划状态**：预规划草案。
- **执行状态**：未执行。
- Phase 03 完成后必须按真实领域/端口/迁移重新审查。
- 导航：[阶段索引](./README.md) · [Phase 03](./phase-03-knowledge-interface.md) · [Phase 05](./phase-05-parser-and-chunk.md) · [Phase 06](./phase-06-online-retrieval.md)

## 1. 阶段目标与必要性

完成首个真实垂直切片：tenant-scoped 文档上传→对象存储→持久 IngestionJob→独立 Worker→基础解析→基础 Chunk→Embedding→索引写入→向量检索→Prompt→LLM 回答→Citation/来源，并建立最小 E2E 和检索基线。该阶段必须交付真实闭环，不能只增加抽象。

## 2. Phase 00 事实依据

RAGFlow 离线主链路为：

`document_api.upload_document` → `FileService.upload_document` → ObjectStorage/File/Document/File2Document → `DocumentService.run` → `TaskService.queue_tasks` → Redis Stream → `task_executor.collect/handle_task` → `TaskHandler._run_standard_chunking_impl` → `ChunkService.build_chunks` → `EmbeddingService.embed_chunks` → `ChunkService.insert_chunks` → DocStore。

固定问答链路为：

`chat_api.session_completion` → `dialog_service.rag_agent(reasoning off)` → `async_chat` → `Dealer.retrieval` → `kb_prompt` → `LLMBundle` → Citation。

上游提供能力与顺序证据，但其 Peewee、settings、Redis ACK 和 DocStore 耦合不直接采用。

## 3. 前置、进入条件和输入

- **前置阶段**：Phase 03。
- **进入条件**：Phase 03 DoD 已完成。仅在用户明确授权复审 Phase 04 计划后，才可执行 P04-T01 作为选型准入任务；P04-T01 必须解决 O-002 搜索后端、O-006 队列实现和 O-007 首批 LLM/Embedding，若确定抽取源码还须解决 O-004。P04-T02 及后续实现任务只有在这些决策已 Resolved、计划再次冻结后才能开始。
- **输入**：统一领域/Ports、API/Worker 骨架、PostgreSQL/Redis/MinIO、真实 Search Adapter、模型凭据或本地模型、最小测试文档。

## 4. 范围、排除与交付物

**范围**：上传、哈希/MIME、安全校验、基础 Parser（至少 TXT/Markdown，加一个真实复杂格式路径）、General Chunk、Embedding、全文/向量最小索引、向量检索、Prompt、LLM、Citation、任务状态/进度、tenant 隔离、E2E/评测基线。

**排除**：完整 OCR/版面和全格式、场景 Chunk 完整集、混合融合/Reranker/跨语言、生命周期原子发布、Agent Tool、GraphRAG/RAPTOR/多模态/时序 RAG。

**交付物**：真实 Adapter、API、Worker pipeline、FixedRAGService/KnowledgeQueryService 最小实现、迁移、E2E 数据和报告。

## 5. 目标模块和文件

```text
src/ragflow_agent/knowledge/application/{upload,ingestion,query,fixed_rag}.py
src/ragflow_agent/knowledge/infrastructure/{database,object_store,queue,parsers,embedding,search,models}/
src/ragflow_agent/api/routes/{knowledge_bases,documents,rag}.py
src/ragflow_agent/worker/ingestion_pipeline.py
tests/{contract,integration,e2e,evaluation}/minimum_rag/
```

## 6. RAGFlow 源码范围与采用

| 源码/调用 | 采用 |
|---|---|
| `document_api.py::upload_document/parse_documents` → `FileService.upload_document` → `DocumentService.run` | 上传/投递顺序参考，自研 |
| `TaskService.queue_tasks` → `RedisDB.queue_product` → `task_executor.collect/handle_task` | 消息边界参考；可靠语义自研 |
| `chunk_builder.py::get_parser/run_chunking` → `rag/app/naive.py::chunk` | General 路径可通过 `ragflow_adapters` 做最小实验，须 O-004 |
| `EmbeddingService.embed_chunks` → `ChunkService.insert_chunks` | 批处理/字段顺序参考，自研 |
| `Dealer.get_vector/search` | 向量检索用例参考，自研 SearchPort Adapter |
| `dialog_service.async_chat` → `kb_prompt` → `LLMBundle` | 固定回答顺序参考，自研 |
| `Dealer.insert_citations` | 引用算法思想可改造实验；目标 Citation 绑定 version |

- **直接复用**：无。
- **`ragflow_adapters` 改造复用**：只在 O-004/许可证实验通过后考虑 `rag/app/naive.py` 的分块规则；否则参考重写。
- **参考后自研**：上传、任务、Embedding、索引、检索、Prompt、回答和 Citation 主链路。
- **明确不采用**：Peewee Service、Quart、全局 settings、异常后无条件 ACK。

## 7. 框架与自研职责

- **LangChain**：Embedding、ChatModel、Prompt、标准输出/流式适配。
- **LangGraph**：不参与固定 RAG；不得用 Agent 图包装最小问答。
- **自研**：领域状态、API、Worker、队列协议、Parser/Chunk pipeline、Search Adapter、固定问答、Citation、权限、Trace。

## 8. 任务总表

| 任务 | 名称 | 状态 | 前置 |
|---|---|---|---|
| P04-T01 | 冻结最小技术选型与垂直切片 | 未开始 | Phase 03 |
| P04-T02 | 实现知识库/文档持久化与对象存储 | 未开始 | P04-T01 |
| P04-T03 | 实现上传 API 与 IngestionJob 投递 | 未开始 | P04-T02 |
| P04-T04 | 实现 Worker 与最小 ingestion pipeline | 未开始 | P04-T01、P04-T03 |
| P04-T05 | 实现基础 Parser | 未开始 | P04-T04 |
| P04-T06 | 实现 General Chunk | 未开始 | P04-T05 |
| P04-T07 | 实现 Embedding Adapter | 未开始 | P04-T01、P04-T06 |
| P04-T08 | 实现索引写入和最小检索 | 未开始 | P04-T01、P04-T07 |
| P04-T09 | 实现 Prompt 与 LLM 回答 | 未开始 | P04-T08 |
| P04-T10 | 实现 Citation、来源和最小 Trace | 未开始 | P04-T09 |
| P04-T11 | 建立最小 E2E 与评测基线 | 未开始 | P04-T02 至 P04-T10 |
| P04-T12 | 执行 Phase 04 出口审查 | 未开始 | P04-T01 至 P04-T11 |

## 9. 具体任务

### P04-T01：冻结最小技术选型与垂直切片

- **状态**：未开始
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
- **验证命令**：按选择记录实际 probe；不得预填。
- **验收标准**：O-002/O-006/O-007 Resolved；回退方案明确。
- **风险和回滚方法**：Adapter 可替换；选型失败不改领域协议。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待记录。

### P04-T02：实现知识库/文档持久化与对象存储

- **状态**：未开始
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
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待记录。

### P04-T03：实现上传 API 与 IngestionJob 投递

- **状态**：未开始
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
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待记录。

### P04-T04：实现 Worker 与最小 ingestion pipeline

- **状态**：未开始
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
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待记录。

### P04-T05：实现基础 Parser

- **状态**：未开始
- **目标**：至少支持 TXT、Markdown 和一个复杂格式的真实 ParseRequest→ParsedDocument。
- **为什么需要**：验证统一文档结构可落地。
- **输入**：P04-T04、ParserPort、样本。
- **前置任务**：P04-T04。
- **操作步骤**：实现简单 Parser；选择复杂格式最低路径；限制大小/超时；保留来源；输出 warning。
- **涉及文件**：`infrastructure/parsers/`、fixtures、测试。
- **预期输出**：基础 Parser Adapter。
- **RAGFlow 源码依据**：`rag/app/naive.py::chunk`、`chunk_builder.get_parser`；复杂 Parser 只作参考。
- **实现或复用方式**：简单格式自研；复杂格式按 O-004 决定。
- **测试方法**：黄金文本、编码、空/损坏文件、资源限制。
- **验证命令**：`uv run pytest tests/contract/parsers tests/integration/parsers/minimum -q`
- **验收标准**：不支持格式返回稳定错误；来源字段完整。
- **风险和回滚方法**：复杂格式失败不阻塞 TXT/MD 闭环，但不得声称多格式完成。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待记录。

### P04-T06：实现 General Chunk

- **状态**：未开始
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
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待记录。

### P04-T07：实现 Embedding Adapter

- **状态**：未开始
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
- **验证命令**：`uv run pytest tests/contract/embedding tests/integration/embedding -q`
- **验收标准**：错误定位到 chunk；模型元数据完整。
- **风险和回滚方法**：供应商失败回退 stub 仅测试，不伪生产。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待记录。

### P04-T08：实现索引写入和最小检索

- **状态**：未开始
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
- **验证命令**：`uv run pytest tests/contract/search tests/integration/search -q`
- **验收标准**：跨租户零结果；记录可按版本重建。
- **风险和回滚方法**：后端 DSL 只在 Adapter；索引 alias 可回退。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待记录。

### P04-T09：实现 Prompt 与 LLM 回答

- **状态**：未开始
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
- **验证命令**：`uv run pytest tests/unit/rag tests/integration/rag/test_answer.py -q`
- **验收标准**：固定 RAG 不经过 Agent；无证据不伪造来源。
- **风险和回滚方法**：Prompt 版本化；模型失败返回稳定错误。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待记录。

### P04-T10：实现 Citation、来源和最小 Trace

- **状态**：未开始
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
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待记录。

### P04-T11：建立最小 E2E 与评测基线

- **状态**：未开始
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
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待记录。

### P04-T12：执行 Phase 04 出口审查

- **状态**：未开始
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
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待记录。

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

## 12. 实际执行结果预留

- 实际技术选型/文件/迁移：待执行。
- 实际 E2E/评测/安全结果：待执行。
- 复用 provenance 与偏差：待执行。
- 阶段出口结论：待执行。
