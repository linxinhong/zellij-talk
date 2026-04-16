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
git clone https://github.com/linxinhong/zellij-talk.git ~/.agents/skills/zellij-talk
```

项目会默认将配置和数据保存在跨平台的 Zellij 配置目录下：
- **macOS / Linux**：`~/.config/zellij/talk/`
- **Windows**：`%APPDATA%\zellij\talk\`

该目录下自动创建：
- `registry.json` — Agent 注册表
- `sessions/` — 各 session 的对话日志（`{session}.md`）以及全局汇总 `all.md`

如需自定义注册表路径，可设置环境变量：

```bash
export AGENTS_REGISTRY="/custom/path/registry.json"
```

如果经常在**普通终端**（非 Zellij）向 Zellij 里的 Agent 发消息，可以设置发送方显示名称，方便日志追溯：

```bash
export ZELLIJ_TALK_FROM="local_planner"
```

首次使用前，如果你需要模板，可以复制注册表模板到默认路径：

```bash
mkdir -p ~/.config/zellij/talk
cp registry.json.example ~/.config/zellij/talk/registry.json
```

## 目录结构

```
zellij-talk/
├── README.md                 # 本文件
├── SKILL.md                  # Kimi Skill 说明
├── .gitignore                # 排除运行时文件
├── registry.json.example     # 注册表模板
└── scripts/                  # Python 核心脚本
    ├── __init__.py
    ├── registry.py           # 注册表管理（原子写、无 jq 依赖）
    ├── zellij.py             # Zellij CLI 封装
    └── cli.py                # 统一命令行入口
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
python3 "$AGENTS_DIR/scripts/cli.py" register kimi_coder_Alex

# Claude Code 面板
python3 "$AGENTS_DIR/scripts/cli.py" register claude_reviewer_Blob
```

### 3. 发送与读取消息

```bash
# 向某个 Agent 发送消息
python3 "$AGENTS_DIR/scripts/cli.py" to kimi_coder_Alex "帮我实现一个 LRU Cache，用 Rust 写"

接收方 Agent 收到的消息会自动附带发送方标识，例如：
```
[来自 kimi_coder_Alex (session: rectangular-viola / pane 1)]
帮我实现一个 LRU Cache，用 Rust 写
```

如果对方未注册，也可以直接通过 `session:pane_id` 回复：

```bash
python3 "$AGENTS_DIR/scripts/cli.py" reply rectangular-viola:1 "收到，继续"
```

# 读取某个 Agent 的最新输出（默认 100 行）
python3 "$AGENTS_DIR/scripts/cli.py" from claude_reviewer_Blob

# 列出所有已注册 Agent
python3 "$AGENTS_DIR/scripts/cli.py" list
```

### 4. 运行示例工作流

```bash
# 将 kimi_coder 的输出转发给 claude_reviewer 审查
python3 "$AGENTS_DIR/scripts/cli.py" review
```

### 5. 注销 Agent

```bash
# 注销单个 Agent
python3 "$AGENTS_DIR/scripts/cli.py" unregister kimi_coder_Alex

# 或一键注销当前 session 的所有 Agent
python3 "$AGENTS_DIR/scripts/cli.py" unregister-all --current-session
```

## 工作模式

### 实时协作模式

适用于复杂项目，多个 AI 实时沟通：

1. 在 Zellij 中创建多个面板
2. 各面板分别注册 Agent
3. 通过 `python3 scripts/cli.py to` / `from` 实时沟通
4. 任务完成后注销

### 流水线模式

适用于任务依次经过多个 Agent 处理：

```
需求分析 → 代码实现 → 测试 → 报告
    ↓          ↓        ↓       ↓
 Planner    Coder   Tester   Reporter
