# -*- coding: utf-8 -*-
"""离线自检：不写云端、不发消息，验证文本组装/冲突/提醒窗口/变更检测"""
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ["DAYFLOW_DRY"] = "1"

import df_common as C
import df_watch as W

FAIL = []


def check(name, cond, extra=""):
    print(("  OK   " if cond else "  FAIL ") + name + ((" | " + extra) if extra else ""))
    if not cond:
        FAIL.append(name)


print("== 1. 真实数据：找最近一个有安排的日期，生成早报 ==")
items = C.get_items()
today = date.today()
future = sorted({date.fromisoformat(i["date"]) for i in items
                 if i.get("date") and i.get("status") != "cancelled"
                 and date.fromisoformat(i["date"]) >= today})
day = future[0] if future else today
txt, open_items, fixed, conf = C.build_today_message(items, day, "morning")
print("  日期:", day, "| 字数:", len(txt), "| 固定时段:", len(fixed))
print("  内容:")
for line in txt.splitlines():
    print("    " + line)
check("早报长度 <= 900", len(txt) <= C.MAX_MSG_CHARS, "len=%d" % len(txt))

print()
print("== 2. 冲突检测 ==")
fake = [
    {"id": "a", "title": "部门工作会议", "date": str(today), "start": "10:30", "end": "12:00",
     "status": "pending", "category": "work", "source": "dingtalk", "plannedMinutes": 90},
    {"id": "b", "title": "部门例会", "date": str(today), "start": "10:30", "end": "12:30",
     "status": "pending", "category": "work", "source": "dingtalk", "plannedMinutes": 120},
    {"id": "c", "title": "下午单独会议", "date": str(today), "start": "15:00", "end": "16:00",
     "status": "pending", "category": "work", "source": "dingtalk", "plannedMinutes": 60},
]
t2, _, f2, c2 = C.build_today_message(fake, today, "morning")
check("识别出 1 处冲突", len(c2) == 1, "conflicts=%d" % len(c2))
check("冲突写进文本", "时间冲突" in t2, "")
print("  冲突行:", [l for l in t2.splitlines() if "撞" in l])

print()
print("== 3. 仅两个不相干会议 → 不应误报冲突 ==")
fake2 = [fake[0], fake[2]]
_, _, _, c3 = C.build_today_message(fake2, today, "morning")
check("无冲突", len(c3) == 0, "conflicts=%d" % len(c3))

print()
print("== 4. 无安排日 → 必须主动询问 ==")
empty_day = date(2099, 12, 30)
t4, _, _, _ = C.build_today_message([], empty_day, "morning")
check("写了'没有任何安排'", "没有任何安排" in t4, "")
check("有主动询问", "有要安排的事吗" in t4, "")
check("无安排字数 <= 900", len(t4) <= C.MAX_MSG_CHARS, "len=%d" % len(t4))
print("  内容:", t4.replace("\n", " / "))

print()
print("== 5. 提前提醒窗口判定（模拟 15 分钟前后）==")
now = datetime(2026, 10, 21, 14, 15)
for offset, expect in [(15, True), (13, True), (17, True), (10, False), (25, False), (1, False)]:
    sdt = now + timedelta(minutes=offset)
    lead = (sdt - now).total_seconds() / 60.0
    hit = (C.LEAD_MINUTES - 2 <= lead <= C.LEAD_MINUTES + 3)
    check("距开始 %2d 分钟 → %s" % (offset, "提醒" if expect else "不提醒"),
          hit == expect, "lead=%.0f hit=%s" % (lead, hit))

print()
print("== 6. 变更检测（新增/取消/改期）==")
old = [{"id": "1", "title": "汇报会", "start": "14:30", "end": "16:30",
        "date": str(today), "status": "pending"},
       {"id": "2", "title": "旧会议", "start": "09:00", "end": "10:00",
        "date": str(today), "status": "pending"}]
new = [{"id": "1", "title": "汇报会", "start": "16:00", "end": "18:00",
        "date": str(today), "status": "pending"},
       {"id": "3", "title": "新加的评审", "start": "11:00", "end": "12:00",
        "date": str(today), "status": "pending"}]
added, dropped, changed = W.diff_items(old, new)
check("识别新增 1", len(added) == 1 and added[0]["id"] == "3", "added=%s" % [a["id"] for a in added])
check("识别取消 1", len(dropped) == 1 and dropped[0]["id"] == "2", "dropped=%s" % [d["id"] for d in dropped])
check("识别改期 1", len(changed) == 1 and changed[0][1]["start"] == "16:00",
      "changed=%s" % [(c[0]["id"], c[1]["start"]) for c in changed])

msg = W.build_update_message(new, today, added, dropped, changed)
check("更新消息含【变动】", "【变动】" in msg, "")
check("更新消息 <= 900", len(msg) <= C.MAX_MSG_CHARS, "len=%d" % len(msg))
print("  变动段:")
for line in msg.splitlines()[:6]:
    print("    " + line)

print()
print("== 7. 30 个事项的超长日 → 截断但仍合规 ==")
many = [{"id": "m%d" % n, "title": "事项%d号标题占位内容" % n,
         "date": str(today), "start": "%02d:00" % (n % 24), "end": "%02d:30" % (n % 24),
         "status": "pending", "category": "work", "source": "manual", "plannedMinutes": 30}
        for n in range(30)]
t7, _, _, _ = C.build_today_message(many, today, "morning")
check("超长日被截断且 <= 900", len(t7) <= C.MAX_MSG_CHARS, "len=%d" % len(t7))

print()
print("=" * 46)
if FAIL:
    print("失败项 %d: %s" % (len(FAIL), FAIL))
    sys.exit(1)
print("全部通过")
sys.exit(0)
