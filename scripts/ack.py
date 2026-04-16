"""Lightweight ACK/DONE/REPLY protocol for zellij-talk."""

import uuid


def generate_msg_id() -> str:
    return uuid.uuid4().hex[:8]


def inject_msg_id(content: str, msg_id: str) -> str:
    return (
        f"{content}\n\n"
        f"<!-- MSG_ID:{msg_id} -->\n"
        f"<!-- 处理前请直接运行：echo '{{\"type\":\"ACK\",\"msg_id\":\"{msg_id}\"}}' >> ~/.config/zellij/talk/replies.jsonl -->\n"
        f"<!-- 若任务完成，可将 type 替换为 DONE；若要回复内容，可替换为 REPLY 并追加 payload 字段 -->"
    )
