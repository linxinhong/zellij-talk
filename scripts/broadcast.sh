#!/bin/bash
# Skill: broadcast.sh
# 职责：向所有已注册 Agent 广播消息
# 用法：broadcast.sh <消息内容>

set -euo pipefail

SCRIPTS="$HOME/.agents/skills/zellij-talk/scripts"
REGISTRY="$HOME/.agents/skills/zellij-talk/registry.json"

MESSAGE="${1:-}"

if [[ -z "$MESSAGE" ]]; then
  echo "❌ 用法: broadcast.sh <消息内容>"
  exit 1
fi

if [[ ! -f "$REGISTRY" ]]; then
  echo "❌ 注册表不存在，无 Agent 可广播"
  exit 1
fi

# 获取所有已注册 Agent
AGENTS=$(jq -r 'keys[]' "$REGISTRY")

for AGENT in $AGENTS; do
  "$SCRIPTS/to.sh" "$AGENT" "$MESSAGE" && echo "📢 已广播给 $AGENT" || echo "⚠️  $AGENT 广播失败"
done

echo "✅ 广播完成"
