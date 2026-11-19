#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""df_watch73 —— 日程心跳 73 补丁版（暂存，未切 cron）

与 df_watch.py 的差异只有两处：
 1. 快照路径的会前提醒**跳过 source=dingtalk**（钉钉会前改由云端候选接管，旧快照不再发）
 2. 新增第 3 步：每轮独立查询 /api/v1/reminders/due?calendarChanges=1&lead=18，
    只接管 source=dingtalk 候选，走 df_reminders73（含 ack 与失败补投）

其它全部照旧：变更检测、完整版推送、非钉钉会前提醒、微信优先 + 私人 Telegram 兜底、
收件人、消息格式、静默时段都不变。df_watch.py / df_common.py 一行未改。

回滚：cron 的 command 从 df_watch73.py 改回 df_watch.py 即可，无需还原任何文件。
"""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import df_common as C
import df_reminders73 as R
import df_watch as W   # 复用 _slim / diff_items / build_update_message / _start_dt

QUIET_START = W.QUIET_START
QUIET_END = W.QUIET_END


def snapshot_reminders(items_now, day, now, reminded):
    """原 df_watch.py 的第 2 步，唯一区别：跳过钉钉来源（不再由旧快照兜底）。"""
    due = []
    for it in items_now:
        if it.get("status") not in ("pending", "partial"):
            continue
        if (it.get("source") or "") == R.TARGET_SOURCE:
            continue          # ← 73 改动点：钉钉会前提醒交给云端候选
        if not (it.get("start") and it.get("end")):
            continue
        sdt = W._start_dt(day, it["start"])
        if sdt is None:
            continue
        lead = (sdt - now).total_seconds() / 60.0
        if not (R.WINDOW_MIN <= lead <= R.WINDOW_MAX):
            continue
        key = "%s|%s|%s" % (it.get("id"), it.get("start"), day.isoformat())
        if reminded.get(key):
            continue
        due.append((it, key, lead))

    if not due:
        return None
    lines = []
    for it, key, lead in due:
        lines.append("还有约 %d 分钟 · %s" % (round(lead), it["start"]))
        lines.append(it["title"][:40])
        tail = "%s-%s" % (it["start"], it["end"])
        if it.get("sourceLocation"):
            tail += " · " + it["sourceLocation"][:30]
        lines.append(tail)
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
    if ok:
        for _, key, _ in due:
            reminded[key] = now.isoformat(timespec="seconds")
        C.save_reminded(reminded, day)
    return "remind:%d/%s/%s" % (len(due), ok, ch)


def main():
    now = datetime.now()
    day = now.date()

    if QUIET_START <= now.hour < QUIET_END:
        print("watch73 quiet-hours")
        return 0

    snap = C.load_snapshot(day)
    age = C.snapshot_age_minutes(day)
    pushed = []

    # 1) 快照缺失/过期 → 拉云端比对（原样保留）
    if snap is None or age is None or age >= C.SNAPSHOT_TTL_MIN:
        items = C.get_items()
        fresh = [W._slim(i) for i in items if C.is_live(i) and C.on_day(i, day)]
        if snap is None:
            C.save_snapshot([i for i in items if C.is_live(i) and C.on_day(i, day)],
                            day, source="watch-init")
            snap = C.load_snapshot(day)
        else:
            added, dropped, changed = W.diff_items(snap.get("items", []), fresh)
            if added or dropped or changed:
                msg = W.build_update_message(
                    [i for i in items if C.is_live(i) and C.on_day(i, day)], day,
                    added, dropped, changed)
                ok, ch = C.send(msg)
                pushed.append("update:%s/%s" % (ok, ch))
            C.save_snapshot([i for i in items if C.is_live(i) and C.on_day(i, day)],
                            day, source="watch")
            snap = C.load_snapshot(day)

    # 2) 非钉钉会前提醒（原 [13,18] 窗口），钉钉已剔除
    items_now = (snap or {}).get("items", [])
    reminded = C.load_reminded(day)
    r = snapshot_reminders(items_now, day, now, reminded)
    if r:
        pushed.append(r)

    # 3) 73：云端候选（只接管 source=dingtalk）+ 补投 ack
    try:
        res = R.run(day=day, now=now)
        pushed.append("r73:%s/sent=%d/skip=%d/pend=%d"
                      % ("ready" if res.get("ready") else "not-ready",
                         len([s for s in res.get("sent", []) if s.get("ok")]),
                         len(res.get("skipped", [])),
                         len(res.get("pendingRetry", []))))
    except Exception as e:  # 新链路任何异常都不能拖垮原有心跳
        pushed.append("r73:error=%s" % str(e)[:80])

    print("watch73 day=%s age=%s pushed=%s"
          % (day, ("%.1f" % age) if age is not None else "none",
             ",".join(pushed) if pushed else "none"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
