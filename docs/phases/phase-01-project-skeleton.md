---
document_id: PHASE-01-PROJECT-SKELETON
document_role: Phase 01 可执行详细计划
status: pending_confirmation
phase: Phase 01
phase_name: 项目骨架
plan_status: 待确认
execution_status: 未执行
last_updated_at: "2026-07-30"
project_root: "D:/download/myself"
ragflow_frozen_baseline_commit: "cd846cc9d4e32a19e684c59a1f302601027ef976"
---

# Phase 01：项目骨架详细计划

## 0. 文档状态与使用规则

- **计划状态**：待确认。
- **执行状态**：未执行。
- 本文件达到可直接执行的任务粒度，但 O-001 项目名/Python 包名、O-012 Git/CI/类型检查器和用户确认仍是执行门禁。
- 执行前必须重新读取 [AGENTS](../../AGENTS.md)、[项目总纲](../00-project-master.md)、[路线图](../05-development-roadmap.md)、[工程标准](../06-engineering-standards.md)、[决策与风险](../07-decisions-and-risks.md)及实际工作区。
- 本轮只生成计划；以下交付物、目录和命令均是规划，不代表已经存在或执行。

导航：[阶段索引](./README.md) · [Phase 00](./phase-00-research-and-baseline.md) · [Phase 02](./phase-02-agent-foundation.md)

## 1. 阶段目标

建立同一仓库、同一发行单元内可安装、可测试、可独立启动的模块化单体 FastAPI API 与 Ingestion Worker 骨架，落地配置、数据库、基础设施端口、日志、异常、测试和 Docker 开发环境，同时只预留第一版多租户授权上下文，不提前实现知识库业务。

## 2. 背景与必要性

Phase 00 确认目标项目仍是 greenfield；后续 Agent、领域模型和 RAG 数据面需要稳定的包结构、进程入口、依赖方向和质量命令。RAGFlow 的全局 `settings`、Quart、Peewee 和任务执行器不适合作为本项目骨架，但其 API/Worker 分进程拓扑可以提供边界证据。

## 3. Phase 00 事实依据

1. 目标目录当前只有 `AGENTS.md` 和文档，没有 `.git`、业务代码、依赖、迁移、测试或部署文件。
2. ADR-007 接受 Python 3.13、uv、FastAPI、PostgreSQL、SQLAlchemy 2、Alembic、Redis、MinIO/S3。
3. ADR-011 接受同仓库模块化单体和独立 Ingestion Worker；二者通过任务队列连接，不用内部 HTTP。
4. ADR-012 要求从第一版保留 `tenant_id`、`owner_id`、`visibility`、`AuthorizationContext`、`PermissionChecker`。
5. 当前没有批准直接复用的 RAGFlow 源文件。

## 4. 前置阶段与进入条件

- **前置阶段**：Phase 00，已完成。
- **执行前必须满足**：
  1. O-001 项目正式名称、发行包名、import package 的答案已提供。
  2. 本计划经用户确认。
  3. 重新检查目标目录 Git/文件状态，确认是否先初始化 Git 由用户授权。
  4. ADR-007、ADR-011、ADR-012 未被新决策替代。
  5. O-012 的 Git/CI/类型检查器选择可在 P01-T01 中记录，但没有用户答案前不得执行相应写入。

## 5. 输入资料与依赖产物

- `docs/00-project-master.md` 至 `docs/07-decisions-and-risks.md`。
- Phase 00 基线、源码地图、复用清单和一致性报告。
- Python 3.13、uv、FastAPI、SQLAlchemy 2、Alembic、pytest、ruff 官方文档。
- 用户确认的项目名、包名、CI 平台和类型检查器。

## 6. 工作范围

1. Python `src` 布局、依赖分组和锁文件。
2. 模块化单体的 API/Worker 两个 bootstrap。
3. 分层配置与密钥规则。
4. SQLAlchemy/Alembic 空基线和连接生命周期。
5. 队列、对象存储、搜索、模型和时钟/ID 等基础设施端口占位。
6. 结构化日志、trace/request/job 标识和统一异常。
7. FastAPI 健康、就绪和错误响应。
8. Worker 启停、心跳和优雅关闭空循环。
9. pytest、ruff、类型检查、导入边界和 CI 骨架。
10. PostgreSQL、Redis、MinIO/S3 的 Docker 开发环境；搜索服务只在 O-002 决定后加入。
11. `AuthorizationContext` 最小不可变结构与可信构造边界预留，不实现权限规则。

