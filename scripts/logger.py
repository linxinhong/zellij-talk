"""Session conversation logger for zellij-talk."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from paths import get_all_jsonl_path, get_sessions_dir, get_session_jsonl_path
from registry import find_agent_by_pane


def now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def get_sender_info() -> dict[str, Any]:
    """Determine current sender based on environment."""
    session = os.environ.get("ZELLIJ_SESSION_NAME")
    pane_id = os.environ.get("ZELLIJ_PANE_ID")
    custom_from = os.environ.get("ZELLIJ_TALK_FROM")

    if custom_from:
        return {
            "name": custom_from,
            "session": session,
            "pane_id": pane_id,
            "source": "custom",
        }

    if session and pane_id:
        agent = find_agent_by_pane(session, pane_id)
        return {
            "name": agent or "未注册",
            "session": session,
            "pane_id": pane_id,
            "source": "zellij",
        }

    return {
        "name": "未识别",
        "session": None,
        "pane_id": None,
        "source": "external",
    }


def log_message(
    target_agents: list[tuple[str, dict[str, Any] | None]],
    message_body: str,
    *,
    message_type: str = "direct",
    file_name: str | None = None,
) -> None:
    """Log a message to relevant session jsonl and the global all.jsonl."""
    sender = get_sender_info()
    timestamp = now_str()

    # Determine To info
    if message_type == "broadcast":
        to_info = {"type": "broadcast", "targets": [{"name": a[0]} for a in target_agents]}
    elif message_type == "multicast":
        to_info = {"type": "multicast", "targets": [{"name": a[0]} for a in target_agents]}
    else:
        to_info = {
            "type": "direct",
            "targets": [
                {
                    "name": a[0],
                    "session": a[1].get("session") if a[1] else None,
                    "pane": a[1].get("pane_id") if a[1] else None,
                }
                for a in target_agents
            ],
        }

    from_info = {
        "name": sender["name"],
        "session": sender.get("session"),
        "pane": sender.get("pane_id"),
    }

    record = {
        "timestamp": timestamp,
        "from": from_info,
        "to": to_info,
        "content": message_body,
        "file": file_name,
    }

    # Collect sessions to write to
    sessions_to_write: set[str] = set()
    for _, meta in target_agents:
        if meta and meta.get("session"):
            sessions_to_write.add(meta["session"])

    # If sender is in Zellij, also write to sender's session
    if sender["source"] == "zellij" and sender.get("session"):
        sessions_to_write.add(sender["session"])

    # Write to each session log
    for session_name in sessions_to_write:
        path = get_session_jsonl_path(session_name)
        _ensure_dir(path)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # Always write to all.jsonl
    all_path = get_all_jsonl_path()
    _ensure_dir(all_path)
    with open(all_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
