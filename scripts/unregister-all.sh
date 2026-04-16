#!/bin/bash
# 一键注销所有或当前 session 的 Agent
# 用法: unregister-all.sh [--current-session]

set -euo pipefail

AGENTS_DIR="${AGENTS_DIR:-$HOME/.agents/skills/zellij-talk}"
REGISTRY="$AGENTS_DIR/registry.json"
SCRIPTS="$AGENTS_DIR/scripts"

CURRENT_SESSION_ONLY=false
if [[ "${1:-}" == "--current-session" ]]; then
  CURRENT_SESSION_ONLY=true
fi

if [[ ! -f "$REGISTRY" ]]; then
  echo "（注册表为空）"
  exit 0
fi

AGENTS=$(jq -r 'keys[]' "$REGISTRY")
REMOVED=0

for AGENT in $AGENTS; do
  if [[ "$CURRENT_SESSION_ONLY" == true ]]; then
    SESSION=$(jq -r --arg n "$AGENT" '.[$n].session' "$REGISTRY")
    if [[ "$SESSION" != "${ZELLIJ_SESSION_NAME:-}" ]]; then
      continue
    fi
  fi

  "$SCRIPTS/unregister.sh" "$AGENT"
  REMOVED=$((REMOVED + 1))
done

if [[ $REMOVED -eq 0 ]]; then
  echo "（没有可注销的 Agent）"
else
  echo "✅ 共注销 $REMOVED 个 Agent"
fi
