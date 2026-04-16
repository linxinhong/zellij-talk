"""Message statistics for zellij-talk."""

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from memory import read_log_file
from paths import get_all_jsonl_path


def compute_stats(session: str | None = None, today: bool = False) -> dict[str, Any]:
    path = get_all_jsonl_path() if not session else Path(str(get_all_jsonl_path()).replace("all.jsonl", f"{session}.jsonl"))
    records = read_log_file(path)

    if today:
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        records = [r for r in records if r.get("timestamp", "").startswith(today_str)]

    total = len(records)
    agent_counts = Counter()
    response_times = []

    for rec in records:
        agent_counts[rec["from"]["name"]] += 1
        # crude response time: look for adjacent pair A->B then B->A
        # we'll do this in a second pass

    # Second pass for response times
    for i in range(len(records) - 1):
        a = records[i]
        b = records[i + 1]
        a_from = a["from"]["name"]
        a_to = [t["name"] for t in a["to"].get("targets", [])]
        b_from = b["from"]["name"]
        b_to = [t["name"] for t in b["to"].get("targets", [])]
        if a_from in b_to and b_from in a_to:
            try:
                ta = datetime.fromisoformat(a["timestamp"])
                tb = datetime.fromisoformat(b["timestamp"])
                delta = (tb - ta).total_seconds()
                if 0 < delta < 3600:
                    response_times.append(delta)
            except Exception:
                continue

    avg_response = sum(response_times) / len(response_times) if response_times else 0
    most_active = agent_counts.most_common(1)[0] if agent_counts else (None, 0)

    return {
        "total_messages": total,
        "most_active_agent": most_active[0],
        "most_active_count": most_active[1],
        "avg_response_time_sec": round(avg_response, 1),
        "response_samples": len(response_times),
        "agent_counts": dict(agent_counts),
    }


def format_stats(data: dict[str, Any]) -> str:
    lines = [
        f"总消息数: {data['total_messages']}",
        f"最活跃 Agent: {data['most_active_agent'] or '-'} ({data['most_active_count']} 条)",
        f"平均响应时间: {data['avg_response_time_sec']}s (样本 {data['response_samples']})",
    ]
    if data["agent_counts"]:
        lines.append("")
        lines.append("各 Agent 消息数:")
        for name, count in sorted(data["agent_counts"].items(), key=lambda x: -x[1]):
            lines.append(f"  {name}: {count}")
    return "\n".join(lines)
