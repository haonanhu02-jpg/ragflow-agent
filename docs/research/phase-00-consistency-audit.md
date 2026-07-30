---
document_id: phase-00-consistency-audit
title: Phase 00 跨文档一致性审计
version: 1.0.0
status: completed
last_updated: 2026-07-30
scope: Phase 00 / P00-T12
---

# Phase 00 跨文档一致性审计

## 1. 文档定位

本报告记录 `P00-T12` 的检查范围、发现项、修正结果和遗留阻塞。它只证明 Phase 00 研究文档在当前基线下通过一致性检查，不表示任何规划能力已经实现。

> **历史快照说明（2026-07-30）**：本报告第 2～7 节保留 P00-T12 在 2026-07-29 的原始 42 项、无时序 RAG、仅 Phase 00 计划的验收现场。用户后续确认 Phase 00 完成，并要求 Phase 09 恢复时序 RAG、生成 Phase 01～10 计划；现行状态以 ADR-013、ADR-014、能力矩阵 `CAP-01`～`CAP-43` 和阶段索引为准，不能用本报告的历史状态覆盖现行文档。

入口与关联文档：

- [项目总纲](../00-project-master.md)
- [RAGFlow 架构](../01-ragflow-architecture.md)
- [能力矩阵](../02-ragflow-capability-matrix.md)
- [目标架构](../03-target-architecture.md)
- [代码复用策略](../04-code-reuse-strategy.md)
- [总体路线图](../05-development-roadmap.md)
- [工程规范](../06-engineering-standards.md)
- [决策与风险](../07-decisions-and-risks.md)
- [阶段状态索引](../phases/README.md)
- [Phase 00 详细计划](../phases/phase-00-research-and-baseline.md)
- [RAGFlow 双基线](./ragflow-baseline.md)
- [目标项目基线](./project-baseline.md)
- [RAGFlow 源码证据地图](./ragflow-source-map.md)

## 2. 审计基线与边界

- RAGFlow 冻结基线：`cd846cc9d4e32a19e684c59a1f302601027ef976`，版本 `0.26.4`，提交日期 `2026-07-27`。
- 滚动观察基线：`main@3c59b707c28f7d0ed2fb62135c661e7633537a1a`，观察日期 `2026-07-29`。
- 目标项目目录：`D:/download/myself`。
- 目标项目没有 `.git`，也没有业务源码、包定义、迁移或测试；本轮只修改 Markdown 文档。
- 审计不执行 Phase 01，不创建 Phase 01–10 详细计划，不把路线图能力标记为已实现。

## 3. 检查方法

### 3.1 自动检查

1. 所有 Markdown 文件按 UTF-8 读取，检查不存在 `U+FFFD` 替换字符。
2. 检查围栏代码块数量为偶数。
3. 忽略围栏代码块后解析相对 Markdown 链接，并验证目标存在。
4. 以未转义的 `|` 为分隔符检查每个 Markdown 表格的列数。
5. 检查能力矩阵恰有 `CAP-01` 至 `CAP-42`，每行字段完整、阶段只属于 Phase 01–10、分类值合法。
6. 检查不存在旧的 Phase 11 表格行或旧阶段计划文件名。
7. 检查 RAGFlow 长期源码链接没有使用 `/blob/main/` 或 `/tree/main/`。
8. 检查阶段目录只存在 Phase 00 详细计划和状态索引。
9. 检查 `AGENTS.md` 与全部总体规划、研究产物文件存在。

### 3.2 人工检查

1. 对照路线图复核 Phase 00–10 名称、直接依赖和责任边界。
2. 对照能力矩阵复核能力名称、采用分类、实施阶段和当前状态。
3. 对照源码证据地图复核离线、在线、Agent、生命周期、权限和高级 RAG 的关键结论。
4. 对照 ADR 复核 Python-only、无时序 RAG、模块化单体 FastAPI、独立 Ingestion Worker、第一版权限边界。
5. 检查“已确认事实”“规划方案”“待验证内容”没有互相冒充。

## 4. 发现项与处理结果

