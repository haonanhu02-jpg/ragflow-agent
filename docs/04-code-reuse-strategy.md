---
document_id: CODE-REUSE-STRATEGY
status: active
last_updated_at: "2026-08-01"
ragflow_frozen_baseline_commit: "cd846cc9d4e32a19e684c59a1f302601027ef976"
---

# RAGFlow Python 代码复用策略

## 文档导航

[项目总纲](./00-project-master.md) · [RAGFlow 架构](./01-ragflow-architecture.md) · [能力矩阵](./02-ragflow-capability-matrix.md) · [目标架构](./03-target-architecture.md) · [开发路线图](./05-development-roadmap.md) · [工程标准](./06-engineering-standards.md) · [决策与风险](./07-decisions-and-risks.md) · [Agentic RAG](./10-agentic-rag.md)

## 1. 复用目标与约束

复用的目标是减少复杂 Parser、Chunk、检索和高级 RAG 算法的重复开发，不是把 RAGFlow 内部运行时移入本项目。

- 上游固定 commit：`cd846cc9d4e32a19e684c59a1f302601027ef976`。
- 分析范围：Python。
- 当前批准直接复制的源文件：无。
- 当前项目状态：Phase 04 至 Phase 07 已完成最小 RAG、Parser/Chunk、在线检索和文档生命周期；RAGFlow 直接复用和改造复用代码仍为零，现有实现均为独立代码。
- 能力分类以[能力矩阵](./02-ragflow-capability-matrix.md)为准。
- 每个候选的源码符号和调用关系以[源码证据地图](./research/ragflow-source-map.md)为证据入口；仅有同名文件不构成可复用结论。

### 1.1 采用分类

| 分类 | 定义 | 合入条件 |
|---|---|---|
| 直接复用 | 基本保持上游文件结构和实现 | 低耦合、许可证清楚、依赖可接受、测试通过、用户批准 |
| 改造复用 | 保留核心算法，替换数据结构、配置、服务和 I/O | 适配端口、隔离依赖、保留来源、建立契约测试 |
| 参考重写 | 只保留行为、顺序、公式或 Prompt 思路 | 新实现不导入上游内部模块，测试验证行为 |
| 自行开发 | 上游或框架不能满足目标 | 先定义领域契约和验收指标 |
| 暂缓 | 目标保留，但当前不实施 | 必须给出恢复条件和阶段 |

### 1.2 抽取难度

- `低`：少量纯函数依赖，输入输出清楚。
- `中`：需要替换 tokenizer、模型或通用工具。
- `高`：依赖 Service、settings、DocStore、Redis 或上游字典 Schema。
- `极高`：跨 API、数据库、任务、模型、存储和全局状态。

## 2. 源码级复用登记

所有源文件均指冻结 commit 下的同名路径。许可证列只说明 RAGFlow 主许可证要求，第三方依赖仍需单独核查。

