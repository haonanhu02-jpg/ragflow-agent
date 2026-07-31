---
document_id: PHASE-07-DOCUMENT-LIFECYCLE
document_role: Phase 07 已执行详细计划
status: completed
phase: Phase 07
phase_name: 文档生命周期
plan_status: 已确认
execution_status: 已完成
last_updated_at: "2026-07-31"
ragflow_frozen_baseline_commit: "cd846cc9d4e32a19e684c59a1f302601027ef976"
---

# Phase 07：文档生命周期详细计划

## 0. 状态与导航

- **计划状态**：已确认。
- **执行状态**：已完成；P07-T01 至 P07-T11 均已通过任务验证与阶段验收。
- Phase 05/06 前置产物已经复核；生命周期策略由 ADR-022 冻结，实际实现与证据见
  [文档生命周期设计与运行证据](../09-document-lifecycle.md)。
- 导航：[阶段索引](./README.md) · [Phase 06](./phase-06-online-retrieval.md) · [Phase 08](./phase-08-agentic-rag.md) · [Phase 10](./phase-10-evaluation-and-production.md)

## 1. 目标、必要性与 Phase 00 依据

实现更新、删除、重新解析、索引重建、任务进度、重试、取消、幂等、状态机、跨 PostgreSQL/对象存储/搜索的一致性补偿、残留清理和批量任务。

Phase 00 证明 RAGFlow 重解析采用原地状态/先删后建；删除先移除关系行再 best-effort 清对象/索引；Redis pending 只处理当前 consumer；receive 增加 retry_count；异常路径仍 ACK。目标不能直接沿用，必须以 DocumentVersion、候选索引、补偿和 reconciliation 自研。

## 2. 前置、输入、范围与排除

- **前置阶段**：Phase 05、Phase 06。
- **进入条件**：已满足。Parser/Chunk/Index/Citation/在线检索字段和任务后端经
  Phase 05/06 验收；版本激活/回滚、重试分类与次数、索引切换、软删除/物理
  回收期限、跨存储补偿和批量隔离规则已由 P07-T01 与 ADR-022 冻结。
- **输入**：DocumentVersion/IngestionJob 状态、Search/Object/Queue Adapter、Trace、评测和故障注入环境。

**范围**：更新/重解析/删除/重建、Embedding/Parser 版本迁移、候选索引激活、进度、可靠消息、dead-letter、取消、幂等、批量、补偿、回收/墓碑/reconciliation。

**排除**：微服务分布式事务、复杂审批、GraphRAG/RAPTOR 算法实现；但派生索引清理端口必须预留。

## 3. 交付物与目标模块

```text
src/ragflow_agent/knowledge/application/lifecycle/
  update.py reparse.py rebuild.py delete.py publish.py reconcile.py batch.py
src/ragflow_agent/worker/{retry,dead_letter,cancellation,progress}.py
tests/{unit,contract,integration,e2e,fault}/lifecycle/
docs/09-document-lifecycle.md
```

## 4. RAGFlow 源码与采用

| 源码/关系 | 采用 |
|---|---|
| `DocumentService.run/clear_chunk_num_when_rerun` | 重解析用例参考 |
| `document_api.update_document/parse_documents/delete_documents` | API 顺序参考 |
| `FileService.delete_docs` → `DocumentService.remove_document/delete_chunk_images` → DocStore/ObjectStore | 部分失败反例 |
| `TaskService.get_task/cancel_all_task_of/has_canceled` | 领取/取消用例参考 |
| `RedisDB.get_unacked_iterator/requeue_msg/RedisMsg.ack` → `task_executor.handle_task` | pending/ACK 反例 |
| `Dealer._prune_deleted_chunks` | 孤儿防御参考 |

- **直接复用**：无。
- **`ragflow_adapters` 改造复用**：无默认；仅可提取经证明纯净的清理 helper。
- **参考后自研**：生命周期 API/状态、取消、pending、清理用例。
- **明确不采用**：关系先删、异常无条件 ACK、固定三次重试、只信消息 tenant。

## 5. 框架与自研职责

