---
document_id: PHASE-STATUS-INDEX
document_role: 阶段计划与执行状态入口
status: active
last_updated_at: "2026-07-30"
current_phase: Phase 03 completed; Phase 04 entry blocked
---

# 阶段状态索引

## 文档导航

[项目总纲](../00-project-master.md) · [开发路线图](../05-development-roadmap.md) · [决策与风险](../07-decisions-and-risks.md) · [Phase 00](./phase-00-research-and-baseline.md) · [Phase 01](./phase-01-project-skeleton.md) · [Phase 02](./phase-02-agent-foundation.md)

## 状态规则

- “计划状态”只说明详细计划文件是否存在并通过检查，不代表阶段已经执行。
- “执行状态”只有在代码、文档、验证命令和验收结果满足阶段 DoD 后才能改为“已完成”。
- 当前项目已完成最小 Agent Runtime和知识领域/Ports/权限/统一查询契约，但没有真实知识基础设施或 RAG 闭环；项目 Git 根目录为 `D:/download/ragflow-agent`，Phase 01 至 Phase 03 的任务已完成。
- Phase 01/02/03 计划状态为“已确认”；Phase 04 至 Phase 10 为“预规划草案”。每阶段执行前必须按上一阶段实际结果复审并确认。
- 阶段名称、依赖和门禁以[开发路线图](../05-development-roadmap.md)为准。

## 阶段状态

| 阶段 | 计划文件 | 计划状态 | 执行状态 | 前置阶段 | 进入条件 | 完成条件 |
|---|---|---|---|---|---|---|
| Phase 00：研究与基线 | [`phase-00-research-and-baseline.md`](./phase-00-research-and-baseline.md) | 已确认 | 已完成 | 无 | 项目目标、路径、Python-only 和双基线可读取 | P00-T01 至 P00-T13、文档一致性和用户出口确认通过 |
| Phase 01：项目骨架 | [`phase-01-project-skeleton.md`](./phase-01-project-skeleton.md) | 已确认 | 已完成 | Phase 00 | 已满足：O-001、O-012、计划确认及工作区复查 | P01-T01 至 P01-T10 和骨架质量门禁通过 |
| Phase 02：Agent基础 | [`phase-02-agent-foundation.md`](./phase-02-agent-foundation.md) | 已确认 | 已完成 | Phase 01 | 已满足：Phase 01 完成、计划复审、ADR-017 冻结 | P02-T01 至 P02-T10，Checkpoint/Trace/错误恢复/最小 Agent 验收通过 |
| Phase 03：知识库统一接口 | [`phase-03-knowledge-interface.md`](./phase-03-knowledge-interface.md) | 已确认 | 已完成 | Phase 02 | 已满足：Phase 02 完成、计划复审、ADR-018 冻结 | P03-T01 至 P03-T11，领域/Ports/权限/Service 契约和阶段门禁通过 |
| Phase 04：最小RAG闭环 | [`phase-04-minimum-rag.md`](./phase-04-minimum-rag.md) | 预规划草案 | 未执行 | Phase 03 | 仅 P04-T01 具备复审入口；P04-T02 起要求 O-002/O-006/O-007 已解决，抽取时 O-004 已解决 | P04-T01 至 P04-T12，上传到 Citation 回答 E2E 通过 |
| Phase 05：Parser与Chunk | [`phase-05-parser-and-chunk.md`](./phase-05-parser-and-chunk.md) | 预规划草案 | 未执行 | Phase 04 | Phase 04 完成；复用/许可/样本/资源复审 | P05-T01 至 P05-T12，格式/策略黄金和资源测试通过 |
| Phase 06：在线检索 | [`phase-06-online-retrieval.md`](./phase-06-online-retrieval.md) | 预规划草案 | 未执行 | Phase 04、Phase 05 | 两阶段完成；O-008/融合/Reranker/Trace 策略确认 | P06-T01 至 P06-T12，检索/Citation/Trace/评测通过 |
| Phase 07：文档生命周期 | [`phase-07-document-lifecycle.md`](./phase-07-document-lifecycle.md) | 预规划草案 | 未执行 | Phase 05、Phase 06 | 两阶段完成；版本/任务/回收语义复审 | P07-T01 至 P07-T11，版本/幂等/补偿/故障恢复通过 |
| Phase 08：Agentic RAG | [`phase-08-agentic-rag.md`](./phase-08-agentic-rag.md) | 预规划草案 | 未执行 | Phase 02、Phase 06 | 两阶段完成；Tool/预算/安全/记忆范围确认 | P08-T01 至 P08-T13，KB/SQL/API Tool、HITL、记忆、预算及多 Agent 决策通过 |
| Phase 09：高级RAG | [`phase-09-advanced-rag.md`](./phase-09-advanced-rag.md) | 预规划草案 | 未执行 | Phase 05、Phase 06、Phase 08 | 三阶段完成；O-009/O-011、数据集/资源/存储确认 | P09-T01 至 P09-T12，十项范围逐项验收及兼容门禁通过 |
| Phase 10：评测与生产化 | [`phase-10-evaluation-and-production.md`](./phase-10-evaluation-and-production.md) | 预规划草案 | 未执行 | Phase 07、Phase 08、Phase 09 | 三阶段完成；生产平台/SLO/RPO/RTO/安全确认 | P10-T01 至 P10-T13，质量/安全/部署/恢复/发布门禁通过 |

## 当前准入结论

- Phase 00 至 Phase 03 已完成；目标项目已具备最小 Agent Runtime和知识领域/Ports/权限/统一查询契约，真实知识基础设施和 RAG 业务仍未开始。
- P02-T01 至 P02-T10 已完成并通过真实 PostgreSQL、Unit/Contract/Integration/E2E 和静态阶段门禁。
- P03-T01 至 P03-T11 已完成并通过领域/权限/状态机、Repository/UoW、全部能力 Ports、Service 和导入边界门禁。
- Phase 04 至 Phase 10 都是预规划草案，必须逐阶段复审确认；Phase 04 目前受 O-002/O-006/O-007 阻塞。
- 2026-07-30 新增 ADR-017（Phase 02 Agent Runtime 与持久 Checkpoint 基线）和 ADR-018（Phase 03 领域/权限/统一查询契约）；Phase 00 旧一致性审计仍记录当时 42 项基线事实。

## 2026-07-30 计划生成一致性检查

- Phase 00 至 Phase 10 共 11 份阶段文件全部存在。
- Phase 01 至 Phase 10 共 116 项计划任务：10、10、11、12、12、12、11、13、12、13。
- 任务编号逐阶段连续且无重复；129 个全阶段任务 ID（含 Phase 00 的 13 项）均有定义，未发现失效任务引用。
- 每个 Phase 01 至 Phase 10 任务均具备状态、目标、必要性、输入、依赖、步骤、文件、输出、源码依据、采用方式、测试、命令、验收、风险/回滚和三个实际结果预留字段。
- 25 个 Markdown 文件的本地链接检查为零失效、零无法解析目标；未使用浮动 RAGFlow `/blob/main/` 或 `/tree/main/` 源码链接。
- 能力矩阵为连续 `CAP-01` 至 `CAP-43`；CAP-31 只在 Phase 08 实现，生成式 Chunk 增强集中在 Phase 09。
- 计划生成检查时目标项目还没有 Git 元数据；当前已完成 Phase 01 工程骨架、Phase 02 Agent 基础和 Phase 03 知识统一契约，但仍没有真实知识基础设施/RAG 业务实现。
