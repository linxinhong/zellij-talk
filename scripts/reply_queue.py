"""Reply queue using JSON Lines for ACK/DONE/REPLY messages."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from paths import get_replies_jsonl_path


def _ensure_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.touch()


def append_reply(
    reply_type: str,
    msg_id: str,
    from_agent: str,
    payload: str | None = None,
) -> None:
    path = get_replies_jsonl_path()
    _ensure_file(path)
    record = {
        "type": reply_type,
        "msg_id": msg_id,
        "from": from_agent,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    if payload is not None:
        record["payload"] = payload
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def find_reply(msg_id: str) -> dict[str, Any] | None:
    path = get_replies_jsonl_path()
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                if rec.get("msg_id") == msg_id:
                    return rec
            except json.JSONDecodeError:
                continue
    return None


def wait_for_reply(msg_id: str, timeout: int, interval: float = 0.5) -> dict[str, Any] | None:
    import time
    elapsed = 0.0
    while elapsed < timeout:
        rec = find_reply(msg_id)
        if rec is not None:
            return rec
        time.sleep(interval)
        elapsed += interval
    return None
