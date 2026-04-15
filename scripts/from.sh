#!/bin/bash
# 读取某个 Agent 的当前输出
# 用法: from.sh <agent_name> [行数，默认 100]

set -euo pipefail

AGENTS_DIR="${AGENTS_DIR:-$HOME/.agents/skills/zellij-talk}"
REGISTRY="$AGENTS_DIR/registry.json"

AGENT_NAME="${1:-}"
LINES="${2:-100}"

if [[ -z "$AGENT_NAME" ]]; then
  echo "❌ 用法: from.sh <agent_name> [行数]"
  exit 1
fi

META=$(jq -e --arg n "$AGENT_NAME" '.[$n]' "$REGISTRY" 2>/dev/null) || {
  echo "❌ [$AGENT_NAME] 未注册"
  exit 1
}

PANE_ID=$(echo "$META" | jq -r '.pane_id')
SESSION=$(echo "$META" | jq -r '.session')

zellij -s "$SESSION" action dump-screen \
  --pane-id "$PANE_ID" --full | tail -n "$LINES"
