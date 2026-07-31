---
document_id: PHASE-05-PARSER-AND-CHUNK
document_role: Phase 05 已确认详细计划与执行记录
status: active
phase: Phase 05
phase_name: Parser与Chunk
plan_status: 已确认
execution_status: 已完成
last_updated_at: "2026-07-31"
ragflow_frozen_baseline_commit: "cd846cc9d4e32a19e684c59a1f302601027ef976"
---

# Phase 05：Parser与Chunk详细计划

## 0. 状态与导航

- **计划状态**：已复审并确认。
- **执行状态**：已完成；P05-T01 至 P05-T12 均已实现并通过本地、真实基础设施和 CI 阶段门禁。
- **准入复核**：Phase 04、真实后端验收、Git/CI 和用户计划确认均通过；不存在实质架构或许可证阻塞。
- Phase 04/05 都不复制、抽取或改写 RAGFlow 源码；ADR-020 与专项基线冻结独立实现、第三方依赖、样本和资源边界。
- 导航：[阶段索引](./README.md) · [Phase 04](./phase-04-minimum-rag.md) · [Phase 06](./phase-06-online-retrieval.md) · [复用策略](../04-code-reuse-strategy.md)

## 1. 目标、必要性和 Phase 00 依据

完成 PDF、DOCX、PPTX、XLSX、TXT、Markdown、HTML 和图片解析，OCR、表格结构、场景 Chunk Method、Parser/Chunk 策略映射和来源元数据保留；所有 RAGFlow 派生实现隔离在 `ragflow_adapters`。

Phase 00 证明 DeepDOC/`rag/app` 具备高价值复杂解析和场景分块，但依赖 settings、tokenizer、模型资源、原生库和全局服务，不能直接复制。Phase 09 将独立实施自动关键词、自动问题、生成式摘要/TOC 和父子 Chunk；本阶段只稳定基础 Parser/Chunk、原文结构和增强扩展点，避免重复实现。

## 2. 前置、输入、范围和排除

- **前置阶段**：Phase 04。
- **进入 P05-T01 条件**：Minimum RAG 真实闭环已通过；本计划按 Phase 04 实际结果复审并由用户确认。
- **进入 P05-T02 条件**：P05-T01 已逐文件决定独立实现/参考重写/改造复用，任何源码抽取已重新解决 O-004，Parser/OCR 模型、可选依赖、黄金样本和 CPU/GPU 资源门禁已记录并通过。
- **输入**：ParsedDocument/Chunk 契约、基础 pipeline、格式黄金样本、资源预算、RAGFlow 复用登记。

**范围**：格式识别；8 类目标输入；OCR/版面/表格；Parser registry；Chunker registry；naive/paper/book/manual/laws/qa/table/resume/picture 等明确策略的适用映射；页码/bbox/heading/table/image/source_order 元数据；资源、超时、临时文件和降级。

**排除**：自动关键词、自动问题、生成摘要、生成 TOC、父子 Chunk 实施；音频/视频跨模态检索；GraphRAG/RAPTOR；在线融合/Rerank。

## 3. 交付物和目标模块

```text
src/ragflow_agent/knowledge/infrastructure/
  parsers/{text,markdown,html,docx,pptx,xlsx,pdf,image}.py
  ocr/tesseract.py
  chunking/{general,scenario}.py
src/ragflow_agent/knowledge/application/parser_registry.py
src/ragflow_agent/knowledge/application/chunker_registry.py
tests/{contract,golden,integration,performance}/parsing/
```

交付 Parser/Chunk 注册表、格式策略矩阵、黄金数据、资源 Profile、许可证/provenance、Adapter 边界测试。由于实际 RAGFlow 复用为零，本阶段未创建空 `ragflow_adapters` 目录。

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
- **`ragflow_adapters` 改造复用**：无获批文件；实际数量为零。
- **参考后自研**：简单文本/HTML Parser、registry、策略映射、稳定 ID、资源治理。
- **明确不采用**：`common.settings`、Peewee、RAGFlow tokenizer 全局状态、Parser 直接写数据库/索引。

## 5. 框架与自研职责

- **LangGraph**：不参与 Parser/Chunk 数据面。
- **LangChain**：简单 Loader/Token splitter 适配和模型接口；不作为统一领域结构。
- **自研**：注册表、契约映射、策略选择、元数据/稳定 ID、资源治理、错误和黄金测试。

