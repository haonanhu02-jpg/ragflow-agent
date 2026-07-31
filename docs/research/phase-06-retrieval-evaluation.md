# Phase 06 检索评测基线

状态：已完成；P06-T12 本地阶段验收结果已冻结。

## 数据与指标

- 数据全部为仓库内人工构造、无敏感信息的小型 Chunk ID/文本样本，不包含用户查询或上传文档。
- 指标为 Recall@K、MRR、NDCG@K、Citation scope 正确性、硬过滤违规数和 Trace 完整性。
- 消融维度固定为全文、向量、RRF 混合、Fake Reranker、Reranker 故障回退和有限空结果降级。
- 真实 Elasticsearch 只验证后端行为和安全过滤；Fake Reranker 结果不得当作真实 BGE 模型质量。

## 阶段出口结果

- 确定性消融夹具包含 1 个查询、2 个相关 Chunk 和 1 个噪声 Chunk。
- 全文与向量单通道的 Recall@3 均为 `0.5`；混合结果 Recall@3 为 `1.0`、
  MRR 为 `1.0`、NDCG@3 为 `1.0`。该夹具证明指标和融合排序的确定性，
  不代表企业语料或真实模型质量。
- `tests/evaluation/retrieval/test_metrics.py`：`2 passed`；Phase 06 检索单元与
  评测合计 `19 passed`。
- 隔离 PostgreSQL/MinIO/Redis/Elasticsearch 全仓回归：`203 passed, 1 skipped`；
  唯一 skip 是本机未安装 Tesseract，与 Phase 06 检索无关。
- 真实 Elasticsearch 与 PostgreSQL 检索/Trace 专项：`4 passed`，验证 BM25、
  KNN、硬过滤、排名、内容最小化 Trace、tenant 隔离、TTL 和清理。
- Fake/Stub 覆盖 DeepSeek 查询变换、BGE Reranker 排序/超时/异常回退；没有
  真实 DeepSeek、BGE-M3 或 BGE Reranker 服务/GPU 质量与性能结论。

## 可复现命令

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\unit\retrieval tests\evaluation\retrieval
.\.venv\Scripts\python.exe -m pytest -q tests\e2e\retrieval `
  tests\integration\database\test_retrieval_trace_store.py `
  tests\integration\search\test_phase06_retrieval.py `
  tests\integration\search\test_elasticsearch.py
.\.venv\Scripts\python.exe -m pytest -q
```

真实后端命令要求设置隔离的 `RAGFLOW_AGENT_TEST_DATABASE_URL`、
`RAGFLOW_AGENT_TEST_REDIS_URL`、`RAGFLOW_AGENT_TEST_S3_*` 和
`RAGFLOW_AGENT_TEST_ELASTICSEARCH_URL`；不得指向生产数据。
