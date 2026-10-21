#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""独立核对健康助理说的「午餐A已删、小酥肉改100g、已存档」是否属实。"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
p = os.path.join(os.path.expanduser("~"), "health", "diet", "2026-10-20.md")
t = open(p, encoding="utf-8").read()

print(f"文件: {p}")
print(f"大小: {os.path.getsize(p):,} 字节 / {len(t.splitlines())} 行\n")

print("=== 午餐 A 残留检查 ===")
for k in ["清炒菠菜", "番茄炒蛋", "午餐 A", "午餐A", "待确认", "308"]:
    n = t.count(k)
    print(f"  {k:<10} {n} 处  {'✅' if n == 0 else '❌ 仍有残留'}")

print("\n=== 小酥肉 ===")
for i, ln in enumerate(t.splitlines(), 1):
    if "小酥肉" in ln:
        print(f"  {i}: {ln.strip()[:150]}")

print("\n=== 全天/合计行 ===")
for i, ln in enumerate(t.splitlines(), 1):
    if any(k in ln for k in ("全天合计", "全天累计", "累计")):
        print(f"  {i}: {ln.strip()[:170]}")

print("\n=== 数据质量提示 ===")
idx = t.find("数据质量")
print("  " + (t[idx:idx + 700].replace("\n", "\n  ") if idx >= 0 else "❌ 没找到"))
