"""
Import Card domain knowledge into SQLBot metadata DB.
- Terminology: business terms from field dictionary
- Data Training: SQL examples from 03_SQL样例.md
- Custom Prompt: hard rules from director SKILL.md
- CoreTable: register Card whitelist tables on ODPS datasource (id=3)
"""

import json
from datetime import datetime
from sqlmodel import Session, select
from common.core.db import engine
from apps.terminology.models.terminology_model import Terminology
from apps.data_training.models.data_training_model import DataTraining
from apps.datasource.models.datasource import CoreTable, CoreField

# ─── 1. Terminology ───────────────────────────────────────

TERMS = [
    # (word, description, oid)
    ("MPAU", "月活用户数 (Monthly Persistent Active Users)。统计口径：近30日有至少1笔成功授权消费的客户数。字段：is_30d_mpau。", 1),
    ("NTB", "New to Bank 新户。指首次开户的客户，通常用于首刷转化分析。关联表：dim_card_ntb_tag_d。", 1),
    ("首刷", "新户首次成功授权消费。NTB首刷率 = 首刷客户数 / 新开户数。排除ATM渠道。", 1),
    ("HK", "香港客户 (cust_sub_type = 'HK')。卡域分析必须按 HK/MCV 拆分展示。", 1),
    ("MCV", "澳门客户 (cust_sub_type = 'MCV')。卡域分析必须按 HK/MCV 拆分展示。", 1),
    ("Stockback", "卡消费回馈活动。用户通过消费获得stockback奖励。", 1),
    ("MCC", "Merchant Category Code 商户类别码。用于分析消费场景（餐饮/购物/出行等）。", 1),
    ("trans_amt_hkd", "卡消费金额（港币）。单位：元。仅统计 is_successful_auth = 1 的交易。", 1),
    ("is_successful_auth", "成功授权标志。1=成功，0=失败。卡消费统计必须过滤 is_successful_auth = 1。", 1),
    ("pt", "ODPS分区字段。全量快照表用 pt = (SELECT MAX(pt) FROM table)，增量表用 pt BETWEEN start AND end。pt不是业务日期。", 1),
    ("trans_date", "业务交易日期。格式 yyyy-mm-dd。用于按日期范围筛选交易，不要用 pt 做业务日期。", 1),
    ("cust_no", "客户号。卡域主键之一，用于关联客户基础信息表拆分 HK/MCV。", 1),
    ("cust_sub_type", "客户子类型。HK=香港客户，MCV=澳门客户。卡域必须按此字段拆分展示。", 1),
    ("KPI", "Key Performance Indicator 关键绩效指标。卡域KPI包括：发卡量、激活率、首刷率、MPAU、消费金额。", 1),
    ("百万劲抽", "卡消费营销活动。按活动期间统计参与客户数和消费金额。", 1),
    ("YTD", "Year to Date 年初至今。用于KPI达成率计算。", 1),
    ("MTD", "Month to Date 月初至今。用于KPI达成率计算。", 1),
    ("open_acct_date", "开户日期。NTB首刷分析的分母基准。字段来自 dim_card_ntb_tag_d。", 1),
    ("dwd_fct_retail_cust_card_auth_d_delta", "卡授权明细增量表。包含每笔卡消费交易详情：金额、商户、MCC、渠道。分区：pt BETWEEN。", 1),
    ("dim_card_ntb_tag_d", "NTB新户标签表（全量快照）。包含开户日期、首刷时间、绑卡时间等。分区：pt = MAX(pt)。", 1),
    ("dim_cust_basic_info_ext_d", "客户基础信息扩展表（全量快照）。用于按 cust_sub_type 拆分 HK/MCV。分区：pt = MAX(pt)。", 1),
    ("dws_card_cust_trans_label_info_d", "卡消费汇总标签表（全量快照）。MPAU主表，含月度消费汇总和MPAU标签。分区：pt = MAX(pt)。", 1),
]

# ─── 2. Data Training (SQL examples) ──────────────────────

