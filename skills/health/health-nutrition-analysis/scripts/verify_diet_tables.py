#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""饮食档案 markdown 自校验 —— 逐列重算核对合计行 + 累计块核对 + 结构重复检查。

用途：写完 `diet/YYYY-MM-DD.md` 后，**从磁盘读回来**独立重算一遍，
确认每张表的逐项相加 == 合计行，防止手写/抄写/四舍五入引入的隐性错数。

💡 为什么必须读回文件而不是相信生成时的变量：
   归档是对外交付物，错在文件里比错在内存里严重。读回文件 = 验的就是用户看到的东西。

🔴 列数坑（2026-10-29 实踩）：
   最初按“第3列开始是数值”硬编码，结果把不同列数的表全判错：
     - 早餐表 = 10 列（含纤维）
     - 午餐表 =  9 列（无机酸/钙）
     - 全天汇总表 = 7 列，且数值从**第1列**开始（餐次|热量|...）
   硬编码导致“0 行被当成通过”和“全天表永远找不到合计”。
   ✅ 正确做法：**从表头找 `热量` 所在列号**，每张表各自定位，不跨表复用。

🔴 2026-11-16 新增两项（同天踩的）：
   ① **累计块核对**：早餐/午餐/加餐 各自的合计，加起来必须等于「截至 HH:MM 累计」那个代码块。
      取文件里**最后一个**累计块（一天会反复追加，第一个是过期的）。
   ② **结构重复检查**：同一 `##` 餐次章节内，三级标题 / 代码块 / 合计行都不能出现两次。
      实测健康助理会把「算术自检」代码块贴两遍（一带标题一不带），数值不影响但档案变两份算式。
      注意：**跨章节重名是正常的**（每餐都有自己的 `### 算术自检`），所以只在节内查，别全文查。

🔴 路径坑（2026-11-16）：这个脚本在 `skills/health/health-nutrition-analysis/scripts/` 下，
   跨 profile 派给健康助理时必须给**绝对路径**——它 cwd 在 `~/health`，跑相对路径 `scripts/xxx.py` 会报找不到，
   而它可能凭记忆把格式相似的「输出」写进回执。运行时副本：`~/health/tools/verify_diet_tables.py`。

用法：
    python verify_diet_tables.py C:/Users/Administrator/health/diet/2026-10-29.md
    python verify_diet_tables.py <file> --strict   # 有任何不匹配就 exit 1

