---
document_id: PHASE-01-PROJECT-SKELETON
document_role: Phase 01 可执行详细计划
status: active
phase: Phase 01
phase_name: 项目骨架
plan_status: 已确认
execution_status: 已完成
last_updated_at: "2026-07-30"
project_root: "D:/download/ragflow-agent"
ragflow_frozen_baseline_commit: "cd846cc9d4e32a19e684c59a1f302601027ef976"
---

# Phase 01：项目骨架详细计划

## 0. 文档状态与使用规则

- **计划状态**：已确认。
- **执行状态**：已完成；P01-T01 至 P01-T10 和阶段验收均通过。
- O-001、O-012 和计划确认门禁已由用户于 2026-07-30 解决；决策记录见 ADR-016。
- 执行前必须重新读取 [AGENTS](../../AGENTS.md)、[项目总纲](../00-project-master.md)、[路线图](../05-development-roadmap.md)、[工程标准](../06-engineering-standards.md)、[决策与风险](../07-decisions-and-risks.md)及实际工作区。
- 本文件现为已完成阶段的事实记录；实际状态以任务记录、当前源码、迁移、测试和阶段验收结果共同为准。

导航：[阶段索引](./README.md) · [Phase 00](./phase-00-research-and-baseline.md) · [Phase 02](./phase-02-agent-foundation.md)

## 1. 阶段目标

建立同一仓库、同一发行单元内可安装、可测试、可独立启动的模块化单体 FastAPI API 与 Ingestion Worker 骨架，落地配置、数据库、基础设施端口、日志、异常、测试和 Docker 开发环境，同时只预留第一版多租户授权上下文，不提前实现知识库业务。

## 2. 背景与必要性

Phase 00 确认目标项目仍是 greenfield；后续 Agent、领域模型和 RAG 数据面需要稳定的包结构、进程入口、依赖方向和质量命令。RAGFlow 的全局 `settings`、Quart、Peewee 和任务执行器不适合作为本项目骨架，但其 API/Worker 分进程拓扑可以提供边界证据。

## 3. Phase 00 事实依据

1. 目标目录当前是 Git 仓库，`main` 与 `origin/main` 均指向 Phase 00 基线 commit `5c015405e4c25346999cbb21736c61a87d5f8cbe`；目录只有 `AGENTS.md` 和文档，没有业务代码、依赖、迁移、测试或部署文件。
2. ADR-007 接受 Python 3.13、uv、FastAPI、PostgreSQL、SQLAlchemy 2、Alembic、Redis、MinIO/S3。
3. ADR-011 接受同仓库模块化单体和独立 Ingestion Worker；二者通过任务队列连接，不用内部 HTTP。
4. ADR-012 要求从第一版保留 `tenant_id`、`owner_id`、`visibility`、`AuthorizationContext`、`PermissionChecker`。
5. 当前没有批准直接复用的 RAGFlow 源文件。

## 4. 前置阶段与进入条件

- **前置阶段**：Phase 00，已完成。
- **执行前必须满足**：
  1. O-001 项目正式名称、发行包名、import package 的答案已提供。**已满足**。
  2. 本计划经用户确认。**已满足**。
  3. 重新检查目标目录 Git/文件状态。**已满足**：仓库已初始化，分支为 `main`，`origin` 已配置且 Phase 00 基线已推送。
  4. ADR-007、ADR-011、ADR-012 未被新决策替代。**已满足**。
  5. O-012 的 Git/CI/类型检查器选择已提供。**已满足**：GitHub Actions + `mypy`，实施分别留给 P01-T10 和 P01-T02。

## 5. 输入资料与依赖产物

- `docs/00-project-master.md` 至 `docs/07-decisions-and-risks.md`。
- Phase 00 基线、源码地图、复用清单和一致性报告。
- Python 3.13、uv、FastAPI、SQLAlchemy 2、Alembic、pytest、ruff 官方文档。
- 用户确认的项目名 `ragflow-agent`、import package `ragflow_agent`、GitHub Actions 和 `mypy`。

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
- `src/ragflow_agent/bootstrap/{api,ingestion_worker}.py`。
- `src/ragflow_agent/config/`、`observability/`、`shared/errors.py`、基础端口。
- `alembic.ini`、`migrations/`、数据库连接基础设施。
- `tests/{unit,contract,integration}/`、质量命令和 CI。
- `docker-compose.dev.yml`、`.env.example`、Docker 开发说明。
- 根 README/AGENTS 的实际执行入口更新。

