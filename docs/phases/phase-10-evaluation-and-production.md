---
document_id: PHASE-10-EVALUATION-AND-PRODUCTION
document_role: Phase 10 计划与执行记录
status: completed
phase: Phase 10
phase_name: 评测与生产化
plan_status: 已批准
execution_status: 已完成
last_updated_at: "2026-08-01"
ragflow_frozen_baseline_commit: "cd846cc9d4e32a19e684c59a1f302601027ef976"
---

# Phase 10：评测与生产化详细计划

## 0. 状态与导航

- **计划状态**：已批准并冻结（ADR-025）。
- **执行状态**：已完成；ADR-026 校正后出口为 `local_or_self_managed_ready`。
- 本阶段按当前代码、Phase 09 产物和生产候选环境执行；未运行的真实 Provider、真实业务数据和持续 SLO 不得由 Fake 或短时测试替代。
- 导航：[阶段索引](./README.md) · [Phase 09](./phase-09-advanced-rag.md) · [路线图](../05-development-roadmap.md) · [工程标准](../06-engineering-standards.md)

## 1. 目标、必要性与 Phase 00 依据

建立版本化检索/答案/引用/Agent/高级 RAG 评测、回归门禁、可观测性、安全/权限、性能容量、Docker 生产部署、配置、备份恢复、故障演练、发布和回滚，使系统可发布、可诊断、可恢复。

Phase 00 确认 RAGFlow `test/benchmark` 主要统计延迟/QPS，不提供完整 Recall/MRR/NDCG/忠实度/引用/Agent 成功率；token sink、Langfuse/OTel/Jaeger 只是部分接入点；Docker/Helm 是产品部署参考，不应直接复制。

## 2. 前置、输入、范围和排除

- **前置阶段**：Phase 07、Phase 08、Phase 09。
- **进入条件**：生命周期、Agentic 和高级能力均有稳定产物；生产平台、观测后端、SLO、RPO/RTO、安全基线和发布责任人确认；本计划重审。
- **输入**：各阶段测试/Trace/指标/数据集/风险；生产环境和合规需求；API/Worker 制品。

**范围**：检索、答案、引用、Agent、数据集、回归、日志/Trace/指标/告警、tenant/ACL、安全、性能/并发/容量/成本、Docker、配置、备份恢复、故障演练、发布回滚。

**排除**：第一版拆微服务、未经确认 UI、自动实现复杂 RBAC/部门/动态规则、未通过 Phase 09 的高级能力默认启用、把压测当质量评测。

## 3. 交付物和目标模块

```text
evaluation/{datasets,retrieval,answers,citations,agent,advanced,reports}/
src/ragflow_agent/observability/
tests/{regression,security,performance,capacity,disaster_recovery}/
deploy/{docker,config,runbooks}/
docs/{09-evaluation-and-observability,10-production-runbook}.md
```

## 4. RAGFlow 源码与采用

| 源码/能力 | 采用 |
|---|---|
| `test/benchmark/dataset.py`、`metrics.py::summarize`、`report.py` | 性能采样/报告格式参考 |
| `common/token_utils.py::token_usage_sink`、LLMBundle/Langfuse、Dealer `trace_id` | 观测事件用例参考 |
| `docker/launch_backend_service.sh::run_server/task_exe`、compose、Helm | API/Worker 拓扑参考重写 |
| `common/settings.py::init_settings`、`api/ragflow_server.py` | 初始化/健康反例 |
| `KnowledgebaseService.accessible`、`Dealer.retrieval/index_name` | 权限生产负向用例 |
| `RedisDB.queue_info` | 队列指标参考 |

- **直接复用**：无。
- **`ragflow_adapters` 改造复用**：本阶段默认无；只可复用已批准的纯指标 helper。
- **参考后自研**：benchmark 报告、部署拓扑和观测字段。
- **明确不采用**：RAGFlow 全量 compose/Helm 直接作为本项目生产方案、仅 QPS 评测、全局 settings。

## 5. 框架与自研职责

- **LangGraph**：图事件、恢复、Agent 指标。
- **LangChain**：模型 callbacks/usage、评测组件 Adapter。
- **自研**：数据集、指标/门禁、统一 Trace/metric、SLO、安全、部署、备份恢复、容量、成本和运行手册。