## 6. 任务总表

| 任务 | 名称 | 状态 | 前置 |
|---|---|---|---|
| P05-T01 | 复审复用、许可、样本与资源门禁 | 已完成 | Phase 04 |
| P05-T02 | 实现 Parser/Chunk 注册表与策略映射 | 已完成 | P05-T01 |
| P05-T03 | 实现 TXT、Markdown 与 HTML Parser | 已完成 | P05-T02 |
| P05-T04 | 实现 DOCX Parser | 已完成 | P05-T01、P05-T02 |
| P05-T05 | 实现 PPTX Parser | 已完成 | P05-T01、P05-T02 |
| P05-T06 | 实现 XLSX 与表格 Parser | 已完成 | P05-T01、P05-T02 |
| P05-T07 | 实现 PDF 文本、版面与表格 Parser | 已完成 | P05-T01、P05-T02 |
| P05-T08 | 实现图片与 OCR Parser | 已完成 | P05-T01、P05-T02 |
| P05-T09 | 实现场景 Chunk Method 集 | 已完成 | P05-T03 至 P05-T08 |
| P05-T10 | 固化元数据、稳定 ID 与降级协议 | 已完成 | P05-T03 至 P05-T09 |
| P05-T11 | 建立黄金、契约与资源测试 | 已完成 | P05-T03 至 P05-T10 |
| P05-T12 | 集成 ingestion 并执行阶段验收 | 已完成 | P05-T01 至 P05-T11 |

## 7. 具体任务

### P05-T01：复审复用、许可、样本与资源门禁

- **状态**：已完成
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
- **实际执行结果**：ADR-020 决定八类 Parser、OCR Adapter、Registry 与九种 Chunk Method 全部独立实现，RAGFlow 直接/改造复用为零；新增 `docs/research/phase-05-parser-license-and-resource-baseline.md`，逐项冻结 RAGFlow import graph、第三方依赖/许可证、Tesseract `eng+chi_sim`、黄金样本 provenance、OOXML/PDF/图片/XLSX 资源上限和失败语义。`pyproject.toml`/`uv.lock` 已加入并锁定纯解析依赖，未安装全局 Python 包或模型。
- **实际验证结果**：`uv lock`、`uv sync --frozen --all-groups`、`uv pip check` 和 beautifulsoup4/charset-normalizer/python-docx/markdown-it-py/openpyxl/pdfplumber/Pillow/python-pptx/pypdfium2/pytesseract import probe 通过；RAGFlow 本地快照逐文件 import 核对确认 DeepDOC Vision 仍依赖 settings、tokenizer、ONNX/OpenCV 和模型下载。
- **计划偏差**：不执行原草案的 RAGFlow 抽取 probe，因为用户和 ADR-020 已明确禁止复制；以第三方库兼容 probe 和独立实现替代。GPU Profile 不进入 Phase 05，OCR 采用 CPU Tesseract 外部进程。

### P05-T02：实现 Parser/Chunk 注册表与策略映射

- **状态**：已完成
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
- **实际执行结果**：新增 `BinaryParserPort`、`ParserCapability`、`ParserRegistry` 与 `ChunkerRegistry`；MIME、扩展名、显式 override 和 Parser 推荐 Chunk Method 均为确定性路由，未知、冲突和不兼容输入使用稳定错误码。
- **实际验证结果**：`pytest tests/unit/parsing/test_registry.py -q` 通过；源码 Ruff 与 strict mypy 通过。
- **计划偏差**：目标文件采用现有模块约定的 `knowledge/infrastructure/parsers/*.py` 与 `knowledge/infrastructure/chunking/*.py`，没有创建同义 `chunkers/` 目录。

### P05-T03：实现 TXT、Markdown 与 HTML Parser

- **状态**：已完成
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
- **实际执行结果**：实现 TXT 编码检测与 warning、CommonMark heading/list/code/table 解析、HTML 主动内容移除以及 heading/table/image provenance；三类输出统一为 schema v2 `ParsedBlock`。
- **实际验证结果**：`pytest tests/golden/parsing/test_format_parsers.py -q` 通过，HTML 脚本清理和图片来源断言通过。
- **计划偏差**：三类格式合并到同一黄金测试文件，避免重复生成相同样本工厂；能力与验收范围未缩减。