| 源文件 | 核心类或函数 | 内部依赖 | 抽取难度 | 许可证要求 | 采用分类 | 改造方案 | 目标模块 |
|---|---|---|---|---|---|---|---|
| `deepdoc/parser/pdf_parser.py` | `RAGFlowPdfParser`、`PlainParser`、`VisionParser` | `common.settings`、project path、RAG tokenizer、Prompt、OCR/Layout/Table vision、pdfplumber、pypdf、Pillow、NumPy、sklearn、XGBoost、模型下载 | 极高 | Apache-2.0；保留声明和修改标记；核查模型、XGBoost、PDF 库和二进制资源 | 改造复用 | 把模型加载、路径、OCR、Vision、回调注入 ParserContext；映射为 ParsedDocument | `src/ragflow_agent/infrastructure/ragflow_adapters/parsing/pdf.py` |
| `deepdoc/parser/docx_parser.py` | `RAGFlowDocxParser` | python-docx、pandas、RAG tokenizer、LazyImage | 中 | Apache-2.0；核查 python-docx 和图片样本 | 改造复用 | 替换 tokenizer；统一段落、表格、图片和层级输出 | `src/ragflow_agent/infrastructure/ragflow_adapters/parsing/docx.py` |
| `deepdoc/parser/excel_parser.py` | `RAGFlowExcelParser` | pandas、openpyxl、codec、LazyImage | 中 | Apache-2.0；核查 openpyxl/pandas | 改造复用 | 把 worksheet/row/table 映射为 ParsedBlock；限制工作簿规模 | `src/ragflow_agent/infrastructure/ragflow_adapters/parsing/excel.py` |
| `deepdoc/parser/ppt_parser.py` | `RAGFlowPptParser` | python-pptx | 低至中 | Apache-2.0；核查 python-pptx | 改造复用 | 保留 slide 顺序和文本提取；补充统一图片/备注字段 | `src/ragflow_agent/infrastructure/ragflow_adapters/parsing/ppt.py` |
| `deepdoc/vision/` | `OCR`、`LayoutRecognizer`、`TableStructureRecognizer` | ONNX Runtime、OpenCV、模型权重、设备选择、资源文件 | 极高 | Apache-2.0；模型权重和训练数据单独许可 | 改造复用 | 独立资源配置和生命周期；CPU/GPU Profile；禁止全局加载泄漏 | `src/ragflow_agent/infrastructure/ragflow_adapters/vision/` |
| `deepdoc/vision/ocr.py` | `OCR`、`TextDetector`、`TextRecognizer` | `snapshot_download("InfiniFlow/deepdoc")`、ONNX Runtime、OpenCV、NumPy、设备/并发和本地模型目录 | 极高 | 源码 Apache-2.0；Hugging Face 仓库快照、ONNX 权重、词表和训练数据另行核验 | 改造复用 | 通过 OCRPort 注入模型目录、设备和生命周期；输出文字、置信度和 bbox | `src/ragflow_agent/infrastructure/ragflow_adapters/vision/ocr.py` |
| `deepdoc/vision/layout_recognizer.py` | `LayoutRecognizer`、`LayoutRecognizer4YOLOv10` | `snapshot_download("InfiniFlow/deepdoc")`、Recognizer、ONNX、NMS/坐标后处理、版面标签 | 极高 | 源码 Apache-2.0；模型权重、标签资源和原生推理库独立审计 | 改造复用 | 把模型加载和后处理拆开；经 LayoutPort 输出规范化 block type/bbox/confidence | `src/ragflow_agent/infrastructure/ragflow_adapters/vision/layout.py` |
| `deepdoc/vision/table_structure_recognizer.py` | `TableStructureRecognizer` | `snapshot_download("InfiniFlow/deepdoc")`、Recognizer、ONNX、OpenCV、表格单元格后处理 | 极高 | 源码 Apache-2.0；模型权重、词表/标签、原生库及训练数据独立审计 | 改造复用 | 通过 TableStructurePort 注入资源；输出 cell/row/column/bbox 和来源关系 | `src/ragflow_agent/infrastructure/ragflow_adapters/vision/table_structure.py` |
| `rag/app/naive.py` | `by_deepdoc`、`by_plaintext`、`chunk`、`Docx`、`Pdf`、`Markdown` | DeepDOC、LLMBundle、tenant model service、Parser 配置、RAG tokenizer、VisionFigureParser、多种外部 Parser | 极高 | Apache-2.0；每个外部 Parser 单独审计 | 改造复用 | 拆成“Parser 选择”和“GeneralChunkStrategy”；不保留 Tenant/LLMBundle 导入 | `src/ragflow_agent/parsing/registry.py`、`src/ragflow_agent/chunking/general.py` |
| `rag/app/paper.py` | `Pdf`、`chunk` | DeepDOC PdfParser、naive PARSERS、RAG tokenizer、版面和图片上下文 | 高 | Apache-2.0；保留修改说明 | 改造复用 | 只提取论文标题/章节/参考文献和 Chunk 规则 | `src/ragflow_agent/chunking/paper.py` |
| `rag/app/book.py` | `Pdf`、`chunk` | PdfParser、RAG tokenizer、章节规则 | 高 | Apache-2.0 | 改造复用 | 映射 ParsedDocument heading path；去除上游字段约定 | `src/ragflow_agent/chunking/book.py` |
| `rag/app/manual.py` | `Pdf`、`Docx`、`chunk` | PDF/DOCX Parser、outline、RAG tokenizer、图片上下文、naive PARSERS | 高 | Apache-2.0 | 改造复用 | 提取手册章节、问句层级、表图上下文规则 | `src/ragflow_agent/chunking/manual.py` |
| `rag/app/laws.py` | `Docx`、`Pdf`、`chunk` | PDF/DOCX Parser、条款识别、RAG tokenizer | 高 | Apache-2.0 | 改造复用 | 提取法规条款层级算法，输出通用 heading_path | `src/ragflow_agent/chunking/laws.py` |
| `rag/app/qa.py` | `Excel`、`Pdf`、`Docx`、`chunk` | 多 Parser、问答字段规则、RAG tokenizer | 高 | Apache-2.0 | 改造复用 | 统一为 QAChunkStrategy，显式验证 question/answer | `src/ragflow_agent/chunking/qa.py` |
| `rag/app/table.py` | `Excel`、`column_data_type`、`chunk` | KnowledgebaseService、settings、ExcelParser、pandas、NumPy、日期解析 | 极高 | Apache-2.0；第三方库单独核查 | 改造复用 | 只保留列名去重、类型推断和行 Chunk；删除 Service/settings | `src/ragflow_agent/chunking/table.py` |
| `rag/app/picture.py` | `chunk`、`vision_llm_chunk` | LLMBundle、tenant model service、OCR、Vision model、临时文件 | 极高 | Apache-2.0；OCR/Vision 模型单独许可 | 改造复用 | 通过 VisionModelPort/OCRPort 注入；输出 ImageBlock/Chunk | `src/ragflow_agent/infrastructure/ragflow_adapters/parsing/image.py` |
| `rag/app/audio.py` | `chunk` | ASR 模型、LLMBundle 或模型服务、tokenizer | 高 | Apache-2.0；ASR 模型单独许可 | 改造复用 | 使用 LangChain/模型 Adapter 的 TranscriptionPort | `src/ragflow_agent/infrastructure/ragflow_adapters/parsing/audio.py` |
| `rag/app/email.py` | `chunk` | 邮件解析、附件、tokenizer | 中 | Apache-2.0；附件解析依赖单独核查 | 改造复用 | 分离 header/body/attachment，保留来源关系 | `src/ragflow_agent/infrastructure/ragflow_adapters/parsing/email.py`、`src/ragflow_agent/chunking/email.py` |
| `rag/svr/task_executor_refactor/chunk_builder.py` | `get_parser`、`run_chunking` | `rag.app.*`、TaskContext、线程池、ParserType | 中 | Apache-2.0 | 参考重写 | 用 ParserRegistry/ChunkStrategyRegistry 替代模块级 factory | `src/ragflow_agent/parsing/registry.py`、`src/ragflow_agent/chunking/registry.py` |
| `rag/svr/task_executor_refactor/chunk_post_processor.py` | `extract_keywords`、`generate_questions`、`generate_metadata`、`apply_tags` | TaskContext、LLMBundle、Prompt、settings、Service、Chunk 字典 | 高 | Apache-2.0；Prompt 也要保留来源 | 参考重写 | 使用 EnrichmentPort 和明确 DTO；每项增强独立开关和错误策略 | `src/ragflow_agent/enrichment/` |
| `rag/svr/task_executor_refactor/chunk_service.py` | `build_chunks`、`insert_chunks` | settings、TaskService、TaskContext、ChunkBuilder、post processor、DocStore、对象存储、RAPTOR | 极高 | Apache-2.0 | 参考重写 | 保留阶段顺序；由 IngestionService 调用各端口，不复制大类 | `src/ragflow_agent/ingestion/service.py` |
| `rag/svr/task_executor_refactor/embedding_service.py` | `EmbeddingService.embed_chunks` | settings、TaskContext、EmbeddingUtils、线程池、RAGFlow Chunk 字典 | 高 | Apache-2.0 | 参考重写 | LangChain Embeddings + EmbeddingPort；显式输入/输出和版本 | `src/ragflow_agent/embedding/service.py` |
| `rag/nlp/query.py` | `FulltextQueryer`、term weight、synonym | QueryBase、MatchTextExpr、RAG tokenizer、Redis cache | 高 | Apache-2.0；同义词资源单独核查 | 改造复用 | 抽取词法权重和查询分析；替换 Redis/global tokenizer | `src/ragflow_agent/retrieval/fulltext.py` |
| `rag/nlp/search.py` | `Dealer.search`、`retrieval`、`rerank`、`rerank_by_model`、`insert_citations` | settings、DocStore 表达式、query/tokenizer、NumPy、字段常量、具体后端分支 | 极高 | Apache-2.0 | 改造复用 | 拆为 CandidateRetriever、Cleaner、Fusion、Reranker、CitationMatcher；后端逻辑进 Adapter | `src/ragflow_agent/retrieval/`、`src/ragflow_agent/citations/` |
| `common/doc_store/doc_store_base.py` | `MatchTextExpr`、`MatchDenseExpr`、`FusionExpr`、`DocStoreConnection` | NumPy、RAGFlow 字段约定 | 中 | Apache-2.0 | 参考重写 | 定义本项目 Filter AST、SearchRequest 和 SearchPort，不沿用字段名 | `src/ragflow_agent/knowledge/ports/search.py` |
| `rag/prompts/generator.py` | `kb_prompt`、`citation_prompt`、`keyword_extraction`、`question_proposal`、`full_question`、`cross_languages`、`gen_meta_filter` | RAG tokenizer、Prompt loader、Jinja sandbox、json_repair、Token 工具 | 中至高 | Apache-2.0；Prompt 文本属于上游作品，保留来源 | 改造复用 | Prompt 独立版本化；LangChain Prompt/Structured Output；替换 Tokenizer | `src/ragflow_agent/generation/prompts/`、`src/ragflow_agent/retrieval/query_processing.py` |
| `common/metadata_utils.py` | `apply_meta_data_filter`、`_run_metadata_filter` | LLM 生成、文档 metadata、RAGFlow 条件结构 | 高 | Apache-2.0 | 参考重写 | 建立严格 Filter AST 和 allowlist；禁止直接执行模型输出 | `src/ragflow_agent/retrieval/filters.py` |
| `agent/tools/retrieval.py` | `RetrievalParam`、`Retrieval._retrieve_kb` | Canvas、KnowledgebaseService、DocMetadataService、LLMBundle、settings、MemoryService、Prompt | 极高 | Apache-2.0 | 参考重写 | 保留 Tool 参数和共享 Retriever 思路；用 LangChain Tool 调 KnowledgeQueryService | `src/ragflow_agent/agent/tools/knowledge_base.py` |
| `agent/canvas.py` | `Graph`、`Canvas.run`、`Canvas._run_impl` | Component system、FileService、LLMBundle、TaskService、Redis、TTS、Langfuse | 极高 | 若复制仍须 Apache-2.0；当前不复制 | 参考重写 | 只提取事件、取消和引用需求；用 LangGraph 重建 | `src/ragflow_agent/agent/graph/` |
| `rag/advanced_rag/agentic_rag_graph.py` | `AgenticState`、`build_agentic_graph`、`run_agentic_rag` | LangGraph、RAGTools、harness、Prompt、Token queue | 高 | Apache-2.0 | 参考重写 | 参考问题规范化、路由、预检索、规划和证据充分性；增加 Checkpoint/HITL | `src/ragflow_agent/agent/graphs/agentic_rag.py` |
| `rag/advanced_rag/agentic_rag.py` | `RAGTools` | Dialog/KB/model Service、Dealer、Web/structured retrieval、Prompt | 极高 | Apache-2.0 | 参考重写 | 将每项能力变为应用服务或 LangChain Tool；不保留 Service 导入 | `src/ragflow_agent/agent/tools/` |
| `rag/graphrag/general/index.py`、`rag/graphrag/checkpoints.py`、`rag/graphrag/phase_markers.py` | `run_graphrag_for_kb`、`generate_subgraph`、`merge_subgraph`、`resolve_entities`、`extract_community`、checkpoint/marker 函数 | DocumentService、TaskService、settings、DocStore、Redis lock/checkpoint、NetworkX、LLM、Embedding | 极高 | Apache-2.0；graspologic/networkx/模型单独审计 | 改造复用 | 保留算法阶段和恢复语义；替换 Service、lock、checkpoint、DocStore 和字段，并绑定 DocumentVersion | `src/ragflow_agent/advanced_rag/graphrag/` |
| `rag/graphrag/search.py` | `KGSearch` | Dealer、settings、DocStore、Prompt、pandas | 极高 | Apache-2.0 | 改造复用 | 从 Dealer 继承改为 AdvancedRetrieverPort 实现 | `src/ragflow_agent/advanced_rag/graphrag/retriever.py` |
| `rag/advanced_rag/knowlege_compile/raptor.py`、`rag/svr/task_executor_refactor/raptor_service.py` | `RecursiveAbstractiveProcessing4TreeOrganizedRetrieval`、`RaptorService._generate_raptor` | sklearn、umap、NumPy、TaskService cancel、LLM cache、token 工具、settings Retriever、DocStore 字段 | 高至极高 | Apache-2.0；sklearn/umap/模型单独审计 | 改造复用 | 只抽取聚类、树摘要和来源合并；注入 Clusterer、Summarizer、CancellationToken，写入/清理/版本完全重建 | `src/ragflow_agent/advanced_rag/raptor/` |
| `api/db/init_data/compilation_templates/timeline.yaml`、`rag/advanced_rag/knowlege_compile/runner.py`、`rag/advanced_rag/knowlege_compile/structure.py` | timeline template；`runner.run_structure_compile_over_batches/_compile_batch/_flush`；`structure.compile_structure_from_text/merge_compiled_structures/cleanup_timeline_isolated_entities` | Knowledge compilation Schema、LLM、Prompt、实体/关系合并和清理；不包含数值时序存储与窗口检索 | 高 | Apache-2.0；Prompt/模板保留上游归属；模型与目标时序后端另审计 | 参考重写 | 只提取事件时间线 Schema、编译和清理思想；自行设计时序数据模型、窗口/聚合查询、权限、Citation、版本与评测，不复制为完整时序引擎 | `src/ragflow_agent/advanced_rag/timeseries/` |
| `api/db/db_models.py` | Tenant、UserTenant、Knowledgebase、Document、Task、Dialog、Conversation、UserCanvas | Peewee、RAGFlow 枚举和 tenant/user/owner 混合产品语义 | 极高 | Apache-2.0；当前不复制 | 参考重写 | 依据目标领域重新设计 SQLAlchemy 模型；显式拆分 tenant_id、owner_id、visibility，不复制 me/team 模型 | `src/ragflow_agent/knowledge/domain/`、`src/ragflow_agent/infrastructure/database/` |
| `api/utils/api_utils.py` | `add_tenant_id_to_kwargs` | Quart/current_user、装饰器、用户 ID 被命名为 tenant_id | 中 | Apache-2.0；当前不复制 | 参考重写 | 只把“认证后注入上下文”作为需求；使用 FastAPI dependency 构造不可被请求覆盖的 AuthorizationContext | `src/ragflow_agent/api/dependencies/auth.py`、`src/ragflow_agent/security/context.py` |
| `api/db/services/knowledgebase_service.py`、`api/common/check_team_permission.py` | `_visibility_and_status_filter`、`accessible`、`check_kb_team_permission` | Peewee、TenantService、UserTenant、me/team permission、状态枚举 | 极高 | Apache-2.0；当前不复制 | 参考重写 | 提取访问用例测试；用 PermissionChecker 和 Repository/Search tenant 约束重建，不复制分散检查 | `src/ragflow_agent/security/permissions.py`、`src/ragflow_agent/knowledge/ports/permissions.py` |
| `api/db/services/file_service.py` | `upload_document`、`delete_docs` | Peewee、对象存储全局、Document/File Service | 极高 | Apache-2.0；当前不复制 | 参考重写 | 拆为 DocumentLifecycleService、Repository、ObjectStoragePort | `src/ragflow_agent/lifecycle/` |
| `api/db/services/document_service.py` | `run`、`do_cancel`、`remove_document`、`delete_chunk_images` | Peewee、settings、Redis、DocStore、TaskService、FileService | 极高 | Apache-2.0；当前不复制 | 参考重写 | 用 DocumentVersion/IngestionJob 和补偿状态机重建 | `src/ragflow_agent/lifecycle/`、`src/ragflow_agent/ingestion/` |
| `api/db/services/task_service.py` | `queue_tasks`、`get_task`、`do_cancel`、`has_canceled`、`cancel_all_task_of` | Peewee、Redis Streams、settings、Parser 配置；Task tenant 依赖联查 | 极高 | Apache-2.0；当前不复制 | 参考重写 | 同仓库 IngestionQueuePort + IngestionJobRepository；消息只含稳定 tenant/job/version 身份；Phase 04 采用 Redis/ARQ | `src/ragflow_agent/knowledge/ports/queue.py`、`src/ragflow_agent/knowledge/application/ingestion.py` |
| `rag/utils/redis_conn.py` | `RedisMsg.ack`、`queue_product`、`queue_consumer`、`get_unacked_iterator` | redis-py、Redis Streams、进程连接和日志 | 高 | Apache-2.0；redis-py 单独登记 | 参考重写 | 只作为可靠性反例/需求证据；Phase 04 未复制 Redis Streams，而是通过 QueuePort 独立实现 ARQ Adapter | `src/ragflow_agent/knowledge/infrastructure/queue/arq.py` |
| `rag/svr/task_executor.py` | `collect`、`handle_task`、`main` | settings、Redis、Service、模型、Parser、DocStore、进程全局；异常后仍最终 ACK | 极高 | Apache-2.0；当前不复制 | 参考重写 | 采用独立 Worker 入口；只参考 pending、并发、心跳和取消，禁止复制无条件 ACK | `src/ragflow_agent/bootstrap/ingestion_worker.py`、`src/ragflow_agent/ingestion/worker.py` |
| `docker/launch_backend_service.sh` | `run_server`、`task_exe`、进程启动选择 | Bash、环境变量、进程监督、可选 Go 路径 | 高 | Apache-2.0；当前不复制；Go 路径范围外 | 参考重写 | 仅作为同仓库 API/Worker 分进程证据；为目标项目分别提供 Python 入口和部署命令 | `src/ragflow_agent/bootstrap/api.py`、`src/ragflow_agent/bootstrap/ingestion_worker.py`、`deployments/` |
| `api/db/services/dialog_service.py` | `async_chat`、`rag_agent`、引用修复 | Peewee Service、LLMBundle、settings、Dealer、Prompt、metadata、Langfuse | 极高 | Apache-2.0；当前不复制 | 参考重写 | 拆为 Query、FixedRAG、Citation 和 Agent 服务 | `src/ragflow_agent/retrieval/`、`src/ragflow_agent/generation/`、`src/ragflow_agent/agent/` |
| `api/db/services/llm_service.py` | `LLMBundle` | Tenant model、各模型实现、Token usage、Langfuse | 极高 | Apache-2.0；当前不复制 | 参考重写 | 使用 LangChain 标准模型；自行实现注册、配额和审计 | `src/ragflow_agent/infrastructure/models/` |
| `common/settings.py` | `StorageFactory`、`init_settings`、全局连接 | 所有数据库、存储、搜索、Redis、Retriever | 极高 | Apache-2.0；当前不复制 | 参考重写 | 使用显式配置和依赖注入；禁止业务代码访问全局连接 | `src/ragflow_agent/config/`、应用 bootstrap |

