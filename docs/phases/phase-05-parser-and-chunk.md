---
document_id: PHASE-05-PARSER-AND-CHUNK
document_role: Phase 05 预规划详细计划
status: draft
phase: Phase 05
phase_name: Parser与Chunk
plan_status: 预规划草案
execution_status: 未执行
last_updated_at: "2026-07-30"
ragflow_frozen_baseline_commit: "cd846cc9d4e32a19e684c59a1f302601027ef976"
---

# Phase 05：Parser与Chunk详细计划

## 0. 状态与导航

- **计划状态**：预规划草案。
- **执行状态**：未执行。
- Phase 04 后必须按真实 ParsedDocument、ChunkRecord、index metadata 和资源 Profile 重审。
- 导航：[阶段索引](./README.md) · [Phase 04](./phase-04-minimum-rag.md) · [Phase 06](./phase-06-online-retrieval.md) · [复用策略](../04-code-reuse-strategy.md)

## 1. 目标、必要性和 Phase 00 依据

完成 PDF、DOCX、PPTX、XLSX、TXT、Markdown、HTML 和图片解析，OCR、表格结构、场景 Chunk Method、Parser/Chunk 策略映射和来源元数据保留；所有 RAGFlow 派生实现隔离在 `ragflow_adapters`。

Phase 00 证明 DeepDOC/`rag/app` 具备高价值复杂解析和场景分块，但依赖 settings、tokenizer、模型资源、原生库和全局服务，不能直接复制。Phase 09 将独立实施自动关键词、自动问题、生成式摘要/TOC 和父子 Chunk；本阶段只稳定基础 Parser/Chunk、原文结构和增强扩展点，避免重复实现。

## 2. 前置、输入、范围和排除

- **前置阶段**：Phase 04。
- **进入条件**：Minimum RAG 真实闭环通过；O-004 在首次抽取前解决；Parser/OCR 模型和可选依赖许可完成门禁；本计划复审确认。
- **输入**：ParsedDocument/Chunk 契约、基础 pipeline、格式黄金样本、资源预算、RAGFlow 复用登记。

**范围**：格式识别；8 类目标输入；OCR/版面/表格；Parser registry；Chunker registry；naive/paper/book/manual/laws/qa/table/resume/picture 等明确策略的适用映射；页码/bbox/heading/table/image/source_order 元数据；资源、超时、临时文件和降级。

**排除**：自动关键词、自动问题、生成摘要、生成 TOC、父子 Chunk 实施；音频/视频跨模态检索；GraphRAG/RAPTOR；在线融合/Rerank。

## 3. 交付物和目标模块

```text
src/ragflow_agent/knowledge/infrastructure/
  parsers/{text,markdown,html,docx,pptx,xlsx,pdf,image}/
  ragflow_adapters/{parsing,chunking,vision}/
  chunkers/{general,paper,book,manual,laws,qa,table,resume,picture}/
src/ragflow_agent/knowledge/application/parser_registry.py
src/ragflow_agent/knowledge/application/chunker_registry.py
tests/{contract,golden,integration,performance}/parsing/
```

交付 Parser/Chunk 注册表、格式策略矩阵、黄金数据、资源 Profile、许可证/provenance、Adapter 边界测试。

## 4. RAGFlow 源码、调用关系与复用方式

| 能力 | 源码/符号 | 采用 |
|---|---|---|
| 路由 | `chunk_builder.py::get_parser/run_chunking` | 参考 registry；自研 |
| PDF | `deepdoc/parser/pdf_parser.py::{RAGFlowPdfParser,PlainParser,VisionParser}` | 经 `ragflow_adapters` 改造候选，极高难度 |
| DOCX/PPTX/XLSX | `deepdoc/parser/{docx,ppt,excel}_parser.py` | 分文件许可证/依赖实验后改造候选 |
| OCR/版面/表格 | `deepdoc/vision/{ocr,layout_recognizer,table_structure_recognizer}.py` | 隔离模型资源后改造候选 |
| 文本/场景 Chunk | `rag/app/{naive,paper,book,manual,laws,qa,table,resume,picture}.py::chunk` | 简单策略参考重写；复杂规则改造候选 |
| 后处理扩展点 | `chunk_post_processor.py` | 本阶段只定义接口，不执行自动增强 |

