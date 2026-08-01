---
document_id: EVALUATION-AND-RELEASE-GATES
status: active
last_updated_at: "2026-08-01"
---

# 评测与发布门禁

## 事实边界

评测数据位于 [`datasets/phase09/v1`](../datasets/phase09/v1/manifest.json) 和 [`datasets/phase10/v1`](../datasets/phase10/v1/manifest.json)。两套数据均为项目自建的 CC0 合成轨道交通场景，不含企业或用户数据；manifest 固定 Schema、来源、许可、split 和每个文件的 SHA-256。

当前机器报告只代表确定性 Fake/Stub、纯算法和隔离本地基础设施结果。尚未运行真实 DeepSeek、BGE-M3、BGE Reranker、Vision 或 ASR，因此不得把当前分数解释为真实模型质量。

## 指标

- 检索：`Precision@K`、`Recall@K`、MRR、NDCG、tenant/ACL 违规和延迟。
- 答案：事实正确性、忠实度、拒答正确性、Citation precision/recall。
- Agent：路径/Tool/参数/终止状态、HITL、Budget、故障和 Trace 关联。
- 高级能力：关键词、问题、摘要、TOC、父子 Chunk、多模态、GraphRAG、RAPTOR、时序分别记录质量、Provider call、Token、主动运行时间、安全违规和 go/no-go。

安全、权限、Citation 和恢复是硬门禁，不能被平均分掩盖。`tests/unit/evaluation/test_dataset_and_gate.py` 包含故意退化样本，证明门禁会失败。

## 可重复命令

```powershell
uv run python -m ragflow_agent.evaluation.dataset datasets/phase10/v1/manifest.json
uv run python -m ragflow_agent.knowledge.advanced.evaluation --dataset datasets/phase09/v1/manifest.json --output reports/phase09/advanced-evaluation.json
uv run python -m ragflow_agent.evaluation.runner --dataset datasets/phase10/v1/manifest.json --output reports/phase10/evaluation.json
uv run pytest tests/unit/evaluation tests/evaluation -q
```

## 发布阈值

确定性回归要求 `Recall@10 >= 0.90`、answer faithfulness `>= 0.90`、Citation recall `>= 0.95`、内部错误率 `< 1%`，且跨 tenant、严重安全和恢复失败全部为 0。生产发布还必须获得真实 Provider、小规模业务数据、生产凭据/网络、隔离恢复和持续运营证据；这些门禁当前不可由 Fake 报告替代。

导航：[项目总纲](./00-project-master.md) · [决策与风险](./07-decisions-and-risks.md) · [生产运行手册](./10-production-runbook.md) · [Phase 09](./phases/phase-09-advanced-rag.md) · [Phase 10](./phases/phase-10-evaluation-and-production.md)
