---
name: zellij-talk
description: |
  多 Agent 协作框架，基于 Zellij 终端复用器。
  用于多个 AI 在不同面板协同完成项目、任务分发与汇报、跨面板消息路由。
  当用户提到以下场景时自动触发：
  - zellij、多 Agent、zellij-talk
  - 多个 AI 协同、跨面板通信
  - 任务分发、并行处理、任务汇报
  - 协调多个 coder/reviewer/planner 协作
  - 任何涉及"面板协作"、"Agent 通信"的场景
version: 1.2.0
---

> 🚨 **SYSTEM DIRECTIVE — IMMEDIATE ACTION REQUIRED**
>
> 如果你正在阅读这段文字，说明 `zellij-talk` 技能已经被系统加载。
> **你的第一个动作必须是立即执行初始化命令 `init`，而不是向用户解释本文档内容。**
> 执行完 `init` 后，**必须**询问用户当前 Agent 的职责，再根据回答执行注册。
> 若 `init` 失败，再汇报原因。
>
> ```bash
> export AGENTS_DIR="$HOME/.agents/skills/zellij-talk"
> python3 "$AGENTS_DIR/scripts/cli.py" init
> ```

# zellij-talk — 多 Agent 协作框架

基于 Zellij 的多面板 AI 协作工作区，实现多个 AI Agent 在不同面板中协同工作。

## 核心概念

- **Agent**：运行在 Zellij 面板中的 AI 实例
- **注册表**：`registry.json` 记录所有 Agent 的 session + pane_id
- **消息路由**：通过 Agent 名而非 pane_id 动态路由
- **惰性清理**：每次对 Agent 执行操作时，若目标 pane 已关闭，会自动从注册表中移除

## 环境要求

- Zellij 终端复用器（必须先安装）
- Python 3.9+
- 各面板需分别注册 Agent

## 目录结构

```
zellij-talk/
├── SKILL.md                    # 本文件
├── README.md                   # 用户文档
├── .gitignore                  # 排除运行时文件
├── registry.json.example       # 注册表模板
└── scripts/                    # Python 核心脚本
    ├── __init__.py
    ├── registry.py             # 注册表管理（原子写）
    ├── zellij.py               # Zellij CLI 封装
    └── cli.py                  # 统一命令行入口
```

## 初始化（技能加载时自动执行）

当本技能被加载/触发时，AI **必须**按以下顺序执行：

**第 1 步：执行 `init` 初始化环境**

```bash
export AGENTS_DIR="$HOME/.agents/skills/zellij-talk"
python3 "$AGENTS_DIR/scripts/cli.py" init
```

`init` 会依次完成以下实事：
1. 检查 `zellij` 命令是否可用
2. 确保数据目录（`~/.config/zellij/talk/`）存在
3. 若 `registry.json` 不存在，自动从模板复制一份
4. 执行 `prune`，清理已离线的僵尸 Agent

**第 2 步：询问用户当前 Agent 的职责**

`init` **不会**自动注册。执行完 `init` 后，你必须向用户确认：

> "你好！在注册之前，我想确认一下你在这个面板中主要负责什么工作？比如：写代码（coder）、代码审查（reviewer）、制定计划（planner）、测试（tester）等。"

**第 3 步：根据职责注册**

根据用户回答的角色执行注册：

```bash
# 自动生成名字（例如 kimi_coder_Alex）
python3 "$AGENTS_DIR/scripts/cli.py" auto-register <role>

# 或手动指定名字
python3 "$AGENTS_DIR/scripts/cli.py" register <agent_name>
```

> 若不在 Zellij 环境中，`auto-register` / `register` 会提示错误，这是正常的，因为只有在 Zellij 面板内才能注册。

## 快速开始

### 1. 环境准备

