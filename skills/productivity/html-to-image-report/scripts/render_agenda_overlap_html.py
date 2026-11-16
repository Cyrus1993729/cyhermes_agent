#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Dayflow items JSON -> 含「时间重叠可视化」的周计划图 HTML（供 browser_exec 截图）。

用法:
    python render_agenda_overlap_html.py <items.json> <out.html> <YYYY-MM-DD 周一>

三块结构（缺一块用户会再提一次）：
  1) 顶部「时间重叠可视化」：每个有重叠的日期一行，当日最长事项画跨度带，
     其余事项画色条，真正重叠的区间盖红色斜纹，重叠分钟数单独一行标签。
  2) 中间「按日期查看一周安排」：7 列议程卡片，完整标题，重叠事项挂红框并
     逐条列出对端**全名** + 重叠窗口 + 分钟数。
  3) 底部「时间重叠明细」：逐对列出 日期 / 事项A+起止 / 事项B+起止 / 重叠时段 / 时长。

判定口径：只有起止时间有真正交集才算重叠（max(start) < min(end)）；
首尾相接（09:30-10:00 与 10:00-10:30）**不算**。这个口径必须写进图注。

设计约束（别改）：
  * 坐标一律相对定位容器自身算（trail left:0 width:AW），不要再给容器加 margin
    又给子元素加 left —— 两段偏移叠加会把最右元素顶出画布。
  * 短色块（宽度 < 104px）不渲染标题文字，否则文字溢出条外。
  * 层级：斜纹 z-index:1 < 色条 2 < 分钟标签 3，斜纹内部不放文字。
