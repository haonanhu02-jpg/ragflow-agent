---
document_id: PHASE-05-PARSER-LICENSE-RESOURCE-BASELINE
document_role: Phase 05 Parser、OCR、样本、资源与许可证执行基线
status: active
last_updated_at: "2026-07-31"
ragflow_frozen_baseline_commit: "cd846cc9d4e32a19e684c59a1f302601027ef976"
---

# Phase 05 Parser、OCR、样本、资源与许可证基线

## 1. 执行结论

- Phase 05 不复制、抽取、翻译或改写 RAGFlow 源码，不创建 RAGFlow 派生文件。
- `deepdoc/parser/`、`deepdoc/vision/`、`rag/app/` 只提供职责、调用顺序和行为目标证据。
- 本阶段 Parser、OCR Adapter、注册表和 Chunk 策略全部独立实现；因此 `ragflow_adapters` 在本阶段保持为空，不制造无实际复用内容的隔离包。
- 若后续首次复制任何第三方源码，必须停止实施，逐文件核查许可证、NOTICE、修改声明、传递依赖和分发义务，并用新 ADR 替代本基线。

## 2. RAGFlow 源码审计

| 冻结源码 | 关键符号 | 实际内部依赖 | Phase 05 处理 |
|---|---|---|---|
| `deepdoc/parser/pdf_parser.py` | `RAGFlowPdfParser`、`PlainParser`、`VisionParser` | `common.settings`、RAG tokenizer、OCR/Layout/Table、NumPy、pdfplumber、XGBoost、模型下载 | 仅参考分层 Profile；独立实现 |
| `deepdoc/parser/docx_parser.py` | `RAGFlowDocxParser` | python-docx、pandas、RAG tokenizer、`LazyImage` | 仅参考段落/表格/图片职责；独立实现 |
| `deepdoc/parser/ppt_parser.py` | `RAGFlowPptParser` | python-pptx | 仅参考 slide 顺序；独立实现 |
| `deepdoc/parser/excel_parser.py` | `RAGFlowExcelParser` | pandas、openpyxl、codec、`LazyImage` | 仅参考 worksheet/row 输出；独立实现 |
| `deepdoc/vision/ocr.py` | `OCR`、`TextDetector`、`TextRecognizer` | Hugging Face snapshot、ONNX Runtime、OpenCV、设备/并发、模型目录 | 不采用；用可替换 OCR Port + Tesseract 基线 |
| `deepdoc/vision/layout_recognizer.py` | `LayoutRecognizer` | ONNX、OpenCV、模型权重、标签/NMS | 不采用模型；使用格式原生坐标和 OCR bbox |
| `deepdoc/vision/table_structure_recognizer.py` | `TableStructureRecognizer` | ONNX、OpenCV、模型权重、RAG tokenizer | 不采用模型；使用 Office/PDF 原生表格结构 |
| `rag/svr/task_executor_refactor/chunk_builder.py` | `get_parser`、`run_chunking` | `TaskContext`、ParserType、模块级 Parser 工厂 | 仅参考路由；自研 Registry |
| `rag/app/{naive,paper,book,manual,laws,qa,table,resume,picture}.py` | `chunk` 及格式专用辅助函数 | DeepDOC、RAG tokenizer、settings、模型服务、业务 Service | 仅参考场景边界；自研版本化策略 |

冻结依据均为 commit `cd846cc9d4e32a19e684c59a1f302601027ef976`。本地
`D:/ragflow/ragflow-main` 只用于 import graph 快速核对。

## 3. 第三方运行依赖

