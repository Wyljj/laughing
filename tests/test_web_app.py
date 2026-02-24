from fastapi.testclient import TestClient

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
