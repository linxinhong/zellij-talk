#!/bin/bash
# Agent 注销脚本
# 用法: unregister.sh <agent_name>

set -euo pipefail

AGENTS_DIR="${AGENTS_DIR:-$HOME/.agents/skills/zellij-talk}"
REGISTRY="$AGENTS_DIR/registry.json"

AGENT_NAME="${1:-}"

if [[ -z "$AGENT_NAME" ]]; then
  echo "❌ 用法: unregister.sh <agent_name>"
  exit 1
fi

if [[ ! -f "$REGISTRY" ]]; then
  echo "⚠️  [$AGENT_NAME] 未注册（注册表不存在）"
  exit 0
fi

if ! jq -e --arg n "$AGENT_NAME" '.[$n]' "$REGISTRY" > /dev/null 2>&1; then
  echo "⚠️  [$AGENT_NAME] 未注册，跳过"
  exit 0
fi

jq --arg n "$AGENT_NAME" 'del(.[$n])' "$REGISTRY" > "${REGISTRY}.tmp"
mv "${REGISTRY}.tmp" "$REGISTRY"
echo "🗑️  [$AGENT_NAME] 已注销"
