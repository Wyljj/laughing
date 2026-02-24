from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from eco_assistant import EnvironmentalConsultingAssistant
from model_gateway import ModelGateway
from knowledge_base import KnowledgeBase


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
AUDIT_LOG = BASE_DIR / "audit_log.jsonl"
UPLOAD_DIR.mkdir(exist_ok=True)

app = FastAPI(title="环保咨询工作台", version="0.1.0")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "web" / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "web" / "templates"))
assistant = EnvironmentalConsultingAssistant()
model_gateway = ModelGateway()
kb = KnowledgeBase(BASE_DIR / "kb.sqlite3")

# 简化示例 RBAC（生产建议换 JWT + 用户中心）
TOKENS = {
    "admin-token": {"role": "admin", "name": "管理员"},
    "consultant-token": {"role": "consultant", "name": "咨询师"},
    "viewer-token": {"role": "viewer", "name": "访客"},
}


def _auth(token: str):
    user = TOKENS.get(token)
    if not user:
        raise HTTPException(status_code=401, detail="invalid token")
    return user


def _audit(action: str, token: str, payload: dict):
    record = {
        "ts": datetime.utcnow().isoformat(),
        "action": action,
        "token": token,
        "payload": payload,
    }
    with AUDIT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {})


@app.post("/api/chat")
def chat(payload: dict):
    token = payload.get("token", "")
    user = _auth(token)

    question = payload.get("question", "")
    profile = payload.get("profile", {})
    if not question:
        raise HTTPException(status_code=400, detail="question required")

    grounded_answer = assistant.answer_user_question(question, profile)
    answer = model_gateway.generate(question=question, profile=profile, grounded_answer=grounded_answer)
    _audit("chat", token, {"role": user["role"], "question": question, "profile": profile})
    return JSONResponse({"answer": answer, "backend": model_gateway.backend or "none"})


@app.post("/api/gap")
def gap(payload: dict):
    token = payload.get("token", "")
    user = _auth(token)

    profile = payload.get("profile", {})
    result = assistant.generate_compliance_advice(profile)
    _audit("gap", token, {"role": user["role"], "profile": profile})
    return JSONResponse({"result": result})


@app.post("/api/upload")
async def upload_file(
    token: str = Form(...),
    project: str = Form("default-project"),
    file: UploadFile = File(...),
):
    user = _auth(token)
    if user["role"] not in ("admin", "consultant"):
        raise HTTPException(status_code=403, detail="forbidden")

    project_dir = UPLOAD_DIR / project
    project_dir.mkdir(parents=True, exist_ok=True)
    target = project_dir / file.filename
    content = await file.read()
    target.write_bytes(content)

    doc_id = None
    if target.suffix.lower() in {".txt", ".md", ".csv"}:
        text = content.decode("utf-8", errors="ignore")
        if text.strip():
            doc_id = kb.ingest_text(project=project, title=file.filename, text=text, source_path=str(target))

    _audit(
        "upload",
        token,
        {
            "role": user["role"],
            "project": project,
            "filename": file.filename,
            "size": len(content),
            "doc_id": doc_id,
        },
    )
    return JSONResponse({"saved": str(target.relative_to(BASE_DIR)), "doc_id": doc_id})


@app.get("/api/audit")
def audit(token: str):
    user = _auth(token)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="forbidden")

    if not AUDIT_LOG.exists():
        return JSONResponse({"records": []})
    records = [json.loads(line) for line in AUDIT_LOG.read_text(encoding="utf-8").splitlines() if line.strip()]
    return JSONResponse({"records": records[-200:]})


@app.post("/api/kb/ingest")
def kb_ingest(payload: dict):
    token = payload.get("token", "")
    user = _auth(token)
    if user["role"] not in ("admin", "consultant"):
        raise HTTPException(status_code=403, detail="forbidden")

    project = payload.get("project", "default-project")
    title = payload.get("title", "untitled")
    text = payload.get("text", "")
    if not text.strip():
        raise HTTPException(status_code=400, detail="text required")

    doc_id = kb.ingest_text(project=project, title=title, text=text, source_path="manual")
    _audit("kb_ingest", token, {"project": project, "title": title, "doc_id": doc_id})
    return JSONResponse({"doc_id": doc_id})


@app.get("/api/kb/list")
def kb_list(token: str, project: str | None = None):
    _auth(token)
    docs = kb.list_documents(project=project)
    return JSONResponse({"documents": docs})


@app.post("/api/kb/search")
def kb_search(payload: dict):
    token = payload.get("token", "")
    _auth(token)
    query = payload.get("query", "")
    project = payload.get("project")
    if not query:
        raise HTTPException(status_code=400, detail="query required")

    hits = kb.search(query=query, project=project, top_k=int(payload.get("top_k", 5)))
    return JSONResponse(
        {
            "hits": [
                {
                    "doc_id": h.doc_id,
                    "title": h.title,
                    "chunk_text": h.chunk_text,
                    "score": h.score,
                    "source": h.source,
                }
                for h in hits
            ]
        }
    )
