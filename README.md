# zellij-talk

基于 [Zellij](https://zellij.dev) 的多面板 AI Agent 协作框架。让多个 AI 实例在不同的 Zellij 面板中协同工作，实现任务分发、并行处理与跨面板消息路由。

## 核心概念

- **Agent**：运行在 Zellij 面板中的 AI 实例
- **注册表**：`registry.json` 记录所有 Agent 的 `session` + `pane_id`
- **消息路由**：通过 Agent 名而非 `pane_id` 动态路由，完全面板无关
- **惰性清理**：对 Agent 执行 `to` / `from` / `broadcast` / `multicast` 等操作时，如果目标 pane 已关闭，会自动从注册表中移除该 Agent

## 环境要求

- [Zellij](https://zellij.dev/documentation/installation.html) 终端复用器
- Python 3.9+

## 安装

克隆仓库到本地，建议放到 `~/.agents/skills/zellij-talk`：

```bash
git clone https://github.com/yourname/zellij-talk.git ~/.agents/skills/zellij-talk
```

在 `~/.zshrc` 或 `~/.bashrc` 中添加环境变量：

```bash
export AGENTS_DIR="$HOME/.agents/skills/zellij-talk"
export AGENTS_REGISTRY="$AGENTS_DIR/registry.json"
```

然后重载配置：

```bash
source ~/.zshrc  # 或 source ~/.bashrc
```

首次使用前，复制注册表模板：

```bash
cp "$AGENTS_DIR/registry.json.example" "$AGENTS_DIR/registry.json"
```

## 目录结构

```
zellij-talk/
├── README.md                 # 本文件
├── SKILL.md                  # Kimi Skill 说明
├── .gitignore                # 排除运行时文件
├── pyproject.toml            # Python 项目配置
├── registry.json.example     # 注册表模板
├── src/
│   └── zellij_talk/          # Python 核心实现
│       ├── __init__.py
│       ├── registry.py       # 注册表管理（原子写、无 jq 依赖）
│       ├── zellij.py         # Zellij CLI 封装
│       └── cli.py            # 统一命令行入口
└── scripts/                  # 薄包装脚本（向后兼容）
    ├── register.sh
    ├── unregister.sh
    ├── unregister-all.sh
    ├── auto-register.sh
    ├── to.sh
    ├── from.sh
    ├── watch.sh
    ├── wait.sh
    ├── list.sh
    ├── health.sh
    ├── prune.sh
    ├── send-file.sh
    ├── multicast.sh
    ├── broadcast.sh
    └── review.sh
```

## 快速开始

### 1. 命名规范

格式：`{agent_tool}_{main_role}_{可记忆英文名}`

| 字段 | 说明 | 示例 |
|------|------|------|
| `agent_tool` | AI 工具名 | `claude` / `kimi` / `opencode` |
| `main_role` | 主要职责 | `coder` / `reviewer` / `tester` / `planner` |
| `可记忆英文名` | 便于识别的名字 | `Blob` / `Alex` / `Cici` |

示例：

```bash
claude_reviewer_Blob    # Claude Code，负责代码审查
kimi_coder_Alex        # Kimi Code，负责功能编写
opencode_planner_Cici  # OpenCode，负责整理计划
```

### 2. 注册 Agent

在每个 Zellij 面板中分别执行：

```bash
# Kimi Code 面板
~/.agents/skills/zellij-talk/scripts/register.sh kimi_coder_Alex

# Claude Code 面板
~/.agents/skills/zellij-talk/scripts/register.sh claude_reviewer_Blob
```

### 3. 发送与读取消息

```bash
# 向某个 Agent 发送消息
~/.agents/skills/zellij-talk/scripts/to.sh kimi_coder_Alex "帮我实现一个 LRU Cache，用 Rust 写"

# 读取某个 Agent 的最新输出（默认 100 行）
~/.agents/skills/zellij-talk/scripts/from.sh claude_reviewer_Blob

# 列出所有已注册 Agent
~/.agents/skills/zellij-talk/scripts/list.sh
```

### 4. 运行示例工作流

```bash
# 将 kimi_coder 的输出转发给 claude_reviewer 审查
~/.agents/skills/zellij-talk/scripts/review.sh
```

### 5. 注销 Agent

```bash
# 注销单个 Agent
~/.agents/skills/zellij-talk/scripts/unregister.sh kimi_coder_Alex

# 或一键注销当前 session 的所有 Agent
~/.agents/skills/zellij-talk/scripts/unregister-all.sh --current-session
```

## 工作模式

### 实时协作模式

适用于复杂项目，多个 AI 实时沟通：

1. 在 Zellij 中创建多个面板
2. 各面板分别注册 Agent
3. 通过 `to.sh` / `from.sh` 实时沟通
4. 任务完成后注销

### 流水线模式

适用于任务依次经过多个 Agent 处理：

```
需求分析 → 代码实现 → 测试 → 报告
    ↓          ↓        ↓       ↓
 Planner    Coder   Tester   Reporter
```

## 核心脚本参考

| 脚本 | 用法 | 说明 |
|------|------|------|
| `register.sh` | `register.sh <agent_name>` | 注册当前面板为 Agent |
| `unregister.sh` | `unregister.sh <agent_name>` | 注销指定 Agent |
| `unregister-all.sh` | `unregister-all.sh [--current-session]` | 批量注销 |
| `auto-register.sh` | `auto-register.sh [role]` | 自动生成名字并注册 |
| `to.sh` | `to.sh <agent_name> <内容> [--no-enter]` | 发送消息（ pane 已关闭时会自动清理注册表） |
| `from.sh` | `from.sh <agent_name> [行数] [--ansi]` | 读取输出（ pane 已关闭时会自动清理注册表） |
| `watch.sh` | `watch.sh <agent_name> [关键词]` | 监听输出 |
| `wait.sh` | `wait.sh <agent_name> <关键词> [超时秒数]` | 阻塞等待关键词 |
| `list.sh` | `list.sh [--json]` | 列出已注册 Agent |
| `health.sh` | `health.sh [agent_name]` | 健康检查 |
| `prune.sh` | `prune.sh [--dry-run]` | 清理僵尸 Agent |
| `send-file.sh` | `send-file.sh <agent_name> <file_path>` | 发送文件 |
| `multicast.sh` | `multicast.sh "agent1,agent2" "消息"` | 多播消息 |
| `broadcast.sh` | `broadcast.sh "消息"` | 广播给所有 Agent |
| `review.sh` | `review.sh [source] [target]` | 代码审查工作流示例 |

## 直接使用 Python CLI

如果你不想通过 `scripts/*.sh` 调用，也可以直接使用 Python 模块：

```bash
# 设置 PYTHONPATH
export PYTHONPATH="$AGENTS_DIR/src:$PYTHONPATH"

# 列出 Agent
python3 -m zellij_talk.cli list

# 发送消息
python3 -m zellij_talk.cli to kimi_coder_Alex "你好"

# 清理僵尸 Agent
python3 -m zellij_talk.cli prune --dry-run
```

## 开发规范

新建脚本时遵循以下原则：

1. **面板无关**：不硬编码 `pane_id`，所有路由通过 Agent 名动态查找
2. **双重定位**：`session` + `pane_id` 缺一不可（跨 session 的 `pane_id` 可能重复）
3. **唯一命名**：同一工作区内不允许重复的 Agent 名
4. **自动清理**：对 Agent 操作时优先检查 pane 存活状态，失效则自动从注册表移除

示例模板：

```bash
#!/bin/bash
set -euo pipefail
SCRIPTS="$HOME/.agents/skills/zellij-talk/scripts"

SOURCE_AGENT="kimi_coder_Alex"
TARGET_AGENT="claude_reviewer_Blob"

CONTENT=$("$SCRIPTS/from.sh" "$SOURCE_AGENT" 80)
"$SCRIPTS/to.sh" "$TARGET_AGENT" "处理后的内容：$CONTENT"
```

## 故障排除

### "未检测到 Zellij 环境变量"

必须在 Zellij 面板内执行 `register.sh`。直接在普通终端运行会报此错误。

### "Agent 未注册"

```bash
~/.agents/skills/zellij-talk/scripts/list.sh
```

确认目标 Agent 已在对应面板注册。如果 pane 已关闭但记录残留，运行：

```bash
~/.agents/skills/zellij-talk/scripts/prune.sh
```

**注意**：现在 `to.sh`、`from.sh`、`broadcast.sh`、`multicast.sh` 会在目标 pane 不存在时**自动清理**注册表，因此通常无需手动运行 `prune.sh`。

## License

MIT
