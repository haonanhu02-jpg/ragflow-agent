---
document_id: RAGFLOW-CAPABILITY-MATRIX
status: active
last_updated_at: "2026-07-30"
ragflow_frozen_baseline_commit: "cd846cc9d4e32a19e684c59a1f302601027ef976"
---

# RAGFlow 能力与目标采用矩阵

## 文档导航

[项目总纲](./00-project-master.md) · [RAGFlow 架构](./01-ragflow-architecture.md) · [目标架构](./03-target-architecture.md) · [代码复用策略](./04-code-reuse-strategy.md) · [开发路线图](./05-development-roadmap.md) · [工程标准](./06-engineering-standards.md) · [决策与风险](./07-decisions-and-risks.md)

## 1. 使用规则

本文件是能力名称、责任归属、采用分类、实施阶段和当前状态的规范来源。其他文档引用能力时必须使用本文件的 `CAP-*` 编号和完整名称。Phase 00 原始基线形成 `CAP-01` 至 `CAP-42`；2026-07-30 用户恢复时序 RAG 范围后新增 `CAP-43`。

- RAGFlow 代码位置均相对于冻结 commit `cd846cc9d4e32a19e684c59a1f302601027ef976`。
- “LangChain 能否承担”和“LangGraph 能否承担”描述框架原生或合理扩展能力，不代表项目已经实现。
- 采用分类只能使用：`直接复用`、`改造复用`、`参考重写`、`自行开发`、`暂缓`。
- 当前项目没有业务代码，因此所有非暂缓能力均为“未实现”。
- 复用的具体源文件、依赖和改造办法见[代码复用策略](./04-code-reuse-strategy.md)。
- 已实际核验的类、函数和调用关系集中登记在[源码证据地图](./research/ragflow-source-map.md)；矩阵中的路径不能脱离该冻结 commit 解释。

## 2. 能力矩阵

