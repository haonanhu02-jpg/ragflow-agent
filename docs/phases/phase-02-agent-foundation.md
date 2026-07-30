---
document_id: PHASE-02-AGENT-FOUNDATION
document_role: Phase 02 执行记录
status: completed
phase: Phase 02
phase_name: Agent基础
plan_status: 已确认
execution_status: 已完成
last_updated_at: "2026-07-30"
ragflow_frozen_baseline_commit: "cd846cc9d4e32a19e684c59a1f302601027ef976"
---

# Phase 02：Agent基础详细计划

## 0. 状态、导航与执行规则

- **计划状态**：已确认；用户授权在准入满足后连续执行全部 Phase 02。
- **执行状态**：已完成；P02-T01 至 P02-T10 和完整阶段验收均通过。
- 执行基线已按 Phase 01 实际包结构、PostgreSQL 基础设施和质量命令复审；复审结论见 P02-T01 实际记录和 ADR-017。
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
| P02-T01 | 复审 Agent 范围与运行契约 | 已完成 | Phase 01 |
| P02-T02 | 定义 AgentState、事件与运行身份 | 已完成 | P02-T01 |
| P02-T03 | 建立 LangChain 模型与 Tool 抽象 | 已完成 | P02-T01、P02-T02 |
| P02-T04 | 实现 Graph/Node/Edge/Router 基础 | 已完成 | P02-T02、P02-T03 |
| P02-T05 | 实现错误、重试、超时与取消 | 已完成 | P02-T04 |
| P02-T06 | 实现 Checkpoint 与运行恢复 | 已完成 | P02-T02、P02-T04 |
| P02-T07 | 实现 Agent Trace 与流式事件 | 已完成 | P02-T04、P02-T06 |
| P02-T08 | 建立最小 Agent 执行闭环 | 已完成 | P02-T03 至 P02-T07 |
| P02-T09 | 验证错误恢复、Checkpoint 与 Trace | 已完成 | P02-T05 至 P02-T08 |
| P02-T10 | 执行 Agent 基础阶段验收 | 已完成 | P02-T01 至 P02-T09 |

## 9. 具体任务

### P02-T01：复审 Agent 范围与运行契约

- **状态**：已完成
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
- **实际执行结果**：复核 Phase 01 的 10 项任务、阶段验收、当前包结构、`main == origin/main`、干净工作树和 GitHub Actions 成功基线；重新核对 RAGFlow 0.26.4 本地快照的 `AgenticState`、六节点图和无参数 `g.compile()`。冻结官方 `langgraph-checkpoint-postgres::AsyncPostgresSaver`、`TenantScopedCheckpointStore`、AgentState v1 和确定性模型门禁，真实模型 Provider 仍按 O-007 延至 Phase 04。
- **实际验证结果**：通过。`uv run pytest tests/unit/import_boundaries -q` 为 `5 passed`；源码边界和待决策均有明确处理，新增 ADR-017。
- **计划偏差**：计划路径中的 `domain/budgets.py` 未创建；Phase 08 才负责业务预算，本阶段仅以 `RuntimeLimits` 提供技术安全上限。

### P02-T02：定义 AgentState、事件与运行身份

- **状态**：已完成
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
- **实际执行结果**：实现不可变 `AgentAuthorizationContext` 最小快照、thread/run/trace 身份、租户绑定 `AgentResumeToken`、消息/Tool/Model DTO、`AgentState` v1、LangGraph primitive state 映射、v0→v1 迁移和未来版本拒绝；Checkpoint payload 拒绝密钥类字段。
- **实际验证结果**：通过。`uv run pytest tests/unit/agent/test_state.py -q` 为 `6 passed`，覆盖确定性往返、迁移、版本拒绝、密钥字段、结构化决策和跨租户恢复令牌。
- **计划偏差**：Phase 03 的共享 `AuthorizationContext` 尚未创建；本阶段使用明确命名的最小 Agent 快照，避免提前实现 `PermissionChecker`。

