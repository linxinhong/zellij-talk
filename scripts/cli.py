"""CLI entry point for zellij-talk."""

import argparse
import random
import subprocess
import sys
import time
from typing import Any

__version__ = "1.1.0"

from registry import get_agent, list_agents, load_registry, register_agent, save_registry, unregister_agent
from zellij import dump_screen, get_current_pane_id, get_current_session, has_zellij_env, is_pane_alive, rename_pane, send_text
import logger
import memory


def _build_sender_prefix() -> str:
    sender = logger.get_sender_info()
    name = sender["name"]
    session = sender.get("session")
    pane_id = sender.get("pane_id")
    if sender["source"] == "external":
        return f"[来自 {name}]"
    if session and pane_id:
        return f"[来自 {name} (session: {session} / pane {pane_id})]"
    return f"[来自 {name}]"


def _obfuscate_talk_tags(text: str) -> str:
    """Replace <talk> and </talk> with Unicode escapes so wait doesn't match
    the instruction itself before the agent outputs the tag.
    """
    return text.replace("<talk>", "\\u003ctalk\\u003e").replace("</talk>", "\\u003c/talk\\u003e")


def _add_talk_hint(text: str) -> str:
    """If the text contains obfuscated talk tags, prepend a hint asking the agent
    to output them wrapped in backticks so the tags are preserved.
    """
    if "\\u003ctalk\\u003e" in text and "\\u003c/talk\\u003e" in text:
        hint = "注：消息中的 \\u003ctalk\\u003e...\\u003c/talk\\u003e 请用反引号包裹后原样输出，例如：\\n`<talk>完成</talk>`\\n\n"
        return hint + text
    return text


def _match_keyword(text: str, keyword: str) -> str | None:
    """Match only exact <talk>keyword</talk> tags. If keyword is not wrapped, wrap it automatically."""
    raw = keyword.strip()
    if raw.startswith("<talk>") and raw.endswith("</talk>"):
        tag = raw
    else:
        tag = f"<talk>{raw}</talk>"
    if tag in text:
        return tag
    return None


def _err(msg: str) -> None:
    print(f"❌ {msg}", file=sys.stderr)


def _warn(msg: str) -> None:
    print(f"⚠️  {msg}", file=sys.stderr)


def _info(msg: str) -> None:
    print(msg)


def _resolve_agent(name: str, auto_prune: bool = True) -> dict[str, Any] | None:
    meta = get_agent(name)
    if meta is None:
        return None
    if auto_prune:
        pane_id = meta.get("pane_id", "")
        session = meta.get("session", "")
        if not is_pane_alive(session, pane_id):
            unregister_agent(name)
            _warn(f'[{name}] 的 pane 已关闭或 session 不存在，已自动注销')
            return None
    return meta


def cmd_register(args: argparse.Namespace) -> int:
    name = args.name
    if not has_zellij_env():
        _err("未检测到 Zellij 环境变量，请在 Zellij 面板内执行此命令")
        return 1
    pane_id = get_current_pane_id()
    session = get_current_session()
    assert pane_id and session

    data = load_registry()
    old = None
    for k, v in data.items():
        if v.get("session") == session and v.get("pane_id") == pane_id and k != name:
            old = k
            break
    if old:
        _warn(f"[{old}] 占用了同一 pane，将自动注销旧记录")
        unregister_agent(old)
    if name in data:
        _warn(f"[{name}] 已注册，将覆盖旧记录")

    register_agent(name, session, pane_id)
    rename_pane(pane_id, name)
    _info(f"✅ [{name}] 注册成功")
    _info(f"   pane_id : {pane_id}")
    _info(f"   session : {session}")
    _info(f"   pane_name : {name}")
    return 0


def cmd_unregister(args: argparse.Namespace) -> int:
    name = args.name
    if unregister_agent(name):
        _info(f"🗑️  [{name}] 已注销")
    else:
        _warn(f"[{name}] 未注册，跳过")
    return 0


def cmd_unregister_all(args: argparse.Namespace) -> int:
    data = list_agents()
    current_session = get_current_session()
    removed = 0
    for name in list(data.keys()):
        if args.current_session:
            if data[name].get("session") != current_session:
                continue
        if unregister_agent(name):
            removed += 1
            _info(f"🗑️  [{name}] 已注销")
    if removed == 0:
        _info("（没有可注销的 Agent）")
    else:
        _info(f"✅ 共注销 {removed} 个 Agent")
    return 0


