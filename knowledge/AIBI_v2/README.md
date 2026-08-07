# AIBI_v2 知识库

> AIBI_v2 是 AI2BI 的**业务知识库**（非代码项目），已并入本仓库 `SQLBot/knowledge/AIBI_v2/`。
> 它与 SQLBot 产品代码分离，作为运行时被后端加载的知识资产。

## 目录结构

```text
knowledge/AIBI_v2/
├── CLAUDE.md              ← 知识库入口与场景索引（原 AIBI_v2 根说明）
├── agents/                ← Agent 定义（如 card_agent.yaml）
├── data/                  ← 通用规则（分析规则/全局规则/SQL 规则）
├── domain/                ← 业务领域知识（card 领域定义、数据资产、字段字典、SQL样例）
├── metrics/               ← 指标定义
├── skills/                ← Skill 场景知识包（_shared 共享 / card 卡域 / director）
└── test_cases/            ← Agent 回归测试用例（routing/sql_regression/evidence）
```

## 加载方式

后端通过 `AIBI_V2_ROOT` 环境变量定位知识库，默认指向 `SQLBot/knowledge/AIBI_v2`：

- `backend/apps/ai2bi/skill_router.py`
- `backend/apps/ai2bi/api.py`
- `backend/apps/ai2bi/test_runner.py`

三个模块从该根目录加载 `skills/`、`data/*.md`、`test_cases/`。

可通过环境变量覆盖，例如：

```bash
export AIBI_V2_ROOT=/path/to/your/knowledge/AIBI_v2
```

## 维护说明

- 知识库是**定义资产**，修改需走业务知识审核，不随一次聊天结果自动变更。
- 新增业务域时，在 `domain/` 建领域定义、在 `skills/` 加 SKILL.md、在 `test_cases/` 加回归用例。
- 与 `docs/ai2bi/08-业务知识录入手册.md` 配合使用。