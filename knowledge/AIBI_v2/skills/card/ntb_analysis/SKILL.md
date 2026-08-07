# Skill: NTB 新户转化 (ntb_analysis)

> 场景 N · 新开户客户 T+14/T+30 首刷率、月度趋势、维度下钻
> 版本：v1.0 | 2026-07-31

---

## 一、输入识别

| 用户问法 | 分析类型 |
|---------|---------|
| NTB 首刷率 / T+30 | A · 现状快照 |
| NTB 月度趋势 | B · 月度趋势 |
| NTB 渠道/三选一下钻 | C · 维度下钻 |

---

## 二、核心表

- `dim_card_ntb_tag_d_aiview`（NTB 维表，**全量快照**）
- `dwd_fct_retail_cust_card_auth_d_delta_aiview`（消费明细，**增量表**）

---

## 三、NTB 铁律（P0）

| 规则 | 内容 |
|------|------|
| **分母口径** | 必须 `open_full_30d=1`（或 `open_full_14d=1`），缺一不可 |
| **默认观察窗口** | T+30（业务方锁定，支持 T+14/T+30 自定义） |
| **默认开户窗口** | 最新可用月份（`open_full_30d=1` 的最大开户月） |
| **HK/MCV 必拆** | 按 `cust_sub_type` 分图分表 |
| **首消排除** | `is_successful_auth=1 AND trans_channel<>'ATM' AND trans_date>=open_acct_date` |
| **first_plan 限制** | `first_stb_plan_apply_time`/`first_pd_plan_apply_time` 时强制 `open_acct_date>='2025-10-24'` |
| **三选一分母** | `gift_flag` 切片限 `open_apply_channel IN ('Organic','Paidmedia')`；`tag_code` 切片必叠 `gift_flag=1` |
| **渠道合并** | Organic+Paidmedia→`Organic(merge)`；MGM+渠道邀请码→`MGM(merge)` |
| **分区探测** | 每次执行前 `SELECT MAX(pt)` 探测最新分区 |

---

## 四、SQL 模板引用

### S11 · NTB 新户 T+30 首刷率
```sql
SELECT t1.cust_sub_type, t1.open_apply_channel,
       COUNT(DISTINCT t1.cust_no) AS total_cust,
       COUNT(DISTINCT CASE WHEN t2.cust_no IS NOT NULL THEN t1.cust_no END) AS first_trans_cust,
       ROUND(COUNT(DISTINCT CASE WHEN t2.cust_no IS NOT NULL THEN t1.cust_no END)*100.0
            /COUNT(DISTINCT t1.cust_no), 2) AS first_trans_rate
FROM dim_card_ntb_tag_d_aiview t1
LEFT JOIN (
    SELECT DISTINCT cust_no
    FROM dwd_fct_retail_cust_card_auth_d_delta_aiview
    WHERE pt BETWEEN '${start_pt}' AND '${end_pt}'
        AND is_successful_auth='1'
        AND trans_channel<>'ATM'
        AND trans_date>=open_acct_date
) t2 ON t1.cust_no=t2.cust_no
WHERE t1.pt=(SELECT MAX(pt) FROM dim_card_ntb_tag_d_aiview)
    AND t1.open_full_30d=1
GROUP BY t1.cust_sub_type, t1.open_apply_channel
```

---

## 五、输出格式

| 客户类型 | 渠道 | 总开户数 | 首刷客户数 | 首刷率 |
|---------|------|---------|-----------|--------|
| HK客户 | Organic | ... | ... | ... |
| HK客户 | Paidmedia | ... | ... | ... |
| MCV客户 | Organic | ... | ... | ... |

三选一（gift_flag / tag_code）维度**不主动输出**，用户明确问才展示。
