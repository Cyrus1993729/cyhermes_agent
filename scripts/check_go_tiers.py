#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""核实 docs/go 里 DeepSeek 额度档 $80/$160/$240 对应的套餐表头。"""
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
r = OP.open(urllib.request.Request("https://opencode.ai/docs/go",
                                   headers={"User-Agent": "curl/8.0.0"}), timeout=45)
t = r.read().decode("utf-8", "replace")
t = re.sub(r"<script.*?</script>|<style.*?</style>", "", t, flags=re.S)
t = html.unescape(re.sub(r"<[^>]+>", " ", t))
t = re.sub(r"\s+", " ", t)

for m in re.finditer(r"DeepSeek V4\.1 Flash \(Off-Peak\)", t):
    s = max(0, m.start() - 900)
    print("=" * 72)
    print("…" + t[s:m.end() + 180] + "…\n")

print("=" * 72)
print("含 $10 / $40 / Go Plus / Go Max 的段落：")
for kw in ["Go Plus", "$10", "$40", "$80", "per month"]:
    for m in re.finditer(re.escape(kw), t):
        s = max(0, m.start() - 180)
        print(f"\n  [{kw}] …{t[s:m.end()+220]}…")
        break
