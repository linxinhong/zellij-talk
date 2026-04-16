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
version: 1.0.0
---

# zellij-talk — 多 Agent 协作框架

基于 Zellij 的多面板 AI 协作工作区，实现多个 AI Agent 在不同面板中协同工作。

## 核心概念

- **Agent**：运行在 Zellij 面板中的 AI 实例
- **注册表**：`registry.json` 记录所有 Agent 的 session + pane_id
- **消息路由**：通过 Agent 名而非 pane_id 动态路由

## 环境要求

- Zellij 终端复用器（必须先安装）
- jq（JSON 处理）
- 各面板需分别注册 Agent

## 目录结构

```
zellij-talk/
├── SKILL.md                    # 本文件
├── scripts/                    # 核心原语
│   ├── register.sh            # 注册当前面板为 Agent
│   ├── unregister.sh          # 注销 Agent
│   ├── auto-register.sh       # 自动生成名字并注册
│   ├── to.sh                  # 向 Agent 发消息（支持管道）
│   ├── from.sh                # 读取 Agent 输出
│   ├── watch.sh               # 监听 Agent 输出
│   ├── wait.sh                # 阻塞等待关键词
│   ├── list.sh                # 列出已注册 Agent
│   ├── health.sh              # Agent 健康检查
│   ├── prune.sh               # 清理僵尸 Agent
│   ├── send-file.sh           # 发送文件给 Agent
│   └── multicast.sh           # 多播消息
```

## 快速开始

### 1. 环境准备

在 `~/.zshrc` 或 `~/.bashrc` 中添加：

```bash
export AGENTS_DIR="$HOME/.agents/skills/zellij-talk"
export AGENTS_REGISTRY="$AGENTS_DIR/registry.json"
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

### 注册 Agent

**第一步：询问职责**

注册前先与用户确认当前 Agent 的主要职责，例如：
> "你好！在注册之前，我想确认一下你在这个面板中主要负责什么工作？比如：写代码（coder）、代码审查（reviewer）、制定计划（planner）、测试（tester）等。"

**第二步：根据职责生成规范名字**

格式：`{tool}_{role}_{可记忆英文名}`

**第三步：执行注册**

```bash
~/.agents/skills/zellij-talk/scripts/register.sh <agent_name>
```

例如：`~/.agents/skills/zellij-talk/scripts/register.sh claude_reviewer_Blob`

### 列出已注册 Agent

```bash
~/.agents/skills/zellij-talk/scripts/list.sh
```

### 向 Agent 发消息

```bash
~/.agents/skills/zellij-talk/scripts/to.sh <agent_name> <内容>
```

默认会按 Enter，添加 `--no-enter` 跳过：

```bash
~/.agents/skills/zellij-talk/scripts/to.sh <agent_name> <内容> --no-enter
```

### 读取 Agent 输出

```bash
~/.agents/skills/zellij-talk/scripts/from.sh <agent_name> [行数] [--ansi]
# 默认 100 行
~/.agents/skills/zellij-talk/scripts/from.sh claude_reviewer_Blob 50

