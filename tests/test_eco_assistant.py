import sqlite3
from pathlib import Path

from eco_assistant import EnvironmentalConsultingAssistant


def test_search_regulations_with_citation_and_status():
    assistant = EnvironmentalConsultingAssistant()
    results = assistant.search_regulations(
        query="排污许可 自行监测",
        region="新疆",
        industry="石油化工",
        top_k=3,
    )
    assert results
    assert all("来源：" in r.citation for r in results)
    assert all(r.effective_status == "生效" for r in results)


def test_upload_sqlite_database_as_enterprise_knowledge(tmp_path: Path):
    db = tmp_path / "regulations.db"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE policy_docs(title TEXT, content TEXT)")
        conn.execute(
            "INSERT INTO policy_docs(title, content) VALUES (?, ?)",
            ("企业自行监测管理制度", "VOC与COD应按周监测并留存原始记录"),
        )
        conn.commit()

    assistant = EnvironmentalConsultingAssistant()
    count = assistant.upload_sqlite_database(db, "policy_docs", "title", "content")
    assert count == 1

    results = assistant.search_regulations("企业自行监测管理制度")
    assert any("企业自行监测管理制度" in r.title for r in results)


def test_gap_analysis_and_advice_include_plan_and_boundary():
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

    gaps = assistant.gap_analysis(profile)
    assert len(gaps) >= 3
    assert any(g.risk_level == "高" for g in gaps)
    assert all(g.references for g in gaps)

    advice = assistant.generate_compliance_advice(profile)
    assert "Gap Analysis" in advice
    assert "不构成法律结论" in advice
    assert "法务或第三方机构复核" in advice


def test_answer_user_question_returns_traceable_quotes():
    assistant = EnvironmentalConsultingAssistant()
    profile = {"region": "新疆", "industry": "石油化工"}
    answer = assistant.answer_user_question("危废暂存间需要满足哪些要求？依据是什么？", profile)
    assert "条款摘录" in answer
    assert "引用：" in answer
