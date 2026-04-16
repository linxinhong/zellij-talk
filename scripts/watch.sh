#!/bin/bash
# 实时监听某个 Agent 的输出
# 用法: watch.sh <agent_name> [关键词，检测到时执行回调]
# 例如: watch.sh claude_reviewer_Blob "审查完成"

set -euo pipefail

AGENTS_DIR="${AGENTS_DIR:-$HOME/.agents/skills/zellij-talk}"
REGISTRY="$AGENTS_DIR/registry.json"

AGENT_NAME="${1:-}"
KEYWORD="${2:-}"

if [[ -z "$AGENT_NAME" ]]; then
  echo "❌ 用法: watch.sh <agent_name> [关键词]"
  exit 1
fi

META=$(jq -e --arg n "$AGENT_NAME" '.[$n]' "$REGISTRY" 2>/dev/null) || {
  echo "❌ [$AGENT_NAME] 未注册"
  exit 1
}

PANE_ID=$(echo "$META" | jq -r '.pane_id')
SESSION=$(echo "$META" | jq -r '.session')

echo "👀 监听 [$AGENT_NAME @ $PANE_ID / $SESSION] ..."
echo "   关键词: ${KEYWORD:-（不过滤）}"

zellij --session "$SESSION" subscribe \
  --pane-id "$PANE_ID" --format json | \
while IFS= read -r line; do
  # viewport 是字符串数组，不是对象数组
  text=$(echo "$line" | jq -r '.viewport // empty | join("\n")' 2>/dev/null)
  [[ -z "$text" ]] && continue

  if [[ -z "$KEYWORD" ]]; then
    echo "$text"
  elif echo "$text" | grep -q "$KEYWORD"; then
    echo "🎯 [$AGENT_NAME] 检测到关键词: $KEYWORD"
    echo "$text"
    # 可在此处插入回调逻辑，例如触发下游 Skill
  fi
done
