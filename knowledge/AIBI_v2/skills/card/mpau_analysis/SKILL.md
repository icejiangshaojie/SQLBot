# Skill: MPAU 成分结构 (mpau_analysis)

> 场景 M · 月活用户成分分析（快照/跨期/归因/下钻/回赠/留存）
> 版本：v1.0 | 2026-07-31

---

## 一、输入识别

| 用户问法 | 分析类型 |
|---------|---------|
| MPAU 成分、月活结构 | A · 快照 |
| MPAU 环比变化 | B · 跨期 |
| MPAU 升降归因 | C · 归因 |
| MPAU 消费类别 | D · 下钻 |
| 回赠计划分布 | E · 回赠 |
| 留存率 | F · 留存 |

---

## 二、核心表

- `dws_card_cust_trans_label_info_d_aiview`（MPAU 主表，**全量快照**）
- `dim_cust_basic_info_ext_d_aiview`（画像，HK/MCV 拆分）

---

## 三、MPAU 五类成分定义

| 成分 | 条件 | 口径 |
|------|------|------|
| 新客首刷 | `is_30d_mpau='Y' AND is_last_mon_mpau='N' AND first_trans_card_time >= 近30天` | 首次刷卡的新客 |
| 持续活跃 | `is_30d_mpau='Y' AND is_last_mon_mpau='Y'` | 连续两月活跃 |
| 沉默回流 | `is_30d_mpau='Y' AND is_last_mon_mpau='N' AND first_trans_card_time < 近30天` | 老客回流 |
| 流失回流 | `is_30d_mpau='N' AND is_last_mon_mpau='Y'` | 上月活跃本月流失 |
| 存量客户首刷 | `is_30d_mpau='Y' AND is_last_mon_mpau='N'` | 存量首刷 |

---

## 四、SQL 模板引用

### S10 · MPAU 成分结构（当月快照）
```sql
SELECT
    CASE
        WHEN is_30d_mpau='Y' AND is_last_mon_mpau='N'
            AND first_trans_card_time >= DATE_SUB('${bizdate}',30) THEN '新客首刷'
        WHEN is_30d_mpau='Y' AND is_last_mon_mpau='Y' THEN '持续活跃'
        WHEN is_30d_mpau='Y' AND is_last_mon_mpau='N'
            AND first_trans_card_time < DATE_SUB('${bizdate}',30) THEN '沉默回流'
        WHEN is_30d_mpau='N' AND is_last_mon_mpau='Y' THEN '流失回流'
        ELSE '存量客户首刷'
    END AS mpau_type,
    COUNT(DISTINCT cust_no) AS cust_cnt
FROM dws_card_cust_trans_label_info_d_aiview
WHERE pt = (SELECT MAX(pt) FROM dws_card_cust_trans_label_info_d_aiview)
    AND is_30d_mpau='Y'
GROUP BY 1
```

### S13 · MPAU 四类消费金额分布
```sql
SELECT '航空酒店', SUM(mpau_air_hotel_amt_new) FROM dws_card_cust_trans_label_info_d_aiview
WHERE pt=(SELECT MAX(pt) FROM dws_card_cust_trans_label_info_d_aiview) AND is_30d_mpau='Y'
UNION ALL
SELECT '日常消费', SUM(mpau_daily_necessities_amt_new) FROM dws_card_cust_trans_label_info_d_aiview
WHERE pt=(SELECT MAX(pt) FROM dws_card_cust_trans_label_info_d_aiview) AND is_30d_mpau='Y'
UNION ALL
SELECT '时尚购物', SUM(mpau_fashion_amt_new) FROM dws_card_cust_trans_label_info_d_aiview
WHERE pt=(SELECT MAX(pt) FROM dws_card_cust_trans_label_info_d_aiview) AND is_30d_mpau='Y'
UNION ALL
SELECT '医美健康', SUM(mpau_healthcare_amt_new) FROM dws_card_cust_trans_label_info_d_aiview
WHERE pt=(SELECT MAX(pt) FROM dws_card_cust_trans_label_info_d_aiview) AND is_30d_mpau='Y'
```

---

## 五、跨期对比基线

默认**上月同日**优先；缺失则月末兜底。

> 占比下降但绝对值增长 = 稀释效应，需自动标注。

---

## 六、输出格式

| MPAU类型 | 客户数 | 占比 | 上月客户数 | 上月占比 | 变化 |
|---------|--------|------|-----------|---------|------|
| 持续活跃 | ... | ... | ... | ... | ... |

四类消费金额分布饼图附后。