## 3. 当前结论

### 3.1 可优先做最小实验的候选

以下只是抽取实验顺序，不是批准直接复用：

1. `deepdoc/parser/ppt_parser.py`
2. `deepdoc/parser/docx_parser.py`
3. `deepdoc/parser/excel_parser.py`
4. `rag/app/paper.py` 的纯 Chunk 规则
5. `rag/app/manual.py` 的纯 Chunk 规则
6. `rag/advanced_rag/knowlege_compile/raptor.py` 的聚类核心

### 3.2 最不应直接复制的文件

1. `common/settings.py`
2. `rag/svr/task_executor.py`
3. `api/db/services/document_service.py`
4. `api/db/services/dialog_service.py`
5. `agent/canvas.py`
6. `api/db/db_models.py`
7. `api/db/services/knowledgebase_service.py` 的权限实现
8. `rag/utils/redis_conn.py` 与 `task_executor.py` 的 ACK/重试组合

已确认的“模块化单体 + 独立 Ingestion Worker”不改变上述复用分类：RAGFlow 的同仓库分进程设计可作拓扑证据，但 Peewee Task、全局 settings、Redis 连接和无条件 ACK 不能进入目标领域核心。第一版权限模型同样只参考其 tenant/team 用例，不复用 tenant/user/owner 混合语义。

