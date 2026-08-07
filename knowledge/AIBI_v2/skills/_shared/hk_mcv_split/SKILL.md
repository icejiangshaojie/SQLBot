# Skill: HK/MCV 拆分规则 (hk_mcv_split)

> 跨域共享 Skill · 适用于需要按客户类型拆分分析的零售场景
> 版本：v1.0 | 2026-08-03

---

## 一、定义

- **HK**：香港本地客户（cust_sub_type = 'HK'）
- **MCV**：大湾区访客客户（cust_sub_type = 'MCV'）

拆分维度来自 `dim_cust_basic_info_ext_d_aiview` 表的 `cust_sub_type` 字段。

## 二、执行规则

1. **必须拆分**：卡消费金额/笔数/客户数，必须按 HK / MCV 拆分展示
2. **JOIN 方式**：`LEFT JOIN dim_cust_basic_info_ext_d_aiview t2 ON t1.cust_no = t2.cust_no`
3. **NULL 处理**：`cust_sub_type` 为 NULL 的客户归入"未知"类别，不得丢弃
4. **输出格式**：每个指标分两列，如 `hk_trans_amt` / `mcv_trans_amt`

## 三、不适用场景

- 对公客户不适用 HK/MCV 拆分（对公无 cust_sub_type 概念）
- 聚合汇总不需要拆分时（如只需总金额），可省略

## 四、SQL 参考

```sql
SELECT t2.cust_sub_type,
       SUM(t1.trans_amt_hkd) AS trans_amt_hkd,
       COUNT(DISTINCT t1.cust_no) AS trans_cust_cnt
FROM {main_table} t1
LEFT JOIN dim_cust_basic_info_ext_d_aiview t2 ON t1.cust_no = t2.cust_no
WHERE ...
GROUP BY t2.cust_sub_type
```