## 6. 任务总表

| 任务 | 名称 | 状态 | 前置 |
|---|---|---|---|
| P10-T01 | 复审生产目标、SLO、RPO/RTO 与发布门禁 | 完成 | Phase 07、08、09 |
| P10-T02 | 建立版本化评测数据集 | 完成 | P10-T01 |
| P10-T03 | 建立检索评测 | 完成 | P10-T02 |
| P10-T04 | 建立答案与引用评测 | 完成 | P10-T02、P10-T03 |
| P10-T05 | 建立 Agent 与高级能力评测 | 完成 | P10-T02、P10-T04 |
| P10-T06 | 建立回归和发布质量门禁 | 完成 | P10-T03 至 P10-T05 |
| P10-T07 | 完善日志、Trace、指标和告警 | 完成 | P10-T01 |
| P10-T08 | 完成多租户、ACL 与安全门禁 | 完成 | P10-T01、P10-T07 |
| P10-T09 | 执行性能、并发、容量与成本测试 | 完成 | P10-T06、P10-T07 |
| P10-T10 | 建立 Docker 生产部署与配置管理 | 完成 | P10-T01、P10-T07 |
| P10-T11 | 实现备份、恢复与迁移验证 | 完成 | P10-T10 |
| P10-T12 | 执行故障演练、发布与回滚 | 完成 | P10-T08 至 P10-T11 |
| P10-T13 | 执行最终生产出口审查 | 完成 | P10-T01 至 P10-T12 |

## 7. 具体任务

### P10-T01：复审生产目标、SLO、RPO/RTO 与发布门禁

- **状态**：完成
- **目标**：冻结环境、流量、数据规模、SLO、告警、RPO/RTO、安全和发布责任。
- **为什么需要**：无目标值无法验收生产化。
- **输入**：Phase 07/08/09 验收、风险、部署需求。
- **前置任务**：Phase 07、08、09 完成。
- **操作步骤**：盘点源码/依赖；定义服务等级/容量/保留；确认部署/观测平台；威胁模型；发布/回滚门禁；修订计划/ADR。
- **涉及文件**：ADR、SLO/运行文档、本文件。
- **预期输出**：生产验收基线。
- **RAGFlow 源码依据**：Docker/Helm/benchmark 仅作能力清单参考。
- **实现或复用方式**：自行决策。
- **测试方法**：需求/风险评审。
- **验证命令**：按实际环境 probe 记录。
- **验收标准**：所有阈值、责任和例外有批准。
- **风险和回滚方法**：不明确则保持未生产，不猜测阈值。
- **实际执行结果**：见第 9 节 P10-T01。
- **实际验证结果**：ADR-025、配置和运行手册一致性通过。
- **计划偏差**：无架构偏差；ADR-026 将企业外部条件从完成阻断项调整为运行时要求或可选扩展。

### P10-T02：建立版本化评测数据集

- **状态**：完成
- **目标**：构建开发/验证/回归分离的脱敏、授权数据集和标注 Schema。
- **为什么需要**：所有质量结论需要稳定数据事实。
- **输入**：P10-T01、各阶段样本和失败案例。
- **前置任务**：P10-T01。
- **操作步骤**：数据来源/许可；轨道交通及通用企业场景；query/relevance/answer/citation/tool labels；难例/负例；版本/hash/split。
- **涉及文件**：`evaluation/datasets/`、datasheet、校验器。
- **预期输出**：版本化数据集。
- **RAGFlow 源码依据**：`test/benchmark/dataset.py` 只参考加载方式。
- **实现或复用方式**：自行开发。
- **测试方法**：Schema、重复/泄漏、标注一致性、敏感扫描。
- **验证命令**：`uv run <dataset-validator>`
- **验收标准**：来源/许可/脱敏/版本/划分清楚。
- **风险和回滚方法**：问题样本隔离，不修改历史版本。
- **实际执行结果**：见第 9 节 P10-T02。
- **实际验证结果**：manifest、hash、许可、脱敏和三个 split 校验通过。
- **计划偏差**：使用 `datasets/phase10/v1` 代替草案路径。

