#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""21:30 今日收尾：列出仍挂着的事项 + 复盘引导 → 微信

cron: 30 21 * * *
- 编号存本地映射（evening_<date>.json），用户回"2 做完了"时据此对上事项
- 无安排也发（用户要求：没安排也要提醒复盘）
"""
import json
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import df_common as C

WEEKDAY_CN = C.WEEKDAY_CN
MAX_LIST = 8


def evening_map_path(day):
    return C.STATE_DIR / ("evening_%s.json" % day.isoformat())


def main():
    day = date.today()
    items = C.get_items()
    todays = [i for i in items if C.is_live(i) and C.on_day(i, day)]
    open_items = [i for i in todays if i.get("status") in ("pending", "partial")]
    done = [i for i in todays if i.get("status") == "completed"]

    # 排序：有时间的按时间，无时间的放后面
    open_items.sort(key=lambda x: (x.get("start") or "99:99", x.get("title") or ""))

    head = "今日收尾 %d月%d日 周%s" % (day.month, day.day, WEEKDAY_CN[day.weekday()])
    lines = [head, ""]

    mapping = []
    if open_items:
        lines.append("今天还挂着 %d 件，回我编号就行：" % len(open_items))
        for n, i in enumerate(open_items[:MAX_LIST], 1):
            t = C.fmt_hhmm(i.get("start"))
            prefix = ("%s " % t) if i.get("start") else ""
            lines.append("%d. %s%s" % (n, prefix, (i.get("title") or "")[:34]))
            mapping.append({"n": n, "id": i.get("id"), "title": i.get("title"),
                            "date": i.get("date"), "start": i.get("start") or "",
                            "status": i.get("status"), "version": i.get("version")})
        if len(open_items) > MAX_LIST:
            lines.append("…还有 %d 件没列（回我「看全部」）" % (len(open_items) - MAX_LIST))
        lines.append("")
        lines.append("哪几件做完了？没做的说一声：明天继续 / 取消。")
    else:
        lines.append("今天没有挂着的事项。")

    if done:
        lines.append("")
        lines.append("今天已完成 %d 项。" % len(done))

    lines.append("")
    lines.append("想留一句复盘就说，不回也行。")

    text = "\n".join(lines)
    ok, channel = C.send(text)

    # 编号映射落盘（供对话中处理用户回复）
    try:
        p = evening_map_path(day)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(
            {"date": day.isoformat(),
             "sentAt": datetime.now().isoformat(timespec="seconds"),
             "open": mapping,
             "doneCount": len(done)},
            ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(p)
    except Exception as e:
        print("evening map save failed: %s" % e)

    C.cleanup_old_state()
    print("evening day=%s open=%d done=%d sent=%s via=%s"
          % (day, len(open_items), len(done), ok, channel))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