## 9. 涉及的目标模块和文件

P01-T01 已将目标路径冻结为：

```text
pyproject.toml
uv.lock
src/ragflow_agent/
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
| P01-T01 | 冻结 Phase 01 执行基线与命名 | 已完成 | Phase 00 |
| P01-T02 | 建立 Python 包、依赖和质量工具 | 已完成 | P01-T01 |
| P01-T03 | 建立类型化配置与密钥边界 | 已完成 | P01-T02 |
| P01-T04 | 建立日志、Trace 与异常基础 | 已完成 | P01-T02、P01-T03 |
| P01-T05 | 建立 SQLAlchemy 与 Alembic 空基线 | 已完成 | P01-T02、P01-T03 |
| P01-T06 | 建立基础设施端口和适配器边界 | 已完成 | P01-T02、P01-T05 |
| P01-T07 | 建立 FastAPI bootstrap | 已完成 | P01-T03、P01-T04、P01-T05 |
| P01-T08 | 建立独立 Ingestion Worker bootstrap | 已完成 | P01-T03、P01-T04、P01-T06 |
| P01-T09 | 建立 Docker 开发环境 | 已完成 | P01-T05、P01-T07、P01-T08 |
| P01-T10 | 建立测试/CI 门禁并执行阶段验收 | 已完成 | P01-T01 至 P01-T09 |

## 14. 具体任务

### P01-T01：冻结 Phase 01 执行基线与命名

- **状态**：已完成
- **目标**：把用户提供的 O-001/O-012 答案写入事实源，固定项目名、发行包、import package、服务名和本阶段工具选择。
- **为什么需要**：未确认命名会污染目录、配置前缀、迁移、镜像和 Trace。
- **输入**：ADR-007、O-001、O-012、当前文件/Git 状态。
- **前置任务**：Phase 00 完成。
- **操作步骤**：重新盘点工作区；取得用户命名结论；确定类型检查器、CI 平台和 Git 仓库事实；记录 ADR/开放项；把旧包路径占位符映射为 `src/ragflow_agent`。
- **涉及文件**：`docs/07-decisions-and-risks.md`、本文件及受命名/状态事实影响的总体规划文档；`pyproject.toml` 留给 P01-T02。
- **预期输出**：命名和工具决策、确认后的路径清单。
- **RAGFlow 源码依据**：`pyproject.toml` 仅用于版本/依赖参考，不决定本项目名称。
- **实现或复用方式**：自行决策与文档化，不复用代码。
- **测试方法**：检查名称符合 Python 包规范且所有文档引用一致。
- **验证命令**：以拆分字符串构造旧占位符并检查全体 Markdown 零命中；检查 import package/发行包命名规则；检查 Git 分支、远程、HEAD 与 `origin/main`；检查本次差异不含业务代码、CI 和依赖文件。
- **验收标准**：O-001/O-012 Resolved；不存在未解释的包名或质量命令占位。
- **风险和回滚方法**：命名变更代价高；代码创建前可只回滚文档决策。
- **实际执行结果**：已核对 Git 与 Phase 00 出口；新增 ADR-016，冻结 `ragflow-agent`、`ragflow_agent`、`src/ragflow_agent`、`ragflow-agent-api`、`ragflow-agent-ingestion-worker`、`RAGFLOW_AGENT_`、GitHub Actions 与 `mypy`；同步清除规划文档中的旧包路径和类型检查器占位符。未创建 Python 包、CI、依赖或业务代码。
- **实际验证结果**：通过。Phase 00 为 `completed` 且 13 项任务均已完成；发行包名、import package 和源码路径规则检查均为 `True`；旧包路径/类型检查占位符扫描结果 `LEGACY_PLACEHOLDERS=0`；Git 检查得到分支 `main`、`HEAD=origin/main=5c015405e4c25346999cbb21736c61a87d5f8cbe`、`origin=https://github.com/haonanhu02-jpg/ragflow-agent.git`；25 个 Markdown 文件本地链接检查 `LOCAL_LINK_MISSING=0`；`git diff --check` 通过；工作树差异均为 Markdown，`NON_DOCUMENT_CHANGES=0`。
- **计划偏差**：原计划把计划中的 `pyproject.toml` 列为涉及文件；本任务按阶段边界只冻结文档事实，`pyproject.toml` 的创建和配置仍由 P01-T02 执行。

