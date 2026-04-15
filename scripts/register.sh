#!/bin/bash
# Agent 注册脚本
# 用法: register.sh <agent_name>
# 例如: register.sh claude_reviewer_23A3
# 在需要注册的面板内执行

set -euo pipefail

AGENTS_DIR="${AGENTS_DIR:-$HOME/.agents/skills/zellij-talk}"
REGISTRY="$AGENTS_DIR/registry.json"

AGENT_NAME="${1:-}"

# 参数检查
if [[ -z "$AGENT_NAME" ]]; then
  echo "❌ 用法: register.sh <agent_name>"
  exit 1
fi

# 前置检查：必须 Zellij 环境
if [[ -z "${ZELLIJ_PANE_ID:-}" || -z "${ZELLIJ_SESSION_NAME:-}" ]]; then
  echo "❌ 未检测到 Zellij 环境变量，请在 Zellij 面板内执行此脚本"
  exit 1
fi

mkdir -p "$AGENTS_DIR"
[[ -f "$REGISTRY" ]] || echo '{}' > "$REGISTRY"

# 冲突检测
if jq -e --arg n "$AGENT_NAME" '.[$n]' "$REGISTRY" > /dev/null 2>&1; then
  echo "⚠️  [$AGENT_NAME] 已注册，将覆盖旧记录"
fi

# 写入注册表（session + pane_id 必须同时记录）
UPDATED=$(jq \
  --arg name    "$AGENT_NAME" \
  --arg pane    "$ZELLIJ_PANE_ID" \
  --arg session "$ZELLIJ_SESSION_NAME" \
  --arg ts      "$(date -Iseconds)" \
  '.[$name] = {
    "pane_id":    $pane,
    "session":    $session,
    "registered": $ts
  }' "$REGISTRY")

echo "$UPDATED" > "$REGISTRY"
echo "✅ [$AGENT_NAME] 注册成功"
echo "   pane_id : $ZELLIJ_PANE_ID"
echo "   session : $ZELLIJ_SESSION_NAME"