# 保留 ANSI 颜色
~/.agents/skills/zellij-talk/scripts/from.sh claude_reviewer_Blob 50 --ansi
```

### 监听 Agent 输出

```bash
~/.agents/skills/zellij-talk/scripts/watch.sh <agent_name> [关键词]
# 监听直到检测到关键词
~/.agents/skills/zellij-talk/scripts/watch.sh claude_reviewer_Blob "审查完成"
```

### 阻塞等待关键词

```bash
~/.agents/skills/zellij-talk/scripts/wait.sh <agent_name> <关键词> [超时秒数]
# 默认超时 60 秒
~/.agents/skills/zellij-talk/scripts/wait.sh claude_reviewer_Blob "审查完成" 120
```

### 自动注册 Agent

```bash
~/.agents/skills/zellij-talk/scripts/auto-register.sh [role]
# 自动生成名字，如 kimi_coder_XXXX
~/.agents/skills/zellij-talk/scripts/auto-register.sh reviewer
```

### 健康检查

```bash
~/.agents/skills/zellij-talk/scripts/health.sh
# 检查所有 Agent
~/.agents/skills/zellij-talk/scripts/health.sh kimi_coder_Alex
```

### 清理僵尸 Agent

```bash
~/.agents/skills/zellij-talk/scripts/prune.sh --dry-run
~/.agents/skills/zellij-talk/scripts/prune.sh
```

### 发送文件

```bash
~/.agents/skills/zellij-talk/scripts/send-file.sh <agent_name> <文件路径>
~/.agents/skills/zellij-talk/scripts/send-file.sh kimi_coder_Alex src/main.rs
```

### 多播消息

```bash
~/.agents/skills/zellij-talk/scripts/multicast.sh "agent1,agent2" "消息内容"
```

### 注销 Agent

```bash
~/.agents/skills/zellij-talk/scripts/unregister.sh <agent_name>
# 一键注销全部（当前 session）
~/.agents/skills/zellij-talk/scripts/unregister-all.sh --current-session
```

## 工作模式

### 实时协作模式

适用于复杂项目，需要多个 AI 实时沟通：

1. **初始化**：用户在 Zellij 中创建多个面板
2. **确认职责**：询问每个 Agent 的主要职责（coder / reviewer / planner / tester 等）
3. **注册**：根据职责生成规范名字，各 AI 分别注册到工作区
4. **协作**：通过 `to.sh` / `from.sh` 实时沟通
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
~/.agents/skills/zellij-talk/scripts/register.sh kimi_coder_Alex
~/.agents/skills/zellij-talk/scripts/register.sh claude_reviewer_Blob

# 2. kimi 完成代码后，通知 reviewer
~/.agents/skills/zellij-talk/scripts/to.sh claude_reviewer_Blob \
  "代码已实现，请审查：\n$(~/.agents/skills/zellij-talk/scripts/from.sh kimi_coder_Alex 50)"

# 3. reviewer 审查并反馈
~/.agents/skills/zellij-talk/scripts/to.sh kimi_coder_Alex \
  "$(~/.agents/skills/zellij-talk/scripts/from.sh claude_reviewer_Blob)"

# 4. 完成后注销
~/.agents/skills/zellij-talk/scripts/unregister.sh kimi_coder_Alex
~/.agents/skills/zellij-talk/scripts/unregister.sh claude_reviewer_Blob
```

### 工作流 2：广播通知

```bash
~/.agents/skills/zellij-talk/scripts/broadcast.sh "项目有紧急变更，请停止当前任务"
```

### 工作流 3：监听完成信号

```bash
~/.agents/skills/zellij-talk/scripts/watch.sh claude_reviewer_Blob "审查完成" &
# 后台监听，检测到关键词后触发后续流程
```

## 脚本路径常量

技能内部使用以下路径常量：

```bash
export AGENTS_DIR="$HOME/.agents/skills/zellij-talk"
export SCRIPTS="$AGENTS_DIR/scripts"
export REGISTRY="$AGENTS_DIR/registry.json"
```

## 故障排除

### "未检测到 Zellij 环境变量"

必须在 Zellij 面板内执行 `register.sh`。直接在终端（非 Zellij）运行会报此错误。

### "Agent 未注册"

检查注册表：
```bash
~/.agents/skills/zellij-talk/scripts/list.sh
```

确认目标 Agent 已在对应面板注册。

### 消息发送失败

可能原因：
1. 目标 Agent 已注销
2. Zellij session 已断开
3. pane_id 发生变化（重新注册）

快速诊断：
```bash
~/.agents/skills/zellij-talk/scripts/health.sh
~/.agents/skills/zellij-talk/scripts/prune.sh
```

### 读取输出为空

可能原因：
1. 面板尚未产生输出
2. pane_id 已失效
3. 需要增加行数：`from.sh <agent> 200`

## 扩展开发

### 添加新 Agent 类型

在命名规范内定义新角色：
- `{tool}_{role}_{id}` 如 `claude_architect_XXXX`

### 添加新业务 Skill

在 `scripts/` 目录创建新脚本：

```bash
#!/bin/bash
set -euo pipefail
SCRIPTS="$HOME/.agents/skills/zellij-talk/scripts"

# 读取源 Agent 输出
CONTENT=$("$SCRIPTS/from.sh" "source_agent" 100)

# 处理并转发
"$SCRIPTS/to.sh" "target_agent" "处理后的内容：$CONTENT"
```

## 设计原则

1. **面板无关**：不硬编码 pane_id，所有路由通过 Agent 名动态查找
2. **双重定位**：session + pane_id 缺一不可
3. **唯一命名**：同一工作区内不允许重复 Agent 名
4. **职责单一**：每个脚本只做一件事
5. **可扩展**：业务层通过 scripts 组合实现复杂工作流
