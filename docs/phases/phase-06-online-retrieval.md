---
document_id: PHASE-06-ONLINE-RETRIEVAL
document_role: Phase 06 正式详细计划与执行记录
status: completed
phase: Phase 06
phase_name: 在线检索
plan_status: 已确认
execution_status: 已完成
last_updated_at: "2026-07-31"
ragflow_frozen_baseline_commit: "cd846cc9d4e32a19e684c59a1f302601027ef976"
---

# Phase 06：在线检索详细计划

## 0. 状态与导航

- **计划状态**：已确认；ADR-021 已冻结并实施准入决策。
- **执行状态**：已完成；P06-T01 至 P06-T12 均通过任务验证和阶段门禁。
- **前置阶段事实**：Phase 04、Phase 05 已完成；现有基线为 Elasticsearch
  BM25/KNN/RRF、统一 SearchPort、schema v2 Chunk metadata、Citation bbox
  和多格式测试集。
- **准入判断**：已通过。用户确认计划，ADR-021 解决 O-008、RRF/Reranker、
  Trace 保留/权限/清理和源码复用边界；允许从 P06-T01 连续执行到 P06-T12。
- 导航：[阶段索引](./README.md) · [Phase 05](./phase-05-parser-and-chunk.md) · [Phase 07](./phase-07-document-lifecycle.md) · [Phase 08](./phase-08-agentic-rag.md)

## 1. 目标、必要性与事实依据

实现可评测、可解释、权限不可放宽的完整在线链路：查询规范化、多轮改写、跨语言和关键词扩展、元数据/权限过滤、全文/向量/混合召回、融合、候选清理、Reranker、阈值/TopK/TopN、空结果降级、完整 Citation 和 Retrieval Trace。

Phase 00 已核验 `Dealer.search/retrieval`、`FulltextQueryer`、`full_question/cross_languages/keyword_extraction`、metadata filter、Rerank、Citation 的实际顺序；上游存在隐式哨兵/二次重查和不完整 Trace，目标协议必须自研。

## 2. 前置、输入、范围与排除

- **前置阶段**：Phase 04、Phase 05。
- **进入条件**：真实 Minimum RAG 和多格式 Chunk 通过；O-008 空结果策略、Reranker/融合/Trace 保留策略有结论；本计划确认。
- **输入**：KnowledgeQueryService、SearchPort、Filter/Permission/Citation/Trace 协议、评测集和模型 Adapter。

**范围**：用户列出的全部在线检索能力及检索/引用评测。

**排除**：Agent 多步循环、GraphRAG/RAPTOR/时序检索默认路由、文档更新/删除实现、复杂权限规则；任何降级不得跨 tenant 或放宽 visibility。

## 3. 交付物与目标模块

```text
src/ragflow_agent/knowledge/application/query/
  preprocess.py rewrite.py translate.py expand.py filters.py
  retrieve.py clean.py fuse.py rerank.py fallback.py
  context.py citations.py trace.py
src/ragflow_agent/knowledge/infrastructure/ragflow_adapters/retrieval/
tests/{unit,contract,integration,evaluation}/retrieval/
```

交付查询 Profile、Filter AST、候选/分数模型、完整 Trace、CitationBuilder、评测报告和统一 `KnowledgeQueryService`。

## 4. RAGFlow 源码与采用

| 源码/关系 | 采用 |
|---|---|
| `rag/nlp/query.py::FulltextQueryer.question` → `Dealer.search` | 分词/权重算法改造候选 |
| `Dealer.search` → dense/text expressions → DocStore | 搜索顺序参考 |
| `Dealer.retrieval` → 清理 → fusion/rerank → threshold/topN | 融合/截断算法改造候选 |
| `generator.py::{full_question,cross_languages,keyword_extraction,gen_meta_filter}` | Prompt/结构化输出参考重写 |
| `common/metadata_utils.py::apply_meta_data_filter` | 哨兵/回退行为只作反例，Filter AST 自研 |
| `Dealer.insert_citations`、`kb_prompt/citation_prompt` | 引用算法改造候选，Citation 模型自研 |
| `dialog_service.async_chat` | 固定回答调用顺序参考 |

