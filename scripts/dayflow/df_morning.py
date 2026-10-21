#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""07:30 今日日程早报 → 微信

cron: 30 7 * * *
"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import df_common as C


def main():
    day = date.today()
    items = C.get_items()
    text, open_items, fixed, conf = C.build_today_message(items, day, reason="morning")
    today_items = [i for i in items if C.is_live(i) and C.on_day(i, day)]
    ok, channel = C.send(text)
    C.save_snapshot(today_items, day, source="morning")
    C.cleanup_old_state()
    print("morning day=%s today_items=%d open=%d conflicts=%d sent=%s via=%s"
          % (day, len(today_items), len(open_items), len(conf), ok, channel))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