## 4. 抽取流程

每个候选必须按顺序完成：

1. 固定上游 commit 和源文件 blob。
2. 记录源文件、符号、调用者和被调用者。
3. 列出 Python 包、模型权重、资源文件、环境变量、数据库、Redis、对象存储和搜索依赖。
4. 建立上游行为测试或黄金样本。
5. 确定目标端口和 DTO。
6. 移除 `common.settings`、Peewee、Quart、Canvas 和全局连接。
7. 保留许可证头并增加修改声明。
8. 添加 provenance 记录。
9. 运行单元、契约、集成和许可证检查。
10. 只有通过评审后，能力矩阵分类才可改为“直接复用”或保持“改造复用”。

## 5. Provenance 记录格式

每个复用模块至少记录：

```yaml
upstream_repository: https://github.com/infiniflow/ragflow
upstream_commit: cd846cc9d4e32a19e684c59a1f302601027ef976
upstream_path: rag/app/paper.py
upstream_symbols:
  - Pdf
  - chunk
license: Apache-2.0
adoption: modified
modifications:
  - removed RAGFlow tokenizer dependency
  - replaced parser dictionary with ParsedDocument
third_party_dependencies: []
tests:
  - tests/contract/parsing/test_paper_chunker.py
```

实际文件名和测试路径在实现时填写，不能把示例当成已经存在。

