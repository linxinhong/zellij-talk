"""Offline message queue using SQLite."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from paths import get_talk_dir


def _db_path() -> Path:
    return get_talk_dir() / "queue.db"


def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            msg_id TEXT UNIQUE,
            to_agent TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            delivered_at TEXT
        )
        """
    )
    conn.commit()


def enqueue(msg_id: str, to_agent: str, content: str) -> None:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(path)) as conn:
        _ensure_table(conn)
        conn.execute(
            "INSERT INTO queue (msg_id, to_agent, content, created_at) VALUES (?, ?, ?, ?)",
            (msg_id, to_agent, content, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()


def dequeue_for_agent(agent: str) -> list[dict[str, Any]]:
    path = _db_path()
    if not path.exists():
        return []
    with sqlite3.connect(str(path)) as conn:
        _ensure_table(conn)
        cur = conn.execute(
            "SELECT msg_id, to_agent, content, created_at FROM queue WHERE to_agent = ? AND delivered_at IS NULL ORDER BY id",
            (agent,),
        )
        rows = cur.fetchall()
        now = datetime.now(timezone.utc).isoformat()
        for row in rows:
            conn.execute(
                "UPDATE queue SET delivered_at = ? WHERE msg_id = ?",
                (now, row[0]),
            )
        conn.commit()
    return [
        {"msg_id": r[0], "to_agent": r[1], "content": r[2], "created_at": r[3]}
        for r in rows
    ]


def list_undelivered(agent: str | None = None) -> list[dict[str, Any]]:
    path = _db_path()
    if not path.exists():
        return []
    with sqlite3.connect(str(path)) as conn:
        _ensure_table(conn)
        if agent:
            cur = conn.execute(
                "SELECT msg_id, to_agent, content, created_at FROM queue WHERE to_agent = ? AND delivered_at IS NULL ORDER BY id",
                (agent,),
            )
        else:
            cur = conn.execute(
                "SELECT msg_id, to_agent, content, created_at FROM queue WHERE delivered_at IS NULL ORDER BY id"
            )
        rows = cur.fetchall()
    return [
        {"msg_id": r[0], "to_agent": r[1], "content": r[2], "created_at": r[3]}
        for r in rows
    ]


def clear_delivered() -> int:
    path = _db_path()
    if not path.exists():
        return 0
    with sqlite3.connect(str(path)) as conn:
        _ensure_table(conn)
        cur = conn.execute("DELETE FROM queue WHERE delivered_at IS NOT NULL")
        conn.commit()
        return cur.rowcount
