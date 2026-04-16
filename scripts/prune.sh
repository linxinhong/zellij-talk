#!/bin/bash
# 清理注册表中已失效的僵尸 Agent
# 用法: prune.sh [--dry-run]

set -euo pipefail

AGENTS_DIR="${AGENTS_DIR:-$HOME/.agents/skills/zellij-talk}"
REGISTRY="$AGENTS_DIR/registry.json"
DRY_RUN=false

if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=true
fi

if [[ ! -f "$REGISTRY" ]]; then
  echo "（注册表不存在）"
  exit 0
fi

PRUNE_LIST=()
TOTAL=0

while IFS=$'\t' read -r NAME PANE SESSION; do
  TOTAL=$((TOTAL + 1))

  STDOUT_FILE=$(mktemp)
  STDERR_FILE=$(mktemp)

  # 分别捕获 stdout 和 stderr
  zellij --session "$SESSION" action dump-screen --pane-id "$PANE" --full \
    >"$STDOUT_FILE" 2>"$STDERR_FILE" || true

  # Session 不存在时 stderr 会有提示
  if grep -qE "Session .* not found" "$STDERR_FILE" 2>/dev/null; then
    PRUNE_LIST+=("$NAME")
    rm -f "$STDOUT_FILE" "$STDERR_FILE"
    continue
  fi

  # Pane 不存在时 stdout 为空
  if [[ ! -s "$STDOUT_FILE" ]]; then
    PRUNE_LIST+=("$NAME")
    rm -f "$STDOUT_FILE" "$STDERR_FILE"
    continue
  fi

  rm -f "$STDOUT_FILE" "$STDERR_FILE"
done < <(jq -r 'to_entries[] | [.key, .value.pane_id, .value.session] | @tsv' "$REGISTRY")

if [[ ${#PRUNE_LIST[@]} -eq 0 ]]; then
  echo "✅ 所有 $TOTAL 个 Agent 均在线，无需清理"
  exit 0
fi

for NAME in "${PRUNE_LIST[@]}"; do
  if [[ "$DRY_RUN" == true ]]; then
    echo "🟡 [dry-run] 将清理: $NAME"
  else
    jq --arg n "$NAME" 'del(.[$n])' "$REGISTRY" > "${REGISTRY}.tmp"
    mv "${REGISTRY}.tmp" "$REGISTRY"
    echo "🗑️  已清理: $NAME"
  fi
done

if [[ "$DRY_RUN" == true ]]; then
  echo "────────────────────────────────────"
  echo "共发现 ${#PRUNE_LIST[@]} / $TOTAL 个僵尸 Agent（未实际删除）"
else
  echo "────────────────────────────────────"
  echo "✅ 共清理 ${#PRUNE_LIST[@]} / $TOTAL 个僵尸 Agent"
fi
