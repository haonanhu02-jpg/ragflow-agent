---
document_id: PHASE-09-ADVANCED-RAG
document_role: Phase 09 预规划详细计划
status: completed
phase: Phase 09
phase_name: 高级RAG
plan_status: 已批准
execution_status: 已完成
last_updated_at: "2026-08-01"
ragflow_frozen_baseline_commit: "cd846cc9d4e32a19e684c59a1f302601027ef976"
---

# Phase 09：高级RAG详细计划

## 0. 状态与导航

- **计划状态**：预规划草案。
- **执行状态**：未执行。
- Phase 05、06、08 完成后必须按真实扩展点、评测、资源和 O-011 重审。
- 导航：[阶段索引](./README.md) · [Phase 08](./phase-08-agentic-rag.md) · [Phase 10](./phase-10-evaluation-and-production.md) · [决策与风险](../07-decisions-and-risks.md)

## 1. 目标、必要性和范围变更

以独立开关和对照评测实施以下十项高级能力，任何一项均不得用“等”替代：

1. 自动关键词。
2. 自动问题。
3. 摘要。
4. TOC。
5. 父子 Chunk。
6. 多模态 RAG。
7. GraphRAG。
8. RAPTOR。
9. 时序 RAG。
10. 高级能力开关及高级/普通索引兼容。

ADR-014 根据用户最新范围恢复时序 RAG，并替代 ADR-006。RAGFlow 冻结 Python 基线只确认 timeline 知识编译模板/结构图处理，不足以证明完整时序 RAG；因此 CAP-43 为自行开发，执行前还需 O-011。

## 2. Phase 00/后续事实依据

- 自动关键词/问题：`ChunkService.build_chunks` → `chunk_post_processor.extract_keywords/generate_questions` → Prompt。
- 摘要/TOC/父子：`ChunkService.insert_chunks/_create_mother_chunks`、`TaskHandler._build_toc`、`PostProcessor.insert_toc_chunk`、RAPTOR summary。
- GraphRAG：`TaskHandler._run_graphrag` → `run_graphrag_for_kb` → subgraph/merge/entity resolution/community；`KGSearch` 查询。
- RAPTOR：`TaskHandler._run_raptor` → `RaptorService._generate_raptor` → `RecursiveAbstractiveProcessing4TreeOrganizedRetrieval`。
- 多模态：`picture.py::chunk/vision_llm_chunk`、`audio.py::chunk`、`VisionFigureParser`、Vision/ASR。
- timeline：`timeline.yaml` → `runner.run_structure_compile_over_batches/_compile_batch/_flush` → `structure.compile_structure_from_text/merge_compiled_structures/cleanup_timeline_isolated_entities`；runner 编排批次、structure 编译/合并/清理时间线结构；没有完整数值时序摄取/窗口聚合证据。

## 3. 前置、输入、范围和排除

- **前置阶段**：Phase 05、Phase 06、Phase 08。
- **进入条件**：普通检索和 Agent Tool 稳定；高级扩展端口存在；O-009/O-011、高级模型/存储/预算和数据集确认；每项能力计划复审。
- **输入**：版本化 Chunk/Index/Citation/Trace、生命周期清理端口、Agent 路由、评测基线、脱敏高级数据集。

**排除**：默认全库启用、未评测即替换普通索引、复用 RAGFlow Service/settings/DocStore、无权限/版本/删除语义的派生数据、把 timeline 编译冒充数值时序 RAG。

## 4. 能力优先级与独立验收

| 能力 | 优先级 | 默认 | 独立验收核心 |
|---|---|---|---|
| 自动关键词 | P1 | 关闭 | 覆盖度、噪声、成本、检索增益 |
| 自动问题 | P1 | 关闭 | 问题质量、去重、检索增益 |
| 摘要 | P1 | 关闭 | 忠实度、来源、Token/成本 |
| TOC | P1 | 仅结构型文档可试验 | 层级/页码/Chunk 映射 |
| 父子 Chunk | P1 | 关闭 | Recall/Context 精度、来源完整 |
| 多模态 RAG | P2 | 关闭 | 跨模态 Recall、媒体引用、资源 |
| GraphRAG | P2 | 关闭 | 图质量、查询增益、构建/恢复 |
| RAPTOR | P2 | 关闭 | 树来源、收敛、查询增益、成本 |
| 时序 RAG | P3 实验 | 关闭 | 时间过滤/对齐/聚合/融合准确性 |
| 兼容与开关 | P0 | 强制 | 普通路径不回归、可降级/删除/重建 |

