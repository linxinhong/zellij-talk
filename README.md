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

## 初始化

当本技能被加载/触发时，AI 会立即执行以下步骤：

**1. 执行 `init` 初始化环境**

```bash
python3 "$AGENTS_DIR/scripts/cli.py" init
```

`init` 会依次完成：检查 `zellij`、确保数据目录存在、从模板创建 `registry.json`（若缺失）、执行 `prune` 清理僵尸 Agent。

**2. 确认职责后注册**

AI 会询问当前 Agent 的职责（如 coder、reviewer、planner、tester 等），再根据回答注册：

```bash
python3 "$AGENTS_DIR/scripts/cli.py" auto-register <role>
```

> 若不在 Zellij 环境中，注册命令会提示错误，这是正常的。

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

## 全局 CLI 入口 `zt`

安装后可以直接使用 `zt` 命令：

```bash
cd ~/.agents/skills/zellij-talk
pip install -e .
```

然后全局使用：

```bash
zt list
zt to claude_tester_Gina "hello"
```

## ACK / DONE / REPLY 协议（文件队列）

zellij-talk 1.2.0 引入了基于文件队列的轻量确认协议，**完全绕开终端 stdin**，避免 ACK 字符乱入发送方面板。

协议核心：共享文件 `~/.config/zellij/talk/replies.jsonl`

### 发送方

```bash
zt to claude_tester_Gina "请 review 这段代码" --wait-done --done-timeout 120
```

发送后，`zt` 会自动监听 `replies.jsonl`，等待对应的 `msg_id` 被标记为 DONE。

### 接收方

收到带 `[MSG_ID:xxx]` 的消息后，**无需调用 `zt to` 回复**。只需在当前面板运行：

```bash
echo '{"type":"DONE","msg_id":"xxx","from":"claude_tester_Gina"}' >> ~/.config/zellij/talk/replies.jsonl
```

或者输出包含 `msg_id` 的自然语言，发送方的 `--wait-ack` 同样可以捕获到。

> **关键**：接收方不要调用 `zt to 发送方 "[ACK:xxx]"`，这会往发送方终端打字符，造成乱入。正确做法是直接写 `replies.jsonl` 或在当前面板自然输出。

## Pipeline 编排

用 YAML 定义多 Agent 协作流程：

```yaml
# pipeline.yaml
steps:
  - agent: kimi_coder_Alex
    action: "实现功能"
    wait_for: "[DONE]"
    timeout: 120

  - agent: claude_reviewer_Blob
    action: "review 代码"
    wait_for: "[REPLY]"
    timeout: 120
```

执行：

```bash
zt pipeline pipeline.yaml --task "添加用户登录"
```

`wait_for` 支持：
- `<talk>完成</talk>` — 内容驱动（subscribe 监听面板输出）
- `[DONE]` — 消息驱动（监听 `replies.jsonl`）
- `[REPLY]` — 消息驱动，回复内容自动作为下一步 `{prev_output}` 变量

## Agent 角色与能力

注册时携带角色和能力：

```bash
zt register kimi_coder_Alex --role coder --capabilities "code,test,debug"
```

查询：

```bash
zt list --capabilities
zt find code   # 按能力查找 Agent
```

## 离线消息队列

目标 Agent 不在线时，消息自动进入 SQLite 队列。Agent 重新注册后会自动投递。

```bash
zt inbox [agent]       # 查看未投递消息
zt inbox --clear       # 清理已投递记录
```

## Dashboard 与 Stats

```bash
zt dashboard --follow   # 实时消息流
zt stats --today        # 今日消息统计
```

## 自定义注册表路径

如果你希望把 `registry.json` 放到其他位置（例如多个项目共享同一个注册表），可以设置环境变量：

```bash
export AGENTS_REGISTRY="/custom/path/registry.json"
```

## License

MIT