### P10-T03：建立检索评测

- **状态**：完成
- **目标**：统一 Recall@K、Precision@K、MRR、NDCG、过滤/权限和延迟评测。
- **为什么需要**：比较全文/向量/混合/Rerank/高级检索。
- **输入**：P10-T02、RetrievalTrace。
- **前置任务**：P10-T02。
- **操作步骤**：实现 runner/metrics；按 tenant/Profile/后端切片；显著性/置信区间；基线存档；回归阈值。
- **涉及文件**：`evaluation/retrieval/`、报告。
- **预期输出**：检索评测体系。
- **RAGFlow 源码依据**：上游 benchmark 不具备这些质量指标。
- **实现或复用方式**：自行开发，可适配成熟评测库。
- **测试方法**：手算样例、空 qrels、tie、过滤错误。
- **验证命令**：`uv run pytest tests/unit/evaluation/test_retrieval_metrics.py -q`; `uv run <retrieval-eval>`
- **验收标准**：指标正确、可重复、可对比基线。
- **风险和回滚方法**：门限变化必须版本/审批。
- **实际执行结果**：见第 9 节 P10-T03。
- **实际验证结果**：手算单元测试与确定性 runner 通过。
- **计划偏差**：未声明真实业务显著性或置信区间结论。

### P10-T04：建立答案与引用评测

- **状态**：完成
- **目标**：评测正确性、忠实度、相关性、拒答、Citation precision/recall/quote/source。
- **为什么需要**：高召回不保证答案可信。
- **输入**：P10-T02、P10-T03、答案/Citation。
- **前置任务**：P10-T02、P10-T03。
- **操作步骤**：确定规则/LLM judge/人工抽检；judge 版本；引用服务端校验；多语言；空结果/冲突；阈值。
- **涉及文件**：`evaluation/{answers,citations}/`、报告。
- **预期输出**：答案/引用评测。
- **RAGFlow 源码依据**：citation_prompt/insert_citations 只作行为参考。
- **实现或复用方式**：LangChain 评测 Adapter + 自研指标/门禁。
- **测试方法**：已知正确/幻觉/错引/漏引/删除/越权。
- **验证命令**：`uv run pytest tests/unit/evaluation/test_answer_citation_metrics.py -q`; `uv run <answer-eval>`
- **验收标准**：judge 可追溯；引用错误不能被平均指标掩盖。
- **风险和回滚方法**：LLM judge 漂移用固定版本+人工校准。
- **实际执行结果**：见第 9 节 P10-T04。
- **实际验证结果**：正确性、忠实度、拒答和 Citation precision/recall 单元测试通过。
- **计划偏差**：未运行真实 LLM Judge，确定性规则与真实模型结果分开报告。

### P10-T05：建立 Agent 与高级能力评测

- **状态**：完成
- **目标**：评测 Agent success、Tool accuracy、步骤/循环、恢复/HITL、成本及每项高级 RAG 增益。
- **为什么需要**：复杂链路必须独立证明收益。
- **输入**：P10-T02、P10-T04、Phase 08/09 报告。
- **前置任务**：P10-T02、P10-T04。
- **操作步骤**：任务 rubric；Tool/参数/终止；恢复/HITL；成本/延迟；自动关键词/问题/摘要/TOC/父子/多模态/GraphRAG/RAPTOR/时序逐项消融。
- **涉及文件**：`evaluation/{agent,advanced}/`、报告。
- **预期输出**：Agent/高级能力评测。
- **RAGFlow 源码依据**：RAGFlow benchmark 无这些指标。
- **实现或复用方式**：LangGraph events + 自研评测。
- **测试方法**：确定性场景、模型多次运行、失败/越权。
- **验证命令**：`uv run <agent-eval>`; `uv run <advanced-eval>`
- **验收标准**：每项能力独立结果；无收益不默认启用。
- **风险和回滚方法**：成本失控按预算中止并记录失败。
- **实际执行结果**：见第 9 节 P10-T05。
- **实际验证结果**：Agent 确定性报告与九项高级能力独立报告通过 Schema/安全门禁。
- **计划偏差**：九项高级能力因无真实模型增益证据全部保持 no-go/off。

