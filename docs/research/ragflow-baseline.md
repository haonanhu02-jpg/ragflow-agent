---
document_id: RAGFLOW-BASELINE
status: active
last_updated_at: "2026-07-30"
ragflow_frozen_baseline_commit: "cd846cc9d4e32a19e684c59a1f302601027ef976"
ragflow_tracking_ref: main
ragflow_tracking_last_observed_commit: "0cb4039be9c0691f89c391c5cc28ab40682a8163"
ragflow_tracking_last_observed_at: "2026-07-29"
---

# RAGFlow 双基线与本地快照核验

## 文档导航

[项目总纲](../00-project-master.md) · [RAGFlow 架构](../01-ragflow-architecture.md) · [决策与风险](../07-decisions-and-risks.md) · [Phase 00 计划](../phases/phase-00-research-and-baseline.md)

## 1. 核验结论

| 项目 | 实际结果 | 证据角色 |
|---|---|---|
| 上游仓库 | `https://github.com/infiniflow/ragflow.git` | 唯一上游来源 |
| 冻结事实基线 | `cd846cc9d4e32a19e684c59a1f302601027ef976` | 长期源码结论和固定链接依据 |
| 冻结提交时间/标题 | `2026-07-27T15:20:09+08:00`；`Enhance: localhost:9385 -> sandbox-executor-manager:9385 (#17414)` | commit 身份验证 |
| 滚动跟踪基线 | `main`=`0cb4039be9c0691f89c391c5cc28ab40682a8163` | 2026-07-30 变化观察，不自动改变冻结事实 |
| 滚动提交时间/标题 | `2026-07-29T21:10:19+08:00`；`fix(ingestion): clamp unconfigured embedding limit; document chunker title parity (comment-only) (#17539)` | 本次观察证据 |
| 冻结/滚动版本 | `pyproject.toml` 均为 `0.26.4`，Python 均为 `>=3.13,<3.14` | 版本与运行要求 |
| 主许可证 | 根 `LICENSE` 为 Apache License 2.0；冻结与滚动 blob 相同 | RAGFlow 主许可证；不覆盖第三方依赖、模型和数据 |
| 根 NOTICE | 冻结与滚动根目录均未发现 `NOTICE` | 分发时仍须复核上游及依赖的 NOTICE/归属要求 |
| 本地辅助快照 | `D:/ragflow/ragflow-main`，无 `.git`，版本标识 `0.26.4` | 只能辅助搜索，不能证明 commit |

冻结 commit 仍可由 Git 读取且 ADR-005 未被替代，因此本次不升级冻结基线。滚动 `main` 的变化进入漂移登记，后续结论仍以冻结 commit 为主。

## 2. 冻结基线到滚动 main 的相关差异

Phase 00 在 2026-07-29、滚动提交 `3c59b707c28f7d0ed2fb62135c661e7633537a1a` 上执行的原始差异审计，在 `pyproject.toml`、`LICENSE`、`api/`、`agent/`、`common/`、`deepdoc/`、`rag/`、`test/benchmark/` 和 `docker/launch_backend_service.sh` 范围内得到 63 个变更路径。该数字是历史验收快照，不应被解释为当前 `main` 的实时差异计数。

2026-07-30 追加检查表明，当前 `main@0cb4039be9c0691f89c391c5cc28ab40682a8163` 的该次提交只修改：

- `internal/ingestion/component/chunker/title.go`
- `internal/ingestion/component/tokenizer.go`
- `internal/ingestion/component/tokenizer_unit_test.go`

它属于 Go ingestion 范围，本项目明确不分析或复现 Go，因此没有改变 Phase 01 至 Phase 10 的 Python 计划边界；冻结事实基线不升级。

与本项目直接相关的变化包括：

