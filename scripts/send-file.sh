#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENTS_DIR="${AGENTS_DIR:-$SCRIPT_DIR/..}"
PYTHONPATH="$AGENTS_DIR/src:${PYTHONPATH:-}" python3 -m zellij_talk.cli send-file "$@"