### P10-T06：建立回归和发布质量门禁

- **状态**：完成
- **目标**：将单元/集成/E2E/评测基线纳入 CI/发布决策。
- **为什么需要**：防止模型、Prompt、Parser、索引和代码变更静默降质。
- **输入**：P10-T03 至 P10-T05。
- **前置任务**：P10-T03 至 P10-T05。
- **操作步骤**：快/慢/供应商测试层级；baseline artifact；阈值/允许退化；报告 diff；审批/例外；防 flaky。
- **涉及文件**：CI、evaluation config、release gate。
- **预期输出**：质量门禁。
- **RAGFlow 源码依据**：benchmark report 只参考输出样式。
- **实现或复用方式**：自行开发。
- **测试方法**：故意引入退化验证门禁失败。
- **验证命令**：`uv run <regression-gate> --baseline <version>`
- **验收标准**：严重权限/引用/恢复指标不能被例外自动忽略。
- **风险和回滚方法**：例外有期限/责任人；门禁配置版本化。
- **实际执行结果**：见第 9 节 P10-T06。
- **实际验证结果**：正常报告通过；故意退化报告确定性失败；CI 门禁已更新。
- **计划偏差**：真实 Provider 测试为可选层且本次未运行。

### P10-T07：完善日志、Trace、指标和告警

- **状态**：完成
- **目标**：关联 API→Job→Parser→Embedding→Search→LLM→Agent/Tool 的观测链路。
- **为什么需要**：生产故障必须定位且不泄密。
- **输入**：P10-T01、各阶段 event/Trace。
- **前置任务**：P10-T01。
- **操作步骤**：统一 Schema/OTel（按选型）；trace propagation；指标/直方图；队列/模型/成本；采样/保留/脱敏；dashboard/alert。
- **涉及文件**：`observability/`、deploy config、runbook、测试。
- **预期输出**：可观测性系统。
- **RAGFlow 源码依据**：token sink、Langfuse、Dealer trace_id、OTEL/Jaeger 配置参考。
- **实现或复用方式**：标准观测库 + 自研 Schema。
- **测试方法**：跨进程传播、sink 故障、采样、敏感字段、告警。
- **验证命令**：`uv run pytest tests/integration/observability -q`
- **验收标准**：关键路径可关联；禁止字段不入日志/Trace。
- **风险和回滚方法**：观测后端故障不阻断核心业务但产生健康告警。
- **实际执行结果**：见第 9 节 P10-T07。
- **实际验证结果**：JSON 日志、OTel、Prometheus、Dashboard/告警配置和实际本地栈启动通过。
- **计划偏差**：月度保留和真实告警通知通道未由短时本地运行证明。

### P10-T08：完成多租户、ACL 与安全门禁

- **状态**：完成
- **目标**：验证 tenant/owner/visibility、ACL 扩展接口、数据权限和安全全链路。
- **为什么需要**：任何越权都是生产阻断。
- **输入**：P10-T01、AuthorizationContext/PermissionChecker、Tool/生命周期。
- **前置任务**：P10-T01、P10-T07。
- **操作步骤**：Repository/Search/Object/Queue/Cache/Checkpoint/Trace/Tool/Citation 负向；文件攻击；Prompt/Tool 注入；SSRF/SQL；密钥/依赖/镜像扫描；审计。
- **涉及文件**：`tests/security/`、policy、runbook。
- **预期输出**：安全验收报告。
- **RAGFlow 源码依据**：KB permission/index_name 用例仅作检查清单。
- **实现或复用方式**：自行开发。
- **测试方法**：矩阵化越权、攻击模拟、扫描。
- **验证命令**：`uv run pytest tests/security -q`; 按实际扫描器记录命令。
- **验收标准**：跨租户零容忍；复杂 RBAC 未实现部分明确。
- **风险和回滚方法**：严重问题阻止发布并关闭相关能力。
- **实际执行结果**：见第 9 节 P10-T08。
- **实际验证结果**：全仓安全负向测试、Secret/大文件/数据集/provenance 和依赖扫描通过。
- **计划偏差**：企业 IdP、外部证书和受控出口属于公网部署强化；项目有意不设置顶层 LICENSE，均不阻止本地或自有云范围完成。

