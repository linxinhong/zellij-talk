#!/bin/bash
# Skill: review.sh
# 职责：读取 kimi coder 输出 → 发给 claude reviewer 审查
# 用法：review.sh [source_agent] [target_agent]

set -euo pipefail

SCRIPTS="$HOME/.agents/skills/zellij-talk/scripts"

# 默认 Agent 名（可配置）
SOURCE_AGENT="${1:-kimi_coder_Alex}"
TARGET_AGENT="${2:-claude_reviewer_Blob}"

# 读取源 Agent 的输出
CONTENT=$("$SCRIPTS/from.sh" "$SOURCE_AGENT" 80)

# 构造 Prompt 并发送给目标 Agent
"$SCRIPTS/to.sh" "$TARGET_AGENT" "请审查以下代码：

$CONTENT

---
审查要点：
1. 代码正确性
2. 潜在 bug
3. 性能问题
4. 可读性与维护性
"
