---
document_id: PHASE-02-AGENT-FOUNDATION
document_role: Phase 02 预规划详细计划
status: draft
phase: Phase 02
phase_name: Agent基础
plan_status: 预规划草案
execution_status: 未执行
last_updated_at: "2026-07-30"
ragflow_frozen_baseline_commit: "cd846cc9d4e32a19e684c59a1f302601027ef976"
---

# Phase 02：Agent基础详细计划

## 0. 状态、导航与执行规则

- **计划状态**：预规划草案。
- **执行状态**：未执行。
- 执行前必须以 Phase 01 实际包结构、模型配置、数据库和质量命令重新审查本计划并取得用户确认。
- 导航：[阶段索引](./README.md) · [Phase 01](./phase-01-project-skeleton.md) · [Phase 03](./phase-03-knowledge-interface.md) · [路线图](../05-development-roadmap.md)

## 1. 阶段目标与必要性

建立与知识库解耦的最小 LangGraph Agent Runtime：版本化状态、Graph/Node/Edge/Router、LangChain Tool/模型适配、Checkpoint、Trace、错误处理和最小执行闭环。先稳定运行治理，避免后续把检索、数据库或 RAGFlow Canvas 耦合进节点。

## 2. Phase 00 事实依据

1. RAGFlow 主 Agent 是 `agent/canvas.py::Canvas` 自定义运行时，不是本项目目标。
2. `rag/advanced_rag/agentic_rag_graph.py::build_agentic_graph` 使用六节点 `StateGraph`，但冻结基线以无参数 `g.compile()` 编译，无 Checkpointer/thread_id/interrupt。
3. `agent/tools/retrieval.py::Retrieval._retrieve_kb` 能证明 Tool 需要参数、检索服务和引用回写边界，但不是 LangChain Tool。
4. CAP-29 至 CAP-31 主要自行开发；LangGraph 负责运行编排，LangChain 负责模型/Tool/Prompt。

## 3. 前置阶段、进入条件和输入

- **前置阶段**：Phase 01。
- **进入条件**：Phase 01 DoD 完成；真实包路径/测试命令稳定；本计划复审并确认；Checkpointer 初始实现和首个测试模型策略有结论。
- **输入**：Phase 01 bootstrap/配置/日志/数据库；ADR-002、ADR-013；LangGraph 官方状态、持久化、interrupt 文档；Phase 00 源码地图。

## 4. 工作范围与明确排除

**包含**：`AgentState`、Graph builder、Node/Edge/Router、通用 Tool、模型适配、Checkpoint、stream event、Trace、错误/重试/超时/取消、最小 deterministic Agent E2E。

**不包含**：真实知识库 Tool、RAG、SQL/API 业务 Tool、HITL、多 Agent、短期/长期记忆、循环/Token/时间/费用预算治理、RAGFlow Canvas、Agent 直连数据库/Redis/Search；这些 Agentic 能力统一进入 Phase 08。

## 5. 主要交付物与目标文件

```text
src/ragflow_agent/agent/
  domain/{state,events,errors,budgets}.py
  application/{runtime,tool_executor}.py
  graphs/minimal_agent.py
  nodes/
  ports/{checkpoint,model,tool,trace}.py
  infrastructure/{langgraph,langchain,checkpoint}/
tests/{unit,contract,integration,e2e}/agent/
```

交付版本化 AgentState/Event、运行记录、Checkpointer Adapter、Tool registry/policy、最小图、错误恢复测试和阶段文档。

## 6. RAGFlow 源码范围、调用关系与采用方式

| 源码 | 类/函数与关系 | 采用 |
|---|---|---|
| `agent/canvas.py` | `Graph` → `Canvas.run` → `Canvas._run_impl` | 明确不采用运行时；仅参考事件、暂停和节点需求 |
| `rag/advanced_rag/agentic_rag_graph.py` | `AgenticState` → `build_agentic_graph` → `g.compile()` → `run_agentic_rag/ainvoke` | 参考后自研；不复制固定图 |
| `agent/tools/retrieval.py` | `RetrievalParam` → `Retrieval._retrieve_kb` | 参考 Tool 参数/结构化输出，真实 KB Tool 留 Phase 08 |
| `api/db/db_models.py` | `Dialog`、`Conversation`、`UserCanvas` | 产品数据用例参考，不复制 Peewee |

