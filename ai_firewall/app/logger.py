"""
logger.py — Audit logger for the AI Firewall.

Every prompt that passes through the firewall is logged —
both allowed and blocked requests.

Why log everything?
  - Blocked requests: evidence of attack attempts
  - Allowed requests: baseline for normal traffic
  - Both together: detect slow-moving probing attacks
    where each individual prompt looks safe but the
    pattern across many requests reveals malicious intent
"""

import sqlite3
from datetime import datetime, timezone
import os

# Build path relative to this file's location
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.getenv("FIREWALL_DB", os.path.join(BASE_DIR, "firewall_audit.db"))


def init_db() -> None:
    """
    Creates the audit log table if it doesn't exist.
    Called once at server startup.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prompt_audit (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp         TEXT NOT NULL,
            prompt            TEXT NOT NULL,
            score             REAL NOT NULL,
            semantic_score    REAL NOT NULL,
            rule_match        INTEGER NOT NULL,
            decision          TEXT NOT NULL,
            detection_method  TEXT NOT NULL,
            blocked           INTEGER NOT NULL
        )
    """)
    conn.commit()
    conn.close()
    print(f"Audit database ready at {DB_PATH}")


def log_request(analysis: dict) -> None:
    """
    Logs a scored prompt to the audit database.

    Args:
        analysis: the full result dict from PromptScorer.score()
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO prompt_audit
            (timestamp, prompt, score, semantic_score,
             rule_match, decision, detection_method, blocked)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now(timezone.utc).isoformat(),
        analysis["prompt"],
        analysis["score"],
        analysis["semantic_score"],
        int(analysis["rule_match"]),
        analysis["decision"],
        analysis["detection_method"],
        int(analysis["is_malicious"]),
    ))
    conn.commit()
    conn.close()


def get_recent_logs(limit: int = 50) -> list[dict]:
    """
    Retrieves the most recent audit log entries.
    Used by the /audit endpoint to inspect firewall activity.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, timestamp, prompt, score, decision, blocked
        FROM prompt_audit
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "id": row[0],
            "timestamp": row[1],
            "prompt": row[2][:100] + "..." if len(row[2]) > 100 else row[2],
            "score": row[3],
            "decision": row[4],
            "blocked": bool(row[5]),
        }
        for row in rows
    ]


def get_stats() -> dict:
    """
    Returns summary statistics about firewall activity.
    Useful for monitoring dashboards.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM prompt_audit")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM prompt_audit WHERE blocked = 1")
    blocked = cursor.fetchone()[0]

    cursor.execute("SELECT AVG(score) FROM prompt_audit")
    avg_score = cursor.fetchone()[0] or 0.0

    cursor.execute("""
        SELECT COUNT(*) FROM prompt_audit
        WHERE blocked = 1
        AND timestamp > datetime('now', '-1 hour')
    """)
    blocked_last_hour = cursor.fetchone()[0]

    conn.close()

    return {
        "total_requests": total,
        "total_blocked": blocked,
        "block_rate": round(blocked / total, 4) if total > 0 else 0.0,
        "average_score": round(avg_score, 4),
        "blocked_last_hour": blocked_last_hour,
    }