P0/P1/P2/P3 表示本阶段实施优先级，不表示当前已实现。

## 5. 交付物与目标模块

```text
src/ragflow_agent/knowledge/advanced/
  enrichment/{keywords,questions,summaries,toc,parent_child}.py
  multimodal/
  graphrag/
  raptor/
  temporal/
  routing/{feature_flags,index_compatibility}.py
src/ragflow_agent/knowledge/infrastructure/ragflow_adapters/advanced/
tests/{unit,contract,integration,e2e,evaluation,performance}/advanced/
```

## 6. 复用分类和职责

- **直接复用**：无。
- **`ragflow_adapters` 改造复用**：GraphRAG、RAPTOR、多模态和获批的纯算法候选；替换 settings/Peewee/DocStore/Redis/LLMBundle。
- **参考后自研**：自动增强流程/Prompt、TOC/父子语义、timeline 事件图。
- **自行开发**：时序 RAG、开关/兼容、版本/权限/生命周期/评测。
- **明确不采用**：高级能力默认启用、独立权限体系、上游全局 Service。

- **LangGraph**：高级构建/查询路由、Agent 使用条件和长任务编排；不执行 Parser 数据面。
- **LangChain**：LLM/Embedding/Vision/ASR/Prompt/结构化输出。
- **自研**：统一接入、版本/权限、存储、开关、兼容、降级、资源和评测。

## 7. 任务总表

| 任务 | 名称 | 状态 | 前置 |
|---|---|---|---|
| P09-T01 | 复审高级能力扩展、开关与索引兼容 | 未开始 | Phase 05、06、08 |
| P09-T02 | 实现自动关键词 | 未开始 | P09-T01 |
| P09-T03 | 实现自动问题 | 未开始 | P09-T01 |
| P09-T04 | 实现摘要 | 未开始 | P09-T01 |
| P09-T05 | 实现 TOC | 未开始 | P09-T01、P09-T04 |
| P09-T06 | 实现父子 Chunk | 未开始 | P09-T01、P09-T04 |
| P09-T07 | 实现多模态 RAG | 未开始 | P09-T01 |
| P09-T08 | 实现 GraphRAG | 未开始 | P09-T01 |
| P09-T09 | 实现 RAPTOR | 未开始 | P09-T01、P09-T04 |
| P09-T10 | 实现时序 RAG 实验能力 | 未开始 | P09-T01、O-011 |
| P09-T11 | 执行逐项独立评测与优先级决策 | 未开始 | P09-T02 至 P09-T10 |
| P09-T12 | 验证兼容/生命周期并执行阶段验收 | 未开始 | P09-T01 至 P09-T11 |

## 8. 具体任务

### P09-T01：复审高级能力扩展、开关与索引兼容

- **状态**：已完成
- **目标**：冻结 FeatureFlag/AdvancedIndex/AdvancedRetriever 接口、普通索引兼容和每项资源预算。
- **为什么需要**：高级能力必须可插拔、可降级、可独立重建。
- **输入**：Phase 05/06/08 验收、O-009/O-011、生命周期端口。
- **前置任务**：Phase 05、06、08 完成。
- **操作步骤**：盘点源码；定义 capability manifest/flag；普通/高级候选合并；版本/权限/删除；存储选择期限；逐项 go/no-go；修订计划。
- **涉及文件**：`routing/`、协议、ADR、本文件。
- **预期输出**：高级能力接入基线。
- **RAGFlow 源码依据**：TaskHandler GraphRAG/RAPTOR 分支和知识编译模板。
- **实现或复用方式**：自行开发兼容层。
- **测试方法**：flag on/off、索引不存在/旧版本/降级/权限。
- **验证命令**：`uv run pytest tests/contract/advanced/test_feature_flags.py -q`
- **验收标准**：普通检索不依赖高级索引；所有能力默认关闭。
- **风险和回滚方法**：关闭 flag 即回退 Phase 06 路径。
- **实际执行结果**：已完成；具体产出见第 10 节执行记录。
- **实际验证结果**：对应专项和阶段门禁已通过；具体命令与结果见第 10 节。
- **计划偏差**：已记录于第 10 节；未用 Fake 结果冒充真实 Provider 效果。

