---
document_id: PHASE-08-AGENTIC-RAG
document_role: Phase 08 预规划详细计划
status: draft
phase: Phase 08
phase_name: Agentic RAG
plan_status: 预规划草案
execution_status: 未执行
last_updated_at: "2026-07-30"
ragflow_frozen_baseline_commit: "cd846cc9d4e32a19e684c59a1f302601027ef976"
---

# Phase 08：Agentic RAG详细计划

## 0. 状态与导航

- **计划状态**：预规划草案。
- **执行状态**：未执行。
- Phase 02、06 完成后按真实 Agent Runtime、KnowledgeQueryService、权限和 Trace 重审。
- 导航：[阶段索引](./README.md) · [Phase 06](./phase-06-online-retrieval.md) · [Phase 07](./phase-07-document-lifecycle.md) · [Phase 09](./phase-09-advanced-rag.md)

## 1. 目标、必要性与 Phase 00 依据

让 LangGraph Agent 通过正式 Tool 使用知识库和受控外部能力，完成查询规划/分解、多次检索、证据检查、Tool 选择、SQL/API Tool、完整 HITL、短期/长期记忆和循环/Token/时间/费用预算。

Phase 00 确认 RAGFlow `Retrieval._retrieve_kb` 直接调用 `settings.retriever.retrieval` 并回写引用，Agentic RAG 是六节点固定图，Canvas 是自定义运行时。目标只参考 Tool 参数、证据检查和节点需求；运行时用 Phase 02 LangGraph，查询只经 Phase 06 `KnowledgeQueryService`。

## 2. 前置、输入、范围与排除

- **前置阶段**：Phase 02、Phase 06。
- **进入条件**：Phase 02 Agent Checkpoint/Trace/错误恢复稳定；统一查询/Citation/Trace 通过；HITL、预算、记忆、Tool 安全及 SQL/API 凭据策略和评测场景确认；本计划复审。
- **输入**：Agent Runtime、KnowledgeQueryService、AuthorizationContext、Retrieval DTO、Tool policy、评测数据和运行成本基线。

**范围**：KB Tool、Agent direct retrieval service、计划/分解、多轮检索、证据充分性、Tool 路由、只读/受限 SQL、allowlisted API、HITL、短期/长期记忆、预算/终止/Trace/恢复，以及有对照收益才启用的多 Agent 协作。

**排除**：Agent 直连 Search/DB；复制 Canvas；固定 RAG 强制进图；默认多 Agent；任意 SQL/URL；GraphRAG/RAPTOR 构建；未经批准的写操作。

## 3. 交付物和目标模块

```text
src/<package>/agent/
  tools/{knowledge_base,sql,api}.py
  graphs/agentic_rag.py
  nodes/{plan,retrieve,evaluate,select_tool,memory,finalize}.py
  application/{tool_policy,memory,budgets}.py
tests/{unit,contract,integration,e2e,evaluation,security}/agentic_rag/
```

## 4. RAGFlow 源码与采用

| 源码/调用关系 | 采用 |
|---|---|
| `agent/tools/retrieval.py::Retrieval._retrieve_kb` → `settings.retriever.retrieval` → TOC/children/KG → `Canvas.add_reference/kb_prompt` | 参数/引用返回参考重写 |
| `agentic_rag_graph.py::AgenticState/build_agentic_graph/run_agentic_rag` | 节点和证据检查用例参考 |
| `rag/advanced_rag/agentic_rag.py::RAGTools` | Tool 能力面参考 |
| `agent/canvas.py::Canvas.run/_run_impl` | 明确不采用运行时；参考 HITL/事件用例 |

- **直接复用**：无。
- **`ragflow_adapters` 改造复用**：无默认。
- **参考后自研**：KB Tool 参数、查询分解/证据判断节点。
- **明确不采用**：Canvas、Agent 直连 retriever/settings、无 checkpoint 图、模型生成 tenant/SQL/URL 直接执行。

## 5. 框架与自研职责

- **LangGraph**：计划/检索/检查/重试/Tool/HITL/记忆路由、Checkpoint、终止。
- **LangChain**：KnowledgeBase/SQL/API Tool Schema，模型、Prompt、结构化输出。
- **自研**：Tool policy、权限/凭据、共享服务、SQL/API 沙箱、记忆治理、证据判定、预算、审计和评测。

## 6. 任务总表