- **直接复用**：无。
- **`ragflow_adapters` 改造复用**：经 O-004/许可/资源实验批准的 DeepDOC Parser、Vision 和复杂 Chunk 规则。
- **参考后自研**：简单文本/HTML Parser、registry、策略映射、稳定 ID、资源治理。
- **明确不采用**：`common.settings`、Peewee、RAGFlow tokenizer 全局状态、Parser 直接写数据库/索引。

## 5. 框架与自研职责

- **LangGraph**：不参与 Parser/Chunk 数据面。
- **LangChain**：简单 Loader/Token splitter 适配和模型接口；不作为统一领域结构。
- **自研**：注册表、契约映射、策略选择、元数据/稳定 ID、资源治理、错误和黄金测试。

## 6. 任务总表

| 任务 | 名称 | 状态 | 前置 |
|---|---|---|---|
| P05-T01 | 复审复用、许可、样本与资源门禁 | 未开始 | Phase 04 |
| P05-T02 | 实现 Parser/Chunk 注册表与策略映射 | 未开始 | P05-T01 |
| P05-T03 | 实现 TXT、Markdown 与 HTML Parser | 未开始 | P05-T02 |
| P05-T04 | 实现 DOCX Parser | 未开始 | P05-T01、P05-T02 |
| P05-T05 | 实现 PPTX Parser | 未开始 | P05-T01、P05-T02 |
| P05-T06 | 实现 XLSX 与表格 Parser | 未开始 | P05-T01、P05-T02 |
| P05-T07 | 实现 PDF 文本、版面与表格 Parser | 未开始 | P05-T01、P05-T02 |
| P05-T08 | 实现图片与 OCR Parser | 未开始 | P05-T01、P05-T02 |
| P05-T09 | 实现场景 Chunk Method 集 | 未开始 | P05-T03 至 P05-T08 |
| P05-T10 | 固化元数据、稳定 ID 与降级协议 | 未开始 | P05-T03 至 P05-T09 |
| P05-T11 | 建立黄金、契约与资源测试 | 未开始 | P05-T03 至 P05-T10 |
| P05-T12 | 集成 ingestion 并执行阶段验收 | 未开始 | P05-T01 至 P05-T11 |

## 7. 具体任务

### P05-T01：复审复用、许可、样本与资源门禁

- **状态**：未开始
- **目标**：逐文件决定改造复用/参考重写并确认样本、模型、原生库和 CPU/GPU Profile。
- **为什么需要**：复杂 Parser 的许可证和资源风险可能阻止抽取。
- **输入**：Phase 04 实际契约、46 行复用清单、O-004。
- **前置任务**：Phase 04 完成。
- **操作步骤**：import graph/资源清单；核查 Apache-2.0 和第三方许可；最小隔离 probe；确定首批 OCR/Layout/Table 模型；登记 provenance；修订任务。
- **涉及文件**：`docs/04-code-reuse-strategy.md`、`07-decisions-and-risks.md`、实验测试。
- **预期输出**：逐文件批准/拒绝清单。
- **RAGFlow 源码依据**：`deepdoc/parser/`、`deepdoc/vision/`、`rag/app/`。
- **实现或复用方式**：审计；未经批准不复制。
- **测试方法**：隔离 import、模型加载、内存/耗时、许可证扫描。
- **验证命令**：按实际候选记录；不得预填通过。
- **验收标准**：每个候选有 commit/path/symbol/license/依赖/目标 Adapter。
- **风险和回滚方法**：不明许可即拒绝复制，改为参考重写/替代库。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待记录。

### P05-T02：实现 Parser/Chunk 注册表与策略映射

- **状态**：未开始
- **目标**：根据 MIME、扩展名、场景和显式配置选择 Parser/Chunker。
- **为什么需要**：禁止格式判断散落在 API/Worker。
- **输入**：P05-T01、Phase 04 pipeline。
- **前置任务**：P05-T01。
- **操作步骤**：定义 capability/priority；验证配置；无支持时稳定错误；建立格式→Parser→默认 Chunk Method 明确表。
- **涉及文件**：`parser_registry.py`、`chunker_registry.py`、测试。
- **预期输出**：可扩展注册表和映射。
- **RAGFlow 源码依据**：`chunk_builder.get_parser/run_chunking`。
- **实现或复用方式**：参考后自研。
- **测试方法**：每种格式/场景、冲突、显式 override、未知类型。
- **验证命令**：`uv run pytest tests/unit/parsing/test_registry.py -q`
- **验收标准**：映射确定性、可追踪，不静默错误降级。
- **风险和回滚方法**：默认策略只回到 General，不改变格式解析结果。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待记录。