### P02-T03：建立 LangChain 模型与 Tool 抽象

- **状态**：已完成
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
- **实际执行结果**：实现 `AgentModelPort`、`AgentToolPort`、`ToolSpec`、显式 allowlist policy、唯一 Tool registry、重复调用结果复用、LangChain `BaseTool` Adapter 和 ChatModel 结构化输出 Adapter；测试使用 `ScriptedAgentModel` 和无副作用 Tool，不绑定供应商。
- **实际验证结果**：通过。`uv run pytest tests/contract/agent/test_tools.py -q` 为 `4 passed`，覆盖 Schema/成功、未知 Tool、禁止 Tool、重复调用和重名注册；strict mypy 验证模型/Tool Adapter 类型。
- **计划偏差**：未实现真实模型冒烟；O-007 的期限仍为 Phase 04，符合计划。

### P02-T04：实现 Graph、Node、Edge 与 Router 基础

- **状态**：已完成
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
- **实际执行结果**：实现 `normalize_input → decide → execute_tool → observe → decide/finish` 的 LangGraph StateGraph、条件 Router、稳定 Tool call ID、依赖注入和静态拓扑常量；节点只依赖 Agent 领域、端口和应用服务。
- **实际验证结果**：通过。`uv run pytest tests/unit/agent/test_graph_routes.py -q` 为 `3 passed`，直接回答和 Tool 路径均确定终止；导入边界验证无数据库、Redis、Search 或后续阶段模块依赖。
- **计划偏差**：未复制 RAGFlow 六节点固定图；按计划以最小闭环自研。

### P02-T05：实现错误、重试、超时与取消

- **状态**：已完成
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
- **实际执行结果**：实现稳定 Agent 错误分类、瞬时失败有限重试和退避、节点/整图硬超时、合作式 `CancellationToken`、技术递归上限及结构化终止错误；重试次数写入成功状态。
- **实际验证结果**：通过。`uv run pytest tests/unit/agent/test_runtime_limits.py -q` 为 `5 passed`，覆盖重试成功、重试耗尽、超时、运行中取消和图步数上限。
- **计划偏差**：循环次数、Token、时间和费用的业务预算仍留 Phase 08；Phase 02 只实现不可关闭的技术安全限额。

### P02-T06：实现 Checkpoint 与运行恢复

- **状态**：已完成
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
- **实际执行结果**：新增官方异步 PostgreSQL Checkpointer 依赖和生命周期，`setup()` 管理上游 Checkpoint 表；自研租户/版本/逻辑 thread 组成的物理 key、load/list/delete、所有权复验和恢复令牌。内存 Saver 只用于 unit/E2E，阶段持久化结论由真实 PostgreSQL 测试支撑。
- **实际验证结果**：通过。临时 PostgreSQL 17 上 `uv run pytest tests/integration/agent/test_checkpoint.py -q` 为 `2 passed`，覆盖运行时重建后读取、Checkpoint 列举/清理、并发 thread 和同逻辑 thread 的跨租户隔离。
- **计划偏差**：未创建项目 Alembic 迁移；官方 Saver 按其协议使用自身 `setup()`/migration 表，Agent 业务表仍未创建。

### P02-T07：实现 Agent Trace 与流式事件

- **状态**：已完成
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
- **实际执行结果**：实现 `AgentEvent` v1、节点/模型/Tool/完成/失败/取消/恢复事件映射、trace/thread/run/request 关联、单调序列、递归脱敏和 `AgentTraceSink`；Sink 故障记录为 `trace_degraded`，不伪装为完整观测成功。
- **实际验证结果**：通过。`uv run pytest tests/unit/agent/test_trace.py -q` 为 `3 passed`，覆盖事件顺序、节点路径、关联 ID、敏感字段脱敏和 Sink 故障降级。
- **计划偏差**：本阶段只交付 Sink 协议与内存/故障测试 Adapter；持久 Trace 后端和外部观测平台仍属 Phase 10。

### P02-T08：建立最小 Agent 执行闭环

