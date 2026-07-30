# Codex 项目操作入口

## 每次进入项目

1. 首先读取 `docs/00-project-master.md`，以其目标、范围、当前阶段和事实优先级为准。
2. 确认当前阶段后，读取对应的 `docs/phases/phase-xx-xxx.md`；当前任务还应读取该文件引用的专项文档。
3. 检查 Git 状态和当前源码，不能只相信文档。仓库存在 Git 元数据时执行 `git status --short`；不存在时明确记录并直接检查实际文件。
4. 修改前确认当前任务编号、依赖任务、阶段范围、允许修改的文件和验收标准。没有任务编号时，不得擅自归入其他任务或阶段。

## 实施规则

- 严格区分事实、决策、规划、待确认、范围外和风险；不得把规划能力描述成已实现。
- RAGFlow 结论必须提供冻结 commit、源码路径、类或函数及必要调用关系。
- RAGFlow 复用代码必须经过 `ragflow_adapters` 或已经通过 ADR 确认的隔离层，禁止让 RAGFlow 内部依赖污染领域层。
- Agent 流程、状态、路由、循环、重试、Checkpoint、HITL 和多 Agent 编排优先使用 LangGraph。
- LangChain 负责模型、Embedding、Retriever、Tool、Prompt、结构化输出和标准接口适配。
- 不得在没有明确必要性和证据时，重新实现 RAGFlow 已具备且适合复用的复杂能力。
- 保留用户已有修改，不覆盖无关文件，不提前实施后续阶段。
- 影响项目架构、范围或关键责任边界的决策，必须先更新 `docs/07-decisions-and-risks.md`。

## 任务完成

1. 执行与风险相称的单元、契约、集成或文档一致性测试，并记录实际命令和结果。
2. 更新当前阶段文件中的任务状态和验收结果；未执行的验证不得标记通过。
3. 同步更新受影响的专项文档。
4. 当前阶段完成时，同步更新：
   - `docs/00-project-master.md`
   - `docs/05-development-roadmap.md`
   - `docs/02-ragflow-capability-matrix.md`
5. Python 变更至少执行 `uv run ruff check .`、`uv run mypy src/ragflow_agent tests` 和 `uv run pytest`；迁移、API、Worker 或容器变更还要执行当前阶段文件规定的专项命令。
