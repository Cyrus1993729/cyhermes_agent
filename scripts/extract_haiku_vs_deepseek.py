#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""提取 Claude Haiku 5.5 的全部分项，并与 DeepSeek V4.1 Flash 对比。"""
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

URL = "https://artificialanalysis.ai/evaluations/automationbench-aa"
r = OP.open(urllib.request.Request(
    URL, headers={"User-Agent": "Mozilla/5.0 (compatible; hermes-agent/0.21.0)"}), timeout=90)
raw = r.read().decode("utf-8", "replace")

blobs = []
for m in re.finditer(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', raw, re.S):
    blobs.append(m.group(1))
for m in re.finditer(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', raw, re.S):
    blobs.append(m.group(1).encode().decode("unicode_escape", "replace"))

TARGETS = ["Claude Haiku 5.5", "DeepSeek V4.1 Flash 1017", "DeepSeek V4.1 Flash"]
found = {}
for blob in blobs:
    for m in re.finditer(r'"name":"([^"]{2,60})"', blob):
        name = m.group(1)
        if not any(name == t or name.startswith(t) for t in TARGETS):
            continue
        seg = blob[m.start(): m.start() + 6000]
        rec = {}
        for k in ["intelligenceIndex", "automationBenchPartialScore", "analystAgent",
                  "analystAgentPassAt1", "terminalBench40", "scicode", "critpt",
                  "briefcase", "gdpval", "omniscience", "lcr", "aime25"]:
            mm = re.search(rf'"{k}":([0-9.]+)', seg)
            if mm:
                rec[k] = float(mm.group(1))
        br = re.search(r'"automationBenchBreakdown":\{([^}]*)\}', seg)
        if br:
            rec["_breakdown"] = {k: round(float(v) * 100, 1)
                                 for k, v in re.findall(r'"(\w+)":([0-9.]+)', br.group(1))}
        if rec.get("automationBenchPartialScore"):
            found[name] = rec

print(f"命中 {len(found)} 条\n")
for name, rec in sorted(found.items()):
    print("=" * 60)
    print(name)
    print("=" * 60)
    ab = rec.get("automationBenchPartialScore")
    print(f"  AA Intelligence Index : {rec.get('intelligenceIndex')}")
    print(f"  AutomationBench       : {ab*100:.1f}%" if ab else "  AutomationBench : -")
    bd = rec.get("_breakdown", {})
    if bd:
        for k, v in bd.items():
            print(f"      {k:<12} {v}%")
    for k in ["terminalBench40", "scicode", "critpt", "briefcase", "gdpval", "omniscience", "lcr", "analystAgent"]:
        if k in rec and rec[k] is not None:
            v = rec[k]
            print(f"  {k:<22} {v*100:.1f}%" if v <= 1.5 else f"  {k:<22} {v}")
    print()