- **LangGraph**：不承担 ingestion 数据面事务/恢复。
- **LangChain**：仅模型/Embedding 调用，不承担一致性。
- **自研**：版本、可靠任务、补偿、原子激活、回收、批量、审计和故障测试。

## 6. 任务总表

| 任务 | 名称 | 状态 | 前置 |
|---|---|---|---|
| P07-T01 | 复审生命周期状态与一致性模型 | 已完成 | Phase 05、06 |
| P07-T02 | 实现更新与重新解析 | 已完成 | P07-T01 |
| P07-T03 | 实现候选索引、重建与原子激活 | 已完成 | P07-T01、P07-T02 |
| P07-T04 | 实现删除、墓碑与残留清理 | 已完成 | P07-T01 |
| P07-T05 | 实现可靠重试、ACK 与死信 | 已完成 | P07-T01 |
| P07-T06 | 实现任务进度与取消 | 已完成 | P07-T02、P07-T05 |
| P07-T07 | 实现幂等与并发控制 | 已完成 | P07-T02 至 P07-T06 |
| P07-T08 | 实现补偿与 Reconciliation | 已完成 | P07-T03、P07-T04、P07-T07 |
| P07-T09 | 实现批量任务 | 已完成 | P07-T06 至 P07-T08 |
| P07-T10 | 建立故障注入和恢复验证 | 已完成 | P07-T02 至 P07-T09 |
| P07-T11 | 执行生命周期阶段验收 | 已完成 | P07-T01 至 P07-T10 |

## 7. 具体任务

### P07-T01：复审生命周期状态与一致性模型

- **状态**：已完成
- **目标**：冻结版本发布、删除可见性、任务状态、索引激活和补偿协议。
- **为什么需要**：实际 Adapter 和 Phase 06 Citation 可能改变预案。
- **输入**：Phase 05/06 验收、风险 R-005/R-018/R-022。
- **前置任务**：Phase 05、06 完成。
- **操作步骤**：盘点源码；绘制状态机/故障矩阵；确定 alias/manifest 激活；重试分类/次数/dead-letter；回收期限；修订计划。
- **涉及文件**：契约文档、ADR、本文件。
- **预期输出**：生命周期执行基线。
- **RAGFlow 源码依据**：`DocumentService`、`TaskService`、Redis/ACK 链路。
- **实现或复用方式**：参考后自研。
- **测试方法**：状态/故障表评审。
- **验证命令**：`uv run pytest tests/unit/knowledge/test_lifecycle_state.py -q`
- **验收标准**：每个跨存储步骤有失败/补偿/幂等定义。
- **风险和回滚方法**：规则不完整即不进入实现。
- **实际执行结果**：ADR-022 冻结 PostgreSQL 权威状态、Outbox、CAS 激活、候选索引、删除保留期、重试分类和批量隔离；领域状态、端口、配置与 `20260731_0004` 迁移已落地。
- **实际验证结果**：`uv run pytest tests/unit/knowledge/test_lifecycle_state.py -q` 通过（3 passed）。
- **计划偏差**：明确不采用 2PC；所有跨存储步骤使用状态机、幂等操作、补偿和对账。

### P07-T02：实现更新与重新解析

- **状态**：已完成
- **目标**：创建新 DocumentVersion 并在后台重跑 pipeline，旧版保持可用。
- **为什么需要**：配置/内容变化不能破坏当前查询。
- **输入**：P07-T01、ingestion pipeline。
- **前置任务**：P07-T01。
- **操作步骤**：update/reparse command；内容/配置 diff；新 version/job；幂等投递；旧版 current 不变；失败状态。
- **涉及文件**：`lifecycle/update.py`、`reparse.py`、API/迁移/测试。
- **预期输出**：更新/重解析服务。
- **RAGFlow 源码依据**：`update_document`、`parse_documents`、`clear_chunk_num_when_rerun`。
- **实现或复用方式**：自行开发。
- **测试方法**：内容/Parser/Chunk config 更新、失败保旧版、tenant。
- **验证命令**：`uv run pytest tests/integration/lifecycle/test_update_reparse.py -q`
- **验收标准**：失败不影响 current version；所有作业可追踪。
- **风险和回滚方法**：保留旧对象/索引直到发布成功。
- **实际执行结果**：实现 `DocumentUpdateService`、`DocumentReparseService`、不可变 `DocumentVersion`、事务 Outbox 与 Ingestion 发布集成；候选版本失败不改变当前版本。
- **实际验证结果**：`uv run pytest tests/integration/lifecycle/test_update_reparse.py -q` 通过。
- **计划偏差**：重解析复用原对象；内容更新先写对象再提交数据库，失败产生的安全孤儿由 reconciliation 发现和清理。

