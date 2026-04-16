"""Pipeline execution for zellij-talk."""

from pathlib import Path
from typing import Any

import yaml


def load_pipeline(path: str) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Pipeline 文件不存在: {path}")
    with open(p, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict) or "steps" not in data:
        raise ValueError("Pipeline YAML 必须包含 'steps' 列表")
    return data


def resolve_agent_ref(ref: str, registry: dict[str, Any]) -> str | None:
    """Resolve an agent reference.
    - If ref starts with '{cap:' resolve by capability.
    - Otherwise treat as exact agent name.
    """
    ref = ref.strip()
    if ref.startswith("{cap:") and ref.endswith("}"):
        cap = ref[5:-1].strip()
        for name, meta in registry.items():
            caps = meta.get("capabilities", [])
            if isinstance(caps, str):
                caps = [c.strip() for c in caps.split(",")]
            if cap in caps:
                return name
        return None
    return ref if ref in registry else None
