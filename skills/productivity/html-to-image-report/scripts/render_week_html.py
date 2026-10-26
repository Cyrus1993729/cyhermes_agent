#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Dayflow items JSON -> 一周日程周视图 HTML（供 browser_exec 截图）。

用法:
    python render_week_html.py <items.json> <out.html> [YYYY-MM-DD 周一]

items.json = `client items` 输出的 JSON 数组（list[dict]）。
默认周起点取最早事项所在周的周一；也可显式传第三个参数。

2026-10-25 实测：1520x1186 画布，@2x 截图 3040x2372，中文正常。
换别的报表也能照抄这套结构（固定画布 + 绝对定位 + data-* 属性供校验）。
"""
import json
import sys
import html
from datetime import date, timedelta

START_H, END_H = 7, 22
PX_H = 58
LEFT = 90
COLW = 200
WD = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
COLORS = {
    "work": ("#3b82f6", "#eff6ff"),
    "sport": ("#f97316", "#fff7ed"),
    "side": ("#a855f7", "#faf5ff"),
    "life": ("#14b8a6", "#f0fdfa"),
}


def hm(s):
    h, m = s.split(":")
    return int(h) + int(m) / 60


def is_allday(it):
    return bool(it.get("allDay")) or (bool(it.get("endDate")) and not it.get("start"))


def render(items, week_start):
    WEEK = [week_start + timedelta(days=i) for i in range(7)]
    rows = [i for i in items if i.get("status") != "cancelled"]
    allday = [i for i in rows if is_allday(i)]
    timed = [i for i in rows if (not is_allday(i)) and i.get("start")]

    W = LEFT + COLW * 7 + 30
    lane_h = 56 if allday else 0
    GH = (END_H - START_H) * PX_H
    H = 150 + lane_h + GH + 110

    p = ['<!doctype html><html><head><meta charset="utf-8"><style>',
         "*{box-sizing:border-box;margin:0;padding:0}",
         'body{width:%dpx;height:%dpx;background:#f8fafc;'
         'font-family:"Microsoft YaHei","Segoe UI",sans-serif;color:#0f172a;overflow:hidden}' % (W, H),
         ".hd{padding:24px 30px 12px}.hd h1{font-size:34px;font-weight:800}",
         ".hd .sub{font-size:16px;color:#64748b;margin-top:6px}",
         ".wrap{position:relative;margin:0 15px;background:#fff;border-radius:14px;"
         "box-shadow:0 2px 14px rgba(15,23,42,.08);overflow:hidden}",
         ".wdrow{display:flex;height:58px;border-bottom:1px solid #e2e8f0;background:#fbfdff}",
         ".wdcell{width:%dpx;display:flex;flex-direction:column;align-items:center;"
         "justify-content:center;gap:2px;border-right:1px solid #eef2f7}" % COLW,
         ".wdcell:first-child{width:%dpx}" % LEFT,
         ".wdcell .d{font-size:19px;font-weight:700}.wdcell .n{font-size:12px;color:#94a3b8}",
         ".wknd .d{color:#e11d48}",
         ".grid{position:relative;height:%dpx}" % GH,
         ".hr{position:absolute;left:0;right:0;border-top:1px solid #eef2f7}",
         ".hrlbl{position:absolute;left:0;width:%dpx;text-align:right;font-size:12px;"
         "color:#94a3b8;transform:translateY(-8px)}" % (LEFT - 14),
         ".col{position:absolute;top:0;bottom:0;width:%dpx;border-right:1px solid #f1f5f9}" % COLW,
         ".ev{position:absolute;border-radius:8px;padding:6px 9px;overflow:hidden;"
         "border-left:4px solid;line-height:1.28}",
         ".ev .t{font-size:12px;font-weight:700;opacity:.85}",
         ".ev .n2{font-size:13px;font-weight:700;margin-top:2px;word-break:break-word}",
         ".ev.short{padding:4px 8px}",
         ".ev.short .t{font-size:10.5px}",
         ".ev.short .n2{font-size:11.5px;margin-top:1px;line-height:1.2}",
         ".lane{position:relative;height:%dpx;border-bottom:1px solid #e2e8f0;"
         "background:#fbfdff}" % lane_h,
         ".adev{position:absolute;top:8px;height:%dpx;border-radius:8px;display:flex;"
         "align-items:center;padding:0 14px;font-size:14px;font-weight:700;color:#fff;"
         "background:linear-gradient(90deg,#2563eb,#3b82f6)}" % max(lane_h - 16, 24),
         ".legend{display:flex;gap:22px;padding:16px 30px 0;font-size:14px;color:#475569;"
         "align-items:center;flex-wrap:wrap}",
         ".dot{display:inline-block;width:12px;height:12px;border-radius:3px;"
         "margin-right:7px;vertical-align:-1px}",
         "</style></head><body>",
         '<div class="hd"><h1>本周日程安排</h1><div class="sub">%s — %s ｜ '
         '数据来自 Dayflow 云端日程库</div></div>' % (
             WEEK[0].strftime("%Y年%m月%d日"), WEEK[-1].strftime("%m月%d日 周日")),
         '<div class="wrap"><div class="wdrow"><div class="wdcell"></div>']

    for i, d in enumerate(WEEK):
        cls = "wdcell wknd" if d.weekday() >= 5 else "wdcell"
        p.append('<div class="%s" data-col="%d"><div class="d">%s</div>'
                 '<div class="n">%d/%d</div></div>' % (cls, i, WD[i], d.month, d.day))
    p.append("</div>")

    if allday:
        p.append('<div class="lane">')
        for it in allday:
            d0 = date.fromisoformat(it["date"])
            d1 = date.fromisoformat(it.get("endDate") or it["date"])
            i0 = max((d0 - WEEK[0]).days, 0)
            i1 = min((d1 - WEEK[0]).days, 6)
            if i1 < 0 or i0 > 6:
                continue
            p.append('<div class="adev" style="left:%dpx;width:%dpx">📌 %s</div>' % (
                LEFT + i0 * COLW + 5, (i1 - i0 + 1) * COLW - 10, html.escape(it["title"])))
        p.append("</div>")

    p.append('<div class="grid">')
    for i in range(7):
        p.append('<div class="col" style="left:%dpx"></div>' % (LEFT + i * COLW))
    # 注意 range 到 END_H 为止，别 +1，否则最后一个整点标签压在画布下沿
    for h in range(START_H, END_H):
        y = (h - START_H) * PX_H
        p.append('<div class="hr" style="top:%dpx"></div>'
                 '<div class="hrlbl" style="top:%dpx">%02d:00</div>' % (y, y, h))

    byday = {}
    for it in timed:
        idx = (date.fromisoformat(it["date"]) - WEEK[0]).days
        if 0 <= idx <= 6:
            byday.setdefault(idx, []).append(it)

    placed = []
    for idx, lst in byday.items():
        lst.sort(key=lambda x: hm(x["start"]))
        slots = []
        mine = []
        for it in lst:
            for si, last in enumerate(slots):
                if hm(it["start"]) >= hm(last["end"]) - 1e-9:
                    slots[si] = it
                    mine.append([idx, it, si])
                    break
            else:
                slots.append(it)
                mine.append([idx, it, len(slots) - 1])
        n = len(slots)
        placed.extend([(i2, it2, si, n) for i2, it2, si in mine])

    for idx, it, col, ncol in placed:
        y0 = (hm(it["start"]) - START_H) * PX_H
        y1 = (hm(it["end"]) - START_H) * PX_H
        c, bg = COLORS.get(it.get("category"), ("#64748b", "#f1f5f9"))
        inner = COLW - 12
        w = inner / ncol - 4 if ncol > 1 else inner
        x = LEFT + idx * COLW + 6 + col * (inner / ncol)
        real = y1 - y0 - 4
        hgt = max(real, 50)
        short = " short" if real < 40 else ""
        p.append('<div class="ev%s" data-day="%d" style="left:%.1fpx;top:%.1fpx;width:%.1fpx;'
                 'height:%.1fpx;background:%s;border-left-color:%s">'
                 '<div class="t" style="color:%s">%s–%s</div>'
                 '<div class="n2">%s</div></div>' % (
                     short, idx, x, y0 + 2, w, hgt, bg, c, c,
                     it["start"], it["end"], html.escape(it["title"])))

    p.append("</div></div>")
    p.append('<div class="legend">'
             '<span><span class="dot" style="background:#3b82f6"></span>主业工作</span>'
             '<span><span class="dot" style="background:#f97316"></span>运动</span>'
             '<span><span class="dot" style="background:#2563eb"></span>全天/多日事项</span>'
             '<span style="color:#94a3b8">注：跨日事项为全天未定钟点；'
             '时长不足 40 分钟的事项做了加高以便看清标题</span></div>')
    p.append("</body></html>")
    return "".join(p), W, H


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    items = json.load(open(sys.argv[1], encoding="utf-8"))
    valid = [i for i in items if i.get("date")]
    if not valid:
        print("items 里没有带 date 的条目")
        return 2
    if len(sys.argv) > 3:
        ws = date.fromisoformat(sys.argv[3])
    else:
        d = min(date.fromisoformat(i["date"]) for i in valid)
        ws = d - timedelta(days=d.weekday())
    out_html, W, H = render(items, ws)
    open(sys.argv[2], "w", encoding="utf-8").write(out_html)
    print("written %s  canvas %dx%d  (截图用 width=%d height=%d)" % (sys.argv[2], W, H, W, H))
    return 0


if __name__ == "__main__":
    sys.exit(main())