- **直接复用**：无。
- **`ragflow_adapters` 改造复用**：经复用门禁批准的全文 query、融合/引用纯算法片段。
- **参考后自研**：查询处理、Filter AST、清理、降级、Trace、统一服务。
- **明确不采用**：隐式 `None/[-999]` 语义、权限放宽、后端特有对象进入应用层。

## 5. 框架与自研职责

- **LangGraph**：此阶段不承载基础检索；只为 Phase 08 暴露结构化结果/重试原因。
- **LangChain**：Prompt、ChatModel、Embeddings、Reranker Adapter、结构化查询输出。
- **自研**：所有检索编排、权限合并、Filter AST、候选/分数、降级、Citation/Trace 和评测。

## 6. 任务总表

| 任务 | 名称 | 状态 | 前置 |
|---|---|---|---|
| P06-T01 | 复审查询协议、Profile 与评测基线 | 已完成 | Phase 04、05 |
| P06-T02 | 实现查询规范化与预处理 | 已完成 | P06-T01 |
| P06-T03 | 实现多轮问题改写 | 已完成 | P06-T02 |
| P06-T04 | 实现跨语言与关键词扩展 | 已完成 | P06-T02 |
| P06-T05 | 实现元数据 AST 与权限过滤 | 已完成 | P06-T01、P06-T02 |
| P06-T06 | 完善全文检索 | 已完成 | P06-T02、P06-T05 |
| P06-T07 | 完善 Query Embedding 与向量检索 | 已完成 | P06-T02、P06-T05 |
| P06-T08 | 实现混合召回与分数融合 | 已完成 | P06-T06、P06-T07 |
| P06-T09 | 实现清理、Reranker、阈值与 TopK/TopN | 已完成 | P06-T08 |
| P06-T10 | 实现空结果降级与重试 | 已完成 | P06-T03 至 P06-T09 |
| P06-T11 | 完善 Citation、Context 与 Retrieval Trace | 已完成 | P06-T09、P06-T10 |
| P06-T12 | 建立评测并执行阶段验收 | 已完成 | P06-T01 至 P06-T11 |

## 7. 具体任务

### P06-T01：复审查询协议、Profile 与评测基线

- **状态**：已完成
- **目标**：按真实字段冻结 RetrievalQuery/Result/Profile/Trace 和指标。
- **为什么需要**：预规划不能假定 Phase 05 metadata 与后端分数语义。
- **输入**：Phase 04/05 验收、O-008、评测基线。
- **前置任务**：Phase 04、05 完成。
- **操作步骤**：检查源码/Git；复核字段/后端；确定 Profile、TopK/TopN 上限、Reranker/Trace 策略；修订任务。
- **涉及文件**：查询协议、评测配置、本文件、ADR。
- **预期输出**：执行基线。
- **RAGFlow 源码依据**：`Dealer._rerank_window/retrieval`。
- **实现或复用方式**：审计/自研。
- **测试方法**：Schema 与后端 capability probe。
- **验证命令**：`uv run pytest -q tests/unit/config/test_settings.py tests/evaluation/retrieval/test_metrics.py`
- **验收标准**：所有待决策有结论或明确 fallback。
- **风险和回滚方法**：保持 Phase 04 Profile 可回退。
- **实际执行结果**：冻结 retrieval schema v2、`OnlineRetrievalProfile`、ADR-021 和 Recall/MRR/NDCG 基线；确认 RAGFlow 代码零复制。
- **实际验证结果**：配置、领域模型和评测单元测试通过。
- **计划偏差**：不另建 context/citations 模块，沿用 Phase 04 `FixedRagService` 的引用和上下文边界。

### P06-T02：实现查询规范化与预处理