## 7. 明确不包含

- KnowledgeBase、Document、Chunk、IngestionTask 领域实现。
- Parser、OCR、Embedding、索引、真实队列消费或检索。
- Agent 业务图和真实模型调用。
- Elasticsearch/OpenSearch 的擅自选择。
- 微服务拆分、Kubernetes、生产部署、复杂 RBAC。
- RAGFlow Quart/Peewee/settings/Canvas 的复制。

## 8. 主要交付物

- `pyproject.toml`、`uv.lock`、开发/测试依赖组。
- `src/<package>/bootstrap/{api,ingestion_worker}.py`。
- `src/<package>/config/`、`observability/`、`shared/errors.py`、基础端口。
- `alembic.ini`、`migrations/`、数据库连接基础设施。
- `tests/{unit,contract,integration}/`、质量命令和 CI。
- `docker-compose.dev.yml`、`.env.example`、Docker 开发说明。
- 根 README/AGENTS 的实际执行入口更新。

## 9. 涉及的目标模块和文件

所有路径在 P01-T01 确认包名后替换 `<package>`：

```text
pyproject.toml
uv.lock
src/<package>/
  bootstrap/
  config/
  shared/
  observability/
  infrastructure/{database,queue,object_store,search,models}/
tests/{unit,contract,integration}/
migrations/
docker-compose.dev.yml
.env.example
README.md
```

## 10. RAGFlow 源码研究范围与调用关系

| 目的 | 冻结源码 | 需要核对的关系 |
|---|---|---|
| Python 版本与依赖分组 | `pyproject.toml` | 只参考 Python 3.13 和依赖类别，不复制全量依赖 |
| API/Worker 分进程 | `docker/launch_backend_service.sh::run_server/task_exe` | shell 分别启动 API 与 `rag/svr/task_executor.py` |
| API 启动 | `api/ragflow_server.py` | 入口调用 `settings.init_settings()` 后启动 Quart；作为反例 |
| 全局初始化反例 | `common/settings.py::init_settings`、`StorageFactory` | 初始化数据库、对象存储、DocStore、Retriever 等全局单例 |
| 队列边界预览 | `api/db/services/task_service.py::queue_tasks` → `rag/utils/redis_conn.py::queue_product` | 只用于定义未来端口，不实现真实任务 |

## 11. 复用方式

| 分类 | 本阶段结论 |
|---|---|
| 直接复用 | 无 |
| `ragflow_adapters` 改造复用 | 无；本阶段不抽取上游源码 |
| 参考后自研 | API/Worker 拓扑、依赖分类、健康检查用例 |
| 明确不采用 | Quart、Peewee、`common.settings` 全局单例、RAGFlow 启动脚本复制 |

## 12. 责任边界

- **LangGraph**：仅验证依赖可导入和测试环境可用，不实现业务图。
- **LangChain**：仅建立模型/Embedding/Tool 适配包边界和测试替身，不调用供应商。
- **本项目自研**：项目布局、配置、FastAPI、Worker、数据库基础、端口、日志、错误、测试和 Docker 开发环境。

## 13. 任务总表与依赖

