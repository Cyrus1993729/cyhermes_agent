#!/usr/bin/env python
"""校验饮食档案 markdown 表格：逐项相加之各列，是否等于「合计」行。

用途
----
饮食档案里的每个餐次都是一张 markdown 表：原料行 + 一行「合计」。
用户会核对，合计对不上就是事故。手写校验脚本很容易排错列（本次实测
就因为把表头列数数错、以及用 startswith("| 午餐") 误匹配到百分比表，
连错两次）。所以固定成脚本。

用法
----
python verify_diet_table.py C:/Users/Administrator/health/diet/2026-10-29.md
python verify_diet_table.py <文件> --quiet   # 只输出失败项

退出码
------
0 = 所有表都对得上；1 = 有表对不上（或解析不到合计行）。

设计要点（改脚本前先读）
--------------------
1. **不靠固定列下标**。按「合计行里该列能不能解析成数字」来判数值列，
   这样营养表（10/11 列）和全天汇总表（7 列）都能用同一套逻辑。
2. **合计行不靠 startswith 匹配**。先把表格块切出来，再在块内找首列
   等于 合计/全天合计 的行——避免误碰到正文里以「| 午餐」开头的百分比表。
3. 容差 0.06：允许两位小数四舍五入带来的尾差（钠那类 839.01 vs 839.0）。
4. † ‡ * 等脚注标记先剔掉再转数字。
"""
import re
import sys

TOL = 0.06
TOTAL_NAMES = ("合计", "全天合计", "总计")


def cells(line):
    return [c.strip().replace("**", "") for c in line.strip().strip("|").split("|")]


def to_num(x):
    if x is None:
        return None
    x = re.sub(r"[†‡*※,]", "", str(x)).strip()
    x = x.replace("--", "").replace("—", "")
    if not x:
        return None
    try:
        return float(x)
    except ValueError:
        return None


def is_sep(row):
    return bool(row) and all(set(c) <= set("-: ") for c in row if c) and any(c for c in row)


def table_blocks(lines):
    """把连续的 | 开头行切成表块。"""
    block, blocks = [], []
    for line in lines:
        if line.lstrip().startswith("|"):
            block.append(line)
        else:
            if len(block) >= 2:
                blocks.append(block)
            block = []
    if len(block) >= 2:
        blocks.append(block)
    return blocks


def check_block(block):
    rows = [cells(l) for l in block]
    total_i = None
    for i, r in enumerate(rows):
        if r and r[0] in TOTAL_NAMES:
            total_i = i
    if total_i is None:
        return None
    header, total = rows[0], rows[total_i]
    data = [r for r in rows[1:total_i] if not is_sep(r)]
    if not data:
        return None

    out = []
    for c in range(1, len(total)):
        tv = to_num(total[c])
        if tv is None:
            continue
        vals = [v for v in (to_num(r[c]) for r in data if c < len(r)) if v is not None]
        if not vals:
            continue
        s = round(sum(vals), 2)
        name = header[c] if c < len(header) else "col%d" % c
        out.append((name, s, tv, abs(s - tv) <= TOL, len(vals)))
    return out


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    path = sys.argv[1]
    quiet = "--quiet" in sys.argv

    with open(path, encoding="utf-8") as f:
        text = f.read()

    # 按 ## 分节，保留节名做报错定位
    chunks, name = [], "(文件头)"
    for line in text.splitlines():
        if line.startswith("## "):
            name = line[3:].strip()
            continue
        chunks.append((name, line))

    sections, cur, cur_name = [], [], chunks[0][0] if chunks else ""
    for nm, line in chunks:
        if nm != cur_name:
            sections.append((cur_name, cur))
            cur, cur_name = [], nm
        cur.append(line)
    if cur:
        sections.append((cur_name, cur))

    checked = failed = 0
    for nm, lines in sections:
        for bi, block in enumerate(table_blocks(lines)):
            res = check_block(block)
            if not res:
                continue
            checked += 1
            bad = [r for r in res if not r[3]]
            label = "%s #%d" % (nm[:28], bi + 1)
            if bad:
                failed += 1
                print("FAIL  %s" % label)
                for name_, s, tv, _ok, n in bad:
                    print("        %-6s 逐项和=%-9.2f 合计行=%-9.2f 差=%+.2f (n=%d)"
                          % (name_, s, tv, s - tv, n))
            elif not quiet:
                print("ok    %-30s %d 列全部对平" % (label, len(res)))

    # 全天汇总表单独再核一次：它只有 6 列且首列是餐次名
    print("\n检查了 %d 张表，失败 %d 张" % (checked, failed))
    return 0 if failed == 0 and checked > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