- **状态**：已完成
- **目标**：规范 Unicode、空白、长度、语言、时间和安全字段并保留原查询。
- **为什么需要**：后续每种变换必须可追溯。
- **输入**：P06-T01。
- **前置任务**：P06-T01。
- **操作步骤**：定义 QueryTransform event；规范化；语言检测；长度/控制字符；生成 canonical query。
- **涉及文件**：`query/preprocess.py`、测试。
- **预期输出**：规范化查询。
- **RAGFlow 源码依据**：`Dealer.retrieval` 的 question/tokenizer 调用只作顺序参考。
- **实现或复用方式**：自行开发。
- **测试方法**：中英、Unicode、超长、空查询、注入文本。
- **验证命令**：`uv run pytest -q tests/unit/retrieval/test_preprocess_and_transforms.py`
- **验收标准**：原始/规范查询同时入 Trace。
- **风险和回滚方法**：规范化规则版本化，可回退原查询。
- **实际执行结果**：实现 Unicode NFKC、控制字符清理、空白规范化、长度限制、轻量语言检测和版本化词法关键词。
- **实际验证结果**：`tests/unit/retrieval/test_preprocess_and_transforms.py` 通过。
- **计划偏差**：时间实体保持原文，不在本阶段引入时间解析器。

### P06-T03：实现多轮问题改写

- **状态**：已完成
- **目标**：把指代/省略问题改为独立问题，并可靠回退。
- **为什么需要**：多轮上下文直接拼接会降低召回。
- **输入**：P06-T02、对话历史契约。
- **前置任务**：P06-T02。
- **操作步骤**：LangChain Prompt/结构化输出；上下文预算；无需改写判定；超时/格式失败回退；Trace。
- **涉及文件**：`query/rewrite.py`、prompts、测试。
- **预期输出**：RewriteResult。
- **RAGFlow 源码依据**：`generator.py::full_question`。
- **实现或复用方式**：参考 Prompt 后自研。
- **测试方法**：指代、省略、完整问题、恶意历史、模型失败。
- **验证命令**：`uv run pytest -q tests/unit/retrieval/test_preprocess_and_transforms.py tests/unit/retrieval/test_provider_adapters.py`
- **验收标准**：失败回到规范查询；不改变权限。
- **风险和回滚方法**：Profile 可关闭改写。
- **实际执行结果**：通过 `QueryTransformProviderPort` 和 `ChatQueryTransformProvider` 生成结构化改写；超时、异常和非法输出回退 canonical query。
- **实际验证结果**：改写开关、历史输入、失败回退和 Provider 契约测试通过。
- **计划偏差**：计划文件名 `rewrite.py` 合并为 `transforms.py`，避免三套重复 Provider 编排。

### P06-T04：实现跨语言与关键词扩展

- **状态**：已完成
- **目标**：生成可控翻译查询和词法/LLM 关键词集合。
- **为什么需要**：跨语言文档和专有名词需要扩召回。
- **输入**：P06-T02、术语测试集。
- **前置任务**：P06-T02。
- **操作步骤**：跨语言结构化输出；保留原 query；术语保护；词法与 LLM 扩展分开；去重/上限；Trace。
- **涉及文件**：`query/{translate,expand}.py`、测试。
- **预期输出**：QueryVariant 集。
- **RAGFlow 源码依据**：`cross_languages`、`keyword_extraction`、Fulltext synonym/term weight。
- **实现或复用方式**：Prompt 参考重写；词法算法可改造。
- **测试方法**：中英、专名、噪声率、超时、关闭 Profile。
- **验证命令**：`uv run pytest -q tests/unit/retrieval/test_preprocess_and_transforms.py tests/unit/retrieval/test_online_pipeline_and_trace.py`
- **验收标准**：变体有来源/语言/成本；原查询始终保留。
- **风险和回滚方法**：噪声超阈则关闭对应扩展。
- **实际执行结果**：实现目标语言变体、确定性词法关键词和可选 Provider 关键词扩展，统一限额、去重与来源记录。
- **实际验证结果**：中文/英文、目标语言、去重、限额、关闭开关和 Provider 失败测试通过。
- **计划偏差**：计划中的 `translate.py`/`expand.py` 合并到 `transforms.py`；未实现未获准的同义词词典服务。

### P06-T05：实现元数据 AST 与权限过滤