- **直接复用**：无。
- **通过 `ragflow_adapters` 改造复用**：无。
- **参考后自研**：状态字段、图节点需求和事件用例。
- **明确不采用**：Canvas Runtime、无 Checkpointer 的 Agentic 图、Peewee 会话模型。

## 7. 责任边界

- **LangGraph**：StateGraph、Node/Edge/Router、受控循环、Checkpointer 和事件流；interrupt/resume 的 HITL 用例留到 Phase 08。
- **LangChain**：ChatModel、Tool、Prompt、结构化输出、模型测试替身。
- **本项目自研**：状态 Schema、运行记录、权限上下文字段、错误、Tool policy、Trace、恢复校验和审计。

## 8. 任务总表

| 任务 | 名称 | 状态 | 前置任务 |
|---|---|---|---|
| P02-T01 | 复审 Agent 范围与运行契约 | 未开始 | Phase 01 |
| P02-T02 | 定义 AgentState、事件与运行身份 | 未开始 | P02-T01 |
| P02-T03 | 建立 LangChain 模型与 Tool 抽象 | 未开始 | P02-T01、P02-T02 |
| P02-T04 | 实现 Graph/Node/Edge/Router 基础 | 未开始 | P02-T02、P02-T03 |
| P02-T05 | 实现错误、重试、超时与取消 | 未开始 | P02-T04 |
| P02-T06 | 实现 Checkpoint 与运行恢复 | 未开始 | P02-T02、P02-T04 |
| P02-T07 | 实现 Agent Trace 与流式事件 | 未开始 | P02-T04、P02-T06 |
| P02-T08 | 建立最小 Agent 执行闭环 | 未开始 | P02-T03 至 P02-T07 |
| P02-T09 | 验证错误恢复、Checkpoint 与 Trace | 未开始 | P02-T05 至 P02-T08 |
| P02-T10 | 执行 Agent 基础阶段验收 | 未开始 | P02-T01 至 P02-T09 |

## 9. 具体任务

### P02-T01：复审 Agent 范围与运行契约

- **状态**：未开始
- **目标**：依据 Phase 01 实际产物冻结 Agent 模块、Checkpointer 候选和运行边界。
- **为什么需要**：预规划路径和基础设施可能已变化。
- **输入**：Phase 01 验收、ADR-002、CAP-29 至 CAP-31。
- **前置任务**：Phase 01 完成。
- **操作步骤**：检查源码/Git；复核包边界；决定 Checkpointer 初始 Adapter；列出节点副作用和权限恢复规则；修订本计划。
- **涉及文件**：本文件、`docs/07-decisions-and-risks.md`、计划中的 `agent/`。
- **预期输出**：Agent Runtime 契约和执行清单。
- **RAGFlow 源码依据**：`agentic_rag_graph.py::build_agentic_graph` 无持久化配置。
- **实现或复用方式**：参考后自研。
- **测试方法**：契约评审和导入图检查。
- **验证命令**：`uv run pytest tests/unit/import_boundaries -q`
- **验收标准**：节点不得直连基础设施；待决策均有结论或期限。
- **风险和回滚方法**：若 Phase 01 接口不稳定，暂停并先修正骨架。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待执行时记录。

### P02-T02：定义 AgentState、事件与运行身份

- **状态**：未开始
- **目标**：定义可序列化、版本化的 state、thread/run/node/event 身份。
- **为什么需要**：Checkpoint、恢复和 Trace 依赖稳定状态。
- **输入**：P02-T01、`AuthorizationContext` 最小字段。
- **前置任务**：P02-T01。
- **操作步骤**：定义输入、消息、Tool call、错误、输出字段；区分持久/瞬时字段；制定 state version/migration；只预留 Phase 08 扩展命名空间，不定义 HITL/预算业务。
- **涉及文件**：`agent/domain/state.py`、`events.py`、测试。
- **预期输出**：AgentState v1 与事件 Schema。
- **RAGFlow 源码依据**：`agentic_rag_graph.py::AgenticState` 仅作字段参考。
- **实现或复用方式**：自行开发。
- **测试方法**：序列化往返、版本拒绝/迁移、敏感字段检查。
- **验证命令**：`uv run pytest tests/unit/agent/test_state.py -q`
- **验收标准**：状态可确定性恢复；不持久化密钥/客户端。
- **风险和回滚方法**：新增字段保持向后兼容；破坏性变化升级版本。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待执行时记录。

