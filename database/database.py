from __future__ import annotations

import json
import sqlite3
from pathlib import Path


def _connect(path: str) -> sqlite3.Connection:
    """Open a connection with WAL mode and row_factory set."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # better read/write concurrency
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(path: str) -> None:
    """Create the scans table if it does not exist."""
    with _connect(path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scans (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                url         TEXT    NOT NULL,
                prediction  TEXT    NOT NULL,
                confidence  REAL    NOT NULL,
                risk_score  INTEGER NOT NULL,
                risk_level  TEXT    NOT NULL,
                issues      TEXT    NOT NULL DEFAULT '[]',
                features    TEXT    NOT NULL DEFAULT '{}',
                created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            )
        """)


def create_scan(path: str, data: dict) -> int:
    """Insert a scan record and return its new auto-incremented id."""
    with _connect(path) as conn:
        cursor = conn.execute(
            """INSERT INTO scans
               (url, prediction, confidence, risk_score, risk_level, issues, features)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                data["url"],
                data["prediction"],
                float(data["confidence"]),
                int(data["risk_score"]),
                data["risk_level"],
                json.dumps(data["issues"]),
                json.dumps(data["features"]),
            ),
        )
        return cursor.lastrowid


def get_scan(path: str, scan_id: int) -> sqlite3.Row | None:
    """Return one scan row by id, or None if not found."""
    with _connect(path) as conn:
        return conn.execute(
            "SELECT * FROM scans WHERE id = ?", (scan_id,)
        ).fetchone()


def list_scans(path: str, search: str = "") -> list[sqlite3.Row]:
    """Return all scans newest-first, optionally filtered by URL substring.

    The LIKE pattern is passed as a parameter — never interpolated into the
    query string — so this is safe from SQL injection.
    """
    with _connect(path) as conn:
        if search:
            return conn.execute(
                "SELECT * FROM scans WHERE url LIKE ? ORDER BY id DESC",
                (f"%{search}%",),
            ).fetchall()
        return conn.execute(
            "SELECT * FROM scans ORDER BY id DESC"
        ).fetchall()


def dashboard_stats(path: str) -> dict:
    """Return aggregated counts needed by the dashboard template."""
    with _connect(path) as conn:
        total = conn.execute("SELECT COUNT(*) FROM scans").fetchone()[0]

        by_prediction = {
            row["prediction"]: row["cnt"]
            for row in conn.execute(
                "SELECT prediction, COUNT(*) AS cnt FROM scans GROUP BY prediction"
            ).fetchall()
        }

        by_risk = {
            row["risk_level"]: row["cnt"]
            for row in conn.execute(
                "SELECT risk_level, COUNT(*) AS cnt FROM scans GROUP BY risk_level"
            ).fetchall()
        }

        recent = conn.execute(
            "SELECT * FROM scans ORDER BY id DESC LIMIT 5"
        ).fetchall()

    return {
        "total": total,
        "by_prediction": by_prediction,
        "by_risk": by_risk,
        "recent": recent,
    }