- **状态**：已完成
- **目标**：将用户/LLM filter 转受控 AST，并与不可删除的权限 AND 条件合并。
- **为什么需要**：防止类型错误、DSL 注入和权限降级。
- **输入**：P06-T01、P06-T02、PermissionChecker、metadata Schema。
- **前置任务**：P06-T01、P06-T02。
- **操作步骤**：定义字段 allowlist/operator/type；解析/验证；权限节点先构造；编译到 Search Adapter；记录 reject reason。
- **涉及文件**：`query/filters.py`、Search Adapter、测试。
- **预期输出**：Filter AST v1。
- **RAGFlow 源码依据**：`apply_meta_data_filter/meta_filter`、`gen_meta_filter`。
- **实现或复用方式**：参考后自研。
- **测试方法**：AND/OR/NOT、类型、非法字段、注入、tenant 伪造。
- **验证命令**：`uv run pytest -q tests/unit/retrieval/test_filters_and_fallback.py tests/integration/search/test_phase06_retrieval.py`
- **验收标准**：权限不可移除；不同后端契约一致。
- **风险和回滚方法**：未知操作符拒绝，不降级全量查询。
- **实际执行结果**：实现递归 AND/OR/NOT Filter AST，并在 Elasticsearch Adapter 强制 tenant、ACL、KB/index、文档启用/删除/可见状态，再叠加用户过滤。
- **实际验证结果**：AST、注入拒绝、角色 ACL、跨租户、文档状态和所有降级分支硬过滤不变测试通过。
- **计划偏差**：Filter 编译直接留在 Elasticsearch Adapter；没有创建后端无关 DSL 字符串。

### P06-T06：完善全文检索

- **状态**：已完成
- **目标**：实现中文/英文 BM25、短语、字段权重和过滤。
- **为什么需要**：关键词、编号、告警码常比向量精确。
- **输入**：P06-T02、P06-T05、索引 mapping。
- **前置任务**：P06-T02、P06-T05。
- **操作步骤**：query analysis；字段/短语/同义；tenant/filter；ScoreBreakdown；分页和上限。
- **涉及文件**：Search Adapter、可选 `ragflow_adapters/retrieval/fulltext.py`。
- **预期输出**：全文候选。
- **RAGFlow 源码依据**：`FulltextQueryer.question` → `Dealer.search`。
- **实现或复用方式**：纯算法经 Adapter 改造候选；DSL 自研。
- **测试方法**：中英、编号、短语、过滤、排序、后端契约。
- **验证命令**：`uv run pytest -q tests/integration/search/test_phase06_retrieval.py tests/integration/search/test_elasticsearch.py`
- **验收标准**：全文 baseline 可复现；分数来源明确。
- **风险和回滚方法**：Analyzer 变化绑定 index_version。
- **实际执行结果**：在现有 Elasticsearch Adapter 上增加独立 BM25 通道、短语 boost、过滤 push-down、候选上限和原始分数/排名。
- **实际验证结果**：真实 Elasticsearch 全文、过滤、状态和排名集成测试通过。
- **计划偏差**：没有抽取 RAGFlow `FulltextQueryer`，也没有引入自定义中文 analyzer；保持 Elasticsearch 默认 analyzer 的明确边界。

### P06-T07：完善 Query Embedding 与向量检索

- **状态**：已完成
- **目标**：生成查询向量并执行 tenant/filter-aware KNN。
- **为什么需要**：语义召回核心。
- **输入**：P06-T02、P06-T05、Embedding Adapter。
- **前置任务**：P06-T02、P06-T05。
- **操作步骤**：规范化/批次/缓存；模型/维度匹配；KNN candidate window；filter pushdown；分数记录。
- **涉及文件**：query embedding、Search Adapter、测试。
- **预期输出**：向量候选。
- **RAGFlow 源码依据**：`Dealer.get_vector/search/_knn_scores`。
- **实现或复用方式**：LangChain Embeddings + 自研 Adapter。
- **测试方法**：维度、模型版本、过滤、Recall@K、错误。
- **验证命令**：`uv run pytest -q tests/integration/search/test_phase06_retrieval.py tests/integration/search/test_elasticsearch.py`
- **验收标准**：查询模型与索引兼容；权限 filter 生效。
- **风险和回滚方法**：不匹配直接错误，不跨 index_version 猜测。
- **实际执行结果**：复用内部 EmbeddingPort，在 Elasticsearch KNN 通道执行同一硬过滤并保留向量原始分数/排名。
- **实际验证结果**：真实 Elasticsearch KNN、索引版本、过滤和排名集成测试通过；CI 使用确定性 Fake Embedding。
- **计划偏差**：未加入查询向量缓存/批处理；当前单请求单查询变体逐次嵌入，性能优化留 Phase 10。