### P01-T02：建立 Python 包、依赖和质量工具

- **状态**：已完成
- **目标**：创建可安装的 `src` 布局、依赖组、锁文件和统一质量命令。
- **为什么需要**：后续所有模块需要可重复环境和稳定导入。
- **输入**：P01-T01 命名、ADR-007、工程标准第 3 节。
- **前置任务**：P01-T01。
- **操作步骤**：创建 `pyproject.toml`；设置 Python 3.13；定义 runtime/dev/parser 可选组；配置 pytest、ruff、类型检查器；生成锁文件；建立包和测试目录。
- **涉及文件**：`pyproject.toml`、`uv.lock`、`src/ragflow_agent/__init__.py`、`tests/`。
- **预期输出**：可安装空包和质量命令。
- **RAGFlow 源码依据**：`pyproject.toml` 的 Python 约束和依赖类别仅作兼容性参考。
- **实现或复用方式**：自行开发。
- **测试方法**：全新环境同步、导入、最小测试、lint 和类型检查。
- **验证命令**：`uv sync --all-groups`; `uv run python -c "import ragflow_agent"`; `uv run pytest`; `uv run ruff check .`
- **验收标准**：锁文件可重复安装；无未声明依赖。
- **风险和回滚方法**：Python 3.13 兼容失败时回退单一依赖，不擅自更换 Python 基线。
- **实际执行结果**：已创建 `pyproject.toml`、`uv.lock`、`src/ragflow_agent/__init__.py`、`tests/unit/test_package.py` 和根 `.gitignore`。发行包为 `ragflow-agent==0.1.0`，Python 约束为 `>=3.13,<3.14`；运行依赖按已接受技术栈声明 FastAPI、LangChain、LangGraph、Pydantic、SQLAlchemy/Alembic、PostgreSQL 驱动、Redis 和 S3 客户端；开发组包含 pytest、pytest-asyncio、pytest-cov、ruff 和 mypy；`parser` extra 已建立但保持空列表，等待 Phase 05 的兼容性、许可证和资源审计。`uv` 使用 Python 3.13.5 在项目 `.venv` 安装并锁定 70 个包，没有创建 FastAPI、Agent、RAG、配置或基础设施业务模块。
- **实际验证结果**：通过。`uv sync --all-groups` 成功创建项目 `.venv` 并安装 70 个锁定包；`uv run python -c "import ragflow_agent"` 通过；`uv run pytest` 得到 `1 passed`；`uv run ruff check .` 得到 `All checks passed!`；补充执行 `uv run mypy src/ragflow_agent tests` 得到 `Success: no issues found in 2 source files`，直接运行依赖导入检查通过，`uv lock --check`、`uv sync --frozen --all-groups` 和 `uv pip check` 均通过。实际解释器为 `D:/download/ragflow-agent/.venv/Scripts/python.exe`，版本 Python 3.13.5。
- **计划偏差**：为防止任务生成的 `.venv`、Python bytecode、测试/质量缓存和构建产物进入 Git，补充了根 `.gitignore`；这是 P01-T02 的工程卫生文件，不扩大业务范围。没有创建计划外业务代码。

### P01-T03：建立类型化配置与密钥边界

- **状态**：已完成
- **目标**：定义 API、Worker、数据库、队列、对象存储、搜索、模型和观测配置 Schema。
- **为什么需要**：业务模块不得直接读取环境变量或泄露密钥。
- **输入**：P01-T02、工程标准第 6 节。
- **前置任务**：P01-T02。
- **操作步骤**：定义不可变配置对象；实现 bootstrap 加载；建立开发/测试覆盖规则；生成无密钥 `.env.example`；增加配置验证错误。
- **涉及文件**：`src/ragflow_agent/config/`、`.env.example`、测试配置。
- **预期输出**：API/Worker 共用的类型化配置。
- **RAGFlow 源码依据**：`common/settings.py::init_settings` 是全局配置反例。
- **实现或复用方式**：参考后自研；明确不采用 RAGFlow settings。
- **测试方法**：必填、默认、非法值、密钥脱敏和环境覆盖单测。
- **验证命令**：`uv run pytest tests/unit/config -q`
- **验收标准**：业务包无 `os.getenv`；日志不输出密钥。
- **风险和回滚方法**：配置过度集中时拆分子 Schema；保持外部变量兼容映射。
- **实际执行结果**：已实现不可变 `AppSettings` 及 API、Worker、Database、Queue、ObjectStore、Search、Model、Observability 子配置；统一使用 `RAGFLOW_AGENT_` 前缀和双下划线嵌套覆盖；数据库 URL、队列 URL、对象存储凭据和模型 API key 使用 `SecretStr`；搜索后端保持 `unconfigured`，未提前解决 O-002/O-007。新增无真实密钥的 `.env.example` 和配置单元测试。
- **实际验证结果**：通过。`uv run pytest tests/unit/config -q` 为 `6 passed`；配置目录 ruff 通过；strict mypy 检查 3 个源文件零问题；业务包 `os.getenv` 扫描零命中。必填数据库 URL、默认值、非法端口、对象存储凭据成对校验、环境覆盖、冻结属性和密钥脱敏均有测试。
- **计划偏差**：无。为兼容 pydantic-settings 运行时 `_env_file` 参数与其 mypy dataclass transform 的签名差异，在唯一 bootstrap 包装处使用精确 `type: ignore[call-arg]` 并记录原因。