### P10-T09：执行性能、并发、容量与成本测试

- **状态**：完成
- **目标**：测 API/Worker/检索/模型/Agent 的延迟、吞吐、队列、资源和成本。
- **为什么需要**：确定扩容、上限和 SLO。
- **输入**：P10-T06、P10-T07、生产数据规模模型。
- **前置任务**：P10-T06、P10-T07。
- **操作步骤**：工作负载；冷/热；并发/背压；大文档/批量/Agent；容量拐点；成本；资源泄漏；报告。
- **涉及文件**：`tests/{performance,capacity}/`、报告。
- **预期输出**：性能/容量/成本基线。
- **RAGFlow 源码依据**：`test/benchmark/metrics.py::summarize` 参考延迟/QPS统计。
- **实现或复用方式**：参考后自研。
- **测试方法**：阶梯负载、耐久、尖峰、依赖限流。
- **验证命令**：`uv run <load-test> --profile production-candidate`
- **验收标准**：达到 P10-T01 阈值；瓶颈和扩容规则明确。
- **风险和回滚方法**：隔离环境/限额；不对外部供应商造成非授权压力。
- **实际执行结果**：见第 9 节 P10-T09。
- **实际验证结果**：本地确定性延迟、32 并发、背压和 local/unknown 成本边界测试通过。
- **计划偏差**：短时合成测试不证明生产容量、外部 Provider 成本或月度 SLO。

### P10-T10：建立 Docker 生产部署与配置管理

- **状态**：完成
- **目标**：同一制品以 API/Worker 两入口部署，具备健康、配置、迁移和扩缩容。
- **为什么需要**：第一版生产拓扑必须可重复。
- **输入**：P10-T01、P10-T07、Phase 01 Docker。
- **前置任务**：P10-T01、P10-T07。
- **操作步骤**：多阶段镜像/non-root/SBOM；API/Worker command；health/readiness；配置/secret 注入；迁移 job；资源/网络/volume；compose 或选定平台清单。
- **涉及文件**：`deploy/docker/`、Dockerfile、config/runbook。
- **预期输出**：生产候选制品。
- **RAGFlow 源码依据**：`launch_backend_service.sh`、compose、Helm 只参考拓扑。
- **实现或复用方式**：参考重写。
- **测试方法**：全新部署、滚动/独立扩缩、健康、secret、镜像扫描。
- **验证命令**：`docker build ...`; `docker compose -f deploy/docker/... config`; 平台验证按决策记录。
- **验收标准**：API/Worker 独立运行；不拆微服务；无默认密钥/root。
- **风险和回滚方法**：镜像版本不可变；保留前版制品。
- **实际执行结果**：见第 9 节 P10-T10。
- **实际验证结果**：Linux/amd64 多阶段 non-root 镜像、Compose 配置、一次性迁移、API/Worker 独立健康和观测栈通过。
- **计划偏差**：arm64 与真实 TLS/IdP/出口环境按实际验证结果记录，不做推断。

### P10-T11：实现备份、恢复与迁移验证

- **状态**：完成
- **目标**：覆盖 PostgreSQL、对象存储、搜索可重建数据、队列/Checkpoint/配置和密钥元数据。
- **为什么需要**：生产必须达到 RPO/RTO。
- **输入**：P10-T10、P10-T01 RPO/RTO。
- **前置任务**：P10-T10。
- **操作步骤**：数据分类/事实源；备份计划/加密/保留；恢复顺序；索引重建；迁移前备份；定期 restore test。
- **涉及文件**：backup scripts/config、`docs/10-production-runbook.md`、tests。
- **预期输出**：备份恢复能力和证据。
- **RAGFlow 源码依据**：上游部署文件只作依赖清单参考。
- **实现或复用方式**：自行开发。
- **测试方法**：空环境/部分丢失/旧版本恢复、校验 hash/tenant。
- **验证命令**：按选定平台执行并记录 restore drill 命令。
- **验收标准**：RPO/RTO 达标；恢复后评测/权限通过。
- **风险和回滚方法**：不覆盖唯一备份；恢复环境隔离。
- **实际执行结果**：见第 9 节 P10-T11。
- **实际验证结果**：内容 hash、空目标、篡改拒绝、恢复相等与 `0005 -> 0006` 往返通过。
- **计划偏差**：没有生产快照和对象量级，RPO/RTO 仅是目标而非生产证明。