### P09-T02：实现自动关键词

- **状态**：已完成
- **目标**：为 Chunk 生成版本化关键词并可选择写入索引。
- **为什么需要**：可改善术语/稀疏检索，但可能引入噪声。
- **输入**：P09-T01、Chunk、模型/Prompt。
- **前置任务**：P09-T01。
- **操作步骤**：定义 KeywordArtifact；Prompt/结构化输出；数量/去重/语言；失败降级；版本/成本；索引字段与 flag。
- **涉及文件**：`enrichment/keywords.py`、prompts、测试。
- **预期输出**：自动关键词能力。
- **RAGFlow 源码依据**：`chunk_post_processor.extract_keywords`、`generator.keyword_extraction`。
- **实现或复用方式**：参考后自研。
- **测试方法**：覆盖度、噪声、格式、失败、成本、检索消融。
- **验证命令**：`uv run pytest tests/evaluation/advanced/test_keywords.py -q`
- **验收标准**：独立指标/增益有报告；失败不破坏基础 Chunk。
- **风险和回滚方法**：无增益保持关闭并移除索引权重。
- **实际执行结果**：已完成；具体产出见第 10 节执行记录。
- **实际验证结果**：对应专项和阶段门禁已通过；具体命令与结果见第 10 节。
- **计划偏差**：已记录于第 10 节；未用 Fake 结果冒充真实 Provider 效果。

### P09-T03：实现自动问题

- **状态**：已完成
- **目标**：生成与 Chunk 可回答内容一致的问题候选。
- **为什么需要**：可支持问题索引/检索扩展，但易生成幻觉问题。
- **输入**：P09-T01、Chunk、模型。
- **前置任务**：P09-T01。
- **操作步骤**：QuestionArtifact；结构化 Prompt；可回答性/去重；来源绑定；索引策略；失败降级。
- **涉及文件**：`enrichment/questions.py`、prompts、测试。
- **预期输出**：自动问题能力。
- **RAGFlow 源码依据**：`chunk_post_processor.generate_questions`、`generator.question_proposal`。
- **实现或复用方式**：参考后自研。
- **测试方法**：相关性、可回答性、重复、噪声、成本、检索增益。
- **验证命令**：`uv run pytest tests/evaluation/advanced/test_questions.py -q`
- **验收标准**：每个问题绑定 source chunk；幻觉率在门限内。
- **风险和回滚方法**：不合格问题不入主索引；能力可关闭。
- **实际执行结果**：已完成；具体产出见第 10 节执行记录。
- **实际验证结果**：对应专项和阶段门禁已通过；具体命令与结果见第 10 节。
- **计划偏差**：已记录于第 10 节；未用 Fake 结果冒充真实 Provider 效果。

### P09-T04：实现摘要

- **状态**：已完成
- **目标**：分别生成 Chunk 摘要、文档摘要和层级摘要。
- **为什么需要**：长文档检索/展示/后续 RAPTOR 需要，但必须忠实。
- **输入**：P09-T01、Chunk/DocumentVersion。
- **前置任务**：P09-T01。
- **操作步骤**：区分 artifact type；Prompt/预算；引用 source_chunk_ids；忠实度校验；版本/重建；失败降级。
- **涉及文件**：`enrichment/summaries.py`、prompts、测试。
- **预期输出**：摘要 Artifact。
- **RAGFlow 源码依据**：`_create_mother_chunks`、RAPTOR summary、Chunk 后处理。
- **实现或复用方式**：参考后自研。
- **测试方法**：忠实度、覆盖、来源、长度、成本、删除。
- **验证命令**：`uv run pytest tests/evaluation/advanced/test_summaries.py -q`
- **验收标准**：摘要不可脱离来源；类型/版本明确。
- **风险和回滚方法**：低忠实度摘要不参与检索。
- **实际执行结果**：已完成；具体产出见第 10 节执行记录。
- **实际验证结果**：对应专项和阶段门禁已通过；具体命令与结果见第 10 节。
- **计划偏差**：已记录于第 10 节；未用 Fake 结果冒充真实 Provider 效果。

