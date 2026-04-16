"""Session conversation logger for zellij-talk."""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from paths import get_all_log_path, get_sessions_dir, get_session_log_path
from registry import find_agent_by_pane, load_registry


def _now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _ensure_log_file(path: Path, session_name: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# Zellij Talk Session: {session_name}\n\n")


def _get_sender_info() -> dict[str, Any]:
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


def _format_from(sender: dict[str, Any]) -> str:
    name = sender["name"]
    session = sender.get("session")
    pane_id = sender.get("pane_id")
    if sender["source"] == "external":
        return f"`外部终端` / `{name}`"
    if session and pane_id:
        return f"`{name}` (session: {session} / pane {pane_id})"
    return f"`{name}`"


def _format_to(agent_name: str, meta: dict[str, Any] | None) -> str:
    if meta is None:
        return f"`{agent_name}`"
    session = meta.get("session", "unknown")
    pane_id = meta.get("pane_id", "unknown")
    return f"`{agent_name}` (session: {session} / pane {pane_id})"


def _append_to_file(path: Path, content: str, session_name: str) -> None:
    _ensure_log_file(path, session_name)
    with open(path, "a", encoding="utf-8") as f:
        f.write(content)


def log_message(
    target_agents: list[tuple[str, dict[str, Any] | None]],
    message_body: str,
    *,
    message_type: str = "direct",
    file_name: str | None = None,
) -> None:
    """Log a message to relevant session logs and the global all.md."""
    sender = _get_sender_info()
    timestamp = _now_str()

    # Determine To line
    if message_type == "broadcast":
        agent_list = ", ".join(a[0] for a in target_agents)
        to_line = f"📢 Broadcast ({agent_list})"
    elif message_type == "multicast":
        agent_list = ", ".join(a[0] for a in target_agents)
        to_line = f"📡 Multicast ({agent_list})"
    else:
        # direct or send-file: first target
        to_line = _format_to(target_agents[0][0], target_agents[0][1]) if target_agents else "`未知`"

    from_line = _format_from(sender)

    # Build body
    body_lines = []
    if file_name:
        body_lines.append(f"*[File: {file_name}]*")
    body_lines.append("```text")
    body_lines.append(message_body)
    body_lines.append("```")
    body = "\n".join(body_lines)

    entry = f"---\n\n## {timestamp}\n\n**From:** {from_line}  \n**To:** {to_line}\n\n{body}\n\n"

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
        path = get_session_log_path(session_name)
        _append_to_file(path, entry, session_name)

    # Always write to all.md
    all_path = get_all_log_path()
    _append_to_file(all_path, entry, "all")