| 任务 | 名称 | 状态 | 前置任务 |
|---|---|---|---|
| P01-T01 | 冻结 Phase 01 执行基线与命名 | 未开始 | Phase 00 |
| P01-T02 | 建立 Python 包、依赖和质量工具 | 未开始 | P01-T01 |
| P01-T03 | 建立类型化配置与密钥边界 | 未开始 | P01-T02 |
| P01-T04 | 建立日志、Trace 与异常基础 | 未开始 | P01-T02、P01-T03 |
| P01-T05 | 建立 SQLAlchemy 与 Alembic 空基线 | 未开始 | P01-T02、P01-T03 |
| P01-T06 | 建立基础设施端口和适配器边界 | 未开始 | P01-T02、P01-T05 |
| P01-T07 | 建立 FastAPI bootstrap | 未开始 | P01-T03、P01-T04、P01-T05 |
| P01-T08 | 建立独立 Ingestion Worker bootstrap | 未开始 | P01-T03、P01-T04、P01-T06 |
| P01-T09 | 建立 Docker 开发环境 | 未开始 | P01-T05、P01-T07、P01-T08 |
| P01-T10 | 建立测试/CI 门禁并执行阶段验收 | 未开始 | P01-T01 至 P01-T09 |

## 14. 具体任务

### P01-T01：冻结 Phase 01 执行基线与命名

- **状态**：未开始
- **目标**：把用户提供的 O-001/O-012 答案写入事实源，固定项目名、发行包、import package、服务名和本阶段工具选择。
- **为什么需要**：未确认命名会污染目录、配置前缀、迁移、镜像和 Trace。
- **输入**：ADR-007、O-001、O-012、当前文件/Git 状态。
- **前置任务**：Phase 00 完成。
- **操作步骤**：重新盘点工作区；取得用户命名结论；确定类型检查器、CI 平台和 Git 初始化授权；记录 ADR/开放项；把 `<package>` 映射为真实路径。
- **涉及文件**：`docs/07-decisions-and-risks.md`、本文件、计划中的 `pyproject.toml`。
- **预期输出**：命名和工具决策、确认后的路径清单。
- **RAGFlow 源码依据**：`pyproject.toml` 仅用于版本/依赖参考，不决定本项目名称。
- **实现或复用方式**：自行决策与文档化，不复用代码。
- **测试方法**：检查名称符合 Python 包规范且所有文档引用一致。
- **验证命令**：`Select-String -Path docs/**/*.md -Pattern '<package>|src/app'`
- **验收标准**：O-001/O-012 Resolved；不存在未解释的包名或质量命令占位。
- **风险和回滚方法**：命名变更代价高；代码创建前可只回滚文档决策。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待执行时记录。

### P01-T02：建立 Python 包、依赖和质量工具

- **状态**：未开始
- **目标**：创建可安装的 `src` 布局、依赖组、锁文件和统一质量命令。
- **为什么需要**：后续所有模块需要可重复环境和稳定导入。
- **输入**：P01-T01 命名、ADR-007、工程标准第 3 节。
- **前置任务**：P01-T01。
- **操作步骤**：创建 `pyproject.toml`；设置 Python 3.13；定义 runtime/dev/parser 可选组；配置 pytest、ruff、类型检查器；生成锁文件；建立包和测试目录。
- **涉及文件**：`pyproject.toml`、`uv.lock`、`src/<package>/__init__.py`、`tests/`。
- **预期输出**：可安装空包和质量命令。
- **RAGFlow 源码依据**：`pyproject.toml` 的 Python 约束和依赖类别仅作兼容性参考。
- **实现或复用方式**：自行开发。
- **测试方法**：全新环境同步、导入、最小测试、lint 和类型检查。
- **验证命令**：`uv sync --all-groups`; `uv run python -c "import <package>"`; `uv run pytest`; `uv run ruff check .`
- **验收标准**：锁文件可重复安装；无未声明依赖。
- **风险和回滚方法**：Python 3.13 兼容失败时回退单一依赖，不擅自更换 Python 基线。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待执行时记录。

### P01-T03：建立类型化配置与密钥边界

- **状态**：未开始
- **目标**：定义 API、Worker、数据库、队列、对象存储、搜索、模型和观测配置 Schema。
- **为什么需要**：业务模块不得直接读取环境变量或泄露密钥。
- **输入**：P01-T02、工程标准第 6 节。
- **前置任务**：P01-T02。
- **操作步骤**：定义不可变配置对象；实现 bootstrap 加载；建立开发/测试覆盖规则；生成无密钥 `.env.example`；增加配置验证错误。
- **涉及文件**：`src/<package>/config/`、`.env.example`、测试配置。
- **预期输出**：API/Worker 共用的类型化配置。
- **RAGFlow 源码依据**：`common/settings.py::init_settings` 是全局配置反例。
- **实现或复用方式**：参考后自研；明确不采用 RAGFlow settings。
- **测试方法**：必填、默认、非法值、密钥脱敏和环境覆盖单测。
- **验证命令**：`uv run pytest tests/unit/config -q`
- **验收标准**：业务包无 `os.getenv`；日志不输出密钥。
- **风险和回滚方法**：配置过度集中时拆分子 Schema；保持外部变量兼容映射。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待执行时记录。