## 6. 许可证门禁

冻结 commit 根目录存在 `LICENSE`，内容为 Apache License 2.0；该根目录未发现 `NOTICE`。这只说明上游源码主许可证事实，不自动覆盖第三方包、远程下载的模型/资源、原生二进制或测试样本。Apache-2.0 第 4 节的最低执行要求在本项目中落为：

1. 向源码或二进制接收者提供 Apache-2.0 许可证副本。
2. 修改过的上游文件携带显著修改说明。
3. 在源码形式的派生作品中保留适用的版权、专利、商标和归属声明。
4. 若未来采用的上游基线出现 `NOTICE`，分发时按许可证要求保留其中适用归属；当前“无 NOTICE”不能固化为未来事实。

除上述要求外，合入前还必须检查：

1. 第三方 Python 包许可证和版本，包括但不限于 ONNX Runtime、OpenCV、XGBoost、scikit-learn、umap-learn、graspologic、NetworkX、PDF/Office 解析库和数据库客户端。
2. OCR、Embedding、Reranker、Vision、ASR 模型权重许可证、模型卡限制和商用/再分发条件。
3. `snapshot_download` 等远程资源的精确仓库、revision、文件 hash 和许可证；冻结源码已发现 `InfiniFlow/deepdoc` 与 `InfiniFlow/text_concat_xgb_v1.0` 下载点。
4. 原生二进制、字体、词表、同义词、标签文件和模型资源的再分发条件。
5. 测试文档、图片、音频、邮件、字体和样本数据的使用权及脱敏证明。
6. 容器镜像、操作系统包和外部服务的许可证/SBOM。

