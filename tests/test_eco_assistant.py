import sqlite3
from pathlib import Path

from eco_assistant import EnvironmentalConsultingAssistant


def test_search_regulations_returns_results():
    assistant = EnvironmentalConsultingAssistant()
    results = assistant.search_regulations("排污许可 监测")
    assert results
    assert any("排污许可" in r.title for r in results)


def test_upload_sqlite_database(tmp_path: Path):
    db = tmp_path / "regulations.db"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE policy_docs(title TEXT, content TEXT)")
        conn.execute(
            "INSERT INTO policy_docs(title, content) VALUES (?, ?)",
            ("企业自行监测管理", "企业应按许可证要求开展监测并留存台账"),
        )
        conn.commit()

    assistant = EnvironmentalConsultingAssistant()
    count = assistant.upload_sqlite_database(db, "policy_docs", "title", "content")
    assert count == 1

    results = assistant.search_regulations("自行监测 台账")
    assert any("企业自行监测管理" == r.title for r in results)


def test_generate_compliance_advice_contains_sources():
    assistant = EnvironmentalConsultingAssistant()
    advice = assistant.generate_compliance_advice(
        industry="化工",
        pollutants=["VOC", "COD"],
        has_permit=False,
        has_monitoring_plan=False,
    )
    assert "建议核验来源" in advice
    assert "https://permit.mee.gov.cn/" in advice