### P01-T04：建立日志、Trace 与异常基础

- **状态**：未开始
- **目标**：统一结构化日志、关联 ID、稳定错误码和异常映射。
- **为什么需要**：API、Worker、任务和后续 Agent/RAG 必须可关联诊断。
- **输入**：P01-T02、P01-T03、工程标准第 7/16 节。
- **前置任务**：P01-T02、P01-T03。
- **操作步骤**：定义 `AppError`；生成 trace/request/job ID；配置 JSON/开发日志；实现敏感字段过滤；定义基础 TraceContext。
- **涉及文件**：`src/<package>/shared/errors.py`、`observability/`、测试。
- **预期输出**：统一错误与日志基础设施。
- **RAGFlow 源码依据**：`common/token_utils.py::token_usage_sink` 和日志只作部分观测用例；不复制。
- **实现或复用方式**：自行开发。
- **测试方法**：错误映射、字段齐全、密钥脱敏、context 传播。
- **验证命令**：`uv run pytest tests/unit/observability tests/unit/shared -q`
- **验收标准**：错误有 `error_code`/`trace_id`；禁止字段不出现在日志。
- **风险和回滚方法**：日志 Schema 变更须版本化；不以记录原文解决诊断问题。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待执行时记录。

### P01-T05：建立 SQLAlchemy 与 Alembic 空基线

- **状态**：未开始
- **目标**：建立异步/同步边界明确的数据库连接、事务和空迁移。
- **为什么需要**：Phase 03 的领域持久化需要稳定迁移与事务基础。
- **输入**：P01-T02、P01-T03、ADR-007。
- **前置任务**：P01-T02、P01-T03。
- **操作步骤**：配置 engine/session factory；定义 UnitOfWork 基础接口占位；初始化 Alembic；创建无业务表基线；验证 upgrade/downgrade。
- **涉及文件**：`infrastructure/database/`、`migrations/`、`alembic.ini`。
- **预期输出**：数据库连接和可逆空迁移。
- **RAGFlow 源码依据**：`api/db/db_models.py` 的 Peewee 模型明确不采用。
- **实现或复用方式**：自行开发。
- **测试方法**：临时 PostgreSQL 上迁移、连接回收和事务回滚。
- **验证命令**：`uv run alembic upgrade head`; `uv run alembic downgrade base`; `uv run pytest tests/integration/database -q`
- **验收标准**：迁移可重复；无业务表提前创建；连接正确关闭。
- **风险和回滚方法**：异步驱动兼容失败时记录 ADR，不混用 session 模式。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待执行时记录。

### P01-T06：建立基础设施端口和适配器边界

- **状态**：未开始
- **目标**：建立 Queue/ObjectStore/Search/Model/Clock/ID 的最小端口位置和依赖方向。
- **为什么需要**：防止 bootstrap 或应用代码直连供应商客户端。
- **输入**：P01-T02、P01-T05、目标架构和工程标准。
- **前置任务**：P01-T02、P01-T05。
- **操作步骤**：定义基础 Protocol 和生命周期；创建仅用于测试的内存/空适配器；增加导入边界测试；不定义知识库 DTO。
- **涉及文件**：`src/<package>/shared/ports/`、`infrastructure/{queue,object_store,search,models}/`。
- **预期输出**：可 wiring 的基础设施边界。
- **RAGFlow 源码依据**：`common/settings.py`、`rag/utils/redis_conn.py` 展示耦合风险。
- **实现或复用方式**：参考后自研。
- **测试方法**：Protocol 类型、生命周期和禁止导入测试。
- **验证命令**：`uv run pytest tests/unit/import_boundaries tests/contract/foundation -q`
- **验收标准**：核心层不导入具体客户端；空适配器不伪装业务成功。
- **风险和回滚方法**：抽象过度时只保留下一阶段会消费的端口。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待执行时记录。

