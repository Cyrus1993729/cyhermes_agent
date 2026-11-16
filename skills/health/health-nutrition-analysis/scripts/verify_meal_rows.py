#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""逐项复核饮食档案：每行 = 每100g 值 × 克数；合计行 = 逐项和。

用途：健康助理产出档案后，主 Hermes 独立复核（它的自述不算验证）。
与 verify_diet_tables.py 的分工：
  - verify_diet_tables.py  → 只核「合计 = 逐项相加」
  - 本脚本                 → 另加「逐项数值 vs 本地来源库」这一层

用法:
    python verify_meal_rows.py <档案绝对路径.md> [--section 午餐]

退出码: 0=全部通过 / 1=有偏差 / 2=解析到 0 行(判异常，不要当通过)

🔴 三个必须知道的坑：
1. 档案末尾常有「一览（挑的时候看这张）」这类**汇总表**，列数比明细表少（无「克」列）。
   如果按「遇到下一个 #### 标题才换块」的写法解析，汇总表会被算进最后一套（实测 S8 出现 −289.6 卡的假偏差）。
   → 本脚本只接受**列数 ≥ 9 且第 3 列像克数**的表；汇总表自动跳过。
2. 薄荷 `public_detail` / cache **没有 calcium 字段**（返回 None）。
   档案里的钙多半取自《中国食物成分表》同码条目，别把 Ca=None 当成「数据错」或「未填」。本脚本跳过钙列比对。
3. 薄荷返回是 **tuple**：`r = public_detail(code); d = r[0] if isinstance(r, tuple) else r`。
   直接 `.get()` 会 AttributeError。
"""
import sys, os, re, json, math

HOME = os.path.expanduser("~")
DB = os.path.join(HOME, "health", "fooddb")

def load_sources():
    idx = {}
    for fn, key in (("foods.json", "foodCode"), ("official_extra.json", "foodCode")):
        p = os.path.join(DB, fn)
        if not os.path.exists(p):
            continue
        data = json.load(open(p, encoding="utf-8"))
        for x in data:
            c = x.get(key)
            if c:
                idx.setdefault(c, x)
    cache_p = os.path.join(DB, "boohee_api", "cache.json")
    cache = json.load(open(cache_p, encoding="utf-8")) if os.path.exists(cache_p) else {}
    return idx, cache

def num(s):
    try:
        return float(str(s).replace("**", "").replace("—", "").replace(",", ""))
    except Exception:
        return float("nan")

def boohee_per100(cache, code):
    """薄荷 cache 是每100g。取不到钙(薄荷无此字段)，返 None。"""
    if code not in cache:
        return None
    e = cache[code]
    cal = {c.get("name_en"): c.get("value") for c in e.get("calory", [])}
    bi = {b.get("name_en"): b for b in e.get("base_ingredients", [])}
    ch = bi.get("carbohydrate", {}) or {}
    fib = None
    for it in ch.get("items", []) or []:
        if it.get("name_en") == "fiber_dietary":
            fib = it.get("value")
    def f(v):
        try:
            return float(v)
        except Exception:
            return None
    return dict(kcal=f(cal.get("total_calory")),
                protein=f((bi.get("protein") or {}).get("value")),
                fat=f((bi.get("fat") or {}).get("value")),
                cho=f(ch.get("value")), fib=f(fib))

COLS = ("kcal", "protein", "fat", "cho", "fib")

def parse_tables(text):
    """返回 [(section, [cells...])]，只收字段表。"""
    rows, cur = [], None
    for line in text.splitlines():
        m = re.match(r"^#{2,5}\s*(.+)$", line)
        if m:
            cur = m.group(1).strip()
            continue
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 9:
            continue                      # 汇总表/一览表，跳过（坑 1）
        if set(cells[0]) <= set("-: "):
            continue
        if num(cells[2]) != num(cells[2]):   # 第3列不是数 → 表头
            continue
        rows.append((cur, cells))
    return rows

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    path = sys.argv[1]
    only = None
    if "--section" in sys.argv:
        only = sys.argv[sys.argv.index("--section") + 1]
    text = open(path, encoding="utf-8").read()
    idx, cache = load_sources()
    rows = parse_tables(text)
    if not rows:
        print("❌ 解析到 0 行 —— 判异常，不要当成通过")
        return 2

    bad, tot = [], {}
    for section, cells in rows:
        if only and only not in (section or ""):
            continue
        name, src, gram = cells[0], cells[1], num(cells[2])
        rep = [num(cells[i]) for i in range(3, 8)]
        if name.startswith("**合计**"):
            tot.setdefault(section, {})["合计"] = rep
            continue
        tot.setdefault(section, {})["sum"] = tot.setdefault(section, {}).get("sum", [0.0] * 5)
        for i, v in enumerate(rep):
            if v == v:
                tot[section]["sum"][i] += v
        m = re.search(r"OFFICIAL-\d+|`([0-9]{6}x?)`|`([a-z0-9_]+)`", src)
        code = m.group(0).strip("`") if m else None
        per = None
        if code and code in idx:
            x = idx[code]
            per = dict(kcal=num(x.get("energyKCal")), protein=num(x.get("protein")),
                       fat=num(x.get("fat")), cho=num(x.get("CHO")), fib=num(x.get("dietaryFiber")))
        elif code:
            per = boohee_per100(cache, code)
        if not per or gram != gram:
            continue                      # 常量估算/包装标签 → 无从复核，跳过
        for i, k in enumerate(COLS):
            exp, got = per.get(k), rep[i]
            if exp is None or exp != exp or got != got:
                continue
            exp *= gram / 100.0
            if abs(exp - got) > max(0.05 * abs(exp), 0.11):
                bad.append((section, name[:18], k, got, round(exp, 2)))

    for s, d in tot.items():
        if "合计" not in d or "sum" not in d:
            continue
        diff = [round(a - b, 2) for a, b in zip(d["合计"], d["sum"])]
        flag = "✅" if all(abs(x) <= 0.15 for x in diff) else "❌"
        print(f"{flag} {s} 合计[{'/'.join(f'{x:.2f}' for x in d['合计'])}] 逐项和[{'/'.join(f'{x:.2f}' for x in d['sum'])}] 差{diff}")

    if bad:
        print("\n❌ 逐项与来源库不符:")
        for b in bad:
            print("   ", b)
        return 1
    print("\n✅ 逐项数值与来源库一致（跳过的行=常量估算/包装标签，属预期）")
    return 0

if __name__ == "__main__":
    sys.exit(main())
