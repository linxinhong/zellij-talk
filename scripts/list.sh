#!/bin/bash
# 列出所有已注册 Agent
# 用法: list.sh [--json]

set -euo pipefail

AGENTS_DIR="${AGENTS_DIR:-$HOME/.agents/skills/zellij-talk}"
REGISTRY="$AGENTS_DIR/registry.json"

if [[ ! -f "$REGISTRY" ]]; then
  echo "（注册表为空）"
  exit 0
fi

if [[ "${1:-}" == "--json" ]]; then
  jq . "$REGISTRY"
else
  echo "已注册的 Agent："
  echo "────────────────────────────────────────────────"
  jq -r 'to_entries[] | "\(.key)\n  pane_id  : \(.value.pane_id)\n  session  : \(.value.session)\n  注册时间 : \(.value.registered)\n"' "$REGISTRY"
fi
