#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""OpenCode Go 用量预警 (cron no_agent: 超阈值才告警, 正常静默)
2026-10-08 换主模型 deepseek-v4-flash → deepseek-v4.1-flash 后同步口径:
单价 Off-Peak $0.15/$0.60/cache $0.003、Peak $0.30/$1.20/cache $0.006(与 V4 Flash 逐列相同),
月额度 $60(V4 Flash 只有 $30)。Peak=北京 9-12/14-18 点,Off-Peak 其余。
数据源: fresh curl opencode.ai/docs/go 原始 HTML 2026-10-08(勿用 web_extract, 有旧版缓存坑)。
从 state.db session_model_usage 统计近 30 天 opencode-go 的 deepseek-v4.1-flash 用量,
按新价格两档估算月 $ 占用:
  - 低估算(全 Off-Peak) ≥70% 或 高估算(全 Peak) ≥100% → 告警
  - 其余静默
"""
import sqlite3, sys, datetime

DB = r'C:\Users\Administrator\AppData\Local\hermes\state.db'
PRICES = {  # USD / 1M tokens (2026-10-08 fresh curl opencode.ai/docs/go 核实)
    'offpeak': {'in': 0.15, 'out': 0.60, 'cache': 0.003},
    'peak':    {'in': 0.30, 'out': 1.20, 'cache': 0.006},
}
MONTHLY_USD = 80.0   # DeepSeek V4.1 Flash $80/月档（2026-10-20 fresh curl 核实；此前记录 $30/$60 均已过时）
WARN_PCT = 70

try:
    now = datetime.datetime.now()
    cutoff = int(now.timestamp()) - 30 * 86400
    db = sqlite3.connect(DB)
    cur = db.cursor()
    cur.execute(
        """SELECT SUM(input_tokens), SUM(output_tokens), SUM(cache_read_tokens)
           FROM session_model_usage
           WHERE first_seen > ? AND billing_provider = 'opencode-go'
             AND model IN ('deepseek-v4-flash', 'deepseek-v4.1-flash')""",
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
    print(f'⚠️ OpenCode Go DeepSeek 用量预警：近30天 ${low:.1f}-${high:.1f}（$60 月档 {low_pct:.0f}%-{high_pct:.0f}%）')
    print('   低估算(全 Off-Peak)≥70% 或 高估算(全 Peak)≥100% → 接近撞额度。排查：日报/批量任务是否撞高峰时段(9-12/14-18 点)，考虑错峰或减量。')