### P01-T04：建立日志、Trace 与异常基础

- **状态**：已完成
- **目标**：统一结构化日志、关联 ID、稳定错误码和异常映射。
- **为什么需要**：API、Worker、任务和后续 Agent/RAG 必须可关联诊断。
- **输入**：P01-T02、P01-T03、工程标准第 7/16 节。
- **前置任务**：P01-T02、P01-T03。
- **操作步骤**：定义 `AppError`；生成 trace/request/job ID；配置 JSON/开发日志；实现敏感字段过滤；定义基础 TraceContext。
- **涉及文件**：`src/ragflow_agent/shared/errors.py`、`observability/`、测试。
- **预期输出**：统一错误与日志基础设施。
- **RAGFlow 源码依据**：`common/token_utils.py::token_usage_sink` 和日志只作部分观测用例；不复制。
- **实现或复用方式**：自行开发。
- **测试方法**：错误映射、字段齐全、密钥脱敏、context 传播。
- **验证命令**：`uv run pytest tests/unit/observability tests/unit/shared -q`
- **验收标准**：错误有 `error_code`/`trace_id`；禁止字段不出现在日志。
- **风险和回滚方法**：日志 Schema 变更须版本化；不以记录原文解决诊断问题。
- **实际执行结果**：新增框架无关 `AppError`，包含稳定 `error_code`、HTTP 状态、trace 绑定和结构化 payload；新增不可变 `TraceContext`、ContextVar 绑定/恢复和随机关联 ID；使用标准库 logging 实现项目命名空间 JSON 日志、API/Worker service name、Trace/tenant/request/job/run 关联字段以及消息、URL 凭据和嵌套敏感字段脱敏。
- **实际验证结果**：通过。`uv run pytest tests/unit/observability tests/unit/shared -q` 为 `9 passed`；对应 ruff 通过；strict mypy 检查 8 个源文件零问题。覆盖错误映射、trace 保留、非法状态、ID 唯一性、上下文恢复、JSON 字段、logger 隔离和敏感值不泄露。
- **计划偏差**：无。当前只提供日志/Trace 基础，不记录文档原文、不接入外部观测平台。

### P01-T05：建立 SQLAlchemy 与 Alembic 空基线

- **状态**：已完成
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
- **实际执行结果**：已建立 SQLAlchemy 2 异步 engine/session factory、事务化 `session_scope`、最小 `UnitOfWork` Protocol 与 SQLAlchemy 实现；已建立 Alembic 异步迁移环境和可逆空基线 `20260730_0001`，未创建任何业务表；新增真实 PostgreSQL 连接、连接释放和事务回滚集成测试。
- **实际验证结果**：通过。临时 `postgres:17-alpine` 上连续执行 `upgrade head`、`downgrade base`、再次 `upgrade head` 成功，升级后仅存在 Alembic 自身版本表；`uv run pytest tests/integration/database -q` 为 `2 passed`；对应 ruff 与 strict mypy 检查通过且无警告。
- **计划偏差**：Windows 上 psycopg 异步驱动不支持默认 Proactor loop；迁移入口和数据库集成测试显式使用 Selector loop，并采用 pytest-asyncio 的 `pytest_asyncio_loop_factories` hook，未改变异步数据库架构。

### P01-T06：建立基础设施端口和适配器边界

