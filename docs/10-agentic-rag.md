---
document_id: AGENTIC-RAG-RUNTIME
document_role: Phase 08 实现事实与运行边界
status: active
last_updated_at: "2026-07-31"
---

# Agentic RAG运行时

本文件记录 Phase 08 已实现事实。项目总览见[项目主文档](./00-project-master.md)，阶段证据见[Phase 08执行记录](./phases/phase-08-agentic-rag.md)，约束决策见[ADR-023](./07-decisions-and-risks.md#adr-023phase-08-agentic-rag-安全证据hitl记忆与预算基线)。

## 1. 已实现边界

- 简单问题走 `AgentKnowledgeGateway.answer_direct` 固定 RAG，不强制经过 Tool。
- 复杂问题由 LangGraph Planner 选择已注册 Tool；知识库 Tool 仍调用同一个 `KnowledgeQueryService`。
- 多步骤问题最多三轮检索，最终由服务端 `EvidenceSufficiencyPolicy` 判定 `sufficient`、`partial_evidence`、`no_evidence` 或 `conflicting_evidence`。
- SQL/API 只通过显式 Registry 和服务端 Policy 执行；Phase 08 未接入生产数据源或真实凭据。
- 高风险 Tool 通过持久审批记录和 LangGraph Checkpoint 暂停/恢复；没有前端页面。
- 长期记忆默认关闭，显式同意后才能写入；Checkpoint、Trace、Memory 分离。
- 所有循环、模型、检索、Tool、Token、主动运行时间和已知费用均受服务端预算控制。
- 单 Agent 已满足首批评测场景；多 Agent 在 Phase 08 明确暂缓，未实现。

## 2. 调用链

```text
POST /v1/agentic-rag/runs
  -> AgenticRagRuntime.start
  -> LangGraph route
     -> simple: AgentKnowledgeGateway.answer_direct
        -> FixedRagService
        -> KnowledgeQueryService
     -> complex: planner -> SecureToolExecutionService
        -> KnowledgeBaseTool -> KnowledgeQueryService
        -> ControlledSqlTool -> SqlExecutorPort
        -> ControlledApiTool -> ApiTransportPort
  -> EvidenceSufficiencyPolicy
  -> answer / conservative terminal state / approval_required

POST /v1/agentic-rag/runs/{run_id}/resume
  -> ApprovalService revalidation
  -> persisted LangGraph Checkpoint
  -> policy + authorization + budget recheck
  -> idempotent execution or terminal status
```

直接 RAG 和 Tool RAG 都继承服务端 `ToolAuthorizationContext`，不能从模型参数取得 `tenant_id`、角色、ACL 或知识库范围。Agent Trace 保存 retrieval trace_id 引用，而不复制完整查询、Chunk、Prompt、凭据或敏感 Tool 响应。

## 3. 关键代码

| 职责 | 实现 |
|---|---|
| 领域状态、审批、记忆、预算、Trace | `src/ragflow_agent/agent/domain/agentic.py` |
| Port | `src/ragflow_agent/agent/ports/agentic.py` |
| LangGraph 路由与执行 | `src/ragflow_agent/agent/graphs/agentic_rag.py` |
| Runtime 与恢复 | `src/ragflow_agent/agent/application/agentic_runtime.py` |
| KB Tool 和共享 Gateway | `src/ragflow_agent/agent/tools/knowledge_base.py` |
| Tool Registry/执行策略 | `src/ragflow_agent/agent/application/tool_policy.py` |
| SQL/API 安全 Tool | `src/ragflow_agent/agent/tools/sql.py`、`api.py` |
| SQL/API 基础设施 | `src/ragflow_agent/agent/infrastructure/sql.py`、`http.py` |
| HITL | `src/ragflow_agent/agent/application/hitl.py` |
| Memory | `src/ragflow_agent/agent/application/memory.py` |
| Evidence/Budget | `src/ragflow_agent/agent/application/evidence.py`、`budgets.py` |
| PostgreSQL Repository | `src/ragflow_agent/agent/infrastructure/database/` |
| API | `src/ragflow_agent/api/routes/agentic.py` |
| Worker 清理任务 | `src/ragflow_agent/worker/arq_worker.py` |
| 迁移 | `migrations/versions/20260731_0005_phase08_agentic_rag.py` |
| 评测 | `src/ragflow_agent/agent/evaluation/`、`tests/evaluation/agentic_rag/` |

## 4. 不可绕过的Policy

Tool 执行顺序固定为：Registry 查找、输入 Schema、凭据字段拒绝、服务端鉴权、风险/HITL、预算、超时/重试、执行、输出 Schema/大小、敏感字段脱敏和 Trace。未知 Tool、模型编造的 Tool、任意 Shell/文件/URL、SQL 写操作与多语句默认拒绝。

SQL 使用 `sqlglot` AST，只允许单条 SELECT/只读 CTE，并执行数据库、Schema、表、字段和函数 allowlist；模型不得控制 tenant 条件。API 只能访问注册时确定的 base URL/path/method，HTTP Transport 禁止重定向，认证由 Secret Provider 注入。

HITL 状态为 `approval_required`、`approved`、`rejected`、`expired`、`cancelled`、`executing`、`succeeded`、`failed`。批准与 Tool 名称、版本和参数摘要绑定；恢复执行重新检查授权、策略、资源、预算和 TTL。重复恢复读取幂等结果，不能重复副作用。

## 5. 数据保留与预算

长期记忆默认 TTL 90 天，保存 consent 版本、时间、tenant、user 和来源；只能保存用户明确确认的稳定信息。撤回/删除后立即不可查询，Worker 清理任务保证物理删除。Memory 不写回知识索引，也不能扩大 ACL 或 Tool 权限。

默认单次运行预算：迭代 8、模型调用 6、检索 3、Tool 尝试 10、总 Token 50000、生成 Token 8000、最终生成预留 1500、主动运行 120 秒、模型调用 45 秒、Tool 调用 15 秒、已知费用 0.50 美元。Checkpoint 恢复沿用剩余预算；等待审批不计主动运行时间，但审批 TTL 持续计算。

## 6. 验证事实与限制

- 确定性 Phase 08 评测 28/28 通过；总体、Tool 合法率、no/partial 判断、Citation 覆盖和 groundedness 均为 100%，关键安全违规 0。
- Phase 08 定向测试 62 通过、3 个 PostgreSQL 条件 skip；真实 PostgreSQL Repository/Checkpoint/只读 SQL Adapter 专项另行 3/3 通过。
- 隔离 PostgreSQL、Redis、MinIO、Elasticsearch 全套测试 286 通过；仅本机无 Tesseract 的可选测试跳过。
- 真实 DeepSeek、BGE-M3、BGE Reranker、生产 SQL/API 和生产高风险写操作均未验证或接入；Fake/Stub 结果不能作为真实模型效果结论。
- Phase 08 未复制、抽取或改写 RAGFlow 源码；只参考冻结基线公开职责与行为。

## 7. 变更规则

新增 Tool 必须先注册完整元数据和安全测试；提升默认预算、引入生产写操作、扩大长期记忆、启用多 Agent、复制 RAGFlow 源码或改变 Checkpoint/Trace/Memory 边界，必须先更新[决策与风险](./07-decisions-and-risks.md)。
