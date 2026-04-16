"""Conversation memory query for zellij-talk."""

import json
from pathlib import Path
from typing import Any

from paths import get_all_jsonl_path, get_session_jsonl_path


def _read_log_file(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def query_memory(
    *,
    session: str | None = None,
    pane: str | None = None,
    agent: str | None = None,
    last: int = 20,
) -> list[dict[str, Any]]:
    """Query conversation memory with optional filters."""
    if session:
        path = get_session_jsonl_path(session)
    else:
        path = get_all_jsonl_path()

    records = _read_log_file(path)

    # Apply filters
    filtered = []
    for rec in records:
        # session filter
        if session:
            sessions = set()
            if rec["from"].get("session"):
                sessions.add(rec["from"]["session"])
            for t in rec["to"].get("targets", []):
                if t.get("session"):
                    sessions.add(t["session"])
            if session not in sessions:
                continue

        # pane filter
        if pane:
            panes = set()
            if rec["from"].get("pane"):
                panes.add(rec["from"]["pane"])
            for t in rec["to"].get("targets", []):
                if t.get("pane"):
                    panes.add(t["pane"])
            if pane not in panes:
                continue

        # agent filter
        if agent:
            agents = set()
            agents.add(rec["from"]["name"])
            for t in rec["to"].get("targets", []):
                agents.add(t.get("name", ""))
            if agent not in agents:
                continue

        filtered.append(rec)

    # Return last N (most recent)
    return filtered[-last:]


def format_text(records: list[dict[str, Any]]) -> str:
    if not records:
        return "（没有找到对话记录）"
    lines = []
    for rec in records:
        ts = rec["timestamp"]
        from_name = rec["from"]["name"]
        from_session = rec["from"].get("session") or "-"
        from_pane = rec["from"].get("pane") or "-"

        to_type = rec["to"]["type"]
        if to_type == "broadcast":
            to_display = f"📢 Broadcast ({', '.join(t['name'] for t in rec['to']['targets'])})"
        elif to_type == "multicast":
            to_display = f"📡 Multicast ({', '.join(t['name'] for t in rec['to']['targets'])})"
        else:
            t = rec["to"]["targets"][0]
            to_session = t.get("session") or "-"
            to_pane = t.get("pane") or "-"
            to_display = f"{t['name']} (session: {to_session} / pane {to_pane})"

        lines.append(f"## {ts}")
        lines.append("")
        lines.append(f"From: {from_name} (session: {from_session} / pane {from_pane})")
        lines.append(f"To:   {to_display}")
        lines.append("")
        if rec.get("file"):
            lines.append(f"[File: {rec['file']}]")
        lines.append(rec["content"])
        lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines).rstrip()