- **状态**：已完成
- **目标**：建立 Queue/ObjectStore/Search/Model/Clock/ID 的最小端口位置和依赖方向。
- **为什么需要**：防止 bootstrap 或应用代码直连供应商客户端。
- **输入**：P01-T02、P01-T05、目标架构和工程标准。
- **前置任务**：P01-T02、P01-T05。
- **操作步骤**：定义基础 Protocol 和生命周期；创建仅用于测试的内存/空适配器；增加导入边界测试；不定义知识库 DTO。
- **涉及文件**：`src/ragflow_agent/shared/ports/`、`infrastructure/{queue,object_store,search,models}/`。
- **预期输出**：可 wiring 的基础设施边界。
- **RAGFlow 源码依据**：`common/settings.py`、`rag/utils/redis_conn.py` 展示耦合风险。
- **实现或复用方式**：参考后自研。
- **测试方法**：Protocol 类型、生命周期和禁止导入测试。
- **验证命令**：`uv run pytest tests/unit/import_boundaries tests/contract/foundation -q`
- **验收标准**：核心层不导入具体客户端；空适配器不伪装业务成功。
- **风险和回滚方法**：抽象过度时只保留下一阶段会消费的端口。
- **实际执行结果**：已建立 Queue、ObjectStore、Search、Model 的最小生命周期 Protocol，以及 Clock、ID 端口；Queue 仅包含 Worker 空壳需要的轮询和结算表面，并明确不承诺投递语义。已建立显式 `Unconfigured*` 适配器、测试专用 `FakeQueue`、端口契约测试和基于 AST 的依赖方向测试；未定义知识库、检索或模型调用 DTO。
- **实际验证结果**：通过。`uv run pytest tests/unit/import_boundaries tests/contract/foundation -q` 为 `8 passed`；28 个相关源文件 strict mypy 零问题；ruff 通过。
- **计划偏差**：无架构偏差。为避免把未选型的供应商适配器伪装成成功，生产占位适配器始终报告未就绪并在 `open`/业务调用时抛出稳定的 `infrastructure_not_configured` 错误；可运行内存实现严格放在 `tests/fakes/`。

### P01-T07：建立 FastAPI bootstrap

- **状态**：已完成
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
- **验证命令**：`uv run pytest tests/integration/api -q`; `uv run python -m ragflow_agent.bootstrap.api --check`
- **验收标准**：API 可独立启动，不导入 Parser/Worker。
- **风险和回滚方法**：启动副作用放入 lifespan；失败时撤回单个 wiring 变更。
- **实际执行结果**：已实现无导入副作用的 FastAPI app factory、lifespan 数据库 engine 创建/释放、`/health/live`、数据库就绪探针驱动的 `/health/ready`、稳定 `AppError` 映射和 trace middleware；已建立只从服务端可信 request state 读取身份的 `TrustedIdentity` 边界，调用方 `tenant/owner` header 不会成为可信权限上下文。新增独立 API CLI 及无基础设施副作用的 `--check`。
- **实际验证结果**：通过。`uv run pytest tests/integration/api -q` 为 `4 passed`；`uv run python -m ragflow_agent.bootstrap.api --check` 输出 `API bootstrap check passed`；API/Bootstrap ruff、strict mypy 与 Worker/Parser/RAG 禁止导入扫描通过。
- **计划偏差**：为提供 uvicorn 进程入口和无弃用警告的 FastAPI TestClient，分别新增运行时依赖 `uvicorn` 与开发依赖 `httpx2`，并更新 `uv.lock`；未引入认证供应商或 Phase 03 `AuthorizationContext`。

### P01-T08：建立独立 Ingestion Worker bootstrap

- **状态**：已完成
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
- **验证命令**：`uv run pytest tests/integration/worker -q`; `uv run python -m ragflow_agent.bootstrap.ingestion_worker --check`
- **验收标准**：Worker 无内部 HTTP、无 API route 导入、无真实任务副作用。
- **风险和回滚方法**：空循环阻塞时使用可控 poll/cancellation；保留单进程测试适配器。
- **实际执行结果**：已实现独立 `IngestionWorker` 生命周期空壳、明确状态、可观察心跳、停止领取、取消安全和队列关闭；Worker 若收到任务会以 `ingestion_not_implemented` 明确失败且不会 ACK/拒绝/处理任务。新增独立进程入口与无基础设施副作用的 `--check`，并增加启动、心跳、取消、优雅退出及 API/HTTP 禁止导入测试。
- **实际验证结果**：通过。`uv run pytest tests/integration/worker tests/unit/import_boundaries -q` 为 `6 passed`；`uv run python -m ragflow_agent.bootstrap.ingestion_worker --check` 输出 `Ingestion worker bootstrap check passed`；相关 ruff 与 strict mypy 检查通过。
- **计划偏差**：无架构偏差。具体任务库和可靠消息语义仍按 O-006 延后；因此运行入口的普通模式使用显式未配置 Queue 并会 fail-fast，只有 `--check` 不连接基础设施，未伪造可消费任务的生产适配器。

