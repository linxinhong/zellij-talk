"""Conversation memory query for zellij-talk."""

import json
import re
from pathlib import Path
from typing import Any

from paths import get_all_log_path, get_session_log_path


_TIMESTAMP_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)
_FROM_RE = re.compile(r"\*\*From:\*\*\s+(.+)$", re.MULTILINE)
_TO_RE = re.compile(r"\*\*To:\*\*\s+(.+)$", re.MULTILINE)
_CONTENT_RE = re.compile(r"```text\n(.*?)\n```", re.DOTALL)
_FILE_RE = re.compile(r"\*\[File:\s+([^\]]+)\]\*")


def _extract_name_session_pane(text: str) -> dict[str, Any]:
    """Parse a From/To line like:
    `kimi_coder_Finn` (session: rectangular-viola / pane 1)
    or `外部终端` / `未识别`
    """
    text = text.strip()
    # Match backtick-quoted name
    name_match = re.search(r"`([^`]+)`", text)
    name = name_match.group(1) if name_match else text

    session_match = re.search(r"session:\s+([^\s/]+)", text)
    pane_match = re.search(r"pane\s+(\d+)", text)

    return {
        "name": name,
        "session": session_match.group(1) if session_match else None,
        "pane": pane_match.group(1) if pane_match else None,
    }


def _parse_to(target_text: str) -> dict[str, Any]:
    target_text = target_text.strip()
    if target_text.startswith("📢 Broadcast ("):
        inner = target_text[len("📢 Broadcast ("):-1]
        targets = [t.strip() for t in inner.split(",") if t.strip()]
        return {"type": "broadcast", "targets": [{"name": t} for t in targets]}
    if target_text.startswith("📡 Multicast ("):
        inner = target_text[len("📡 Multicast ("):-1]
        targets = [t.strip() for t in inner.split(",") if t.strip()]
        return {"type": "multicast", "targets": [{"name": t} for t in targets]}

    # Direct target, may contain session/pane info
    target = _extract_name_session_pane(target_text)
    return {"type": "direct", "targets": [target]}


def _parse_block(block: str) -> dict[str, Any] | None:
    block = block.strip()
    if not block:
        return None

    ts_match = _TIMESTAMP_RE.search(block)
    from_match = _FROM_RE.search(block)
    to_match = _TO_RE.search(block)
    content_match = _CONTENT_RE.search(block)

    if not ts_match or not from_match or not to_match:
        return None

    timestamp = ts_match.group(1).strip()
    from_info = _extract_name_session_pane(from_match.group(1))
    to_info = _parse_to(to_match.group(1))

    raw_content = content_match.group(1) if content_match else ""
    file_name = None

    # Check if first line is *[File: ...]*
    lines = raw_content.splitlines()
    if lines:
        file_m = _FILE_RE.match(lines[0])
        if file_m:
            file_name = file_m.group(1)
            raw_content = "\n".join(lines[1:]).strip()

    return {
        "timestamp": timestamp,
        "from": from_info,
        "to": to_info,
        "content": raw_content,
        "file": file_name,
    }


def _read_log_file(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    # Skip the header line
    lines = text.splitlines()
    if lines and lines[0].startswith("#"):
        text = "\n".join(lines[1:])
    blocks = re.split(r"^---\s*$", text, flags=re.MULTILINE)
    records = []
    for block in blocks:
        rec = _parse_block(block)
        if rec:
            records.append(rec)
    return records


def query_memory(
    *,
    session: str | None = None,
    pane: str | None = None,
    agent: str | None = None,
    last: int = 20,
) -> list[dict[str, Any]]:
    """Query conversation memory with optional filters."""
    # Determine source file
    if session:
        path = get_session_log_path(session)
    else:
        path = get_all_log_path()

    records = _read_log_file(path)

    # Apply filters
    filtered = []
    for rec in records:
        # session filter
        if session:
            sessions = set()
            if rec["from"]["session"]:
                sessions.add(rec["from"]["session"])
            for t in rec["to"]["targets"]:
                if t.get("session"):
                    sessions.add(t["session"])
            if session not in sessions:
                continue

        # pane filter
        if pane:
            panes = set()
            if rec["from"]["pane"]:
                panes.add(rec["from"]["pane"])
            for t in rec["to"]["targets"]:
                if t.get("pane"):
                    panes.add(t["pane"])
            if pane not in panes:
                continue

        # agent filter
        if agent:
            agents = set()
            agents.add(rec["from"]["name"])
            for t in rec["to"]["targets"]:
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
        from_session = rec["from"]["session"] or "-"
        from_pane = rec["from"]["pane"] or "-"

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