### P01-T07：建立 FastAPI bootstrap

- **状态**：未开始
- **目标**：实现可独立启动、可测试的 API 入口和健康/就绪接口。
- **为什么需要**：后续 API 功能必须有统一 wiring、认证上下文和错误映射。
- **输入**：P01-T03、P01-T04、P01-T05。
- **前置任务**：P01-T03、P01-T04、P01-T05。
- **操作步骤**：创建 app factory/lifespan；注入配置和数据库；实现 `/health/live`、`/health/ready`；添加错误处理和 trace middleware；预留可信 `AuthorizationContext` 构造接口。
- **涉及文件**：`bootstrap/api.py`、`api/`、API 测试。
- **预期输出**：FastAPI 空服务。
- **RAGFlow 源码依据**：`api/ragflow_server.py` 只作启动用例；Quart 不采用。
- **实现或复用方式**：自行开发。
- **测试方法**：TestClient/ASGI 生命周期、健康、错误、trace、OpenAPI。
- **验证命令**：`uv run pytest tests/integration/api -q`; `uv run python -m <package>.bootstrap.api --check`
- **验收标准**：API 可独立启动，不导入 Parser/Worker。
- **风险和回滚方法**：启动副作用放入 lifespan；失败时撤回单个 wiring 变更。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待执行时记录。

### P01-T08：建立独立 Ingestion Worker bootstrap

- **状态**：未开始
- **目标**：建立独立进程入口、心跳、优雅关闭和空任务循环。
- **为什么需要**：验证 API/Worker 物理边界，不提前实现 ingestion。
- **输入**：P01-T03、P01-T04、P01-T06、ADR-011。
- **前置任务**：P01-T03、P01-T04、P01-T06。
- **操作步骤**：创建 worker factory；定义启动/停止钩子和 readiness；使用测试队列适配器；停止领取与安全退出；保证不导入 API 路由。
- **涉及文件**：`bootstrap/ingestion_worker.py`、`worker/`、测试。
- **预期输出**：可独立运行的空 Worker。
- **RAGFlow 源码依据**：`docker/launch_backend_service.sh` → `rag/svr/task_executor.py` 证明分进程边界。
- **实现或复用方式**：参考拓扑后自研。
- **测试方法**：启动、心跳、取消、优雅关闭、导入边界。
- **验证命令**：`uv run pytest tests/integration/worker -q`; `uv run python -m <package>.bootstrap.ingestion_worker --check`
- **验收标准**：Worker 无内部 HTTP、无 API route 导入、无真实任务副作用。
- **风险和回滚方法**：空循环阻塞时使用可控 poll/cancellation；保留单进程测试适配器。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待执行时记录。

### P01-T09：建立 Docker 开发环境

- **状态**：未开始
- **目标**：提供 PostgreSQL、Redis、MinIO/S3 和 API/Worker 的可重复开发拓扑。
- **为什么需要**：集成测试和本地开发不能依赖未记录的本机服务。
- **输入**：P01-T05、P01-T07、P01-T08。
- **前置任务**：P01-T05、P01-T07、P01-T08。
- **操作步骤**：编写 compose；添加健康检查、volume、network 和占位配置；API/Worker 使用同一制品不同命令；搜索后端保持 profile/待定。
- **涉及文件**：`docker-compose.dev.yml`、Dockerfile、`.dockerignore`、README。
- **预期输出**：最小开发环境。
- **RAGFlow 源码依据**：`docker/docker-compose-base.yml` 和 `launch_backend_service.sh` 只参考拓扑。
- **实现或复用方式**：参考重写。
- **测试方法**：全新启动、健康、停止、volume 清理说明。
- **验证命令**：`docker compose -f docker-compose.dev.yml config`; `docker compose -f docker-compose.dev.yml up --build --wait`
- **验收标准**：API/Worker 独立健康；没有默认密钥；搜索未被擅自选型。
- **风险和回滚方法**：端口冲突通过环境配置；数据删除使用显式开发命令。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待执行时记录。