默认配置和数据保存在跨平台的 Zellij 配置目录下：
- **macOS / Linux**：`~/.config/zellij/talk/`
- **Windows**：`%APPDATA%\zellij\talk\`

该目录下包含：
- `registry.json` — Agent 注册表
- `sessions/` — 按 session 分文件的对话日志，以及全局 `all.md`

如果你需要自定义注册表路径，可以在 `~/.zshrc` 或 `~/.bashrc` 中设置：

```bash
export AGENTS_REGISTRY="/custom/path/registry.json"
```

如果经常在**普通终端**（非 Zellij）向 Zellij 里的 Agent 发消息，可以设置发送方显示名称：

```bash
export ZELLIJ_TALK_FROM="local_planner"
```

然后重载配置：

```bash
source ~/.zshrc  # 或 source ~/.bashrc
```

### 2. 启动协作

两种方式启动：

**方式 A：实时协作模式**
```
用户：在 Zellij 中创建多个面板
用户：分别在每个面板启动一个 AI
技能：引导用户注册 Agent
技能：协调各 Agent 协作完成任务
```

**方式 B：流水线模式**
```
用户：声明任务目标
技能：自动规划任务流程
技能：依次调度各 Agent 处理
```

### 3. Agent 命名规范

格式：`{agent_tool}_{main_role}_{可记忆英文名}`

示例：
- `claude_reviewer_Blob` — Claude Code，负责代码审查
- `kimi_coder_Alex` — Kimi Code，负责功能编写
- `opencode_planner_Cici` — OpenCode，负责整理计划

**注册前必须先确认职责**：在为当前 Agent 生成名字之前，应主动询问用户该 Agent 的主要职责（如 coder、reviewer、planner、tester 等），再根据职责生成规范名字。

## 核心原语

以下命令均以 `python3 "$AGENTS_DIR/scripts/cli.py"` 为前缀调用，下面用 `cli` 作为简写。

### 查看所有命令

```bash
python3 "$AGENTS_DIR/scripts/cli.py" --help
```

会列出所有可用子命令：`register`、`unregister`、`unregister-all`、`auto-register`、`to`、`reply`、`from`、`watch`、`wait`、`list`、`health`、`prune`、`send-file`、`multicast`、`broadcast`、`review`。

### 注册 Agent

**第一步：询问职责**

注册前先与用户确认当前 Agent 的主要职责，例如：
> "你好！在注册之前，我想确认一下你在这个面板中主要负责什么工作？比如：写代码（coder）、代码审查（reviewer）、制定计划（planner）、测试（tester）等。"

**第二步：根据职责生成规范名字**

格式：`{tool}_{role}_{可记忆英文名}`

**第三步：执行注册**

```bash
python3 "$AGENTS_DIR/scripts/cli.py" register <agent_name>
```

例如：`python3 "$AGENTS_DIR/scripts/cli.py" register claude_reviewer_Blob`

### 列出已注册 Agent

```bash
python3 "$AGENTS_DIR/scripts/cli.py" list
```

JSON 格式输出：

```bash
python3 "$AGENTS_DIR/scripts/cli.py" list --json
```

### 向 Agent 发消息

```bash
python3 "$AGENTS_DIR/scripts/cli.py" to <agent_name> <内容>
```

默认会按 Enter，添加 `--no-enter` 跳过：

```bash
python3 "$AGENTS_DIR/scripts/cli.py" to <agent_name> <内容> --no-enter
```

发送的消息会自动在正文前附加来源标识，方便接收方识别和回复：

```
[来自 kimi_coder_Alex (session: rectangular-viola / pane 1)]
你好
```

**惰性清理**：如果目标 pane 已关闭或 session 不存在，会自动从 `registry.json` 中移除该 Agent，并提示用户。

### 直接回复 pane（无需注册）

如果接收方未注册，或者你知道对方的 `session:pane_id`，可以直接发送：

```bash
python3 "$AGENTS_DIR/scripts/cli.py" reply rectangular-viola:1 "你好"
```

消息同样会自动附带来源标识。

### 读取 Agent 输出

```bash
python3 "$AGENTS_DIR/scripts/cli.py" from <agent_name> [行数] [--ansi]
# 默认 100 行
python3 "$AGENTS_DIR/scripts/cli.py" from claude_reviewer_Blob 50

