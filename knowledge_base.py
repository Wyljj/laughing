from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sqlite3
from typing import Iterable


@dataclass(slots=True)
class KBHit:
    doc_id: int
    title: str
    chunk_text: str
    score: int
    source: str


class KnowledgeBase:
    def __init__(self, db_path: str | Path = "kb.sqlite3") -> None:
        self.db_path = Path(db_path)
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  project TEXT NOT NULL,
                  title TEXT NOT NULL,
                  source_path TEXT,
                  created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chunks (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  doc_id INTEGER NOT NULL,
                  chunk_text TEXT NOT NULL,
                  chunk_index INTEGER NOT NULL,
                  FOREIGN KEY(doc_id) REFERENCES documents(id)
                )
                """
            )
            conn.commit()

    def ingest_text(self, project: str, title: str, text: str, source_path: str = "") -> int:
        chunks = self._chunk_text(text)
        if not chunks:
            chunks = [text[:2000]]

        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO documents(project, title, source_path) VALUES (?, ?, ?)",
                (project, title, source_path),
            )
            doc_id = int(cur.lastrowid)
            conn.executemany(
                "INSERT INTO chunks(doc_id, chunk_text, chunk_index) VALUES (?, ?, ?)",
                [(doc_id, chunk, idx) for idx, chunk in enumerate(chunks)],
            )
            conn.commit()
        return doc_id

    def list_documents(self, project: str | None = None) -> list[dict]:
        sql = "SELECT id, project, title, source_path, created_at FROM documents"
        params: tuple = ()
        if project:
            sql += " WHERE project=?"
            params = (project,)
        sql += " ORDER BY id DESC"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [
            {"id": r[0], "project": r[1], "title": r[2], "source_path": r[3], "created_at": r[4]}
            for r in rows
        ]

    def search(self, query: str, project: str | None = None, top_k: int = 5) -> list[KBHit]:
        tokens = self._tokenize(query)
        if not tokens:
            return []

        sql = (
            "SELECT d.id, d.title, c.chunk_text, d.source_path "
            "FROM chunks c JOIN documents d ON c.doc_id=d.id"
        )
        params: tuple = ()
        if project:
            sql += " WHERE d.project=?"
            params = (project,)

        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()

        scored: list[KBHit] = []
        for r in rows:
            txt = r[2]
            score = sum(1 for t in tokens if t in txt)
            if score > 0:
                scored.append(KBHit(doc_id=r[0], title=r[1], chunk_text=txt[:500], score=score, source=r[3] or ""))
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:top_k]

    def _chunk_text(self, text: str, max_chars: int = 700) -> list[str]:
        parts = re.split(r"[\n。；;]", text)
        chunks: list[str] = []
        buf = ""
        for p in parts:
            p = p.strip()
            if not p:
                continue
            if len(buf) + len(p) + 1 > max_chars:
                if buf:
                    chunks.append(buf)
                buf = p
            else:
                buf = f"{buf}\n{p}".strip()
        if buf:
            chunks.append(buf)
        return chunks

    def _tokenize(self, text: str) -> list[str]:
        raw = [t for t in re.split(r"[^\w\u4e00-\u9fff]+", text.lower()) if t]
        out: list[str] = []
        for t in raw:
            if len(t) >= 2:
                out.append(t)
                if re.search(r"[\u4e00-\u9fff]", t) and len(t) >= 4:
                    out.extend(t[i : i + 2] for i in range(len(t) - 1))
        return list(dict.fromkeys(out))