| 任务 | 名称 | 状态 | 前置 |
|---|---|---|---|
| P08-T01 | 复审场景、Tool 策略和预算 | 未开始 | Phase 02、06 |
| P08-T02 | 实现 KnowledgeBaseTool | 未开始 | P08-T01 |
| P08-T03 | 实现 Agent 直接检索接口 | 未开始 | P08-T02 |
| P08-T04 | 实现查询规划与分解 | 未开始 | P08-T02、P08-T03 |
| P08-T05 | 实现多次检索与证据检查 | 未开始 | P08-T04 |
| P08-T06 | 实现 Tool 选择和统一执行策略 | 未开始 | P08-T01、P08-T05 |
| P08-T07 | 实现受控 SQL Tool | 未开始 | P08-T06 |
| P08-T08 | 实现受控 API Tool | 未开始 | P08-T06 |
| P08-T09 | 实现 HITL 与高风险审批 | 未开始 | P08-T06 至 P08-T08 |
| P08-T10 | 实现短期与长期记忆 | 未开始 | P08-T01、P08-T09 |
| P08-T11 | 完善预算、Trace、恢复与终止 | 未开始 | P08-T02 至 P08-T10 |
| P08-T12 | 评测并按需实现多 Agent 协作 | 未开始 | P08-T04 至 P08-T11 |
| P08-T13 | 建立 Agentic RAG E2E/评测并验收 | 未开始 | P08-T01 至 P08-T12 |

## 7. 具体任务

### P08-T01：复审场景、Tool 策略和预算

- **状态**：未开始
- **目标**：冻结首批 Agentic 场景、Tool allowlist、审批和预算。
- **为什么需要**：预计划不能替代真实模型、权限和成本数据。
- **输入**：Phase 02/06 验收、Agent 评测集、O-008/O-009。
- **前置任务**：Phase 02、06 完成。
- **操作步骤**：盘点源码；定义成功/终止；决定 SQL/API 只读范围；预算/阈值；记忆范围；修订计划/ADR。
- **涉及文件**：本文件、Tool policy、风险登记。
- **预期输出**：Agentic 执行 Profile。
- **RAGFlow 源码依据**：Agentic 图和 Retrieval Tool 能力面。
- **实现或复用方式**：审计/自研。
- **测试方法**：威胁建模与场景评审。
- **验证命令**：按实际安全/模型 probe 记录。
- **验收标准**：所有副作用、凭据和审批边界明确。
- **风险和回滚方法**：不明确 Tool 默认禁用。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待记录。

### P08-T02：实现 KnowledgeBaseTool

- **状态**：未开始
- **目标**：以 LangChain Tool 包装统一 KnowledgeQueryService。
- **为什么需要**：Agent 不能复制或绕过检索。
- **输入**：P08-T01、Phase 06 查询协议。
- **前置任务**：P08-T01。
- **操作步骤**：定义输入/输出 Schema；注入 AuthorizationContext；调用查询服务；返回 candidates/citations/trace_ref/empty_reason；结构化错误。
- **涉及文件**：`tools/knowledge_base.py`、测试。
- **预期输出**：正式 KB Tool。
- **RAGFlow 源码依据**：`RetrievalParam`、`Retrieval._retrieve_kb`。
- **实现或复用方式**：LangChain Tool + 参考重写。
- **测试方法**：与固定 RAG 候选对比、越权、空结果、超时。
- **验证命令**：`uv run pytest tests/contract/agentic_rag/test_kb_tool.py -q`
- **验收标准**：同配置候选可对比；Tool 不接受模型 tenant。
- **风险和回滚方法**：失败返回 typed error，不改用直连 Search。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待记录。

### P08-T03：实现 Agent 直接检索接口

- **状态**：未开始
- **目标**：为节点提供非自然语言包装的结构化检索调用。
- **为什么需要**：规划/证据检查需要访问 RetrievalResult，而不是解析 Tool 文本。
- **输入**：P08-T02、Agent Runtime。
- **前置任务**：P08-T02。
- **操作步骤**：定义 `AgentKnowledgeGateway`；继承 context；调用相同服务；预算/trace；禁止基础设施对象。
- **涉及文件**：Agent application gateway、测试。
- **预期输出**：Agent 内部统一检索接口。
- **RAGFlow 源码依据**：上游 Tool 直连 retriever 是需避免的耦合。
- **实现或复用方式**：自行开发。
- **测试方法**：KB Tool/Gateway 一致性、权限、取消。
- **验证命令**：`uv run pytest tests/unit/agentic_rag/test_knowledge_gateway.py -q`
- **验收标准**：只有一个查询核心；无第二套检索。
- **风险和回滚方法**：Gateway 保持薄层，可回退 KB Tool 调用语义。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待记录。

