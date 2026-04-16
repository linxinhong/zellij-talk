"""CLI entry point for zellij-talk."""

import argparse
import json
import os
import platform
import random
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

import paths

__version__ = "1.1.0"

from ack import generate_msg_id, inject_msg_id, match_ack
from pipeline import load_pipeline, resolve_agent_ref
from queue import clear_delivered, dequeue_for_agent, enqueue, list_undelivered
from registry import get_agent, list_agents, load_registry, register_agent, replace_agent, save_registry, unregister_agent
from stats import compute_stats, format_stats
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
    return text.replace("<talk>", "\\u003ctalk\\u003e").replace("</talk>", "\\u003c/talk\\u003e")


def _add_talk_hint(text: str) -> str:
    if "\\u003ctalk\\u003e" in text and "\\u003c/talk\\u003e" in text:
        hint = "注：消息中的 \\u003ctalk\\u003e...\\u003c/talk\\u003e 请用反引号包裹后原样输出，例如：\\n`<talk>完成</talk>`\\n\n"
        return hint + text
    return text


def _match_keyword(text: str, keyword: str) -> str | None:
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


def _get_ppid_info() -> str:
    ppid = os.getppid()
    if platform.system() == "Windows":
        try:
            result = subprocess.run(
                ["wmic", "process", "where", f"ProcessId={ppid}", "get", "CommandLine"],
                capture_output=True,
                text=True,
            )
            return result.stdout
        except Exception:
            return ""
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