### P07-T03：实现候选索引、重建与原子激活

- **状态**：已完成
- **目标**：完整构建/验证新 index_version 后原子切换并可回滚。
- **为什么需要**：Embedding/Parser/Chunk 变更需要安全重建。
- **输入**：P07-T01、P07-T02、Search Adapter。
- **前置任务**：P07-T01、P07-T02。
- **操作步骤**：candidate index/manifest；完整性/计数/维度；切 alias/current manifest；旧版保留；回滚/回收。
- **涉及文件**：`lifecycle/{rebuild,publish}.py`、search Adapter、测试。
- **预期输出**：版本发布与回滚。
- **RAGFlow 源码依据**：上游先删后建作为反例。
- **实现或复用方式**：自行开发。
- **测试方法**：部分写失败、切换竞态、回滚、查询连续性。
- **验证命令**：`uv run pytest tests/integration/lifecycle/test_index_publish.py -q`
- **验收标准**：切换前验证完整；旧版始终可回退。
- **风险和回滚方法**：激活失败保持旧 manifest。
- **实际执行结果**：实现候选验证、Elasticsearch generation/alias 切换、PostgreSQL CAS 激活、旧版本退休、未知切换结果对账和显式回滚。
- **实际验证结果**：`uv run pytest tests/integration/lifecycle/test_index_publish.py -q` 通过；隔离四后端 E2E 的真实 alias 切换通过。
- **计划偏差**：同时保留按 document version 的逻辑投影与 Elasticsearch 物理 generation alias，以兼容现有最小索引和重建路径。

### P07-T04：实现删除、墓碑与残留清理

- **状态**：已完成
- **目标**：先撤销可见性，再幂等回收关系、对象、索引、派生工件和缓存。
- **为什么需要**：防止删除部分失败造成泄露/孤儿。
- **输入**：P07-T01、对象/Search/Repository。
- **前置任务**：P07-T01。
- **操作步骤**：delete command/权限；tombstone；查询立即不可见；异步 cleanup checklist；审计；保留 Citation 行为规则。
- **涉及文件**：`lifecycle/delete.py`、cleanup jobs、测试。
- **预期输出**：安全删除流程。
- **RAGFlow 源码依据**：`delete_documents` → `delete_docs/remove_document/delete_chunk_images`。
- **实现或复用方式**：参考缺口后自研。
- **测试方法**：每个清理步骤失败、重复删除、越权、引用。
- **验证命令**：`uv run pytest tests/fault/lifecycle/test_delete_cleanup.py -q`
- **验收标准**：删除后立即不可检索；残留可自动/人工修复。
- **风险和回滚方法**：物理删除前保留墓碑；误删恢复策略明确。
- **实际执行结果**：实现立即 tombstone、授权恢复、恢复时取消旧 cleanup Outbox、到期 Outbox 驱动的幂等物理回收；在线查询在候选返回后再次以 PostgreSQL 权威状态 fail-closed 过滤。
- **实际验证结果**：`uv run pytest tests/fault/lifecycle/test_delete_cleanup.py -q` 通过。
- **计划偏差**：自动化测试使用可控时钟推进 31 天验证延迟物理清理；运行默认保留期为 30 天且可配置。

### P07-T05：实现可靠重试、ACK 与死信