任何一项不明确时，分类保持“参考重写”或停止引入。

### 6.1 许可证与资源审计状态

| 层级 | 当前已确认 | 当前未确认/门禁 |
|---|---|---|
| RAGFlow 源码 | 冻结 commit 根 `LICENSE` 为 Apache-2.0；根目录无 `NOTICE` | 任何滚动基线都要重新检查 LICENSE/NOTICE；复制范围尚未获批 |
| Python 依赖 | `pyproject.toml` 可定位版本或约束 | 每个候选的实际闭包、传递依赖、许可证兼容性和漏洞状态 |
| DeepDOC 模型 | 源码调用 `snapshot_download`，可定位 `InfiniFlow/deepdoc`、`InfiniFlow/text_concat_xgb_v1.0` | 权重/词表/训练数据的精确 revision、文件 hash、商用和再分发条件 |
| Provider 模型 | Phase 04 已选 DeepSeek `deepseek-chat` 与 `BAAI/bge-m3`，仅通过 Provider Adapter 配置 | 服务条款、数据驻留、输出使用限制、真实模型性能；Reranker/OCR/Vision/ASR 仍待后续阶段 |
| 原生与容器 | 可从 pyproject、Docker/Helm 定位 ONNX/OpenCV/搜索/对象存储等依赖 | 平台二进制、镜像层、SBOM、CVE、许可证文本与发布包归属 |
| 数据与素材 | 未批准复用上游 benchmark 文档或模型样本 | 每份黄金样本、轨道交通资料、图片/音频/字体的授权和脱敏 |

