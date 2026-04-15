#!/bin/bash
# 向指定 Agent 发送内容
# 用法: to.sh <agent_name> <内容> [--no-enter]
# 完全面板无关，通过注册表动态查找 session + pane_id

set -euo pipefail

AGENTS_DIR="${AGENTS_DIR:-$HOME/.agents/skills/zellij-talk}"
REGISTRY="$AGENTS_DIR/registry.json"

AGENT_NAME="${1:-}"
CONTENT="${2:-}"
NO_ENTER="${3:-}"

if [[ -z "$AGENT_NAME" ]]; then
  echo "❌ 用法: to.sh <agent_name> <内容> [--no-enter]"
  exit 1
fi

if [[ -z "$CONTENT" ]]; then
  echo "❌ 内容不能为空"
  exit 1
fi

# 从注册表读取（同时取 session 和 pane_id）
META=$(jq -e --arg n "$AGENT_NAME" '.[$n]' "$REGISTRY" 2>/dev/null) || {
  echo "❌ [$AGENT_NAME] 未注册，请先在对应面板执行 register.sh"
  exit 1
}

PANE_ID=$(echo "$META" | jq -r '.pane_id')
SESSION=$(echo "$META" | jq -r '.session')

# 注入内容（不切换焦点）
zellij -s "$SESSION" action paste --pane-id "$PANE_ID" "$CONTENT"

if [[ "$NO_ENTER" != "--no-enter" ]]; then
  zellij -s "$SESSION" action send-keys --pane-id "$PANE_ID" "Enter"
fi

echo "📨 [$AGENT_NAME @ $PANE_ID / $SESSION] ← 已发送"