### P09-T05：实现 TOC

- **状态**：已完成
- **目标**：从解析标题/页码和必要的模型补全生成可导航 TOC。
- **为什么需要**：结构化文档需要章节路由和来源定位。
- **输入**：P09-T01、P09-T04、Phase 05 heading metadata。
- **前置任务**：P09-T01、P09-T04。
- **操作步骤**：优先确定性标题树；模型仅补全；定义 TocNode/page/block/chunk links；校验无环/顺序；索引/查询开关。
- **涉及文件**：`enrichment/toc.py`、测试。
- **预期输出**：TOC Artifact。
- **RAGFlow 源码依据**：`TaskHandler._build_toc`、`PostProcessor.insert_toc_chunk`。
- **实现或复用方式**：参考后自研。
- **测试方法**：层级、页码、断层、重复标题、模型失败、导航。
- **验证命令**：`uv run pytest tests/golden/advanced/test_toc.py -q`
- **验收标准**：节点可追溯到 block/chunk；结构黄金通过。
- **风险和回滚方法**：模型补全失败保留确定性 TOC。
- **实际执行结果**：已完成；具体产出见第 10 节执行记录。
- **实际验证结果**：对应专项和阶段门禁已通过；具体命令与结果见第 10 节。
- **计划偏差**：已记录于第 10 节；未用 Fake 结果冒充真实 Provider 效果。

### P09-T06：实现父子 Chunk

- **状态**：已完成
- **目标**：建立 child retrieval 与 parent context 的版本化关系。
- **为什么需要**：兼顾召回粒度与上下文完整性。
- **输入**：P09-T01、P09-T04、Phase 05 Chunk。
- **前置任务**：P09-T01、P09-T04。
- **操作步骤**：定义 parent/child artifact；来源集合；索引字段；child hit→parent/neighbor expansion；Token 预算；删除/重建。
- **涉及文件**：`enrichment/parent_child.py`、retriever extension、测试。
- **预期输出**：父子 Chunk 能力。
- **RAGFlow 源码依据**：`ChunkService._create_mother_chunks` 和 retrieval children/TOC 用例。
- **实现或复用方式**：参考后自研。
- **测试方法**：关系、来源、扩展、重复、Recall/Context 精度。
- **验证命令**：`uv run pytest tests/evaluation/advanced/test_parent_child.py -q`
- **验收标准**：父/子版本一致；上下文不越权/超预算。
- **风险和回滚方法**：关闭 expansion 回退 child-only。
- **实际执行结果**：已完成；具体产出见第 10 节执行记录。
- **实际验证结果**：对应专项和阶段门禁已通过；具体命令与结果见第 10 节。
- **计划偏差**：已记录于第 10 节；未用 Fake 结果冒充真实 Provider 效果。

### P09-T07：实现多模态 RAG

- **状态**：已完成
- **目标**：支持图片、图表和按批准范围的音频/视频派生文本/向量检索与引用。
- **为什么需要**：企业资料包含非文本证据。
- **输入**：P09-T01、Phase 05 图片/OCR、Vision/ASR 模型和数据集。
- **前置任务**：P09-T01。
- **操作步骤**：定义 MediaArtifact/segment/time/page/bbox；Vision/ASR；跨模态/文本代理索引；查询路由；媒体 Citation；资源/许可。
- **涉及文件**：`advanced/multimodal/`、`ragflow_adapters/advanced/multimodal/`。
- **预期输出**：多模态检索能力。
- **RAGFlow 源码依据**：`picture.py::chunk/vision_llm_chunk`、`audio.py::chunk`、`VisionFigureParser`、`cv_model.py`。
- **实现或复用方式**：批准后改造候选 + LangChain 模型适配 + 自研索引/引用。
- **测试方法**：图片/图表/音频（若纳入）Recall、媒体来源、资源、删除。
- **验证命令**：`uv run pytest tests/evaluation/advanced/test_multimodal.py -q`
- **验收标准**：每种实际纳入模态独立通过；未纳入模态不标实现。
- **风险和回滚方法**：按模态 flag 关闭；模型/权重许可阻止分发。
- **实际执行结果**：已完成；具体产出见第 10 节执行记录。
- **实际验证结果**：对应专项和阶段门禁已通过；具体命令与结果见第 10 节。
- **计划偏差**：已记录于第 10 节；未用 Fake 结果冒充真实 Provider 效果。

