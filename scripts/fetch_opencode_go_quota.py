#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""完整抓取 OpenCode Go 全部模型的 价格 / 月额度 / 估算请求数（fresh curl，不用缓存）。

输出三张表：
  A. 价格 + 月度额度（Go 档 / Go Plus 档）
  B. 估算请求数（5h / 周 / 月）
"""
import re
import ssl
import sys
import html
import json
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
PROXY = "http://127.0.0.1:10808"
CTX = ssl.create_default_context()
OP = urllib.request.build_opener(
    urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}),
    urllib.request.HTTPSHandler(context=CTX))

r = OP.open(urllib.request.Request("https://opencode.ai/docs/go",
                                   headers={"User-Agent": "curl/8.0.0"}), timeout=60)
raw = r.read().decode("utf-8", "replace")
print("页面字节:", len(raw))


def cells(row_html):
    out = []
    for m in re.finditer(r"<t[dh][^>]*>(.*?)</t[dh]>", row_html, re.S):
        v = html.unescape(re.sub(r"<[^>]+>", " ", m.group(1)))
        out.append(re.sub(r"\s+", " ", v).strip())
    return out


tables = []
for tm in re.finditer(r"<table[^>]*>(.*?)</table>", raw, re.S):
    body = tm.group(1)
    rows = [cells(rm.group(1)) for rm in re.finditer(r"<tr[^>]*>(.*?)</tr>", body, re.S)]
    rows = [r for r in rows if r]
    if rows:
        tables.append(rows)

print(f"共解析到 {len(tables)} 张表\n")

for i, rows in enumerate(tables, 1):
    print("=" * 78)
    print(f"表 {i}  （{len(rows)} 行 × {len(rows[0])} 列）")
    print("=" * 78)
    for row in rows:
        print("  | " + " | ".join(c[:30] for c in row))
    print()

# 汇总成结构化 JSON 落盘，供后续核算用
out = {"fetched_tables": tables}
p = "C:/Users/Administrator/AppData/Local/hermes/cache/opencode_go_tables.json"
with open(p, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("已落盘:", p)
