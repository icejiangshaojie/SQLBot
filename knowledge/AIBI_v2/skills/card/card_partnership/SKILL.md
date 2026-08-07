# Skill: 商户合作活动 (card_partnership)

> 场景 P · 品牌合作活动的消费/参与/留存分析
> 版本：v1.0 | 2026-07-31

---

## 一、输入识别

| 用户问法 | 分析类型 |
|---------|---------|
| 活动基础信息 | L0a · 基础信息 |
| 活动消费对比 | L0b · 消费对比 |
| 活动参与识别 | L0c · 参与识别 |
| 活动留存 | L0d · 留存 |
| 完整报告 | L1 · 完整报告 |

---

## 二、核心表

- `dwd_fct_retail_cust_card_auth_d_delta_aiview`（消费明细，**增量表**）
- `dim_cust_basic_info_ext_d_aiview`（画像，HK/MCV 拆分）

---

## 三、执行流程

1. **活动配置**：活动名/时间窗口/MCC/商户名/对比基线
2. **L0a 基础信息**：活动期间消费金额/笔数/客户数
3. **L0b 消费对比**：活动期 vs 基线期（活动前 N 天）
4. **L0c 参与识别**：活动商户消费客户 vs 非活动商户消费客户
5. **L0d 留存**：活动后 T+7/T+14/T+30 留存率
6. **L1 完整报告**：整合 L0a-L0d

---

## 四、SQL 模板

### 活动期间消费
```sql
SELECT t2.cust_sub_type,
       SUM(t1.trans_amt_hkd) AS amt,
       COUNT(DISTINCT t1.cust_no) AS cust_cnt,
       COUNT(1) AS trans_cnt
FROM dwd_fct_retail_cust_card_auth_d_delta_aiview t1
LEFT JOIN dim_cust_basic_info_ext_d_aiview t2 ON t1.cust_no=t2.cust_no
WHERE t1.pt BETWEEN '${activity_start}' AND '${activity_end}'
    AND t1.is_successful_auth='1'
    AND (t1.merchant_name LIKE '%${merchant}%' OR t1.mcc IN (${mcc_list}))
GROUP BY t2.cust_sub_type
```

### 活动期 vs 基线期对比
```sql
SELECT
    CASE WHEN t1.trans_date BETWEEN '${activity_start}' AND '${activity_end}' THEN '活动期'
         ELSE '基线期' END AS period,
    t2.cust_sub_type,
    SUM(t1.trans_amt_hkd) AS amt,
    COUNT(DISTINCT t1.cust_no) AS cust_cnt
FROM dwd_fct_retail_cust_card_auth_d_delta_aiview t1
LEFT JOIN dim_cust_basic_info_ext_d_aiview t2 ON t1.cust_no=t2.cust_no
WHERE t1.pt BETWEEN '${baseline_start}' AND '${activity_end}'
    AND t1.is_successful_auth='1'
    AND (t1.merchant_name LIKE '%${merchant}%' OR t1.mcc IN (${mcc_list}))
GROUP BY 1, 2
```

---

## 五、输出格式

| 指标 | HK活动期 | HK基线期 | HK变化 | MCV活动期 | MCV基线期 | MCV变化 |
|------|---------|---------|--------|----------|----------|--------|
| 消费金额 | ... | ... | ... | ... | ... | ... |
| 客户数 | ... | ... | ... | ... | ... | ... |
