# SQL 样例 · 卡域分析

> 版本：v1.0 | 2026-07-31 | 来源：Obsidian 知识库 + ODPS 验证
> 所有 SQL 走 `_aiview` 视图，运行时 hub-first fallback

---

## S1 · 消费总收入

```sql
-- agg_type: sum
-- source: dws_card_cust_trans_date_income_cost_d.sql line 63
-- 口径: 交换费+Visa赞助费+DCC+外汇利润+ATM取现手续费
SELECT trans_income_fees
FROM dws_card_cust_trans_date_income_cost_d_aiview
WHERE pt = '${pt}'
```

## S2 · 消费总支出

```sql
-- agg_type: sum
-- source: dws_card_cust_trans_date_income_cost_d.sql line 78
-- 口径: 清算成本+授权成本+ATM成本+验证费+Visa杂费+返现成本+Stockback成本
SELECT trans_cost_fees
FROM dws_card_cust_trans_date_income_cost_d_aiview
WHERE pt = '${pt}'
```

## S3 · 消费净收入

```sql
-- agg_type: sum
-- source: dws_card_cust_trans_date_income_cost_d.sql line 106
-- 口径: 消费总收入 - 消费总支出
SELECT trans_net_revenue
FROM dws_card_cust_trans_date_income_cost_d_aiview
WHERE pt = '${pt}'
```

## S4 · Stockback 普通返增

```sql
-- agg_type: sum
-- source: dws_card_cust_trans_date_income_cost_d.sql line 111
SELECT stockback_basic_reward_amt_hkd
FROM dws_card_cust_trans_date_income_cost_d_aiview
WHERE pt = '${pt}'
```

## S5 · Stockback 新户额外成本

```sql
-- agg_type: sum
-- source: dws_card_cust_trans_date_income_cost_d.sql line 116
-- 口径: 推广期新户返现比例3%，其中1%是额外增加的返现比例
SELECT stockback_ntb_extra_reward_amt_hkd
FROM dws_card_cust_trans_date_income_cost_d_aiview
WHERE pt = '${pt}'
```

## S6 · Stockback 总返现金额

```sql
-- agg_type: sum
-- source: dws_card_cust_trans_date_income_cost_d.sql line 76
SELECT stockback_reward_amt_hkd
FROM dws_card_cust_trans_date_income_cost_d_aiview
WHERE pt = '${pt}'
```

## S7 · FX Mark-up 跟 DCC 收入

```sql
-- agg_type: sum
-- source: dws_card_kpi_net_revenue_daily_tracking_d.sql line 25
SELECT fx_dcc_amt_hkd
FROM dws_card_kpi_net_revenue_daily_tracking_d_aiview
WHERE pt = '${pt}'
```

## S8 · Reward Cost（返现成本支出）

```sql
-- agg_type: sum
-- source: dws_card_kpi_net_revenue_daily_tracking_d.sql line 28
SELECT reward_amt_hkd
FROM dws_card_kpi_net_revenue_daily_tracking_d_aiview
WHERE pt = '${pt}'
```

## S9 · 卡消费总额（按日 + HK/MCV 拆分）

```sql
-- 场景: 卡消费现状看板
-- 表: dwd_fct_retail_cust_card_auth_d_delta_aiview (增量表)
-- ⚠️ 必须 pt BETWEEN
SELECT
    t1.trans_date,
    t2.cust_sub_type,
    SUM(t1.trans_amt_hkd) AS trans_amt_hkd,
    COUNT(DISTINCT t1.cust_no) AS trans_cust_cnt,
    COUNT(1) AS trans_cnt
FROM dwd_fct_retail_cust_card_auth_d_delta_aiview t1
LEFT JOIN dim_cust_basic_info_ext_d_aiview t2
    ON t1.cust_no = t2.cust_no
WHERE t1.pt BETWEEN '${start_pt}' AND '${end_pt}'
    AND t1.is_successful_auth = '1'
    AND t1.trans_channel <> 'ATM'
GROUP BY t1.trans_date, t2.cust_sub_type
ORDER BY t1.trans_date
```

## S10 · MPAU 成分结构（当月快照）