def _get_ppid_info() -> str:
    import os
    ppid = os.getppid()
    # macOS / Linux fallback without psutil
    try:
        path = f"/proc/{ppid}/cmdline"
        if os.path.exists(path):
            with open(path, "rb") as f:
                data = f.read().replace(b"\x00", b" ")
                return data.decode("utf-8", errors="ignore")
    except Exception:
        pass
    try:
        result = subprocess.run(
            ["ps", "-p", str(ppid), "-o", "comm=,args="],
            capture_output=True,
            text=True,
        )
        return result.stdout
    except Exception:
        return ""


def cmd_auto_register(args: argparse.Namespace) -> int:
    role = args.role or "coder"

    tool = "agent"
    combined = _get_ppid_info().lower()
    if "kimi" in combined:
        tool = "kimi"
    elif "claude" in combined:
        tool = "claude"
    elif "opencode" in combined:
        tool = "opencode"

    names = [
        "Alex", "Blob", "Cici", "David", "Ella", "Finn", "Gina", "Hugo",
        "Iris", "Jake", "Kiki", "Liam", "Mila", "Nico", "Olga", "Pete",
        "Quin", "Rita", "Sam", "Tina", "Umar", "Vera", "Walt", "Xena",
        "York", "Zara",
    ]
    data = load_registry()
    start = random.randint(0, len(names) - 1)
    chosen = None
    for i in range(len(names)):
        candidate = f"{tool}_{role}_{names[(start + i) % len(names)]}"
        if candidate not in data:
            chosen = candidate
            break
    if not chosen:
        _err("名字池已用完，请手动指定名字")
        return 1

    # delegate to register
    class FakeArgs:
        name = chosen
    ret = cmd_register(FakeArgs())
    if ret == 0:
        _info("")
        _info(f"💡 提示：你可以在其他面板通过以下方式与我通信")
        _info(f'   python3 scripts/cli.py to {chosen} "你好"')
    return ret


def cmd_to(args: argparse.Namespace) -> int:
    name = args.agent
    content = args.content or ""
    if not content and not sys.stdin.isatty():
        content = sys.stdin.read()
    content = content.strip()
    if not content:
        _err("内容不能为空")
        return 1
    meta = _resolve_agent(name)
    if meta is None:
        _err(f"[{name}] 未注册，请先在对应面板执行 register")
        return 1
    prefix = _build_sender_prefix()
    content = _obfuscate_talk_tags(content)
    content = _add_talk_hint(content)
    full_content = f"{prefix}\n{content}"
    send_text(meta["session"], meta["pane_id"], full_content, no_enter=args.no_enter)
    logger.log_message([(name, meta)], content, message_type="direct")
    _info(f"📨 [{name} @ {meta['pane_id']} / {meta['session']}] ← 已发送")
    return 0


def cmd_reply(args: argparse.Namespace) -> int:
    """Send a message directly to a session:pane, even if unregistered."""
    target = args.target
    content = args.content or ""
    if not content and not sys.stdin.isatty():
        content = sys.stdin.read()
    content = content.strip()
    if not content:
        _err("内容不能为空")
        return 1

    if ":" not in target:
        _err("目标格式错误，应为 session:pane_id，例如 rectangular-viola:0")
        return 1

    session, pane_id = target.split(":", 1)
    if not session or not pane_id:
        _err("目标格式错误，应为 session:pane_id")
        return 1

    prefix = _build_sender_prefix()
    content = _obfuscate_talk_tags(content)
    content = _add_talk_hint(content)
    full_content = f"{prefix}\n{content}"
    send_text(session, pane_id, full_content, no_enter=args.no_enter)
    logger.log_message([(target, {"session": session, "pane_id": pane_id})], content, message_type="direct")
    _info(f"📨 [{pane_id} / {session}] ← 已直接发送")
    return 0


def cmd_from(args: argparse.Namespace) -> int:
    name = args.agent
    meta = _resolve_agent(name)
    if meta is None:
        _err(f"[{name}] 未注册")
        return 1
    text = dump_screen(meta["session"], meta["pane_id"], ansi=args.ansi)
    lines = text.splitlines()
    output = "\n".join(lines[-args.lines:])
    print(output)
    return 0


