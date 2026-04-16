# Changelog

All notable changes to this project will be documented in this file.

## [1.2.0] - 2026-04-17

### Added

- **ACK/DONE/REPLY Protocol**: Lightweight message-level completion tracking.
  - `zt to <agent> --wait-ack --ack-timeout 60`
  - `zt to <agent> --wait-done --done-timeout 60`
  - `zt to <agent> --wait-reply --reply-timeout 60`
- **Offline Message Queue**: SQLite-based queue (`~/.config/zellij/talk/queue.db`) with automatic dequeue on agent registration.
  - `zt inbox [agent] [--clear]`
- **Structured JSON Messaging**: Send typed envelopes between agents.
  - `zt send-json <agent> --payload '{...}' --type <type>`
  - `zt envelope <agent> --payload "..." --type <type>`
- **Pipeline Orchestration**: YAML-defined multi-agent workflows.
  - `zt pipeline <file.yaml> --task "..."`
  - Supports content-driven (`<talk>完成</talk>`) and message-driven (`[DONE]`, `[REPLY]`) wait modes.
- **Agent Roles & Capabilities**: Register agents with metadata.
  - `zt register <name> --role coder --capabilities "code,test" --prompt "..."`
  - `zt list --capabilities`
  - `zt find <cap>` for capability-based discovery.
- **Dashboard**: Real-time message flow visualization over JSONL logs.
  - `zt dashboard [--session] [--follow]`
- **Stats**: Message statistics including response time analysis.
  - `zt stats [--session] [--today] [--json]`
- **Global CLI Entrypoint**: `pyproject.toml` with `zt` console script.
  - Install via `pip install -e .` and use `zt` globally.
- **`--file` Support**: Send complex multi-line messages from file without shell escaping issues.
  - `zt to <agent> --file /tmp/msg.txt`
  - `zt reply <session:pane> --file /tmp/msg.txt`

### Changed

- **Conversation logs migrated from Markdown to JSON Lines** (`.jsonl`), replacing fragile regex parsing with robust line-by-line JSON reads.
- **`is_pane_alive`** no longer dumps full scrollback, improving `prune` and `health` performance.
- **`dump_screen`** now supports `full=False` for lightweight viewport-only reads.

### Fixed

- **Registry concurrency**: Added `filelock` to protect read-modify-write operations across multiple agents.
- **`cmd_health`** now returns correct exit codes (`1` for unregistered target, `2` if dead agents found, `0` otherwise).
- **`cmd_init`** example path resolution simplified and made robust.
- **`cmd_review`** no longer uses hardcoded example agent names; requires explicit `source` and `target`.
- **`cmd_register`** nested RMW reduced via atomic `replace_agent`.

### Renamed

- `scripts/queue.py` → `scripts/msg_queue.py` to avoid conflict with the Python standard library `queue` module.