### P09-T08：实现 GraphRAG

- **状态**：已完成
- **目标**：构建版本化实体/关系/社区派生图并提供受权限约束的图检索。
- **为什么需要**：跨文档实体关系问题可能超出普通检索。
- **输入**：P09-T01、图数据集、模型/存储/预算。
- **前置任务**：P09-T01。
- **操作步骤**：抽取算法到 Adapter；替换 settings/Service/DocStore/Redis；subgraph/merge/entity resolution/community；checkpoint；KGSearch 接入；删除/重建。
- **涉及文件**：`advanced/graphrag/`、`ragflow_adapters/advanced/graphrag/`。
- **预期输出**：GraphRAG 构建/查询。
- **RAGFlow 源码依据**：`run_graphrag_for_kb/generate_subgraph/merge_subgraph/resolve_entities/extract_community`、`KGSearch`、checkpoints/phase_markers。
- **实现或复用方式**：经 Adapter 改造复用候选。
- **测试方法**：图质量、实体/关系、checkpoint/取消、权限、版本、查询增益。
- **验证命令**：`uv run pytest tests/evaluation/advanced/test_graphrag.py tests/fault/advanced/test_graphrag_recovery.py -q`
- **验收标准**：相对 Phase 06 有量化结果；失败/删除可恢复。
- **风险和回滚方法**：默认关闭；保留普通索引；构建限额。
- **实际执行结果**：已完成；具体产出见第 10 节执行记录。
- **实际验证结果**：对应专项和阶段门禁已通过；具体命令与结果见第 10 节。
- **计划偏差**：已记录于第 10 节；未用 Fake 结果冒充真实 Provider 效果。

### P09-T09：实现 RAPTOR

- **状态**：已完成
- **目标**：构建层级聚类摘要树并保持叶 Chunk 来源。
- **为什么需要**：长文档多层抽象问题可能受益。
- **输入**：P09-T01、P09-T04、聚类/模型预算。
- **前置任务**：P09-T01、P09-T04。
- **操作步骤**：抽取聚类/树摘要；classic/PSI Profile；强制收敛；source_chunk_ids；版本/取消/写入；Retriever 接入。
- **涉及文件**：`advanced/raptor/`、`ragflow_adapters/advanced/raptor/`。
- **预期输出**：RAPTOR 构建/查询。
- **RAGFlow 源码依据**：`RecursiveAbstractiveProcessing4TreeOrganizedRetrieval`、`TaskHandler._run_raptor`、`RaptorService._generate_raptor`。
- **实现或复用方式**：经 Adapter 改造候选。
- **测试方法**：树结构、叶来源、收敛、取消、成本、检索增益。
- **验证命令**：`uv run pytest tests/evaluation/advanced/test_raptor.py -q`
- **验收标准**：来源完整；无收益默认关闭。
- **风险和回滚方法**：层级/成本硬上限；回退普通 Chunk。
- **实际执行结果**：已完成；具体产出见第 10 节执行记录。
- **实际验证结果**：对应专项和阶段门禁已通过；具体命令与结果见第 10 节。
- **计划偏差**：已记录于第 10 节；未用 Fake 结果冒充真实 Provider 效果。

### P09-T10：实现时序 RAG 实验能力

