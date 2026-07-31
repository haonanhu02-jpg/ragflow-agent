---
document_id: PHASE-06-ONLINE-RETRIEVAL
document_role: Phase 06 预规划详细计划
status: draft
phase: Phase 06
phase_name: 在线检索
plan_status: 预规划草案
execution_status: 未执行
last_updated_at: "2026-07-31"
ragflow_frozen_baseline_commit: "cd846cc9d4e32a19e684c59a1f302601027ef976"
---

# Phase 06：在线检索详细计划

## 0. 状态与导航

- **计划状态**：预规划草案。
- **执行状态**：未执行。
- **前置阶段事实**：Phase 04、Phase 05 已完成；现有基线为 Elasticsearch
  BM25/KNN/RRF、统一 SearchPort、schema v2 Chunk metadata、Citation bbox
  和多格式测试集。
- **准入判断**：阶段依赖已满足，可以进入正式计划复审；O-008、
  Reranker/融合/Trace 保留策略和本计划确认尚未完成，因此当前不得执行
  P06-T01。
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
| P06-T01 | 复审查询协议、Profile 与评测基线 | 未开始 | Phase 04、05 |
| P06-T02 | 实现查询规范化与预处理 | 未开始 | P06-T01 |
| P06-T03 | 实现多轮问题改写 | 未开始 | P06-T02 |
| P06-T04 | 实现跨语言与关键词扩展 | 未开始 | P06-T02 |
| P06-T05 | 实现元数据 AST 与权限过滤 | 未开始 | P06-T01、P06-T02 |
| P06-T06 | 完善全文检索 | 未开始 | P06-T02、P06-T05 |
| P06-T07 | 完善 Query Embedding 与向量检索 | 未开始 | P06-T02、P06-T05 |
| P06-T08 | 实现混合召回与分数融合 | 未开始 | P06-T06、P06-T07 |
| P06-T09 | 实现清理、Reranker、阈值与 TopK/TopN | 未开始 | P06-T08 |
| P06-T10 | 实现空结果降级与重试 | 未开始 | P06-T03 至 P06-T09 |
| P06-T11 | 完善 Citation、Context 与 Retrieval Trace | 未开始 | P06-T09、P06-T10 |
| P06-T12 | 建立评测并执行阶段验收 | 未开始 | P06-T01 至 P06-T11 |

## 7. 具体任务

### P06-T01：复审查询协议、Profile 与评测基线

- **状态**：未开始
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
- **验证命令**：按实际 Adapter 记录。
- **验收标准**：所有待决策有结论或明确 fallback。
- **风险和回滚方法**：保持 Phase 04 Profile 可回退。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待记录。

### P06-T02：实现查询规范化与预处理

- **状态**：未开始
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
- **验证命令**：`uv run pytest tests/unit/retrieval/test_preprocess.py -q`
- **验收标准**：原始/规范查询同时入 Trace。
- **风险和回滚方法**：规范化规则版本化，可回退原查询。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待记录。

### P06-T03：实现多轮问题改写

- **状态**：未开始
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
- **验证命令**：`uv run pytest tests/unit/retrieval/test_rewrite.py -q`
- **验收标准**：失败回到规范查询；不改变权限。
- **风险和回滚方法**：Profile 可关闭改写。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待记录。

### P06-T04：实现跨语言与关键词扩展

- **状态**：未开始
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
- **验证命令**：`uv run pytest tests/unit/retrieval/test_query_expansion.py -q`
- **验收标准**：变体有来源/语言/成本；原查询始终保留。
- **风险和回滚方法**：噪声超阈则关闭对应扩展。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待记录。

### P06-T05：实现元数据 AST 与权限过滤

- **状态**：未开始
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
- **验证命令**：`uv run pytest tests/unit/retrieval/test_filters.py tests/contract/search/test_filters.py -q`
- **验收标准**：权限不可移除；不同后端契约一致。
- **风险和回滚方法**：未知操作符拒绝，不降级全量查询。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待记录。

### P06-T06：完善全文检索

- **状态**：未开始
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
- **验证命令**：`uv run pytest tests/integration/retrieval/test_fulltext.py -q`
- **验收标准**：全文 baseline 可复现；分数来源明确。
- **风险和回滚方法**：Analyzer 变化绑定 index_version。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待记录。

### P06-T07：完善 Query Embedding 与向量检索

- **状态**：未开始
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
- **验证命令**：`uv run pytest tests/integration/retrieval/test_vector.py -q`
- **验收标准**：查询模型与索引兼容；权限 filter 生效。
- **风险和回滚方法**：不匹配直接错误，不跨 index_version 猜测。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待记录。

### P06-T08：实现混合召回与分数融合

- **状态**：未开始
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
- **验证命令**：`uv run pytest tests/unit/retrieval/test_fusion.py -q`
- **验收标准**：每个候选可还原 text/vector/fused 分数。
- **风险和回滚方法**：默认 Profile 保留单路 fallback。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待记录。

### P06-T09：实现清理、Reranker、阈值与 TopK/TopN

- **状态**：未开始
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
- **验证命令**：`uv run pytest tests/unit/retrieval/test_clean_rerank.py -q`
- **验收标准**：淘汰原因进入 Trace；模型失败有明确策略。
- **风险和回滚方法**：Reranker 超时回退融合分数且显式标记。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待记录。

### P06-T10：实现空结果降级与重试

- **状态**：未开始
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
- **验证命令**：`uv run pytest tests/unit/retrieval/test_fallback.py -q`
- **验收标准**：后端错误不伪装空；任何重试不扩大授权。
- **风险和回滚方法**：默认保守/直接空结果；策略可关闭。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待记录。

### P06-T11：完善 Citation、Context 与 Retrieval Trace

- **状态**：未开始
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
- **验证命令**：`uv run pytest tests/unit/retrieval/test_trace_citation.py -q`
- **验收标准**：单次查询可完整还原；Citation 全部可验证。
- **风险和回滚方法**：Trace 最小化；敏感字段只记录摘要/ID。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待记录。

### P06-T12：建立评测并执行阶段验收

- **状态**：未开始
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
- **验证命令**：`uv run pytest tests/**/retrieval -q`; `uv run <evaluation-command>`
- **验收标准**：CAP-11 至 CAP-22 按真实结果验收；权限/Trace/Citation 零严重缺陷。
- **风险和回滚方法**：无收益功能保持关闭，不为通过删除困难样本。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待记录。

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

## 9. 实际执行结果预留

- 实际 Profile/模型/策略：待执行。
- 实际指标/安全/后端契约结果：待执行。
- 实际偏差和新增决策：待执行。
- 阶段出口结论：待执行。