- `api/db/db_models.py`、`api/db/services/dialog_service.py`、`api/db/services/knowledgebase_service.py` 已变化。
- `api/apps/restful_apis/document_api.py`、`chat_api.py`、`chunk_api.py`、`dataset_api.py`、`agent_api.py` 已变化。
- `rag/nlp/search.py`、多项 `rag/app/*.py`、`rag/llm/*.py` 已变化。
- `deepdoc/parser/json_parser.py`、`markdown_parser.py`、`mistral_parser.py` 已变化。
- `docker/launch_backend_service.sh` 和 `pyproject.toml` 已变化，但项目版本号仍是 `0.26.4`。
- `api/apps/llm_app.py` 已从滚动 `main` 删除。

抽样 blob 对比显示冻结与滚动 `main` 仍相同的关键文件包括：

- `common/settings.py`
- `api/db/services/document_service.py`
- `api/db/services/task_service.py`
- `rag/svr/task_executor.py`
- `rag/svr/task_executor_refactor/task_handler.py`
- `agent/tools/retrieval.py`
- `rag/advanced_rag/agentic_rag_graph.py`

因此滚动变化需要逐能力复核，但没有证据要求立即替换冻结基线。

## 3. 本地快照 blob 对比

| 文件 | 本地=冻结 | 本地=滚动 main | 冻结=滚动 main | 处理 |
|---|---:|---:|---:|---|
| `pyproject.toml` | 否 | 否 | 否 | 本地仅辅助；版本字段相同不代表文件相同 |
| `LICENSE` | 是 | 是 | 是 | 可辅助阅读 |
| `AGENTS.md` | 否 | 否 | 是 | 本地内容不得作为固定上游事实 |
| `api/db/db_models.py` | 否 | 否 | 否 | 只从冻结 Git 对象取证 |
| `api/db/services/document_service.py` | 否 | 否 | 是 | 只从冻结 Git 对象取证 |
| `api/db/services/task_service.py` | 否 | 否 | 是 | 只从冻结 Git 对象取证 |
| `api/db/services/dialog_service.py` | 是 | 否 | 否 | 本地可辅助冻结基线搜索 |
| `common/settings.py` | 是 | 是 | 是 | 本地可辅助搜索 |
| `rag/svr/task_executor.py` | 否 | 否 | 是 | 只从冻结 Git 对象取证 |
| `rag/svr/task_executor_refactor/task_handler.py` | 否 | 否 | 是 | 只从冻结 Git 对象取证 |
| `rag/nlp/search.py` | 否 | 否 | 否 | 只从冻结 Git 对象取证 |
| `agent/tools/retrieval.py` | 是 | 是 | 是 | 本地可辅助搜索 |
| `rag/advanced_rag/agentic_rag_graph.py` | 是 | 是 | 是 | 本地可辅助搜索 |

## 4. 后续取证规则

1. 长期结论必须引用冻结 commit、源码路径、类/函数和调用关系。
2. 本地文件与冻结 blob 不同时，必须通过审计 Git 仓库的 `git show frozen:<path>` 读取冻结内容。
3. 滚动 `main` 只记录与已采用能力相关的新增、删除、重命名或行为变化。
4. 升级冻结基线必须新建或更新 ADR，并重新执行能力、复用和许可证审计。
5. RAGFlow 根 Apache-2.0 不代表 Python 包、模型权重、OCR/Vision/ASR 资源、字体和测试数据已经完成许可审计。

## 5. 实际验证

2026-07-29 实际执行：

```powershell
git fetch --filter=blob:none --no-tags --depth=1 origin cd846cc9d4e32a19e684c59a1f302601027ef976
git fetch --filter=blob:none --no-tags --depth=1 origin refs/heads/main
git rev-parse frozen
git rev-parse tracking-main
git cat-file -t frozen
git cat-file -t tracking-main
git show frozen:pyproject.toml
git diff --name-status frozen tracking-main -- pyproject.toml LICENSE api agent common deepdoc rag test/benchmark docker/launch_backend_service.sh
git hash-object -- D:\ragflow\ragflow-main\<path>
```

结果：两个引用均解析为 commit；冻结 commit 精确匹配已接受基线；滚动 `main` 已更新；本地无 Git 元数据；关键文件对比和差异统计已记录。验证通过。