### P06-T08：实现混合召回与分数融合

- **状态**：已完成
- **目标**：合并全文/向量候选并生成可解释统一分数。
- **为什么需要**：单路召回覆盖不足且原始分数不可直接比较。
- **输入**：P06-T06、P06-T07。
- **前置任务**：P06-T06、P06-T07。
- **操作步骤**：候选 identity；归一化；加权/RRF 候选实验；保留原始分数；权重边界/稳定排序。
- **涉及文件**：`query/fuse.py`、测试/评测。
- **预期输出**：HybridCandidate。
- **RAGFlow 源码依据**：`Dealer.retrieval/rerank_with_knn`、`FusionExpr`。
- **实现或复用方式**：融合算法改造候选。
- **测试方法**：权重 0/1、重复、tie、后端分数尺度、Recall。
- **验证命令**：`uv run pytest -q tests/unit/retrieval/test_fusion_rerank.py tests/evaluation/retrieval/test_metrics.py`
- **验收标准**：每个候选可还原 text/vector/fused 分数。
- **风险和回滚方法**：默认 Profile 保留单路 fallback。
- **实际执行结果**：实现双通道候选按 `chunk_id` 去重、RRF `k=60`、稳定 tie-break，并保留全文/向量/融合分数与排名。
- **实际验证结果**：RRF、单通道、重复候选、tie 和真实 Elasticsearch 双路召回测试通过。
- **计划偏差**：没有实现加权分数归一化候选；ADR-021 已将 RRF 冻结为默认且唯一 Phase 06 融合算法。

### P06-T09：实现清理、Reranker、阈值与 TopK/TopN

- **状态**：已完成
- **目标**：移除无效/重复候选、执行 Rerank 并明确截断顺序。
- **为什么需要**：避免旧版本、孤儿、重复和低质量证据进入上下文。
- **输入**：P06-T08、Reranker Adapter。
- **前置任务**：P06-T08。
- **操作步骤**：清理规则/reason；每文档上限；批量 Rerank/超时；阈值；TopK candidate/TopN final；稳定 tie。
- **涉及文件**：`query/{clean,rerank}.py`、测试。
- **预期输出**：FinalCandidate 集。
- **RAGFlow 源码依据**：`_prune_deleted_chunks`、`rerank_by_model`、`_rerank_window`。
- **实现或复用方式**：清理参考重写；LangChain/供应商 Reranker；融合算法可改造。
- **测试方法**：孤儿/旧版/重复/空文本、超时、阈值边界。
- **验证命令**：`uv run pytest -q tests/unit/retrieval/test_fusion_rerank.py tests/unit/retrieval/test_online_pipeline_and_trace.py`
- **验收标准**：淘汰原因进入 Trace；模型失败有明确策略。
- **风险和回滚方法**：Reranker 超时回退融合分数且显式标记。
- **实际执行结果**：实现融合窗口后 Rerank、每文档限额、软阈值、最终 TopN；新增 BGE HTTP Adapter/内部 Port，超时、异常或身份集合变化时回退 RRF。
- **实际验证结果**：Fake Reranker 的排序、分数、超时、异常、非法候选和确定性截断测试通过。
- **计划偏差**：未进行真实 BGE Reranker/GPU 验证；不能报告真实模型质量或性能。

### P06-T10：实现空结果降级与重试