| ID | 能力名称 | RAGFlow 是否具备 | RAGFlow 代码位置 | LangChain 能否承担 | LangGraph 能否承担 | 采用方式 | 复用分类 | 实施阶段 | 验收方法 | 当前状态 |
|---|---|---|---|---|---|---|---|---|---|---|
| CAP-01 | 多格式文档解析 | 是 | `deepdoc/parser/{pdf,docx,excel,ppt}_parser.py`；`rag/app/naive.py::chunk`；`chunk_builder.py::get_parser` | 部分：标准 Loader | 否 | 统一 ParserPort；简单格式优先标准库，复杂格式适配 RAGFlow Parser | 改造复用 | Phase 04 最小路径；Phase 05 完整 | PDF、DOCX、PPTX、XLSX、TXT、MD、HTML、图片、音频、邮件黄金样本 | 未实现；冻结源码已核验 |
| CAP-02 | OCR 与版面分析 | 是 | `deepdoc/vision/`；`deepdoc/parser/pdf_parser.py::RAGFlowPdfParser` | 否 | 否 | 隔离模型资源和全局 settings，输出统一 ParsedBlock | 改造复用 | Phase 05 | 扫描 PDF、复杂版面、表格和坐标黄金输出；资源上限测试 | 未实现；源码已定位 |
| CAP-03 | 统一文档结构 | 部分 | DeepDOC sections、positions、tables、images 字段 | 部分：Document 类型不足 | 否 | 自定义 ParsedDocument/ParsedBlock，适配各 Parser 输出 | 自行开发 | Phase 03 契约；Phase 05 全 Parser 落地 | 所有 Parser 通过同一契约测试，保留页码、bbox、层级和来源顺序 | 未实现；待设计 |
| CAP-04 | 场景化 Chunk Method | 是 | `rag/svr/task_executor_refactor/chunk_builder.py::get_parser/run_chunking`；`rag/app/{naive,paper,book,manual,laws,qa,table,resume,picture,audio,email}.py::chunk` | 部分：Text Splitter | 否 | 建立 ChunkerPort 和策略注册表；抽取场景规则 | 改造复用 | Phase 04 General；Phase 05 完整 | 每种策略固定输入、黄金 Chunk、稳定 ID、Token 上限和重叠测试 | 未实现；冻结源码已核验 |
| CAP-05 | Chunk 自动关键词 | 是 | `rag/svr/task_executor_refactor/chunk_service.py::build_chunks` → `chunk_post_processor.py::extract_keywords`；`rag/prompts/generator.py::keyword_extraction` | 是：模型、Prompt、结构化输出 | 否 | 重写应用流程并参考 Prompt/批处理 | 参考重写 | Phase 09 | 关键词数量、格式、可重复性、失败降级、成本和检索增益测试 | 未实现；冻结源码已核验 |
| CAP-06 | Chunk 自动问题 | 是 | `rag/svr/task_executor_refactor/chunk_service.py::build_chunks` → `chunk_post_processor.py::generate_questions`；`rag/prompts/generator.py::question_proposal` | 是 | 否 | 重写应用流程并参考 Prompt | 参考重写 | Phase 09 | 问题格式、覆盖度、去重、失败降级、成本和检索增益测试 | 未实现；冻结源码已核验 |
| CAP-07 | 摘要、标题与 TOC | 部分 | `ChunkService.insert_chunks/_create_mother_chunks`；`TaskHandler._build_toc`；`PostProcessor.insert_toc_chunk`；RAPTOR summary | 是 | 部分：可编排 | Phase 05 只保留解析得到的结构字段和增强扩展点；Phase 09 分离摘要、生成 TOC 和父子 Chunk 产物 | 参考重写 | Phase 05 结构契约；Phase 09 自动生成/父子/RAPTOR | 层级、页码、来源映射、忠实度、Token 预算、父子关系和重建测试 | 未实现；冻结源码已核验 |
| CAP-08 | Embedding 与索引写入 | 是 | `rag/svr/task_executor_refactor/embedding_service.py::EmbeddingService.embed_chunks`；`chunk_service.py::ChunkService.insert_chunks` | 是：Embeddings | 否 | LangChain Embeddings + 自研版本和 SearchIndexPort；参考字段构造 | 参考重写 | Phase 04 | 批处理、维度、模型版本、失败重试、索引可检索和重建测试 | 未实现；冻结源码已核验 |
| CAP-09 | 全文检索 | 是 | `rag/nlp/query.py::FulltextQueryer.question`；`rag/nlp/search.py::Dealer.search` | 部分 | 否 | SearchPort 实现 BM25；参考 query/tokenizer | 改造复用 | Phase 04 基线；Phase 06 完整 | 关键词、短语、中文英文、过滤和排序评测 | 未实现；冻结源码已核验 |
| CAP-10 | 向量检索 | 是 | `Dealer.get_vector/search/_knn_scores`；`MatchDenseExpr`；各 DocStore | 是：Retriever/VectorStore | 否 | LangChain Embeddings + SearchPort KNN | 参考重写 | Phase 04 基线；Phase 06 完整 | Recall@K、维度校验、阈值和过滤测试 | 未实现；冻结源码已核验 |
| CAP-11 | 混合检索 | 是 | `Dealer.search/retrieval/rerank_with_knn`；`FusionExpr` | 部分 | 否 | 全文和向量候选统一到 RetrievalCandidate 后融合 | 改造复用 | Phase 06 | 相对全文/向量基线提升；融合权重边界测试 | 未实现；候选与最终融合已核验 |
| CAP-12 | 查询改写与独立问题生成 | 是 | `generator.py::full_question` | 是 | 是：决定是否改写和重试 | LangChain Prompt/结构化输出；LangGraph 路由 | 参考重写 | Phase 06 | 多轮省略、指代、无需改写和失败回退数据集 | 未实现；源码已定位 |
| CAP-13 | 跨语言查询 | 是 | `generator.py::cross_languages`；Dialog/Tool 调用 | 是 | 部分：路由 | 参考 Prompt，输出原查询与翻译查询集合 | 参考重写 | Phase 06 | 中英跨语言 Recall、专有名词保真和降级测试 | 未实现；源码已定位 |
| CAP-14 | 关键词扩展 | 是 | `generator.py::keyword_extraction`；`FulltextQueryer` synonym/term weight | 是 | 部分 | LLM 关键词与词法同义扩展分开记录 | 改造复用 | Phase 06 | 扩展前后 Recall、噪声率、延迟和 Trace 测试 | 未实现；源码已定位 |
| CAP-15 | 元数据过滤 | 是 | `common/metadata_utils.py::apply_meta_data_filter/meta_filter`；`generator.py::gen_meta_filter`；`DocMetadataService` push-down | 部分：SelfQuery 可参考 | 否 | 自定义可验证 Filter AST，适配 SearchPort | 参考重写 | Phase 06 | 操作符、类型、组合逻辑、非法字段和后端一致性测试 | 未实现；返回哨兵与 fallback 已核验 |
| CAP-16 | 权限过滤 | 部分 | `Knowledgebase.permission`；`KnowledgebaseService._visibility_and_status_filter/accessible`；`check_team_permission.py`；`Dealer.retrieval` tenant index | 否 | 否 | `AuthorizationContext` + `PermissionChecker`；强制 tenant 条件进入 Repository、Task、Search、Tool 和 Citation，复杂 ACL 后置 | 自行开发 | Phase 03 契约；Phase 06 检索强制；Phase 10 生产门禁 | 跨租户默认拒绝、owner/visibility、伪造资源 ID、搜索与数据库一致性及 Tool/Citation 越权负向测试 | 未实现；第一版边界已确认 |
| CAP-17 | 空结果降级 | 部分 | `Dealer.search` 二次重查；`apply_meta_data_filter` 的 `None/[-999]`；`Dialog.prompt_config.empty_response`；Agentic abstain | 部分 | 是：降级路由和重试 | 结构化 `empty_reason`；默认策略待确认 | 自行开发 | Phase 06 | 真空结果、阈值过高、过滤过严和后端故障测试 | 未实现；RAGFlow 隐式语义已核验，目标策略待决策 |
| CAP-18 | 候选清理与去重 | 是 | `Dealer._prune_deleted_chunks`；检索合并和 Chunk ID 去重 | 部分 | 否 | 自研统一 CandidateCleaner，参考孤儿 Chunk 防御 | 参考重写 | Phase 06 | 删除文档、旧版本、重复 Chunk、空文本和每文档限额测试 | 未实现；源码已定位 |
| CAP-19 | Reranker | 是 | `Dealer.rerank_by_model`；`LLMBundle.similarity` | 是：Reranker 适配 | 否 | LangChain/供应商模型适配 + RerankerPort | 参考重写 | Phase 06 | NDCG/MRR 提升、批处理、超时和无模型降级 | 未实现；源码已定位 |
| CAP-20 | 分数融合、阈值与 TopK/TopN | 是 | `Dealer._rerank_window/retrieval/rerank_by_model/rerank_with_knn`；Dialog 字段 | 部分 | 否 | 统一 ScoreBreakdown；复用融合算法思想 | 改造复用 | Phase 06 | 权重 0/1、阈值边界、分页、TopK/TopN 和排序稳定性 | 未实现；分数与截断顺序已核验 |
| CAP-21 | 引用与来源定位 | 是 | `generator.py::kb_prompt/citation_prompt`；`Dealer.fetch_chunk_vectors/insert_citations`；`dialog_service.py::repair_bad_citation_formats` | 部分：Prompt | 否 | 参考引用算法，自研 Citation 并绑定 DocumentVersion | 改造复用 | Phase 04 基础；Phase 06 完整 | 引用存在性、页码、quote、版本、删除后行为和准确率 | 未实现；相似度引用算法已核验 |
| CAP-22 | Retrieval Trace | 部分 | `Dealer.retrieval(trace_id)` 权重日志；`DialogService.async_chat` Langfuse LLM observation/耗时；无统一持久候选事件模型 | 部分：Callback | 部分：图 Trace | 自研查询变换、候选和分数全链路事件模型 | 自行开发 | Phase 06 | 单次查询可还原所有阶段、参数、模型、候选和延迟 | 未实现；源码缺口已核验 |
| CAP-23 | 文档上传与解析任务 | 是 | `document_api.py::upload_document/parse_documents` → `FileService.upload_document` → `DocumentService.run` → `TaskService.queue_tasks` | 否 | 部分：可编排 | FastAPI 持久化 tenant-scoped IngestionJob 后投递；独立 Worker 按 tenant_id + job_id 加载并执行 | 参考重写 | Phase 04 | 上传、哈希、tenant 隔离、任务、进度、失败和对象存储集成测试 | 未实现；冻结调用链已核验 |
| CAP-24 | 文档更新与重新解析 | 是 | `document_api.py::update_document/parse_documents`；`DocumentService.clear_chunk_num_when_rerun/run`；旧 Task/Nav/DocStore delete | 否 | 部分 | 自研 DocumentVersion 和候选索引激活 | 自行开发 | Phase 07 | 旧版本持续可查、新版本原子切换、失败保留旧版 | 未实现；RAGFlow 原地更新和先删后建已核验 |
| CAP-25 | 文档删除与索引同步 | 是 | `document_api.py::delete_documents` → `FileService.delete_docs` → `DocumentService.delete_document_and_update_kb_counts/remove_document/delete_chunk_images` → DocStore/ObjectStore | 否 | 部分 | 自研跨 PostgreSQL/ObjectStore/Search 补偿流程 | 自行开发 | Phase 07 | 正常删除、部分失败、重试、幂等和引用不可见性 | 未实现；关系行先删、后续 best-effort 已核验 |
| CAP-26 | 任务重试、取消与幂等 | 部分 | `TaskService.get_task` 领取计数/3 次放弃；`cancel_all_task_of/has_canceled`；Redis pending/requeue；`task_executor.handle_task` 异常后 ACK | 否 | 是：只编排 Agent 重试和恢复 | TaskQueuePort + IngestionJob 状态机；禁止照搬异常后无条件 ACK，区分成功、可重试、不可重试和死信 | 自行开发 | Phase 07 | 重复投递、Worker 崩溃、ACK 时机、死信、取消竞态、恢复和无重复 Chunk | 未实现；可靠性缺口已核验 |
| CAP-27 | 固定 RAG 问答 | 是 | `chat_api.py::session_completion` → `dialog_service.py::rag_agent`（reasoning off）→ `async_chat` → `Dealer.retrieval` → `kb_prompt` → `LLMBundle` → Citation | 是 | 否 | 自研 FixedRAGService，使用统一 KnowledgeQueryService | 参考重写 | Phase 04 | 端到端答案、空结果、引用、流式输出和 Trace | 未实现；冻结调用链已核验 |
| CAP-28 | KnowledgeBaseTool | 是 | `agent/tools/retrieval.py::Retrieval._retrieve_kb` → `settings.retriever.retrieval` → TOC/children/KG → `Canvas.add_reference`/`kb_prompt` | 是：Tool | 是：Tool 节点 | LangChain Tool 包装 KnowledgeQueryService；参考参数与引用输出 | 参考重写 | Phase 08 | 与固定 RAG 检索结果一致；结构化错误和引用测试 | 未实现；冻结调用链已核验 |
| CAP-29 | LangGraph 状态、路由与循环 | 部分 | `agentic_rag_graph.py::AgenticState/build_agentic_graph/run_agentic_rag`；主 Canvas 是自定义运行时 | 部分 | 是 | 自研 AgentState 和业务图，参考 Agentic RAG 节点 | 自行开发 | Phase 02 基础；Phase 08 知识检索循环 | 路由、循环上限、超时、取消、错误路径和状态序列 | Phase 02 基础已实现并验收：AgentState v1、最小图/Router、技术步数上限、重试/超时/取消；知识检索循环仍未实现 |
| CAP-30 | Checkpoint 与运行恢复 | 否：Agentic 图未配置 Checkpointer | `agentic_rag_graph.py::build_agentic_graph` 以无参数 `g.compile()` 结束；`ainvoke` 无 thread_id | 否 | 是 | 使用 LangGraph Checkpointer，持久化 thread/run | 自行开发 | Phase 02 | 进程重启、节点失败、重复恢复和版本兼容测试 | 已实现并验收：官方异步 PostgreSQL Saver、租户作用域、版本迁移/拒绝、失败节点恢复、重复 resume 和跨租户失败关闭 |
| CAP-31 | Human-in-the-loop | 部分：Canvas 有 `userfillup/user_inputs`，非目标运行时 | `agent/canvas.py::Canvas._run_impl`；Agentic `StateGraph` 无 interrupt | 部分：Tool | 是 | LangGraph interrupt/resume + 审批数据模型；复用 Phase 02 Checkpoint/恢复协议 | 自行开发 | Phase 08 | 中断、审批、拒绝、超时、重复提交、权限重验和审计测试 | 未实现；运行时差异已核验 |
| CAP-32 | 多 Agent 协作 | 部分 | Canvas Agent Invoke/组件与 Agentic orchestrator；无 LangGraph supervisor/worker 治理和持久共享状态 | 是：Tool/Agent 封装 | 是 | 在单 Agent 成熟后设计 supervisor/worker 图 | 自行开发 | Phase 08 | 子 Agent 边界、共享状态、失败隔离、终止和成本测试 | 未实现；源码边界已核验 |
| CAP-33 | GraphRAG | 是 | `TaskHandler._run_graphrag`；`general/index.py::run_graphrag_for_kb/generate_subgraph/resolve_entities/extract_community`；`checkpoints.py`；`phase_markers.py`；`search.py::KGSearch` | 部分 | 部分：构建/检索编排 | 抽取算法并替换 Service、settings、DocStore、Redis 依赖，派生物绑定版本 | 改造复用 | Phase 09 | 图构建正确性、实体/关系质量、查询增益、版本绑定、重建、取消和 checkpoint 恢复 | 未实现；构建/恢复/查询链已核验 |
| CAP-34 | RAPTOR | 是 | `knowlege_compile/raptor.py::RecursiveAbstractiveProcessing4TreeOrganizedRetrieval`；`TaskHandler._run_raptor`；`RaptorService._generate_raptor` | 部分 | 部分：任务编排 | 抽取聚类、树摘要和来源合并，接入统一 Chunk/Index/Version | 改造复用 | Phase 09 | 层级树、叶 Chunk 来源、检索增益、成本、收敛和取消测试 | 未实现；算法/来源/写入链已核验 |
| CAP-35 | 多模态 RAG | 是 | `rag/app/picture.py::chunk/vision_llm_chunk`、`audio.py::chunk`、`deepdoc/parser/figure_parser.py::VisionFigureParser`、LLMBundle Vision/ASR | 部分：模型接口 | 部分：流程编排 | ParserPort + Vision/ASR LangChain 适配 + 多模态 Chunk | 改造复用 | Phase 05 解析基础；Phase 09 跨模态检索 | 图片/音频解析、媒体来源映射、跨模态检索和引用测试 | 未实现；解析/模型链已核验 |
| CAP-36 | 模型注册与调用 | 是 | `LLMBundle`；`tenant_model_service.py`；`rag/llm/` | 是 | 否 | LangChain 模型接口；自研注册、密钥、配额、降级和审计 | 自行开发 | Phase 01 基础；Phase 04 最小可用；后续扩展 | 多供应商契约、流式、Token、超时、降级和密钥保护 | Phase 02 已增加结构化 AgentModelPort/LangChain ChatModel Adapter 和确定性门禁；真实 Provider、调用与注册仍未实现 |
| CAP-37 | FastAPI 服务接口 | 否：RAGFlow 使用 Quart | `api/apps/` 仅作接口用例参考；`launch_backend_service.sh` 证明 API/Worker 可分进程 | 否 | 否 | 自研 FastAPI API 入口；与 Worker 同仓库共享应用/领域代码，不经内部 HTTP 调用 Worker | 自行开发 | Phase 01 基础；各阶段扩展 | OpenAPI、校验、错误、`AuthorizationContext`、流式、API/Worker 进程边界和集成测试 | Phase 01 已实现 app factory、健康/就绪、错误/Trace 和可信身份边界；业务 API 未实现 |
| CAP-38 | 后台任务与 Ingestion 执行 | 是 | `TaskService.queue_tasks/get_task`；`RedisDB.queue_product/queue_consumer/get_unacked_iterator`；`task_executor.py::collect/handle_task`；`TaskManager.run_refactored_task`；`TaskHandler.handle_task`；`launch_backend_service.sh` | 否 | 部分：不承担数据面 Worker | 模块化单体 + 独立 Ingestion Worker 已确认；TaskQueuePort/IngestionJob 共享契约，具体队列库待确认 | 参考重写 | Phase 04 基础；Phase 07 可靠化 | 独立启动、tenant-scoped 消息、ACK、重试、取消、崩溃恢复、幂等、进度和背压 | Phase 01 已实现独立 Worker 生命周期/心跳/关闭空壳；任务消费、ACK、重试和 ingestion 未实现 |
| CAP-39 | 评测与回归门禁 | 部分：主要是性能 benchmark | `test/benchmark/dataset.py`；`metrics.py::summarize`；`report.py::{chat_report,retrieval_report}` | 部分：可接评测库 | 部分：图执行评测 | 自研检索、答案、引用、Agent、性能和回归体系 | 自行开发 | Phase 04 起建基线；Phase 10 完整门禁 | 固定数据集、Recall/MRR/NDCG、忠实度、引用正确率、Agent 成功率、性能阈值、基线对比和 CI 门禁 | Phase 01 仅完成工程测试/静态/迁移/容器 CI 门禁；RAG 质量评测未实现 |
| CAP-40 | 日志、指标与链路追踪 | 部分 | logging；`common/token_utils.py::token_usage_sink`；LLMBundle/Langfuse；Dealer `trace_id` 日志；Docker OTEL/Jaeger 配置 | 部分：Callbacks | 部分：LangGraph events | 自研统一 Trace/metric schema，接入标准观测后端 | 自行开发 | Phase 01 基础；Phase 10 完整 | 请求到任务、检索、模型、Agent 的关联；trace 传播、采样和敏感信息检查 | Phase 02 已增加 AgentEvent v1、节点/模型/Tool/恢复关联、脱敏和降级标志；持久 Trace 后端、指标和外部观测未实现 |
| CAP-41 | 权限与安全 | 部分 | `Tenant`、`UserTenant`、KB permission、`add_tenant_id_to_kwargs`、`check_team_permission.py`、API token、认证配置、Sandbox | 否 | 部分：Tool 审批 | 第一版自研 tenant 强隔离、owner/visibility、AuthorizationContext、PermissionChecker；复杂 RBAC、部门和动态规则后置 | 自行开发 | Phase 03 第一版边界；Phase 10 生产门禁；复杂规则另行决策 | 跨租户/owner/visibility 负向测试、密钥扫描、文件攻击、Tool 审批和审计 | Phase 01 已实现可信身份入口、密钥脱敏/扫描和非 root 容器；tenant/ACL 领域契约未实现 |
| CAP-42 | 生产部署、备份与恢复 | 是：RAGFlow 有 Docker/Helm | `docker/launch_backend_service.sh`；`docker/docker-compose{,-base}.yml`；`helm/templates/ragflow.yaml`；`helm/values.yaml` | 否 | 否 | 第一版同一制品启动 FastAPI 与独立 Worker；自研配置、迁移、备份和恢复手册，不拆微服务 | 参考重写 | Phase 10 | API/Worker 独立健康检查和扩缩容、全新部署、升级、回滚、备份恢复和容量测试 | Phase 01 已实现同一非 root 镜像和开发 Compose 健康拓扑；生产部署、备份恢复未实现 |
| CAP-43 | 时序 RAG | 部分：有 timeline 知识编译，不是完整时序 RAG | `api/db/init_data/compilation_templates/timeline.yaml`；`runner.py::run_structure_compile_over_batches/_compile_batch/_flush` → `structure.py::compile_structure_from_text/merge_compiled_structures/cleanup_timeline_isolated_entities` | 部分：模型/Prompt/Tool 适配 | 部分：查询与工具路由 | 自研事件时间线、数值时序窗口/聚合/对齐、文本证据融合、时间 Citation/Trace；timeline 模板只作参考 | 自行开发 | Phase 09 | 时间过滤、乱序/缺失/时区、窗口聚合、事件/文本对齐、tenant/版本/删除、普通检索对照增益 | 未实现；范围由 ADR-014 恢复，完整 RAGFlow 路径执行前再验证 |

