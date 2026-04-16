#!/bin/bash
# 读取文件并通过 to.sh 发送给指定 Agent
# 用法: send-file.sh <agent_name> <file_path>

set -euo pipefail

AGENTS_DIR="${AGENTS_DIR:-$HOME/.agents/skills/zellij-talk}"
SCRIPTS="$AGENTS_DIR/scripts"

AGENT_NAME="${1:-}"
FILE_PATH="${2:-}"

if [[ -z "$AGENT_NAME" || -z "$FILE_PATH" ]]; then
  echo "❌ 用法: send-file.sh <agent_name> <file_path>"
  exit 1
fi

if [[ ! -f "$FILE_PATH" ]]; then
  echo "❌ 文件不存在: $FILE_PATH"
  exit 1
fi

# 推断语言
EXT="${FILE_PATH##*.}"
LANG=""
case "$EXT" in
  rs)  LANG="rust" ;;
  py)  LANG="python" ;;
  js)  LANG="javascript" ;;
  ts)  LANG="typescript" ;;
  tsx) LANG="tsx" ;;
  jsx) LANG="jsx" ;;
  go)  LANG="go" ;;
  sh|bash|zsh) LANG="bash" ;;
  md)  LANG="markdown" ;;
  json) LANG="json" ;;
  yaml|yml) LANG="yaml" ;;
  html) LANG="html" ;;
  css) LANG="css" ;;
  java) LANG="java" ;;
  cpp|c|h|hpp) LANG="cpp" ;;
  *)   LANG="" ;;
esac

FILENAME=$(basename "$FILE_PATH")
CONTENT=$(cat "$FILE_PATH")

if [[ -n "$LANG" ]]; then
  MESSAGE="请查看文件 \`$FILENAME\`：

\`\`\`$LANG
$CONTENT
\`\`\`
"
else
  MESSAGE="请查看文件 \`$FILENAME\`：

\`\`\`
$CONTENT
\`\`\`
"
fi

"$SCRIPTS/to.sh" "$AGENT_NAME" "$MESSAGE"
