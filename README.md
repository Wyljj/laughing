# 环保咨询助手（Environmental Consulting Assistant）

一个面向企业环保合规场景的本地助手，重点解决：

1. **环保法规查询（可追溯）**：输出条款级引用、原文摘录、生效状态。  
2. **企业合规建议（可执行 + 可审计）**：输出 Gap 分析、整改计划、证据材料包、时限与责任人。  
3. **上传数据库**：导入企业内部 SQLite 数据，补充制度与台账规则。

## 数据来源（内置参考）

- 生态环境部（法规标准）：https://www.mee.gov.cn/ywgz/fgbz/
- 排污许可专题：https://www.mee.gov.cn/ywgz/pwxkgl/
- 全国排污许可证管理信息平台（公开端）：https://permit.mee.gov.cn/

## 核心能力（MVP）

- 法规/标准检索（支持地区、行业、污染因子、生效状态过滤）
- 条款级定位（第几条/章节）
- 结构化结果输出：适用范围、关键义务、禁止事项、法律责任、执行要点
- 强制引用输出：结论绑定条款来源
- 合规差距分析：排污许可、自行监测、危废规范化、环评验收等高频场景
- 整改方案：7/30/90 天行动计划 + 证据清单 + 责任人

## 安全边界（硬规则）

- 不做法律结论：统一使用“依据…一般需要/建议…”表达
- 高风险事项（处罚/停产/刑责）需提示法务/第三方复核
- 无引用不输出结论

## 快速开始

```bash
python eco_assistant.py
```

会演示 3 个典型问题：

- 危废暂存间要求与依据
- 排污许可中自行监测频次/因子
- 新增产线的环评/验收/排污许可流程与风险

## 作为模块使用

```python
from eco_assistant import EnvironmentalConsultingAssistant

assistant = EnvironmentalConsultingAssistant()

profile = {
    "region": "新疆",
    "industry": "石油化工",
    "pollutants": ["VOC", "COD"],
    "has_permit": False,
    "has_monitoring_plan": False,
    "has_haz_waste_room": False,
    "has_eia_acceptance": False,
}

# 1) 法规查询（带引用）
results = assistant.search_regulations(
    query="危废暂存间 标识 台账",
    region="新疆",
    industry="石油化工",
)
for item in results:
    print(item.title, item.citation, item.effective_status)

# 2) 合规问答（条款摘录 + 引用）
print(assistant.answer_user_question("危废暂存间需要满足哪些要求？依据是什么？", profile))

# 3) Gap 分析与整改方案
print(assistant.generate_compliance_advice(profile))

# 4) 上传企业数据库
count = assistant.upload_sqlite_database(
    db_path="sample_regulations.db",
    table="policy_docs",
    title_col="title",
    content_col="content",
    source_name="企业上传数据库",
)
print("导入条数:", count)
```

## 构造测试数据库

```bash
python scripts/create_sample_db.py
```

将生成 `sample_regulations.db`，可用于演示“上传数据库”能力。
