#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""从 AA 页面内嵌 JSON 精确提取指定模型的 AutomationBench-AA 与各分项分数。"""
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
FIELDS = ["intelligenceIndex", "automationBenchPartialScore",
          "terminalBench40", "scicode", "aime25", "gpqa",
          "briefcase", "gdpval", "omniscience", "lcr", "critpt"]

r = OP.open(urllib.request.Request(
    URL, headers={"User-Agent": "Mozilla/5.0 (compatible; hermes-agent/0.21.0)"}), timeout=90)
raw = r.read().decode("utf-8", "replace")

blobs = []
for m in re.finditer(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', raw, re.S):
    blobs.append(m.group(1))
for m in re.finditer(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', raw, re.S):
    blobs.append(m.group(1).encode().decode("unicode_escape", "replace"))

# 逐个模型对象提取：找 "name":"XXX" 到最近的 automationBenchPartialScore
records = {}
for blob in blobs:
    for m in re.finditer(r'"name":"([^"]{2,60})"', blob):
        name = m.group(1)
        seg = blob[m.start(): m.start() + 4000]
        ab = re.search(r'"automationBenchPartialScore":([0-9.]+)', seg)
        ii = re.search(r'"intelligenceIndex":([0-9.]+)', seg)
        if ab:
            rec = records.setdefault(name, {})
            rec["automationBench"] = round(float(ab.group(1)) * 100, 1)
            if ii:
                rec["intelligence"] = round(float(ii.group(1)), 1)
            br = re.search(r'"automationBenchBreakdown":\{([^}]*)\}', seg)
            if br:
                for k, v in re.findall(r'"(\w+)":([0-9.]+)', br.group(1)):
                    rec.setdefault("breakdown", {})[k] = round(float(v) * 100, 1)

TARGETS = ["DeepSeek V4.1 Flash", "GLM-5.3-Flash", "GLM-5.3", "MiMo-V2.6-Flash",
           "MiMo-V2.6-Pro", "LongCat-2.0", "Hy3", "Qwen3.8 Flash", "Qwen3.8 Max",
           "Kimi K3", "GPT 6 Luna", "Claude Haiku 5.5", "DeepSeek V4 Pro",
           "Step 5", "Muse Spark 1.3", "Gemini 4 Argon", "GPT 5.6 Luna"]

print(f"共解析到 {len(records)} 个模型的 AutomationBench 记录\n")
print(f"{'模型':<30}{'总分':>7}{'AutoBench':>11}{'严格分':>9}{'完成度':>9}")
print("-" * 70)
rows = []
for name, rec in records.items():
    if not any(t.lower() in name.lower() for t in TARGETS):
        continue
    bd = rec.get("breakdown", {})
    rows.append((name, rec.get("intelligence"), rec["automationBench"],
                 bd.get("strictScore"), bd.get("completion")))
rows.sort(key=lambda x: -(x[2] or 0))
for n, ii, ab, ss, cp in rows:
    print(f"{n[:29]:<30}{ii if ii else '-':>7}{ab:>11}{ss if ss else '-':>9}{cp if cp else '-':>9}")

print("\n（AutomationBench 定义：任务目标完成率 × 未触发违规。Zapier 开发，AA 独立测。）")