### P02-T03：建立 LangChain 模型与 Tool 抽象

- **状态**：未开始
- **目标**：建立统一 ChatModel 和结构化 Tool registry/executor。
- **为什么需要**：图节点不应绑定供应商或业务 Tool 实现。
- **输入**：P02-T01、P02-T02、Phase 01 模型端口。
- **前置任务**：P02-T01、P02-T02。
- **操作步骤**：定义 Tool 输入/输出/错误；适配 LangChain Tool；实现 deterministic model/tool stub；建立 allowlist/policy 钩子。
- **涉及文件**：`agent/ports/{model,tool}.py`、`infrastructure/langchain/`。
- **预期输出**：模型与 Tool 契约。
- **RAGFlow 源码依据**：`RetrievalParam`、`RAGTools` 只参考参数化 Tool 需求。
- **实现或复用方式**：LangChain 标准组件 + 自研 policy。
- **测试方法**：Schema、超时、错误、未知 Tool、重复调用。
- **验证命令**：`uv run pytest tests/contract/agent/test_tools.py -q`
- **验收标准**：Tool 返回稳定结构；模型不能绕过 registry。
- **风险和回滚方法**：供应商差异封装在 Adapter；可退回 stub。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待执行时记录。

### P02-T04：实现 Graph、Node、Edge 与 Router 基础

- **状态**：未开始
- **目标**：实现输入规范化、模型决策、Tool 执行、观察和终止的最小图。
- **为什么需要**：形成通用可测试编排核心。
- **输入**：P02-T02、P02-T03。
- **前置任务**：P02-T02、P02-T03。
- **操作步骤**：定义纯节点接口；构建 StateGraph；添加条件边和终止；实现依赖注入；导出图结构快照。
- **涉及文件**：`agent/graphs/minimal_agent.py`、`nodes/`。
- **预期输出**：可编译最小图。
- **RAGFlow 源码依据**：`build_agentic_graph` 六节点顺序只作图结构用例。
- **实现或复用方式**：LangGraph + 自研节点。
- **测试方法**：每条 edge、路由和终止路径确定性单测。
- **验证命令**：`uv run pytest tests/unit/agent/test_graph_routes.py -q`
- **验收标准**：所有路由有终止；节点无数据库/Redis/Search 导入。
- **风险和回滚方法**：图过度通用时收敛到最小节点集。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待执行时记录。

### P02-T05：实现错误、重试、超时与取消

- **状态**：未开始
- **目标**：统一可重试/不可重试错误、节点超时和取消。
- **为什么需要**：防止错误吞噬、无界挂起和取消失效。
- **输入**：P02-T04、工程标准第 14 节。
- **前置任务**：P02-T04。
- **操作步骤**：错误分类；配置 retry/backoff；每节点/整图超时；CancellationToken；定义稳定终止原因。
- **涉及文件**：`agent/domain/errors.py`、runtime。
- **预期输出**：错误和取消治理策略。
- **RAGFlow 源码依据**：Canvas/Agentic 图只提供分散异常与取消用例，没有本项目统一错误协议。
- **实现或复用方式**：自行开发，LangGraph 承担路由/重试编排。
- **测试方法**：超时、取消、瞬时/永久错误和重试耗尽。
- **验证命令**：`uv run pytest tests/unit/agent/test_runtime_limits.py -q`
- **验收标准**：每条异常路径有稳定 outcome；超时与取消可终止执行。
- **风险和回滚方法**：默认重试次数保守；配置错误时拒绝启动。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待执行时记录。

### P02-T06：实现 Checkpoint 与运行恢复