### P08-T04：实现查询规划与分解

- **状态**：未开始
- **目标**：将复杂问题结构化为可执行子查询/依赖。
- **为什么需要**：多证据任务不能只做一次召回。
- **输入**：P08-T02、P08-T03、规划评测集。
- **前置任务**：P08-T02、P08-T03。
- **操作步骤**：定义 Plan Schema；LangChain 结构化输出；验证子查询/依赖/上限；简单问题跳过；Trace。
- **涉及文件**：`nodes/plan.py`、prompts、测试。
- **预期输出**：QueryPlan。
- **RAGFlow 源码依据**：Agentic RAG orchestrator 节点只作参考。
- **实现或复用方式**：参考后自研。
- **测试方法**：简单/复杂/不可分解/注入/模型错误。
- **验证命令**：`uv run pytest tests/unit/agentic_rag/test_planning.py -q`
- **验收标准**：计划有上限/终止，不能生成 tenant/凭据。
- **风险和回滚方法**：失败退单查询，不扩大 Tool 权限。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待记录。

### P08-T05：实现多次检索与证据检查

- **状态**：未开始
- **目标**：按计划执行受预算约束的多轮检索并判断充分/冲突/缺失。
- **为什么需要**：避免无效循环和无证据回答。
- **输入**：P08-T04、RetrievalTrace/Citation。
- **前置任务**：P08-T04。
- **操作步骤**：retrieve/evaluate nodes；去重子查询；evidence rubric；冲突/补查/澄清/abstain 路由；循环上限。
- **涉及文件**：`nodes/{retrieve,evaluate}.py`、图、测试。
- **预期输出**：多轮检索图。
- **RAGFlow 源码依据**：Agentic evidence grading/abstain 节点参考。
- **实现或复用方式**：LangGraph + 参考后自研。
- **测试方法**：充分/不足/冲突/重复/空结果/循环。
- **验证命令**：`uv run pytest tests/unit/agentic_rag/test_retrieval_loop.py -q`
- **验收标准**：所有循环受预算；引用来自最终证据。
- **风险和回滚方法**：阈值不稳时默认 abstain/澄清。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待记录。

### P08-T06：实现 Tool 选择和统一执行策略

- **状态**：未开始
- **目标**：在 KB/SQL/API Tool 之间做结构化、可审计选择。
- **为什么需要**：模型自由调用会造成权限和成本风险。
- **输入**：P08-T01、P08-T05。
- **前置任务**：P08-T01、P08-T05。
- **操作步骤**：Tool catalog/能力/风险；policy 预检；选择 Schema；参数验证；并发/串行规则；统一错误/Trace。
- **涉及文件**：`tool_policy.py`、`nodes/select_tool.py`、测试。
- **预期输出**：Tool Router/Executor。
- **RAGFlow 源码依据**：`RAGTools` 和 Canvas Tool 用例参考。
- **实现或复用方式**：LangChain Tool + 自研 policy。
- **测试方法**：未知/禁用/高风险/参数注入/错误 Tool。
- **验证命令**：`uv run pytest tests/unit/agentic_rag/test_tool_policy.py -q`
- **验收标准**：未授权 Tool 在执行前拒绝。
- **风险和回滚方法**：默认 allowlist/deny；高风险转 HITL。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待记录。

### P08-T07：实现受控 SQL Tool

- **状态**：未开始
- **目标**：提供 tenant-scoped、只读、Schema allowlist、限时限行 SQL 查询。
- **为什么需要**：结构化工单/资产数据不能只用文档检索。
- **输入**：P08-T06、独立只读数据源/Schema。
- **前置任务**：P08-T06。
- **操作步骤**：选择 DSL/生成策略；AST/只读校验；参数化；tenant predicate；statement timeout/row limit；结果脱敏；审批策略。
- **涉及文件**：`tools/sql.py`、SQL policy/Adapter、security tests。
- **预期输出**：受控 SQL Tool。
- **RAGFlow 源码依据**：本能力无已确认可复用 Python 路径，标记目标自研。
- **实现或复用方式**：LangChain Tool + 自研安全层。
- **测试方法**：DML/DDL/注释绕过/多语句/tenant 绕过/超时/大结果。
- **验证命令**：`uv run pytest tests/security/agentic_rag/test_sql_tool.py -q`
- **验收标准**：只读、tenant 强制、无凭据泄露。
- **风险和回滚方法**：默认关闭；任何解析不确定即拒绝。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待记录。

### P08-T08：实现受控 API Tool

