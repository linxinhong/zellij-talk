# CLAUDE.md — zellij-talk Multi-Agent Workspace

> 全局上下文，每次 Claude Code 会话自动加载。
> 只写对所有任务普遍适用的内容，项目特定规则写在项目根目录的 CLAUDE.md。

---

## 一、工作区环境

你运行在一个基于 **Zellij** 的多面板 AI 协作工作区中。
面板数量、布局、位置均为运行时状态，**任何脚本和 Skill 都不应假设面板结构**。

你的身份信息由 Zellij 自动注入为环境变量：

```bash  
$ZELLIJ_SESSION_NAME   # 当前 session 名，字符串，全局唯一  
$ZELLIJ_PANE_ID        # 当前 pane_id，格式 terminal_N，仅在本 session 内唯一  
⚠️ 关键约束：pane_id 跨 session 不唯一（不同 session 里都可以有 terminal_3）。
定位任何一个 Agent 必须同时持有 session + pane_id 两个字段，缺一不可。

二、Agent 命名规范
命名格式
{agent_tool}_{main_role}_{4位唯一ID}
字段	说明	示例
agent_tool	运行该 Agent 的 AI 工具名	claude / kimi / opencode
main_role	该 Agent 在本次任务中的主要职责	coder / reviewer / tester / planner
4位唯一ID	随机大写字母+数字，防止同角色多实例冲突	23A3 / F1B9 / 0C4E
命名示例
css
claude_reviewer_23A3    ← Claude Code，负责代码审查
kimi_coder_F1B9        ← Kimi Code，负责功能编写
opencode_planner_0C4E  ← OpenCode，负责整理计划和 TODO
claude_tester_9D2A     ← 另一个 Claude Code 实例，负责测试
kimi_coder_B3E7        ← 又一个 Kimi Code 实例（与 F1B9 并行）
生成唯一 ID
bash
# 生成 4 位随机大写字母+数字 ID
generate_agent_id() {
  cat /dev/urandom | tr -dc 'A-Z0-9' | head -c 4
}

# 示例：生成完整 Agent 名
agent_name="claude_reviewer_$(generate_agent_id)"
echo $agent_name  # e.g. claude_reviewer_A7F2
冲突检测（注册前调用）
bash
# 检查名称是否已被占用
check_name_conflict() {
  local name="$1"
  local registry="$AGENTS_DIR/registry.json"
  if jq -e --arg n "$name" '.[$n]' "$registry" > /dev/null 2>&1; then
    echo "❌ 名称 [$name] 已被占用，请重新生成 ID"
    return 1
  fi
  return 0
}
三、Skill 系统
目录结构
ruby
~/.agents/skills/zellij-talk/
├── scripts/                    # 核心原语脚本（稳定层，轻易不改）
│   ├── register.sh             # Agent 注册
│   ├── unregister.sh           # Agent 注销
│   ├── auto-register.sh        # 自动生成名字并注册
│   ├── to.sh                   # 向 Agent 发送内容（支持管道）
│   ├── from.sh                 # 读取 Agent 输出
│   ├── watch.sh                # 实时监听 Agent 输出
│   ├── wait.sh                 # 阻塞等待关键词
│   ├── list.sh                 # 列出所有已注册 Agent
│   ├── health.sh               # Agent 健康检查
│   ├── prune.sh                # 清理僵尸 Agent
│   ├── send-file.sh            # 发送文件给 Agent
│   └── multicast.sh            # 多播消息给指定 Agent
│
└── registry.json               # 运行时 Agent 注册表（由脚本维护）
环境变量
bash
export AGENTS_DIR="$HOME/.agents/skills/zellij-talk"
export AGENTS_REGISTRY="$AGENTS_DIR/registry.json"
建议写入 ~/.zshrc 或 ~/.bashrc：

bash
echo 'export AGENTS_DIR="$HOME/.agents/skills/zellij-talk"' >> ~/.zshrc
echo 'export AGENTS_REGISTRY="$AGENTS_DIR/registry.json"' >> ~/.zshrc
四、核心原语脚本
scripts/register.sh — 注册当前面板为某个 Agent
bash
#!/bin/bash
# 用法: register.sh <agent_name>
# 例如: register.sh claude_reviewer_23A3
# 在需要注册的面板内执行

set -euo pipefail
AGENTS_DIR="${AGENTS_DIR:-$HOME/.agents/skills/zellij-talk}"
REGISTRY="$AGENTS_DIR/registry.json"

AGENT_NAME="$1"

# 前置检查
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
scripts/unregister.sh — 注销 Agent
bash
#!/bin/bash
# 用法: unregister.sh <agent_name>

REGISTRY="${AGENTS_REGISTRY:-$HOME/.agents/skills/zellij-talk/registry.json}"
AGENT_NAME="$1"

if ! jq -e --arg n "$AGENT_NAME" '.[$n]' "$REGISTRY" > /dev/null 2>&1; then
  echo "⚠️  [$AGENT_NAME] 未注册，跳过"
  exit 0
fi

jq --arg n "$AGENT_NAME" 'del(.[$n])' "$REGISTRY" > "${REGISTRY}.tmp"
mv "${REGISTRY}.tmp" "$REGISTRY"
echo "🗑️  [$AGENT_NAME] 已注销"
scripts/to.sh — 向某个 Agent 发送内容
bash
#!/bin/bash
# 用法: to.sh <agent_name> <内容> [--no-enter]
# 完全面板无关，通过注册表动态查找 session + pane_id

set -euo pipefail
REGISTRY="${AGENTS_REGISTRY:-$HOME/.agents/skills/zellij-talk/registry.json}"

AGENT_NAME="$1"
CONTENT="$2"
NO_ENTER="${3:-}"

# 从注册表读取（同时取 session 和 pane_id）
META=$(jq -e --arg n "$AGENT_NAME" '.[$n]' "$REGISTRY" 2>/dev/null) || {
  echo "❌ [$AGENT_NAME] 未注册，请先在对应面板执行 register.sh"
  exit 1
}

PANE_ID=$(echo "$META" | jq -r '.pane_id')
SESSION=$(echo "$META"  | jq -r '.session')

# 注入内容（不切换焦点）
zellij -s "$SESSION" action paste --pane-id "$PANE_ID" "$CONTENT"

if [[ "$NO_ENTER" != "--no-enter" ]]; then
  zellij -s "$SESSION" action send-keys --pane-id "$PANE_ID" "Enter"
fi

echo "📨 [$AGENT_NAME @ $PANE_ID / $SESSION] ← 已发送"
scripts/from.sh — 读取某个 Agent 的当前输出
bash
#!/bin/bash
# 用法: from.sh <agent_name> [行数，默认 100]

set -euo pipefail
REGISTRY="${AGENTS_REGISTRY:-$HOME/.agents/skills/zellij-talk/registry.json}"

AGENT_NAME="$1"
LINES="${2:-100}"

META=$(jq -e --arg n "$AGENT_NAME" '.[$n]' "$REGISTRY" 2>/dev/null) || {
  echo "❌ [$AGENT_NAME] 未注册"
  exit 1
}

PANE_ID=$(echo "$META" | jq -r '.pane_id')
SESSION=$(echo "$META"  | jq -r '.session')

zellij -s "$SESSION" action dump-screen \
  --pane-id "$PANE_ID" --full | tail -n "$LINES"
scripts/wait.sh — 阻塞等待关键词
bash
#!/bin/bash
# 用法: wait.sh <agent_name> <关键词> [超时秒数，默认 60]

set -uo pipefail
SCRIPTS="$HOME/.agents/skills/zellij-talk/scripts"

AGENT_NAME="${1:-}"
KEYWORD="${2:-}"
TIMEOUT="${3:-60}"
INTERVAL=2
LINES=100

echo "⏳ 等待 [$AGENT_NAME] 输出中出现关键词: '$KEYWORD' (超时 ${TIMEOUT}s)"

ELAPSED=0
while [[ $ELAPSED -lt $TIMEOUT ]]; do
  OUTPUT=$("$SCRIPTS/from.sh" "$AGENT_NAME" "$LINES" 2>/dev/null) || true
  if echo "$OUTPUT" | grep -q "$KEYWORD"; then
    echo "🎯 检测到关键词: $KEYWORD"
    echo "$OUTPUT" | grep "$KEYWORD"
    exit 0
  fi
  sleep "$INTERVAL"
  ELAPSED=$((ELAPSED + INTERVAL))
done

echo "⏰ 超时 (${TIMEOUT}s)，未检测到关键词: $KEYWORD"
exit 1
scripts/health.sh — Agent 健康检查
bash
#!/bin/bash
# 用法: health.sh [agent_name]
# 无参数时检查所有已注册 Agent

set -euo pipefail
REGISTRY="${AGENTS_REGISTRY:-$HOME/.agents/skills/zellij-talk/registry.json}"

TARGET_AGENT="${1:-}"
if [[ -n "$TARGET_AGENT" ]]; then
  META=$(jq -e --arg n "$TARGET_AGENT" '.[$n]' "$REGISTRY" 2>/dev/null) || {
    echo "❌ [$TARGET_AGENT] 未注册"
    exit 1
  }
  # ... 检查逻辑
else
  # ... 遍历检查所有 Agent
fi
scripts/prune.sh — 清理僵尸 Agent
bash
#!/bin/bash
# 用法: prune.sh [--dry-run]
# 扫描注册表，删除 session/pane 已失效的记录

set -euo pipefail
REGISTRY="${AGENTS_REGISTRY:-$HOME/.agents/skills/zellij-talk/registry.json}"
# 通过 dump-screen 检测每个 Agent 的 session/pane 是否存活
# 失效则删除记录
scripts/send-file.sh — 发送文件
bash
#!/bin/bash
# 用法: send-file.sh <agent_name> <file_path>
# 读取文件并自动包裹代码块，通过 to.sh 发送

set -euo pipefail
SCRIPTS="$HOME/.agents/skills/zellij-talk/scripts"
AGENT_NAME="$1"
FILE_PATH="$2"
# ... 推断语言、包裹代码块、调用 to.sh
scripts/multicast.sh — 多播消息
bash
#!/bin/bash
# 用法: multicast.sh "agent1,agent2" "消息内容"

set -euo pipefail
SCRIPTS="$HOME/.agents/skills/zellij-talk/scripts"
IFS=',' read -ra AGENTS <<< "$1"
for AGENT in "${AGENTS[@]}"; do
  AGENT=$(echo "$AGENT" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
  "$SCRIPTS/to.sh" "$AGENT" "$2"
done
scripts/list.sh — 列出所有已注册 Agent
bash
#!/bin/bash
# 用法: list.sh [--json]

REGISTRY="${AGENTS_REGISTRY:-$HOME/.agents/skills/zellij-talk/registry.json}"

if [[ ! -f "$REGISTRY" ]]; then
  echo "（注册表为空）"
  exit 0
fi

if [[ "${1:-}" == "--json" ]]; then
  jq . "$REGISTRY"
else
  echo "已注册的 Agent："
  echo "────────────────────────────────────────────────"
  jq -r 'to_entries[] | "\(.key)\n  pane_id  : \(.value.pane_id)\n  session  : \(.value.session)\n  注册时间 : \(.value.registered)\n"' "$REGISTRY"
fi
五、Skill 开发规范
Skill 模板
bash
#!/bin/bash
# Skill 名称：xxx.sh
# 职责：描述这个 Skill 做什么
# 用法：xxx.sh [参数]

set -euo pipefail
SCRIPTS="$HOME/.agents/skills/zellij-talk/scripts"

# ✅ 只认 Agent 名，不认 pane_id
SOURCE_AGENT="kimi_coder_F1B9"
TARGET_AGENT="claude_reviewer_23A3"

# 读取源 Agent 的输出
CONTENT=$("$SCRIPTS/from.sh" "$SOURCE_AGENT" 80)

# 构造 Prompt 并发送给目标 Agent
"$SCRIPTS/to.sh" "$TARGET_AGENT" "你的任务描述：

$CONTENT"
Skill 三原则
原则	说明
面板无关	不硬编码 pane_id，所有路由通过 Agent 名 → 注册表动态查找
session + pane_id 缺一不可	跨 session 的 pane_id 不唯一，两个字段必须同时使用
Agent 名唯一	同一工作区内不允许重复的 Agent 名，注册前必须做冲突检测
六、典型工作流
bash
# ── 启动阶段（每个面板内各执行一次）──────────────────────────

# 在 Kimi Code 面板内
~/.agents/skills/zellij-talk/scripts/register.sh kimi_coder_F1B9

# 在 Claude Code 面板内（你自己）
~/.agents/skills/zellij-talk/scripts/register.sh claude_reviewer_23A3

# 在 OpenCode 面板内
~/.agents/skills/zellij-talk/scripts/register.sh opencode_planner_0C4E


# ── 任务阶段（在任意面板/任意位置调用）──────────────────────

# 查看所有已注册的 Agent
~/.agents/skills/zellij-talk/scripts/list.sh

# 一次性发送任务（面板无关）
~/.agents/skills/zellij-talk/scripts/to.sh kimi_coder_F1B9 \
  "帮我实现一个 LRU Cache，用 Rust 写"

# 调用 Skill（组合多个 Agent 的协作）
~/.agents/skills/zellij-talk/scripts/review.sh

# 后台监听某个 Agent，检测到完成信号时触发下游
~/.agents/skills/zellij-talk/scripts/watch.sh \
  claude_reviewer_23A3 "审查完成" &

# Agent 完成任务后注销
~/.agents/skills/zellij-talk/scripts/unregister.sh kimi_coder_F1B9
七、快速参考
bash
# 注册自己（在当前面板执行）
~/.agents/skills/zellij-talk/scripts/register.sh <agent_name>

# 向任意 Agent 发内容
~/.agents/skills/zellij-talk/scripts/to.sh <agent_name> "<内容>"

# 读取任意 Agent 的输出
~/.agents/skills/zellij-talk/scripts/from.sh <agent_name> [行数]

# 监听任意 Agent
~/.agents/skills/zellij-talk/scripts/watch.sh <agent_name> [关键词]

# 查看注册表
~/.agents/skills/zellij-talk/scripts/list.sh
yaml

---  

几个关键设计决策的说明：  

**关于 `pane_id + session` 必须同时存在：**  
- `pane_id` 格式是 `terminal_N`，在同一 session 内唯一 [ref:12]()  
- 不同 session 完全可以各自有 `terminal_3`，单独用 pane_id 定位会打到错误的 Agent  
- 所以注册表里两个字段缺一不可，`to.sh` / `from.sh` 也都同时读取两个字段  

**关于 Agent 命名：**  
- `claude_reviewer_23A3` 这种格式，一眼就能看出"谁在做什么"，4位 ID 解决了同角色多实例的冲突问题  
- 注册时做冲突检测，杜绝同名覆盖导致消息路由混乱
