#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""从 Artificial Analysis 页面内嵌 JSON 里挖 AutomationBench-AA 分项分数。"""
import re
import ssl
import sys
import json
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
PROXY = "http://127.0.0.1:10808"
CTX = ssl.create_default_context()
OP = urllib.request.build_opener(
    urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}),
    urllib.request.HTTPSHandler(context=CTX))

URLS = [
    "https://artificialanalysis.ai/models/comparisons/glm-5-3-flash-vs-deepseek-v4-1-flash",
    "https://artificialanalysis.ai/evaluations/automationbench-aa",
]

WANT = ["deepseek", "glm-5.3-flash", "mimo-v2.6", "longcat", "hy3", "qwen3.8", "glm-5-3-flash"]

for u in URLS:
    print("=" * 74)
    print(u)
    print("=" * 74)
    try:
        r = OP.open(urllib.request.Request(
            u, headers={"User-Agent": "Mozilla/5.0 (compatible; hermes-agent/0.21.0)"}), timeout=60)
        raw = r.read().decode("utf-8", "replace")
    except Exception as e:
        print("  ❌", type(e).__name__, str(e)[:120])
        continue
    print(f"  HTML {len(raw)} 字节")

    # 找内嵌 JSON：__NEXT_DATA__ / self.__next_f.push / application/json
    blobs = []
    for m in re.finditer(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', raw, re.S):
        blobs.append(m.group(1))
    for m in re.finditer(r'__NEXT_DATA__[^>]*>(.*?)</script>', raw, re.S):
        blobs.append(m.group(1))
    for m in re.finditer(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', raw, re.S):
        blobs.append(m.group(1).encode().decode("unicode_escape", "replace"))
    print(f"  内嵌 JSON 块 {len(blobs)} 个，合计 {sum(len(b) for b in blobs):,} 字符")

    # 在 JSON 里找 automationbench 附近的键值
    joined = "\n".join(blobs)
    hits = 0
    for m in re.finditer(r"[Aa]utomation[^,\"]{0,40}", joined):
        s = max(0, m.start() - 400)
        seg = joined[s:m.end() + 500]
        nums = re.findall(r"\d+\.\d+", seg)
        names = [w for w in WANT if w in seg.lower()]
        if names and nums:
            print(f"\n  [命中] 模型线索={names} 数值样本={nums[:8]}")
            print(f"    …{seg[:500]}…")
            hits += 1
            if hits >= 4:
                break
    if not hits:
        # 退而求其次：直接找模型名 + 附近数值
        for w in ["deepseek-v4-1-flash", "glm-5-3-flash"]:
            for m in list(re.finditer(re.escape(w), joined, re.I))[:2]:
                s = max(0, m.start() - 300)
                print(f"\n  [{w}] …{joined[s:m.end()+600][:800]}…")
