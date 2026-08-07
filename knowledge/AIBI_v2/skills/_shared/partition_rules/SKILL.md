# Skill: ODPS 分区规则模板 (partition_rules)

> 跨域共享 Skill · 适用于所有 ODPS 查询
> 版本：v1.0 | 2026-08-03

---

## 一、分区规则

| 表类型 | 分区写法 | 说明 |
|--------|----------|------|
| 全量快照表 | `pt = (SELECT MAX(pt) FROM table_name)` | 取最新分区 |
| 增量表 | `pt BETWEEN 'start' AND 'end'` | 按业务日期范围 |
| 固定分区 | `pt = 'yyyymmdd'` | 指定日期 |

## 二、常见错误

1. ❌ 不加分区条件 → ODPS 全表扫描，性能极差
2. ❌ 用 pt 当业务日期 → `pt` 是分区键，业务日期用 `trans_date` / `business_date`
3. ❌ 增量表只写 `pt = max` → 增量表需指定日期范围

## 三、判断表类型

- 表名含 `_delta` → 增量表，必须 `pt BETWEEN`
- 表名不含 `_delta` → 通常为全量快照表，使用 `pt = MAX(pt)`

## 四、SQL 参考

```sql
-- 全量快照表
WHERE pt = (SELECT MAX(pt) FROM dim_cust_basic_info_ext_d)

-- 增量表
WHERE pt BETWEEN '20260701' AND '20260731'

-- 子查询方式取全量最新
WHERE t1.pt = (SELECT MAX(pt) FROM dwd_fct_retail_cust_card_auth_d_delta WHERE pt >= '20260701')
```
