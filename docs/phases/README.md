---
document_id: PHASE-STATUS-INDEX
document_role: 阶段计划与执行状态入口
status: active
last_updated_at: "2026-08-01"
current_phase: Phase 09 completed; Phase 10 in progress
---

# 阶段状态索引

## 文档导航

[项目总纲](../00-project-master.md) · [开发路线图](../05-development-roadmap.md) · [决策与风险](../07-decisions-and-risks.md) · [Phase 00](./phase-00-research-and-baseline.md) · [Phase 01](./phase-01-project-skeleton.md) · [Phase 02](./phase-02-agent-foundation.md)

## 状态规则

- “计划状态”只说明详细计划文件是否存在并通过检查，不代表阶段已经执行。
- “执行状态”只有在代码、文档、验证命令和验收结果满足阶段 DoD 后才能改为“已完成”。
- 当前项目已完成最小 Agent Runtime、知识领域/Ports/权限/统一查询契约、Phase 04 最小 RAG、Phase 05 Parser/Chunk、Phase 06 在线检索和 Phase 07 文档生命周期；项目 Git 根目录为 `D:/download/ragflow-agent`。
- Phase 01 至 Phase 09 计划状态为“已确认”且执行完成；Phase 10 已批准并执行中。
- 阶段名称、依赖和门禁以[开发路线图](../05-development-roadmap.md)为准。

## 阶段状态

| 阶段 | 计划文件 | 计划状态 | 执行状态 | 前置阶段 | 进入条件 | 完成条件 |
|---|---|---|---|---|---|---|
| Phase 00：研究与基线 | [`phase-00-research-and-baseline.md`](./phase-00-research-and-baseline.md) | 已确认 | 已完成 | 无 | 项目目标、路径、Python-only 和双基线可读取 | P00-T01 至 P00-T13、文档一致性和用户出口确认通过 |
| Phase 01：项目骨架 | [`phase-01-project-skeleton.md`](./phase-01-project-skeleton.md) | 已确认 | 已完成 | Phase 00 | 已满足：O-001、O-012、计划确认及工作区复查 | P01-T01 至 P01-T10 和骨架质量门禁通过 |
| Phase 02：Agent基础 | [`phase-02-agent-foundation.md`](./phase-02-agent-foundation.md) | 已确认 | 已完成 | Phase 01 | 已满足：Phase 01 完成、计划复审、ADR-017 冻结 | P02-T01 至 P02-T10，Checkpoint/Trace/错误恢复/最小 Agent 验收通过 |
| Phase 03：知识库统一接口 | [`phase-03-knowledge-interface.md`](./phase-03-knowledge-interface.md) | 已确认 | 已完成 | Phase 02 | 已满足：Phase 02 完成、计划复审、ADR-018 冻结 | P03-T01 至 P03-T11，领域/Ports/权限/Service 契约和阶段门禁通过 |
| Phase 04：最小RAG闭环 | [`phase-04-minimum-rag.md`](./phase-04-minimum-rag.md) | 已确认 | 已完成 | Phase 03 | 已满足：Phase 03 完成；ADR-019 解决 O-002/O-006/O-007；O-004 按不抽取源码闭环 | 已满足：P04-T01 至 P04-T12，Fake/真实后端上传到 Citation 回答 E2E 通过 |
| Phase 05：Parser与Chunk | [`phase-05-parser-and-chunk.md`](./phase-05-parser-and-chunk.md) | 已确认 | 已完成 | Phase 04 | 已满足：Phase 04 完成；ADR-020 冻结复用/许可/样本/资源 | 已满足：P05-T01 至 P05-T12，八格式、九策略、资源、真实后端和 CI 门禁通过 |
| Phase 06：在线检索 | [`phase-06-online-retrieval.md`](./phase-06-online-retrieval.md) | 已确认 | 已完成 | Phase 04、Phase 05 | 已满足：两阶段完成；ADR-021 冻结 O-008/RRF/Reranker/Trace | 已满足：P06-T01 至 P06-T12，检索/Citation/Trace/评测及阶段门禁通过 |
| Phase 07：文档生命周期 | [`phase-07-document-lifecycle.md`](./phase-07-document-lifecycle.md) | 已确认 | 已完成 | Phase 05、Phase 06 | 已满足：两阶段完成；ADR-022 冻结版本/任务/回收/补偿语义 | 已满足：P07-T01 至 P07-T11，版本/幂等/补偿/故障恢复和隔离四后端门禁通过 |
| Phase 08：Agentic RAG | [`phase-08-agentic-rag.md`](./phase-08-agentic-rag.md) | 已确认 | 已完成 | Phase 02、Phase 06 | 已满足：两阶段完成；ADR-023 冻结 Tool/预算/安全/记忆范围 | 已满足：P08-T01 至 P08-T13，两条 RAG 路径、KB/SQL/API Tool、HITL、记忆、预算、评测及多 Agent 暂缓决策通过 |
| Phase 09：高级RAG | [`phase-09-advanced-rag.md`](./phase-09-advanced-rag.md) | 已确认 | 已完成 | Phase 05、Phase 06、Phase 08 | 已满足：ADR-024、数据集/预算/存储/兼容冻结 | 已满足：P09-T01 至 P09-T12，九类能力和兼容/生命周期门禁通过 |
| Phase 10：评测与生产化 | [`phase-10-evaluation-and-production.md`](./phase-10-evaluation-and-production.md) | 已确认 | 执行中 | Phase 07、Phase 08、Phase 09 | 已满足：ADR-025 冻结平台/SLO/RPO/RTO/安全 | P10-T01 至 P10-T13，质量/安全/部署/恢复/发布门禁通过 |

