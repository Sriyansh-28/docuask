"""SQLite persistence for interaction telemetry (Session 4).

Every ``/ask`` logs a row here with its measured latency; ``/feedback`` updates
that row's thumbs rating; ``/stats`` aggregates the table for the dashboard.

Uses the stdlib ``sqlite3`` with a single shared connection guarded by a lock —
FastAPI runs sync endpoints in a threadpool, so ``check_same_thread=False`` plus
the lock keeps concurrent writes safe. The DB path comes from ``DOCUASK_DB``
(default ``docuask.db``); tests point it at ``:memory:``.
"""

from __future__ import annotations

import os
import sqlite3
import statistics
import threading
import uuid
from datetime import datetime, timezone

_DEFAULT_PATH = os.getenv("DOCUASK_DB", "docuask.db")
_lock = threading.Lock()
_conn: sqlite3.Connection | None = None

_SCHEMA = """
CREATE TABLE IF NOT EXISTS interactions (
    id          TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    question    TEXT NOT NULL,
    answer      TEXT NOT NULL,
    latency_ms  INTEGER NOT NULL,
    feedback    TEXT,               -- NULL | 'up' | 'down'
    created_at  TEXT NOT NULL       -- ISO-8601 UTC
);
"""


def _connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    conn.commit()
    return conn


def get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = _connect(_DEFAULT_PATH)
    return _conn


def configure(path: str) -> sqlite3.Connection:
    """(Re)point the store at ``path``. Used by tests to isolate each case."""
    global _conn
    with _lock:
        if _conn is not None:
            _conn.close()
        _conn = _connect(path)
    return _conn


def log_interaction(document_id: str, question: str, answer: str, latency_ms: int) -> str:
    """Persist one Q&A turn and return its generated interaction id."""
    interaction_id = uuid.uuid4().hex[:12]
    created_at = datetime.now(timezone.utc).isoformat()
    with _lock:
        conn = get_conn()
        conn.execute(
            "INSERT INTO interactions "
            "(id, document_id, question, answer, latency_ms, feedback, created_at) "
            "VALUES (?, ?, ?, ?, ?, NULL, ?)",
            (interaction_id, document_id, question, answer, latency_ms, created_at),
        )
        conn.commit()
    return interaction_id


def set_feedback(interaction_id: str, feedback: str) -> bool:
    """Set the thumbs rating for a row. Returns False if the id is unknown."""
    with _lock:
        conn = get_conn()
        cur = conn.execute(
            "UPDATE interactions SET feedback = ? WHERE id = ?",
            (feedback, interaction_id),
        )
        conn.commit()
        return cur.rowcount > 0


def get_stats() -> dict[str, object]:
    """Aggregate metrics for the dashboard."""
    with _lock:
        conn = get_conn()
        total = conn.execute("SELECT COUNT(*) AS c FROM interactions").fetchone()["c"]
        latencies = [
            row["latency_ms"]
            for row in conn.execute("SELECT latency_ms FROM interactions").fetchall()
        ]
        up = conn.execute(
            "SELECT COUNT(*) AS c FROM interactions WHERE feedback = 'up'"
        ).fetchone()["c"]
        down = conn.execute(
            "SELECT COUNT(*) AS c FROM interactions WHERE feedback = 'down'"
        ).fetchone()["c"]
        by_day = conn.execute(
            "SELECT substr(created_at, 1, 10) AS day, COUNT(*) AS c "
            "FROM interactions GROUP BY day ORDER BY day"
        ).fetchall()

    rated = up + down
    return {
        "total_questions": total,
        "median_latency_ms": round(statistics.median(latencies)) if latencies else None,
        "thumbs_up_rate": (up / rated) if rated else None,
        "thumbs_up": up,
        "thumbs_down": down,
        "questions_over_time": [{"date": r["day"], "count": r["c"]} for r in by_day],
    }
