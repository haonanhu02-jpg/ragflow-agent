---
document_id: PRODUCTION-RUNBOOK
status: local-self-managed-ready
last_updated_at: "2026-08-01"
platform: Linux Docker Compose
---

# 生产候选运行手册

## 平台与责任

第一版保持模块化单体，同一不可变镜像分别运行 FastAPI 与 Ingestion Worker。Linux `amd64` 是主要验证目标；只有实际执行多架构构建后才能声明 `arm64`。数据库迁移只由 `migrate` one-shot Job 执行。职责角色为 `release_owner`、`security_approver` 和 `ops_oncall`，不得用模型或 Agent 代替审批。

UI/管理控制台不属于本路线图，当前只交付后端 API、Worker、评测与生产候选。

## 配置与启动

1. 将 `deploy/production.env.example` 复制到仓库外的 Secret 管理位置并注入真实值；不得提交含真实值的副本。TLS 证书与私钥通过仓库外路径挂载到可选 `edge` profile。
2. 为应用使用最小权限数据库账号、S3 凭据、Elasticsearch 身份和网络出口 allowlist。生产 Tool SQL 使用独立只读账号。
3. 构建后生成 SBOM，完成依赖、镜像、密钥和 provenance 审查。项目有意不设置顶层 LICENSE，镜像不声明项目 license 标签；第三方、数据集、模型和外部资源许可证记录必须保留。
4. 先运行 `migrate`，确认成功后再滚动替换 API/Worker。

```bash
docker build --build-arg VCS_REF="$(git rev-parse HEAD)" -t ragflow-agent:production-candidate .
docker compose --env-file /secure/ragflow-agent.env -f deploy/docker-compose.prod.yml config --quiet
docker compose --env-file /secure/ragflow-agent.env -f deploy/docker-compose.prod.yml run --rm migrate
docker compose --env-file /secure/ragflow-agent.env -f deploy/docker-compose.prod.yml up -d api worker otel-collector prometheus grafana
```

外部入口启用 `--profile edge`；Nginx 配置实施 TLS 1.2/1.3、请求速率限制和安全响应头。应用与观测网络默认 `internal`，远程 Provider 的网络出口由部署环境接入受控代理或 allowlist；本机模型可通过 Compose 的 `host-gateway` 映射访问。开发环境可使用受控身份头，本地或自有云若对公网开放则必须由受信任网关或身份适配器注入身份。企业 SSO/外部 IdP 是可选接入，不是当前源码完成条件。

API 必须通过 `/health/live` 和 `/health/ready`，Worker 必须单独健康。`/metrics` 由 Prometheus 抓取，Trace 使用 OTLP；观测后端故障不得阻断核心请求。

## SLO 与告警

目标：月度可用性 99.5%；readiness p95 500ms；非 LLM API p95 1s；检索 p95 2s；固定 RAG p95 20s；内部错误率低于 1%；跨租户/严重安全违规为 0。Outbox、DLQ、清理和 Memory 积压超过 5 分钟告警。短时测试只记录测试窗口，不证明月度目标。

日志和 Trace 默认保留 30 天，指标 90 天。长期记忆撤回后立即不可用并在 24 小时内物理清理。完整 Prompt、原文、SQL/API 完整响应和凭据禁止进入日志与 Trace。

## 备份、恢复与索引重建

- RPO 24 小时、RTO 4 小时，备份默认保留 30 天。
- 每日备份 PostgreSQL、MinIO/S3、配置版本和必要 Secret 元数据；备份加密与密钥分离。
- Checkpoint 和 Memory 位于 PostgreSQL 权威备份范围；搜索索引不作为唯一事实源。
- 恢复只在隔离空环境执行：PostgreSQL → 对象 → 配置/Secret 元数据 → Checkpoint/Memory 验证 → Elasticsearch 全量重建 → tenant/ACL/Citation/评测复跑。
- 不覆盖唯一备份，不在生产数据上演练。

仓库内 `ragflow_agent.operations.backup` 提供内容 hash 验证和空目录保护，用于隔离演练与 CI；生产 PostgreSQL/S3 原生命令由部署环境 Secret 和平台工具执行。

## 故障演练

隔离 GameDay 依次注入 PostgreSQL、Redis、MinIO、Elasticsearch、Worker kill、Provider timeout、网络中断、Checkpoint 故障和 DLQ 积压。每次记录发现时间、恢复时间、数据损失、告警和剩余积压。未经授权不得对外部 Provider 压测、渗透或执行写 Tool。

## 发布与回滚

发布记录必须固定应用镜像 digest、配置版本、Alembic revision 和索引版本。回滚顺序：停止新流量/任务 → 恢复上一镜像和配置 → 对可逆迁移执行批准的 downgrade → 切回上一索引 alias → 复跑安全和评测门禁。不可逆迁移若没有备份、影子字段和回退脚本，禁止发布。

当前完成结论以 [`reports/phase10/release-report.json`](../reports/phase10/release-report.json) 为准。质量、安全和隔离恢复门禁保持 fail closed；Chat/Embedding/Reranker 与基础设施 Secret 由用户在运行环境提供。Docker Scout、企业 IdP/系统接入、真实业务效果和长期 SLO 是可选外部验证，不阻止本地或自有云部署运行。

导航：[评测](./09-evaluation.md) · [工程标准](./06-engineering-standards.md) · [决策与风险](./07-decisions-and-risks.md) · [Phase 10](./phases/phase-10-evaluation-and-production.md)