## 3. 分类汇总

### 3.1 改造复用

`CAP-01`、`CAP-02`、`CAP-04`、`CAP-09`、`CAP-11`、`CAP-14`、`CAP-20`、`CAP-21`、`CAP-33`、`CAP-34`、`CAP-35`。

### 3.2 参考重写

`CAP-05`、`CAP-06`、`CAP-07`、`CAP-08`、`CAP-10`、`CAP-12`、`CAP-13`、`CAP-15`、`CAP-18`、`CAP-19`、`CAP-23`、`CAP-27`、`CAP-28`、`CAP-38`、`CAP-42`。

### 3.3 自行开发

`CAP-03`、`CAP-16`、`CAP-17`、`CAP-22`、`CAP-24`、`CAP-25`、`CAP-26`、`CAP-29`、`CAP-30`、`CAP-31`、`CAP-32`、`CAP-36`、`CAP-37`、`CAP-39`、`CAP-40`、`CAP-41`、`CAP-43`。

### 3.4 直接复用与暂缓

- 当前没有能力获批“直接复用”；源文件必须先经过[代码复用策略](./04-code-reuse-strategy.md)规定的依赖、许可证和测试审计。
- 当前没有目标能力标记为“暂缓”。GraphRAG、RAPTOR、多模态 RAG 和时序 RAG 安排在 Phase 09，均默认关闭并要求独立验收。

## 4. 维护约束

1. 增删能力必须同步更新[项目总纲](./00-project-master.md)、[目标架构](./03-target-architecture.md)和[开发路线图](./05-development-roadmap.md)。
2. 修改采用分类必须同步更新[代码复用策略](./04-code-reuse-strategy.md)。
3. 修改阶段必须同步更新[开发路线图](./05-development-roadmap.md)和未生成的对应阶段文档。
4. 当前状态只有在代码、迁移和验收测试存在后才能改为“已实现”。
