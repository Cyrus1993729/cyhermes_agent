#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""最终核对：额度更新是否全部落到位。"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
H = os.path.join(os.path.expanduser("~"), "AppData", "Local", "hermes")

uw = os.path.join(H, "scripts", "usage_watch.py")
newref = os.path.join(H, "skills", "software-development", "hermes-china-providers",
                      "references", "opencode-go-full-quota-table-2026-10-20.md")
skill = os.path.join(H, "skills", "software-development", "hermes-china-providers", "SKILL.md")
oldref = os.path.join(H, "skills", "research", "model-subscription-evaluation",
                      "references", "opencode-go-2026-08.md")

t = open(uw, encoding="utf-8").read()
m = re.search(r"MONTHLY_USD = ([0-9.]+)", t)
print(f"① usage_watch.py MONTHLY_USD = {m.group(1) if m else '❌未找到'}")

sz = os.path.getsize(newref)
n = sum(1 for ln in open(newref, encoding="utf-8") if ln.startswith("| "))
print(f"② 新参考表 {sz:,} 字节，表格行 {n} 行")

s = open(skill, encoding="utf-8").read()
print(f"③ skill 正文「额度现况（2026-10-20）」: {s.count('额度现况（2026-10-20')} 处")
print(f"   含 '$80' 的次数: {s.count('$80')}")

o = open(oldref, encoding="utf-8").read()
print(f"④ 旧参考文件横幅: {o.count('历史快照')} 处")

# 扫全库残留未标注的旧额度陈述
bad = []
for root, _, files in os.walk(os.path.join(H, "skills")):
    for f in files:
        if not f.endswith(".md"):
            continue
        p = os.path.join(root, f)
        try:
            txt = open(p, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        for i, line in enumerate(txt.splitlines(), 1):
            if "月额度 $30" in line or "$30 档" in line:
                if any(k in line for k in ("历史", "作废", "后续", "旧版", "过时")):
                    continue
                bad.append(f"{os.path.relpath(p, H)}:{i}: {line.strip()[:110]}")

print(f"\n⑤ 仍存在未标注的旧额度陈述: {len(bad)} 条")
for b in bad[:8]:
    print("   ", b)
