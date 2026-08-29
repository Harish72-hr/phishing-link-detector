from __future__ import annotations

import json
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS scans (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 url TEXT NOT NULL,
 prediction TEXT NOT NULL,
 confidence REAL NOT NULL,
 risk_score INTEGER NOT NULL,
 risk_level TEXT NOT NULL,
 issues TEXT NOT NULL,
 features TEXT NOT NULL,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""


def get_connection(path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def init_db(path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with get_connection(path) as connection:
        connection.execute(SCHEMA)


def create_scan(path: str | Path, data: dict[str, object]) -> int:
    with get_connection(path) as connection:
        cursor = connection.execute(
            "INSERT INTO scans (url, prediction, confidence, risk_score, risk_level, issues, features) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (data["url"], data["prediction"], data["confidence"], data["risk_score"], data["risk_level"], json.dumps(data["issues"]), json.dumps(data["features"])),
        )
        return int(cursor.lastrowid)


def get_scan(path: str | Path, scan_id: int) -> sqlite3.Row | None:
    with get_connection(path) as connection:
        return connection.execute("SELECT * FROM scans WHERE id = ?", (scan_id,)).fetchone()


def list_scans(path: str | Path, search: str = "") -> list[sqlite3.Row]:
    with get_connection(path) as connection:
        if search:
            return connection.execute("SELECT * FROM scans WHERE url LIKE ? ORDER BY id DESC", (f"%{search}%",)).fetchall()
        return connection.execute("SELECT * FROM scans ORDER BY id DESC").fetchall()


def dashboard_stats(path: str) -> dict[str, object]:
    with get_connection(path) as connection:
        rows = connection.execute("SELECT prediction, risk_level, date(created_at) AS day, COUNT(*) AS count FROM scans GROUP BY prediction, risk_level, day ORDER BY day").fetchall()
        total = connection.execute("SELECT COUNT(*) FROM scans").fetchone()[0]
        phishing = connection.execute("SELECT COUNT(*) FROM scans WHERE prediction = 'Phishing'").fetchone()[0]
        levels = {level: connection.execute("SELECT COUNT(*) FROM scans WHERE risk_level = ?", (level,)).fetchone()[0] for level in ("Critical", "High", "Medium", "Low")}
        activity: dict[str, int] = {}
        for row in rows:
            activity[row["day"]] = activity.get(row["day"], 0) + row["count"]
        return {"total": total, "phishing": phishing, "legitimate": total - phishing, "levels": levels, "activity": activity}
