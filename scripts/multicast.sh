#!/bin/bash
# 向指定多个 Agent 发送消息
# 用法: multicast.sh "agent1,agent2,agent3" "消息内容"

set -euo pipefail

AGENTS_DIR="${AGENTS_DIR:-$HOME/.agents/skills/zellij-talk}"
SCRIPTS="$AGENTS_DIR/scripts"

AGENTS_STR="${1:-}"
MESSAGE="${2:-}"

if [[ -z "$AGENTS_STR" || -z "$MESSAGE" ]]; then
  echo "❌ 用法: multicast.sh \"agent1,agent2\" \"消息内容\""
  exit 1
fi

IFS=',' read -ra AGENTS <<< "$AGENTS_STR"

for AGENT in "${AGENTS[@]}"; do
  # 去除首尾空格
  AGENT=$(echo "$AGENT" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
  if [[ -n "$AGENT" ]]; then
    "$SCRIPTS/to.sh" "$AGENT" "$MESSAGE" && echo "📢 已发送给 $AGENT" || echo "⚠️  $AGENT 发送失败"
  fi
done

echo "✅ 多播完成"
