# Skill: 成功授权过滤 (success_auth_filter)

> 跨域共享 Skill · 适用于零售卡交易场景
> 版本：v1.0 | 2026-08-03

---

## 一、定义

**成功授权**（is_successful_auth = 1）是零售卡交易的硬过滤条件。

只有成功授权的交易才计入"卡消费金额"、"卡消费笔数"等核心指标。

## 二、执行规则

1. **硬过滤**：所有涉及卡消费金额/笔数的查询，必须加 `is_successful_auth = '1'`
2. **字符类型**：字段值为字符串，必须用 `'1'` 而非 `1`
3. **NOT NULL 补充**：如果 is_successful_auth 为 NULL，视为非成功授权
4. **禁用场景**：查询"授权失败率"等场景可移除此过滤，但需在输出中说明

## 三、SQL 参考

```sql
WHERE t1.is_successful_auth = '1'
```

## 四、关联排除

- ATM 取现排除：`AND t1.trans_channel <> 'ATM'`
- NTB 首消场景：`AND t1.trans_channel <> 'ATM'`