### P01-T10：建立测试/CI 门禁并执行阶段验收

- **状态**：未开始
- **目标**：把安装、测试、lint、类型、迁移、导入和 Docker 检查固化为阶段门禁。
- **为什么需要**：骨架只有在新环境可重复验证时才可供后续阶段使用。
- **输入**：P01-T01 至 P01-T09。
- **前置任务**：P01-T01 至 P01-T09。
- **操作步骤**：建立 CI；并行运行质量检查；添加包边界和密钥扫描；更新 AGENTS/README/总文档；记录真实命令结果。
- **涉及文件**：CI 配置、`AGENTS.md`、`README.md`、本文件及总体文档。
- **预期输出**：Phase 01 验收报告和可执行开发入口。
- **RAGFlow 源码依据**：无新增事实。
- **实现或复用方式**：自行开发。
- **测试方法**：在干净环境运行全部门禁。
- **验证命令**：`uv sync --frozen --all-groups`; `uv run ruff check .`; `uv run <type-checker>`; `uv run pytest`; `docker compose -f docker-compose.dev.yml config`
- **验收标准**：全部命令通过；业务能力仍未被伪实现；文档状态真实。
- **风险和回滚方法**：不降低门禁掩盖失败；逐项回滚最近配置变更。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待执行时记录。

## 15. 测试与验证方案

- Unit：配置、错误、日志脱敏、ID/Trace。
- Contract：基础端口生命周期和测试适配器。
- Integration：PostgreSQL 迁移、API/Worker 启停。
- Static：ruff、类型检查、导入边界、密钥扫描。
- Environment：锁文件、Docker compose config、全新环境安装。

## 16. 阶段级验收标准

1. API 与 Worker 可独立启动、健康检查和关闭。
2. 同仓库共享配置/数据库/端口，不通过内部 HTTP。
3. Alembic upgrade/downgrade 验证通过。
4. 锁文件、测试、lint、类型和导入边界通过。
5. `AuthorizationContext` 只作可信边界预留，没有伪权限实现。
6. 没有知识库、Parser、检索或 Agent 业务代码。

## 17. Definition of Done

- P01-T01 至 P01-T10 全部完成且记录真实结果。
- O-001 已解决；所有占位路径已替换。
- 代码、迁移、测试、Docker 和文档一致。
- 主文档、路线图、能力矩阵、决策风险和阶段索引已同步。
- Phase 02 进入条件有明确结论。

## 18. 风险、限制与处理

| 风险 | 处理 |
|---|---|
| Python 3.13 依赖不兼容 | 单包验证、版本锁定；改变 Python 基线需 ADR |
| 骨架抽象过度 | 只创建下一阶段确定消费的端口 |
| API/Worker 重复实现 | 共享应用/领域/基础设施，仅 bootstrap 分离 |
| 密钥进入日志/fixture | 脱敏测试和扫描门禁 |
| O-002/O-006/O-007 被提前决定 | 保持配置和端口占位，期限仍是 Phase 04 |
| 预计划与实际漂移 | 执行前按 R-023 重新审查 |

## 19. 阶段结束后必须更新

`AGENTS.md`、`README.md`、`docs/00-project-master.md`、`docs/02-ragflow-capability-matrix.md`、`docs/05-development-roadmap.md`、`docs/06-engineering-standards.md`、`docs/07-decisions-and-risks.md`、`docs/phases/README.md` 和本文件。

## 20. 下一阶段进入条件

Phase 02 只有在 Phase 01 DoD 完成、Agent 状态/Checkpoint 待决策已登记、Phase 02 计划基于实际包结构重新审查并由用户确认后才能执行。

## 21. 实际执行结果预留

- **实际开始/结束时间**：待执行。
- **实际变更文件**：待执行。
- **实际验证命令与结果**：待执行。
- **计划偏差及 ADR**：待执行。
- **阶段出口结论**：待执行。