### P05-T03：实现 TXT、Markdown 与 HTML Parser

- **状态**：未开始
- **目标**：保留编码、标题层级、列表、表格和来源顺序。
- **为什么需要**：建立无模型依赖的稳定格式基线。
- **输入**：P05-T02、黄金样本。
- **前置任务**：P05-T02。
- **操作步骤**：编码检测；Markdown AST/HTML 清理；标题路径；表格/链接；安全限制；映射 ParsedBlock。
- **涉及文件**：`parsers/{text,markdown,html}/`、fixtures。
- **预期输出**：三类 Parser。
- **RAGFlow 源码依据**：`rag/app/naive.py` 只作文本用例。
- **实现或复用方式**：标准库/成熟库 + 自研适配。
- **测试方法**：编码、脚本清理、嵌套标题、表格、超大文档。
- **验证命令**：`uv run pytest tests/golden/parsing/test_text_markdown_html.py -q`
- **验收标准**：结构/元数据黄金输出稳定。
- **风险和回滚方法**：第三方 AST 升级锁版本，黄金测试阻止漂移。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待记录。

### P05-T04：实现 DOCX Parser

- **状态**：未开始
- **目标**：解析段落、标题、表格、图片锚点和页/节可得信息。
- **为什么需要**：企业手册和工单常见格式。
- **输入**：P05-T01、P05-T02、DOCX 黄金样本。
- **前置任务**：P05-T01、P05-T02。
- **操作步骤**：选择标准库/Adapter；处理段落顺序、样式层级、表格、图片；资源限制；映射 warnings。
- **涉及文件**：`parsers/docx/` 或 `ragflow_adapters/parsing/docx.py`。
- **预期输出**：DOCX Parser。
- **RAGFlow 源码依据**：`deepdoc/parser/docx_parser.py::RAGFlowDocxParser`。
- **实现或复用方式**：经批准改造复用或参考重写。
- **测试方法**：标题/表格/图片/损坏包/宏风险。
- **验证命令**：`uv run pytest tests/golden/parsing/test_docx.py -q`
- **验收标准**：顺序和来源可追溯；无上游全局依赖。
- **风险和回滚方法**：Adapter 失败回退标准库能力并明确 warning。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待记录。

### P05-T05：实现 PPTX Parser

- **状态**：未开始
- **目标**：解析 slide 文本、标题、表格、图片及顺序。
- **为什么需要**：运维培训和方案资料大量使用演示文稿。
- **输入**：P05-T01、P05-T02、PPTX 样本。
- **前置任务**：P05-T01、P05-T02。
- **操作步骤**：按 slide/shape 顺序解析；保留 slide 编号和 bbox；表格/图片；明确 notes 是否支持；降级。
- **涉及文件**：`parsers/pptx/` 或 `ragflow_adapters/parsing/pptx.py`。
- **预期输出**：PPTX Parser。
- **RAGFlow 源码依据**：`deepdoc/parser/ppt_parser.py::RAGFlowPptParser`；冻结源码未确认 notes 专用输出。
- **实现或复用方式**：经批准改造或参考重写。
- **测试方法**：多版式、表格、图片、隐藏 slide、空 slide。
- **验证命令**：`uv run pytest tests/golden/parsing/test_pptx.py -q`
- **验收标准**：不把未支持 notes 描述成已解析。
- **风险和回滚方法**：unsupported 元素记录 warning，不返回空成功。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待记录。

### P05-T06：实现 XLSX 与表格 Parser

- **状态**：未开始
- **目标**：解析 worksheet、区域、表头、单元格类型和合并关系。
- **为什么需要**：结构化运维记录和清单需要表格保真。
- **输入**：P05-T01、P05-T02、XLSX/复杂表格样本。
- **前置任务**：P05-T01、P05-T02。
- **操作步骤**：限制 sheet/row/cell；处理公式值策略；合并单元格；表格 ParsedBlock；防公式注入。
- **涉及文件**：`parsers/xlsx/` 或 `ragflow_adapters/parsing/excel.py`。
- **预期输出**：XLSX/Table Parser。
- **RAGFlow 源码依据**：`deepdoc/parser/excel_parser.py::RAGFlowExcelParser`、`table_parser.py`。
- **实现或复用方式**：经批准改造/标准库适配。
- **测试方法**：多 sheet、合并、公式、日期、空行、超大表。
- **验证命令**：`uv run pytest tests/golden/parsing/test_xlsx.py -q`
- **验收标准**：类型、表头和来源位置可追溯。
- **风险和回滚方法**：超限拒绝或分批；不执行公式/宏。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待记录。

