#!/bin/bash
# 阻塞等待某个 Agent 输出中出现指定关键词
# 用法: wait.sh <agent_name> <关键词> [超时秒数，默认 60]

set -uo pipefail

AGENTS_DIR="${AGENTS_DIR:-$HOME/.agents/skills/zellij-talk}"
SCRIPTS="$AGENTS_DIR/scripts"

AGENT_NAME="${1:-}"
KEYWORD="${2:-}"
TIMEOUT="${3:-60}"
INTERVAL=2
LINES=100

if [[ -z "$AGENT_NAME" || -z "$KEYWORD" ]]; then
  echo "❌ 用法: wait.sh <agent_name> <关键词> [超时秒数]"
  exit 1
fi

echo "⏳ 等待 [$AGENT_NAME] 输出中出现关键词: '$KEYWORD' (超时 ${TIMEOUT}s)"

ELAPSED=0
while [[ $ELAPSED -lt $TIMEOUT ]]; do
  OUTPUT=$("$SCRIPTS/from.sh" "$AGENT_NAME" "$LINES" 2>/dev/null) || true

  if echo "$OUTPUT" | grep -q "$KEYWORD"; then
    echo "🎯 检测到关键词: $KEYWORD"
    echo "$OUTPUT" | grep "$KEYWORD"
    exit 0
  fi

  sleep "$INTERVAL"
  ELAPSED=$((ELAPSED + INTERVAL))
done

echo "⏰ 超时 (${TIMEOUT}s)，未检测到关键词: $KEYWORD"
exit 1