### 6.2 Phase 04 实际复用审计

- **直接复用**：0 个 RAGFlow 文件/函数。
- **改造复用**：0 个 RAGFlow 文件/函数。
- **参考重写/自行开发**：上传顺序、任务边界、Parser/Chunk 职责、Embedding→Index 顺序、检索和固定回答调用关系只作为 frozen commit 行为证据；目标代码位于 `knowledge/application` 与 `knowledge/infrastructure`。
- **第三方依赖**：pypdf、ARQ/redis-py、Elasticsearch Client、LangChain OpenAI Adapter 和 boto3 按本项目依赖直接使用，不是从 RAGFlow 抽取。
- **许可结论**：Phase 04 没有 RAGFlow 派生源码分发义务；后续首次复制或修改上游文件前，必须重新打开 O-004/许可证 ADR，登记精确文件、修改、NOTICE 和传递资源。

### 6.3 Phase 05 实际复用审计

- **直接复用**：0 个 RAGFlow 文件/类/函数。
- **改造复用**：0 个 RAGFlow 文件/类/函数。
- **参考范围**：`deepdoc/parser/{pdf,docx,ppt,excel}_parser.py`、
  `deepdoc/vision/{ocr,layout_recognizer,table_structure_recognizer}.py`、
  `chunk_builder.py::get_parser/run_chunking` 和
  `rag/app/{naive,paper,book,manual,laws,qa,table,resume,picture}.py::chunk`
  只用于职责、依赖图和行为目标核对。
- **独立实现**：Parser/OCR/Chunk 代码全部位于本项目
  `knowledge/{application,infrastructure,ports,domain}`；使用
  python-docx、python-pptx、openpyxl、pdfplumber、pypdfium2、Pillow、
  pytesseract、BeautifulSoup、markdown-it-py 等公开第三方接口。
- **隔离层结论**：因为没有 RAGFlow 派生代码，本阶段不创建空的
  `ragflow_adapters` 包；后续首次复制/修改上游代码时仍必须通过该隔离层并
  重新打开 O-004。
- **证据**：[Phase 05 许可与资源基线](./research/phase-05-parser-license-and-resource-baseline.md)、
  [Phase 05 执行记录](./phases/phase-05-parser-and-chunk.md)。

