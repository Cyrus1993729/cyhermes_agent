#!/usr/bin/env python3
"""读本机 a2a_agents 里某个 peer 的真实现值（不回显 token）。

用法:
    python read_a2a_peer.py            # 列出所有 peer
    python read_a2a_peer.py 妈妈       # 只看一个 peer（中文名直接传，别加引号转义）

为什么不用正则抠块:
    2026-10-20 / 2026-11-08 两次实测，`^a2a_agents:\s*\n\s+\S+:\s*\n(.*?)(?=^\S)` 这类
    单正则都会 AttributeError: 'NoneType' object has no attribute 'group'
    （缩进 4/6 空格、块在文件尾部、CRLF 等任一条件打破假设就废）。
    本脚本按【相对缩进】逐行走：找到 `a2a_agents:` → 取下一个非空行缩进作 peer 基准
    → 缩进等于基准且形如 `name:` 的行开新 peer → 更深缩进的行归属该 peer。

输出:
    peer / url / token: present(len=N) 或 MISSING / auth.type / capabilities
    token 只报存在与长度，永不打印值 —— 回执、日志、截图都安全。
"""
import io
import os
import sys


def config_path() -> str:
    home = os.environ.get("HERMES_HOME")
    if not home:
        la = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~/.local/share")
        home = os.path.join(la, "hermes")
    return os.path.join(home, "config.yaml")


def parse(path: str) -> dict:
    lines = io.open(path, encoding="utf-8").read().splitlines()
    try:
        start = next(i for i, l in enumerate(lines) if l.strip() == "a2a_agents:")
    except StopIteration:
        return {}
    base = len(lines[start]) - len(lines[start].lstrip())
    nodes: dict = {}
    cur = None
    for raw in lines[start + 1:]:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        ind = len(raw) - len(raw.lstrip())
        if ind <= base:
            break  # 块结束
        body = raw.strip()
        if ind == base + 2 and body.endswith(":") and " " not in body[:-1]:
            cur = body[:-1]
            nodes[cur] = {"capabilities": []}
            continue
        if cur is None:
            continue
        key, _, val = body.partition(":")
        key, val = key.strip(), val.strip()
        if key == "token":
            nodes[cur]["token"] = val
        elif key == "type":
            nodes[cur]["auth_type"] = val
        elif key == "url":
            nodes[cur]["url"] = val
        elif body.startswith("- "):
            nodes[cur]["capabilities"].append(body[2:].strip())
    return nodes


def show(name: str, d: dict) -> None:
    tok = d.get("token") or ""
    print(f"peer        : {name}")
    print(f"url         : {d.get('url', 'MISSING')}")
    print(f"auth.type   : {d.get('auth_type', '-')}")
    print("token       : " + (f"present(len={len(tok)})" if tok else "MISSING"))
    caps = d.get("capabilities") or []
    print("capabilities: " + (", ".join(caps) if caps else "-"))
    print()


if __name__ == "__main__":
    p = config_path()
    if not os.path.exists(p):
        print(f"config not found: {p}")
        sys.exit(1)
    nodes = parse(p)
    if not nodes:
        print("no a2a_agents block found")
        sys.exit(1)
    want = sys.argv[1] if len(sys.argv) > 1 else None
    if want:
        if want not in nodes:
            print(f"peer {want!r} not found; have: {list(nodes)}")
            sys.exit(1)
        show(want, nodes[want])
    else:
        for k, v in nodes.items():
            show(k, v)
