---
document_id: RAGFLOW-SOURCE-MAP
status: active
last_updated_at: "2026-07-30"
ragflow_frozen_baseline_commit: "cd846cc9d4e32a19e684c59a1f302601027ef976"
scope: RAGFlow Python
phase: "Phase 00"
---

# RAGFlow Python 源码证据地图

## 1. 用途与证据规则

本文记录 Phase 00 实际读取的 RAGFlow Python 源码、核心符号、调用关系、持久化副作用和目标项目采用边界。它是[项目总纲](../00-project-master.md)、[RAGFlow 架构](../01-ragflow-architecture.md)、[能力矩阵](../02-ragflow-capability-matrix.md)和[复用策略](../04-code-reuse-strategy.md)的底层证据索引，不替代这些文档。

- 所有上游链接固定到 commit [`cd846cc9d4e32a19e684c59a1f302601027ef976`](https://github.com/infiniflow/ragflow/tree/cd846cc9d4e32a19e684c59a1f302601027ef976)。
- `D:/ragflow/ragflow-main` 只用于文件存在性和辅助搜索；其内容与冻结 commit 有混合差异，不作为冻结事实来源。
- “调用关系”只记录源码中可定位的调用、构造或字段读写；目录名推断不算证据。
- 本项目未批准直接复制任何 RAGFlow 源文件；表中的“采用边界”只是研究结论。

## 2. P00-T03：架构、数据与依赖

### 2.1 启动和全局初始化

| 证据 ID | 源文件与符号 | 实际调用关系和副作用 | 内部/外部依赖 | 采用边界 |
|---|---|---|---|---|
| RF-A01 | [`api/ragflow_server.py::settings.init_settings`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/api/ragflow_server.py#L96) | API 进程启动时先初始化设置；随后调用 `init_web_data()`，最终运行 Quart 应用。 | Quart、数据库初始化、`common.settings` | API 启动顺序只作参考；目标项目使用 FastAPI composition root。 |
| RF-A02 | [`common/settings.py::init_settings`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/common/settings.py#L218) | 读取服务配置；按 `DOC_ENGINE` 动态构造 `ESConnection`、`InfinityConnection`、`OSConnection` 或 OceanBase/SeekDB 连接；按 `STORAGE_IMPL_TYPE` 创建对象存储；最后构造全局 `search.Dealer(docStoreConn)` 和 `KGSearch(docStoreConn)`。 | `rag.utils.*_conn`、`StorageFactory`、模型/数据库配置 | 不复用全局单例；改为显式配置、端口和依赖注入。 |
| RF-A03 | [`common/settings.py::StorageFactory`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/common/settings.py#L202) | `create()` 从注册表选择 Azure、S3、MinIO、OSS、GCS、OpenDAL 等存储实现；`init_settings()` 将实例写入全局 `STORAGE_IMPL`。 | 各对象存储 SDK、加密存储包装 | 接口设计参考；目标项目以 `ObjectStoragePort` 隔离供应商实现。 |
| RF-A04 | [`common/settings.py::get_svr_queue_name`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/common/settings.py#L137) | 根据优先级和 suffix 生成任务队列名称，供 API/Worker 共享。 | 环境变量、Redis/Valkey | 队列命名和优先级只参考，不把全局设置引入领域层。 |

确认的进程边界：RAGFlow API、Task Executor 和 Agent/检索代码在同一 Python 仓库内，但 API 与 executor 可作为不同进程启动。目标项目采用同仓库的“模块化单体 FastAPI + 独立 Ingestion Worker”，不复制 RAGFlow 的 Quart 启动和全局初始化方式。

### 2.2 关系数据模型和 Chunk 存储边界

| 证据 ID | 源文件与符号 | 关键字段/关联 | 已确认事实 | 目标影响 |
|---|---|---|---|---|
| RF-D01 | [`api/db/db_models.py::Tenant`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/api/db/db_models.py#L722)、[`UserTenant`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/api/db/db_models.py#L748) | `UserTenant.tenant_id`；用户、租户和角色关系 | RAGFlow 已有租户和成员关系，但这不是目标项目 `AuthorizationContext`/`PermissionChecker` 的完整实现。 | 只参考实体关系；目标模型从首版强制 `tenant_id`。 |
| RF-D02 | [`Knowledgebase`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/api/db/db_models.py#L837) | `tenant_id`、`permission=me\|team`、`created_by`、`embd_id`、`parser_id`、`parser_config`、文档/Chunk/Token 统计 | 知识库是租户、解析和检索配置的聚合载体；`permission` 只有 `me\|team` 产品语义。 | 参考配置集合；目标项目分离 `tenant_id`、`owner_id`、`visibility`。 |
| RF-D03 | [`Document`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/api/db/db_models.py#L894) | `kb_id`、`parser_id`、`parser_config`、`created_by`、进度、Chunk/Token 统计 | `Document` 没有独立 `tenant_id`；租户需经 Knowledgebase 获取。 | 目标模型应冗余或强制携带 tenant scope，避免跨层漏过滤。 |
| RF-D04 | [`File`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/api/db/db_models.py#L924)、[`File2Document`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/api/db/db_models.py#L939) | `File.tenant_id`、`created_by`；文件到 Document 映射 | 对象存储文件元数据和知识库 Document 分开维护。 | 参考生命周期关系；目标端口需保证元数据与对象一致性。 |
| RF-D05 | [`Task`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/api/db/db_models.py#L1002) | `doc_id`、页范围、任务类型、进度、`retry_count` | `Task` 没有独立 `tenant_id`；消费时依赖 Document/Knowledgebase 联查。 | 目标任务信封必须显式携带 tenant 和幂等标识。 |
| RF-D06 | [`Dialog`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/api/db/db_models.py#L1020)、[`Conversation`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/api/db/db_models.py#L1056) | Dialog 持有租户、知识库和检索/生成配置；Conversation 持有消息和引用 | 固定 RAG 的配置与会话分离。 | 参考会话聚合；目标项目用统一 Retrieval Trace/Citation 类型。 |
| RF-D07 | [`common/doc_store/doc_store_base.py::DocStoreConnection`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/common/doc_store/doc_store_base.py#L148) | `create_idx/search/insert/update/delete` 和结果解析接口 | `db_models.py` 不存在同级关系型 `Chunk` 模型；Chunk 以搜索文档形式写入 DocStore。 | 目标领域定义 `ChunkRecord`，存储适配器负责搜索索引映射。 |

关系主链为 `Tenant → Knowledgebase → Document → Task`；源文件关系为 `File ↔ File2Document ↔ Document`。搜索 Chunk 不应被误写成 Peewee 数据表。

### 2.3 DocStore 和搜索表达式

| 证据 ID | 源文件与符号 | 能力 | 已确认实现差异 | 采用边界 |
|---|---|---|---|---|
| RF-S01 | [`doc_store_base.py::MatchTextExpr/MatchDenseExpr/MatchSparseExpr/MatchTensorExpr/FusionExpr`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/common/doc_store/doc_store_base.py#L58) | 全文、稠密向量、稀疏向量、张量和融合的中间表达式 | 表达式由各 DocStore 方言转换，字段命名仍是 RAGFlow 索引约定。 | 改造复用或参考重写为目标 `SearchQuery`；不得泄漏后端 DSL。 |
| RF-S02 | [`rag/utils/es_conn.py::ESConnection.search`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/utils/es_conn.py#L136) | ES 条件、全文、向量、分页、排序和聚合查询；另有批量 `insert/update/delete`。 | 继承 `ESConnectionBase`，使用 RAGFlow mapping、索引命名和字段约定。 | 参考重写搜索适配器；不直接抽取整个连接类。 |
| RF-S03 | [`rag/utils/opensearch_conn.py::OSConnection.search`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/utils/opensearch_conn.py#L314) | OpenSearch BM25、KNN 和 hybrid pipeline；不可用时退化为 plain KNN。 | `OSConnection._init_hybrid_search()` 创建 normalization pipeline，weighted-sum 权重来自设置。 | 后端特性参考；目标降级和融合策略须显式、可追踪。 |
| RF-S04 | [`common/doc_store/infinity_conn_base.py::InfinityConnectionBase`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/common/doc_store/infinity_conn_base.py#L155) | 索引/表创建、全文与向量查询、批量写入、聚合和 SQL。 | Infinity 使用表模型和 DataFrame 结果，接口兼容但行为不完全等价于 ES/OpenSearch。 | 第一版搜索后端未决；只保留端口，不承诺多后端等价。 |

### 2.4 模型统一层

| 证据 ID | 源文件与符号 | 统一方法 | 具体 Provider 入口 | 采用边界 |
|---|---|---|---|---|
| RF-M01 | [`api/db/services/llm_service.py::LLMBundle`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/api/db/services/llm_service.py#L29) | `encode`、`encode_queries`、`similarity`、`describe`、`transcription`、`tts`、`async_chat*` | 租户模型解析、Token 统计、Langfuse | 不复用租户 Service；目标用 LangChain 标准模型接口并自研注册、审计和配额。 |
| RF-M02 | [`rag/llm/embedding_model.py::Base`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/llm/embedding_model.py#L145) | `encode`、`encode_queries` | 多供应商 Embedding 类 | LangChain 能覆盖主流标准适配；缺口按 Provider 单独补齐。 |
| RF-M03 | [`rag/llm/rerank_model.py::Base`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/llm/rerank_model.py#L28) | `similarity` | 多供应商 Reranker 类 | 以 LangChain Runnable/自定义接口封装，算法能力与供应商调用分离。 |
| RF-M04 | [`rag/llm/cv_model.py::Base`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/llm/cv_model.py#L60)、[`ocr_model.py::Base`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/llm/ocr_model.py#L30)、[`sequence2txt_model.py::Base`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/llm/sequence2txt_model.py#L32) | 图像描述、OCR、语音转文本 | MinerU、Paddle/OpenDataLoader、Mistral 及多种 Vision/ASR Provider | 多模态阶段按许可证和部署形态逐项选择，不整体复制。 |

### 2.5 基础设施依赖事实

冻结 commit 的 [`pyproject.toml`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/pyproject.toml) 与源码共同确认：

- Web/API：Quart、Quart-Auth、Quart-CORS、Quart-Schema；RAGFlow 本身不是目标项目的 FastAPI 实现。
- 关系数据库：Peewee；`db_models.py` 定义 MySQL、PostgreSQL 和 OceanBase 连接/锁实现。
- 搜索：Elasticsearch DSL、OpenSearch SDK、Infinity SDK；源码另含 OceanBase/SeekDB DocStore 路径。
- 对象存储：MinIO、Boto3/S3 以及设置注册的 Azure、OSS、GCS、OpenDAL 实现。
- 任务协调：`rag/utils/redis_conn.py` 封装 Redis/Valkey Stream、锁、pending 和 ACK。
- 文档/多模态：OpenCV、ONNX Runtime、PDF/Office 解析、OCR/视觉相关库；具体模型权重许可证不能由 Apache-2.0 仓库许可证代替。
- 编排：RAGFlow 冻结 commit 自身声明 `langgraph==1.2.0`，但其产品主 API、Canvas Agent 和离线 ingestion 并非统一由 LangGraph 驱动。

## 3. P00-T04：离线知识库构建链路

### 3.1 从上传到投递

| 证据 ID | 源文件与符号 | 调用关系 | 输入/持久化副作用 | 失败或边界 |
|---|---|---|---|---|
| RF-I01 | [`document_api.py::upload_document/_upload_local_documents`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/api/apps/restful_apis/document_api.py#L413) | 路由先读取 Knowledgebase 并调用 `check_kb_team_permission`；local 分支通过 thread pool 调 `FileService.upload_document`，web/empty 分支分别建档。 | 上传文件、tenant、KB、可选 Parser 配置；返回 Document 数据。 | local 上传可部分成功；这里只建档，不自动完成解析。 |
| RF-I02 | [`file_service.py::FileService.upload_document`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/api/db/services/file_service.py#L514) | `get_kb_folder/new_a_file_from_kb` → 对象存储 `put` → `DocumentService.insert` → `FileService.add_file_from_kb`。 | 写对象、Document、File 和 File2Document；按文件类型覆盖 picture/audio/presentation/email Parser。 | 跨对象存储与关系库没有单一事务；失败补偿必须单独设计。 |
| RF-I03 | [`document_api.py::_run_sync/parse_documents`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/api/apps/restful_apis/document_api.py#L1434) | 权限检查 → 状态重置/可选删除旧 Task、导航与索引 Chunk → `DocumentService.run`。 | reparse 可删除旧搜索 Chunk并重置统计；cancel 走 Redis cancel key。 | 删除旧索引后再排队存在中间态；Phase 07 必须定义候选版本切换。 |
| RF-I04 | [`document_service.py::DocumentService.run`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/api/db/services/document_service.py#L1181) | 向 Document dict 注入 `tenant_id`；有 `pipeline_id` 时调用 `queue_dataflow`，否则从 File2Document 取存储地址后调用 `queue_tasks`。 | 标准 ingestion 与自定义 dataflow 在这里分叉。 | tenant 不是 Document 原生字段，而是在投递前临时注入。 |
| RF-I05 | [`task_service.py::queue_tasks`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/api/db/services/task_service.py#L435) | PDF 按页、table 按行、其他单 Task → 计算 digest/复用旧任务 → 批量写 Task → `begin2parse` → seed Redis counter → `REDIS_CONN.queue_product`。 | PDF 默认每 12 页，paper 默认 22 页；`one`/KG/TOC 单大任务；table 每 3000 行；消息只含未完成 Task 的轻量字段。 | DB 写入和 Stream 投递不是原子事务；投递异常只 abort Redis counter。 |
| RF-I06 | [`redis_conn.py::RedisDB.queue_product`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/utils/redis_conn.py#L404) | JSON 序列化后调用 Redis Stream `XADD`。 | 队列是 Redis/Valkey Stream。 | 只有布尔结果；可靠性和重放在 P00-T07 进一步审计。 |

### 3.2 Worker、路由和标准执行

| 证据 ID | 源文件与符号 | 调用关系 | 输出/副作用 | 失败或边界 |
|---|---|---|---|---|
| RF-I07 | [`docker/launch_backend_service.sh`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/docker/launch_backend_service.sh#L90) | 可分别启动 `api/ragflow_server.py` 和一个或多个 `rag/svr/task_executor.py -i <task_id>`。 | 同仓库不同进程。 | 脚本中的 Go/binary 分支不在本项目研究或复现范围。 |
| RF-I08 | [`task_executor.py::collect`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/svr/task_executor.py#L223) | 先 `get_unacked_iterator`，再 `queue_consumer`；普通消息用 `TaskService.get_task` 联查 Document/KB/Tenant/模型上下文。 | 领取时 `TaskService.get_task` 增加 retry_count；无任务或已取消则 ACK。 | 队列消息不是完整业务真相，Worker 依赖数据库重载。 |
| RF-I09 | [`task_executor.py::handle_task`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/svr/task_executor.py#L1741) | `TE_RUN_MODE=0` → `TaskManager.run_refactored_task`；`1` 同时执行旧路径和 refactor dry-run；其他值走旧 `do_handle_task`。 | 更新全局任务统计、记录 PipelineOperationLog，函数末尾 ACK。 | 发生异常也会在记录失败进度后 ACK；不能直接采用为目标项目重试语义。 |
| RF-I10 | [`task_manager.py::TaskManager.run_refactored_task`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/svr/task_executor_refactor/task_manager.py#L58) | 原始 task + semaphore + callback → `TaskContext` → `TaskHandler.handle_task`。 | 把弱类型 dict 包装为 typed property facade，并携带 limiter/取消/进度/记录器。 | TaskContext 仍直接暴露 RAGFlow schema 与全局服务。 |
| RF-I11 | [`task_handler.py::TaskHandler.handle`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/svr/task_executor_refactor/task_handler.py#L207) | 绑定 Embedding → 建索引 → 按 memory、dataflow、RAPTOR、GraphRAG、structure/evaluation/reembedding/clone 或 standard 路由。 | 标准、dataflow 和高级任务共享 Worker 入口。 | GraphRAG/RAPTOR 只在此定位，算法在 P00-T09 深入。 |
| RF-I12 | [`TaskHandler._run_standard_chunking_impl`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/svr/task_executor_refactor/task_handler.py#L548) | 对象存储 get → `ChunkService.build_chunks` → `EmbeddingService.embed_chunks` → `ChunkService.insert_chunks` → table metadata/TOC → `DocumentService.increment_chunk_num` → 文档级后处理 → 完成进度。 | 写 Chunk 图片、向量字段、DocStore、Task.chunk_ids、Document/KB 统计与 metadata。 | 多资源副作用通过局部回滚和取消检查协调，不是完整事务。 |

### 3.3 Chunk 构建、增强、Embedding 和索引

| 证据 ID | 源文件与符号 | 实际顺序/算法 | 输出/副作用 | 采用判断 |
|---|---|---|---|---|
| RF-I13 | [`chunk_builder.py::get_parser/run_chunking`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/svr/task_executor_refactor/chunk_builder.py#L39) | parser_id 注册到 `rag.app.*` 模块；调用统一模块级 `chunk(filename,binary,from_page,to_page,lang,callback,kb_id,parser_config,tenant_id)`。 | 返回 RAGFlow Chunk dict。 | 注册表和调用契约可参考；输出必须适配 `ParsedDocument/ChunkRecord`。 |
| RF-I14 | [`chunk_service.py::ChunkService.build_chunks`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/svr/task_executor_refactor/chunk_service.py#L91) | 文件大小 → Parser/Chunk → outline → 稳定内容 hash ID/图片上传 → 自动关键词 → 自动问题 → metadata + built-in metadata → tags。 | Chunk dict 增加 `doc_id/kb_id/id/create_time/img_id/important_kwd/question_kwd/metadata_obj/tag`。 | 顺序作为行为蓝本；LLM 增强失败和成本边界需目标项目显式化。 |
| RF-I15 | [`embedding_service.py::EmbeddingService.embed_chunks`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/svr/task_executor_refactor/embedding_service.py#L58) | 准备 title/content → title 向量复制 → content 批量 encode/truncate → 按 `filename_embd_weight` 混合 → attach `q_<dim>_vec`。 | 返回 token_count 和 vector_size，并原地修改 Chunk。 | 算法参考重写；目标项目必须记录 Embedding 模型、维度和版本。 |
| RF-I16 | [`chunk_service.py::ChunkService.insert_chunks`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/svr/task_executor_refactor/chunk_service.py#L239) | 从 `mom` 建不可用 mother chunks → 按批插入 mother/main → 每批更新 `Task.chunk_ids`；Task 消失时删除已插入 Chunk/图片。 | `docStoreConn.insert/delete`、Task.chunk_ids、Chunk 图片。 | 局部回滚思路可参考；目标项目使用索引版本和幂等 Job。 |
| RF-I17 | [`post_processor.py::PostProcessor`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/svr/task_executor_refactor/post_processor.py#L42) | 索引后聚合 table metadata；可把异步生成的 TOC 作为额外 Chunk 插入并增加计数。 | 更新 Document metadata、插入 TOC Chunk。 | 必须区分主索引成功与派生物成功，避免统计漂移。 |
| RF-I18 | [`dataflow_service.py::DataflowService.run_dataflow`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/svr/task_executor_refactor/dataflow_service.py#L94) | 加载 Canvas DSL → `rag.flow.Pipeline.run` → 归一化 Chunk → Embedding → `ChunkService.insert_chunks` → 统计/日志。 | 自定义 ingestion 绕过标准 Parser/Chunk 注册表，但复用索引服务。 | 目标首版不引入 Canvas dataflow runtime；只参考可插拔 ingestion step。 |

### 3.4 格式 Parser、视觉能力和 Chunk Method

| 范围 | 源码证据 | 已确认行为 | 依赖/耦合 |
|---|---|---|---|
| PDF/OCR/Layout/Table | [`RAGFlowPdfParser`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/deepdoc/parser/pdf_parser.py#L56) → [`OCR`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/deepdoc/vision/ocr.py#L493)、[`LayoutRecognizer`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/deepdoc/vision/layout_recognizer.py#L33)、[`TableStructureRecognizer`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/deepdoc/vision/table_structure_recognizer.py#L30) | PDF 页面图像、OCR boxes、版面类别、表格结构、坐标和表/图产物；支持 ONNX/部分 Ascend 路径。 | pdfplumber、pypdf、ONNX Runtime、OpenCV、Hugging Face 资源、NumPy、scikit-learn、XGBoost、settings/tokenizer。 |
| DOCX | [`RAGFlowDocxParser`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/deepdoc/parser/docx_parser.py#L33) | 按段落、表格和图片抽取；图片以 LazyImage 传递。 | python-docx、Pandas、RAGFlow tokenizer/schema。 |
| XLS/XLSX/CSV | [`RAGFlowExcelParser`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/deepdoc/parser/excel_parser.py#L29) | workbook/worksheet、行数、HTML/Markdown/文本及 sheet 图片；table Chunk Method 按表头和每行生成 Chunk。 | openpyxl、Pandas；`rag/app/table.py` 直接写 Knowledgebase parser_config。 |
| PPT/PPTX | [`RAGFlowPptParser`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/deepdoc/parser/ppt_parser.py#L22) | 按 slide 顺序和 shape 位置提取文本/表格。 | python-pptx；当前读取路径未见 notes 专用输出，不能把“备注支持”写成已确认能力。 |
| 通用 naive | [`rag/app/naive.py::chunk`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/app/naive.py#L946) | DOCX、PDF、Excel/CSV、文本/代码、Markdown/HTML 等按格式分支；PDF 可选 DeepDOC、MinerU、Docling、OpenDataLoader、TCADP、PaddleOCR、SoMark、Mistral OCR 或 Plain/Vision。 | 高耦合 `LLMBundle`、tenant model service、RAG tokenizer、settings 和第三方 Parser。Go 代码文件扩展处理不属于本项目复现范围。 |
| 论文/书籍/手册/法规 | [`paper.py::chunk`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/app/paper.py#L134)、[`book.py::chunk`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/app/book.py#L63)、[`manual.py::chunk`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/app/manual.py#L137)、[`laws.py::chunk`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/app/laws.py#L167) | 论文抽标题/作者/摘要/章节；书籍移除目录并按层级或 token 合并；手册用 outline/问句层级；法规构建条款树。 | 共享 DeepDOC、naive Parser、RAG tokenizer/字段 schema。 |
| QA/表格 | [`qa.py::chunk`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/app/qa.py#L287)、[`table.py::chunk`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/app/table.py#L384) | QA 支持 Excel/CSV/TXT/PDF/DOCX 的问答结构；table 第一行/多级表头，按数据行 Chunk并推断类型。 | table 直接依赖 `KnowledgebaseService` 和 settings，不能作为纯 Chunker 直接抽取。 |
| 图片/音频/邮件 | [`picture.py::chunk`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/app/picture.py#L41)、[`audio.py::chunk`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/app/audio.py#L27)、[`email.py::chunk`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/app/email.py#L29) | 图片走 OCR/Vision 描述；音频走 `LLMBundle.transcription`；邮件解析 header/body，附件递归调用 naive。 | tenant 模型 Service、临时文件、Vision/ASR Provider、递归 Parser。 |

### 3.5 离线主链路结论

标准链路为：

`document_api.upload_document → FileService.upload_document → ObjectStorage + File/Document/File2Document → document_api.parse_documents/_run_sync → DocumentService.run → TaskService.queue_tasks → RedisDB.queue_product(XADD) → task_executor.collect → TaskService.get_task → TaskManager.run_refactored_task → TaskHandler.handle_task → _run_standard_chunking_impl → ChunkService.build_chunks → rag.app.*.chunk → ChunkPostProcessor → EmbeddingService.embed_chunks → ChunkService.insert_chunks → DocStoreConnection.insert → PostProcessor → DocumentService.increment_chunk_num/TaskService.update_progress → RedisMsg.ack`。

该链路证明 RAGFlow 具备完整 ingestion 能力，但也暴露对象存储、Peewee、Redis、DocStore、LLMBundle 和全局 settings 的强耦合。目标项目优先复用复杂 Parser/视觉算法，编排和持久化按端口参考重写。

## 4. P00-T05：在线检索、生成与引用链路

### 4.1 固定 RAG 入口和参数来源

| 证据 ID | 源文件与符号 | 调用关系/参数 | 已确认语义 |
|---|---|---|---|
| RF-Q01 | [`chat_api.py::session_completion`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/api/apps/restful_apis/chat_api.py#L1154) | 加载 Dialog/Conversation 后调用 `rag_agent`；`rag_agent` 在 reasoning 未启用时转调 `async_chat`。 | 固定 RAG 与 Agentic 路径共用 API 外壳，但运行链不同。 |
| RF-Q02 | [`dialog_service.py::async_chat`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/api/db/services/dialog_service.py#L572) | 从 Dialog 读取 `kb_ids`、`top_n`、`top_k`、`similarity_threshold`、`vector_similarity_weight`、reranker、Prompt、metadata filter、引用和空结果配置；绑定 Embedding/Rerank/Chat/TTS。 | 参数是产品模型字段，不是独立查询 DTO；目标项目统一为 `KnowledgeQuery`/`RetrievalPolicy`。 |
| RF-Q03 | [`dialog_service.py::get_models`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/api/db/services/dialog_service.py#L359) | 解析知识库 Embedding owner、Dialog tenant 的 Chat/Rerank/TTS 配置并构造 `LLMBundle`。 | 多租户模型归属与检索调用耦合；目标通过模型注册表和授权上下文解耦。 |

### 4.2 查询处理和 metadata 过滤

| 证据 ID | 源文件与符号 | 执行顺序/输出 | 风险和目标边界 |
|---|---|---|---|
| RF-Q04 | [`generator.py::full_question`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/prompts/generator.py#L254) | 多轮 refine 开启且有多于一个用户问题时，将 messages 改写为独立问题。 | Prompt/模型失败没有统一 query-transform event；目标记录输入、输出、模型和降级。 |
| RF-Q05 | [`generator.py::cross_languages`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/prompts/generator.py#L290) | 按配置语言生成跨语言查询；LLM 错误时回退原查询。 | 可参考 Prompt 与回退，输出需结构化为 query variants。 |
| RF-Q06 | [`metadata_utils.py::apply_meta_data_filter`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/common/metadata_utils.py#L153) | auto/semi 调 `gen_meta_filter`，manual 直接使用条件；优先 `DocMetadataService` push-down，失败回退 Python `meta_filter`。 | 操作符包括 contains/not contains/in/not in/start/end/empty/比较；未知操作符和比较异常可静默无匹配。目标必须用字段 allowlist、类型检查和严格 Filter AST。 |
| RF-Q07 | 同上 `apply_meta_data_filter` 返回值 | manual 有条件但无匹配返回 `[-999]`；auto/semi 无匹配返回 `None`；基础 doc_ids 与新结果用 `extend`。 | 三态哨兵不是稳定领域契约；目标使用结构化 `FilterResult` 和明确 intersection/union 语义。 |
| RF-Q08 | [`generator.py::keyword_extraction`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/prompts/generator.py#L224) | keyword 开启时把生成关键词以逗号追加到查询字符串。 | LLM 扩展和词法同义扩展应分开记录，不能只保存最终字符串。 |

`async_chat` 的实际顺序是：多轮独立问题 → 跨语言 → metadata doc_ids → LLM 关键词追加 → retrieval。

### 4.3 全文、向量、混合、清理和 Rerank

| 证据 ID | 源文件与符号 | 实际算法/顺序 | 分数或降级语义 |
|---|---|---|---|
| RF-Q09 | [`query.py::FulltextQueryer`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/nlp/query.py#L28) | `question()` 使用 RAG tokenizer、term weight 和 Redis-backed synonym 形成 `MatchTextExpr`；另提供 token/vector hybrid similarity。 | 词法算法可抽取实验，但 tokenizer、Redis 和字段权重需隔离。 |
| RF-Q10 | [`search.py::Dealer.search`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/nlp/search.py#L134) | 构造 KB/doc/available 等 filters；全文 `MatchTextExpr` + 查询 Embedding 的 `MatchDenseExpr` + `FusionExpr("weighted_sum", topk, weights="0.001,1")` 交给 DocStore。 | 初次 hybrid 权重用于候选召回，不等同用户配置的最终融合权重。 |
| RF-Q11 | 同上 `Dealer.search` 空结果 fallback | 有 doc filter 时退化为无 match 的结构过滤；否则全文 `min_match 0.3 → 0.1`，dense similarity 改为 `0.17` 后重试。 | 空结果降级是隐式后端重查，目标必须写入 Retrieval Trace。 |
| RF-Q12 | [`Dealer._rerank_window`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/nlp/search.py#L525)、[`retrieval`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/nlp/search.py#L549) | 候选窗口约 64 且向上取 page_size 整倍数；外部 reranker 时受 top 限制；search 后先 `_prune_deleted_chunks`。 | TopK 是后端候选上限，TopN 是最终页大小；目标 DTO 必须分名。 |
| RF-Q13 | [`Dealer.rerank_by_model`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/nlp/search.py#L494) | 外部模型分数与 token similarity 按 `(1-vector_weight, vector_weight)` 融合，再加 tag/PageRank feature。 | “vector_similarity”字段在有 reranker 时实际承载模型相似度，目标 `ScoreBreakdown` 必须使用明确分量名。 |
| RF-Q14 | [`Dealer.rerank/rerank_with_knn`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/nlp/search.py#L434) | 无外部 reranker：Infinity 使用后端 `_score`；OceanBase 用返回向量本地混合；其他路径二次 KNN 取纯向量分数再与 token 分数融合。 | 搜索后端分数语义不等价；OpenSearch 也落入 non-Infinity/non-OceanBase 分支。 |
| RF-Q15 | `Dealer.retrieval` threshold/sort/page | 稳定降序排序；vector weight 为 0 时后阈值强制 0，否则应用 similarity_threshold；过滤后才切页并构造 chunk/doc_aggs。 | 需要保留 raw、normalized、rerank、feature 和 final score，不能只存一个 similarity。 |

### 4.4 Context、生成、空结果与引用

| 证据 ID | 源文件与符号 | 调用和副作用 | 已确认差距 |
|---|---|---|---|
| RF-Q16 | [`generator.py::kb_prompt`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/prompts/generator.py#L139) | 按 max_tokens 把候选格式化为 knowledge；可包含文档 metadata。 | Context selection 与 Prompt 格式耦合；目标拆为 ContextAssembler 和 Prompt。 |
| RF-Q17 | `dialog_service.py::async_chat` 空结果分支 | `knowledges` 为空且配置 `empty_response` 时直接 yield 非最终+最终响应；未配置/空字符串则继续 LLM，knowledge 为空。 | 不能区分无候选、阈值清空、过滤清空、后端失败。目标定义 `empty_reason` 和策略路由。 |
| RF-Q18 | [`generator.py::citation_prompt`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/prompts/generator.py#L214) → `LLMBundle.async_chat_streamly_delta/async_chat` | 有知识且 quote 开启时把 citation 指引附加到系统 Prompt；流式/非流式生成答案。 | 模型可直接输出 `[ID:n]`，仍需后处理验证。 |
| RF-Q19 | [`Dealer.insert_citations`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/nlp/search.py#L251) | 若模型未产生引用标记，则按句切分答案、Embedding 句子，与 Chunk token/vector 做混合相似度，阈值从 0.63 逐级下降到 0.3，最多为句子追加 4 个 Chunk ID。 | 引用是相似度匹配，不等同逐字证据；目标需保存 quote、页/bbox 和校验结果。 |
| RF-Q20 | `dialog_service.py::repair_bad_citation_formats/decorate_answer` | 修复标记；根据引用 Chunk 的 doc_id 缩减 doc_aggs；响应前移除向量。 | 引用绑定 Chunk/doc 当前值，没有 `document_version_id` 和授权快照。 |
| RF-Q21 | `async_chat` Langfuse/日志 | 可创建 Langfuse trace_id，记录 LLM observation、耗时和 token；`Dealer.retrieval(trace_id)` 主要用于权重日志。 | 没有统一、持久、可重放的 query transform、filter、候选、分数组成、阈值和引用事件模型，故 CAP-22 仅“部分具备”。 |

### 4.5 固定 RAG 完整调用链

`chat_api.session_completion → dialog_service.rag_agent(reasoning off) → async_chat → get_models → full_question? → cross_languages? → apply_meta_data_filter? → keyword_extraction? → Dealer.retrieval → Dealer.search(FulltextQueryer + MatchDenseExpr + FusionExpr) → _prune_deleted_chunks → rerank_by_model / Infinity score / OceanBase local rerank / KNN second pass → threshold → stable sort → page TopN → retrieval_by_toc? → retrieval_by_children → KG/Web supplement? → kb_prompt → empty_response or LLMBundle generation → insert_citations? → repair_bad_citation_formats → response reference`。

## 5. P00-T06：Agent 与 LangGraph 差距

### 5.1 三种 Agent/Tool 运行面

| 证据 ID | 源文件与符号 | 实际运行方式 | 耦合和采用边界 |
|---|---|---|---|
| RF-G01 | [`agent/canvas.py::Graph`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/agent/canvas.py#L49)、[`Canvas`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/agent/canvas.py#L330) | 自定义 DSL/组件图：加载 component/upstream/downstream/variables，`Canvas.run/_run_impl` 批量调组件并产生 SSE 风格事件。 | 不是 LangGraph；直接依赖 `FileService`、`LLMBundle`、`has_canceled`、Redis cancel/log、TTS、Langfuse ContextVar。只参考事件、取消、输入和引用需求。 |
| RF-G02 | `Canvas._run_impl` | 根据 path 和组件类型处理 iteration/loop/exitloop；检测 `userfillup` resume，未满足输入时 yield `user_inputs`；Redis cancel key 控制取消。 | await/input 是 Canvas 自有运行语义，不等于 LangGraph durable interrupt；没有目标 Checkpoint 数据模型。 |
| RF-G03 | [`agent_api.py::agent_chat_completion/_run_workflow_session`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/api/apps/restful_apis/agent_api.py#L1300) | 加载 UserCanvas/Conversation，运行 Canvas，流式保存消息、reference、trace items，支持 session、rerun、webhook 和附件。 | 产品 API/Service 极高耦合；目标用 FastAPI + LangGraph run/thread 端口重建。 |
| RF-G04 | [`agent/tools/retrieval.py::Retrieval._retrieve_kb`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/agent/tools/retrieval.py#L90) | 解析 KB 名称/ID/变量 → 校验 Embedding 一致 → 构造 Embedding/Rerank/Chat → metadata/cross-language → `settings.retriever.retrieval` → TOC/children/KG → Canvas reference → `kb_prompt`。 | 是 Canvas Tool，不是 LangChain Tool；参数和返回行为可参考，运行时应改为 LangChain Tool 调 `KnowledgeQueryService`。 |
| RF-G05 | 固定 RAG `async_chat` 与 Canvas `Retrieval` | 两者最终都调用全局 `settings.retriever.retrieval`，但各自重复模型绑定、filter、补充检索和输出格式。 | RAGFlow 共享 Dealer，不是共享应用层知识查询服务。目标 `CAP-27`/`CAP-28` 必须共享同一个 `KnowledgeQueryService`。 |

### 5.2 RAGFlow 的 LangGraph Agentic RAG

| 证据 ID | 源文件与符号 | 已确认实现 | 缺口 |
|---|---|---|---|
| RF-G06 | [`agentic_rag_graph.py::AgenticState`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/advanced_rag/agentic_rag_graph.py#L57) | TypedDict 包含 messages、question、keywords、route、plan、claims、kbinfos、verdict、partial/abstain/empty、loop、feedback。 | State 是请求内 dict；没有领域 run/version/authorization/budget/audit 类型。 |
| RF-G07 | [`build_agentic_graph`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/advanced_rag/agentic_rag_graph.py#L156) | 六个节点：formalize_question → route → pre_search → planner → orchestrator_loop → formalize_answer，全部是固定边；循环逻辑封装在 orchestrator 节点内部。 | 文件 docstring 仍写“4-node”，以实际六个 `add_node` 为准；没有图级 conditional edge/HITL。 |
| RF-G08 | 同上 `return g.compile()` | `StateGraph(AgenticState)` 最终无参数 `compile()`；`run_agentic_rag` 直接 `graph.ainvoke`，只给 recursion_limit。 | 没有 checkpointer、store、thread_id、interrupt/resume 或持久恢复；不能据“导入 LangGraph”判断 CAP-30/CAP-31 已具备。 |
| RF-G09 | [`agentic_rag.py::RAGTools`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/advanced_rag/agentic_rag.py#L71) | 封装 formalize、文档筛选、hybrid/Web/SQL、充分性、follow-up、全文档和两个外部 Tool（`rag`、`summarize_document`）。 | 直接依赖 Knowledgebase/Document metadata Service、LLMBundle、全局 retriever；只参考 Tool 边界和证据聚合。 |
| RF-G10 | `run_agentic_rag(max_loops)` | max_loops 只用于计算 LangGraph recursion_limit；实际 loop/verdict 由 harness orchestrator 管理。 | 预算、成本、工具策略、取消、重试和循环上限需要目标项目统一治理。 |

### 5.3 目标责任边界

| 来源 | 在目标项目承担 | 不承担 |
|---|---|---|
| LangChain | Chat/Embedding/Reranker/Prompt/Structured Output、Retriever/Tool 标准包装、Provider callbacks | durable workflow、权限、生命周期、完整 Trace |
| LangGraph | Agent 状态、路由、循环、重试、Checkpoint、interrupt/resume、HITL、子图和多 Agent 编排 | Parser、Embedding 批处理、搜索索引、tenant 判定 |
| RAGFlow 复用/参考 | Retrieval Tool 参数、Canvas 事件需求、Agentic RAG 的问题规范化/预检索/计划/充分性/证据汇总 | Canvas runtime、Quart/Peewee Service、全局 settings、现成 durable Agent 平台 |
| 自研 | `AgentState` 领域语义、run/thread 数据、`AuthorizationContext`、预算/超时/取消、ToolPolicy、审计、Retrieval Trace、`KnowledgeQueryService` | 不重写 LangGraph 已提供的基础编排机制 |

## 6. P00-T07：生命周期、队列与 Worker 可靠性

### 6.1 更新、重解析、停止和删除

| 证据 ID | 源文件与符号 | 操作顺序 | 一致性/竞态结论 |
|---|---|---|---|
| RF-L01 | [`document_api.py::update_document`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/api/apps/restful_apis/document_api.py#L165) | 校验 KB/Document 所属 → metadata/name/parser_config/pipeline/chunk method/enabled 分项更新；Parser/pipeline 改变可调用 reset-for-reparse。 | 多字段更新不是统一 DocumentVersion 事务；当前 Document 原地变化。 |
| RF-L02 | [`document_api.py::parse_documents`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/api/apps/restful_apis/document_api.py#L1497) | 已完成文档先扣减旧统计 → 删除旧 Task、导航和 doc_id Chunk → `DocumentService.run` 排新任务。 | 旧 Chunk 在新版本成功前被删除，存在不可查询窗口；没有候选索引/原子激活。 |
| RF-L03 | [`document_api.py::stop_parse_documents`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/api/apps/restful_apis/document_api.py#L1613) | `cancel_all_task_of` → Document 标 CANCEL、统计清零 → 删除该 doc 全部索引 Chunk。 | 正在运行的 Parser/Embedding 依赖后续 cancel 检查才停止，删除与写入可能竞态。 |
| RF-L04 | [`document_api.py::delete_documents`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/api/apps/restful_apis/document_api.py#L1089) → [`FileService.delete_docs`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/api/db/services/file_service.py#L677) | 访问检查 → 每个 doc 删除 Task → `DocumentService.remove_document` → File/File2Document → 仅当 file 被删时删除对象。 | 多文档逐个执行，部分失败返回 errors，不是全批原子。 |
| RF-L05 | [`DocumentService.delete_document_and_update_kb_counts`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/api/db/services/document_service.py#L802) → [`remove_document`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/api/db/services/document_service.py#L458) | 先在 DB atomic 内删除 Document 并扣 KB 统计，再 best-effort 取消 Task、删 Task/图片/缩略图/导航/Chunk/派生产物/metadata/Graph 引用。 | 关系行先消失；后续大多 catch-and-continue，可能留下孤儿对象、Chunk 或派生数据。`Dealer._prune_deleted_chunks` 是在线防御。 |

冻结数据模型只有 Document 当前状态和 Task；未发现 `DocumentVersion`、候选 index version 或 active pointer。该“缺少”结论来自 `db_models.py` 的实际类清单与上述原地更新/删除调用，不是按名称猜测。

### 6.2 投递、领取、重试、ACK 和取消

| 证据 ID | 源文件与符号 | 已确认行为 | 可靠性边界 |
|---|---|---|---|
| RF-L06 | [`TaskService.queue_tasks`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/api/db/services/task_service.py#L435) | `bulk_insert_into_db(Task)` 和 `DocumentService.begin2parse` 之后逐条 `XADD`；失败会 abort Redis chunk counter 并抛出。 | DB/Stream 非原子；存在已入库未投递任务，没有 outbox/sweeper 证据。 |
| RF-L07 | [`RedisDB.queue_consumer/get_unacked_iterator`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/utils/redis_conn.py#L415) | `XREADGROUP` 每次一条；Worker 启动优先读取当前 consumer 的 pending（msg_id 从 0），再读取新消息。 | 只恢复同 consumer 名下 pending；`get_pending_msg/requeue_msg` 存在，但主 collect 未自动 claim 其他已死 consumer 的 pending。 |
| RF-L08 | [`TaskService.get_task`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/api/db/services/task_service.py#L165) | 联查 Task→Document→KB→Tenant；每次领取把 `retry_count + 1`。领取前值 ≥3 时标 Task/Document 失败并返回 None，随后 collect ACK。 | 次数是“领取次数”而不是按异常类型调度的 retry policy；没有 backoff/next_attempt_at/dead-letter。 |
| RF-L09 | [`task_executor.py::handle_task`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/svr/task_executor.py#L1741) | 成功、`TaskCanceledException` 和一般异常分别记统计/进度；函数结束后统一 `redis_msg.ack()`。 | 一般异常也 ACK，不会凭 Redis pending 自动重试；进程在 ACK 前崩溃才可能由相同 consumer pending 恢复。 |
| RF-L10 | [`cancel_all_task_of/has_canceled`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/api/db/services/task_service.py#L597) | 对每个 Task 写 `<task_id>-cancel` Redis key；Worker/Parser/Chunk/Embedding 分散检查；Document CANCEL 另在 DB 保存。 | Redis key、DB status、正在运行的副作用之间无原子状态机；取消后必须继续防止 late write。 |
| RF-L11 | [`RedisDB.requeue_msg`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/utils/redis_conn.py#L489) | 读取旧消息，重新 XADD，再 ACK 旧 ID。 | 工具存在不代表主 Worker 有 DLQ/retry schedule；调用关系中未见统一失败分类。 |

### 6.3 目标项目可靠性约束

1. 拓扑仍是同仓库 FastAPI + 独立 Ingestion Worker；这不是微服务拆分。
2. `TaskQueuePort` 的具体库仍为 O-006，不因 RAGFlow 使用 Redis Streams 而提前决定。
3. 任务消息至少携带 `tenant_id + job_id + attempt/idempotency_key`；Worker 必须从数据库重载并二次校验 tenant。
4. 状态机区分 queued/running/succeeded/retryable_failed/permanent_failed/cancelled；ACK 只在状态持久化和副作用策略确定后执行。
5. 必须定义 claim/lease、指数退避、最大尝试、dead-letter、shutdown、心跳、backpressure 和 stale job sweeper。
6. 文档重解析使用 `DocumentVersion` 与候选索引版本；新版本完成后原子切换 active pointer，失败保留旧可用版本。
7. 对象存储、关系库和搜索引擎通过幂等操作、补偿记录和 reconciliation 处理，不伪装为跨系统 ACID。

## 7. P00-T08：Tenant、ACL 与数据权限

### 7.1 身份、租户和成员关系

| 证据 ID | 源文件与符号 | 已确认行为 | 对目标项目的含义 |
|---|---|---|---|
| RF-P01 | [`api/apps/restful_apis/user_api.py::user_register`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/api/apps/restful_apis/user_api.py#L427) | 注册时同时写入 `User.id=user_id`、`Tenant.id=user_id`、`UserTenant(tenant_id=user_id,user_id=user_id,role=OWNER)`，并创建 `File(tenant_id=user_id,created_by=user_id)`。 | 个人工作区初始化把 user ID 与 tenant ID 取相同值；不能把这种初始化约定复制为目标领域恒等关系。 |
| RF-P02 | [`api/apps/restful_apis/tenant_api.py::create/agree/rm`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/api/apps/restful_apis/tenant_api.py#L60) | 邀请创建 `UserTenantRole.INVITE`，接受后改为 `NORMAL`；列成员和邀请要求 `current_user.id == tenant_id`，移除允许 tenant ID 对应用户或本人操作。 | 角色和成员关系存在，但管理授权仍依赖“owner user ID 等于 tenant ID”的产品约定。 |
| RF-P03 | [`api/db/services/user_service.py::TenantService.get_info_by/get_joined_tenants_by_user_id`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/api/db/services/user_service.py#L162) | `get_info_by` 只返回 OWNER 成员关系；`get_joined_tenants_by_user_id` 只返回 NORMAL 成员关系。 | 所有者与普通加入成员分支由查询方法隐式区分，不是统一授权决策对象。 |

### 7.2 知识库、文档和检索权限

| 证据 ID | 源文件与符号 | 已确认行为 | 边界/缺口 |
|---|---|---|---|
| RF-P04 | [`api/db/db_models.py::{Tenant,UserTenant,Knowledgebase,Document,Task}`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/api/db/db_models.py#L722) | `Knowledgebase` 有 `tenant_id`、`permission=me\|team`、`created_by`；`Document` 只有 `kb_id`、`created_by`，`Task` 只有 `doc_id`；Chunk 是搜索文档而不是关系模型。 | Document/Task/Chunk 的 tenant 需要沿 KB/Document 或调用参数推导，没有跨层统一的授权上下文。 |
| RF-P05 | [`api/utils/api_utils.py::add_tenant_id_to_kwargs`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/api/utils/api_utils.py#L241) | 装饰器无条件把 `current_user.id` 写入 `kwargs["tenant_id"]`。 | 防止请求体直接伪造该参数，但参数名实际承载 current user ID；user/tenant/owner 语义仍混合。 |
| RF-P06 | [`KnowledgebaseService._visibility_and_status_filter/accessible/accessible4deletion`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/api/db/services/knowledgebase_service.py#L76) | 列表允许自己的 KB 或已加入 tenant 的 `permission=team` KB；单项访问执行相同语义；删除只检查 `created_by == user_id`。 | 查看与删除由不同规则实现，规则分散在 Service 方法中。 |
| RF-P07 | [`api/common/check_team_permission.py::check_kb_team_permission/check_file_team_permission`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/api/common/check_team_permission.py#L25) | 若资源 tenant 等于当前 `other` 直接允许；否则 KB 必须为 TEAM，且用户的 NORMAL tenant 列表包含资源 tenant。 | 这是另一组独立 helper；未形成所有 Repository、任务、对象和 Tool 共用的 `PermissionChecker`。 |
| RF-P08 | [`DocumentService.accessible/accessible4deletion`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/api/db/services/document_service.py#L891) | 普通访问委托 `KnowledgebaseService.accessible`；删除通过 `Knowledgebase.created_by` 与 `UserTenant.tenant_id` 联查 NORMAL/OWNER。 | Document 没有自己的 visibility；删除联查又使用 `created_by`，证明 tenant/creator 语义不能直接照搬。 |
| RF-P09 | [`rag/nlp/search.py::index_name/Dealer.retrieval`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/nlp/search.py#L35) | 调用方传入 `tenant_ids`；Retriever 将其映射为 `ragflow_{uid}` 索引列表，并同时按 `kb_ids`、`doc_ids`、`available_int` 过滤。 | 每 tenant 索引是防线之一，但 `Dealer` 不负责认证或判断调用方是否有权提供这些 tenant IDs。 |

### 7.3 目标项目第一版权限不变量

1. `AuthorizationContext` 明确区分 subject、当前 `tenant_id`、角色/声明和请求关联信息；HTTP 参数、队列消息、模型或 Tool 参数都不能替换已认证 tenant。
2. `KnowledgeBase`、`Document` 明确保存 `tenant_id`、`owner_id`、`visibility`；版本、任务、Chunk、索引记录、对象 key、缓存/锁、Citation、Retrieval Trace 和 Agent/Tool 运行记录至少显式携带 tenant。
3. Repository 和 Search Adapter 强制合并 tenant 条件；业务 metadata filter、空结果降级和 Agent Tool 不能移除或扩大该条件。
4. Worker 只把队列中的 `tenant_id + job_id` 当定位信息，必须从数据库重载任务并由 `PermissionChecker`/领域不变量复核。
5. 每 tenant 物理索引或共享索引只是部署选择，不能替代索引文档中的 tenant 字段、写入校验和返回前授权。
6. 第一版实现 tenant 强隔离、owner、visibility、`AuthorizationContext`、`PermissionChecker` 及跨租户负向测试；复杂 RBAC、部门权限和动态数据规则明确后置。
7. RAGFlow 的 `me|team`、Tenant/UserTenant 和 tenant index 仅作场景与攻击面参考；目标权限模型归类为自行开发。

## 8. P00-T09：高级 RAG、多模态、评测和生产依赖

### 8.1 GraphRAG 构建、恢复和查询

| 证据 ID | 源文件与符号 | 已确认实现 | 采用边界 |
|---|---|---|---|
| RF-X01 | [`TaskHandler.handle/_run_graphrag`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/svr/task_executor_refactor/task_handler.py#L247) | `task_type=="graphrag"` 独立分支绑定 KB Chat/Embedding，受 `kg_limiter` 控制后调用 `run_graphrag_for_kb`。 | 是 Ingestion 派生任务，不应放进在线请求或 Agent 图节点内同步构建。 |
| RF-X02 | [`run_graphrag_for_kb`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/graphrag/general/index.py#L256) | 按 doc 读取现有 Chunk、分批抽取 subgraph、重试/超时、并发合并；可继续执行实体消歧和社区报告。 | 编排完整但直接依赖 DocumentService、全局 Retriever/DocStore、RAGFlow 字段和 Task callback。 |
| RF-X03 | [`generate_subgraph`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/graphrag/general/index.py#L731) | 实体/关系生成 NetworkX 图，写入 `knowledge_graph_kwd=subgraph`、`source_id=doc_id`、`available_int=0` 的搜索文档；写前先删同 doc subgraph。 | subgraph 有来源，但仍是搜索文档字典；目标需要显式 GraphArtifact/Version 和原子激活策略。 |
| RF-X04 | `run_graphrag_for_kb::_acquire_lock`、[`RedisDistributedLock`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/utils/redis_conn.py) | doc 并发之后以 `graphrag_task_{kb_id}` Redis lock 串行 merge 和 post-merge 阶段；多处调用 `has_canceled(task_id)`。 | 可参考锁粒度、取消检查和重试边界；锁实现、租约与作业状态必须经端口重建。 |
| RF-X05 | [`rag/graphrag/checkpoints.py`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/graphrag/checkpoints.py)、[`phase_markers.py`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/graphrag/phase_markers.py) | 实体消歧/社区 checkpoint 以 `tenant_id:kb_id:type:key` 存 Redis，数据与索引均 7 天 TTL；resolution/community 完成 marker 也是 7 天 TTL、KB 级。新图合并或解绑时清 marker。 | 这是 GraphRAG 作业恢复，不是 LangGraph Agent Checkpoint；Redis TTL 到期后必须可安全重算。 |
| RF-X06 | [`resolve_entities/extract_community`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/graphrag/general/index.py#L851) | 实体消歧更新 graph/Pagerank；社区报告使用稳定 ID，先插新集合再删 stale IDs，失败时退回 delete-then-insert；成功后清对应 checkpoint。 | 局部已有崩溃防御，但不是与 DocumentVersion 绑定的统一派生索引事务。 |
| RF-X07 | [`rag/graphrag/search.py::KGSearch.retrieval`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/graphrag/search.py#L139) | LLM 改写实体类型/实体，检索实体、关系、n-hop 和社区报告，按 similarity×Pagerank 排序并在 Token 预算内拼成一个合成 Chunk。 | 继承 Dealer、直接用 DocStore/pandas/RAGFlow 字段；返回固定相似度 1.0，必须用独立高级 Retriever 与 Trace 适配。 |

### 8.2 RAPTOR

| 证据 ID | 源文件与符号 | 已确认实现 | 采用边界 |
|---|---|---|---|
| RF-X08 | [`RecursiveAbstractiveProcessing4TreeOrganizedRetrieval`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/advanced_rag/knowlege_compile/raptor.py#L165) | 支持 classic/PSI tree builder；classic 支持 GMM（UMAP 降维 + GaussianMixture）与 AHC，相邻 cosine 的顺序聚类也在实现中；逐层 LLM 摘要并重新 Embedding。 | 算法可作为改造复用候选，但 NumPy/sklearn/umap、LLM、Embedding、Token 和取消依赖必须隔离。 |
| RF-X09 | 同上 `__call__/_materialize_tree` | 输入标准化为 `(text, vector, source_chunk_ids)`；父摘要合并全部叶 Chunk ID，classic 可输出树；聚类不缩小时强制单簇防止无限循环；多处 `has_canceled`。 | 来源追踪比单纯摘要完整，但目标仍需 `document_version_id`、摘要 Prompt/模型版本和成本记录。 |
| RF-X10 | [`TaskHandler._run_raptor`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/svr/task_executor_refactor/task_handler.py#L354) → [`RaptorService._generate_raptor`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/svr/task_executor_refactor/raptor_service.py#L350) | 从现有向量 Chunk 加载 `(content,vector,id)`，生成 summary rows 或不可检索的 `raptor_tree` row，经 ChunkService 插入后清理 stale RAPTOR rows，并 best-effort 写结构图。 | 整体 Service/索引写入极重耦合；采用时只抽取算法和来源规则，任务、Chunk、清理、版本与索引由目标应用层负责。 |

### 8.3 多模态

| 证据 ID | 源文件与符号 | 已确认实现 | 缺口/采用方式 |
|---|---|---|---|
| RF-X11 | [`rag/app/picture.py::chunk/vision_llm_chunk`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/app/picture.py#L41) | 图片可先走配置的 PaddleOCR，否则本地 OCR/Vision 描述；视频分支使用 Vision 模型；输出包含 image/doc_type/content 和媒体上下文。 | Parser、tenant model Service、临时文件与模型调用耦合；通过 OCRPort/VisionModelPort 和 ParsedBlock 适配。 |
| RF-X12 | [`rag/app/audio.py::chunk`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/app/audio.py#L27) | 写临时音频文件，选择 tenant ASR 模型，经 `LLMBundle.transcription` 得到文本 Chunk。 | 提供转写，不等于跨模态向量检索；目标需保留时间/媒体来源并经 TranscriptionPort 接入。 |
| RF-X13 | [`deepdoc/parser/figure_parser.py::VisionFigureParser`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/deepdoc/parser/figure_parser.py#L201) | PDF/DOCX/XLSX 图像可携带上下文调用 Vision Prompt，增强 figure description 后并回表图集合。 | 多模态能力横跨 Parser、VLM 和 Chunk 字段；不是可整体复制的单一模块。 |

### 8.4 Timeline knowledge compilation

| 证据 ID | 源文件与符号 | 已确认覆盖 | 明确不覆盖/采用边界 |
|---|---|---|---|
| RF-X20 | [`api/db/init_data/compilation_templates/timeline.yaml`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/api/db/init_data/compilation_templates/timeline.yaml) → [`runner.py::run_structure_compile_over_batches/_compile_batch/_flush`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/advanced_rag/knowlege_compile/runner.py) → [`structure.py::compile_structure_from_text/merge_compiled_structures/cleanup_timeline_isolated_entities`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/rag/advanced_rag/knowlege_compile/structure.py) | runner 编排批次；structure 从文本编译、合并事件 timeline 结构并清理孤立实体，证明 RAGFlow 有事件时间线 knowledge compilation。 | 没有证明数值时序存储、窗口/聚合查询、降采样、异常区间、时态过滤和完整时序 Citation。`CAP-43` 采用参考后自研；Phase 09 执行前验证目标数据模型和后端。 |

### 8.5 Benchmark、观测和部署

| 证据 ID | 源文件与符号 | 已确认覆盖 | 明确不覆盖/采用边界 |
|---|---|---|---|
| RF-X14 | [`test/benchmark/dataset.py`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/test/benchmark/dataset.py)、[`chat.py`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/test/benchmark/chat.py)、[`retrieval.py`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/test/benchmark/retrieval.py) | CLI 可建 Dataset、上传/触发/等待解析、创建 Chat，再按 iterations/concurrency 请求 Chat 或 Retrieval。 | 是端到端性能压测 harness，不是目标评测体系。 |
| RF-X15 | [`test/benchmark/metrics.py::summarize`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/test/benchmark/metrics.py#L49)、[`report.py`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/test/benchmark/report.py) | Chat 统计首 Token/总延迟；Retrieval 统计总延迟；报告 success/failure、avg/min/P50/P90/P95、总时长和 QPS。 | 对 `test/benchmark` 全文件扫描未发现 Recall、MRR、NDCG、忠实度、引用正确率或 Agent 成功率实现；这些必须自行开发。 |
| RF-X16 | [`common/token_utils.py::token_usage_sink`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/common/token_utils.py#L48)、`LLMBundle`、`DialogService.async_chat` | Canvas run 可用 ContextVar 汇总 Token；LLMBundle 可建 Langfuse generation；固定 RAG 可创建 Langfuse trace/observation，Dealer 记录 trace_id 与权重。 | 没有统一跨 API→任务→Parser→检索→模型→Agent 的持久事件 schema。 |
| RF-X17 | [`docker/service_conf.yaml.template`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/docker/service_conf.yaml.template)、[`docker/docker-compose-base.yml`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/docker/docker-compose-base.yml) | 配置暴露 OTEL host/port；Compose 可选启动 Jaeger。 | 配置和容器存在不等于所有业务路径已产生完整 span；目标需用契约测试验证 trace 传播。 |
| RF-X18 | [`docker/launch_backend_service.sh`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/docker/launch_backend_service.sh)、[`docker/docker-compose.yml`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/docker/docker-compose.yml) | 默认启动 Python RAGFlow API 与多个 Python task executor；基础依赖包括 MySQL、MinIO、Valkey 和所选搜索后端，另有可选 DeepDoc/Jaeger/TEI/NATS/ClickHouse 等 profile。 | 只作为依赖清单和同仓库多进程证据；Go 分支范围外，目标不复制容器拓扑。 |
| RF-X19 | [`helm/templates/ragflow.yaml`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/helm/templates/ragflow.yaml)、[`helm/values.yaml`](https://github.com/infiniflow/ragflow/blob/cd846cc9d4e32a19e684c59a1f302601027ef976/helm/values.yaml) | Chart 默认一个 `replicas: 1` 的 RAGFlow Deployment；values 配置 RAGFlow、Infinity/ES/OpenSearch、MinIO、MySQL、Valkey 及存储。 | 不能据此认定目标已具备独立 API/Worker 扩缩容、备份恢复或生产 SLO；这些仍是 Phase 10 自研交付。 |

### 8.6 采用结论

1. GraphRAG、RAPTOR 和多模态 RAG 均是 RAGFlow 已具备、目标项目尚未实现的 Phase 09 能力；“已具备”不得跨项目解释。RAGFlow 对时序 RAG 只具备 timeline knowledge compilation 的局部证据，不能归类为完整具备。
2. GraphRAG/RAPTOR 默认关闭，只有在固定评测集上相对 Phase 06 基线证明质量收益且成本、失败和生命周期可控后，才允许默认启用。
3. 图/树/媒体派生物必须绑定 `tenant_id + document_version_id + algorithm/model/prompt version`，并支持取消、删除、重建和降级。
4. RAGFlow benchmark 仅作为性能 harness 设计参考；质量、引用、Agent 和安全评测归类为自行开发。
5. RAGFlow Docker/Helm 仅提供依赖与部署用例，目标项目维持“模块化单体 FastAPI + 独立 Ingestion Worker”，不拆微服务，也不复现 Go。