### P05-T04：实现 DOCX Parser

- **状态**：已完成
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
- **实际执行结果**：使用 `python-docx` 独立实现段落/标题/表格/图片锚点顺序映射，并在打开 OOXML 前检查条目数、解压大小和压缩比。
- **实际验证结果**：生成式 DOCX 黄金、结构断言、OOXML 攻击门禁和 4 worker/8 次并发可重复性测试通过。
- **计划偏差**：DOCX 没有可靠页码概念，未伪造页码；图片保留包内关系路径而不提取或持久化二进制。

### P05-T05：实现 PPTX Parser

- **状态**：已完成
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
- **实际执行结果**：使用 `python-pptx` 独立实现 slide/shape 顺序、标题、文本、表格、图片和 normalized bbox；空尺寸 shape 不生成伪造 bbox。
- **实际验证结果**：生成式 PPTX 黄金测试验证 heading/text/table、slide 编号、顺序和 bbox；OOXML 资源门禁共用测试通过。
- **计划偏差**：notes 明确不在基线输出中，以 warning 记录能力边界；隐藏 slide 不被宣称为特殊处理。

### P05-T06：实现 XLSX 与表格 Parser

- **状态**：已完成
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
- **实际执行结果**：使用 `openpyxl` 以只读/不执行宏的方式输出每 worksheet 的表格块，保留 sheet heading、字面公式、日期/布尔类型，并对公式未计算和 merged cells 给出 warning；增加 sheet/row/non-empty-cell 上限。
- **实际验证结果**：XLSX 黄金测试确认表头、公式字面值、合并单元格 warning 和统一 `TableMetadata`；资源限制契约通过。
- **计划偏差**：不计算公式、不展开合并单元格语义，避免执行不可信内容；该降级是显式 warning。

### P05-T07：实现 PDF 文本、版面与表格 Parser

- **状态**：已完成
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
- **实际执行结果**：使用 `pdfplumber` 提取 native word/table 与 page-points bbox，按视觉坐标形成稳定行顺序；无 native 内容页使用 `pypdfium2` 渲染并经 OCR Port 处理；页数和渲染像素受限。
- **实际验证结果**：生成式 native PDF 的文本、表格、页码、bbox 黄金测试以及 blank scanned-page OCR fallback/warning 契约通过。
- **计划偏差**：复杂多栏语义版面模型和页眉页脚分类未实现，不把坐标排序描述为模型版面识别；这部分仍是后续增强风险。

### P05-T08：实现图片与 OCR Parser

- **状态**：已完成
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
- **实际执行结果**：新增内部 `OcrEnginePort` 和外部 Tesseract Adapter；图片在 EXIF 方向归一、格式验证和像素门禁后返回 image block、OCR 行、pixel bbox 与置信度；无文本/缺引擎/缺语言均稳定失败。
- **实际验证结果**：Static OCR 只验证 Parser 集成；GitHub Actions 安装 Tesseract `eng`/`chi_sim` 并强制执行真实英文 OCR、语言包和 bbox 测试。Fake 结果未标记为真实 OCR。
- **计划偏差**：不引入 GPU/模型版面/表格识别；Phase 05 CPU baseline 只承诺 Tesseract OCR 与确定性行分组。

### P05-T09：实现场景 Chunk Method 集

- **状态**：已完成
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
- **实际执行结果**：实现 General、Paper、Book、Manual、Laws、QA、Table、Resume、Picture 九种独立策略；场景策略以 heading/article/Q&A/table row/image-page 边界分组，统一 token 上限、overlap、来源块和策略版本。
- **实际验证结果**：`pytest tests/contract/parsing/test_metadata_and_chunking.py -q` 对九种策略逐项验证稳定 ID、顺序、来源、parser/chunker 元数据，并单独验证 Table header repeat 与 QA pairing。
- **计划偏差**：采用契约测试而非提交大体积黄金 Chunk 文件；算法是依据公开行为独立实现的 Phase 05 基线，不声称与 RAGFlow 逐字节等价。

### P05-T10：固化元数据、稳定 ID 与降级协议