- **状态**：未开始
- **目标**：调用 allowlisted API，限制方法、域名、参数、重试、响应和凭据。
- **为什么需要**：企业 Agent 需要外部系统但存在 SSRF/副作用风险。
- **输入**：P08-T06、API catalog。
- **前置任务**：P08-T06。
- **操作步骤**：OpenAPI/手工 Schema；host/method allowlist；凭据注入；网络/大小/超时；写请求 HITL；响应映射。
- **涉及文件**：`tools/api.py`、Adapter、security tests。
- **预期输出**：受控 API Tool。
- **RAGFlow 源码依据**：无确认复用路径；自研。
- **实现或复用方式**：LangChain Tool + 自研网关。
- **测试方法**：SSRF、重定向、超时、超大响应、凭据、写请求。
- **验证命令**：`uv run pytest tests/security/agentic_rag/test_api_tool.py -q`
- **验收标准**：模型不能指定任意 URL/认证；副作用受审批。
- **风险和回滚方法**：默认 GET/allowlist；发现风险立即禁用 Tool。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待记录。

### P08-T09：实现 HITL 与高风险审批

- **状态**：未开始
- **目标**：为 SQL/API/低证据/高费用动作提供审批、澄清和恢复。
- **为什么需要**：Phase 02 只提供 Checkpoint 和恢复基础，本阶段才建立完整人工审批语义。
- **输入**：P08-T06 至 P08-T08、Phase 02 Checkpoint/恢复协议。
- **前置任务**：P08-T06 至 P08-T08。
- **操作步骤**：风险分级；ApprovalRequest 摘要；批准/修改/拒绝；超时；恢复时重验权限/参数；审计。
- **涉及文件**：Agent graph/HITL application、测试。
- **预期输出**：完整 Agentic HITL。
- **RAGFlow 源码依据**：Canvas user input 用例只参考。
- **实现或复用方式**：LangGraph interrupt/resume + 自研 policy。
- **测试方法**：重复/过期/越权审批、参数变化、拒绝。
- **验证命令**：`uv run pytest tests/integration/agentic_rag/test_hitl.py -q`
- **验收标准**：审批对象与执行动作一致；过期默认拒绝。
- **风险和回滚方法**：审批存储故障保持暂停。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待记录。

### P08-T10：实现短期与长期记忆

- **状态**：未开始
- **目标**：区分 thread 短期状态与经治理的长期用户/任务记忆。
- **为什么需要**：连续交互需要上下文，但不能无限保存敏感内容。
- **输入**：P08-T01、P08-T09、Checkpoint/权限。
- **前置任务**：P08-T01、P08-T09。
- **操作步骤**：定义 MemoryRecord/类型/来源/TTL/consent；短期 summary；长期写入审批/策略；tenant/user scope；检索与删除；Prompt 注入防护。
- **涉及文件**：`application/memory.py`、ports/Adapter、迁移、测试。
- **预期输出**：Memory service 和节点。
- **RAGFlow 源码依据**：冻结 RAGFlow 无本项目完整记忆治理证据；自行开发。
- **实现或复用方式**：LangGraph state + LangChain summary + 自研持久治理。
- **测试方法**：跨租户/用户、TTL、删除、错误记忆、注入、恢复。
- **验证命令**：`uv run pytest tests/integration/agentic_rag/test_memory.py -q`
- **验收标准**：短/长期明确；无默认保存密钥/全文。
- **风险和回滚方法**：长期记忆默认关闭/最小化，可全量删除。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待记录。

### P08-T11：完善预算、Trace、恢复与终止

- **状态**：未开始
- **目标**：统一检索/Tool/模型/记忆的循环、Token、时间、费用和恢复治理。
- **为什么需要**：多 Tool/多检索显著放大成本和故障面。
- **输入**：P08-T02 至 P08-T10。
- **前置任务**：P08-T02 至 P08-T10。
- **操作步骤**：预算 ledger；每节点/Tool 消耗；hard/soft limit；checkpoint；恢复重验；Trace 关联 retrieval/tool/citation；终止原因。
- **涉及文件**：Agent budgets/runtime/trace、测试。
- **预期输出**：Agentic 运行治理。
- **RAGFlow 源码依据**：上游 Agentic 固定图无完整治理证据。
- **实现或复用方式**：LangGraph + 自研。
- **测试方法**：每种超限、崩溃恢复、重复副作用、Trace。
- **验证命令**：`uv run pytest tests/fault/agentic_rag/test_runtime_governance.py -q`
- **验收标准**：无无限循环；副作用节点幂等/审批；成本可解释。
- **风险和回滚方法**：默认保守上限；恢复冲突终止而非重放。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待记录。

