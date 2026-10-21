#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""核对：我们 config 里引用的模型，网关是否还在售（/models 拉全量对比）。"""
import os
import re
import ssl
import sys
import json
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
PROXY = "http://127.0.0.1:10808"
HERMES = os.path.join(os.path.expanduser("~"), "AppData", "Local", "hermes")
CTX = ssl.create_default_context()
OP = urllib.request.build_opener(
    urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}),
    urllib.request.HTTPSHandler(context=CTX))


def load_env():
    d = {}
    with open(os.path.join(HERMES, ".env"), encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                d[k.strip()] = v.strip().strip('"').strip("'")
    return d


env = load_env()
key = env["OPENCODE_GO_API_KEY"]
h = {"Authorization": f"Bearer {key}", "User-Agent": "hermes-agent/0.21.0",
     "x-opencode-session": "hermes-model-audit"}
r = OP.open(urllib.request.Request("https://opencode.ai/zen/go/v1/models", headers=h), timeout=60)
data = json.loads(r.read().decode())
live = sorted({str(m.get("id") or m.get("name")) for m in (data.get("data") or data.get("models") or [])})
print(f"网关在线模型（{len(live)} 个）：")
for m in live:
    print("   ", m)

# 扫 config.yaml 里出现的模型名
cfg = os.path.join(HERMES, "config.yaml")
txt = open(cfg, encoding="utf-8", errors="replace").read()
referenced = set()
for line in txt.splitlines():
    s = line.strip()
    m = re.match(r"^(?:-\s*)?model:\s*['\"]?([\w.\-:/]+)['\"]?", s)
    if m:
        referenced.add(m.group(1))
    m2 = re.match(r"^(?:default|model_provider):\s*['\"]?([\w.\-:/]+)['\"]?", s)
    if m2 and "/" in m2.group(1):
        referenced.add(m2.group(1))

print(f"\nconfig.yaml 引用的模型名（{len(referenced)} 个）：")
missing = []
for m in sorted(referenced):
    ok = m in live
    # provider:model 形式只看后半段
    short = m.split(":")[-1]
    ok2 = short in live
    mark = "✅" if (ok or ok2) else "❓"
    if not (ok or ok2):
        missing.append(m)
    print(f"   {mark} {m}")

print(f"\n不在网关在线列表里的：{missing if missing else '（无）'}")
print("（注：❓ 也可能属于非 opencode 的 provider，如 deepseek 官方 / anthropic，需人工确认）")
