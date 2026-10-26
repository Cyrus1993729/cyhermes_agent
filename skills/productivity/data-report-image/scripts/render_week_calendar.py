#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""周日程图 HTML 生成器。

用法：
    python render_week_calendar.py --start 2026-10-26 --days 7 --out C:/tmp/week_cal.html
    python render_week_calendar.py --start 2026-10-26 --items-json items.json --out C:/tmp/week_cal.html

不给 --items-json 时默认从 Dayflow 客户端拉（路径见 NODE/APP 常量）。
只生成 HTML，截图交给浏览器 CDP（见 SKILL.md / references）。

设计形式是用户 2026-10-25 认可过的版本，改样式前先问。
"""
import argparse
import html
import json
import os
import subprocess
from datetime import date, timedelta

NODE = "C:/Users/Administrator/AppData/Local/DayflowHome/tools/node24/node.exe"
APP = ("C:/Users/Administrator/AppData/Local/DayflowHome/releases/"
       "sites29-afdf902-home1/deployment/home.mjs")

WD = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
COLORS = {
    "work": ("#3b82f6", "#eff6ff"),
    "sport": ("#f97316", "#fff7ed"),
    "side": ("#a855f7", "#faf5ff"),
    "life": ("#14b8a6", "#f0fdfa"),
}
LEFT, COLW, PX_H = 90, 200, 56
MIN_BLOCK_H = 50  # 短事项块最小高度，否则标题被裁切


def fetch_items():
    out = subprocess.run([NODE, APP, "client", "items"], capture_output=True,
                         text=True, encoding="utf-8", timeout=120)
    for line in (out.stdout or "").splitlines():
        line = line.strip()
        if line.startswith("["):
            try:
                return json.loads(line)
            except ValueError:
                continue
    raise SystemExit("拿不到 client items 输出：" + (out.stdout or "")[:300]
                     + (out.stderr or "")[:300])


def hm(s):
    h, m = s.split(":")
    return int(h) + int(m) / 60


def is_allday(it):
    return bool(it.get("allDay")) or bool(it.get("endDate") and not it.get("start"))


def build(rows, week, subtitle):
    allday = [i for i in rows if is_allday(i)]
    timed = [i for i in rows if not is_allday(i) and i.get("start") and i.get("end")]

    if timed:
        lo = min(hm(i["start"]) for i in timed)
        hi = max(hm(i["end"]) for i in timed)
        start_h, end_h = max(0, int(lo)), min(24, int(-(-hi // 1)))
    else:
        start_h, end_h = 8, 20
    if end_h - start_h < 6:
        end_h = min(24, start_h + 6)

    lane_h = 56 if allday else 0
    grid_top = 150 + lane_h
    gh = (end_h - start_h) * PX_H
    W = LEFT + COLW * 7 + 30
    H = grid_top + gh + 110

    p = [f'''<!doctype html><html><head><meta charset="utf-8"><style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{width:{W}px;height:{H}px;background:#f8fafc;font-family:"Microsoft YaHei","Segoe UI",sans-serif;color:#0f172a;overflow:hidden}}
.hd{{padding:24px 30px 12px}} .hd h1{{font-size:34px;font-weight:800}}
.hd .sub{{font-size:16px;color:#64748b;margin-top:6px}}
.wrap{{position:relative;margin:0 15px;background:#fff;border-radius:14px;box-shadow:0 2px 14px rgba(15,23,42,.08);overflow:hidden}}
.wdrow{{display:flex;height:58px;border-bottom:1px solid #e2e8f0;background:#fbfdff}}
.wdcell{{width:{COLW}px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px;border-right:1px solid #eef2f7}}
.wdcell:first-child{{width:{LEFT}px}}
.wdcell .d{{font-size:19px;font-weight:700}} .wdcell .n{{font-size:12px;color:#94a3b8}}
.wknd .d{{color:#e11d48}}
.grid{{position:relative;height:{gh}px}}
.hr{{position:absolute;left:0;right:0;border-top:1px solid #eef2f7}}
.hrlbl{{position:absolute;left:0;width:{LEFT-14}px;text-align:right;font-size:12px;color:#94a3b8;transform:translateY(-8px)}}
.col{{position:absolute;top:0;bottom:0;width:{COLW}px;border-right:1px solid #f1f5f9}}
.ev{{position:absolute;border-radius:8px;padding:6px 9px;overflow:hidden;border-left:4px solid;line-height:1.28}}
.ev .t{{font-size:12px;font-weight:700;opacity:.85}}
.ev .n2{{font-size:13px;font-weight:700;margin-top:2px;word-break:break-word}}
.ev.short{{padding:4px 8px}} .ev.short .t{{font-size:10.5px}}
.ev.short .n2{{font-size:11.5px;margin-top:1px;line-height:1.2}}
.lane{{position:relative;height:{lane_h}px;border-bottom:1px solid #e2e8f0;background:#fbfdff}}
.adev{{position:absolute;top:8px;height:{max(lane_h-16,24)}px;border-radius:8px;display:flex;align-items:center;padding:0 14px;font-size:14px;font-weight:700;color:#fff;background:linear-gradient(90deg,#2563eb,#3b82f6)}}
.legend{{display:flex;gap:22px;padding:16px 30px 0;font-size:14px;color:#475569;align-items:center;flex-wrap:wrap}}
.dot{{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:7px;vertical-align:-1px}}
</style></head><body>
<div class="hd"><h1>本周日程安排</h1><div class="sub">{html.escape(subtitle)}</div></div>
<div class="wrap"><div class="wdrow"><div class="wdcell"></div>''']

    for i, d in enumerate(week):
        cls = "wdcell wknd" if d.weekday() >= 5 else "wdcell"
        p.append(f'<div class="{cls}" data-col="{i}"><div class="d">{WD[i]}</div>'
                 f'<div class="n">{d.month}/{d.day}</div></div>')
    p.append("</div>")

    if allday:
        p.append('<div class="lane">')
        for it in allday:
            d0 = date.fromisoformat(it["date"])
            d1 = date.fromisoformat(it.get("endDate") or it["date"])
            i0 = (d0 - week[0]).days
            i1 = (d1 - week[0]).days
            p.append(f'<div class="adev" style="left:{LEFT + i0 * COLW + 5}px;'
                     f'width:{(i1 - i0 + 1) * COLW - 10}px">\U0001F4CC {html.escape(it["title"])}</div>')
        p.append("</div>")

    p.append('<div class="grid">')
    for i in range(7):
        p.append(f'<div class="col" style="left:{LEFT + i * COLW}px"></div>')
    for h in range(start_h, end_h):
        y = (h - start_h) * PX_H
        p.append(f'<div class="hr" style="top:{y}px"></div>'
                 f'<div class="hrlbl" style="top:{y}px">{h:02d}:00</div>')

    byday = {}
    for it in timed:
        byday.setdefault((date.fromisoformat(it["date"]) - week[0]).days, []).append(it)
    for _, lst in byday.items():
        lst.sort(key=lambda x: hm(x["start"]))
        slots = []
        for it in lst:
            for si, last in enumerate(slots):
                if hm(it["start"]) >= hm(last["end"]) - 1e-9:
                    slots[si] = it
                    it["_col"] = si
                    break
            else:
                slots.append(it)
                it["_col"] = len(slots) - 1
        for it in lst:
            it["_ncol"] = len(slots)

    short_titles = []
    for it in timed:
        i = (date.fromisoformat(it["date"]) - week[0]).days
        if i < 0 or i > 6:
            continue
        y0 = (hm(it["start"]) - start_h) * PX_H
        y1 = (hm(it["end"]) - start_h) * PX_H
        c, bg = COLORS.get(it.get("category"), ("#64748b", "#f1f5f9"))
        ncol, col = it.get("_ncol", 1), it.get("_col", 0)
        inner = COLW - 12
        w = inner / ncol - 4 if ncol > 1 else inner
        x = LEFT + i * COLW + 6 + col * (inner / ncol)
        real = y1 - y0 - 4
        hgt = max(real, MIN_BLOCK_H)
        short = " short" if real < 40 else ""
        if real < 40:
            mins = int(round((hm(it["end"]) - hm(it["start"])) * 60))
            short_titles.append(f'{it["start"]} 的「{it["title"]}」实际只有 {mins} 分钟')
        p.append(f'<div class="ev{short}" data-day="{i}" style="left:{x:.1f}px;top:{y0 + 2}px;'
                 f'width:{w:.1f}px;height:{hgt:.1f}px;background:{bg};border-left-color:{c}">'
                 f'<div class="t" style="color:{c}">{it["start"]}–{it["end"]}</div>'
                 f'<div class="n2">{html.escape(it["title"])}</div></div>')
    p.append("</div></div>")

    legend = ('<div class="legend">'
              '<span><span class="dot" style="background:#3b82f6"></span>主业工作</span>'
              '<span><span class="dot" style="background:#f97316"></span>运动</span>')
    if allday:
        legend += ('<span><span class="dot" style="background:#2563eb"></span>'
                   '全天/多日事项</span>')
    if short_titles:
        legend += ('<span style="color:#94a3b8">注：' + "；".join(short_titles)
                   + '，为看清标题做了加高</span>')
    p.append(legend + "</div></body></html>")
    return "".join(p), W, H


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True, help="本周周一，如 2026-10-26")
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--items-json", default=None, help="可选：已导出的 items JSON")
    ap.add_argument("--out", required=True, help="输出 HTML 绝对路径")
    ap.add_argument("--subtitle", default="数据来自 Dayflow 云端日程库")
    a = ap.parse_args()

    if a.items_json:
        with open(a.items_json, encoding="utf-8") as f:
            rows = json.load(f)
    else:
        rows = fetch_items()

    week = [date.fromisoformat(a.start) + timedelta(days=i) for i in range(a.days)]
    lo, hi = week[0].isoformat(), week[-1].isoformat()
    rows = [it for it in rows
            if it.get("status") != "cancelled" and lo <= (it.get("date") or "") <= hi]

    sub = (f"{week[0].year}年{week[0].month}月{week[0].day}日 {WD[week[0].weekday()]} — "
           f"{week[-1].month}月{week[-1].day}日 {WD[week[-1].weekday()]} ｜ {a.subtitle}")
    doc, W, H = build(rows, week, sub)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"OK {a.out}  canvas={W}x{H}  items={len(rows)}")


if __name__ == "__main__":
    main()