- **状态**：已完成
- **目标**：区分瞬时/永久/取消错误并保证 ACK 安全。
- **为什么需要**：避免任务丢失或无限重试。
- **输入**：P07-T01、Queue Adapter。
- **前置任务**：P07-T01。
- **操作步骤**：错误分类；visibility/lease；retry/backoff；attempt；dead-letter；安全 ACK；Worker crash recovery。
- **涉及文件**：`worker/{retry,dead_letter}.py`、queue Adapter、测试。
- **预期输出**：可靠消息协议。
- **RAGFlow 源码依据**：`get_task`、`get_unacked_iterator/requeue_msg`、`handle_task` ACK。
- **实现或复用方式**：参考后自研。
- **测试方法**：崩溃点、重复、lease 过期、永久错误、DLQ。
- **验证命令**：`uv run pytest tests/fault/worker/test_delivery_semantics.py -q`
- **验收标准**：安全持久化前不 ACK；最终失败可查询。
- **风险和回滚方法**：重试风暴用上限/退避/熔断。
- **实际执行结果**：实现显式 transient/permanent/cancelled 分类、指数退避与 jitter、最大尝试次数、Outbox 状态和可查询 dead-letter 记录；未知代码错误默认永久失败。
- **实际验证结果**：`uv run pytest tests/fault/worker/test_delivery_semantics.py -q` 通过。
- **计划偏差**：ARQ 不暴露独立 ACK lease API；可靠边界由 ARQ 持久任务与 PostgreSQL Outbox 组合提供，跨租户生产调度/告警仍登记为 R-033。

### P07-T06：实现任务进度与取消

- **状态**：已完成
- **目标**：提供单调/阶段化进度、取消请求、取消确认和审计。
- **为什么需要**：长 Parser/Embedding/重建需要用户控制。
- **输入**：P07-T02、P07-T05。
- **前置任务**：P07-T02、P07-T05。
- **操作步骤**：progress event；CancellationToken/checkpoint；停止领取/写入前终态检查；API 查询/取消；重复取消。
- **涉及文件**：`worker/{progress,cancellation}.py`、API、测试。
- **预期输出**：进度/取消闭环。
- **RAGFlow 源码依据**：`do_cancel/has_canceled/cancel_all_task_of`。
- **实现或复用方式**：参考后自研。
- **测试方法**：各阶段取消、取消与激活竞态、重复提交。
- **验证命令**：`uv run pytest tests/integration/lifecycle/test_progress_cancel.py -q`
- **验收标准**：取消后不激活新版本；状态可解释。
- **风险和回滚方法**：不可中断外部调用后再次检查终态。
- **实际执行结果**：生命周期操作提供单调阶段进度、查询/取消 API；Ingestion 在阶段边界和发布前协作检查取消，并持久化取消终态。
- **实际验证结果**：`uv run pytest tests/integration/lifecycle/test_progress_cancel.py -q` 通过。
- **计划偏差**：取消是协作式取消，不对正在执行的第三方调用做不安全硬终止。

### P07-T07：实现幂等与并发控制

- **状态**：已完成
- **目标**：处理重复请求/消息、并发更新/删除/重建和 Worker 抢占。
- **为什么需要**：至少一次投递会重复。
- **输入**：P07-T02 至 P07-T06。
- **前置任务**：P07-T02 至 P07-T06。
- **操作步骤**：idempotency key；状态 compare-and-set；aggregate lock/lease；稳定 Chunk/Index ID；冲突错误。
- **涉及文件**：lifecycle/worker/Repository、测试。
- **预期输出**：并发与幂等控制。
- **RAGFlow 源码依据**：Task retry_count/pending 行为只作问题证据。
- **实现或复用方式**：自行开发。
- **测试方法**：并发相同/不同命令、重复投递、锁失效。
- **验证命令**：`uv run pytest tests/fault/lifecycle/test_idempotency_concurrency.py -q`
- **验收标准**：无重复 Chunk/激活；冲突可重试/审计。
- **风险和回滚方法**：锁不是唯一保障，数据库状态比较兜底。
- **实际执行结果**：命令指纹、稳定操作/Outbox/索引 generation 标识、唯一约束、版本激活 CAS 与 Elasticsearch fencing 共同阻止幂等键碰撞、重复发布和陈旧写入；历史结果返回前重验操作者与权限。
- **实际验证结果**：`uv run pytest tests/fault/lifecycle/test_idempotency_concurrency.py -q` 通过。
- **计划偏差**：未引入分布式锁；数据库 CAS 是最终并发兜底。

### P07-T08：实现补偿与 Reconciliation

