"""Registry management for zellij-talk agents."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _get_registry_path() -> Path:
    env = os.environ.get("AGENTS_REGISTRY")
    if env:
        return Path(env)
    # Infer project root from the location of this script (scripts/registry.py)
    default = Path(__file__).resolve().parent.parent / "registry.json"
    return default


def load_registry() -> dict[str, Any]:
    path = _get_registry_path()
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_registry(data: dict[str, Any]) -> None:
    path = _get_registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def register_agent(name: str, session: str, pane_id: str) -> None:
    data = load_registry()
    # Remove any other agent using the same pane in the same session
    to_remove = [
        k
        for k, v in data.items()
        if k != name and v.get("session") == session and v.get("pane_id") == pane_id
    ]
    for k in to_remove:
        del data[k]
    data[name] = {
        "pane_id": pane_id,
        "session": session,
        "registered": datetime.now(timezone.utc).isoformat(),
    }
    save_registry(data)


def unregister_agent(name: str) -> bool:
    data = load_registry()
    if name not in data:
        return False
    del data[name]
    save_registry(data)
    return True


def get_agent(name: str) -> dict[str, Any] | None:
    return load_registry().get(name)


def list_agents() -> dict[str, Any]:
    return load_registry()
