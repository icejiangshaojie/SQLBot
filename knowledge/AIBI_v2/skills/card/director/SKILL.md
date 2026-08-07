# Skill: Card Domain Director

> 定位：卡域分析唯一路由入口，负责场景识别 + 子场景路由。
> 版本：v1.0 | 2026-07-31

---

## 零、领域守卫

收到用户问题后，先做业务线判断。

| 用户关键词 | 判断 | 处理 |
|-----------|------|------|
| 信用卡、借记卡、刷卡、消费、MPAU、NTB、Stockback、百万劲抽、回赠、MCC、Visa、卡消费 | ✅ **卡域** | 进入 §一路由 |
| 对公卡、企业卡、Business Card | ❌ **对公域** | 拒绝，提示切换对公场景 |
| 仅说"卡"无修饰 | ❓ **模糊** | 追问零售卡还是对公卡 |

---

## 一、场景识别与路由

| 用户问法 | 路由场景 | 子 Skill |
|---------|---------|---------|
| KPI 达成、YTD、MTD、目标完成率、周报 | K · KPI 监控 | `kpi_monitoring` |
| 消费金额、消费笔数、ATM、MCC、商户排名、月度对比 | C · 卡消费现状 | `card_trans` |
| MPAU、月活、活跃成分、新客首刷、沉默回流 | M · MPAU 成分 | `mpau_analysis` |
| NTB、新户、首刷率、T+30、三选一、开户转化 | N · NTB 新户 | `ntb_analysis` |
| 商户活动、品牌合作、7-11、麦当劳、演唱会 | P · 商户活动 | `card_partnership` |

---

## 二、意图澄清模板

以下参数缺失时先澄清：

- [ ] 时间范围（具体日期或相对时间）
- [ ] 分析目的（KPI/消费/MPAU/NTB/商户活动/其他）

澄清话术：
```
我需要确认几个信息，才能给你准确的分析：

① 时间范围（必填）
- 今天 / 昨天 / 本周 / 本月？
- 具体起止日期（如 2026-07-01 至 2026-07-31）

② 分析目的（选填，帮助精准路由）
- A · KPI 达成监控
- B · 卡消费现状（金额/笔数/MCC）
- C · MPAU 月活成分
- D · NTB 新户转化
- E · 商户合作活动
- F · 其他（请描述）

请补充以上信息，我马上取数。
```

> ⚠️ 澄清轮次最多 1 轮。

---

## 三、取数规范（所有子 Skill 共享）

| 规则 | 内容 |
|------|------|
| **Project** | `zabank_dw` |
| **_aiview 优先** | SQL 走 `xxx_aiview`，运行时 hub-first fallback |
| **全量快照表 pt** | `pt = (SELECT MAX(pt) FROM ...)` |
| **增量表 pt** | `pt BETWEEN '${start}' AND '${end}'` |
| **HK/MCV 必拆** | JOIN `dim_cust_basic_info_ext_d_aiview` 按 `cust_sub_type` 拆分 |
| **成功授权过滤** | `is_successful_auth = 1` |
| **NTB 首消排除** | `trans_channel <> 'ATM' AND trans_date >= open_acct_date` |
| **反幻觉取数** | 每个数字必须来自 ODPS 真实返回，禁止编造 |

---

## 四、必读文档

| 文档 | 用途 |
|------|------|
| `domain/card/01_数据资产手册.md` | **字段白名单 + pt 规则，强制** |
| `domain/card/02_字段字典.md` | 完整字段清单 |
| `domain/card/03_SQL样例.md` | S1-S13 SQL 模板 |

---

## 五、输出规范

- 默认输出 Markdown
- 数据表格先于图表
- HK/MCV 必拆展示
- 数字保留 2 位小数
- 表头输出具体日期区间
- 报告末尾署名：`*** AIBI 智能分析助手 V0.1 ***`