- **状态**：未开始
- **目标**：持久化 thread/run state 并支持进程重启恢复。
- **为什么需要**：长任务和故障恢复的基础；Phase 08 HITL 将复用该能力。
- **输入**：P02-T02、P02-T04、P02-T01 的 Checkpointer 结论。
- **前置任务**：P02-T02、P02-T04。
- **操作步骤**：实现 Adapter；tenant-scoped key；写入/读取/list/清理；状态版本校验；重复恢复幂等。
- **涉及文件**：`agent/ports/checkpoint.py`、`infrastructure/checkpoint/`、迁移（如需）。
- **预期输出**：持久 Checkpointer。
- **RAGFlow 源码依据**：冻结 `g.compile()` 无 Checkpointer，是明确缺口。
- **实现或复用方式**：LangGraph Checkpointer + 自研 tenant/版本治理。
- **测试方法**：重启、并发、旧版本、跨租户、重复 resume。
- **验证命令**：`uv run pytest tests/integration/agent/test_checkpoint.py -q`
- **验收标准**：恢复后路径与不重启一致；跨租户拒绝。
- **风险和回滚方法**：存储 Adapter 可替换；迁移提供回滚/兼容读取。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待执行时记录。

### P02-T07：实现 Agent Trace 与流式事件

- **状态**：未开始
- **目标**：输出节点、路由、模型、Tool、错误和恢复事件。
- **为什么需要**：可诊断 Agent 运行且为 Phase 10 观测提供基线。
- **输入**：P02-T04、P02-T06、Phase 01 Trace。
- **前置任务**：P02-T04、P02-T06。
- **操作步骤**：定义 event envelope；映射 LangGraph stream；关联 trace/thread/run；脱敏；持久/实时 sink 分离。
- **涉及文件**：`agent/domain/events.py`、`ports/trace.py`、Adapter。
- **预期输出**：AgentTrace v1。
- **RAGFlow 源码依据**：Canvas 事件和 Agentic 调用日志只作部分参考。
- **实现或复用方式**：LangGraph events + 自研 Schema。
- **测试方法**：事件顺序、关联 ID、脱敏、sink 故障降级。
- **验证命令**：`uv run pytest tests/unit/agent/test_trace.py -q`
- **验收标准**：一次运行可还原节点路径；Trace 失败不伪造业务成功。
- **风险和回滚方法**：禁记原始敏感内容；Schema 版本化。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待执行时记录。

### P02-T08：建立最小 Agent 执行闭环

- **状态**：未开始
- **目标**：用 deterministic model 和无副作用 Tool 完成输入→路由→Tool→观察→回答。
- **为什么需要**：证明 Runtime 真实可运行而非只有抽象。
- **输入**：P02-T03 至 P02-T07。
- **前置任务**：P02-T03 至 P02-T07。
- **操作步骤**：实现示例 Tool；配置最小图；运行流式/非流式；验证 checkpoint、错误、重试、超时和取消分支。
- **涉及文件**：`graphs/minimal_agent.py`、E2E 测试。
- **预期输出**：最小 Agent E2E。
- **RAGFlow 源码依据**：不新增上游事实。
- **实现或复用方式**：LangChain + LangGraph + 自研 Runtime。
- **测试方法**：黄金状态序列和事件快照。
- **验证命令**：`uv run pytest tests/e2e/agent/test_minimal_agent.py -q`
- **验收标准**：全部分支确定性通过；无知识库伪实现。
- **风险和回滚方法**：模型不确定性通过 stub 隔离；真实模型冒烟另设可选测试。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待执行时记录。

### P02-T09：验证错误恢复、Checkpoint 与 Trace

