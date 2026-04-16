#!/bin/bash
# Agent 健康检查
# 用法: health.sh [agent_name]
# 无参数时检查所有已注册 Agent

set -euo pipefail

AGENTS_DIR="${AGENTS_DIR:-$HOME/.agents/skills/zellij-talk}"
REGISTRY="$AGENTS_DIR/registry.json"
TARGET_AGENT="${1:-}"

if [[ ! -f "$REGISTRY" ]]; then
  echo "（注册表不存在）"
  exit 0
fi

printf "%-24s %-20s %-8s %-6s %s\n" "Agent" "Session" "Pane" "状态" "备注"
echo "────────────────────────────────────────────────────────────────────────────"

check_agent() {
  local NAME="$1"
  local PANE="$2"
  local SESSION="$3"

  local STDOUT_FILE=$(mktemp)
  local STDERR_FILE=$(mktemp)

  zellij --session "$SESSION" action dump-screen --pane-id "$PANE" --full \
    >"$STDOUT_FILE" 2>"$STDERR_FILE" || true

  if grep -qE "Session .* not found" "$STDERR_FILE" 2>/dev/null; then
    printf "%-24s %-20s %-8s %-6s %s\n" "$NAME" "$SESSION" "$PANE" "🔴" "session 不存在"
    rm -f "$STDOUT_FILE" "$STDERR_FILE"
    return
  fi

  if [[ ! -s "$STDOUT_FILE" ]]; then
    printf "%-24s %-20s %-8s %-6s %s\n" "$NAME" "$SESSION" "$PANE" "🟠" "pane 不存在或已关闭"
    rm -f "$STDOUT_FILE" "$STDERR_FILE"
    return
  fi

  printf "%-24s %-20s %-8s %-6s %s\n" "$NAME" "$SESSION" "$PANE" "🟢" "在线"
  rm -f "$STDOUT_FILE" "$STDERR_FILE"
}

if [[ -n "$TARGET_AGENT" ]]; then
  META=$(jq -e --arg n "$TARGET_AGENT" '.[$n]' "$REGISTRY" 2>/dev/null) || {
    echo "❌ [$TARGET_AGENT] 未注册"
    exit 1
  }
  PANE=$(echo "$META" | jq -r '.pane_id')
  SESSION=$(echo "$META" | jq -r '.session')
  check_agent "$TARGET_AGENT" "$PANE" "$SESSION"
else
  while IFS=$'\t' read -r NAME PANE SESSION; do
    check_agent "$NAME" "$PANE" "$SESSION"
  done < <(jq -r 'to_entries[] | [.key, .value.pane_id, .value.session] | @tsv' "$REGISTRY")
fi
