# 环保咨询助手（Environmental Consulting Assistant）

一个可本地运行的轻量级环保咨询助手，支持：

- **环保法规查询**：按关键词检索法规要点。
- **企业合规建议**：根据企业行业与排污信息生成整改/合规建议。
- **上传数据库**：导入企业内部 SQLite 数据库中的制度或法规文本，扩展知识库。

## 数据来源（内置参考）

- 生态环境部（法规标准）：https://www.mee.gov.cn/ywgz/fgbz/
- 排污许可专题：https://www.mee.gov.cn/ywgz/pwxkgl/
- 全国排污许可证管理信息平台（公开端）：https://permit.mee.gov.cn/

## 快速开始

```bash
python eco_assistant.py
```

## 作为模块使用

```python
from eco_assistant import EnvironmentalConsultingAssistant

assistant = EnvironmentalConsultingAssistant()

# 1) 法规检索
results = assistant.search_regulations("排污许可 监测 台账")
for doc in results:
    print(doc.title, doc.source)

# 2) 上传 SQLite 数据库（示例：policy_docs 表）
count = assistant.upload_sqlite_database(
    db_path="sample_regulations.db",
    table="policy_docs",
    title_col="title",
    content_col="content",
    source_name="企业上传数据库",
)
print("导入条数:", count)

# 3) 生成企业合规建议
advice = assistant.generate_compliance_advice(
    industry="电子制造",
    pollutants=["VOC", "COD"],
    has_permit=False,
    has_monitoring_plan=False,
)
print(advice)
```

## 构造测试数据库

```bash
python scripts/create_sample_db.py
```

将生成 `sample_regulations.db`，可用于演示“上传数据库”能力。