```sql
-- 场景: MPAU 成分分析
-- 表: dws_card_cust_trans_label_info_d_aiview (全量快照)
-- 5类: 新客首刷/持续活跃/沉默回流/流失回流/存量客户首刷
SELECT
    CASE
        WHEN is_30d_mpau = 'Y' AND is_last_mon_mpau = 'N' AND first_trans_card_time >= DATE_SUB('${bizdate}', 30) THEN '新客首刷'
        WHEN is_30d_mpau = 'Y' AND is_last_mon_mpau = 'Y' THEN '持续活跃'
        WHEN is_30d_mpau = 'Y' AND is_last_mon_mpau = 'N' AND first_trans_card_time < DATE_SUB('${bizdate}', 30) THEN '沉默回流'
        WHEN is_30d_mpau = 'N' AND is_last_mon_mpau = 'Y' THEN '流失回流'
        WHEN is_30d_mpau = 'Y' AND is_last_mon_mpau = 'N' THEN '存量客户首刷'
        ELSE '非活跃'
    END AS mpau_type,
    COUNT(DISTINCT cust_no) AS cust_cnt
FROM dws_card_cust_trans_label_info_d_aiview
WHERE pt = (SELECT MAX(pt) FROM dws_card_cust_trans_label_info_d_aiview)
    AND is_30d_mpau = 'Y'
GROUP BY 1
```

## S11 · NTB 新户 T+30 首刷率

```sql
-- 场景: NTB 新户转化
-- 表: dim_card_ntb_tag_d (全量快照) + dwd_fct_retail_cust_card_auth_d_delta (增量)
-- ⚠️ 分母必须 open_full_30d=1，分子排除 ATM
SELECT
    t1.cust_sub_type,
    t1.open_apply_channel,
    COUNT(DISTINCT t1.cust_no) AS total_cust,
    COUNT(DISTINCT CASE WHEN t2.cust_no IS NOT NULL THEN t1.cust_no END) AS first_trans_cust,
    ROUND(COUNT(DISTINCT CASE WHEN t2.cust_no IS NOT NULL THEN t1.cust_no END) * 100.0
          / COUNT(DISTINCT t1.cust_no), 2) AS first_trans_rate
FROM dim_card_ntb_tag_d_aiview t1
LEFT JOIN (
    SELECT DISTINCT cust_no
    FROM dwd_fct_retail_cust_card_auth_d_delta_aiview
    WHERE pt BETWEEN '${start_pt}' AND '${end_pt}'
        AND is_successful_auth = '1'
        AND trans_channel <> 'ATM'
        AND trans_date >= open_acct_date
) t2 ON t1.cust_no = t2.cust_no
WHERE t1.pt = (SELECT MAX(pt) FROM dim_card_ntb_tag_d_aiview)
    AND t1.open_full_30d = 1
GROUP BY t1.cust_sub_type, t1.open_apply_channel
```

## S12 · KPI YTD 达成率

```sql
-- 场景: KPI 监控
-- 表: dm_db_card_kpi_2026_weekly_d_aiview (全量快照)
SELECT
    kpi_name,
    stat_start_end_date,
    accu_value_ytd,
    accu_value_target_ytd,
    accu_achieve_rate_ytd,
    growth_value,
    comparative_growth_rate
FROM dm_db_card_kpi_2026_weekly_d_aiview
WHERE pt = (SELECT MAX(pt) FROM dm_db_card_kpi_2026_weekly_d_aiview)
    AND is_latest_weekly = 'Y'
ORDER BY kpi_name
```

## S13 · MPAU 四类消费金额分布

```sql
-- 场景: MPAU 下钻分析
-- 表: dws_card_cust_trans_label_info_d_aiview
SELECT
    '航空酒店' AS category, SUM(mpau_air_hotel_amt_new) AS amt FROM dws_card_cust_trans_label_info_d_aiview WHERE pt = (SELECT MAX(pt) FROM dws_card_cust_trans_label_info_d_aiview) AND is_30d_mpau='Y'
UNION ALL
SELECT '日常消费', SUM(mpau_daily_necessities_amt_new) FROM dws_card_cust_trans_label_info_d_aiview WHERE pt = (SELECT MAX(pt) FROM dws_card_cust_trans_label_info_d_aiview) AND is_30d_mpau='Y'
UNION ALL
SELECT '时尚购物', SUM(mpau_fashion_amt_new) FROM dws_card_cust_trans_label_info_d_aiview WHERE pt = (SELECT MAX(pt) FROM dws_card_cust_trans_label_info_d_aiview) AND is_30d_mpau='Y'
UNION ALL
SELECT '医美健康', SUM(mpau_healthcare_amt_new) FROM dws_card_cust_trans_label_info_d_aiview WHERE pt = (SELECT MAX(pt) FROM dws_card_cust_trans_label_info_d_aiview) AND is_30d_mpau='Y'
```