- **状态**：未开始
- **目标**：通过故障注入验证重试、进程恢复、状态版本、租户隔离和 Trace 连续性。
- **为什么需要**：单元测试不足以证明最小 Agent 在故障和重启后仍保持确定性。
- **输入**：P02-T05 至 P02-T08。
- **前置任务**：P02-T05 至 P02-T08。
- **操作步骤**：注入模型/Tool 瞬时与永久错误；中断进程并恢复；验证旧 state version 拒绝；验证跨租户拒绝；比较恢复前后事件序列。
- **涉及文件**：`tests/integration/agent/test_runtime_recovery.py`、fault fixtures。
- **预期输出**：Agent Runtime 恢复与 Trace 验证记录。
- **RAGFlow 源码依据**：冻结 `agentic_rag_graph.py` 无 Checkpointer，Canvas 异常/事件仅作缺口证据。
- **实现或复用方式**：自行开发测试，复用 LangGraph Checkpointer。
- **测试方法**：故障注入、重启、重复 resume、状态迁移和跨租户测试。
- **验证命令**：`uv run pytest tests/integration/agent/test_runtime_recovery.py -q`
- **验收标准**：恢复路径确定；副作用不重复；Trace 可关联；跨租户恢复失败关闭。
- **风险和回滚方法**：若持久 Checkpointer 不稳定，保留端口并回滚 Adapter；不得用内存 Checkpointer 冒充阶段完成。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待执行时记录。

### P02-T10：执行 Agent 基础阶段验收

- **状态**：未开始
- **目标**：验证 Agent Runtime、恢复、错误治理和导入边界并同步文档。
- **为什么需要**：Phase 03/08 只能依赖已验证的运行契约。
- **输入**：P02-T01 至 P02-T09。
- **前置任务**：P02-T01 至 P02-T09。
- **操作步骤**：运行全套测试；故障注入；检查状态/事件版本；更新总文档和能力状态；记录偏差。
- **涉及文件**：测试、本文及总体文档。
- **预期输出**：Phase 02 验收记录。
- **RAGFlow 源码依据**：核对未误用 Canvas 或上游全局依赖。
- **实现或复用方式**：审计。
- **测试方法**：Unit/Contract/Integration/E2E/静态边界。
- **验证命令**：`uv run pytest tests/**/agent -q`; `uv run ruff check .`; `uv run mypy src/ragflow_agent tests`
- **验收标准**：CAP-29/30/31 基础验收通过；Phase 08 能复用同一 Runtime。
- **风险和回滚方法**：任何恢复/权限失败均阻止阶段完成。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待执行时记录。

## 10. 测试与验证方案

Unit 覆盖状态、路由和错误；Contract 覆盖 Tool/Model/Checkpoint/Trace；Integration 覆盖持久恢复、重试、超时、取消和跨租户；E2E 覆盖最小闭环；静态检查阻止节点直连基础设施。

## 11. 阶段验收与 Definition of Done

1. 状态和事件可版本化、可恢复。
2. Graph 所有路径有终止，重试、超时和取消受控。
3. Checkpoint 重启恢复、结构化 Tool 错误、重试、超时和取消通过测试。
4. Agent 节点不访问具体数据库/Redis/Search。
5. P02-T01 至 P02-T10 全部记录真实结果。
6. 总纲、路线图、矩阵、风险和阶段索引同步。

## 12. 风险与处理

| 风险 | 处理 |
|---|---|
| Checkpoint 与业务实体混淆 | 分离 AgentState/Run 与领域聚合 |
| 模型路由测试脆弱 | deterministic stub 为门禁，真实模型仅冒烟 |
| 恢复时权限漂移 | resume 必须重验 AuthorizationContext |
| 图路径无终止或重试失控 | 静态路由检查、有限重试和硬超时 |
| 预规划漂移 | Phase 01 后按 R-023 重审 |

## 13. 阶段结束更新与下一阶段

更新 `docs/00-project-master.md`、`02-ragflow-capability-matrix.md`、`03-target-architecture.md`、`05-development-roadmap.md`、`06-engineering-standards.md`、`07-decisions-and-risks.md`、`phases/README.md` 和本文件。

Phase 03 只有在 Agent 的 `AuthorizationContext` 传递、Tool 边界和恢复协议稳定，且 Phase 03 计划按实际代码复审确认后才能执行。

## 14. 实际执行结果预留

- 实际开始/结束时间：待执行。
- 实际变更和迁移：待执行。
- 实际测试命令与结果：待执行。
- 计划偏差/新增 ADR：待执行。
- 阶段出口结论：待执行。