### P05-T07：实现 PDF 文本、版面与表格 Parser

- **状态**：未开始
- **目标**：处理可选中文本 PDF 的页、段落、bbox、阅读顺序和表格。
- **为什么需要**：复杂 PDF 是 RAGFlow 核心价值来源。
- **输入**：P05-T01、P05-T02、复杂 PDF 黄金集。
- **前置任务**：P05-T01、P05-T02。
- **操作步骤**：文本提取；版面/顺序；表格识别；页码/bbox；扫描页路由 OCR；超时/内存/临时文件；provenance。
- **涉及文件**：`parsers/pdf/`、`ragflow_adapters/parsing/pdf.py`。
- **预期输出**：PDF Parser Profile。
- **RAGFlow 源码依据**：`pdf_parser.py::{RAGFlowPdfParser,PlainParser,VisionParser}`。
- **实现或复用方式**：批准后经 Adapter 改造；否则分层替代。
- **测试方法**：多栏、页眉页脚、表格、混排、加密/损坏、资源。
- **验证命令**：`uv run pytest tests/golden/parsing/test_pdf.py tests/performance/parsing/test_pdf_limits.py -q`
- **验收标准**：阅读顺序和坐标达到黄金阈值；失败可诊断。
- **风险和回滚方法**：按 parser profile 回退 Plain/OCR，不静默丢页。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待记录。

### P05-T08：实现图片与 OCR Parser

- **状态**：未开始
- **目标**：对图片/扫描页执行 OCR、版面/表格处理并保留坐标。
- **为什么需要**：轨道交通图片和扫描文档无法只靠文本提取。
- **输入**：P05-T01、P05-T02、OCR 模型和图片集。
- **前置任务**：P05-T01、P05-T02。
- **操作步骤**：图片验证/解码；OCR/布局/表格端口；方向/缩放；置信度/warning；模型生命周期和批次。
- **涉及文件**：`parsers/image/`、`ragflow_adapters/vision/`。
- **预期输出**：图片/OCR Parser。
- **RAGFlow 源码依据**：`deepdoc/vision/ocr.py`、`layout_recognizer.py`、`table_structure_recognizer.py`。
- **实现或复用方式**：隔离模型资源后改造候选。
- **测试方法**：中英、低清、旋转、表格、恶意图片、GPU/CPU。
- **验证命令**：`uv run pytest tests/golden/parsing/test_image_ocr.py tests/performance/parsing/test_ocr_limits.py -q`
- **验收标准**：字符/版面/表格指标和资源上限达标。
- **风险和回滚方法**：模型不可用返回明确降级/失败，不伪造空文本。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待记录。

### P05-T09：实现场景 Chunk Method 集

- **状态**：未开始
- **目标**：实现 General、Paper、Book、Manual、Laws、QA、Table、Resume、Picture 的明确策略。
- **为什么需要**：不同结构需要不同边界和上下文。
- **输入**：P05-T03 至 P05-T08、场景黄金集。
- **前置任务**：P05-T03 至 P05-T08。
- **操作步骤**：逐策略定义输入/配置；章节/表格/QA 边界；Token/重叠；稳定 ID；注册映射；每策略独立黄金测试。
- **涉及文件**：`chunkers/`、`ragflow_adapters/chunking/`。
- **预期输出**：场景 Chunker 集。
- **RAGFlow 源码依据**：`rag/app/{naive,paper,book,manual,laws,qa,table,resume,picture}.py::chunk`。
- **实现或复用方式**：简单策略参考重写，复杂规则按批准改造。
- **测试方法**：每策略黄金输出、Token、重叠、表图上下文。
- **验证命令**：`uv run pytest tests/golden/chunking -q`
- **验收标准**：每种策略有独立验收；不使用“类似策略”代替。
- **风险和回滚方法**：策略版本升级产生新 index_version。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待记录。

### P05-T10：固化元数据、稳定 ID 与降级协议