- **状态**：已完成
- **目标**：发现并修复数据库、对象和索引不一致。
- **为什么需要**：跨系统没有原子事务。
- **输入**：P07-T03、P07-T04、P07-T07。
- **前置任务**：P07-T03、P07-T04、P07-T07。
- **操作步骤**：outbox/补偿日志（按实际决策）；完整性扫描；孤儿/缺失分类；安全修复；dry-run/审计。
- **涉及文件**：`lifecycle/reconcile.py`、迁移、CLI/job、测试。
- **预期输出**：补偿与对账工具。
- **RAGFlow 源码依据**：关系先删/后续 best-effort 和 `_prune_deleted_chunks`。
- **实现或复用方式**：参考缺口后自研。
- **测试方法**：构造每类不一致、dry-run、重复修复。
- **验证命令**：`uv run pytest tests/fault/lifecycle/test_reconcile.py -q`
- **验收标准**：修复幂等、tenant-scoped、可审计。
- **风险和回滚方法**：默认 dry-run；破坏性修复需显式批准。
- **实际执行结果**：实现 tenant-scoped、有界、默认 dry-run 的对账，识别 stale operation/outbox、索引漂移、孤儿对象/投影和到期墓碑；只自动修复可证明安全的孤儿。
- **实际验证结果**：`uv run pytest tests/fault/lifecycle/test_reconcile.py -q` 通过。
- **计划偏差**：不确定或破坏性差异只报告不自动修复，生产级跨租户定时调度和告警留 R-033。

### P07-T09：实现批量任务

- **状态**：已完成
- **目标**：支持 tenant-scoped 批量重解析、重建和删除及限流。
- **为什么需要**：模型/Parser 升级会影响大量文档。
- **输入**：P07-T06 至 P07-T08。
- **前置任务**：P07-T06 至 P07-T08。
- **操作步骤**：batch aggregate/child jobs；分页选择；并发/背压；进度汇总；部分失败/取消/恢复。
- **涉及文件**：`lifecycle/batch.py`、API/CLI、测试。
- **预期输出**：批量任务能力。
- **RAGFlow 源码依据**：Task splitting 只作分片用例。
- **实现或复用方式**：自行开发。
- **测试方法**：大批次、部分失败、租户边界、恢复。
- **验证命令**：`uv run pytest tests/integration/lifecycle/test_batch.py -q`
- **验收标准**：子任务可独立重试；汇总准确；背压有效。
- **风险和回滚方法**：默认低并发；支持暂停/取消。
- **实际执行结果**：实现 tenant/knowledge-base 作用域批次、子操作汇总、部分失败/取消状态和默认并发上限 3；提供创建和查询 API。
- **实际验证结果**：`uv run pytest tests/integration/lifecycle/test_batch.py -q` 通过。
- **计划偏差**：当前批次聚合既有生命周期操作；批次 API 不直接为文档选择集创建新的子命令，编排式批量创建留后续增强。

### P07-T10：建立故障注入和恢复验证

- **状态**：已完成
- **目标**：证明每个关键阶段的崩溃、超时和部分失败可恢复。
- **为什么需要**：可靠性不能只靠正常路径。
- **输入**：P07-T02 至 P07-T09。
- **前置任务**：P07-T02 至 P07-T09。
- **操作步骤**：故障点矩阵；kill Worker；对象/Search/DB/Queue 错误；恢复/重投/对账；记录 RTO/残留。
- **涉及文件**：`tests/fault/lifecycle/`、报告。
- **预期输出**：恢复证据。
- **RAGFlow 源码依据**：不新增事实。
- **实现或复用方式**：自行开发测试。
- **测试方法**：自动故障注入和重复运行。
- **验证命令**：`uv run pytest tests/fault/lifecycle -q`
- **验收标准**：旧版可用、无越权/重复、残留可修。
- **风险和回滚方法**：隔离测试环境，禁止生产数据。
- **实际执行结果**：建立删除部分失败、重复/并发、投递语义、对账修复及真实 PostgreSQL/Redis/MinIO/Elasticsearch 生命周期链路验证。
- **实际验证结果**：Phase 07 聚焦套件 `17 passed`；隔离四后端生命周期 E2E `1 passed`，既有真实后端回归 `11 passed`。
- **计划偏差**：验证覆盖确定性故障点和短时恢复，未进行长时间 Worker kill/网络分区混沌测试，登记为 R-034。