### P01-T09：建立 Docker 开发环境

- **状态**：已完成
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
- **实际执行结果**：已建立 digest 固定的非 root Python 3.13/uv 应用镜像，以及 PostgreSQL 17、Redis 8、MinIO、API 和 Worker 的开发 Compose 拓扑；API 与 Worker 使用同一镜像、不同命令。所有凭据通过 Compose 必填环境变量传入，无默认密钥；端口可覆盖；搜索后端未加入。Worker 通过显式且仅限 development 的 `--development-idle` 模式保持独立进程和健康状态，该模式不生成、ACK、拒绝或处理任务。
- **实际验证结果**：通过。`docker compose -f docker-compose.dev.yml config --quiet` 通过；全新项目名下 `up --build --wait` 成功，API、Worker、PostgreSQL、Redis、MinIO 五个容器均为 `healthy`；验证后的专用容器、网络和三个临时数据卷已按精确项目名清理。
- **计划偏差**：由于 O-006 尚未决定任务库和可靠消息语义，开发 Worker 不能连接一个伪造的可消费队列。原“占位配置”具体化为显式 development-only 非消费模式；默认 Worker 入口仍使用 `UnconfiguredQueue` fail-fast，未形成生产消息方案或搜索选型。

### P01-T10：建立测试/CI 门禁并执行阶段验收

- **状态**：已完成
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
- **验证命令**：`uv sync --frozen --all-groups`; `uv run ruff check .`; `uv run mypy src/ragflow_agent tests`; `uv run pytest`; `docker compose -f docker-compose.dev.yml config`
- **验收标准**：全部命令通过；业务能力仍未被伪实现；文档状态真实。
- **风险和回滚方法**：不降低门禁掩盖失败；逐项回滚最近配置变更。
- **实际执行结果**：已创建 GitHub Actions 质量工作流，固化冻结安装、ruff、strict mypy、密钥卫生、完整 pytest、真实 PostgreSQL 迁移往返、API/Worker bootstrap 和 Compose 配置门禁；已更新 AGENTS/README 和全部阶段出口文档。新增仓库密钥卫生脚本，扫描 tracked/untracked 非忽略文本并拒绝常见私钥、供应商 Token 和非占位凭据。
- **实际验证结果**：通过。完整本地阶段验收的锁文件、ruff、mypy、密钥扫描、完整测试、真实 PostgreSQL 迁移往返、包/直接依赖导入、API/Worker 检查、Compose 配置与五容器健康检查均通过；远程 GitHub Actions 结果在推送后记录。
- **计划偏差**：CI 使用单一 job 顺序执行门禁而未拆并行 job，以避免重复安装并保证迁移/测试共享同一 PostgreSQL 基线；不降低任何计划门禁。

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

- **实际开始/结束时间**：2026-07-30；P01-T01 至 P01-T10 当日完成。
- **实际变更文件**：建立根工程/容器/CI 文件、`src/ragflow_agent` 的配置/共享/观测/基础设施/API/Worker/bootstrap 包、Alembic 空迁移、unit/contract/integration 测试和阶段出口文档；完整清单以本阶段提交为准。
- **实际验证命令与结果**：`uv sync --frozen --all-groups`、ruff、strict mypy、完整 pytest、密钥扫描、真实 PostgreSQL Alembic 往返、API/Worker bootstrap、Docker Compose 配置/构建/五容器健康和文档一致性检查全部通过。
- **计划偏差及 ADR**：未新增架构 ADR；记录 Windows Selector loop、development-only 非消费 Worker、CI 单 job 三项实施偏差，O-002/O-006/O-007 保持 Deferred。
- **阶段出口结论**：Phase 01 满足 DoD 并完成；Phase 02 详细计划必须基于实际骨架复审并由用户确认，不在本轮执行。
