import sqlite3
from pathlib import Path

DB = Path("sample_regulations.db")

with sqlite3.connect(DB) as conn:
    conn.execute("DROP TABLE IF EXISTS policy_docs")
    conn.execute(
        """
        CREATE TABLE policy_docs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL
        )
        """
    )
    conn.executemany(
        "INSERT INTO policy_docs(title, content) VALUES (?, ?)",
        [
            (
                "工业企业突发环境事件应急预案管理",
                "企业应建立环境应急预案并定期演练，形成演练记录和问题整改闭环。",
            ),
            (
                "危险废物仓库管理制度",
                "危废仓库应防渗防雨，分类存放并建立出入库台账，规范张贴标识。",
            ),
        ],
    )
    conn.commit()

print(f"Created sample db: {DB.resolve()}")
