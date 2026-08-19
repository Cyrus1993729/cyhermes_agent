#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""OpenCode Go 用量预警 (cron no_agent: 超阈值才告警, 正常静默)
2026-08-17 DeepSeek 涨价后: Flash 月额度 $60→$15, 价格同步官方峰谷
(Peak=北京 9-12/14-18 点, Off-Peak 其余, OpenCode 官方文档价格)。
从 state.db session_model_usage 统计近 30 天 opencode-go 的 deepseek-v4-flash 用量,
按新价格两档估算月 $ 占用:
  - 低估算(全 Off-Peak) ≥70% 或 高估算(全 Peak) ≥100% → 告警
  - 其余静默
"""
import sqlite3, sys, datetime

DB = r'C:\Users\Administrator\AppData\Local\hermes\state.db'
PRICES = {  # USD / 1M tokens (OpenCode Go 2026-08-17 涨价后)
    'offpeak': {'in': 0.22, 'out': 0.66, 'cache': 0.007},
    'peak':    {'in': 0.44, 'out': 1.32, 'cache': 0.014},
}
MONTHLY_USD = 30.0   # Flash $30/月档 (2026-08-18 OpenCode"廉价搜索行动"第一阶段: $15→$30, 5h 3,800→7,600)
WARN_PCT = 70

try:
    now = datetime.datetime.now()
    cutoff = int(now.timestamp()) - 30 * 86400
    db = sqlite3.connect(DB)
    cur = db.cursor()
    cur.execute(
        """SELECT SUM(input_tokens), SUM(output_tokens), SUM(cache_read_tokens)
           FROM session_model_usage
           WHERE first_seen > ? AND model LIKE '%flash%' AND billing_provider = 'opencode-go'""",
        (cutoff,))
    tin, tout, tc = cur.fetchone()
    db.close()
except Exception:
    sys.exit(0)  # 数据库异常静默（不误报）

if not (tin or tout or tc):
    sys.exit(0)  # 无数据（观察期/迁移前）静默


def cost(p):
    return (tin or 0) / 1e6 * p['in'] + (tout or 0) / 1e6 * p['out'] + (tc or 0) / 1e6 * p['cache']


low = cost(PRICES['offpeak'])
high = cost(PRICES['peak'])
low_pct = low / MONTHLY_USD * 100
high_pct = high / MONTHLY_USD * 100

if low_pct >= WARN_PCT or high_pct >= 100:
    print(f'⚠️ OpenCode Go Flash 用量预警：近30天 ${low:.1f}-${high:.1f}（$15 月档 {low_pct:.0f}%-{high_pct:.0f}%）')
    print('   低估算(全 Off-Peak)≥70% 或 高估算(全 Peak)≥100% → 接近撞额度。排查：日报/批量任务是否撞高峰时段(9-12/14-18 点)，考虑错峰或减量。')