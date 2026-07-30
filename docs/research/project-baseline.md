---
document_id: PROJECT-BASELINE
status: active
observed_at: "2026-07-30"
project_root: "D:/download/myself"
---

# 目标项目现状基线

## 文档导航

[项目总纲](../00-project-master.md) · [开发路线图](../05-development-roadmap.md) · [Phase 00 计划](../phases/phase-00-research-and-baseline.md)

## 1. 结论

- **[事实]** `D:/download/myself` 可读取，没有 `.git`，因此不存在可执行的 `git status` 或可报告的项目 commit。
- **[事实]** 2026-07-30 盘点时项目只有 `AGENTS.md` 和 Markdown 文档；没有业务源码。
- **[事实]** `src/`、`tests/`、`migrations/`、`pyproject.toml`、`uv.lock`、`.env.example`、`README.md`、`deployments/`、`scripts/`、`.github/` 均不存在。
- **[事实]** Python 文件、数据库迁移、自动化测试、部署文件数量均为 0。
- **[事实]** 当前没有 FastAPI 服务、Ingestion Worker、Agent Runtime、知识库实体、Parser、Chunk、Embedding、索引、检索、引用或权限实现。
- **[事实]** Phase 00 已完成；Phase 01 为“待确认/未执行”，Phase 02 至 Phase 10 为“预规划草案/未执行”。

## 2. 文件清单

2026-07-30 同步完成后共有 25 个文件，全部为 Markdown：

| 文件 | 类型 | 状态解释 |
|---|---|---|
| `AGENTS.md` | 操作入口 | 已存在，不是业务实现 |
| `docs/00-project-master.md` | 总纲 | 已存在，事实/规划文档 |
| `docs/01-ragflow-architecture.md` | RAGFlow 分析 | 已存在，Phase 00 已核验产物 |
| `docs/02-ragflow-capability-matrix.md` | 能力矩阵 | 已存在，Phase 00 已核验并在 ADR-014 后追加 CAP-43 |
| `docs/03-target-architecture.md` | 目标架构 | 已存在，规划，不是实现 |
| `docs/04-code-reuse-strategy.md` | 复用策略 | 已存在，当前无已批准直接复用代码 |
| `docs/05-development-roadmap.md` | 总体路线图 | 已存在，规划，不是实现 |
| `docs/06-engineering-standards.md` | 工程规则 | 已存在，Phase 01 才落地工具配置 |
| `docs/07-decisions-and-risks.md` | ADR/风险注册表 | 已存在 |
| `docs/phases/README.md` | 阶段状态索引 | 已存在 |
| `docs/phases/phase-00-research-and-baseline.md` | Phase 00 执行计划与记录 | 已完成 |
| `docs/phases/phase-01-project-skeleton.md` | Phase 01 详细计划 | 待确认/未执行 |
| `docs/phases/phase-02-agent-foundation.md` 至 `phase-10-evaluation-and-production.md` | Phase 02 至 Phase 10 详细计划 | 预规划草案/未执行 |
| `docs/research/ragflow-baseline.md` | P00-T01 研究产物 | 已生成并验证 |

Phase 00 原始盘点开始时有 12 个文件，P00-T02 生成本文件后为 13 个。其后 Phase 00 产物和 Phase 01 至 Phase 10 计划使当前总数变为 25；这些变化都是文档产出，不是业务实现。

## 3. 目标差距

| 能力层 | 当前事实 | 进入实现所需前置 |
|---|---|---|
| 工程骨架 | 不存在 | Phase 00 完成、O-001 解决、Phase 01 计划确认 |
| Agent Runtime | 不存在 | Phase 01 骨架后进入 Phase 02 |
| 知识库统一接口 | 不存在 | Phase 02 后进入 Phase 03 |
| 最小 RAG | 不存在 | Phase 03 契约和 O-002/O-006/O-007 后进入 Phase 04 |
| Parser/Chunk | 不存在 | Phase 04 闭环后进入 Phase 05 |
| 在线检索 | 不存在 | Phase 04、Phase 05 后进入 Phase 06 |
| 文档生命周期 | 不存在 | Phase 05、Phase 06 后进入 Phase 07 |
| Agentic RAG | 不存在 | Phase 02、Phase 06 后进入 Phase 08 |
| 高级 RAG | 不存在 | Phase 05、Phase 06、Phase 08 后进入 Phase 09 |
| 评测与生产化 | 不存在 | Phase 07、Phase 08、Phase 09 后进入 Phase 10 |

## 4. 实际验证

2026-07-29 执行 Phase 00 原始盘点，2026-07-30 在阶段计划生成后执行增量盘点：

```powershell
Get-ChildItem -LiteralPath 'D:\download\myself' -Force
Get-ChildItem -LiteralPath 'D:\download\myself' -Recurse -File -Force
Get-FileHash -Algorithm SHA256 <each-file>
@('.git','src','tests','migrations','pyproject.toml','uv.lock','.env.example','README.md','deployments','scripts','.github') |
  ForEach-Object { Test-Path -LiteralPath (Join-Path 'D:\download\myself' $_) }
```

结果：Phase 00 原始盘点开始时 12 个文件；2026-07-30 增量盘点为 25 个文件。两次盘点均只有 Markdown/入口文档；Python、迁移、测试和部署文件均为 0；所有预期实现路径均不存在。验证通过。