TRAINING = [
    # (question, description/sql, datasource_id, oid)
    (
        "本月卡消费总金额是多少",
        "SELECT SUM(`t1`.`trans_amt_hkd`) AS `total_amount` FROM `dwd_fct_retail_cust_card_auth_d_delta` `t1` WHERE `t1`.`pt` BETWEEN FORMATDATETIME(NOW(), 'yyyyMMdd') AND FORMATDATETIME(NOW(), 'yyyyMMdd') AND `t1`.`is_successful_auth` = 1 LIMIT 1000",
        3, 1,
    ),
    (
        "7月卡消费金额按HK和MCV拆分",
        "SELECT `c`.`cust_sub_type` AS `customer_type`, SUM(`t1`.`trans_amt_hkd`) AS `total_amount` FROM `dwd_fct_retail_cust_card_auth_d_delta` `t1` JOIN `dim_cust_basic_info_ext_d` `c` ON `t1`.`cust_no` = `c`.`cust_no` WHERE `t1`.`pt` BETWEEN '20260701' AND '20260731' AND `t1`.`is_successful_auth` = 1 AND `c`.`pt` = (SELECT MAX(`pt`) FROM `dim_cust_basic_info_ext_d`) GROUP BY `c`.`cust_sub_type` ORDER BY `total_amount` DESC LIMIT 1000",
        3, 1,
    ),
    (
        "本月MPAU有多少",
        "SELECT COUNT(DISTINCT `t1`.`cust_no`) AS `mpau_count` FROM `dws_card_cust_trans_label_info_d` `t1` WHERE `t1`.`pt` = (SELECT MAX(`pt`) FROM `dws_card_cust_trans_label_info_d`) AND `t1`.`is_30d_mpau` = 'Y' LIMIT 1000",
        3, 1,
    ),
    (
        "NTB新户首刷转化率",
        "SELECT COUNT(DISTINCT CASE WHEN `t1`.`first_trans_card_time` IS NOT NULL THEN `t1`.`cust_no` END) * 100.0 / COUNT(DISTINCT `t1`.`cust_no`) AS `first_trans_rate` FROM `dim_card_ntb_tag_d` `t1` WHERE `t1`.`pt` = (SELECT MAX(`pt`) FROM `dim_card_ntb_tag_d`) LIMIT 1000",
        3, 1,
    ),
    (
        "最近一周卡消费按MCC排名前10",
        "SELECT `t1`.`mcc` AS `mcc`, SUM(`t1`.`trans_amt_hkd`) AS `total_amount` FROM `dwd_fct_retail_cust_card_auth_d_delta` `t1` WHERE `t1`.`pt` BETWEEN '20260725' AND '20260731' AND `t1`.`is_successful_auth` = 1 GROUP BY `t1`.`mcc` ORDER BY `total_amount` DESC LIMIT 10",
        3, 1,
    ),
]

# ─── 3. Custom Prompt (hard rules) ────────────────────────

CARD_RULES = """
## 卡域分析硬规则（必须遵守）

### 1. 分区规则
- 全量快照表（dim_*/dws_*）：必须使用 `pt = (SELECT MAX(pt) FROM table_name)`
- 增量表（dwd_fct_*_delta）：必须使用 `pt BETWEEN 'start' AND 'end'`
- 禁止不带分区条件查询全量表

### 2. HK/MCV 拆分
- 卡消费统计必须按 cust_sub_type 拆分 HK 和 MCV
- JOIN dim_cust_basic_info_ext_d 获取 cust_sub_type
- 该表也是全量快照，需要加 pt = MAX(pt)

### 3. 成功授权过滤
- 卡消费金额统计必须过滤 `is_successful_auth = 1`
- NTB首刷场景额外排除 ATM 渠道：`trans_channel <> 'ATM'`

### 4. 金额单位
- trans_amt_hkd 单位为元，不是万
- 展示时标注"HKD"

### 5. 表白名单
- 卡域只能使用以下表：
  - dwd_fct_retail_cust_card_auth_d_delta (卡授权明细，增量)
  - dim_card_ntb_tag_d (NTB标签，全量)
  - dim_cust_basic_info_ext_d (客户基础信息，全量)
  - dws_card_cust_trans_label_info_d (消费汇总标签，全量)
- 禁止使用对公表（zabank_ai2bi_hub 下的表）
- 禁止 JOIN 零售 user_id 和对公 cust_no

### 6. 输出规范
- 数据表格先于图表
- HK/MCV 必须拆分展示
- 数字保留2位小数
- 表头输出具体日期区间
"""