## 当前准入结论

- Phase 00 至 Phase 08 已完成；目标项目已具备最小 Agent Runtime、知识领域/Ports/权限/统一查询契约、真实后端最小 RAG、八格式 Parser/Tesseract OCR/schema v2/九种 Chunk Method、安全在线检索、版本化文档生命周期和受治理 Agentic RAG。
- P02-T01 至 P02-T10 已完成并通过真实 PostgreSQL、Unit/Contract/Integration/E2E 和静态阶段门禁。
- P03-T01 至 P03-T11 已完成并通过领域/权限/状态机、Repository/UoW、全部能力 Ports、Service 和导入边界门禁。
- P04-T01 至 P04-T12 已完成并通过 PostgreSQL/MinIO/Redis/Elasticsearch 真实后端、Fake Provider、迁移、tenant、Citation/Trace、本地质量门禁及代码提交 `0732d47` 的 GitHub Actions。
- P05-T01 至 P05-T12 已完成；实现提交 `0a4bca1` 已推送，GitHub Actions run `30614252319` 成功，包含真实 Tesseract `eng`/`chi_sim`、bbox 和完整质量门禁。
- P06-T01 至 P06-T12 已完成；双路召回、RRF、Provider 隔离 Reranker、有限安全降级和内容最小化持久 Trace 已通过真实 Elasticsearch/PostgreSQL 与完整质量门禁。
- P07-T01 至 P07-T11 已完成；不可变版本、候选索引/alias + CAS 激活、删除/恢复/回收、Outbox、重试/死信、取消、批量和 reconciliation 已通过完整质量门禁与隔离四后端测试；实现提交 `71f15d5` 的 [GitHub Actions](https://github.com/haonanhu02-jpg/ragflow-agent/actions/runs/30634884467) 成功。
- P08-T01 至 P08-T13 已完成；直接 RAG/Tool RAG、规划/有限检索、Evidence、Tool Registry、SQL/API 安全、持久 HITL、长期记忆、预算和 Trace 已通过完整质量门禁；多 Agent 因无量化收益暂缓。
- Phase 09 已完成；Phase 10 按 ADR-025 执行中。高级能力均保持 experimental/off，不能把 Fake 评测描述为真实模型效果。
- ADR-017 至 ADR-023 分别记录 Phase 02 至 Phase 08 的执行基线；Phase 00 旧一致性审计仍记录当时 42 项基线事实。

## 2026-07-30 计划生成一致性检查

- Phase 00 至 Phase 10 共 11 份阶段文件全部存在。
- Phase 01 至 Phase 10 共 116 项计划任务：10、10、11、12、12、12、11、13、12、13。
- 任务编号逐阶段连续且无重复；129 个全阶段任务 ID（含 Phase 00 的 13 项）均有定义，未发现失效任务引用。
- 每个 Phase 01 至 Phase 10 任务均具备状态、目标、必要性、输入、依赖、步骤、文件、输出、源码依据、采用方式、测试、命令、验收、风险/回滚和三个实际结果预留字段。
- 25 个 Markdown 文件的本地链接检查为零失效、零无法解析目标；未使用浮动 RAGFlow `/blob/main/` 或 `/tree/main/` 源码链接。
- 能力矩阵为连续 `CAP-01` 至 `CAP-43`；CAP-31 只在 Phase 08 实现，生成式 Chunk 增强集中在 Phase 09。
- 计划生成检查时目标项目还没有 Git 元数据；当前已完成 Phase 01 工程骨架、Phase 02 Agent 基础、Phase 03 知识统一契约和 Phase 04 最小 RAG 闭环。
