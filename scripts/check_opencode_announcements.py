#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""抓 OpenCode 各公告/文档页，找 1017 或 DeepSeek 版本说明（fresh curl，不用 web_extract 缓存）。"""
import os
import re
import ssl
import sys
import html
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
PROXY = "http://127.0.0.1:10808"
CTX = ssl.create_default_context()
OP = urllib.request.build_opener(
    urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}),
    urllib.request.HTTPSHandler(context=CTX))

URLS = [
    "https://opencode.ai/changelog",
    "https://opencode.ai/blog",
    "https://opencode.ai/docs",
    "https://opencode.ai/notes",
    "https://anomalyco.dev/notes",
    "https://opencode.ai/docs/go",
]


def fetch(u):
    req = urllib.request.Request(u, headers={"User-Agent": "curl/8.0.0"})
    r = OP.open(req, timeout=45)
    return r.geturl(), r.read().decode("utf-8", "replace")


def plain(t):
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", t, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    return re.sub(r"\s+", " ", t)


for u in URLS:
    try:
        final, raw = fetch(u)
    except Exception as e:
        print(f"=== {u}  ❌ {type(e).__name__}: {str(e)[:90]}")
        continue
    print(f"\n{'='*70}\n=== {u}  ({len(raw)}B)  final={final}\n{'='*70}")
    txt = plain(raw)
    hits = 0
    # 找 1017 及其上下文
    for m in re.finditer(r"1017", txt):
        s, e = max(0, m.start() - 200), min(len(txt), m.end() + 200)
        print(f"  [1017] …{txt[s:e]}…")
        hits += 1
        if hits >= 3:
            break
    for m in re.finditer(r"DeepSeek", txt, re.I):
        s, e = max(0, m.start() - 150), min(len(txt), m.end() + 250)
        print(f"  [DeepSeek] …{txt[s:e]}…")
        hits += 1
        if hits >= 6:
            break
    if not hits:
        print("  （无 1017 / DeepSeek 相关内容）")
