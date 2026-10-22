#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""每日微信日程对话交接：扫 state.db 里微信会话当天的消息，生成 handoff 摘要。

cron: 0 22 * * *
- 写 state/dayflow/handoff-<日期>.md（供总管查阅）
- stdout 只在有用户消息时输出（cron deliver=telegram，空则静默不打扰）
- 只读，不改任何业务数据
"""
import datetime
import os
import sqlite3
import sys
from pathlib import Path

HERMES = Path(os.environ.get("LOCALAPPDATA", r"C:/Users/Administrator/AppData/Local")) / "hermes"
DB = HERMES / "state.db"
OUT_DIR = HERMES / "state" / "dayflow"

# 助理自动推送的消息（不是用户对话），从交接里剔除
AUTO_PREFIX = ("今日日程", "今日收尾", "还有约", "【通道测试】")

# 日程相关关键词——用于标注"这条值得总管看一眼"
KEYWORDS = ("日程", "安排", "会议", "提醒", "完成", "复盘", "做完", "没做", "改期",
            "取消", "推迟", "几点", "明天", "今天", "下周", "参加", "汇报", "培训",
            "体检", "团建", "加班", "下午", "上午", "晚上")


def main():
    today = datetime.date.today()
    start_epoch = datetime.datetime.combine(today, datetime.time(0, 0)).timestamp()

    if not DB.exists():
        print("handoff: state.db 不存在")
        return 0

    con = sqlite3.connect(str(DB), timeout=20)
    con.row_factory = sqlite3.Row
    try:
        row = con.execute(
            "SELECT id FROM sessions WHERE source='weixin' "
            "ORDER BY last_activity_at DESC LIMIT 1"
        ).fetchone()
        if not row:
            print("handoff: 没有微信会话")
            return 0
        sid = row["id"]

        rows = con.execute(
            "SELECT role, content, timestamp FROM messages "
            "WHERE session_id = ? AND timestamp >= ? ORDER BY timestamp",
            (sid, start_epoch),
        ).fetchall()
    finally:
        con.close()

    user_msgs, bot_msgs = [], []
    for r in rows:
        text = (r["content"] or "").strip()
        if not text:
            continue
        ts = datetime.datetime.utcfromtimestamp(r["timestamp"] + 8 * 3600).strftime("%H:%M")
        if r["role"] == "user":
            user_msgs.append((ts, text))
        elif r["role"] == "assistant":
            if any(text.startswith(p) for p in AUTO_PREFIX):
                continue  # 自动推送，不算对话
            bot_msgs.append((ts, text))

    if not user_msgs and not bot_msgs:
        return 0  # 今天微信没聊过，静默

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / ("handoff-%s.md" % today.isoformat())

    lines = ["# %s 微信日程对话交接" % today.isoformat(), ""]
    lines.append("会话: %s" % sid)
    lines.append("")

    if user_msgs:
        lines.append("## 用户说了什么")
        for ts, text in user_msgs:
            lines.append("- %s  %s" % (ts, text.replace("\n", " ")[:200]))
        lines.append("")

    if bot_msgs:
        lines.append("## 秘书回了什么")
        for ts, text in bot_msgs:
            lines.append("- %s  %s" % (ts, text.replace("\n", " ")[:200]))
        lines.append("")

    flagged = [t for _, t in user_msgs if any(k in t for k in KEYWORDS)]
    if flagged:
        lines.append("## 需要总管留意的")
        for t in flagged:
            lines.append("- %s" % t.replace("\n", " ")[:200])
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")

    # stdout：有用户消息才输出（会被 cron 推到 Telegram）
    brief = ["微信日程交接 %d月%d日" % (today.month, today.day)]
    brief.append("你说了 %d 条，秘书回了 %d 条" % (len(user_msgs), len(bot_msgs)))
    for ts, text in user_msgs[-5:]:
        brief.append("· %s %s" % (ts, text.replace("\n", " ")[:60]))
    if len(user_msgs) > 5:
        brief.append("· …还有 %d 条" % (len(user_msgs) - 5))
    brief.append("明细: %s" % path.name)
    print("\n".join(brief))
    return 0


if __name__ == "__main__":
    sys.exit(main())