退出码：0 全部一致 / 1 有不一致（仅 --strict 下）；无表格时 exit 2。
"""
import re
import sys
import collections
from pathlib import Path

TOL = 0.06  # 显示精度容差（两位小数四舍五入后的最大偏差）


def _cells(line):
    """把 markdown 表格行拆成单元格，去掉加粗与脚注符号。"""
    s = line.strip()
    if not s.startswith("|"):
        return None
    raw = s.strip("|").split("|")
    return [c.strip().replace("**", "").replace("†", "").replace("‡", "").replace("※", "") for c in raw]


def _is_sep(cells):
    return all(set(c) <= set("-: ") and c for c in cells)


def _num(x):
    try:
        return float(str(x).replace("**", "").replace("†", "").replace("‡", "").replace("※", "").strip())
    except (TypeError, ValueError):
        return None


NUMERIC_HINTS = {"热量", "蛋白", "脂肪", "碳水", "碳水(净)", "纤维", "钠", "嘌呤", "糖", "钙",
                 "毛消耗", "净增", "克", "克（可食部）", "用量"}


def check_table(header, rows, total_row):
    """header/rows/total_row 均为 cells 列表。返回 (ok, detail)。

    🔴 2026-10-31 修：原版「一列里只要有一个非数值单元格就整行跳过」，
    遇到新增的 `来源` 文本列（skill 现在强制每样食物标来源）会**整表被判无效**，
    表被静默跳过、看起来像"没有表"。改为**按列判断**：
      - 该列所有行都是数值 → 参与求和比对
      - 该列有非数值单元格 → 只有表头属于 NUMERIC_HINTS 时才报错（防手滑写错一个格），
        否则视为文本列（来源/备注/标记）直接跳过
    """
    if "热量" not in header:
        return None, "表头无「热量」列，跳过"
    start = header.index("热量")
    n = len(header) - start

    sums = {}
    bad = []
    for k in range(n):
        name = header[start + k]
        vals = [_num(r[start + k]) if start + k < len(r) else None for r in rows]
        miss = sum(1 for v in vals if v is None)
        if miss == 0:
            sums[k] = sum(vals)
        elif name in NUMERIC_HINTS:
            bad.append(f"{name}: 有 {miss}/{len(rows)} 行不是数值（疑似写错格或列数错位）")
    counted = len(rows)

    if not counted:
        return None, "无有效数据行（疑似列数判断错误）"

    filed = [_num(x) for x in total_row[start:start + n]]
    for k, s in sums.items():
        name = header[start + k]
        b = filed[k] if k < len(filed) else None
        if b is None:
            if name not in NUMERIC_HINTS:
                continue          # 比例/密度这类不可加列，合计行写「—」是正常的
            bad.append(f"{name}: 合计行非数值（{total_row[start + k] if start + k < len(total_row) else '缺列'!r}）")
        elif abs(s - b) > TOL:
            bad.append(f"{name}: 重算 {s:.2f} vs 合计 {b:.2f}（差 {s - b:+.2f}）")
    return (not bad), {"cols": n, "rows": counted, "numeric_cols": len(sums),
                       "sums": [round(sums[k], 2) for k in sorted(sums)], "bad": bad}


def scan(path):
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    section = "(文首)"
    results = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("## "):
            section = line[3:].strip()
        cells = _cells(line)
        if cells and i + 1 < len(lines):
            nxt = _cells(lines[i + 1])
            if nxt and _is_sep(nxt):
                header = cells
                rows, total = [], None
                j = i + 2
                while j < len(lines):
                    c = _cells(lines[j])
                    if not c:
                        break
                    key = c[0].replace("**", "")
                    if key in ("合计", "全天合计"):
                        total = c
                    elif key and not _is_sep(c):
                        rows.append(c)
                    j += 1
                if total is not None and rows:
                    ok, detail = check_table(header, rows, total)
                    if ok is not None:
                        results.append((section, header[0], ok, detail))
                i = j
                continue
        i += 1
    return results


def check_accumulate(text):
    """累计块核对：各餐合计之和 == 「累计」行。取文件里最后一个累计块。"""
    blocks = re.findall(r"```(.*?)```", text, re.S)
    block = None
    for b in reversed(blocks):
        if "累计" in b and re.search(r"(?m)^\s*(早餐|午餐)", b):
            block = b
            break
    if block is None:
        return None
    rows = {}
    for line in block.strip().splitlines():
        m = re.match(r"^(早餐|午餐|加餐|夜宵|累计)\s+(.*)$", line.strip())
        if not m:
            continue
        rows[m.group(1)] = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)", m.group(2))]
    if "累计" not in rows:
        return None
    meals = [k for k in ("早餐", "午餐", "加餐", "夜宵") if k in rows]
    bad = []
    for idx, v in enumerate(rows["累计"]):
        s = sum(rows[k][idx] for k in meals if idx < len(rows[k]))
        if abs(round(s, 2) - v) > 0.011:
            bad.append(f"第{idx + 1}项: 各餐和 {s:.2f} vs 累计 {v:.2f}")
    return {"ok": not bad, "bad": bad, "meals": meals}


def check_dup(text):
    """结构重复：只在同一 ## 章节内查（跨章节重名是正常的）。"""
    dup_h, dup_b, dup_t = [], [], []
    for sec in re.split(r"(?m)^##\s", text)[1:]:
        name = sec.split("\n", 1)[0].strip()
        heads = [l.strip() for l in sec.splitlines() if re.match(r"^###\s", l.strip())]
        for h, n in collections.Counter(heads).items():
            if n > 1:
                dup_h.append(f"{name} / {h} x{n}")
        blocks = [b.strip() for b in re.findall(r"```(.*?)```", sec, re.S) if b.strip()]
        for b, n in collections.Counter(blocks).items():
            if n > 1:
                dup_b.append(f"{name} / 「{b.splitlines()[0][:30]}…」x{n}")
        tt = [l.strip() for l in sec.splitlines() if "**合计**" in l]
        for t, n in collections.Counter(tt).items():
            if n > 1:
                dup_t.append(f"{name} / 合计行 x{n}")
    return {"ok": not (dup_h or dup_b or dup_t), "head": dup_h, "block": dup_b, "total": dup_t}


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    path = sys.argv[1]
    strict = "--strict" in sys.argv
    text = Path(path).read_text(encoding="utf-8")
    res = scan(path)
    if not res:
        print(f"⚠️  {path} 里没找到带合计行的表格")
        return 2

    fails = 0
    print(f"检查 {path}\n" + "=" * 66)
    for section, first_col, ok, detail in res:
        mark = "✓" if ok else "✗"
        if not ok:
            fails += 1
        if isinstance(detail, dict):
            print(f"[{mark}] {section}｜{detail['rows']}行/{detail['cols']}列")
            print(f"     重算 {detail['sums']}")
            for b in detail["bad"]:
                print(f"     ❌ {b}")
        else:
            print(f"[?] {section}｜{detail}")
    print("=" * 66)
    print(f"{len(res)} 张表 / {fails} 张不一致" if fails else f"{len(res)} 张表全部一致 ✓")

    acc = check_accumulate(text)
    if acc is not None:
        if acc["ok"]:
            print(f"累计块（{'+'.join(acc['meals'])} 相加）一致 ✓")
        else:
            fails += 1
            print("累计块不一致 ✗")
            for b in acc["bad"]:
                print(f"     ❌ {b}")

    dup = check_dup(text)
    if dup["ok"]:
        print("结构重复检查：无重复 ✓")
    else:
        fails += 1
        print("结构重复检查：有重复 ✗")
        for k, label in (("head", "标题"), ("block", "代码块"), ("total", "合计行")):
            for d in dup[k]:
                print(f"     ❌ 重复{label}：{d}")

    print("=" * 66)
    print("总计：" + ("ALL PASS" if not fails else "FAIL"))
    if fails and strict:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
