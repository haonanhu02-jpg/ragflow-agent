---
document_id: DOCUMENT-LIFECYCLE
status: active
last_updated_at: "2026-07-31"
phase: Phase 07
---

# 文档生命周期与跨存储一致性

## 1. 定位与事实边界

本文是 Phase 07 已实现生命周期行为的专项事实文档。总览见[项目总纲](./00-project-master.md)，阶段证据见[Phase 07 计划](./phases/phase-07-document-lifecycle.md)，架构决策见 [ADR-022](./07-decisions-and-risks.md#adr-022phase-07-文档生命周期与跨存储一致性基线)。

- PostgreSQL 是文档状态、活动版本、操作、Outbox 和批次的权威数据源。
- MinIO 保存原始文件，Elasticsearch 是可重建检索投影，Redis/ARQ 只传递任务。
- 未使用分布式事务或 2PC；采用事务 Outbox、幂等任务、步骤状态、CAS/fencing、有限重试、补偿和对账。
- RAGFlow 源码直接复用与改造复用均为零；实现为独立开发。
- 真实 DeepSeek、BGE-M3 和 BGE Reranker 尚未验证，本阶段真实测试使用确定性 Embedding，不代表真实模型验证。

## 2. 领域状态

### 2.1 Document

| 状态 | 可检索 | 允许激活 | 说明 |
|---|---:|---:|---|
| `active` | 是，仅 `current_version_id` | 是 | 正常状态 |
| `delete_pending` | 否 | 否 | 已写删除意图，等待保留期和物理回收 |
| `deleted` | 否 | 否 | 物理清理完成，仅保留最小墓碑 |

`Document.revision` 是乐观锁和 fencing 的权威版本；所有活动版本切换使用 `DocumentRepository.save_if_revision()`。

### 2.2 DocumentVersion

```text
registered -> ingesting -> ready -> superseded -> ready (rollback)
                    |          |          |
                    +-> failed +----------+-> deleted
```

- 内容版本不可变；更新和重解析都创建新的 `version_id`。
- `index_version_id` 绑定检索投影；`activated_at`、`retired_at` 和 `purge_after` 记录发布与保留窗口。
- 同一逻辑文档最多一个 PostgreSQL `current_version_id`。
- 更新、删除、恢复、回滚和批次在返回幂等历史结果前，都会重新验证 tenant、文档写权限、操作类型和命令指纹；相同幂等键对应不同文档、载荷或操作者时返回冲突。

### 2.3 LifecycleOperation

状态为 `pending`、`running`、`waiting_retry`、`cancel_requested`、`cancelled`、`succeeded`、`failed`、`dead_letter`。操作记录包含 `operation_id`、tenant/KB/document/version、幂等键、步骤、attempt、revision、fencing token、操作者、原因、request ID 和结构化错误。

## 3. 更新、重解析、激活与回滚

1. `DocumentUpdateService.update/reparse` 保持旧活动版本不变，创建新 `DocumentVersion`、`LifecycleOperation`、`IngestionJob/Task` 和 `LifecycleOutboxEvent`。
2. 内容更新先写 tenant 命名空间对象；重解析复用历史原始对象，不重新上传。
3. `LifecycleOutboxDispatcher.dispatch_due` 将 `ingestion.requested` 发布到 Redis/ARQ；重复事件由确定性 message/job ID 和 Outbox 状态消除副作用。
4. `IngestionPipeline.handle` 解析、切块、Embedding、写入候选投影，并在各不可逆边界前检查取消状态。
5. `DocumentVersionPublisher.complete_ingestion` 先验证候选 chunk，再以 fencing token 提升投影，然后在 PostgreSQL 中 CAS 切换活动版本并退役旧版。
6. 若投影提升后数据库 CAS 失败，最终查询仍以 PostgreSQL 活动版本过滤候选，旧版本继续服务；对账可发现未完成操作。
7. `rollback` 只接受仍保留且健康的 `superseded` 版本，使用同一发布/CAS 链路并保留审计操作。

关键实现：

- `src/ragflow_agent/knowledge/application/lifecycle/update.py`
- `src/ragflow_agent/knowledge/application/lifecycle/publish.py`
- `src/ragflow_agent/knowledge/application/ingestion.py`
- `src/ragflow_agent/knowledge/infrastructure/search/elasticsearch.py`

## 4. 删除、恢复与物理回收

`DocumentDeletionService.request_delete` 在同一 PostgreSQL 事务中写 `delete_pending`、清空 `current_version_id`、递增 revision、登记操作和延迟 cleanup Outbox。事务提交后再 best-effort 退役 Elasticsearch 投影，因此外部清理失败也不会恢复可见性。

- 默认软删除 30 天；保留期内 `restore` 验证历史投影健康后通过 CAS 恢复，并在同一数据库事务取消旧的延迟 cleanup Outbox。
- 保留期到期后，`LifecycleOutboxDispatcher` 调用只处理已到期墓碑的 `purge_due`；它删除该文档所有 Elasticsearch 版本，按对象键去重清理 MinIO，并将版本和文档置为 `deleted`。
- 相同命令的重复删除、重复 Outbox、重复物理回收均为幂等结果；恢复会取消旧 cleanup 事件，避免恢复后的文档被历史定时事件回收。
- 对真实用户或非隔离数据的立即不可逆清理仍属于破坏性操作，必须另行授权。

## 5. 全量索引重建

`IndexRebuildService` 与 `LifecycleSearchPort` 实现 generation 物理索引：

1. 创建不可见 staging 索引。
2. 写入 tenant/KB 范围内的记录。
3. 验证 mapping、数量、生命周期字段、范围、抽样查询和 checksum。
4. 使用 Elasticsearch 原子 aliases 操作切换稳定读写别名。
5. 返回结果不明确时读取 alias 实际状态；未切换则删除 staging，已切换则按实际状态收敛。
6. 回滚先验证目标 generation 健康；当前 alias 指向的物理索引不得删除。

上一健康物理索引默认保留 7 天；到期清理由后续维护任务处理。

## 6. 重试、取消、死信与进度

- 自动重试：超时/连接故障、408/409/425/429/5xx、显式并发冲突。
- 不自动重试：权限、参数、格式/内容、确定性业务冲突、其他 4xx、代码错误和未知失败。
- 默认总尝试 6 次；并发冲突最多 3 次；指数退避、全抖动、`Retry-After` 和 300 秒上限均可配置。
- 重试耗尽进入持久 `dead_letter`，保留分类、步骤、attempt 和最后错误。
- 取消是协作式的；已激活成功项不回滚，未激活任务在解析、切块、Embedding、索引和激活边界检查 `cancel_requested`。
- 进度单调，不能回退；批次状态从子操作真实终态重新计算。

## 7. 对账与批量隔离

`LifecycleReconciler.run` 默认 dry-run、tenant-scoped、有限批次，检测：

- 长时间 `pending/running/waiting_retry/cancel_requested` 操作；
- 到期未投递 Outbox；
- 候选投影或源对象缺失；
- 无权威版本引用的孤儿对象和孤儿投影；
- 到期未完成的物理回收。

显式非 dry-run 时只自动执行可证明安全且幂等的孤儿对象/投影删除；不确定状态只报告，不猜测修复。

`LifecycleBatchService` 强制单 tenant、单知识库，限制并发，允许 `succeeded`、`partial_success`、`failed`、`cancelled`，单文档失败不回滚其他成功项。全量 generation 构建必须全部验证通过才切 alias。

## 8. API、Worker 与迁移

- API：文档更新、重解析、删除、恢复、版本回滚、操作查询/取消、批次创建/查询。
- Worker：`process_ingestion`、`dispatch_lifecycle_outbox`、`reconcile_lifecycle`；API 提交后还会 best-effort 触发本 tenant Outbox 投递，失败事件仍留在 PostgreSQL。
- 数据库迁移：`migrations/versions/20260731_0004_phase07_document_lifecycle.py`；业务迁移由 Alembic 管理，与 LangGraph Checkpoint `AsyncPostgresSaver.setup()` 完全分离。

## 9. RAGFlow 源码依据与采用边界

冻结基线：`cd846cc9d4e32a19e684c59a1f302601027ef976`。

| 事实 | RAGFlow 路径/符号 | 本项目处理 |
|---|---|---|
| 更新/重解析入口 | `api/apps/restful_apis/document_api.py::update_document/parse_documents` | 参考用例，自研不可变版本 |
| 清重解析状态 | `api/db/services/document_service.py::DocumentService.clear_chunk_num_when_rerun/run` | 不采用原地先删后建 |
| 删除与对象清理 | `document_api.py::delete_documents`；`DocumentService.remove_document/delete_chunk_images` | 作为部分失败反例，自研 tombstone/补偿 |
| 取消 | `api/db/services/task_service.py::cancel_all_task_of/has_canceled` | 参考协作式取消 |
| Redis pending/requeue | `rag/utils/redis_conn.py::get_unacked_iterator/requeue_msg` | 参考后自研 Outbox/ARQ |
| Worker ACK | `rag/svr/task_executor.py::handle_task` | 不采用异常后无条件 ACK |
| 删除结果防御 | `rag/nlp/search.py::Dealer._prune_deleted_chunks` | 强化为每次返回前 PostgreSQL 权威校验 |

## 10. 验证证据与限制

- 默认无外部服务：`206 passed, 16 skipped`。
- 隔离 PostgreSQL/Redis/MinIO/Elasticsearch 全仓：`221 passed, 1 skipped`；唯一 skip 为本机没有 Tesseract，与 Phase 07 无关。
- Phase 07 专项：17 项确定性状态、故障、幂等、权限、批次和对账测试。
- 真实生命周期 E2E：1 项，通过更新、Outbox、发布、唯一活动版本、generation alias、删除不可见和物理回收。
- 前序真实后端回归：11 项通过。
- Alembic `0003 -> 0004 -> 0003 -> 0004` 往返通过。

仍未完成：跨进程高并发压测、长时间 Worker kill/lease 混沌、真实 DeepSeek/BGE 模型、复杂 RBAC、生产告警后端、自动跨 tenant 调度器、GraphRAG/RAPTOR 派生索引清理实现。这些不得描述为当前生产能力。
