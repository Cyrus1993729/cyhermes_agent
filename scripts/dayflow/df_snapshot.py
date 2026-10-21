#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""对话中改完日程后，手动刷新今日快照，避免 watch 重复推送"今日日程已更新"

用法: python df_snapshot.py
（由助理在对话里 create/patch 之后调用）
"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import df_common as C


def main():
    day = date.today()
    items = C.get_items()
    today = [i for i in items if C.is_live(i) and C.on_day(i, day)]
    C.save_snapshot(today, day, source="manual-sync")
    print("snapshot refreshed: %d items on %s" % (len(today), day))
    return 0


if __name__ == "__main__":
    sys.exit(main())