- **状态**：已完成
- **目标**：区分真空、阈值、过滤、后端错误并按 O-008 可控重试。
- **为什么需要**：空结果不能与故障混淆，也不能放宽权限。
- **输入**：P06-T03 至 P06-T09。
- **前置任务**：P06-T03 至 P06-T09。
- **操作步骤**：定义 empty_reason；配置去改写/降阈/减关键词等序列；硬性保留 tenant/visibility/KB；限制重试/预算；Trace。
- **涉及文件**：`query/fallback.py`、测试。
- **预期输出**：FallbackPolicy。
- **RAGFlow 源码依据**：`Dealer.search` 二次重查、metadata `None/[-999]`、`empty_response`。
- **实现或复用方式**：行为参考后自研。
- **测试方法**：各种空/故障、权限不变、预算终止。
- **验证命令**：`uv run pytest -q tests/unit/retrieval/test_filters_and_fallback.py tests/unit/retrieval/test_online_pipeline_and_trace.py`
- **验收标准**：后端错误不伪装空；任何重试不扩大授权。
- **风险和回滚方法**：默认保守/直接空结果；策略可关闭。
- **实际执行结果**：实现最多四步的候选扩大/软阈值下调/系统推断过滤移除/全文与向量单通道尝试；最终返回 `no_evidence`，依赖故障抛出结构化错误。
- **实际验证结果**：有限终止、真空与系统错误区分、所有硬过滤不变及 Trace 降级步骤测试通过。
- **计划偏差**：不按旧草案“去改写/减关键词”重试；查询变体固定，符合用户冻结的降级顺序。

### P06-T11：完善 Citation、Context 与 Retrieval Trace

- **状态**：已完成
- **目标**：记录所有查询变换/候选/分数/淘汰/模型/延迟并生成完整来源。
- **为什么需要**：回答、Agent Tool、评测和审计共享。
- **输入**：P06-T09、P06-T10、Phase 05 来源。
- **前置任务**：P06-T09、P06-T10。
- **操作步骤**：Context 预算/多样性；Citation 二次权限/版本/quote；Trace event；脱敏/保留；API 流式事件。
- **涉及文件**：`query/{context,citations,trace}.py`、API、测试。
- **预期输出**：RetrievalTrace/Citation v2。
- **RAGFlow 源码依据**：`kb_prompt/citation_prompt`、`Dealer.insert_citations`、`async_chat` Langfuse observation。
- **实现或复用方式**：引用算法改造候选；数据/Trace 自研。
- **测试方法**：可重放、引用正确率、删除/越权、脱敏。
- **验证命令**：`uv run pytest -q tests/unit/retrieval/test_online_pipeline_and_trace.py tests/integration/database/test_retrieval_trace_store.py tests/e2e/retrieval`
- **验收标准**：单次查询可完整还原；Citation 全部可验证。
- **风险和回滚方法**：Trace 最小化；敏感字段只记录摘要/ID。
- **实际执行结果**：固定 RAG 改用统一在线检索服务；公开回答仅返回 trace_id/来源。PostgreSQL Trace 只持久化摘要、ID、排名、分数、耗时、错误和降级，30 天 TTL；详细读取按 tenant 与角色控制，写失败不阻断检索并计数。
- **实际验证结果**：真实 PostgreSQL 租户隔离、内容最小化、权限、过期清理和真实 ES+PG E2E 通过；Trace 含融合、Rerank 和最终排名。
- **计划偏差**：未增加流式 Trace API；完整 Trace 由受限读取端点提供，聚合指标 180 天只保留策略边界，未建设长期指标仓库。

### P06-T12：建立评测并执行阶段验收

