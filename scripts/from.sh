#!/bin/bash
# 读取某个 Agent 的当前输出
# 用法: from.sh <agent_name> [行数] [--ansi]
# 例如: from.sh claude_reviewer_23A3 50
#       from.sh claude_reviewer_23A3 --ansi
#       from.sh claude_reviewer_23A3 50 --ansi

set -euo pipefail

AGENTS_DIR="${AGENTS_DIR:-$HOME/.agents/skills/zellij-talk}"
REGISTRY="$AGENTS_DIR/registry.json"

AGENT_NAME=""
LINES=100
ANSI=false

# 解析参数
while [[ $# -gt 0 ]]; do
  case "$1" in
    --ansi)
      ANSI=true
      shift
      ;;
    [0-9]*)
      LINES="$1"
      shift
      ;;
    *)
      if [[ -z "$AGENT_NAME" ]]; then
        AGENT_NAME="$1"
      else
        echo "❌ 未知参数: $1"
        exit 1
      fi
      shift
      ;;
  esac
done

if [[ -z "$AGENT_NAME" ]]; then
  echo "❌ 用法: from.sh <agent_name> [行数] [--ansi]"
  exit 1
fi

META=$(jq -e --arg n "$AGENT_NAME" '.[$n]' "$REGISTRY" 2>/dev/null) || {
  echo "❌ [$AGENT_NAME] 未注册"
  exit 1
}

PANE_ID=$(echo "$META" | jq -r '.pane_id')
SESSION=$(echo "$META" | jq -r '.session')

ANSI_FLAG=""
if [[ "$ANSI" == true ]]; then
  ANSI_FLAG="--ansi"
fi

zellij --session "$SESSION" action dump-screen \
  --pane-id "$PANE_ID" --full $ANSI_FLAG | tail -n "$LINES"
