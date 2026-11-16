#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""校验方案/餐次档案：每个食材行回源重算 + 合计行对逐项和。

用法：
    python verify_plan_tables.py <档案绝对路径>

数据源（按优先级）：~/health/fooddb/foods.json -> official_extra.json -> boohee_api/cache.json

判定：
  - 逐项差异 > max(5%, 0.11)          => ERROR
  - 逐项和 vs 合计行 > max(1%, 1.0)   => ERROR
  - 识别到的食材表里一行都没有        => ERROR（静默通过是历史踩过的坑）
  - 只认表头同时含「食材」「来源」的表：档案末尾的「一览表」不会被误当食材行

注意：
  - 「—」「**」「†」「‡」会被剥掉；「—」视为缺值，跳过比对、不当 0
  - 无 code 的行（包装标签 / 常量 / 生抽等）只参与加总，不参与回源比对

逻辑取自 2026-11-02/03 两次实跑通过的交互脚本：8 套早餐方案 62 行 0 处不符，
并正确复现「S8 一览表被误纳导致合计多 289.6 卡」这个解析陷阱。
"""
import json
import os
import re
import sys

DB = os.path.join(os.path.expanduser("~"), "health", "fooddb")
FIELDS = ("kcal", "protein", "fat", "cho", "fib", "na", "ca")
HEADER_ALIASES = {
    "kcal": ("热量", "能量"),
    "protein": ("蛋白",),
    "fat": ("脂肪",),
    "cho": ("碳水",),
    "fib": ("纤维",),
    "na": ("钠",),
    "ca": ("钙",),
    "purine": ("嘌呤",),
    "gram": ("克",),
}


def num(value):
    if value is None:
        return None
    text = str(value).replace("**", "").replace("*", "")
    for junk in ("†", "‡", "%"):
        text = text.replace(junk, "")
    text = text.strip()
    if text in ("", "—", "-", "–", "None", "nan", "null"):
        return None
    try:
        return float(text)
    except ValueError:
        return None


def load_sources():
    foods, extra, cache = {}, {}, {}
    path = os.path.join(DB, "foods.json")
    if os.path.exists(path):
        for row in json.load(open(path, encoding="utf-8")):
            foods[row.get("foodCode")] = row
    path = os.path.join(DB, "official_extra.json")
    if os.path.exists(path):
        for row in json.load(open(path, encoding="utf-8")):
            code = row.get("foodCode")
            if code:
                extra.setdefault(code, row)
    path = os.path.join(DB, "boohee_api", "cache.json")
    if os.path.exists(path):
        cache = json.load(open(path, encoding="utf-8"))
    return foods, extra, cache


def strip_unit(value):
    return num(re.sub(r"[A-Za-zμ]+", "", str(value)))


def per100(code, foods, extra, cache):
    """返回每 100 g 的 {kcal,protein,fat,cho,fib}；查不到返回 None。"""
    if code in foods:
        row = foods[code]
        return dict(kcal=num(row.get("energyKCal")), protein=num(row.get("protein")),
                    fat=num(row.get("fat")), cho=num(row.get("CHO")),
                    fib=num(row.get("dietaryFiber")))
    if code in extra:
        row = extra[code]
        return dict(kcal=strip_unit(row.get("energyKCal")), protein=strip_unit(row.get("protein")),
                    fat=strip_unit(row.get("fat")), cho=strip_unit(row.get("CHO")),
                    fib=strip_unit(row.get("dietaryFiber")))
    if code in cache:
        entry = cache[code]
        cal = {c.get("name_en"): c.get("value") for c in entry.get("calory", []) or []}
        base = {b.get("name_en"): b for b in entry.get("base_ingredients", []) or []}
        carbs = base.get("carbohydrate", {}) or {}
        fib = next((i.get("value") for i in carbs.get("items", []) or []
                    if i.get("name_en") == "fiber_dietary"), None)
        return dict(kcal=num(cal.get("total_calory")),
                    protein=num((base.get("protein") or {}).get("value")),
                    fat=num((base.get("fat") or {}).get("value")),
                    cho=num(carbs.get("value")), fib=num(fib))
    return None


def pick_code(source):
    match = re.search(r"OFFICIAL-\d+", source or "")
    if match:
        return match.group(0)
    for hit in re.finditer(r"`([^`]+)`", source or ""):
        code = hit.group(1).strip()
        if re.fullmatch(r"[0-9]{6}x?", code) or re.fullmatch(r"[a-z][a-z0-9_]*[0-9][a-z0-9_]*", code) \
                or re.fullmatch(r"[a-z]{4,}", code):
            return code
    return None


def column_map(header):
    mapping = {"source": None}
    for index, cell in enumerate(header):
        for name, aliases in HEADER_ALIASES.items():
            if name in mapping:
                continue
            if any(alias in cell for alias in aliases):
                mapping[name] = index
                break
        if "来源" in cell:
            mapping["source"] = index
    return mapping


def parse_tables(path):
    lines = open(path, encoding="utf-8").read().split("\n")
    tables, current, header = [], None, None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("|"):
            if current:
                tables.append(current)
            current, header = None, None
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if set("".join(cells)) <= set("-: "):
            continue
        if header is None:
            if "食材" in cells[0] and any("来源" in c for c in cells):
                header = cells
                current = {"line": index + 1, "cols": column_map(cells), "rows": [], "total": None}
            continue
        if "合计" in cells[0]:
            current["total"] = cells
            tables.append(current)
            current, header = None, None
            continue
        current["rows"].append((index + 1, cells))
    if current:
        tables.append(current)
    return tables


def main(path):
    if not os.path.exists(path):
        print("找不到档案：%s" % path)
        return 2
    foods, extra, cache = load_sources()
    tables = parse_tables(path)
    errors, warnings = [], []
    if not tables:
        print("❌ 没有识别到任何「食材 / 来源 / 克」表 —— 解析失败不是通过")
        return 1
    for table in tables:
        cols = table["cols"]
        if not table["rows"]:
            errors.append("第 %d 行起的表：识别到 0 行食材（表头在但行没解析出来）" % table["line"])
            continue
        sums = {f: 0.0 for f in FIELDS}
        seen = {f: False for f in FIELDS}
        for line_no, cells in table["rows"]:
            gram = num(cells[cols["gram"]]) if cols.get("gram") is not None and cols["gram"] < len(cells) else None
            source = cells[cols["source"]] if cols.get("source") is not None and cols["source"] < len(cells) else ""
            code = pick_code(source)
            row_per100 = per100(code, foods, extra, cache) if code else None
            for field in FIELDS:
                col = cols.get(field)
                if col is None or col >= len(cells):
                    continue
                value = num(cells[col])
                if value is None:
                    continue
                sums[field] += value
                seen[field] = True
                if row_per100 is None or gram is None:
                    continue
                base = row_per100.get(field)
                if base is None:
                    continue
                expect = base * gram / 100.0
                if abs(value - expect) > max(0.05 * abs(expect), 0.11):
                    errors.append("第 %d 行 %s：表 %.2f vs 算 %.2f（code %s / %.1f g）"
                                  % (line_no, cells[0][:14], value, expect, code, gram))
            if code and row_per100 is None:
                warnings.append("第 %d 行 %s：code `%s` 在本地三库里都没有，未能回源"
                                % (line_no, cells[0][:14], code))
        if table["total"]:
            total_cells = table["total"]
            for field in FIELDS:
                col = cols.get(field)
                if col is None or col >= len(total_cells) or not seen[field]:
                    continue
                reported = num(total_cells[col])
                if reported is None:
                    continue
                if abs(reported - sums[field]) > max(0.01 * abs(sums[field]), 1.0):
                    errors.append("第 %d 行起的表：合计 %s = %.2f，逐项和 = %.2f"
                                  % (table["line"], field, reported, sums[field]))
        else:
            warnings.append("第 %d 行起的表：没有合计行" % table["line"])
    print("识别到 %d 张食材表" % len(tables))
    for message in warnings:
        print("⚠️  " + message)
    for message in errors:
        print("❌ " + message)
    if errors:
        print("\n结论：%d 处不一致，需修。" % len(errors))
        return 1
    print("\n结论：全部通过（逐项回源 + 合计加总）。")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
