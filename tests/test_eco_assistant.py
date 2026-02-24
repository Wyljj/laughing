import sqlite3
from pathlib import Path

from eco_assistant import EnvironmentalConsultingAssistant


def test_search_regulations_prefers_national_and_local_with_effective_status():
    assistant = EnvironmentalConsultingAssistant()
    results = assistant.search_regulations("危废 暂存间 标识", region="新疆", top_k=5)
    assert len(results) >= 2
    assert all(r.status == "现行有效" for r in results)
    assert any(r.region == "新疆" for r in results)
    assert any(r.region == "全国" for r in results)


def test_answer_template_requires_at_least_two_citations():
    assistant = EnvironmentalConsultingAssistant()
    profile = {"region": "新疆", "industry": "石油化工"}
    answer = assistant.answer_user_question("危废暂存间要求和依据是什么？", profile)
    assert "【结论摘要】" in answer
    assert "【适用依据（全国→地方）】" in answer
    assert "【风险与边界提示】" in answer


def test_gap_analysis_outputs_five_scene_plan_and_evidence():
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
    gaps = assistant.gap_analysis(profile)
    assert len(gaps) == 5
    assert any(g.plan_days == 7 for g in gaps)
    assert any(g.plan_days == 90 for g in gaps)
    assert all(g.evidence_chain for g in gaps)
    assert all(g.citations for g in gaps)


def test_upload_sqlite_database_as_additional_knowledge(tmp_path: Path):
    db = tmp_path / "regulations.db"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE policy_docs(title TEXT, content TEXT)")
        conn.execute(
            "INSERT INTO policy_docs(title, content) VALUES (?, ?)",
            ("企业危废管理细则", "危废台账应与转移联单保持一致并双人复核"),
        )
        conn.commit()

    assistant = EnvironmentalConsultingAssistant()
    imported = assistant.upload_sqlite_database(db, "policy_docs", "title", "content")
    assert imported == 1

    results = assistant.search_regulations("企业危废管理细则", status="现行有效", top_k=5)
    assert any("企业危废管理细则" in r.doc_title for r in results)


def test_consulting_assessment_report_has_structured_fields():
    assistant = EnvironmentalConsultingAssistant()
    report = assistant.consulting_assessment_report(
        "职业卫生 检测 限值", {"region": "全国", "industry": "职业卫生"}
    )
    assert "咨询评估" in report.summary
    assert report.legal_basis
    assert report.citations
    assert report.evidence_points
