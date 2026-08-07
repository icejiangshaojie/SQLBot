# ODPS SQL 规则

## 一、分区规则

| 表类型 | 分区写法 | 说明 |
|--------|----------|------|
| 全量快照表 | `pt = (SELECT MAX(pt) FROM table_name)` | 取最新分区 |
| 增量表 | `pt BETWEEN 'start' AND 'end'` | 按业务日期范围 |
| 固定分区 | `pt = 'yyyymmdd'` | 指定日期 |

## 二、常见陷阱

1. **pt 不是业务日期**：`pt` 是分区键，业务日期用 `trans_date` / `business_date`
2. **金额单位**：`trans_amt_hkd` 单位是元，不是万
3. **NULL 分组**：`GROUP BY` 会将 NULL 归为一组，注意是否需要 `WHERE field IS NOT NULL`
4. **JOIN 粒度**：先确认左右表粒度，避免笛卡尔积
5. **DISTINCT COUNT**：`COUNT(DISTINCT field)` 在 ODPS 上较慢，大表注意性能

## 三、SQL 安全

1. 只允许 `SELECT / SHOW / DESC / DESCRIBE / EXPLAIN`
2. 禁止 `INSERT / UPDATE / DELETE / DROP / ALTER / CREATE / TRUNCATE`
3. 禁止多语句（分号后多条 SQL）
4. 默认强制 `LIMIT 1000`
5. 禁止 `SELECT *`，必须明确字段列表（DESC 除外）
