# Phase 0 接口合同

> 本文档固化 Phase 0 已实现的运行合同，供前后端对齐、测试与后续演进参考。代码位置：`backend/apps/ai2bi/analysis_contract.py`、`qa_checker.py`、`evidence_builder.py`、`evidence_models.py`，前端 `frontend/src/types/analysis.ts`。

## 分析状态（AnalysisRunStatus）

分析一次运行最终落为以下状态之一：

| status | 含义 | 是否展示 LLM 正文 |
| --- | --- | --- |
| `completed` | 分析完成，QA 通过 | ✅ |
| `warning` | 完成但有警告（如数据不足事实、因果嫌疑） | ✅（带提示） |
| `blocked` | QA 阻断（无来源数字/预测/无支持因果） | ❌，输出原因 |
| `data_insufficient` | 数据不足，不产结论 | ❌，系统固定说明 |
| `failed` | 分析引擎/LLM 异常 | ❌，输出原因 |
| `skipped` | 跳过（如分析意图评估后跳过） | ❌，输出原因 |

对应枚举：`AnalysisStatus`（`backend/apps/ai2bi/analysis_contract.py`）。前端 `AnalysisRunStatus` 与此对齐。

## AnalysisFact

每条事实必须可定位到来源，`source_type` 三选一：

- `sql`：SQL 直接返回。
- `backend_calc`：后端确定性计算（带 `formula` 与 `input_refs`）。
- `model_inferred`：模型推导（Phase 0 默认不应作为唯一结论证据）。

字段：`fact_id`、`category`、`label`、`value`、`unit`、`source_type`、`formula?`、`input_refs[]`、`row_refs[]`、`column?`、`display?`、`status(verified|data_insufficient)`、`reason?`。

## QA 合同（QaResult）

```json
{
  "status": "passed | warning | blocked",
  "findings": [
    { "code": "unsourced_numbers", "severity": "block|warning|info",
      "message": "...", "fact_ids": [], "source_refs": [] }
  ],
  "summary": {
    "sql_facts": 0, "backend_facts": 0, "model_facts": 0,
    "data_insufficient": 0, "sourced_numbers": 0,
    "derived_count": 0, "inferred_count": 0, "unsourced_count": 0
  },
  "renderable": true
}
```

- `renderable`：`passed`/`warning` 为 `true`；`blocked` 为 `false`。
- `block` 级阻断项：无来源经营数字、与事实不一致数字、数值预测、无支持因果断言。
- **来源判定**：答案中的经营数字须在 Facts 值集合或原始结果 `result.data` 数值集合中（后者允许 LLM 引用 SQL 直出明细值，避免误报）。

## SSE 事件

主聊天链路（`in_chat=True`）流式事件：

| type | 负载 | 说明 |
| --- | --- | --- |
| `id` | `{id}` | 记录 id |
| `question` | `{question}` | 问题回显 |
| `datasource-result` | `{content, reasoning_content}` | 数据源选择 |
| `sql` / `result` | ... | SQL 与结果（既有） |
| `analysis_status` | `{status, message}` | 分析状态推进 |
| `evidence_qa` | `{content}` | QA 结果 JSON 字符串 |
| `analysis` | `{content}` | 通过 QA 的分析正文 |
| `evidence_ready` | `{record_id, status}` | 证据持久化完成 |
| `analysis_error` | `{code, message, retryable}` | 分析失败 |
| `finish` | `{}` | 结束 |

MCP 非流式模式（`in_chat=False, stream=False`）不逐条 SSE，`await_result()` 全量消费生成器后返回 JSON（含 `record_id`、`sql`、`data`、`chart`）；分析结果写入 `ai2bi_evidence`，`analysis_status` 一并持久化。

## 数值精度与舍入

- Fact 值统一 `round(value, 2)` 后纳入来源集合比较。
- 增长率/占比按业务规则保留展示精度（`display`），原始值保留在 `value`。
- 零分母、NULL、样本不足不产出数值，改输出 `data_insufficient` 事实并带 `reason`。

## 持久化（ai2bi_evidence）

关键列：`source_record_id`（指向原始查询记录）、`analysis_status`、`analysis_error`、`analysis_facts`、`qa_result`、`analysis_output`、`result_hash`、`metric_context`、`agent_snapshot`、`model_name`、`total_tokens`、`duration_ms`。

读取接口：`GET /ai2bi/evidence/{record_id}` 返回扩展详情。同一分析记录采用可重复更新（upsert），避免刷新/重试产生多条含义不明的记录。

## 前端映射

- `getEvidence(recordId)` → `EvidenceDetail`（`frontend/src/api/ai2bi.ts`）。
- `createSseDecoder` / `parseSseText`（`frontend/src/utils/sse.ts`）：以空行边界解码、串联 `data:` 行、容错分块与未知事件。
- `AnalysisRunPanel` 对 `completed/warning/blocked/data_insufficient/failed/skipped` 做状态投影。