- **状态**：已完成
- **目标**：量化各检索步骤相对 Phase 04 基线的收益与成本。
- **为什么需要**：复杂链路必须由 Recall/MRR/NDCG/Citation 指标证明。
- **输入**：P06-T01 至 P06-T11。
- **前置任务**：P06-T01 至 P06-T11。
- **操作步骤**：版本化数据集；单路/混合/Rerank/扩展消融；后端契约；安全/E2E；更新文档/矩阵。
- **涉及文件**：evaluation suite/report、总体文档、本文件。
- **预期输出**：Phase 06 评测与出口报告。
- **RAGFlow 源码依据**：`test/benchmark` 仅性能参考，不替代质量评测。
- **实现或复用方式**：自行开发评测。
- **测试方法**：Unit/Contract/Integration/E2E/Evaluation/Security。
- **验证命令**：`uv run pytest -q`; `uv run ruff check .`; `uv run mypy src/ragflow_agent tests`; `uv run python scripts/check_secret_hygiene.py`
- **验收标准**：CAP-11 至 CAP-22 按真实结果验收；权限/Trace/Citation 零严重缺陷。
- **风险和回滚方法**：无收益功能保持关闭，不为通过删除困难样本。
- **实际执行结果**：实现 Recall@K、MRR、NDCG@K 小型确定性评测与消融夹具，执行 Unit/Integration/E2E、真实后端、静态、迁移、bootstrap、Compose、锁文件和密钥门禁。
- **实际验证结果**：隔离 PostgreSQL/MinIO/Redis/Elasticsearch 环境 `203 passed, 1 skipped`；唯一 skip 为本机未安装 Tesseract，与 Phase 06 无关。真实检索专项 `4 passed`。
- **计划偏差**：评测为无敏感信息的小型确定性夹具，不代表企业数据集或真实 BGE 质量；扩大数据集留 Phase 10。

## 8. 验收、DoD、风险与后续

**DoD**：P06-T01 至 P06-T12 完成；查询处理、双路/混合、融合、Rerank、降级、Citation/Trace 有代码和测试；质量相对基线量化；权限条件在所有分支保持；固定 RAG 使用统一服务；总文档同步。

| 风险 | 处理 |
|---|---|
| 后端分数不可比 | 归一化/融合消融，保存原分数 |
| 查询扩展噪声 | 变体上限和独立开关 |
| Reranker 成本/超时 | 批次、预算、显式 fallback |
| 降级越权 | 权限过滤不可删除，负向测试 |
| Trace 泄密 | 数据最小化、脱敏和保留策略 |

阶段结束更新总纲、架构、矩阵、复用、路线图、标准、风险、阶段索引和本文件。Phase 07 使用稳定版本/可见性字段；Phase 08 使用同一 KnowledgeQueryService。

## 9. 实际执行结果与出口结论

- **实际 Profile**：`retrieval-v2`；RRF `k=60`；候选、Rerank 窗口、最终 TopN、
  阈值、超时、每文档限额和最多四次降级均由配置约束。
- **实际模型边界**：DeepSeek 查询变换和 BGE Reranker 均经内部 Port/Adapter；
  本阶段只完成 Fake/Stub 确定性验证，没有真实 DeepSeek、BGE-M3 或 BGE
  Reranker 服务/GPU 质量声明。
- **真实基础设施**：隔离 PostgreSQL/MinIO/Redis/Elasticsearch 完整回归
  `203 passed, 1 skipped`；真实 ES+PG 在线检索/Trace 专项 `4 passed`。
- **安全与隐私**：硬过滤在全部降级分支保持；Trace 不持久化原查询、正文、
  Prompt、密钥或 Authorization；tenant/角色读取、30 天 TTL 与清理均有测试。
- **评测**：小型确定性夹具中混合结果 Recall@3 为 1.0，高于两条单通道的
  0.5；该结论只证明评测和融合行为，不代表真实模型或企业语料质量。
- **复用与许可**：直接复用/改造复用 RAGFlow 源码均为零；只使用固定 commit
  的公开行为证据，未触发衍生源码许可审查。
- **计划偏差**：`rewrite.py`、`translate.py`、`expand.py` 合并为统一
  `transforms.py`；`fuse.py` 实际命名 `fusion.py`；Citation/Context 沿用并扩展
  Phase 04 主链路；本地 Windows 真实 PG E2E 使用 Selector event loop。
- **阶段出口结论**：P06-T01 至 P06-T12 全部完成并通过本地门禁；提交、推送和
  GitHub Actions 证据在远程闭环后补记。Phase 07 仅具备计划复审入口，不在本阶段执行。
