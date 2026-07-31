---
document_id: PHASE-08-AGENTIC-RAG
document_role: Phase 08 详细计划与执行记录
status: completed
phase: Phase 08
phase_name: Agentic RAG
plan_status: 已批准
execution_status: 已完成
last_updated_at: "2026-07-31"
ragflow_frozen_baseline_commit: "cd846cc9d4e32a19e684c59a1f302601027ef976"
---

# Phase 08：Agentic RAG详细计划

## 0. 状态与导航

- **计划状态**：已批准；ADR-023 已冻结八项准入决策。
- **执行状态**：已完成；P08-T01 至 P08-T13 均已实现并通过任务验证与阶段验收。
- 本阶段在现有 Agent Runtime、KnowledgeQueryService、权限和 Trace 上增量实施，不另建平行运行时或检索核心。
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

### 2.1 已冻结的 Phase 08 执行 Profile

- **场景**：简单直接 RAG、知识库 Tool、多步/多轮检索、KB+只读 SQL/API、四类证据状态、Fake 高风险 Tool HITL、依赖故障安全失败。
- **Tool**：默认拒绝、显式 Registry、Schema、服务端执行前/恢复后重新授权；模型不能修改风险、审批、权限或预算。
- **SQL/API**：SQL AST 单条只读查询、服务端 tenant 条件、默认 200 行/5 秒；API 固定 base URL/path/method、无重定向、服务端凭据、Schema/大小/超时限制。
- **HITL**：八状态、参数摘要绑定、30 分钟 TTL、真实用户角色审批、原子 claim 和幂等恢复；无前端要求。
- **Memory**：Checkpoint/Trace/Memory 分离，长期记忆默认关闭、明确同意、tenant+user 隔离、90 天 TTL、撤回/删除后 24 小时清理。
- **Evidence**：服务端 `EvidenceSufficiencyPolicy` 最终裁决，关键子问题 100% 覆盖，最多三轮检索，冲突/不足保守终止。
- **Budget**：iteration/model/retrieval/tool/token/generated/reserve/active-time/cost 默认分别为 `8/6/3/10/50000/8000/1500/120s/USD 0.50`；恢复不重置。
- **Evaluation**：确定性机器可读数据集；安全项 100% 且关键违规为零，总体/Tool 至少 90%，no/partial 至少 95%，Citation 至少 95%，groundedness 目标至少 90%。

## 3. 交付物和目标模块