- **状态**：已完成
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
- **实际执行结果**：`ParsedDocument`/`ChunkRecord` 升至 schema v2；保留 parser/source/warnings、source order、block kinds、bbox、table/image、strategy/version；场景策略使用 `sha256-v2`，General 保留 `sha256-v1` 兼容 Phase 04；Elasticsearch mapping 可原位追加 Phase 05 字段，Citation 恢复 bbox。
- **实际验证结果**：跨格式/九策略契约、真实 Elasticsearch mapping/upsert/retrieve/Citation bbox 测试通过。
- **计划偏差**：没有创建数据库迁移，因为新增字段只属于领域对象和 Elasticsearch 文档；现有索引通过 `put_mapping` 向后兼容。

### P05-T11：建立黄金、契约与资源测试

- **状态**：已完成
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
- **实际执行结果**：新增生成式八格式样本工厂、样本 provenance README、Parser 黄金、Chunk/metadata/degradation 契约、OOXML/image 资源攻击和并发可重复性测试；二进制样本均在测试时生成。
- **实际验证结果**：Parser/Chunk 专项 25 项通过、真实 Tesseract 在本机无运行时环境时 1 项显式 skip；CI 将该测试设置为 required，不能静默 skip。
- **计划偏差**：未提交真实企业复杂文档或 GPU 性能基线；复杂样本代表性继续作为 R-015，当前验收只覆盖小型合法、攻击和结构样本。

### P05-T12：集成 ingestion 并执行阶段验收

- **状态**：已完成
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
- **实际执行结果**：生产 runtime 已接入八 Parser、Tesseract、auto Chunk 路由和九种策略；上传允许列表扩展到八类输入；新增八格式 Memory E2E 和 PostgreSQL/MinIO/Redis/Elasticsearch 真实后端 E2E。
- **实际验证结果**：本地隔离 Compose 真实后端专项 8 项通过；完整真实基础设施环境 180 项通过、1 项真实 Tesseract 本机显式 skip；默认无外部服务环境 169 项通过、12 项显式 skip；`ruff check .`、strict `mypy src/ragflow_agent tests`、锁文件、密钥卫生、Alembic、bootstrap 和 Compose config 通过；GitHub Actions 最终结果见阶段出口记录。
- **计划偏差**：真实 DeepSeek/BGE-M3/GPU 仍不是 Phase 05 门禁；真实 Tesseract 由 Linux CI 覆盖，本机 Windows 未安装 Tesseract 时如实 skip。

## 8. 阶段验收、DoD、风险与后续

**验收/DoD**：已满足。P05-T01 至 P05-T12 完成；8 类目标输入、OCR、表格和 9 种明确 Chunk 策略均有黄金/资源/E2E；metadata/Citation 来源稳定；RAGFlow 复制/改造复用为零，因此未创建空 `ragflow_adapters` 包；自动增强未误标实现；总体文档已同步。

| 风险 | 处理 |
|---|---|
| 模型/原生库许可 | 分层登记，不明则不复制/不分发 |
| GPU/内存过高 | 可选 Profile、批次/超时/并发限制 |
| Parser 输出漂移 | 黄金样本与版本锁定 |
| 临时文件/恶意文档 | 沙箱边界、大小/时间/清理门禁 |
| 与 Phase 09 重复 | 本阶段只做基础结构和扩展点 |

阶段结束更新总纲、架构、矩阵、复用、路线图、标准、风险、状态索引和本文件。Phase 06 需基于实际 metadata/Chunk/Citation 重审后执行。

## 9. 实际执行结果预留

- 实际批准复用清单：RAGFlow 直接复用 0、改造复用 0；全部目标实现为独立第三方适配或自研，详见 [Phase 05 许可与资源基线](../research/phase-05-parser-license-and-resource-baseline.md)。
- 实际格式/策略/模型与资源结果：八类格式、Tesseract CPU OCR、9 种策略、schema v2、OOXML/PDF/图片/XLSX 门禁已落地；复杂模型版面、GPU 和真实外部 Chat/Embedding 未进入本阶段验收。
- 实际测试命令和偏差：默认环境、隔离真实后端环境和 GitHub Actions 三层验证；本机没有 Tesseract 时只允许显式 skip，CI required；没有提交二进制测试文档。
- 阶段出口结论：Phase 05 已完成；Phase 06 的技术准入条件已具备，但仍须先按本阶段实际 metadata、Citation 和 Elasticsearch 能力复审其预规划草案，且本轮不执行 Phase 06。