| ID | 严重度 | 发现 | 处理 | 状态 |
|---|---|---|---|---|
| F-001 | 高 | 总纲、能力矩阵和决策记录残留旧的 12 阶段映射及 Phase 11 | 统一为 Phase 00–10；Phase 02=Agent 基础、Phase 03=知识库统一接口、Phase 04=最小 RAG 闭环、Phase 09=高级 RAG、Phase 10=评测与生产化 | 已修正 |
| F-002 | 高 | 路线图、阶段索引和 Phase 00 计划的执行状态未反映 P00-T01 至 P00-T11 实际完成情况 | 按真实验证记录更新任务和阶段状态；不把 Phase 00 标记完成 | 已修正 |
| F-003 | 高 | 能力矩阵部分能力仍映射到旧阶段或已取消的 Phase 11 | 42 项能力全部重映射到 Phase 01–10，并保持“未实现” | 已修正 |
| F-004 | 中 | 源码证据地图表格单元格中的 `me\|team` 未转义，造成 Markdown 列数错误 | 改为 `me\|team` | 已修正 |
| F-005 | 中 | 总纲未把三个 Phase 00 研究产物列为已生成的事实入口 | 补充双基线、项目基线和源码证据地图链接 | 已修正 |
| F-006 | 中 | `visibility`/权限领域接口曾被归入 Agent 基础阶段 | 统一归入 Phase 03“知识库统一接口” | 已修正 |
| F-007 | 中 | 评测和可观测性表述可能把 RAGFlow 的压测、token sink、Langfuse/OTel 配置误写为完整质量评测与端到端追踪 | 明确其只覆盖部分基准或接入点；Recall/MRR/NDCG、faithfulness、引用正确性、Agent 成功率和统一 Retrieval Trace 仍需自研 | 已修正 |
| F-008 | 低 | 路线图和状态索引提前引用尚未生成的本报告，导致相对链接暂时失效 | 生成本报告后重新执行链接检查 | 已修正 |

## 5. 一致性结论

### 5.1 已通过

- 阶段集合统一为 Phase 00–10，名称和直接依赖一致。
- 能力矩阵包含 42 项能力，所有能力仍为规划状态，没有业务实现证据的能力未被标记完成。
- LangChain 负责标准组件和适配，LangGraph 负责 Agent 编排，RAGFlow Python 代码只经隔离层评估复用，自研层负责企业边界、可靠性和缺口能力。
- API/Worker 拓扑、Python-only、无时序 RAG、第一版 `tenant_id` 强制隔离及 `owner_id`、`visibility`、`AuthorizationContext`、`PermissionChecker` 边界一致。
- RAGFlow 事实引用固定到冻结 commit；滚动 `main` 仅作为差异观察，不作为长期事实链接。
- 没有创建 Phase 01–10 的详细计划或业务代码。
- `docs/06-engineering-standards.md` 在本轮检查中没有需要改变的语义，仅作为一致性输入保留。

### 5.2 未解决但不推翻 P00-T12

| 项目 | 影响 | 处理 |
|---|---|---|
| O-001 项目正式名称和 Python 包名 | 阻止 Phase 00 出口和 Phase 01 准入 | 继续使用 `src/app` 文档占位；不得创建包 |
| 七份辅助文档的最终用户确认 | 阻止 Phase 00 Definition of Done | 在出口审查中明确列为待用户确认 |
| Phase 00 出口结论的用户确认 | 阻止将 Phase 00 标记完成 | P00-T13 只能先给出“不准入”结论 |
| Phase 01 详细计划不存在 | 阻止执行 Phase 01 | 这是本轮明确限制；不得提前创建 |
| O-002、O-006、O-007 | 在 Phase 04 前必须决定模型、队列和搜索后端 | 不阻止完成研究审计，不得擅自决策 |
| O-004 | 首次抽取 RAGFlow 代码前必须完成依赖/许可证试验 | 不阻止完成研究审计，不得直接复制 |

## 6. P00-T12 验收

- 产出：本报告及受影响总体文档修正。
- 结果：结构、链接、阶段、能力矩阵、长期源码链接、状态和责任边界检查通过。
- 计划偏差：原计划只要求在 Phase 00 计划第 14 节记录结果；实际增加独立报告，便于长期审计和让路线图、状态索引稳定链接。
- 结论：`P00-T12` 可以标记为已完成；Phase 00 是否结束由 `P00-T13` 单独判定。