def cmd_watch(args: argparse.Namespace) -> int:
    name = args.agent
    keyword = args.keyword or ""
    meta = _resolve_agent(name)
    if meta is None:
        _err(f"[{name}] 未注册")
        return 1
    _info(f"👀 监听 [{name} @ {meta['pane_id']} / {meta['session']}] ...")
    _info(f"   标签: {keyword or '（不过滤）'}")

    import subprocess

    proc = subprocess.Popen(
        ["zellij", "--session", meta["session"], "subscribe", "--pane-id", meta["pane_id"], "--format", "json"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    try:
        import json
        for line in proc.stdout or []:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                viewport = obj.get("viewport")
                if not viewport:
                    continue
                text = "\n".join(viewport)
                if not keyword:
                    print(text)
                else:
                    matched = _match_keyword(text, keyword)
                    if matched:
                        _info(f"🎯 [{name}] 检测到标签: {matched}")
                        print(text)
            except json.JSONDecodeError:
                continue
    except KeyboardInterrupt:
        pass
    finally:
        proc.terminate()
    return 0


def cmd_wait(args: argparse.Namespace) -> int:
    name = args.agent
    keyword = args.keyword
    timeout = args.timeout
    interval = 2
    lines = 100
    _info(f"⏳ 等待 [{name}] 输出中出现标签: '{keyword}' (超时 {timeout}s)")
    sys.stdout.flush()

    meta = _resolve_agent(name, auto_prune=False)
    if meta is None:
        _err(f"[{name}] 未注册")
        return 1

    elapsed = 0
    while elapsed < timeout:
        text = dump_screen(meta["session"], meta["pane_id"], ansi=False)
        output_lines = text.splitlines()
        output = "\n".join(output_lines[-lines:])
        matched = _match_keyword(output, keyword)
        if matched:
            _info(f"🎯 检测到标签: {matched}")
            for line in output_lines:
                if matched in line:
                    print(line)
            return 0
        time.sleep(interval)
        elapsed += interval
    _err(f"超时 ({timeout}s)，未检测到标签: {keyword}")
    return 1


def cmd_list(args: argparse.Namespace) -> int:
    data = list_agents()
    if not data:
        _info("（注册表为空）")
        return 0
    if args.json:
        import json
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return 0
    _info("已注册的 Agent：")
    _info("────────────────────────────────────────────────")
    for k, v in data.items():
        _info(k)
        _info(f"  pane_id  : {v.get('pane_id')}")
        _info(f"  session  : {v.get('session')}")
        _info(f"  注册时间 : {v.get('registered')}")
    return 0


def cmd_health(args: argparse.Namespace) -> int:
    data = list_agents()
    target = args.agent

    def check_one(name: str, pane: str, session: str) -> None:
        alive = is_pane_alive(session, pane)
        if not alive:
            print(f"{name:24} {session:20} {pane:8} 🔴    pane 不存在或 session 不存在")
        else:
            print(f"{name:24} {session:20} {pane:8} 🟢    在线")

    print(f"{'Agent':24} {'Session':20} {'Pane':8} {'状态':6} {'备注'}")
    print("─" * 60)
    if target:
        meta = get_agent(target)
        if meta is None:
            _err(f"[{target}] 未注册")
            return
        check_one(target, meta["pane_id"], meta["session"])
    else:
        for name, meta in data.items():
            check_one(name, meta["pane_id"], meta["session"])


def cmd_memory(args: argparse.Namespace) -> int:
    records = memory.query_memory(
        session=args.session,
        pane=args.pane,
        agent=args.agent,
        last=args.last,
    )
    if args.json:
        import json as _json
        print(_json.dumps(records, indent=2, ensure_ascii=False))
    else:
        print(memory.format_text(records))
    return 0


def cmd_prune(args: argparse.Namespace) -> int:
    data = list_agents()
    prune_list = []
    for name, meta in data.items():
        if not is_pane_alive(meta["session"], meta["pane_id"]):
            prune_list.append(name)
    if not prune_list:
        _info(f"✅ 所有 {len(data)} 个 Agent 均在线，无需清理")
        return 0
    for name in prune_list:
        if args.dry_run:
            _info(f"🟡 [dry-run] 将清理: {name}")
        else:
            unregister_agent(name)
            _info(f"🗑️  已清理: {name}")
    if args.dry_run:
        _info(f"────────────────────────────────────")
        _info(f"共发现 {len(prune_list)} / {len(data)} 个僵尸 Agent（未实际删除）")
    else:
        _info(f"────────────────────────────────────")
        _info(f"✅ 共清理 {len(prune_list)} / {len(data)} 个僵尸 Agent")
    return 0


def cmd_send_file(args: argparse.Namespace) -> int:
    name = args.agent
    file_path = args.file_path
    import pathlib
    p = pathlib.Path(file_path)
    if not p.exists():
        _err(f"文件不存在: {file_path}")
        return 1

    ext_map = {
        "rs": "rust", "py": "python", "js": "javascript", "ts": "typescript",
        "tsx": "tsx", "jsx": "jsx", "go": "go", "sh": "bash", "bash": "bash",
        "zsh": "bash", "md": "markdown", "json": "json", "yaml": "yaml",
        "yml": "yaml", "html": "html", "css": "css", "java": "java",
        "cpp": "cpp", "c": "cpp", "h": "cpp", "hpp": "cpp",
    }
    lang = ext_map.get(p.suffix.lstrip("."), "")
    content = p.read_text(encoding="utf-8")
    filename = p.name
    if lang:
        message = f"请查看文件 `{filename}`：\n\n```{lang}\n{content}\n```\n"
    else:
        message = f"请查看文件 `{filename}`：\n\n```\n{content}\n```\n"

    meta = _resolve_agent(name)
    if meta is None:
        _err(f"[{name}] 未注册")
        return 1
    prefix = _build_sender_prefix()
    message = _obfuscate_talk_tags(message)
    message = _add_talk_hint(message)
    full_message = f"{prefix}\n{message}"
    send_text(meta["session"], meta["pane_id"], full_message)
    logger.log_message([(name, meta)], content, message_type="direct", file_name=filename)
    _info(f"📨 [{name}] ← 已发送文件 {filename}")
    return 0


def cmd_multicast(args: argparse.Namespace) -> int:
    agents_str = args.agents
    message = args.message
    agents = [a.strip() for a in agents_str.split(",") if a.strip()]
    prefix = _build_sender_prefix()
    message = _obfuscate_talk_tags(message)
    message = _add_talk_hint(message)
    full_message = f"{prefix}\n{message}"
    sent = []
    for agent in agents:
        meta = _resolve_agent(agent)
        if meta is None:
            _warn(f"{agent} 发送失败（未注册或已离线）")
            continue
        send_text(meta["session"], meta["pane_id"], full_message)
        sent.append((agent, meta))
        _info(f"📢 已发送给 {agent}")
    if sent:
        logger.log_message(sent, message, message_type="multicast")
    _info("✅ 多播完成")
    return 0


def cmd_broadcast(args: argparse.Namespace) -> int:
    message = args.message
    data = list_agents()
    if not data:
        _err("注册表不存在，无 Agent 可广播")
        return 1
    prefix = _build_sender_prefix()
    message = _obfuscate_talk_tags(message)
    message = _add_talk_hint(message)
    full_message = f"{prefix}\n{message}"
    sent = []
    for agent in list(data.keys()):
        meta = _resolve_agent(agent)
        if meta is None:
            _warn(f"{agent} 广播失败（已离线并自动注销）")
            continue
        send_text(meta["session"], meta["pane_id"], full_message)
        sent.append((agent, meta))
        _info(f"📢 已广播给 {agent}")
    if sent:
        logger.log_message(sent, message, message_type="broadcast")
    _info("✅ 广播完成")
    return 0


def cmd_review(args: argparse.Namespace) -> int:
    source = args.source or "kimi_coder_Alex"
    target = args.target or "claude_reviewer_Blob"
    meta_src = _resolve_agent(source)
    if meta_src is None:
        _err(f"[{source}] 未注册")
        return 1
    text = dump_screen(meta_src["session"], meta_src["pane_id"], ansi=False)
    lines = text.splitlines()
    content = "\n".join(lines[-80:])
    prompt = f"""请审查以下代码：

{content}

---
审查要点：
1. 代码正确性
2. 潜在 bug
3. 性能问题
4. 可读性与维护性
"""
    meta_tgt = _resolve_agent(target)
    if meta_tgt is None:
        _err(f"[{target}] 未注册")
        return 1
    send_text(meta_tgt["session"], meta_tgt["pane_id"], prompt)
    _info(f"📨 审查请求已发送给 [{target}]")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="zellij-talk", description="zellij-talk CLI")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p = subparsers.add_parser("register", help="注册当前面板为 Agent")
    p.add_argument("name", help="Agent 名称")

    p = subparsers.add_parser("unregister", help="注销指定 Agent")
    p.add_argument("name", help="Agent 名称")

    p = subparsers.add_parser("unregister-all", help="注销所有 Agent")
    p.add_argument("--current-session", action="store_true", help="仅注销当前 session")

    p = subparsers.add_parser("auto-register", help="自动生成名字并注册")
    p.add_argument("role", nargs="?", default="coder", help="角色，默认 coder")

    p = subparsers.add_parser("to", help="向 Agent 发消息")
    p.add_argument("agent", help="Agent 名称")
    p.add_argument("content", nargs="?", help="消息内容")
    p.add_argument("--no-enter", action="store_true", help="不发送回车")

    p = subparsers.add_parser("reply", help="直接向 session:pane 发消息（无需注册）")
    p.add_argument("target", help="目标，格式: session:pane_id")
    p.add_argument("content", nargs="?", help="消息内容")
    p.add_argument("--no-enter", action="store_true", help="不发送回车")

    p = subparsers.add_parser("from", help="读取 Agent 输出")
    p.add_argument("agent", help="Agent 名称")
    p.add_argument("lines", nargs="?", type=int, default=100, help="行数，默认 100")
    p.add_argument("--ansi", action="store_true", help="保留 ANSI 颜色")

    p = subparsers.add_parser("watch", help="监听 Agent 输出")
    p.add_argument("agent", help="Agent 名称")
    p.add_argument("keyword", nargs="?", help="关键词")

    p = subparsers.add_parser("wait", help="阻塞等待关键词")
    p.add_argument("agent", help="Agent 名称")
    p.add_argument("keyword", help="关键词")
    p.add_argument("timeout", nargs="?", type=int, default=60, help="超时秒数，默认 60")

    p = subparsers.add_parser("list", help="列出已注册 Agent")
    p.add_argument("--json", action="store_true", help="以 JSON 输出")

    p = subparsers.add_parser("health", help="健康检查")
    p.add_argument("agent", nargs="?", help="指定 Agent，不填则检查全部")

    p = subparsers.add_parser("memory", help="查询对话历史记录")
    p.add_argument("--session", help="按 session 过滤")
    p.add_argument("--pane", help="按 pane_id 过滤")
    p.add_argument("--agent", help="按 Agent 名过滤")
    p.add_argument("--last", type=int, default=20, help="返回最近 N 条，默认 20")
    p.add_argument("--json", action="store_true", help="以 JSON 输出")

    p = subparsers.add_parser("prune", help="清理僵尸 Agent")
    p.add_argument("--dry-run", action="store_true", help="仅预览不删除")

    p = subparsers.add_parser("send-file", help="发送文件给 Agent")
    p.add_argument("agent", help="Agent 名称")
    p.add_argument("file_path", help="文件路径")

    p = subparsers.add_parser("multicast", help="多播消息")
    p.add_argument("agents", help="逗号分隔的 Agent 列表")
    p.add_argument("message", help="消息内容")

    p = subparsers.add_parser("broadcast", help="广播消息")
    p.add_argument("message", help="消息内容")

    p = subparsers.add_parser("review", help="代码审查工作流")
    p.add_argument("source", nargs="?", help="源 Agent")
    p.add_argument("target", nargs="?", help="目标 Agent")

    args = parser.parse_args(argv)
    handlers = {
        "register": cmd_register,
        "unregister": cmd_unregister,
        "unregister-all": cmd_unregister_all,
        "auto-register": cmd_auto_register,
        "to": cmd_to,
        "reply": cmd_reply,
        "from": cmd_from,
        "watch": cmd_watch,
        "wait": cmd_wait,
        "list": cmd_list,
        "health": cmd_health,
        "memory": cmd_memory,
        "prune": cmd_prune,
        "send-file": cmd_send_file,
        "multicast": cmd_multicast,
        "broadcast": cmd_broadcast,
        "review": cmd_review,
    }
    handler = handlers[args.command]
    return handler(args) or 0


if __name__ == "__main__":
    sys.exit(main())