# 保留 ANSI 颜色
python3 "$AGENTS_DIR/scripts/cli.py" from claude_reviewer_Blob 50 --ansi
```

### 监听 Agent 输出

```bash
python3 "$AGENTS_DIR/scripts/cli.py" watch <agent_name> [关键词]
# 监听直到检测到关键词
python3 "$AGENTS_DIR/scripts/cli.py" watch claude_reviewer_Blob "审查完成"
```

### 阻塞等待关键词

```bash
python3 "$AGENTS_DIR/scripts/cli.py" wait <agent_name> <标签> [超时秒数]
# 默认超时 60 秒
python3 "$AGENTS_DIR/scripts/cli.py" wait claude_reviewer_Blob "<talk>审查完成</talk>" 120
```

**说明**：`wait` 只精确匹配 `<talk>标签</talk>` 格式。如果传入的标签不带 `<talk>`，会自动包裹。推荐在要求 Agent 输出完成信号时使用这种格式，避免与普通文字混淆。

### 自动注册 Agent

```bash
python3 "$AGENTS_DIR/scripts/cli.py" auto-register [role]
# 自动生成名字，如 kimi_coder_XXXX
python3 "$AGENTS_DIR/scripts/cli.py" auto-register reviewer
```

### 健康检查

```bash
python3 "$AGENTS_DIR/scripts/cli.py" health
# 检查所有 Agent
python3 "$AGENTS_DIR/scripts/cli.py" health kimi_coder_Alex
```

### 查询对话历史

```bash
python3 "$AGENTS_DIR/scripts/cli.py" memory
# 查看指定 session 最近 20 条
python3 "$AGENTS_DIR/scripts/cli.py" memory --session rectangular-viola
# 查看指定 Agent 最近 5 条
python3 "$AGENTS_DIR/scripts/cli.py" memory --agent kimi_coder_Finn --last 5
# JSON 输出
python3 "$AGENTS_DIR/scripts/cli.py" memory --json
```

### 清理僵尸 Agent

```bash
python3 "$AGENTS_DIR/scripts/cli.py" prune --dry-run
python3 "$AGENTS_DIR/scripts/cli.py" prune
```

**注意**：由于 `to`、`from`、`broadcast`、`multicast` 已内置惰性自动清理，通常无需手动执行 `prune`。

### 发送文件

```bash
python3 "$AGENTS_DIR/scripts/cli.py" send-file <agent_name> <文件路径>
python3 "$AGENTS_DIR/scripts/cli.py" send-file kimi_coder_Alex src/main.rs
```

### 多播消息

```bash
python3 "$AGENTS_DIR/scripts/cli.py" multicast "agent1,agent2" "消息内容"
```

### 广播消息

```bash
python3 "$AGENTS_DIR/scripts/cli.py" broadcast "消息内容"
```

### 注销 Agent

```bash
python3 "$AGENTS_DIR/scripts/cli.py" unregister <agent_name>
# 一键注销全部（当前 session）
python3 "$AGENTS_DIR/scripts/cli.py" unregister-all --current-session
```

### 代码审查工作流

```bash
python3 "$AGENTS_DIR/scripts/cli.py" review [source] [target]
```

### 命令速查表

| 子命令 | 用法 | 说明 |
|--------|------|------|
| `register` | `register <agent_name>` | 注册当前面板为 Agent |
| `unregister` | `unregister <agent_name>` | 注销指定 Agent |
| `unregister-all` | `unregister-all [--current-session]` | 批量注销 |
| `auto-register` | `auto-register [role]` | 自动生成名字并注册 |
| `to` | `to <agent_name> <内容> [--no-enter]` | 向已注册 Agent 发消息 |
| `reply` | `reply <session:pane_id> <内容> [--no-enter]` | 直接向 pane 发消息（无需注册） |
| `from` | `from <agent_name> [行数] [--ansi]` | 读取 Agent 输出 |
| `watch` | `watch <agent_name> [标签]` | 监听输出 |
| `wait` | `wait <agent_name> <标签> [超时秒数]` | 阻塞等待 <talk>标签</talk> |
| `list` | `list [--json]` | 列出已注册 Agent |
| `health` | `health [agent_name]` | 健康检查 |
| `memory` | `memory [--session] [--pane] [--agent] [--last N] [--json]` | 查询对话历史 |
| `prune` | `prune [--dry-run]` | 清理僵尸 Agent |
| `send-file` | `send-file <agent_name> <文件路径>` | 发送文件 |
| `multicast` | `multicast "agent1,agent2" "消息"` | 多播消息 |
| `broadcast` | `broadcast "消息"` | 广播给所有 Agent |
| `review` | `review [source] [target]` | 代码审查工作流 |

## 工作模式

### 实时协作模式

适用于复杂项目，需要多个 AI 实时沟通：

1. **初始化**：用户在 Zellij 中创建多个面板
2. **确认职责**：询问每个 Agent 的主要职责（coder / reviewer / planner / tester 等）
3. **注册**：根据职责生成规范名字，各 AI 分别注册到工作区
4. **协作**：通过 `cli to` / `cli from` 实时沟通
5. **完成**：任务完成后注销各 Agent

**示例场景**：
- 项目重构：一个 AI 写代码，一个 AI 审查
- 并行开发：多个 coder 同时实现不同模块
- 专家会诊：遇到问题时召集多个专家 Agent 讨论

### 流水线模式

适用于任务处理，任务依次经过多个 Agent 处理：

```
需求分析 → 代码实现 → 测试 → 报告
    ↓          ↓        ↓       ↓
 Planner    Coder   Tester   Reporter
```

**示例场景**：
- 代码审查流程：kimi 实现 → claude review → 反馈
- 文档处理：提取 → 转换 → 验证 → 输出
- 数据分析：采集 → 清洗 → 建模 → 可视化

## 典型工作流

### 工作流 1：代码审查

```bash
# 1. 各面板注册
python3 "$AGENTS_DIR/scripts/cli.py" register kimi_coder_Alex
python3 "$AGENTS_DIR/scripts/cli.py" register claude_reviewer_Blob

