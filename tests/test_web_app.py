from fastapi.testclient import TestClient

import web_app
from web_app import app


client = TestClient(app)


def test_index_page():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "环保咨询工作台" in resp.text


def test_chat_requires_token_and_returns_answer():
    resp = client.post(
        "/api/chat",
        json={
            "token": "consultant-token",
            "question": "危废暂存间要求和依据是什么？",
            "profile": {"region": "新疆", "industry": "石油化工"},
        },
    )
    assert resp.status_code == 200
    assert "结论摘要" in resp.json()["answer"]
    assert "backend" in resp.json()


def test_gap_endpoint():
    resp = client.post(
        "/api/gap",
        json={
            "token": "consultant-token",
            "profile": {
                "region": "新疆",
                "industry": "石油化工",
                "has_hw_identification": False,
                "has_haz_waste_room": False,
                "has_transfer_manifest": False,
                "has_training": False,
                "vendor_qualified": False,
            },
        },
    )
    assert resp.status_code == 200
    assert "Gap清单" in resp.json()["result"]


def test_chat_uses_model_gateway_when_enabled(monkeypatch):
    def fake_generate(question, profile, grounded_answer):
        return "模型增强回复"

    monkeypatch.setattr(web_app.model_gateway, "generate", fake_generate)
    monkeypatch.setattr(web_app.model_gateway, "backend", "ollama")

    resp = client.post(
        "/api/chat",
        json={
            "token": "consultant-token",
            "question": "测试模型增强",
            "profile": {"region": "全国", "industry": "通用"},
        },
    )
    assert resp.status_code == 200
    assert resp.json()["answer"] == "模型增强回复"
    assert resp.json()["backend"] == "ollama"


def test_kb_ingest_search_list_flow():
    ingest = client.post(
        "/api/kb/ingest",
        json={
            "token": "consultant-token",
            "project": "demo-project",
            "title": "危废管理制度",
            "text": "危废暂存间应防渗防雨并设置标识，台账与联单一致。",
        },
    )
    assert ingest.status_code == 200
    doc_id = ingest.json()["doc_id"]
    assert doc_id > 0

    listed = client.get("/api/kb/list", params={"token": "consultant-token", "project": "demo-project"})
    assert listed.status_code == 200
    assert any(d["id"] == doc_id for d in listed.json()["documents"])

    search = client.post(
        "/api/kb/search",
        json={"token": "consultant-token", "project": "demo-project", "query": "防渗 标识 台账"},
    )
    assert search.status_code == 200
    assert search.json()["hits"]