- **状态**：已完成
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
- **实际执行结果**：完成输入→模型结构化路由→无副作用 Tool→观察→模型回答→持久 Checkpoint/Trace 的确定性闭环；同时支持无 Tool 的直接回答路径。
- **实际验证结果**：通过。`uv run pytest tests/e2e/agent/test_minimal_agent.py -q` 为 `1 passed`，黄金答案、单次 Tool 调用、终态、恢复状态和事件类型均符合预期。
- **计划偏差**：真实模型调用和业务 Tool 未纳入，符合 Phase 02 排除项。

### P02-T09：验证错误恢复、Checkpoint 与 Trace

- **状态**：已完成
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
- **实际执行结果**：在真实 PostgreSQL 上注入 Tool 瞬时失败直至重试耗尽，使用重建后的 Runtime/Model/Tool 实例从失败节点恢复；验证稳定 call ID、重复 resume 不重复执行已完成 Tool、Trace 关联连续和跨租户 token 失败关闭。
- **实际验证结果**：通过。临时 PostgreSQL 17 上 `uv run pytest tests/integration/agent/test_runtime_recovery.py -q` 为 `2 passed`。
- **计划偏差**：故障恢复测试采用同一测试进程内销毁并重建 Runtime 对象模拟进程重启；持久状态来自真实 PostgreSQL，不使用内存 Saver 冒充。

### P02-T10：执行 Agent 基础阶段验收

- **状态**：已完成
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
- **实际执行结果**：执行完整 Unit/Contract/Integration/E2E、导入边界、锁文件、依赖一致性、包导入、ruff、strict mypy、密钥卫生、真实 PostgreSQL Checkpoint/迁移、API/Worker bootstrap、Compose 配置和包含新增依赖的非 root Docker 镜像构建；同步主文档、架构、矩阵、路线图、标准、ADR/风险、阶段索引和 README。
- **实际验证结果**：通过。`uv lock --check`、`uv sync --frozen --all-groups`、`uv pip check`、直接导入、`uv run ruff check .`、`uv run mypy src/ragflow_agent tests`、密钥扫描均通过；真实 PostgreSQL 17 上完整 `uv run pytest` 为 `63 passed`，Alembic upgrade/downgrade/upgrade 通过；API/Worker bootstrap、Compose config 和 `docker build --tag ragflow-agent:phase02-validation .` 通过；27 个 Markdown 文件本地链接零失效，P02-T01 至 P02-T10 连续无重复。
- **计划偏差**：验收额外执行依赖一致性、迁移往返、bootstrap、Compose 和 Docker build，以证明 Phase 01 门禁未回归及新增 Checkpointer 依赖可进入运行镜像；没有扩大业务范围。

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

## 14. 实际执行结果

- **实际开始/结束时间**：2026-07-30；P02-T01 至 P02-T10 当日连续完成。
- **实际变更和迁移**：新增 `src/ragflow_agent/agent/` 的 domain/ports/application/nodes/graphs/infrastructure，新增 26 项 Agent 专项测试和 2 项 Agent 导入边界测试；`uv.lock` 增加官方 PostgreSQL Checkpointer。没有新增项目业务表或 Alembic revision，官方 Checkpoint 内部表由 `AsyncPostgresSaver.setup()` 管理。
- **实际测试命令与结果**：任务级 5/6/4/3/5/2/3/1/2 项验证均通过；最终全量 `63 passed`，ruff、strict mypy（108 files）、锁文件、依赖检查、密钥卫生、真实 PostgreSQL Checkpoint/迁移、bootstrap、Compose、Docker build 和文档一致性全部通过。
- **计划偏差/新增 ADR**：新增 ADR-017 和 R-025；未创建 `budgets.py` 或项目 Checkpoint 迁移；真实模型仍按 O-007 延后。
- **阶段出口结论**：Phase 02 满足 DoD 并完成；不得自动进入 Phase 03，须先按实际 Agent 契约复审 Phase 03 计划。