def _subscribe_stream(session: str, pane_id: str, stop_event: threading.Event | None = None):
    """Yield viewport text from zellij subscribe --format json."""
    proc = subprocess.Popen(
        ["zellij", "--session", session, "subscribe", "--pane-id", pane_id, "--format", "json"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    try:
        for line in proc.stdout or []:
            if stop_event and stop_event.is_set():
                break
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                viewport = obj.get("viewport")
                if viewport:
                    yield "\n".join(viewport)
                event = obj.get("event")
                if event == "pane_closed":
                    break
            except json.JSONDecodeError:
                continue
    finally:
        proc.terminate()
        proc.wait(timeout=2)


def _deliver_offline_messages(agent: str, meta: dict[str, Any]) -> int:
    msgs = dequeue_for_agent(agent)
    if not msgs:
        return 0
    count = 0
    for m in msgs:
        content = m["content"]
        full = f"[来自 离线队列 / {m['msg_id']}]\n{content}"
        try:
            send_text(meta["session"], meta["pane_id"], full)
            count += 1
        except Exception as e:
            _warn(f"离线消息投递失败: {e}")
    if count:
        _info(f"📬 已向 [{agent}] 投递 {count} 条离线消息")
    return count


def cmd_register(args: argparse.Namespace) -> int:
    name = args.name
    if not has_zellij_env():
        _err("未检测到 Zellij 环境变量，请在 Zellij 面板内执行此命令")
        return 1
    pane_id = get_current_pane_id()
    session = get_current_session()
    assert pane_id and session

    existed_before = name in load_registry()
    meta = {
        "role": args.role or None,
        "capabilities": [c.strip() for c in args.capabilities.split(",") if c.strip()] if args.capabilities else [],
        "system_prompt": args.prompt or None,
    }
    old = replace_agent(name, session, pane_id, extra_meta={k: v for k, v in meta.items() if v is not None})
    if old:
        _warn(f"[{old}] 占用了同一 pane，将自动注销旧记录")
    if existed_before:
        _warn(f"[{name}] 已注册，将覆盖旧记录")

    rename_pane(pane_id, name)
    _info(f"✅ [{name}] 注册成功")
    _info(f"   pane_id : {pane_id}")
    _info(f"   session : {session}")
    _info(f"   pane_name : {name}")
    if meta.get("role"):
        _info(f"   role : {meta['role']}")
    if meta.get("capabilities"):
        _info(f"   capabilities : {', '.join(meta['capabilities'])}")

    # Deliver offline messages
    agent_meta = _resolve_agent(name, auto_prune=False)
    if agent_meta:
        _deliver_offline_messages(name, agent_meta)
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


def cmd_init(args: argparse.Namespace) -> int:
    _info("🚀 初始化 zellij-talk ...")
    if shutil.which("zellij") is None:
        _err("未找到 zellij 命令，请先安装 Zellij")
        return 1
    _info("✅ zellij 已安装")
    talk_dir = paths.get_talk_dir()
    talk_dir.mkdir(parents=True, exist_ok=True)
    _info(f"✅ 数据目录已就绪: {talk_dir}")
    registry_path = paths.get_registry_path()
    if not registry_path.exists():
        example = Path(__file__).parent.parent / "registry.json.example"
        if example.exists():
            import shutil as _shutil
            _shutil.copy2(example, registry_path)
            _info(f"✅ 已从模板创建注册表: {registry_path}")
        else:
            _warn(f"注册表模板不存在，跳过: {example}")
    else:
        _info(f"✅ 注册表已存在: {registry_path}")
    _info("")
    class PruneArgs:
        dry_run = False
    cmd_prune(PruneArgs())
    _info("")
    _info("✅ 环境初始化完成。下一步：请确认当前 Agent 的职责，然后执行 register 或 auto-register。")
    _info("   示例：python3 scripts/cli.py auto-register reviewer")
    return 0


def cmd_auto_register(args: argparse.Namespace) -> int:
    role = args.role or "coder"
    tool = os.environ.get("ZELLIJ_TALK_TOOL", "")
    if not tool:
        combined = _get_ppid_info().lower()
        if "kimi" in combined:
            tool = "kimi"
        elif "claude" in combined:
            tool = "claude"
        elif "opencode" in combined:
            tool = "opencode"
    if not tool:
        tool = "agent"
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
    class FakeArgs:
        name = chosen
        role = None
        capabilities = None
        prompt = None
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

    msg_id = generate_msg_id()
    prefix = _build_sender_prefix()
    content = _obfuscate_talk_tags(content)
    content = _add_talk_hint(content)
    full_content = f"{prefix}\n{inject_msg_id(content, msg_id)}"
    try:
        send_text(meta["session"], meta["pane_id"], full_content, no_enter=args.no_enter)
    except Exception as e:
        _warn(f"发送失败，消息已转入离线队列: {e}")
        enqueue(msg_id, name, content)
        return 2
    logger.log_message([(name, meta)], content, message_type="direct")
    _info(f"📨 [{name} @ {meta['pane_id']} / {meta['session']}] ← 已发送 [MSG_ID:{msg_id}]")

    if args.wait_ack:
        _info(f"⏳ 等待 ACK [{msg_id}] ...")
        stop_event = threading.Event()
        result = {"found": False}

        def _search():
            for text in _subscribe_stream(meta["session"], meta["pane_id"], stop_event=stop_event):
                if match_ack(text, msg_id):
                    result["found"] = True
                    return

        t = threading.Thread(target=_search)
        t.daemon = True
        t.start()
        t.join(timeout=args.ack_timeout)
        if not result["found"]:
            stop_event.set()
            t.join(timeout=2)

        if result["found"]:
            _info(f"✅ 收到 ACK [{msg_id}]")
        else:
            _warn(f"⚠️ 未收到 ACK [{msg_id}]，消息已转入离线队列")
            enqueue(msg_id, name, content)
            return 2
    return 0


def cmd_send_json(args: argparse.Namespace) -> int:
    name = args.agent
    payload = args.payload or ""
    if not payload and args.file:
        p = Path(args.file)
        if not p.exists():
            _err(f"文件不存在: {args.file}")
            return 1
        payload = p.read_text(encoding="utf-8")
    if not payload:
        _err("payload 不能为空")
        return 1
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        _err("payload 不是合法的 JSON")
        return 1

    meta = _resolve_agent(name)
    if meta is None:
        _err(f"[{name}] 未注册")
        return 1

    envelope = {
        "id": generate_msg_id(),
        "from": logger.get_sender_info()["name"],
        "to": name,
        "type": args.type or "message",
        "payload": data,
        "ts": logger._now_str(),
    }
    text = json.dumps(envelope, ensure_ascii=False)
    send_text(meta["session"], meta["pane_id"], text)
    logger.log_message([(name, meta)], text, message_type="direct")
    _info(f"📨 JSON 消息已发送给 [{name}] [ID:{envelope['id']}]")
    return 0


def cmd_envelope(args: argparse.Namespace) -> int:
    envelope = {
        "id": generate_msg_id(),
        "from": logger.get_sender_info()["name"],
        "to": args.agent,
        "type": args.type or "message",
        "payload": args.payload,
        "ts": logger._now_str(),
    }
    print(json.dumps(envelope, ensure_ascii=False, indent=2))
    return 0


def cmd_reply(args: argparse.Namespace) -> int:
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
    text = dump_screen(meta["session"], meta["pane_id"], ansi=args.ansi, full=False)
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
    try:
        for text in _subscribe_stream(meta["session"], meta["pane_id"]):
            if not keyword:
                print(text)
            else:
                matched = _match_keyword(text, keyword)
                if matched:
                    _info(f"🎯 [{name}] 检测到标签: {matched}")
                    print(text)
                    return 0
    except KeyboardInterrupt:
        pass
    return 0


def cmd_wait(args: argparse.Namespace) -> int:
    name = args.agent
    keyword = args.keyword
    timeout = args.timeout
    _info(f"⏳ 等待 [{name}] 输出中出现标签: '{keyword}' (超时 {timeout}s)")
    sys.stdout.flush()
    meta = _resolve_agent(name, auto_prune=False)
    if meta is None:
        _err(f"[{name}] 未注册")
        return 1

    stop_event = threading.Event()
    result = {"found": False, "matched": None, "text": ""}

    def _search():
        for text in _subscribe_stream(meta["session"], meta["pane_id"], stop_event=stop_event):
            result["text"] = text
            matched = _match_keyword(text, keyword)
            if matched:
                result["found"] = True
                result["matched"] = matched
                return

    t = threading.Thread(target=_search)
    t.daemon = True
    t.start()
    t.join(timeout=timeout)
    if not result["found"]:
        stop_event.set()
        t.join(timeout=2)

    if result["found"]:
        matched = result["matched"]
        _info(f"🎯 检测到标签: {matched}")
        for line in result["text"].splitlines():
            if matched in line:
                print(line)
        return 0

    _err(f"超时 ({timeout}s)，未检测到标签: {keyword}")
    return 1


def cmd_list(args: argparse.Namespace) -> int:
    data = list_agents()
    if not data:
        _info("（注册表为空）")
        return 0
    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return 0
    _info("已注册的 Agent：")
    _info("────────────────────────────────────────────────")
    for k, v in data.items():
        _info(k)
        _info(f"  pane_id  : {v.get('pane_id')}")
        _info(f"  session  : {v.get('session')}")
        _info(f"  注册时间 : {v.get('registered')}")
        if args.capabilities:
            caps = v.get("capabilities", [])
            role = v.get("role", "")
            _info(f"  role     : {role or '-'}")
            _info(f"  caps     : {', '.join(caps) if caps else '-'}")
    return 0


def cmd_find(args: argparse.Namespace) -> int:
    data = list_agents()
    caps_query = set(c.strip() for c in args.cap.split(",") if c.strip())
    matches = []
    for name, meta in data.items():
        agent_caps = set()
        raw_caps = meta.get("capabilities", [])
        if isinstance(raw_caps, str):
            agent_caps = set(c.strip() for c in raw_caps.split(",") if c.strip())
        elif isinstance(raw_caps, list):
            agent_caps = set(raw_caps)
        if caps_query.issubset(agent_caps):
            matches.append((name, meta))
    if not matches:
        _info("（未找到匹配的 Agent）")
        return 0
    _info("匹配的 Agent：")
    _info("────────────────────────────────────────────────")
    for name, meta in matches:
        caps = meta.get("capabilities", [])
        _info(f"{name}  [{', '.join(caps)}]  ({meta['session']} / {meta['pane_id']})")
    return 0


def cmd_health(args: argparse.Namespace) -> int:
    data = list_agents()
    target = args.agent
    any_dead = False

    def check_one(name: str, pane: str, session: str) -> None:
        nonlocal any_dead
        alive = is_pane_alive(session, pane)
        if not alive:
            any_dead = True
            print(f"{name:24} {session:20} {pane:8} 🔴    pane 不存在或 session 不存在")
        else:
            print(f"{name:24} {session:20} {pane:8} 🟢    在线")

    print(f"{'Agent':24} {'Session':20} {'Pane':8} {'状态':6} {'备注'}")
    print("─" * 60)
    if target:
        meta = get_agent(target)
        if meta is None:
            _err(f"[{target}] 未注册")
            return 1
        check_one(target, meta["pane_id"], meta["session"])
    else:
        for name, meta in data.items():
            check_one(name, meta["pane_id"], meta["session"])
    return 2 if any_dead else 0


def cmd_memory(args: argparse.Namespace) -> int:
    records = memory.query_memory(
        session=args.session,
        pane=args.pane,
        agent=args.agent,
        last=args.last,
    )
    if args.json:
        print(json.dumps(records, indent=2, ensure_ascii=False))
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
    source = args.source
    target = args.target
    if not source or not target:
        _err("请提供 source 和 target Agent 名称，例如: review kimi_coder_Alex claude_reviewer_Blob")
        return 1
    meta_src = _resolve_agent(source)
    if meta_src is None:
        _err(f"[{source}] 未注册")
        return 1
    text = dump_screen(meta_src["session"], meta_src["pane_id"], ansi=False, full=False)
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


def cmd_inbox(args: argparse.Namespace) -> int:
    agent = args.agent
    if args.clear:
        count = clear_delivered()
        _info(f"🗑️  已清理 {count} 条已投递的离线消息")
        return 0
    msgs = list_undelivered(agent)
    if not msgs:
        _info("（没有未投递的离线消息）")
        return 0
    _info(f"未投递的离线消息 ({len(msgs)} 条):")
    _info("────────────────────────────────────────────────")
    for m in msgs:
        _info(f"[{m['msg_id']}] → {m['to_agent']}  ({m['created_at']})")
        _info(f"    {m['content'][:80]}{'...' if len(m['content']) > 80 else ''}")
    return 0


def cmd_pipeline(args: argparse.Namespace) -> int:
    try:
        spec = load_pipeline(args.file)
    except Exception as e:
        _err(str(e))
        return 1
    steps = spec.get("steps", [])
    if not steps:
        _warn("Pipeline 为空")
        return 0

    variables = {"task": args.task or ""}
    registry = list_agents()

    for idx, step in enumerate(steps):
        agent_ref = step.get("agent", "")
        resolved = resolve_agent_ref(agent_ref, registry)
        if resolved is None:
            _err(f"第 {idx + 1} 步: 无法解析 agent '{agent_ref}'")
            return 1
        action = step.get("action", "")
        for k, v in variables.items():
            action = action.replace(f"{{{k}}}", str(v))

        _info(f"▶ 步骤 {idx + 1}: {resolved} ← {action[:60]}")
        class ToArgs:
            agent = resolved
            content = action
            no_enter = False
            wait_ack = False
            ack_timeout = 60
        ret = cmd_to(ToArgs())
        if ret not in (0, 2):
            _err(f"第 {idx + 1} 步发送失败")
            return 1

        wait_for = step.get("wait_for")
        if wait_for:
            step_timeout = step.get("timeout", 60)
            class WaitArgs:
                agent = resolved
                keyword = wait_for
                timeout = step_timeout
            _info(f"⏳ 等待 {resolved} 输出 '{wait_for}' (最多 {step_timeout}s)")
            wret = cmd_wait(WaitArgs())
            if wret != 0:
                _err(f"第 {idx + 1} 步等待超时或失败")
                return 1
            # Capture last output for next step variable
            text = dump_screen(registry[resolved]["session"], registry[resolved]["pane_id"], full=False)
            variables["prev_output"] = "\n".join(text.splitlines()[-50:])
    _info("✅ Pipeline 执行完毕")
    return 0


def cmd_dashboard(args: argparse.Namespace) -> int:
    import time
    path = paths.get_session_jsonl_path(args.session) if args.session else paths.get_all_jsonl_path()
    if not path.exists():
        _info("（日志文件不存在）")
        return 0
    _info(f"📊 Dashboard: {path}")
    _info("─" * 60)
    last_size = path.stat().st_size
    # Print existing tail
    records = memory._read_log_file(path)
    for rec in records[-20:]:
        print(_format_dashboard_line(rec))
    if not args.follow:
        return 0
    try:
        while True:
            time.sleep(1)
            size = path.stat().st_size
            if size > last_size:
                new_records = memory._read_log_file(path)
                for rec in new_records[len(records):]:
                    print(_format_dashboard_line(rec))
                records = new_records
                last_size = size
    except KeyboardInterrupt:
        pass
    return 0


def _format_dashboard_line(rec: dict[str, Any]) -> str:
    ts = rec.get("timestamp", "")
    from_name = rec["from"]["name"]
    to_type = rec["to"]["type"]
    if to_type == "broadcast":
        to_display = f"📢 {', '.join(t['name'] for t in rec['to']['targets'])}"
    elif to_type == "multicast":
        to_display = f"📡 {', '.join(t['name'] for t in rec['to']['targets'])}"
    else:
        to_display = rec["to"]["targets"][0]["name"]
    content = rec.get("content", "").replace("\n", " ")[:40]
    return f"[{ts}] {from_name} → {to_display}  \"{content}{'...' if len(rec.get('content', '')) > 40 else ''}\""


def cmd_stats(args: argparse.Namespace) -> int:
    try:
        data = compute_stats(session=args.session, today=args.today)
    except Exception as e:
        _err(str(e))
        return 1
    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(format_stats(data))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="zellij-talk", description="zellij-talk CLI")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p = subparsers.add_parser("register", help="注册当前面板为 Agent")
    p.add_argument("name", help="Agent 名称")
    p.add_argument("--role", help="角色，例如 reviewer")
    p.add_argument("--capabilities", help="能力列表，逗号分隔，例如 read_code,review")
    p.add_argument("--prompt", help="系统提示词 / 角色描述")

    p = subparsers.add_parser("unregister", help="注销指定 Agent")
    p.add_argument("name", help="Agent 名称")

    p = subparsers.add_parser("unregister-all", help="注销所有 Agent")
    p.add_argument("--current-session", action="store_true", help="仅注销当前 session")

    p = subparsers.add_parser("init", help="初始化：清理僵尸 Agent 并自动注册当前面板")
    p.add_argument("role", nargs="?", default="coder", help="角色，默认 coder")

    p = subparsers.add_parser("auto-register", help="自动生成名字并注册")
    p.add_argument("role", nargs="?", default="coder", help="角色，默认 coder")

    p = subparsers.add_parser("to", help="向 Agent 发消息")
    p.add_argument("agent", help="Agent 名称")
    p.add_argument("content", nargs="?", help="消息内容")
    p.add_argument("--no-enter", action="store_true", help="不发送回车")
    p.add_argument("--wait-ack", action="store_true", help="发送后等待 ACK")
    p.add_argument("--ack-timeout", type=int, default=60, help="ACK 超时秒数，默认 60")

    p = subparsers.add_parser("send-json", help="发送结构化 JSON 消息")
    p.add_argument("agent", help="Agent 名称")
    p.add_argument("--file", help="从文件读取 payload")
    p.add_argument("--payload", help="直接传入 JSON payload 字符串")
    p.add_argument("--type", default="message", help="消息类型")

    p = subparsers.add_parser("envelope", help="生成 JSON 信封到 stdout")
    p.add_argument("agent", help="目标 Agent")
    p.add_argument("--payload", required=True, help="payload 内容")
    p.add_argument("--type", default="message", help="消息类型")

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
    p.add_argument("--capabilities", action="store_true", help="显示角色和能力")

    p = subparsers.add_parser("find", help="按能力查找 Agent")
    p.add_argument("cap", help="能力名称，逗号分隔表示 AND")

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

    p = subparsers.add_parser("inbox", help="查看离线消息队列")
    p.add_argument("agent", nargs="?", help="指定 Agent")
    p.add_argument("--clear", action="store_true", help="清理已投递消息")

    p = subparsers.add_parser("pipeline", help="执行多步协作 pipeline")
    p.add_argument("file", help="YAML pipeline 文件路径")
    p.add_argument("--task", help="任务描述，用于变量替换")

    p = subparsers.add_parser("dashboard", help="消息流仪表盘")
    p.add_argument("--session", help="指定 session，默认全局 all.jsonl")
    p.add_argument("--follow", action="store_true", help="持续跟踪新消息")

    p = subparsers.add_parser("stats", help="消息统计")
    p.add_argument("--session", help="指定 session")
    p.add_argument("--today", action="store_true", help="仅统计今日")
    p.add_argument("--json", action="store_true", help="以 JSON 输出")

    args = parser.parse_args(argv)
    handlers = {
        "register": cmd_register,
        "unregister": cmd_unregister,
        "unregister-all": cmd_unregister_all,
        "init": cmd_init,
        "auto-register": cmd_auto_register,
        "to": cmd_to,
        "send-json": cmd_send_json,
        "envelope": cmd_envelope,
        "reply": cmd_reply,
        "from": cmd_from,
        "watch": cmd_watch,
        "wait": cmd_wait,
        "list": cmd_list,
        "find": cmd_find,
        "health": cmd_health,
        "memory": cmd_memory,
        "prune": cmd_prune,
        "send-file": cmd_send_file,
        "multicast": cmd_multicast,
        "broadcast": cmd_broadcast,
        "review": cmd_review,
        "inbox": cmd_inbox,
        "pipeline": cmd_pipeline,
        "dashboard": cmd_dashboard,
        "stats": cmd_stats,
    }
    handler = handlers[args.command]
    return handler(args) or 0


if __name__ == "__main__":
    sys.exit(main())
