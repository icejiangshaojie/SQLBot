---
skill_id: corp_deposit_balance_overview
skill_name: 对公存款余额概览
version: "0.1.0"
status: draft
domain_ref: corp_deposit
agent_ref: corp_deposit_agent
layer: L2_scenario
owner: business.owner@example.com
triggered_by:
  - 存款余额
  - 日均余额
  - 存款趋势
not_applicable_when:
  - 用户实际询问零售存款或理财
input_contract:
  metric_refs:
    - corp_deposit.average_daily_balance
  required_dimensions: []
  required_conditions:
    - 已确认时间范围
output_contract:
  mode: sql_and_analysis
  analysis_templates:
    - summary
    - trend
    - ranking
    - structure_split
  required_sections:
    - 结论
    - 基本分析
    - 口径与范围
    - 证据标注汇总
asset_refs:
  table_refs:
    - corp_deposit.dws_customer_daily_balance
  metric_refs:
    - corp_deposit.average_daily_balance
  rule_refs:
    - corp_deposit.valid_customer
  sql_template_refs:
    - corp_deposit.monthly_average_balance
---

# 业务背景

填写本场景的业务定义、使用范围和用户可理解的说明。

# 推荐分析步骤

1. 确认用户询问的是时点余额、日均余额还是月均余额。
2. 确认时间范围、客群和币种。
3. 执行汇总查询；用户要求“情况怎么样”时，在 AnalysisPlan 内追加趋势或结构查询。
4. 由后端分析引擎计算日均、峰谷、占比或排名等事实。
5. LLM 仅解释 AnalysisFacts，并标注来源。

# 注意事项

- 不得用单月汇总数据声称存在趋势。
- 没有比较周期时不得输出同比或环比。
- 不得把余额波动直接归因为某项经营活动。

# 正例

- “2026 年 7 月对公日均存款余额是多少？”
- “7 月对公存款余额趋势怎么样？”

# 反例

- “预测下个月存款余额。”
- “为什么余额下降？”没有专项归因资产时只能说明已观察到的变化。
