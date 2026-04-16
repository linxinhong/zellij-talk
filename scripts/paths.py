"""Cross-platform path resolution for zellij-talk."""

import os
import sys
from pathlib import Path


def get_talk_dir() -> Path:
    """Return the talk directory under Zellij config path."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / "zellij" / "talk"
    else:
        # macOS / Linux / Unix
        xdg = os.environ.get("XDG_CONFIG_HOME")
        if xdg:
            base = Path(xdg)
        else:
            base = Path.home() / ".config"
        return base / "zellij" / "talk"


def get_registry_path() -> Path:
    env = os.environ.get("AGENTS_REGISTRY")
    if env:
        return Path(env)
    return get_talk_dir() / "registry.json"


def get_sessions_dir() -> Path:
    return get_talk_dir() / "sessions"


def get_session_log_path(session_name: str) -> Path:
    return get_sessions_dir() / f"{session_name}.md"


def get_all_log_path() -> Path:
    return get_sessions_dir() / "all.md"
