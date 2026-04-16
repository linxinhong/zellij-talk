#!/bin/bash
# 向指定 Agent 发送内容
# 用法: to.sh <agent_name> [内容] [--no-enter]
# 支持管道: echo "msg" | to.sh agent_name
#           echo "msg" | to.sh agent_name --no-enter

set -euo pipefail

AGENTS_DIR="${AGENTS_DIR:-$HOME/.agents/skills/zellij-talk}"
REGISTRY="$AGENTS_DIR/registry.json"

AGENT_NAME=""
CONTENT=""
NO_ENTER=false
STDIN_CONTENT=""

# 检测 stdin 是否有数据
if [[ -p /dev/stdin ]] || ! [[ -t 0 ]]; then
  STDIN_CONTENT=$(cat)
fi

# 解析参数
for arg in "$@"; do
  case "$arg" in
    --no-enter)
      NO_ENTER=true
      ;;
    *)
      if [[ -z "$AGENT_NAME" ]]; then
        AGENT_NAME="$arg"
      elif [[ -z "$CONTENT" ]]; then
        CONTENT="$arg"
      else
        CONTENT="$CONTENT $arg"
      fi
      ;;
  esac
done

if [[ -z "$AGENT_NAME" ]]; then
  echo "❌ 用法: to.sh <agent_name> [内容] [--no-enter]"
  echo "       echo '<内容>' | to.sh <agent_name> [--no-enter]"
  exit 1
fi

# 优先使用 stdin，其次使用参数
if [[ -n "$STDIN_CONTENT" ]]; then
  CONTENT="$STDIN_CONTENT"
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
zellij --session "$SESSION" action paste --pane-id "$PANE_ID" "$CONTENT"

if [[ "$NO_ENTER" == false ]]; then
  zellij --session "$SESSION" action send-keys --pane-id "$PANE_ID" "Enter"
fi

echo "📨 [$AGENT_NAME @ $PANE_ID / $SESSION] ← 已发送"