```text
src/ragflow_agent/agent/
  tools/{knowledge_base,sql,api}.py
  graphs/agentic_rag.py
  application/{agentic_runtime,planning,evidence,tool_policy,hitl,memory,budgets,sensitive}.py
  infrastructure/{database,http,sql}/
  evaluation/
src/ragflow_agent/api/routes/agentic.py
tests/{unit,contract,integration,e2e,evaluation}/agentic_rag/
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
| P08-T01 | 复审场景、Tool 策略和预算 | 已完成 | Phase 02、06 |
| P08-T02 | 实现 KnowledgeBaseTool | 已完成 | P08-T01 |
| P08-T03 | 实现 Agent 直接检索接口 | 已完成 | P08-T02 |
| P08-T04 | 实现查询规划与分解 | 已完成 | P08-T02、P08-T03 |
| P08-T05 | 实现多次检索与证据检查 | 已完成 | P08-T04 |
| P08-T06 | 实现 Tool 选择和统一执行策略 | 已完成 | P08-T01、P08-T05 |
| P08-T07 | 实现受控 SQL Tool | 已完成 | P08-T06 |
| P08-T08 | 实现受控 API Tool | 已完成 | P08-T06 |
| P08-T09 | 实现 HITL 与高风险审批 | 已完成 | P08-T06 至 P08-T08 |
| P08-T10 | 实现短期与长期记忆 | 已完成 | P08-T01、P08-T09 |
| P08-T11 | 完善预算、Trace、恢复与终止 | 已完成 | P08-T02 至 P08-T10 |
| P08-T12 | 评测并按需实现多 Agent 协作 | 已完成：暂缓多 Agent | P08-T04 至 P08-T11 |
| P08-T13 | 建立 Agentic RAG E2E/评测并验收 | 已完成 | P08-T01 至 P08-T12 |

## 7. 具体任务

### P08-T01：复审场景、Tool 策略和预算

- **状态**：已完成
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
- **实际执行结果**：用户已正式批准 Phase 08；ADR-023 与本计划冻结场景、Tool/SQL/API、HITL、Memory、Evidence、Budget 和 Evaluation 八项决策；配置契约落入 `AgenticRagSettings`，SQL AST 依赖通过项目 `uv` 环境锁定。
- **实际验证结果**：`AgenticRagSettings` 默认值断言、`uv lock --check` 和配置目录 Ruff 全部通过；SQL AST 依赖锁定为 `sqlglot 29.0.1`。
- **计划偏差**：原草案把 SQL/API 只读范围、证据阈值和记忆策略列为待确认；现已由用户指令明确，不再是开放决策。

### P08-T02：实现 KnowledgeBaseTool

- **状态**：已完成
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
- **实际执行结果**：`KnowledgeBaseTool` 以 Pydantic Schema 和 LangChain `StructuredTool` 包装现有 `KnowledgeQueryService`，服务端注入 `ToolAuthorizationContext`，返回候选、Citation、Retrieval Trace 引用和结构化错误；Tool 不接受模型提供 tenant/ACL。
- **实际验证结果**：`tests/contract/agentic_rag/test_kb_tool.py` 通过；固定 RAG 与 Tool 共用查询核心，空结果、越权边界和返回协议通过测试。
- **计划偏差**：无源码复制；规划中的路径落为 `src/ragflow_agent/agent/tools/knowledge_base.py`。

### P08-T03：实现 Agent 直接检索接口

- **状态**：已完成
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
- **实际执行结果**：`AgentKnowledgeGateway` 同时暴露结构化检索与固定 RAG 回答，两条路径共享 `KnowledgeQueryService`、授权上下文、Citation 转换和敏感内容清理。
- **实际验证结果**：`tests/unit/agentic_rag/test_knowledge_gateway.py` 通过；直接 RAG 与 Tool RAG 的租户、ACL、知识库范围和活动版本约束均由统一查询核心执行。
- **计划偏差**：为保持 Agent core 的 import boundary，Gateway 与 Knowledge DTO 转换放在 `agent/tools/knowledge_base.py`，没有让 `agent/application` 直接依赖 Knowledge 模块。

### P08-T04：实现查询规划与分解

- **状态**：已完成
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
- **实际执行结果**：实现确定性保守 Planner 和 LangChain 结构化 Planner；服务端 Tool allowlist 约束模型输出，简单问题直达 RAG，复杂问题生成有限、有序子任务。
- **实际验证结果**：`tests/unit/agentic_rag/test_planning.py` 通过；覆盖简单/复杂路由、非法 Tool、子任务上限和模型故障回退。
- **计划偏差**：节点未拆成多个 `nodes/*.py`，而是在单一 `graphs/agentic_rag.py` 中保持状态迁移内聚；Planner 独立于图实现。

### P08-T05：实现多次检索与证据检查

- **状态**：已完成
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
- **实际执行结果**：LangGraph 按计划执行最多三轮检索；`EvidenceSufficiencyPolicy` 在服务端检查租户/ACL/活动文档、相关度、关键子问题覆盖、冲突、Citation 和提示注入，并产生 `sufficient`、`partial_evidence`、`no_evidence` 或 `conflicting_evidence`。
- **实际验证结果**：`tests/unit/agentic_rag/test_evidence.py` 与 `tests/e2e/agentic_rag` 通过；充分、部分、空、冲突、重复查询和三轮上限均有确定性用例。
- **计划偏差**：证据检查集中在独立 application policy，不允许 LLM 覆盖最终结论。

### P08-T06：实现 Tool 选择和统一执行策略

- **状态**：已完成
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
- **实际执行结果**：实现 `SecureToolRegistry` 和 `SecureToolExecutionService`；执行链固定为注册查找、Schema、服务端权限、风险/HITL、预算、超时/重试、执行、脱敏/大小限制和 Trace 摘要，成功的同 Tool/参数调用受重复执行保护。
- **实际验证结果**：`tests/unit/agentic_rag/test_tool_policy.py` 通过；覆盖未知 Tool、非法参数、越权、模型提权、凭据字段、提示注入、失败分类、重试和预算。
- **计划偏差**：安全与故障测试按项目现有测试层级放入 `tests/unit/agentic_rag` 和 E2E，而未新建仅按名称分类的 `tests/security` 目录。

### P08-T07：实现受控 SQL Tool

- **状态**：已完成
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
- **验证命令**：`uv run pytest tests/unit/agentic_rag/test_sql_tool.py -q`
- **验收标准**：只读、tenant 强制、无凭据泄露。
- **风险和回滚方法**：默认关闭；任何解析不确定即拒绝。
- **实际执行结果**：实现基于 `sqlglot 29.0.1` 的单条 SELECT/只读 CTE AST 校验、库/Schema/表/列/函数 allowlist、参数化约束、服务端 tenant 包装、默认 200 行和 5 秒超时；独立 SQL Adapter 使用只读事务且错误脱敏。
- **实际验证结果**：`tests/unit/agentic_rag/test_sql_tool.py` 通过；DML、DDL、多语句、通配列、字符串直写、越权 tenant、禁用字段/函数和超限均被阻止。
- **计划偏差**：真实生产只读数据源/账号未配置；本阶段验证的是完整安全逻辑和可注入 Executor 协议，不声称真实业务数据库集成。

### P08-T08：实现受控 API Tool

- **状态**：已完成
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
- **验证命令**：`uv run pytest tests/unit/agentic_rag/test_api_tool.py -q`
- **验收标准**：模型不能指定任意 URL/认证；副作用受审批。
- **风险和回滚方法**：默认 GET/allowlist；发现风险立即禁用 Tool。
- **实际执行结果**：实现固定 base URL/path/method 注册、请求/响应 Schema、服务端身份/tenant/凭据注入、禁重定向、连接/读取超时、响应大小/重试限制和敏感字段脱敏；副作用请求必须审批。
- **实际验证结果**：`tests/unit/agentic_rag/test_api_tool.py` 通过；任意 URL、未注册路径/方法、动态认证、超大/非法响应和敏感字段泄漏均被阻止或清理。
- **计划偏差**：使用安全 Fake Transport 做故障注入；未使用生产 API 或真实凭据，不把协议验证描述为生产集成。

### P08-T09：实现 HITL 与高风险审批

- **状态**：已完成
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
- **实际执行结果**：实现八态审批模型、30 分钟默认 TTL、Tool/version/参数摘要/tenant/user/角色/幂等键绑定、CAS 状态转换、LangGraph interrupt/resume、恢复前重新鉴权/策略/预算检查和幂等副作用结果。
- **实际验证结果**：`tests/integration/agentic_rag/test_hitl.py` 和 PostgreSQL Checkpoint 重建测试通过；覆盖批准、拒绝、取消、过期、越权、参数变化失效和重复恢复不重复执行。
- **计划偏差**：按约定只交付 API/Service/持久化/暂停恢复测试，无前端；高风险执行使用 Fake Tool。

### P08-T10：实现短期与长期记忆

- **状态**：已完成
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
- **验证命令**：`uv run pytest tests/unit/agentic_rag/test_memory.py tests/integration/api/test_agentic_api.py -q`
- **验收标准**：短/长期明确；无默认保存密钥/全文。
- **风险和回滚方法**：长期记忆默认关闭/最小化，可全量删除。
- **实际执行结果**：Checkpoint、Agent/Retrieval Trace 和长期记忆物理分离；长期记忆默认关闭，只接受显式 consent 与“记住”请求，记录 consent 版本/时间/来源，tenant+user 双重隔离，90 天 TTL，支持查看、撤回和删除；Worker cron 执行过期/撤回物理清理。
- **实际验证结果**：`tests/unit/agentic_rag/test_memory.py`、API 测试和真实 PostgreSQL Repository 测试通过；覆盖未同意拒绝、隔离、秘密拒绝、TTL、撤回、删除和真实清理。
- **计划偏差**：短期上下文由 LangGraph Checkpoint 状态承担；没有增加 LLM 自动摘要，避免扩大数据保留范围。

### P08-T11：完善预算、Trace、恢复与终止

- **状态**：已完成
- **目标**：统一检索/Tool/模型/记忆的循环、Token、时间、费用和恢复治理。
- **为什么需要**：多 Tool/多检索显著放大成本和故障面。
- **输入**：P08-T02 至 P08-T10。
- **前置任务**：P08-T02 至 P08-T10。
- **操作步骤**：预算 ledger；分别记录并限制业务循环次数、输入/输出/总 Token、端到端运行时间和模型/Tool 费用；定义各维度 hard/soft limit；checkpoint；恢复重验；Trace 关联 retrieval/tool/citation；终止原因。
- **涉及文件**：Agent budgets/runtime/trace、测试。
- **预期输出**：Agentic 运行治理。
- **RAGFlow 源码依据**：上游 Agentic 固定图无完整治理证据。
- **实现或复用方式**：LangGraph + 自研。
- **测试方法**：分别注入循环次数、Token、运行时间和费用超限；验证 soft/hard limit、崩溃恢复、重复副作用和 Trace。
- **验证命令**：`uv run pytest tests/unit/agentic_rag/test_budgets.py tests/e2e/agentic_rag/test_paths.py -q`
- **验收标准**：业务循环次数、Token、运行时间和费用四类预算均有独立可配置上限、独立超限测试和稳定终止原因；Checkpoint 恢复后已消耗预算不回退；无无限循环；副作用节点幂等/审批；成本可解释。
- **风险和回滚方法**：默认保守上限；恢复冲突终止而非重放。
- **实际执行结果**：`BudgetLimits/BudgetUsage` 对迭代、模型、检索、Tool、总/生成 Token、finalization reserve、主动时间和费用实施服务端硬限制；恢复沿用原 ledger。Agent Trace 只保存最小摘要并关联 retrieval trace_id，故障与停止原因结构化。
- **实际验证结果**：`tests/unit/agentic_rag/test_budgets.py`、E2E 和 PostgreSQL 恢复测试通过；覆盖各预算上限、未知/本地费用、重复 Tool、HITL 等待不计 active time、恢复不重置与失败不伪装 no_evidence。
- **计划偏差**：实际故障与预算测试位于 `tests/unit/agentic_rag`、`tests/e2e/agentic_rag`，未创建仅为目录分类的 `tests/fault`。

### P08-T12：评测并按需实现多 Agent 协作

- **状态**：已完成：暂缓启用多 Agent
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
- **验证命令**：`uv run pytest tests/evaluation/agentic_rag/test_report.py -q`
- **验收标准**：若启用则有可重复质量收益且不越权/失控；若暂缓则记录指标、原因和重新评审条件。
- **风险和回滚方法**：多 Agent 默认关闭；关闭 Profile 即回退单 Agent，不能影响 KB Tool 或固定 RAG。
- **实际执行结果**：单 Agent LangGraph 已覆盖直达 RAG、Tool RAG、多步骤检索、SQL/API 联合、HITL 和全部预算/安全场景；当前没有可重复证据证明 supervisor/worker 能带来足以抵消状态、权限、恢复和成本复杂度的收益，因此 CAP-32 保持默认关闭并暂缓实现。
- **实际验证结果**：28 场景确定性基线总体通过率 100%，Tool 选择/参数合法率 100%，无必须依赖多 Agent 才能通过的场景；重新评审条件为 Phase 09/10 出现单 Agent 无法满足且可量化的质量、隔离或吞吐需求。
- **计划偏差**：按任务原定“按需实现”门禁作出暂缓结论，因此未创建 `agent/graphs/multi_agent/`；这不是漏实现，也不把 CAP-32 标为已实现。

### P08-T13：建立 Agentic RAG E2E/评测并验收

- **状态**：已完成
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
- **验证命令**：`uv run pytest -q tests/contract/agentic_rag tests/unit/agentic_rag tests/integration/agentic_rag tests/e2e/agentic_rag tests/evaluation/agentic_rag`; `uv run python -m ragflow_agent.agent.evaluation --input tests/evaluation/agentic_rag/deterministic-results.json --output <temporary-report-path>`
- **验收标准**：CAP-28/31/32 及 CAP-29 Agentic 扩展按真实结果通过；越权零容忍。
- **风险和回滚方法**：无收益/高风险 Tool 默认关闭；不降低安全门禁。
- **实际执行结果**：建立 28 场景、合法无敏感数据的 `deterministic_fake` 评测输入与机器可读报告生成器，覆盖两条 RAG 路径、多跳、SQL/API、安全、HITL、Memory、预算、故障和 Citation；完成 API/Service/Graph/Repository/迁移和阶段文档。
- **实际验证结果**：Phase 08 定向套件 62 通过、3 项因未注入 PostgreSQL 而条件跳过；Phase 08 PostgreSQL Repository/Checkpoint/只读 SQL Adapter 专项另行 3/3 通过。完整隔离四后端套件 286 通过、仅本机 Tesseract 可选项 1 跳过。评测 28/28，通过率、Tool 合法率、no/partial 准确率、Citation 覆盖率和 groundedness 均为 100%，关键安全违规 0。
- **计划偏差**：指标仅代表确定性 Fake/安全隔离测试；未运行真实 DeepSeek、BGE-M3、BGE Reranker、生产 SQL 或生产 API，不能外推为真实模型质量或生产集成效果。

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

## 9. 实际执行结果

- **实际 Tool/模型/预算/记忆策略**：ADR-023 的八项策略均已落入类型化配置、领域对象、Policy、Graph、Repository、API、Worker 与测试；业务代码仍经内部 Provider/Port，不直接绑定供应商 SDK。
- **实际任务成功/安全/成本指标**：`deterministic_fake` 28/28；总体、Tool 合法率、no/partial、Citation、groundedness 均为 100%，关键安全违规 0。该结果只证明确定性协议和策略，不代表真实模型质量。
- **阶段级验证**：Ruff 全部通过；mypy 对 329 个源文件通过；无外部配置套件 268 通过/19 条件跳过；隔离 PostgreSQL/Redis/MinIO/Elasticsearch 套件 286 通过/1 条件跳过；Alembic `0005 -> 0004 -> 0005` 往返通过；API/Worker bootstrap 与 `uv lock --check` 通过。
- **迁移与数据边界**：`20260731_0005_phase08_agentic_rag.py` 建立 Agent Run、Approval、Memory Consent 和 Long-term Memory 表；LangGraph Checkpoint 表仍由官方 `AsyncPostgresSaver.setup()` 管理。
- **计划偏差与新增 ADR**：新增 ADR-023；节点保持在一个内聚图文件；多 Agent 因无量化增益暂缓；安全/故障测试沿用现有测试层级；没有复制、抽取或改写 RAGFlow 源码。
- **阶段出口结论**：Phase 08 DoD 已满足。Phase 09 的阶段依赖已满足，但 O-009、O-011 及高级能力数据集/资源/索引兼容方案仍须在执行前按 Phase 09 正式计划复审；本阶段不执行 Phase 09。