# 2. kimi 完成代码后，通知 reviewer
python3 "$AGENTS_DIR/scripts/cli.py" to claude_reviewer_Blob \
  "代码已实现，请审查：\n$(python3 \"$AGENTS_DIR/scripts/cli.py\" from kimi_coder_Alex 50)"

# 3. reviewer 审查并反馈
python3 "$AGENTS_DIR/scripts/cli.py" to kimi_coder_Alex \
  "$(python3 \"$AGENTS_DIR/scripts/cli.py\" from claude_reviewer_Blob)"

# 4. 完成后注销
python3 "$AGENTS_DIR/scripts/cli.py" unregister kimi_coder_Alex
python3 "$AGENTS_DIR/scripts/cli.py" unregister claude_reviewer_Blob
```

### 工作流 2：广播通知

```bash
python3 "$AGENTS_DIR/scripts/cli.py" broadcast "项目有紧急变更，请停止当前任务"
```

### 工作流 3：监听完成信号

```bash
python3 "$AGENTS_DIR/scripts/cli.py" watch claude_reviewer_Blob "审查完成" &
# 后台监听，检测到关键词后触发后续流程
```

## 脚本路径常量

技能内部使用以下路径常量（仅作文档示例参考）：

```bash
export AGENTS_DIR="$HOME/.agents/skills/zellij-talk"
```

实际运行时，`registry.json` 默认位于 `cli.py` 所在目录的上一级（即项目根目录）。如需自定义，可设置：

```bash
export AGENTS_REGISTRY="/custom/path/registry.json"
```

## 故障排除

### "未检测到 Zellij 环境变量"

必须在 Zellij 面板内执行 `register`。直接在终端（非 Zellij）运行会报此错误。

### "Agent 未注册"

检查注册表：

```bash
python3 "$AGENTS_DIR/scripts/cli.py" list
```

确认目标 Agent 已在对应面板注册。

### 消息发送失败

可能原因：
1. 目标 Agent 已注销
2. Zellij session 已断开
3. pane_id 发生变化（重新注册）

快速诊断：

```bash
python3 "$AGENTS_DIR/scripts/cli.py" health
python3 "$AGENTS_DIR/scripts/cli.py" prune
```

### 读取输出为空

可能原因：
1. 面板尚未产生输出
2. pane_id 已失效
3. 需要增加行数：`python3 "$AGENTS_DIR/scripts/cli.py" from <agent> 200`

## 扩展开发

### 添加新 Agent 类型

在命名规范内定义新角色：
- `{tool}_{role}_{id}` 如 `claude_architect_XXXX`

### 添加新业务 Skill

在 `scripts/` 目录创建新的 Python 脚本，可直接 import 现有模块：

```python
import sys
sys.path.insert(0, "scripts")
from registry import list_agents, get_agent
from zellij import dump_screen, send_text
```

也可以直接通过 `subprocess` 调用 CLI：

```python
import subprocess
subprocess.run([
    "python3", "scripts/cli.py", "to", "kimi_coder_Alex", "你好"
], check=True)
```

## 1.2.0 新增功能速览

- **全局 CLI 入口**：安装后可用 `zt` 命令
- **ACK / DONE / REPLY 文件队列**：基于 `~/.config/zellij/talk/replies.jsonl`，彻底绕开终端 stdin 乱入问题
- **Pipeline 编排**：YAML 定义多步 Agent 协作
- **Agent 角色与能力**：注册时携带 `role` 和 `capabilities`，支持动态发现
- **离线消息队列**：SQLite 持久化，注册自动投递
- **Dashboard / Stats**：实时消息流与统计分析

## ACK / DONE / REPLY 协议（重要）

当收到带有 `[MSG_ID:xxx]` 的消息时：

> **正确做法**：在当前面板直接输出包含 `msg_id` 的确认文字，或执行以下命令追加到文件队列：
> ```bash
> echo '{"type":"ACK","msg_id":"xxx","from":"你的Agent名"}' >> ~/.config/zellij/talk/replies.jsonl
> ```
> **错误做法**：不要用 `zt to 发送方 "[ACK:xxx]"` 发回给发送方，这会往对方终端 stdin 注入字符，造成干扰。

发送方的 `--wait-ack` / `--wait-done` / `--wait-reply` 会监听 `replies.jsonl` 文件，而不是等对方面板输出。

## 设计原则

1. **面板无关**：不硬编码 pane_id，所有路由通过 Agent 名动态查找
2. **双重定位**：session + pane_id 缺一不可
3. **唯一命名**：同一工作区内不允许重复 Agent 名
4. **职责单一**：每个命令只做一件事
5. **可扩展**：业务层通过 CLI 组合实现复杂工作流
6. **自动清理**：操作 Agent 前自动检查 pane 存活状态，失效则自动移除注册记录