### 6.4 Phase 06 实际复用审计

- **直接复用**：0 个 RAGFlow 文件/类/函数。
- **改造复用**：0 个 RAGFlow 文件/类/函数；没有创建
  `knowledge/infrastructure/ragflow_adapters/retrieval/`。
- **参考后自研**：查询变体、Filter AST、Elasticsearch 双通道、RRF、候选清理、
  Reranker 回退、安全降级、Citation/Context 接线和 PostgreSQL Retrieval Trace。
- **源码边界**：只以冻结 commit 的 `FulltextQueryer`、`Dealer.search/retrieval`、
  `generator.py` 查询变换、metadata 哨兵和 Citation 调用顺序作为行为证据；没有
  复制 Prompt、算法片段、注释、测试或上游依赖图。
- **许可证结果**：未形成 RAGFlow 派生源码分发；第三方运行时只通过
  `pyproject.toml`/`uv.lock` 管理。首次复制或修改上游源码前仍必须重开 O-004
  许可证审查并通过隔离层。
- **证据**：[Phase 06 执行记录](./phases/phase-06-online-retrieval.md)、
  [Phase 06 评测](./research/phase-06-retrieval-evaluation.md)、ADR-021。

### 6.5 Phase 07 实际复用审计

- **直接复用/改造复用**：均为 0 个 RAGFlow 文件、类或函数。
- **参考后自研**：只把 `document_api.update_document/parse_documents/delete_documents`、`DocumentService.run/remove_document/delete_chunk_images/clear_chunk_num_when_rerun`、`TaskService.cancel_all_task_of/has_canceled`、Redis pending/requeue、`task_executor.handle_task` 和 `Dealer._prune_deleted_chunks` 作为职责、失败顺序和反例证据。
- **独立实现**：版本、Outbox、候选索引/alias、CAS 激活、删除/恢复/回收、重试/死信、进度/取消、批量和 reconciliation 均位于本项目 `knowledge`/`worker` 模块。
- **许可证结果**：Phase 07 未形成 RAGFlow 派生源码；O-004 继续按“首次复制/修改前重开审查”闭环，ADR-022 记录本阶段边界。
- **证据**：[Phase 07 执行记录](./phases/phase-07-document-lifecycle.md)、[生命周期设计](./09-document-lifecycle.md)、ADR-022。

### 6.6 Phase 08 实际复用审计

- **直接复用/改造复用**：均为 0 个 RAGFlow 文件、类或函数；没有创建 Phase 08 `ragflow_adapters`。
- **参考后自研**：只把 `Retrieval._retrieve_kb`、`RAGTools`、`AgenticState/build_agentic_graph` 和 Canvas user-input 行为作为 Tool 能力、节点与人工输入用例证据。
- **独立实现**：直接 RAG/KB Tool 共享 Gateway、LangGraph Agentic 图、Tool Registry、SQL/API 安全、HITL、Memory、Evidence、Budget、Agent Trace 和评测均位于本项目 `agent` 模块。
- **许可证结果**：Phase 08 未形成 RAGFlow 派生源码；首次复制或修改上游源码前仍须重开 O-004，登记精确来源、许可证、NOTICE 和隔离方案。
- **证据**：[Phase 08 执行记录](./phases/phase-08-agentic-rag.md)、[Agentic RAG运行时](./10-agentic-rag.md)、ADR-023。

## 7. 与能力和阶段的关系

- Phase 00：完成源码、依赖和许可证登记，不做抽取实验，不合入业务实现。
- Phase 04：已完成；只参考最小 RAG 闭环所需的 Parser/Chunk/检索行为，未引入 RAGFlow 源码。
- Phase 05：已完成；研究 DeepDOC、OCR、多格式和场景化 Chunk Method，但实际 RAGFlow 直接/改造复用均为零，全部独立实现。
- Phase 06：已完成；研究 FulltextQueryer、Dealer、Prompt、过滤、融合、Rerank 和 Citation，但实际 RAGFlow 直接/改造复用均为零，全部独立实现。
- Phase 07：已完成；研究更新/重解析/删除/任务取消与 ACK 缺口，版本、一致性和可靠任务能力全部独立实现。
- Phase 08：已完成；只参考 Agent Retrieval Tool、Agentic RAG 和 Canvas 人工输入用例，未引入 Canvas 或任何 RAGFlow 源码。
- Phase 09：GraphRAG、RAPTOR、多模态和时序均已独立实现；RAGFlow 直接/改造复用代码为零，冻结源码只作公开行为与架构证据。

阶段依赖和验收门禁见[开发路线图](./05-development-roadmap.md)。