"""
import json
import html
import sys
from datetime import date, timedelta

WD = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
CAT = {"work": "主业", "side": "副业", "sport": "运动", "life": "生活"}
COLOR = {"work": "#3b82f6", "side": "#a855f7", "sport": "#f97316", "life": "#14b8a6"}

CANVAS_W = 1520
BODY_PAD = 28
SECT_PAD = 20
LABEL_W = 74
AXIS_PAD = 1
MIN_LABEL_PX = 104


def hm(s):
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def fmt(x):
    return "%02d:%02d" % (x // 60, x % 60)


def detect_overlaps(evs):
    """严格交集才算重叠，返回 [(a, b, start_min, end_min)]。"""
    timed = [e for e in evs if e.get("start") and e.get("end")]
    timed.sort(key=lambda e: hm(e["start"]))
    pairs = []
    for i in range(len(timed)):
        for j in range(i + 1, len(timed)):
            a, b = timed[i], timed[j]
            s = max(hm(a["start"]), hm(b["start"]))
            e = min(hm(a["end"]), hm(b["end"]))
            if e > s:
                pairs.append((a, b, s, e))
    return pairs


def axis_range(timed):
    """从当周数据算轴范围，前后各留 1 小时，夹到 0-24，最少 3 小时。"""
    if not timed:
        return 480, 1380
    lo = min(hm(e["start"]) for e in timed) // 60 - AXIS_PAD
    hi = -(-max(hm(e["end"]) for e in timed) // 60) + AXIS_PAD
    lo, hi = max(0, lo), min(24, hi)
    if hi - lo < 3:
        hi = min(24, lo + 3)
    return lo * 60, hi * 60


def card_html(it):
    st = "已完成" if it.get("status") == "completed" else "待办"
    ov = it.get("_ov", [])
    cls = ("done " if st == "已完成" else "") + ("conflict" if ov else "")
    ovh = ""
    if ov:
        lines = "<br>".join("&#10231; " + html.escape(o) for o in ov)
        ovh = '<div class="ovh">\u26a0 时间重叠 %d 项<br>%s</div>' % (len(ov), lines)
    return ('<article class="event %s"><div class="time">%s&ndash;%s '
            '<span class="badge">%s</span></div><div class="title">%s</div>'
            '<div class="meta">%s</div>%s</article>'
            % (cls, it.get("start", ""), it.get("end", ""), st,
               html.escape(it["title"]),
               CAT.get(it.get("category"), it.get("category", "")), ovh))


def render(items, week_start):
    WEEK = [week_start + timedelta(days=i) for i in range(7)]
    rows = [i for i in items if i.get("status") != "cancelled"]

    byday = {i: [] for i in range(7)}
    for it in rows:
        d = it.get("date")
        if not d or not it.get("start"):
            continue
        idx = (date.fromisoformat(d) - week_start).days
        if 0 <= idx < 7:
            byday[idx].append(it)
    for lst in byday.values():
        lst.sort(key=lambda e: e["start"])

    over = {}
    for i in range(7):
        p = detect_overlaps(byday[i])
        if p:
            over[i] = p

    # 卡片内的重叠说明：全名，不截断
    for pairs in over.values():
        for a, b, s, e in pairs:
            tail = "（%s–%s，%d分）" % (fmt(s), fmt(e), e - s)
            a.setdefault("_ov", []).append(b["title"] + tail)
            b.setdefault("_ov", []).append(a["title"] + tail)

    timed = [e for lst in byday.values() for e in lst]
    AX0, AX1 = axis_range(timed)
    AW = CANVAS_W - BODY_PAD * 2 - 2 - SECT_PAD * 2 - LABEL_W

    def px(m):
        return (m - AX0) / float(AX1 - AX0) * AW

    ax = ['<div class="axisrow">']
    for h in range(AX0 // 60, AX1 // 60 + 1):
        ax.append('<div class="tick" style="left:%.1fpx">%02d:00</div>' % (px(h * 60), h))
    ax.append('<div class="axline" style="left:0;width:%.0fpx"></div>' % AW)
    ax.append("</div>")

    for i in sorted(over):
        evs = byday[i]
        main = max(evs, key=lambda e: hm(e["end"]) - hm(e["start"]))
        band = ""
        for a, b, s, e in over[i]:
            band += ('<div class="ovband" style="left:%.1fpx;width:%.1fpx"></div>'
                     % (px(s), max(px(e) - px(s), 3)))
        mx0 = px(hm(main["start"]))
        mw = px(hm(main["end"])) - mx0
        band += ('<div class="mainband" style="left:%.1fpx;width:%.1fpx">'
                 '<span>%s（%s–%s）</span></div>'
                 % (mx0, mw, html.escape(main["title"]), main["start"], main["end"]))
        for e in evs:
            if e is main:
                continue
            w = max(px(hm(e["end"])) - px(hm(e["start"])), 5)
            txt = ""
            if w >= MIN_LABEL_PX:
                txt = "<span>%s</span>" % html.escape(e["title"])
            band += ('<div class="bar" style="left:%.1fpx;width:%.1fpx;background:%s">%s</div>'
                     % (px(hm(e["start"])), w, COLOR.get(e.get("category"), "#64748b"), txt))
        for a, b, s, e in over[i]:
            band += ('<div class="olab" style="left:%.1fpx;width:%.1fpx">%d分</div>'
                     % (px(s), max(px(e) - px(s), 26), e - s))
        d = WEEK[i]
        ax.append('<div class="dayrow"><div class="daylbl">%s<small>%d/%d<br>重叠 %d 对</small>'
                  '</div><div class="trail">%s</div></div>'
                  % (WD[i], d.month, d.day, len(over[i]), band))

    total = sum(len(v) for v in over.values())
    sec1 = ('<div class="sect"><h2>时间重叠可视化<span class="tag">共 %d 对</span></h2>%s'
            '<div class="legend2">'
            '<span><span class="lg" style="background:#dbeafe;border:1px solid #93c5fd"></span>'
            '当日最长事项（时间跨度带）</span>'
            '<span><span class="lg" style="background:#3b82f6"></span>同日其他事项</span>'
            '<span><span class="lg" style="background:repeating-linear-gradient(45deg,'
            '#ef444499,#ef444499 4px,#ef444433 4px,#ef444433 8px);border:1px solid #ef4444">'
            '</span>红色斜纹＝两条时间真正重叠的区间</span>'
            '<span><span class="lg" style="background:#fee2e2;border:1px solid #fca5a5"></span>'
            '红色标签＝重叠分钟数</span></div></div>') % (total, "".join(ax))

    cards = []
    for i in range(7):
        body = "".join(card_html(it) for it in byday[i]) or '<div class="empty">暂无安排</div>'
        d = WEEK[i]
        sub = "%d 项%s" % (len(byday[i]),
                          ("　· 重叠 %d 对" % len(over[i])) if i in over else "")
        cards.append('<section class="day"><header class="dayhead"><b>%s</b>'
                    '<span>%d/%d</span><small>%s</small></header>'
                    '<div class="items">%s</div></section>'
                    % (WD[i], d.month, d.day, sub, body))
    sec2 = ('<div class="sect"><h2>按日期查看一周安排</h2><div class="grid">%s</div></div>'
            % "".join(cards))

    trs = []
    for i in sorted(over):
        for a, b, s, e in over[i]:
            trs.append('<tr><td class="dk">%s</td><td>%s<i>%s–%s</i></td>'
                       '<td>%s<i>%s–%s</i></td><td class="win">%s–%s</td>'
                       '<td class="min">%d 分钟</td></tr>'
                       % (WD[i], html.escape(a["title"]), a["start"], a["end"],
                          html.escape(b["title"]), b["start"], b["end"],
                          fmt(s), fmt(e), e - s))
    sec3 = ('<div class="sect"><h2>时间重叠明细<span class="tag">逐对列出</span></h2>'
            '<table><thead><tr><th>日期</th><th>事项 A</th><th>事项 B</th>'
            '<th>实际重叠时段</th><th>时长</th></tr></thead><tbody>%s</tbody></table></div>'
            % "".join(trs))

    head = ('<div class="titlebar"><h1>本周工作安排</h1><div class="sub">%s—%s ｜ 共 %d 项，'
            '其中 %d 对时间重叠</div></div>'
            % (WEEK[0].strftime("%Y年%m月%d日"), WEEK[-1].strftime("%m月%d日 周日"),
               len(rows), total))
    foot = ('<div class="foot">判定口径：只有起止时间存在真正交集才计为重叠，首尾相接'
            '（如 09:30–10:00 与 10:00–10:30）不算。图中不修改任何时间、标题或完成状态，'
            '只做视觉标注；时间轴上宽度不足的色块不显示标题文字，完整名称见卡片与明细表。</div>')
    return CSS + head + sec1 + sec2 + sec3 + foot + "</body></html>"


CSS = '''<!doctype html><html><head><meta charset="utf-8"><style>
*{box-sizing:border-box;margin:0;padding:0}
body{width:1520px;background:#f4f7fb;font-family:"Microsoft YaHei","Segoe UI",sans-serif;color:#152238;padding:28px 28px 22px;overflow-x:hidden}
h1{font-size:36px;font-weight:800;letter-spacing:.5px}
.sub{color:#63728a;font-size:15px;margin-top:7px}.titlebar{margin-bottom:16px}
h2{font-size:19px;font-weight:800;margin:0 0 12px;display:flex;align-items:center;gap:9px}
h2 .tag{font-size:12px;font-weight:700;color:#b42318;background:#fee4e2;border-radius:20px;padding:3px 10px}
.sect{background:#fff;border:1px solid #e1e8f0;border-radius:14px;padding:18px 20px;margin-bottom:16px;box-shadow:0 2px 10px #15223808}
.axisrow{position:relative;height:28px;margin-left:74px}
.tick{position:absolute;top:0;font-size:12px;color:#94a3b8;transform:translateX(-16px)}
.axline{position:absolute;top:21px;height:1px;background:#e2e8f0}
.dayrow{position:relative;height:118px;border-top:1px solid #f1f5f9}
.daylbl{position:absolute;left:0;top:26px;width:64px;font-weight:800;font-size:15px;line-height:1.3;z-index:5}
.daylbl small{display:block;font-weight:500;font-size:11px;color:#94a3b8;line-height:1.5}
.trail{position:absolute;left:74px;top:0;right:0;bottom:0}
.mainband{position:absolute;top:14px;height:26px;background:#dbeafe;border:1px solid #93c5fd;border-radius:6px;overflow:hidden;z-index:2}
.mainband span{font-size:11px;color:#1e40af;font-weight:700;padding-left:7px;line-height:24px;white-space:nowrap}
.bar{position:absolute;top:50px;height:26px;border-radius:5px;overflow:hidden;box-shadow:0 1px 3px #15223822;z-index:2}
.bar span{font-size:10px;color:#fff;font-weight:700;line-height:26px;padding-left:6px;white-space:nowrap}
.ovband{position:absolute;top:8px;height:74px;z-index:1;background:repeating-linear-gradient(45deg,#ef444440,#ef444440 6px,#ef444412 6px,#ef444412 12px);border:1.5px solid #ef4444;border-radius:5px}
.olab{position:absolute;top:82px;height:17px;line-height:17px;text-align:center;font-size:10px;font-weight:800;color:#b91c1c;background:#fee2e2;border-radius:4px;z-index:3;white-space:nowrap;overflow:hidden}
.legend2{margin-top:12px;font-size:13px;color:#5b6b80;display:flex;gap:26px;flex-wrap:wrap;align-items:center}
.lg{display:inline-block;width:22px;height:12px;border-radius:3px;margin-right:6px;vertical-align:-1px}
.grid{display:grid;grid-template-columns:repeat(7,1fr);gap:10px;align-items:stretch}
.day{background:#fff;border:1px solid #e1e8f0;border-radius:13px;overflow:hidden;min-height:640px;box-shadow:0 2px 8px #1522380a}
.dayhead{background:#f8fafc;border-bottom:1px solid #e6edf5;padding:10px 12px;display:flex;align-items:baseline;gap:7px;flex-wrap:wrap}
.dayhead b{font-size:18px}.dayhead span{font-size:14px;color:#718096}
.dayhead small{font-size:11px;color:#94a3b8;width:100%}
.items{padding:8px;display:flex;flex-direction:column;gap:8px}
.event{border-radius:8px;background:#eff6ff;border-left:4px solid #3b82f6;padding:9px;overflow-wrap:anywhere}
.event.done{background:#f1f5f9;border-left-color:#94a3b8}
.event.conflict{background:#fff5f5;border-left-color:#ef4444;box-shadow:0 0 0 1.5px #ef444433}
.time{font-size:12px;font-weight:700;color:#40536c;display:flex;justify-content:space-between;align-items:center}
.badge{font-size:10px;color:#64748b;font-weight:500}
.title{font-size:13px;font-weight:700;line-height:1.35;margin-top:5px}
.meta{font-size:11px;color:#76849a;margin-top:3px}
.ovh{margin-top:7px;padding:6px 7px;background:#fff;border:1px dashed #f5a3a3;border-radius:6px;font-size:10.5px;line-height:1.55;color:#b42318;font-weight:700}
.empty{color:#a1adbb;text-align:center;padding:30px 0;font-size:13px}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;font-size:12px;color:#64748b;font-weight:700;padding:8px 10px;border-bottom:2px solid #e2e8f0}
td{padding:9px 10px;border-bottom:1px solid #f1f5f9;vertical-align:middle}
td i{display:block;font-style:normal;font-size:11px;color:#94a3b8;margin-top:2px}
.dk{font-weight:800;color:#334155;white-space:nowrap}
.win{font-weight:800;color:#b91c1c;white-space:nowrap}
.min{font-weight:800;color:#b91c1c;white-space:nowrap}
.foot{margin-top:4px;padding:12px 16px;background:#fff;border-radius:10px;color:#68778d;font-size:12.5px;line-height:1.65}
</style></head><body>'''


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        return 1
    with open(sys.argv[1], encoding="utf-8") as f:
        items = json.load(f)
    out = render(items, date.fromisoformat(sys.argv[3]))
    with open(sys.argv[2], "w", encoding="utf-8") as f:
        f.write(out)
    print("written %s ｜ 画布宽 %d ｜ 截图前跑溢出扫描 + clipped 校验" % (sys.argv[2], CANVAS_W))
    return 0


if __name__ == "__main__":
    sys.exit(main())