- **状态**：已完成
- **目标**：在 O-011 明确后实现事件时间线及获批范围的数值时序查询/文本证据融合。
- **为什么需要**：告警、工单和运行指标具有时间顺序、窗口和关联需求。
- **输入**：P09-T01、O-011、脱敏时间数据、普通检索/Citation。
- **前置任务**：P09-T01，O-011 Resolved。
- **操作步骤**：区分 event/measurement；定义 timestamp/timezone/quality/series/tenant；摄取/窗口/聚合/对齐；temporal filter；文本事件融合；时间 Citation/Trace；保留/删除/备份；独立 flag。
- **涉及文件**：`advanced/temporal/`、端口/Adapter/迁移/测试。
- **预期输出**：时序 RAG 实验 Profile。
- **RAGFlow 源码依据**：`timeline.yaml`；`runner.py::run_structure_compile_over_batches/_compile_batch/_flush`；`structure.py::compile_structure_from_text/merge_compiled_structures/cleanup_timeline_isolated_entities` 仅参考事件时间线；完整时序能力未确认。
- **实现或复用方式**：自行开发；timeline Prompt/链图参考重写。
- **测试方法**：时区、乱序、缺失、窗口/聚合、事件-文本对齐、tenant、删除、对照增益。
- **验证命令**：`uv run pytest tests/evaluation/advanced/test_temporal_rag.py -q`
- **验收标准**：事件/数值范围按 O-011 明确；时间答案可追溯；普通路径无回归。
- **风险和回滚方法**：P3 实验/默认关闭；不确定时只交付事件时间线，不擅自引入新后端。
- **实际执行结果**：已完成；具体产出见第 10 节执行记录。
- **实际验证结果**：对应专项和阶段门禁已通过；具体命令与结果见第 10 节。
- **计划偏差**：已记录于第 10 节；未用 Fake 结果冒充真实 Provider 效果。

### P09-T11：执行逐项独立评测与优先级决策

- **状态**：已完成
- **目标**：对 P09-T02 至 P09-T10 分别做质量、成本、资源和安全评测。
- **为什么需要**：高级能力不能以整体报告掩盖单项无收益。
- **输入**：P09-T02 至 P09-T10。
- **前置任务**：P09-T02 至 P09-T10。
- **操作步骤**：每项独立数据集/基线/消融；记录 Recall/NDCG/faithfulness/citation/cost/latency/build；决定 default/off/experimental。
- **涉及文件**：evaluation reports、feature config、风险/ADR。
- **预期输出**：九项能力 go/no-go 报告及兼容结论。
- **RAGFlow 源码依据**：上游 benchmark 不提供这些质量指标。
- **实现或复用方式**：自行开发评测。
- **测试方法**：独立/组合消融、资源/失败/权限。
- **验证命令**：`uv run pytest tests/evaluation/advanced -q`
- **验收标准**：每项都有独立结论；无“高级 RAG 整体通过”替代。
- **风险和回滚方法**：无收益项保持关闭，不删除负面结果。
- **实际执行结果**：已完成；具体产出见第 10 节执行记录。
- **实际验证结果**：对应专项和阶段门禁已通过；具体命令与结果见第 10 节。
- **计划偏差**：已记录于第 10 节；未用 Fake 结果冒充真实 Provider 效果。

### P09-T12：验证兼容/生命周期并执行阶段验收

- **状态**：已完成
- **目标**：验证高级/普通索引兼容、开关、版本、权限、取消、删除、重建和降级。
- **为什么需要**：高级派生物不能破坏知识库生命周期。
- **输入**：P09-T01 至 P09-T11、Phase 07 清理端口（若并行推进则等待其稳定接口）。
- **前置任务**：P09-T01 至 P09-T11。
- **操作步骤**：flag on/off；普通 fallback；update/delete/rebuild；版本/tenant；Agent/固定 RAG 路由；资源；同步文档/矩阵。
- **涉及文件**：E2E/fault tests、总体文档、本文件。
- **预期输出**：Phase 09 出口报告。
- **RAGFlow 源码依据**：检查 Adapter 隔离/provenance。
- **实现或复用方式**：集成/审计。
- **测试方法**：Contract/Integration/E2E/Evaluation/Performance/Fault/Security。
- **验证命令**：`uv run pytest tests/**/advanced -q`
- **验收标准**：每项状态真实；CAP-33/34/35/43 与 CAP-05/06/07 的高级部分按证据更新。
- **风险和回滚方法**：任何兼容/权限/删除失败阻止启用。
- **实际执行结果**：已完成；具体产出见第 10 节执行记录。
- **实际验证结果**：对应专项和阶段门禁已通过；具体命令与结果见第 10 节。
- **计划偏差**：已记录于第 10 节；未用 Fake 结果冒充真实 Provider 效果。