- **状态**：未开始
- **目标**：统一跨格式来源字段、Chunk ID、warnings 和 parser/chunker version。
- **为什么需要**：Phase 06 检索过滤和 Citation 依赖稳定元数据。
- **输入**：P05-T03 至 P05-T09。
- **前置任务**：P05-T03 至 P05-T09。
- **操作步骤**：定义规范化规则；元数据 allowlist；source block 映射；版本摘要；降级原因；兼容 Phase 04 索引。
- **涉及文件**：领域/Adapter 映射、Schema、测试。
- **预期输出**：元数据/ID 协议 v2（如需）。
- **RAGFlow 源码依据**：positions/tables/images 和 Chunk 字段用例。
- **实现或复用方式**：自行开发。
- **测试方法**：跨格式 Schema、稳定性、版本变化、敏感元数据。
- **验证命令**：`uv run pytest tests/contract/parsing/test_metadata.py -q`
- **验收标准**：所有目标格式满足同一契约。
- **风险和回滚方法**：破坏性字段变化保留转换器并重建索引。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待记录。

### P05-T11：建立黄金、契约与资源测试

- **状态**：未开始
- **目标**：建立格式/策略可重复质量和资源门禁。
- **为什么需要**：Parser 版本漂移、模型变化和复杂样本最易引起回归。
- **输入**：P05-T03 至 P05-T10。
- **前置任务**：P05-T03 至 P05-T10。
- **操作步骤**：版本化样本来源/许可；黄金输出；结构指标；CPU/GPU/内存/时间上限；临时文件清理；并发。
- **涉及文件**：`tests/golden/`、`tests/performance/`、报告。
- **预期输出**：Parser/Chunk 质量基线。
- **RAGFlow 源码依据**：无新增。
- **实现或复用方式**：自行开发评测。
- **测试方法**：golden diff、资源监控、错误注入。
- **验证命令**：`uv run pytest tests/golden/parsing tests/golden/chunking tests/performance/parsing -q`
- **验收标准**：所有格式/策略有黄金和资源结果。
- **风险和回滚方法**：禁止无审查更新黄金；模型升级独立基线。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待记录。

### P05-T12：集成 ingestion 并执行阶段验收

- **状态**：未开始
- **目标**：让全部格式/策略通过统一 Worker pipeline 和索引闭环。
- **为什么需要**：单独 Parser 通过不等于 ingestion 可用。
- **输入**：P05-T01 至 P05-T11。
- **前置任务**：P05-T01 至 P05-T11。
- **操作步骤**：E2E 上传/解析/Chunk/索引；检查 tenant/进度/错误；运行门禁；更新 provenance/文档/矩阵。
- **涉及文件**：pipeline、E2E、总体文档、本文件。
- **预期输出**：Phase 05 验收报告。
- **RAGFlow 源码依据**：核对所有 Adapter 仍隔离，不导入 settings/Peewee。
- **实现或复用方式**：集成与审计。
- **测试方法**：每格式真实 E2E、资源、跨租户、失败。
- **验证命令**：`uv run pytest tests/e2e/parsing tests/golden tests/contract/parsing -q`
- **验收标准**：CAP-01 至 CAP-04 基础/完整范围按真实结果验收；自动增强仍未实现。
- **风险和回滚方法**：任何高风险格式可默认关闭，但状态必须真实。
- **实际执行结果**：待执行。
- **实际验证结果**：待执行。
- **计划偏差**：待记录。

## 8. 阶段验收、DoD、风险与后续

**验收/DoD**：P05-T01 至 P05-T12 完成；8 类目标输入、OCR、表格和明确 Chunk 策略均有黄金/资源/E2E；metadata/Citation 来源稳定；所有上游代码有 provenance 且只从 `ragflow_adapters` 进入；自动增强未误标实现；总体文档同步。

| 风险 | 处理 |
|---|---|
| 模型/原生库许可 | 分层登记，不明则不复制/不分发 |
| GPU/内存过高 | 可选 Profile、批次/超时/并发限制 |
| Parser 输出漂移 | 黄金样本与版本锁定 |
| 临时文件/恶意文档 | 沙箱边界、大小/时间/清理门禁 |
| 与 Phase 09 重复 | 本阶段只做基础结构和扩展点 |

阶段结束更新总纲、架构、矩阵、复用、路线图、标准、风险、状态索引和本文件。Phase 06 需基于实际 metadata/Chunk/Citation 重审后执行。

## 9. 实际执行结果预留

- 实际批准复用清单：待执行。
- 实际格式/策略/模型与资源结果：待执行。
- 实际测试命令和偏差：待执行。
- 阶段出口结论：待执行。