```

## 核心命令参考

所有命令统一通过 `python3 "$AGENTS_DIR/scripts/cli.py" <子命令>` 调用。你可以随时查看完整帮助：

```bash
python3 "$AGENTS_DIR/scripts/cli.py" --help
```

| 子命令 | 用法 | 说明 |
|--------|------|------|
| `register` | `register <agent_name>` | 注册当前面板为 Agent |
| `unregister` | `unregister <agent_name>` | 注销指定 Agent |
| `unregister-all` | `unregister-all [--current-session]` | 批量注销 |
| `auto-register` | `auto-register [role]` | 自动生成名字并注册 |
| `to` | `to <agent_name> <内容> [--no-enter]` | 发送消息（pane 已关闭时自动清理） |
| `reply` | `reply <session:pane_id> <内容> [--no-enter]` | 直接向 pane 发消息（无需注册） |
| `from` | `from <agent_name> [行数] [--ansi]` | 读取输出（pane 已关闭时自动清理） |
| `watch` | `watch <agent_name> [标签]` | 监听输出 |
| `wait` | `wait <agent_name> <标签> [超时秒数]` | 阻塞等待 <talk>标签</talk> |
| `list` | `list [--json]` | 列出已注册 Agent |
| `health` | `health [agent_name]` | 健康检查 |
| `memory` | `memory [--session] [--pane] [--agent] [--last N] [--json]` | 查询对话历史 |
| `prune` | `prune [--dry-run]` | 清理僵尸 Agent |
| `send-file` | `send-file <agent_name> <file_path>` | 发送文件 |
| `multicast` | `multicast "agent1,agent2" "消息"` | 多播消息 |
| `broadcast` | `broadcast "消息"` | 广播给所有 Agent |
| `review` | `review [source] [target]` | 代码审查工作流示例 |

## 开发规范

新建脚本时遵循以下原则：

1. **面板无关**：不硬编码 `pane_id`，所有路由通过 Agent 名动态查找
2. **双重定位**：`session` + `pane_id` 缺一不可（跨 session 的 `pane_id` 可能重复）
3. **唯一命名**：同一工作区内不允许重复的 Agent 名
4. **自动清理**：操作 Agent 前自动检查 pane 存活状态，失效则自动移除注册记录

示例模板：

```bash
#!/bin/bash
set -euo pipefail
AGENTS_DIR="${AGENTS_DIR:-$HOME/.agents/skills/zellij-talk}"

SOURCE_AGENT="kimi_coder_Alex"
TARGET_AGENT="claude_reviewer_Blob"

CONTENT=$(python3 "$AGENTS_DIR/scripts/cli.py" from "$SOURCE_AGENT" 80)
python3 "$AGENTS_DIR/scripts/cli.py" to "$TARGET_AGENT" "处理后的内容：$CONTENT"
```

也可以直接用 Python 写扩展：

```python
import sys
sys.path.insert(0, "scripts")
from registry import list_agents
from zellij import dump_screen, send_text
```

## 故障排除

### "未检测到 Zellij 环境变量"

必须在 Zellij 面板内执行 `register`。直接在普通终端运行会报此错误。

### "Agent 未注册"

```bash
python3 "$AGENTS_DIR/scripts/cli.py" list
```

确认目标 Agent 已在对应面板注册。如果 pane 已关闭但记录残留，运行：

```bash
python3 "$AGENTS_DIR/scripts/cli.py" prune
```

**注意**：`to`、`from`、`broadcast`、`multicast` 会在目标 pane 不存在时**自动清理**注册表，因此通常无需手动运行 `prune`。

### 读取输出为空

可能原因：
1. 面板尚未产生输出
2. pane_id 已失效
3. 需要增加行数：`python3 "$AGENTS_DIR/scripts/cli.py" from <agent> 200`

## 查询对话历史

所有发送的消息都会自动记录，可以通过 `memory` 命令查询：

```bash
# 查看最近 20 条全局对话
python3 "$AGENTS_DIR/scripts/cli.py" memory

# 查看指定 session 的记录
python3 "$AGENTS_DIR/scripts/cli.py" memory --session rectangular-viola

# 查看指定 Agent 的记录
python3 "$AGENTS_DIR/scripts/cli.py" memory --agent kimi_coder_Finn --last 5

# JSON 格式输出
python3 "$AGENTS_DIR/scripts/cli.py" memory --session rectangular-viola --json
```

## 自定义注册表路径

如果你希望把 `registry.json` 放到其他位置（例如多个项目共享同一个注册表），可以设置环境变量：

```bash
export AGENTS_REGISTRY="/custom/path/registry.json"
```

## License

MIT