### P07-T11：执行生命周期阶段验收

- **状态**：已完成
- **目标**：完成 CAP-24/25/26 和 CAP-38 可靠化验收。
- **为什么需要**：Phase 10 生产门禁的硬依赖。
- **输入**：P07-T01 至 P07-T10。
- **前置任务**：P07-T01 至 P07-T10。
- **操作步骤**：运行全套测试；检查迁移/回滚/审计；更新文档/矩阵/风险；形成运行手册。
- **涉及文件**：总体文档、`docs/09-document-lifecycle.md`、本文件。
- **预期输出**：Phase 07 出口报告。
- **RAGFlow 源码依据**：核对未复制不可靠 ACK/删除顺序。
- **实现或复用方式**：审计。
- **测试方法**：Unit/Contract/Integration/E2E/Fault/Security。
- **验证命令**：`uv run pytest tests/**/lifecycle tests/fault/worker -q`
- **验收标准**：更新/删除/重建/取消/重试/幂等/批量全部通过。
- **风险和回滚方法**：严重一致性缺陷阻止阶段完成。
- **实际执行结果**：CAP-24、CAP-25、CAP-26 和 CAP-38 的 Phase 07 范围已实现；迁移、API/Worker、文档、能力矩阵和风险记录同步完成。
- **实际验证结果**：隔离四后端全套 `221 passed, 1 skipped`；无外部服务套件 `206 passed, 16 skipped`；Ruff、严格 mypy、锁文件、包导入、API/Worker bootstrap、Alembic 升降级和敏感信息检查均通过。实现提交 `71f15d5` 已推送，其 [GitHub Actions 运行](https://github.com/haonanhu02-jpg/ragflow-agent/actions/runs/30634884467) 成功。
- **计划偏差**：本机唯一跳过项为未安装 Tesseract 的既有 OCR 运行时测试，与生命周期无关；真实长期调度和混沌验证未冒充完成。

## 8. 验收、DoD、风险与后续

**DoD**：P07-T01 至 P07-T11 全部完成；版本发布/回滚、删除、可靠消息、取消/进度、幂等、批量、补偿/对账和故障恢复有证据；旧版本在失败时可用；总文档同步。

| 风险 | 处理 |
|---|---|
| 跨存储竞态 | candidate version + compensation + reconciliation |
| 取消后继续写 | 写入/激活前重复终态检查 |
| DLQ 积压 | 指标、告警、可重放和责任人 |
| 过早回收旧版 | 保留窗口和 Citation/运行引用检查 |
| 批量压垮依赖 | 背压、配额、暂停/恢复 |

阶段结束更新总纲、矩阵、架构、路线图、标准、风险、阶段索引和本文件。Phase 10 才能完成生产化；Phase 08 算法上不硬依赖本阶段，但任何生产发布必须依赖。

## 9. 实际执行结果

- **实际消息/索引/回收策略**：PostgreSQL 是权威状态；事务 Outbox 驱动 ARQ 投递；候选 generation 验证后切 Elasticsearch alias，再以数据库 CAS 发布当前版本；删除先 tombstone，默认 30 天后幂等回收。
- **实际故障注入/恢复证据**：聚焦生命周期/Worker 套件 17 项通过，真实 PostgreSQL/Redis/MinIO/Elasticsearch 生命周期 E2E 通过；完整隔离后端套件 221 项通过、1 项仅因本机无 Tesseract 跳过。
- **远程验证证据**：实现提交 `71f15d5` 已推送到 `origin/main`，[GitHub Actions 运行 `30634884467`](https://github.com/haonanhu02-jpg/ragflow-agent/actions/runs/30634884467) 成功。
- **计划偏差/新增 ADR**：新增 ADR-022；不采用 2PC/分布式锁/RAGFlow 源码，生产调度告警与长时混沌分别登记 R-033、R-034。
- **阶段出口结论**：Phase 07 的代码、测试和文档验收完成；可以进入 Phase 08 计划复审，不自动执行 Phase 08。