### P08-T12：评测并按需实现多 Agent 协作

- **状态**：未开始
- **目标**：用单 Agent 基线判断是否需要 supervisor/worker；只有明确收益时实现受控多 Agent。
- **为什么需要**：项目最终目标包含多 Agent，但无收益的默认拆分会扩大状态、权限、成本和故障面。
- **输入**：P08-T04 至 P08-T11、CAP-32、至少一个需要职责分解的评测场景。
- **前置任务**：P08-T04 至 P08-T11。
- **操作步骤**：定义单 Agent 基线；设计 supervisor/worker 状态和 Tool 边界；验证 tenant/context 传播、子任务终止、失败隔离、共享证据和预算；比较质量/成本/时延；形成启用或暂缓结论。
- **涉及文件**：`agent/graphs/multi_agent/`（仅收益成立时）、`tests/evaluation/agentic_rag/test_multi_agent.py`、ADR/评测报告。
- **预期输出**：CAP-32 的可审计启用或暂缓结论；收益成立时提供最小多 Agent Profile。
- **RAGFlow 源码依据**：Canvas Agent Invoke/组件和 Agentic orchestrator 仅作协作需求参考；没有可直接复用的 LangGraph supervisor/worker 治理。
- **实现或复用方式**：LangGraph 编排 + 自行开发；不复用 Canvas。
- **测试方法**：单/多 Agent 对照、共享状态、权限、失败隔离、终止、预算和恢复。
- **验证命令**：`uv run pytest tests/evaluation/agentic_rag/test_multi_agent.py -q`
- **验收标准**：若启用则有可重复质量收益且不越权/失控；若暂缓则记录指标、原因和重新评审条件。
- **风险和回滚方法**：多 Agent 默认关闭；关闭 Profile 即回退单 Agent，不能影响 KB Tool 或固定 RAG。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待执行时记录。

### P08-T13：建立 Agentic RAG E2E/评测并验收

- **状态**：未开始
- **目标**：验证固定 RAG、KB Tool、多步检索、SQL/API、HITL、记忆和预算。
- **为什么需要**：单节点测试不能证明任务成功和安全。
- **输入**：P08-T01 至 P08-T12。
- **前置任务**：P08-T01 至 P08-T12。
- **操作步骤**：版本化场景；固定 RAG 对照；Agent success/Tool accuracy/citation/cost/latency；越权/注入；恢复；更新文档。
- **涉及文件**：E2E/evaluation/security、总体文档、本文件。
- **预期输出**：Phase 08 验收报告。
- **RAGFlow 源码依据**：上游用例不替代目标评测。
- **实现或复用方式**：自行开发评测。
- **测试方法**：Unit/Contract/Integration/E2E/Evaluation/Security/Fault。
- **验证命令**：`uv run pytest tests/**/agentic_rag -q`; `uv run <agent-evaluation-command>`
- **验收标准**：CAP-28/31/32 及 CAP-29 Agentic 扩展按真实结果通过；越权零容忍。
- **风险和回滚方法**：无收益/高风险 Tool 默认关闭；不降低安全门禁。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待记录。

## 8. 验收、DoD、风险与后续

**DoD**：P08-T01 至 P08-T13 完成；KB Tool 与固定 RAG 共用查询核心；规划/多检索/证据/Tool/HITL/记忆/预算/恢复均有测试；SQL/API 通过安全门禁；CAP-32 有启用或暂缓结论；评测指标版本化；总体文档同步。

| 风险 | 处理 |
|---|---|
| Agent 绕过权限 | Tool/Gateway 强制 context，节点无底层客户端 |
| SQL/API 注入和副作用 | AST/allowlist/HITL/只读/网络边界 |
| 循环与成本失控 | ledger、硬上限、abstain |
| 长期记忆泄密/污染 | consent、TTL、来源、删除、最小化 |
| 多 Agent 复杂度 | 本阶段不默认启用；有明确场景再扩展 CAP-32 |

阶段结束更新总纲、矩阵、目标架构、路线图、标准、风险、阶段索引和本文件。Phase 09 可以让高级检索以 Tool/路由接入，但不得改变统一权限和查询核心。

## 9. 实际执行结果预留

- 实际 Tool/模型/预算/记忆策略：待执行。
- 实际任务成功/安全/成本指标：待执行。
- 计划偏差与新增 ADR：待执行。
- 阶段出口结论：待执行。
