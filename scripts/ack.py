"""Lightweight ACK/DONE/REPLY protocol for zellij-talk."""

import re
import uuid


def generate_msg_id() -> str:
    return uuid.uuid4().hex[:8]


def inject_msg_id(content: str, msg_id: str) -> str:
    return f"[MSG_ID:{msg_id}]\n{content}"


def match_ack(text: str, msg_id: str) -> bool:
    return f"[ACK:{msg_id}]" in text


def match_done(text: str, msg_id: str) -> bool:
    return f"[DONE:{msg_id}]" in text


def match_reply(text: str, msg_id: str) -> str | None:
    pattern = re.compile(re.escape(f"[REPLY:{msg_id}]") + r"\s*(.*)", re.DOTALL)
    m = pattern.search(text)
    if m:
        return m.group(1).strip()
    return None