| 依赖（锁定版本） | 用途 | 许可证/边界 |
|---|---|---|
| beautifulsoup4 4.15.0 | HTML 清理与结构遍历 | MIT；不执行脚本 |
| charset-normalizer 3.4.9 | 文本编码探测 | MIT |
| markdown-it-py 4.2.0 | CommonMark AST | MIT |
| python-docx 1.2.0 | DOCX 段落、样式、表格、图片锚点 | MIT；不支持旧 `.doc` |
| python-pptx 1.0.2 | PPTX slide、shape、表格、图片 | MIT；不支持旧 `.ppt` |
| openpyxl 3.1.5 + defusedxml 0.7.1 | XLSX worksheet、类型、公式字面量、合并信息 | MIT + Python-2.0；不执行公式或宏 |
| pdfplumber 0.11.10 | 文本 PDF 字词坐标、阅读顺序和表格 | MIT；扫描页必须转 OCR |
| pypdfium2 5.12.1 | 扫描 PDF 页渲染 | Apache-2.0/BSD-3-Clause；发布时保留其 PDFium/依赖许可证 |
| Pillow 12.3.0 | 图片验证、方向和像素限制 | HPND |
| pytesseract 0.3.13 | Tesseract CLI Adapter | Apache-2.0；不捆绑 OCR 引擎/语言权重 |
| Tesseract 5.x 外部运行时 | 英文/简体中文真实 OCR | Apache-2.0；CI 安装 `eng`、`chi_sim`，部署方独立管理语言数据 |

开发/测试依赖另包含 `types-openpyxl 3.1.5.20260724`（仅 strict mypy）
和 `reportlab 4.5.1`（BSD，仅在内存中生成合成 PDF 黄金样本），均不进入
Parser 生产调用链。

许可证信息来自对应发行包元数据和上游许可证。它是工程合规基线，不构成法律意见。

## 4. Parser、Chunk 与资源 Profile

- 默认 Parser 选择同时校验 MIME 和扩展名；未知、冲突或旧 Office 二进制格式必须返回稳定错误。
- 默认格式映射：TXT→General、Markdown/HTML/DOCX/PPTX→Manual、XLSX→Table、PDF→Paper、图片→Picture；显式策略可覆盖，但未知覆盖不能静默回退。
- 上传上限沿用 Phase 04 的 `max_upload_bytes`。
- OOXML 包限制：最多 5,000 entries、解压后最多 100 MiB、单项压缩比最多 100。
- 图片限制：最多 40,000,000 pixels；禁止 Pillow decompression-bomb warning 静默通过。
- XLSX 限制：最多 64 sheets、每 sheet 100,000 rows、总计 1,000,000 非空 cells。
- PDF 限制：最多 2,000 pages；小型黄金样本的 Parser 预算为 10 秒，Worker 总超时继续由现有配置约束。
- Parser 不写数据库、索引或临时文件；它只输出版本化 `ParsedDocument`。OCR/格式库异常必须映射为稳定错误或结构化 warning。
- Phase 05 不承诺 GPU Profile，不下载或分发模型权重。Tesseract 是 CPU 外部进程；不可用时图片/扫描页返回明确失败，不能返回空成功。

## 5. 测试样本规则

- `tests/fixtures/parsing/` 只保存人工创建、无敏感信息、UTF-8、小体积的文本样本和 provenance 清单。
- DOCX、PPTX、XLSX、PDF 和图片样本由测试使用锁定库在临时目录/内存中确定性生成，不提交用户上传文件或第三方文档。
- 黄金输出只描述稳定的领域字段；不得包含临时路径、时间戳、依赖库内部对象或平台相关二进制差异。
- Tesseract 契约测试可在本地无引擎时显式 skip，但 GitHub Actions 必须安装 `eng`、`chi_sim` 并设置“必须执行”开关；CI 中 skip 真实 OCR 视为失败。
- 资源测试使用小型、人工生成的限界输入；不提交超大压缩包、模型权重、缓存或测试输出。

## 6. 关联文档

[Phase 05 计划](../phases/phase-05-parser-and-chunk.md) ·
[复用策略](../04-code-reuse-strategy.md) ·
[决策与风险](../07-decisions-and-risks.md)