### P10-T12：执行故障演练、发布与回滚

- **状态**：完成
- **目标**：演练依赖/Worker/模型/搜索/数据库故障及版本发布回滚。
- **为什么需要**：Runbook 必须被实际验证。
- **输入**：P10-T08 至 P10-T11。
- **前置任务**：P10-T08 至 P10-T11。
- **操作步骤**：故障目录；GameDay；告警/值守；发布 canary/迁移；质量/安全门禁；应用/DB/index/config 回滚；复盘。
- **涉及文件**：drill tests、release/runbook、报告。
- **预期输出**：故障演练和发布证据。
- **RAGFlow 源码依据**：无新增。
- **实现或复用方式**：自行开发运维流程。
- **测试方法**：受控故障注入、恢复计时、数据一致性/评测复跑。
- **验证命令**：按实际平台记录，不预填成功。
- **验收标准**：告警及时、恢复达标、回滚完整、无越权/数据损坏。
- **风险和回滚方法**：预演/staging/停止条件；生产演练需授权。
- **实际执行结果**：见第 9 节 P10-T12。
- **实际验证结果**：隔离 Compose 依赖/网络/Worker 演练与 Provider/Checkpoint/DLQ 安全故障注入通过。
- **计划偏差**：未操作真实用户数据或不可逆迁移；隔离发布/回滚已验证，真实环境操作由用户部署时执行。

### P10-T13：执行最终生产出口审查

- **状态**：完成
- **目标**：综合质量、安全、性能、部署、恢复和文档决定是否发布。
- **为什么需要**：路线图没有 Phase 11，必须形成明确生产准入。
- **输入**：P10-T01 至 P10-T12。
- **前置任务**：P10-T01 至 P10-T12。
- **操作步骤**：核对全部 DoD/风险/开放项；运行最终门禁；确认高级 flag；签署 release/rollback；同步所有事实文档。
- **涉及文件**：全部总体文档、release report、runbook、本文件。
- **预期输出**：允许/不允许发布结论。
- **RAGFlow 源码依据**：核对所有复用 provenance 和冻结基线。
- **实现或复用方式**：审计。
- **测试方法**：全量回归、评测、安全、性能、恢复、部署。
- **验证命令**：使用 P10-T06/P10-T08/P10-T09/P10-T11/P10-T12 的已确认门禁命令。
- **验收标准**：所有硬门禁通过；例外有批准/期限；无计划项误标。
- **风险和回滚方法**：任何严重缺陷结论为不发布。
- **实际执行结果**：ADR-026 校正后的机器报告明确 `production_exit=local_or_self_managed_ready`。
- **实际验证结果**：本地或自有云质量、安全、隔离恢复、Compose 与源码门禁通过；模型由用户运行时配置。
- **计划偏差**：企业接入、长期 SLO 和真实业务效果改列为后续使用或可选扩展。

## 8. 阶段验收、DoD、风险和后续

**DoD**：P10-T01 至 P10-T13 完成；数据集/检索/答案/引用/Agent/高级能力评测和回归门禁可重复；日志/Trace/指标/告警完整；tenant/ACL/安全通过；性能容量成本达标；部署/配置/备份恢复/演练/发布回滚有证据；形成明确生产准入。

| 风险 | 处理 |
|---|---|
| 评测集偏差 | 多场景/难例/独立 split/人工抽检 |
| 线上线下漂移 | 版本、采样、影子/回放和监控 |
| Trace 泄密 | 最小化、脱敏、访问/保留 |
| 恢复仅停留文档 | 定期 restore/GameDay 硬门禁 |
| 高级能力复杂度 | 按 Phase 09 独立 go/no-go 和 flag |
| 真实模型或长期运营证据未执行 | 如实标为运行时/运营期未验证，不降低当前质量、安全和恢复硬门禁 |

