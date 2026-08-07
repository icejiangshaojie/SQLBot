# Skill: KPI 监控 (kpi_monitoring)

> 场景 K · 卡域 KPI 监控（YTD/MTD 达成率、周趋势）
> 版本：v1.0 | 2026-07-31

---

## 一、输入识别

| 用户问法 | SQL 模板 |
|---------|---------|
| KPI 达成率 / YTD / MTD | S12 |
| 周报 / 周趋势 | S12 |
| 净收入 / 消费PV / Reward Cost | S7, S8 |

---

## 二、核心表

- `dm_db_card_kpi_2026_weekly_d_aiview`（周报，全量快照）
- `dm_db_card_kpi_monthly_tracking_d_aiview`（月报，全量快照）
- `dws_card_kpi_net_revenue_daily_tracking_d_aiview`（日度跟踪，全量快照）

---

## 三、执行流程

1. **探测最新分区**：`SELECT MAX(pt) FROM dm_db_card_kpi_2026_weekly_d_aiview`
2. **查 KPI 周报**（S12）：YTD 达成率、环比增长率
3. **查日度净收入**（S7/S8）：fx_dcc_amt_hkd / reward_amt_hkd
4. **输出**：表格 + 达成率状态判定（直接看达成率判状态，不设额外阈值）

---

## 四、SQL 模板引用

### S12 · KPI YTD 达成率
```sql
SELECT kpi_name, stat_start_end_date, accu_value_ytd, accu_value_target_ytd,
       accu_achieve_rate_ytd, growth_value, comparative_growth_rate
FROM dm_db_card_kpi_2026_weekly_d_aiview
WHERE pt = (SELECT MAX(pt) FROM dm_db_card_kpi_2026_weekly_d_aiview)
    AND is_latest_weekly = 'Y'
ORDER BY kpi_name
```

### S7 · FX Mark-up + DCC 收入
```sql
SELECT fx_dcc_amt_hkd FROM dws_card_kpi_net_revenue_daily_tracking_d_aiview
WHERE pt = '${pt}'
```

### S8 · Reward Cost
```sql
SELECT reward_amt_hkd FROM dws_card_kpi_net_revenue_daily_tracking_d_aiview
WHERE pt = '${pt}'
```

---

## 五、输出格式

| KPI名称 | 周期 | YTD累计 | YTD目标 | 达成率 | 环比 |
|---------|------|---------|---------|--------|------|
| ... | ... | ... | ... | ... | ... |
