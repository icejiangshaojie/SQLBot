# Skill: 卡消费现状 (card_trans)

> 场景 C · 卡消费金额/笔数/客户数、ATM 取现、MCC 商户排名、月度对比
> 版本：v1.0 | 2026-07-31

---

## 一、输入识别

| 用户问法 | SQL 模板 |
|---------|---------|
| 消费金额/笔数/客户数 | S9 |
| ATM 取现 | S9 (改 trans_channel) |
| MCC 商户排名 Top N | 自定义 |
| 月度同期对比 | S9 + GROUP BY month |
| 消费总收入/支出/净收入 | S1, S2, S3 |

---

## 二、核心表

- `dwd_fct_retail_cust_card_auth_d_delta_aiview`（消费明细，**增量表，pt BETWEEN**）
- `dws_card_cust_trans_date_income_cost_d_aiview`（日级汇总，全量快照）
- `dim_cust_basic_info_ext_d_aiview`（画像，HK/MCV 拆分）

---

## 三、执行流程

1. **确定时间范围**：用户指定或默认近 30 天
2. **查消费明细**（S9）：按日 + HK/MCV 拆分
3. **查收入支出**（S1-S3）：从日级汇总表取
4. **MCC 分析**：`GROUP BY mcc, mcc_desc ORDER BY SUM(trans_amt_hkd) DESC LIMIT 20`
5. **输出**：表格先于图表，HK/MCV 必拆

---

## 四、SQL 模板引用

### S9 · 卡消费总额（按日 + HK/MCV）
```sql
SELECT t1.trans_date, t2.cust_sub_type,
       SUM(t1.trans_amt_hkd) AS trans_amt_hkd,
       COUNT(DISTINCT t1.cust_no) AS trans_cust_cnt,
       COUNT(1) AS trans_cnt
FROM dwd_fct_retail_cust_card_auth_d_delta_aiview t1
LEFT JOIN dim_cust_basic_info_ext_d_aiview t2 ON t1.cust_no = t2.cust_no
WHERE t1.pt BETWEEN '${start_pt}' AND '${end_pt}'
    AND t1.is_successful_auth = '1'
    AND t1.trans_channel <> 'ATM'
GROUP BY t1.trans_date, t2.cust_sub_type
ORDER BY t1.trans_date
```

### S1-S3 · 消费收入/支出/净收入
```sql
SELECT trans_income_fees, trans_cost_fees, trans_net_revenue
FROM dws_card_cust_trans_date_income_cost_d_aiview
WHERE pt = '${pt}'
```

---

## 五、输出格式

| 日期 | HK消费金额 | HK笔数 | HK客户数 | MCV消费金额 | MCV笔数 | MCV客户数 |
|------|-----------|--------|---------|------------|---------|----------|

MCC Top 20 表格附后。
