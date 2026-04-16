"""Zellij CLI wrapper and pane health checks."""

import shutil
import subprocess


def _run(
    *args: str,
    capture: bool = True,
    check: bool = False,
    input_data: str | None = None,
) -> subprocess.CompletedProcess:
    cmd = ["zellij", *args]
    result = subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        input=input_data,
        check=check,
    )
    return result


def is_pane_alive(session: str, pane_id: str) -> bool:
    """Check if a pane is still alive by dumping its screen."""
    result = _run(
        "--session", session,
        "action", "dump-screen",
        "--pane-id", pane_id,
        "--full",
    )
    if "Session" in result.stderr and "not found" in result.stderr:
        return False
    if not result.stdout:
        return False
    return True


def send_text(session: str, pane_id: str, text: str, *, no_enter: bool = False) -> None:
    _run(
        "--session", session,
        "action", "paste",
        "--pane-id", pane_id,
        text,
        check=True,
    )
    if not no_enter:
        _run(
            "--session", session,
            "action", "send-keys",
            "--pane-id", pane_id,
            "Enter",
            check=True,
        )


def dump_screen(session: str, pane_id: str, *, ansi: bool = False) -> str:
    args = [
        "--session", session,
        "action", "dump-screen",
        "--pane-id", pane_id,
        "--full",
    ]
    if ansi:
        args.append("--ansi")
    result = _run(*args, check=True)
    return result.stdout


def rename_pane(pane_id: str, name: str) -> None:
    _run(
        "action", "rename-pane",
        "--pane-id", pane_id,
        name,
        check=True,
    )


def has_zellij_env() -> bool:
    import os

    return bool(os.environ.get("ZELLIJ_PANE_ID") and os.environ.get("ZELLIJ_SESSION_NAME"))


def get_current_pane_id() -> str | None:
    import os

    return os.environ.get("ZELLIJ_PANE_ID")


def get_current_session() -> str | None:
    import os

    return os.environ.get("ZELLIJ_SESSION_NAME")
