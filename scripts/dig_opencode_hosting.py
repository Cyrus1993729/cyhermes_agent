#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""挖 docs/go 的 ZDR 脚注（星号说明）+ changelog 到底记了什么。"""
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


def fetch(u):
    r = OP.open(urllib.request.Request(u, headers={"User-Agent": "curl/8.0.0"}), timeout=45)
    return r.read().decode("utf-8", "replace")


def plain(t):
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", t, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    return re.sub(r"\s+", " ", t)


print("=" * 72)
print("① docs/go —— 托管 / 中国 / ZDR 星号 相关内容")
print("=" * 72)
txt = plain(fetch("https://opencode.ai/docs/go"))
for kw in ["hosted in China", "China", "ZDR", "*", "proxy", "upstream", "provider"]:
    pass
# 星号脚注
for m in re.finditer(r"\*[^ ]", txt):
    s, e = max(0, m.start() - 120), min(len(txt), m.end() + 400)
    seg = txt[s:e]
    if "DeepSeek" in seg or "ZDR" in seg or "retention" in seg.lower():
        print(f"\n  [脚注候选] …{seg}…")
# China 相关
seen = set()
for m in re.finditer(r"China", txt):
    s, e = max(0, m.start() - 200), min(len(txt), m.end() + 300)
    seg = txt[s:e]
    k = seg[:60]
    if k in seen:
        continue
    seen.add(k)
    print(f"\n  [China] …{seg}…")
    if len(seen) >= 3:
        break

print("\n\n" + "=" * 72)
print("② changelog —— 页面结构 / 最近几条标题")
print("=" * 72)
cl = plain(fetch("https://opencode.ai/changelog"))
print("  正文字数:", len(cl))
for kw in ["model", "Model", "provider", "Provider", "deepseek", "DeepSeek"]:
    n = len(re.findall(kw, cl))
    if n:
        print(f"  含「{kw}」: {n} 次")
for m in re.finditer(r"(model|provider)", cl, re.I):
    s, e = max(0, m.start() - 150), min(len(cl), m.end() + 200)
    print(f"\n  …{cl[s:e]}…")
    break
print("\n  开头 800 字：")
print("  " + cl[:800])
