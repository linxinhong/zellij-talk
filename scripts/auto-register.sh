#!/bin/bash
# 自动生成 Agent 名字并注册
# 用法: auto-register.sh [role，默认 coder]

set -euo pipefail

AGENTS_DIR="${AGENTS_DIR:-$HOME/.agents/skills/zellij-talk}"
REGISTRY="$AGENTS_DIR/registry.json"
SCRIPTS="$AGENTS_DIR/scripts"

ROLE="${1:-coder}"

# 自动推断当前 AI 工具名
TOOL="agent"
PPID_COMM=$(ps -p $PPID -o comm= 2>/dev/null || true)
PPID_ARGS=$(ps -p $PPID -o args= 2>/dev/null || true)

COMBINED="${PPID_COMM} ${PPID_ARGS}"
if echo "$COMBINED" | grep -qi "kimi"; then
  TOOL="kimi"
elif echo "$COMBINED" | grep -qi "claude"; then
  TOOL="claude"
elif echo "$COMBINED" | grep -qi "opencode"; then
  TOOL="opencode"
fi

# 可记忆英文名字池（A-Z）
NAMES=(
  "Alex" "Blob" "Cici" "David" "Ella" "Finn" "Gina" "Hugo"
  "Iris" "Jake" "Kiki" "Liam" "Mila" "Nico" "Olga" "Pete"
  "Quin" "Rita" "Sam"  "Tina" "Umar" "Vera" "Walt" "Xena"
  "York" "Zara"
)

# 冲突检测
mkdir -p "$AGENTS_DIR"
[[ -f "$REGISTRY" ]] || echo '{}' > "$REGISTRY"

# 从名字池中找一个未被占用的名字
NAME_IDX=$((RANDOM % ${#NAMES[@]}))
for ((i = 0; i < ${#NAMES[@]}; i++)); do
  CANDIDATE="${NAMES[$(( (NAME_IDX + i) % ${#NAMES[@]} ))]}"
  AGENT_NAME="${TOOL}_${ROLE}_${CANDIDATE}"
  if ! jq -e --arg n "$AGENT_NAME" '.[$n]' "$REGISTRY" > /dev/null 2>&1; then
    break
  fi
done

# 注册
"$SCRIPTS/register.sh" "$AGENT_NAME"

echo ""
echo "💡 提示：你可以在其他面板通过以下方式与我通信"
echo "   to.sh $AGENT_NAME \"你好\""