# ─── 4. Card whitelist tables ─────────────────────────────

CARD_TABLES = [
    "dwd_fct_retail_cust_card_auth_d_delta",
    "dim_card_ntb_tag_d",
    "dim_cust_basic_info_ext_d",
    "dws_card_cust_trans_label_info_d",
]


def import_all():
    from sqlalchemy import text
    with Session(engine) as session:
        # ── Terminology (use raw SQL to bypass VECTOR column) ──
        existing_terms = {t.word for t in session.exec(select(Terminology)).all()}
        new_terms = 0
        for word, desc, oid in TERMS:
            if word not in existing_terms:
                session.execute(text(
                    "INSERT INTO terminology (oid, create_time, word, description, specific_ds, datasource_ids, enabled) "
                    "VALUES (:oid, :now, :word, :desc, false, '[]'::jsonb, true)"
                ), {"oid": oid, "now": datetime.now(), "word": word, "desc": desc})
                new_terms += 1
        session.commit()
        print(f"Terminology: {new_terms} new entries imported")

        # ── Data Training (use raw SQL to bypass VECTOR column) ──
        existing_training = {t.question for t in session.exec(select(DataTraining)).all()}
        new_training = 0
        for question, sql, ds_id, oid in TRAINING:
            if question not in existing_training:
                session.execute(text(
                    "INSERT INTO data_training (oid, datasource, create_time, question, description, enabled) "
                    "VALUES (:oid, :ds, :now, :q, :desc, true)"
                ), {"oid": oid, "ds": ds_id, "now": datetime.now(), "q": question, "desc": sql})
                new_training += 1
        session.commit()
        print(f"Data Training: {new_training} new entries imported")

        # ── Custom Prompt (use raw SQL) ──
        from sqlalchemy import text as _text
        existing_cp = session.execute(_text(
            "SELECT id FROM custom_prompt WHERE name = :name"
        ), {"name": "卡域分析硬规则"}).first()
        if not existing_cp:
            session.execute(_text(
                "INSERT INTO custom_prompt (oid, type, create_time, name, prompt, specific_ds, datasource_ids) "
                "VALUES (1, 'generate_sql', :now, :name, :prompt, false, '[]'::jsonb)"
            ), {"now": datetime.now(), "name": "卡域分析硬规则", "prompt": CARD_RULES})
            session.commit()
            print("Custom Prompt: '卡域分析硬规则' imported")
        else:
            session.execute(_text(
                "UPDATE custom_prompt SET prompt = :prompt WHERE name = :name"
            ), {"prompt": CARD_RULES, "name": "卡域分析硬规则"})
            session.commit()
            print("Custom Prompt: '卡域分析硬规则' updated")

        # ── CoreTable (Card whitelist on ODPS datasource id=3) ──
        existing_tables = {
            t.table_name for t in session.exec(
                select(CoreTable).where(CoreTable.ds_id == 3)
            ).all()
        }
        new_tables = 0
        for table_name in CARD_TABLES:
            if table_name not in existing_tables:
                session.add(CoreTable(
                    ds_id=3,
                    table_name=table_name,
                    table_comment="",
                    checked=True,
                ))
                new_tables += 1
        session.commit()
        print(f"CoreTable: {new_tables} new tables registered on ODPS datasource")

        # ── Summary ──
        term_count = len(session.exec(select(Terminology)).all())
        train_count = len(session.exec(select(DataTraining)).all())
        table_count = len(session.exec(select(CoreTable).where(CoreTable.ds_id == 3)).all())
        print(f"\n=== Summary ===")
        print(f"  Terminology total: {term_count}")
        print(f"  Data Training total: {train_count}")
        print(f"  ODPS CoreTable: {table_count}")


if __name__ == "__main__":
    import_all()
