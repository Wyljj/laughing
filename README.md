# 全国环保 + 职业卫生咨询助手（MVP）

本项目是“法规检索 + 危废合规建议 + 咨询评估能力底座”的可运行样例。

## 目标能力

- **法规检索（全国可用）**：条款级检索，支持地区/行业/污染因子过滤。
- **危废合规建议（闭环）**：5大场景问诊，输出 Gap + 7/30/90天整改计划 + 证据链。
- **咨询评估底座**：可生成结构化评估结果（摘要、依据、建议、证据、引用）。
- **职业卫生扩展位**：底层法规元数据兼容职业卫生标准（如 GBZ 系列）。

## 输出硬规则

1. 无引用不下结论（至少 2 条有效依据）。
2. 仅提供“依据 + 一般要求 + 建议动作”，不作法律裁决。
3. 处罚/停产/刑责边界自动触发复核提示。

## 法规元数据（RAG 最小字段）

每个条款块至少包含：

- `doc_title`
- `doc_type`
- `issuer`
- `region` / `region_code`
- `industry_tags`
- `effective_date` / `expire_date`
- `status`
- `article_id`
- `source_url`

## 快速运行

```bash
python eco_assistant.py
```

## 运行测试

```bash
pytest -q
```

## 作为模块使用

```python
from eco_assistant import EnvironmentalConsultingAssistant

assistant = EnvironmentalConsultingAssistant()

profile = {
    "region": "新疆",
    "industry": "石油化工",
    "has_hw_identification": False,
    "has_haz_waste_room": False,
    "has_transfer_manifest": False,
    "has_training": False,
    "vendor_qualified": False,
}

print(assistant.answer_user_question("危废暂存间需要满足哪些要求？依据是什么？", profile))
print(assistant.generate_compliance_advice(profile))
```