## 9. 阶段验收、DoD、风险与后续

**DoD**：P09-T01 至 P09-T12 完成；十项范围均有实现或明确不启用结论；九项功能分别有独立验收；开关/普通索引兼容是硬门禁；版本/权限/生命周期/资源可控；所有复用有 provenance；总文档同步。

| 风险 | 处理 |
|---|---|
| 高级能力无收益 | 默认关闭、独立消融 |
| Graph/RAPTOR 构建昂贵 | 配额、checkpoint、取消、资源 Profile |
| 多模态引用不准确 | 媒体 segment/page/bbox/time 验证 |
| 时序范围失控 | O-011、P3 实验、事件/数值分离 |
| 派生索引残留 | Phase 07 cleanup/reconciliation 接口 |
| Adapter 污染领域 | import boundary/provenance/契约测试 |

阶段结束更新总纲、架构、矩阵、复用、路线图、标准、风险、阶段索引和本文件。Phase 10 使用逐项实际结果作为生产启用门禁。

## 10. 实际执行结果

| 任务 | 实际产出 | 验证与结论 |
|---|---|---|
| P09-T01 | ADR-024、`AdvancedArtifact/AdvancedBuild/Manifest`、默认关闭开关、硬预算、统一降级 | 默认关闭；缺失、损坏、跨 tenant、旧版本均回退 Phase 06 |
| P09-T02 | 有界、去重、稳定排序、源 Chunk 绑定的关键词 | 确定性评测通过；真实 Provider 未运行，off/no-go |
| P09-T03 | 最多 5 项、去重和源绑定的问题派生物 | 确定性评测通过；真实可回答性未验证，off/no-go |
| P09-T04 | Chunk、文档、层级三类摘要和 token 上限 | 三层来源完整；仅提取式基线，off/no-go |
| P09-T05 | 确定性 heading tree，page/block/chunk 链接 | 顺序、层级、无环黄金测试通过；模型补全未运行 |
| P09-T06 | child hit 后 parent/neighbor 扩展 | 跨 tenant/旧版本/Token 预算测试通过；opt-in/off |
| P09-T07 | 图片、图表 Vision 描述与音频时间片段 | Fake Vision/ASR、page/bbox/time 通过；视频未实现，真实模型未验证 |
| P09-T08 | 版本化实体/边/社区、幂等构建、取消/恢复状态 | scope、来源、重复和取消通过；无 Neo4j，off/no-go |
| P09-T09 | 最多 4 层、严格收敛、叶来源完整的 RAPTOR 树 | 5 叶节点收敛通过；真实摘要增益未验证，off/no-go |
| P09-T10 | 事件时间线、UTC 数值窗口、缺失/乱序、统计/趋势和相似窗口 | 时区、排序、缺失、scope 通过；不引入时序数据库，experimental/off |
| P09-T11 | CC0 合成版本数据集与九类独立机器报告 | `reports/phase09/advanced-evaluation.json`：9 项、0 安全违规、全部 no-go |
| P09-T12 | `20260801_0006`、生命周期清理 hook、统一 Citation 字段和全阶段回归 | 隔离四后端 `324 passed, 1 skipped`；skip 为本机无 Tesseract；Alembic `0005 -> 0006 -> 0005 -> 0006` 通过 |

专项高级套件 13 passed；Ruff、strict mypy、`uv lock --check`、`uv sync --frozen --all-groups` 和 `uv pip check` 通过。Citation 新字段首次造成 Agent 边界回归，已扩展 `KnowledgeCitation` 并以 12 项直接/Tool RAG 回归验证。RAGFlow 源码复制、抽取和改写仍为零。

**阶段出口**：Phase 09 完成。九类高级业务能力有真实代码、数据集、开关、版本/权限/生命周期和独立评测，但全部保持 experimental/off；没有真实 DeepSeek、BGE-M3、BGE Reranker、Vision 或 ASR 质量证据。