阶段结束更新 `AGENTS.md`、总纲、架构、矩阵、复用、路线图、标准、风险、阶段索引、运行/评测文档和本文件。路线图没有 Phase 11；通过后进入版本运营或经新 ADR 修订下一轮路线图。

## 9. 实际执行结果

| 任务 | 实际产出 | 证据边界 |
|---|---|---|
| P10-T01 | ADR-025 冻结 Linux Docker Compose、SLO、RPO/RTO、角色和 UI Deferred | 目标已冻结，月度 SLO 尚未被短时测试证明 |
| P10-T02 | `datasets/phase10/v1` 与 fail-closed validator | CC0 合成数据，非真实企业数据 |
| P10-T03 | Precision/Recall/MRR/NDCG 和权限/延迟字段 | 指标手算通过，真实业务检索质量未验证 |
| P10-T04 | 正确性、忠实度、拒答、Citation precision/recall | 确定性规则，不冒充 LLM Judge |
| P10-T05 | Agent 与九项高级能力独立报告 | Fake/纯算法；九项高级能力全部 no-go/off |
| P10-T06 | 不可豁免门禁、故意退化测试、Phase 10 CI | 本地门禁通过；真实 Provider 层未运行 |
| P10-T07 | JSON 日志、Trace context、OTLP、Prometheus、Dashboard、告警 | 本地 Collector/Prometheus/Grafana 启动；实际通知与保留期未证明 |
| P10-T08 | tenant/ACL/Tool/SQL/API/SSRF/密钥/供应链负向测试与治理扫描 | 严重违规 0；依赖审计通过；Docker Scout 为可选外部扫描，项目顶层 LICENSE 有意不设置 |
| P10-T09 | 本地延迟/并发/背压/成本状态报告 | 100 合成样本、32 并发；不代表生产容量或供应商费用 |
| P10-T10 | 多阶段 non-root 镜像、API/Worker、一次性迁移、独立卷、TLS/限流配置 | amd64 实测；arm64 因 Docker Hub token 端点拒绝连接而未完成构建验证 |
| P10-T11 | 内容寻址备份/恢复、篡改拒绝、索引重建顺序、迁移往返 | 合成 authority 数据；没有生产备份恢复证据 |
| P10-T12 | PostgreSQL/Redis/MinIO/Elasticsearch/Worker/网络实栈演练与 Provider/Checkpoint/DLQ 故障注入 | 隔离环境；未触碰生产数据或真实外部写操作 |
| P10-T13 | `reports/phase10/release-report.json` | 出口：`local_or_self_managed_ready` |

关键机器产物：`reports/phase10/evaluation.json`、`operations.json`、`governance-scan.json`、`dependency-audit.json`、`sbom.json`、`image-scan.json`、`deployment-verification.json` 与 `release-report.json`。

计划偏差：断点前已提前生成部分 Phase 10 基线文件，并随 Phase 09 checkpoint 提交 `38b48ba` 一并提交；恢复后未重做已完成实现，只完成验证、缺口修复和正式记录。外部观测镜像首次拉取遇到 TLS timeout，重试后成功。Docker Desktop 对隔离 Compose 的宿主端口存在 HostConfig 已配置但 NetworkSettings 未发布的本机异常，因此 API/观测健康以容器内部真实请求验证；arm64 构建在重复尝试时均被 Docker Hub token 网络拒绝，未标记为已验证。详细证据见 `reports/phase10/deployment-verification.json`。

最终结论：Phase 00 至 Phase 10 以及当前约定的 Agent + RAG 后端源码范围已经完成。项目已达到本地或自有云部署运行条件。企业系统接入、真实业务效果验证和长期运营指标属于后续使用或可选扩展，不属于当前项目完成阻断项。

## 10. 最终验证记录

