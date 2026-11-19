#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""日程心跳（每 5 分钟）：变更检测 + 开始前 15 分钟提醒

cron: */5 * * * *
- 快照新鲜（<15 分钟）→ 不碰云端，直接用本地快照判断提醒
- 快照过期 → 拉云端比对；有变化就推"今日日程已更新"（完整版 + 变动摘要）
- 平台只读不写：本脚本不改任何事项状态
"""
import sys
from datetime import date, datetime, time as dtime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import df_common as C

QUIET_START = 0    # 深夜不跑（0:00-6:00）
QUIET_END = 6


def _start_dt(day, hhmm):
    try:
        h, m = hhmm.split(":")
        return datetime.combine(day, dtime(int(h), int(m)))
    except Exception:
        return None


def _slim(item):
    return {
        "id": item.get("id"),
        "title": item.get("title") or "",
        "date": item.get("date"),
        "endDate": item.get("endDate"),
        "start": item.get("start") or "",
        "end": item.get("end") or "",
        "status": item.get("status"),
        "sourceLocation": item.get("sourceLocation") or "",
        "source": item.get("source") or "",
        "plannedMinutes": item.get("plannedMinutes") or 0,
    }


def diff_items(old, new):
    old_map = {i["id"]: i for i in old}
    new_map = {i["id"]: i for i in new}
    added, dropped, changed = [], [], []
    for k, v in new_map.items():
        if k not in old_map:
            if v.get("status") != "cancelled":
                added.append(v)
            continue
        o = old_map[k]
        if v.get("status") == "cancelled" and o.get("status") != "cancelled":
            dropped.append(o)
            continue
        if (o.get("start") != v.get("start") or o.get("end") != v.get("end")
                or o.get("title") != v.get("title") or o.get("date") != v.get("date")):
            changed.append((o, v))
    for k, o in old_map.items():
        if k not in new_map and o.get("status") != "cancelled":
            dropped.append(o)
    return added, dropped, changed


def build_update_message(items, day, added, dropped, changed):
    base, _, _, _ = C.build_today_message(items, day, reason="update")
    lines = []
    if added or dropped or changed:
        lines.append("【变动】新增 %d，取消 %d，改期 %d"
                     % (len(added), len(dropped), len(changed)))
        for v in added[:3]:
            lines.append("+ %s %s %s" % (v.get("start") or "全天", v.get("end") or "",
                                         (v.get("title") or "")[:30]))
        for o in dropped[:3]:
            lines.append("- 取消 %s %s" % (o.get("start") or "", (o.get("title") or "")[:30]))
        for o, v in changed[:3]:
            if o.get("start") != v.get("start"):
                lines.append("~ %s %s → %s" % ((v.get("title") or "")[:20],
                                               o.get("start") or "全天", v.get("start") or "全天"))
            else:
                lines.append("~ %s（内容有变）" % (v.get("title") or "")[:24])
    return "\n".join(lines) + "\n\n" + base


def main():
    now = datetime.now()
    day = now.date()

    if QUIET_START <= now.hour < QUIET_END:
        print("watch quiet-hours")
        return 0

    snap = C.load_snapshot(day)
    age = C.snapshot_age_minutes(day)
    pushed = []

    # 1) 快照缺失或过期 → 拉云端
    if snap is None or age is None or age >= C.SNAPSHOT_TTL_MIN:
        items = C.get_items()
        fresh = [_slim(i) for i in items if C.is_live(i) and C.on_day(i, day)]
        if snap is None:
            C.save_snapshot([i for i in items if C.is_live(i) and C.on_day(i, day)],
                            day, source="watch-init")
            snap = C.load_snapshot(day)
        else:
            added, dropped, changed = diff_items(snap.get("items", []), fresh)
            if added or dropped or changed:
                msg = build_update_message(
                    [i for i in items if C.is_live(i) and C.on_day(i, day)], day,
                    added, dropped, changed)
                ok, ch = C.send(msg)
                pushed.append("update:%s/%s" % (ok, ch))
            C.save_snapshot([i for i in items if C.is_live(i) and C.on_day(i, day)],
                            day, source="watch")
            snap = C.load_snapshot(day)

    # 2) 提前 15 分钟提醒（基于最新快照，不额外打接口）
    items_now = (snap or {}).get("items", [])
    reminded = C.load_reminded(day)
    due = []
    for it in items_now:
        if it.get("status") not in ("pending", "partial"):
            continue
        if not (it.get("start") and it.get("end")):
            continue
        sdt = _start_dt(day, it["start"])
        if sdt is None:
            continue
        lead = (sdt - now).total_seconds() / 60.0
        if not (C.LEAD_MINUTES - 2 <= lead <= C.LEAD_MINUTES + 3):
            continue
        key = "%s|%s|%s" % (it.get("id"), it.get("start"), day.isoformat())
        if reminded.get(key):
            continue
        due.append((it, key, lead))

    if due:
        lines = []
        for it, key, lead in due:
            head = "还有约 %d 分钟 · %s" % (round(lead), it["start"])
            lines.append(head)
            lines.append(it["title"][:40])
            tail = "%s-%s" % (it["start"], it["end"])
            if it.get("sourceLocation"):
                tail += " · " + it["sourceLocation"][:30]
            lines.append(tail)
            # 同一时段冲突提示
            for other in items_now:
                if other.get("id") == it.get("id"):
                    continue
                if other.get("status") == "cancelled":
                    continue
                if other.get("start") == it.get("start"):
                    lines.append("⚠️ 同时还有：" + (other.get("title") or "")[:24])
            lines.append("")
        msg = "\n".join(lines).strip()
        ok, ch = C.send(msg)
        pushed.append("remind:%d/%s/%s" % (len(due), ok, ch))
        if ok:
            for _, key, _ in due:
                reminded[key] = now.isoformat(timespec="seconds")
            C.save_reminded(reminded, day)

    print("watch day=%s age=%s pushed=%s"
          % (day, ("%.1f" % age) if age is not None else "none",
             ",".join(pushed) if pushed else "none"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
