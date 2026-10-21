#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""验证 Claude Haiku 5.5 走 Anthropic 协议端点是否可用（OpenAI 兼容端点报 ModelProtocolUnsupported）。"""
import os
import re
import ssl
import sys
import json
import time
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding="utf-8")
H = os.path.join(os.path.expanduser("~"), "AppData", "Local", "hermes")
PROXY = "http://127.0.0.1:10808"
CTX = ssl.create_default_context()
OP = urllib.request.build_opener(
    urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}),
    urllib.request.HTTPSHandler(context=CTX))


def load_env():
    d = {}
    with open(os.path.join(H, ".env"), encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                d[k.strip()] = v.strip().strip('"').strip("'")
    return d


env = load_env()
key = env.get("OPENCODE_GO_API_KEY", "")

# 从 config.yaml 找 opencode-go-anthropic 的 base_url
cfg = open(os.path.join(H, "config.yaml"), encoding="utf-8", errors="replace").read()
m = re.search(r"-\s*name:\s*opencode-go-anthropic(.{0,400})", cfg, re.S)
base = None
if m:
    bm = re.search(r"base_url:\s*(\S+)", m.group(1))
    base = bm.group(1).strip('"\'') if bm else None
print("config 里 opencode-go-anthropic base_url =", base)

CANDIDATES = [
    base,
    "https://opencode.ai/zen/go",
    "https://opencode.ai/zen/go/v1",
    "https://opencode.ai/inference/go",
]
CANDIDATES = [c for c in CANDIDATES if c]

for b in CANDIDATES:
    url = b.rstrip("/") + "/messages"
    print(f"\n{'='*66}\n尝试 {url}\n{'='*66}")
    body = json.dumps({
        "model": "claude-haiku-5-5",
        "max_tokens": 64,
        "messages": [{"role": "user", "content": "只回复两个字：收到"}],
    }).encode()
    headers = {
        "Content-Type": "application/json",
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
        "User-Agent": "hermes-agent/0.21.0",
        "x-opencode-session": "hermes-haiku-protocol-test",
    }
    t0 = time.time()
    try:
        r = OP.open(urllib.request.Request(url, data=body, headers=headers), timeout=90)
        d = json.loads(r.read().decode())
        dt = time.time() - t0
        txt = ""
        for blk in (d.get("content") or []):
            if blk.get("type") == "text":
                txt += blk.get("text", "")
        print(f"  ✅ 200 ({dt:.1f}s)")
        print(f"  model   : {d.get('model')}")
        print(f"  content : {txt[:80]!r}")
        print(f"  usage   : {d.get('usage')}")
        break
    except urllib.error.HTTPError as e:
        print(f"  ❌ HTTP {e.code}: {e.read().decode(errors='replace')[:220]}")
    except Exception as e:
        print(f"  ❌ {type(e).__name__}: {str(e)[:150]}")