| 验证 | 实际结果 |
|---|---|
| `uv lock --check`、`uv sync --frozen --all-groups`、`uv pip check` | 通过；162 个锁定包兼容 |
| `uv run ruff check .` | 通过 |
| `uv run mypy src/ragflow_agent tests` | 通过；408 个源文件无问题 |
| 隔离四后端 `uv run pytest` | 收集 330 项，329 passed、1 skipped；唯一 skip 为 Windows 本机没有 Tesseract，CI 单独安装并强制执行 OCR |
| 故意退化与 fail-closed 发布门禁 | 5 项定向测试通过；降级指标、跨租户违规、Citation 退化均会阻止发布 |
| Alembic | 隔离 PostgreSQL `20260801_0006 -> 20260731_0005 -> 20260801_0006` 通过；全新 Compose 迁移 Job 退出码 0 |
| 数据集与评测 runner | Phase 09/10 manifest、hash、split、许可、脱敏验证通过；机器报告可重复生成 |
| Secret/大小/provenance 治理 | 无密钥命中、无超大文件、无 RAGFlow/第三方源码复制；项目顶层 LICENSE 有意不设置，第三方/数据集许可记录保留 |
| `pip-audit`（OSV） | 真实联网审计完成，0 个已知漏洞 |
| CycloneDX SBOM | 可复现生成并通过 schema 验证 |
| Docker Scout | 已尝试；缺少 Docker ID/PAT，作为可选外部扫描未执行，不是 Compose 运行阻断项 |
| Linux amd64 镜像 | 构建通过；`USER=ragflow-agent`，不声明项目 license label，API/Worker bootstrap 通过 |
| Linux arm64 镜像 | 两次构建均在 Docker Hub anonymous token 连接处失败；未验证 |
| Docker Compose 生产候选 | 全新隔离栈 PostgreSQL/Redis/MinIO/Elasticsearch healthy，迁移成功，API/Worker healthy；Collector 接收 spans，Prometheus ready，Grafana database ok |
| Compose 宿主访问 | Docker Desktop 本机端口转发异常；容器内部 HTTP 和健康检查通过，不记作宿主/生产入口验证 |
| 故障与恢复 | PostgreSQL、Redis、MinIO、Elasticsearch、Worker、网络执行隔离实栈注入；Provider/Checkpoint/DLQ 使用确定性安全注入；Worker kill 的自动重启未证明 |
| 备份恢复、性能与容量 | 合成 authority 内容 hash 恢复通过；100 个合成延迟样本、32 并发、0 错误，只证明本地机制，不证明生产规模/RTO/SLO |

机器报告的最终判定为 `production_exit=local_or_self_managed_ready`。GitHub Actions 以提交后的最终 `main` workflow 结果作为仓库级门禁，运行链接在交付汇报中记录。

## 11. ADR-026 完成范围校正记录

2026-08-01 按用户最终完成定义执行独立校正：仓库根目录实际不存在本项目 `LICENSE`，
`pyproject.toml` 也没有项目许可证字段；已移除 Dockerfile 的 `NOASSERTION` 项目许可证标签，
并把治理扫描改为记录 `project_license_policy=intentionally_absent`。第三方依赖、数据集、模型和
外部资源的许可证/provenance 未删除。

发布判定只把质量、安全和隔离恢复作为本地或自有云硬门禁；真实 Provider、基础设施 Secret
作为用户运行时输入，Docker Scout、ARM64、企业系统/IdP、真实业务效果、长期 SLO、正式运维
组织、Kubernetes、私有仓库和 UI 作为可选扩展。`release-report.json` schema v2 的结论为
`local_or_self_managed_ready`，无 decision blocker。

本次实际验证：受影响的 8 项发布/治理/安全测试通过；更新后全仓 `312 passed, 19 skipped`，
Ruff 通过，mypy 408 个源文件通过；`uv lock --check`、`uv sync --frozen --all-groups`、
`uv pip check`、wheel/sdist 构建、开发与生产 Compose config 均通过。19 个 skip 均因本轮未注入
隔离后端或本机 Tesseract；Phase 10 既有隔离实栈结果继续作为对应证据，不将 Fake 或未运行的
真实模型测试改写为真实效果。

最终结论：Phase 00至Phase 10以及当前约定的Agent＋RAG后端源码范围已经完成。项目已达到本地或自有云部署运行条件。企业系统接入、真实业务效果验证和长期运营指标属于后续使用或可选扩展，不属于当前项目完成阻断项。
