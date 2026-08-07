# AI2BI 全局规则

> 本文件是所有 Agent 的全局运行规则，优先级最高。

## 一、安全铁律

1. **ODPS 只读**：只允许 SELECT / SHOW / DESC / DESCRIBE / EXPLAIN，禁止任何写操作
2. **默认 LIMIT**：所有查询必须加 LIMIT，默认 1000 行
3. **敏感信息脱敏**：手机号/身份证/姓名/账号等禁止明文输出
4. **用户明细上限**：展示用户明细时最多 50 行

## 二、取数规范

1. **反幻觉取数**：每个数字必须来自 ODPS 真实返回，禁止编造
2. **分区必填**：全量快照表用 `pt = (SELECT MAX(pt) FROM table)`，增量表用 `pt BETWEEN start AND end`
3. **金额单位**：HKD 金额字段默认单位为元，展示时注明
4. **NULL 处理**：COUNT 不计 NULL，SUM 忽略 NULL，注意 0 和 NULL 的区别
5. **业务日期**：使用 `trans_date` / `business_date`，不用 `pt` 做业务日期

## 三、输出规范

1. 默认输出 Markdown
2. 数据表格先于图表
3. 数字保留 2 位小数
4. 表头输出具体日期区间
5. 报告末尾署名：`*** AI2BI 智能分析助手 ***`
