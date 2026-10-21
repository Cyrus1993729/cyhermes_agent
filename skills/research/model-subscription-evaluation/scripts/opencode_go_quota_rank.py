#!/usr/bin/env python3
"""OpenCode Go 额度占用排名 —— 按本机 state.db 真实用量折算（双口径）。

用法:
    cd ~/AppData/Local/hermes && python <skill_dir>/scripts/opencode_go_quota_rank.py

何时用:
    用户问「套餐额度够不够 / 哪个模型性价比高 / 有没有更强的模型且不超限额」时，
    第一步先跑这个，拿到全部候选的占用率，再谈结论。

口径（两个都要看，结论按活跃日口径下判断）:
    30 天实际   = 窗口内真实发生 —— 窗口含停摆日时会系统性低估一个正常月份
    活跃日外推  = (活跃日 token 求和) / 活跃日数 × 30   ← 正常月份的代表值
    最重一天    = 单日最大成本，与 5h 上限（月额度 × 20%）比

依赖: 仅 stdlib。数据源: ~/AppData/Local/hermes/state.db 的 session_model_usage 表。

⚠️ 改套餐价格后要手工刷新下面 PRICES 里的数字。来源（必须 fresh curl，勿用 web_extract，会返旧版缓存）:
    curl -s --max-time 40 -x http://127.0.0.1:10808 -H "User-Agent: curl/8.0.0" \
        https://opencode.ai/docs/go/ -o go_docs.html
    然后解析 <table> 里的价格表（共 9 张表，价格表是第 4 张 = Go 计划）。
"""

import collections
import datetime
import os
import sqlite3
import sys
import time

# ---------------------------------------------------------------- 配置
PROVIDER = "opencode-go"
WINDOW_DAYS = 45          # 取数窗口（要比 30 天宽，才看得见活跃日分布）
MONTH_DAYS = 30
ACTIVE_MIN_CALLS = 20     # 当天调用数 > 此值才算「活跃日」（滤掉零星 cron）

# OpenCode Go $10/月计划价格表（$/1M tokens）—— 2026-10-20 fresh curl 现抓
# 数据源：https://opencode.ai/docs/go （跳转 /v2/docs/console/go/）
# 完整表（含 Go Plus 档、请求数、模型 ID、ZDR）：hermes-china-providers/references/opencode-go-full-quota-table-2026-10-20.md
# (名称, 输入$, 输出$, 缓存读$, 月额度$)
PRICES = [
    ("DeepSeek V4.1 Flash (Off-Peak)", 0.15, 0.60, 0.003, 80),
    ("DeepSeek V4.1 Flash (Peak)", 0.30, 1.20, 0.006, 80),
    ("DeepSeek V4 Pro (Off-Peak)", 0.66, 1.98, 0.022, 15),
    ("GLM-5.3-Flash", 0.15, 0.50, 0.03, 60),
    ("GLM-5.3", 1.40, 4.40, 0.26, 15),
    ("GLM-5.2", 1.40, 4.40, 0.26, 60),
    ("Kimi K3", 3.00, 15.00, 0.30, 15),
    ("Kimi K2.7 Code", 0.95, 4.00, 0.19, 60),
    ("LongCat-2.0", 0.30, 1.20, 0.006, 60),
    ("MiMo-V2.6-Pro", 0.435, 0.87, 0.003625, 15),
    ("MiMo-V2.6-Flash", 0.14, 0.28, 0.0028, 60),
    ("MiMo-V2.5", 0.14, 0.28, 0.0028, 60),
    ("MiniMax M3", 0.30, 1.20, 0.06, 60),
    ("Muse Spark 1.3 Contributor", 0.10, 0.20, 0.002, 60),  # 训练用数据，红线
    ("Muse Spark 1.2 Contributor", 0.10, 0.20, 0.002, 60),  # 训练用数据，红线
    ("Gemini 4 Argon Contributor", 4.00, 20.00, 0.20, 30),   # 训练用数据，红线
    ("Qwen3.8 Max", 2.00, 6.00, 0.25, 15),
    ("Qwen3.8 Flash", 0.15, 0.47, 0.016, 30),
    ("Qwen3.7 Plus", 0.40, 1.60, 0.04, 60),
    ("Qwen3.7 Plus (>256K)", 1.20, 4.80, 0.12, 60),
    ("Hy3", 0.14, 0.58, 0.035, 60),
    ("Hy4 preview", 0.834, 2.501, 0.042, 30),
    ("Step 5 Preview", 1.00, 2.70, 0.10, 15),
    ("Grok 4.7 (<=200K)", 2.00, 6.00, 0.50, 15),
    ("GPT 6 Luna (<=272K)", 0.10, 0.50, 0.01, 15),
    ("GPT 5.6 Luna (<=272K)", 0.20, 1.20, 0.02, 15),
    ("Claude Haiku 5.5 (<=100K)", 0.10, 0.50, 0.01, 15),
]

# 数据政策红线（Go 官方 ZDR 表，2026-10-20 实测）—— 命中这些的模型直接排除，不进推荐
TRAINING_ON_DATA = {
    "Muse Spark 1.3 Contributor",
    "Muse Spark 1.2 Contributor",
    "Gemini 4 Argon Contributor",
}

RED = "\u26d4"
WARN = "\u26a0\ufe0f"
M = 1_000_000


def find_db():
    home = os.environ.get("HERMES_HOME")
    cands = []
    if home:
        cands.append(os.path.join(home, "state.db"))
    cands.append(os.path.join(os.path.expanduser("~"), "AppData", "Local", "hermes", "state.db"))
    cands.append(os.path.join(os.path.expanduser("~"), ".hermes", "state.db"))
    for p in cands:
        if os.path.exists(p):
            return p
    sys.exit("找不到 state.db，试过: " + ", ".join(cands))


def load_daily(db):
    """按天聚合 opencode-go 用量。"""
    con = sqlite3.connect(db)
    cur = con.execute(
        "SELECT first_seen, api_call_count, input_tokens, output_tokens, cache_read_tokens "
        "FROM session_model_usage WHERE billing_provider = ? AND first_seen > ?",
        (PROVIDER, time.time() - WINDOW_DAYS * 86400),
    )
    by_day = collections.defaultdict(lambda: [0, 0, 0, 0])   # calls, miss, out, cache
    for ts, calls, miss, out, cache in cur.fetchall():
        d = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
        b = by_day[d]
        b[0] += calls or 0
        b[1] += miss or 0
        b[2] += out or 0
        b[3] += cache or 0
    con.close()
    return by_day


def main():
    db = find_db()
    by_day = load_daily(db)
    if not by_day:
        sys.exit("窗口内没有 %s 的用量记录" % PROVIDER)

    active = [v for v in by_day.values() if v[0] > ACTIVE_MIN_CALLS]
    if not active:
        sys.exit("没有活跃日（阈值 %d 次；调小 ACTIVE_MIN_CALLS 重试）" % ACTIVE_MIN_CALLS)

    a_calls = sum(v[0] for v in active)
    a_miss = sum(v[1] for v in active)
    a_out = sum(v[2] for v in active)
    a_cache = sum(v[3] for v in active)
    n = len(active)
    scale = MONTH_DAYS / n

    t_calls = sum(v[0] for v in by_day.values())
    t_miss = sum(v[1] for v in by_day.values())
    t_out = sum(v[2] for v in by_day.values())
    t_cache = sum(v[3] for v in by_day.values())

    print("state.db : %s" % db)
    print("窗口     : 近 %d 天，共 %d 天有记录，其中活跃日(>%d 次调用) %d 天"
          % (WINDOW_DAYS, len(by_day), ACTIVE_MIN_CALLS, n))
    print("30 天实际   : %d calls | 非缓存 %.2fM | 输出 %.2fM | 缓存读 %.1fM"
          % (t_calls, t_miss / M, t_out / M, t_cache / M))
    print("活跃日外推30天: %d calls | 非缓存 %.2fM | 输出 %.2fM | 缓存读 %.1fM"
          % (a_calls * scale, a_miss * scale / M, a_out * scale / M, a_cache * scale / M))
    print("单次均值 : 非缓存 %.0f | 输出 %.0f | 缓存读 %.0f  (缓存占输入 %.1f%%)"
          % (a_miss / a_calls, a_out / a_calls, a_cache / a_calls,
             a_cache / (a_cache + a_miss) * 100 if (a_cache + a_miss) else 0))
    print()

    rows = []
    for name, pi, po, pc, limit in PRICES:
        cost_act = (t_miss * pi + t_out * po + t_cache * pc) / M
        cost_active = (a_miss * scale * pi + a_out * scale * po + a_cache * scale * pc) / M
        pct = cost_active / limit * 100
        cap = limit / cost_active * (a_calls * scale) if cost_active else 0
        worst = max(by_day.values(), key=lambda v: v[1] * pi + v[2] * po + v[3] * pc)
        worst_cost = (worst[1] * pi + worst[2] * po + worst[3] * pc) / M
        rows.append((pct, name, cost_act, cost_active, limit, cap, worst_cost, limit * 0.20))

    rows.sort()
    print("%-30s %9s %9s %9s %7s %10s %9s %9s"
          % ("模型", "30天实际$", "活跃外推$", "占用%", "额度$", "月可支撑", "最重日$", "5h上限$"))
    for pct, name, c_act, c_act2, limit, cap, worst, h5 in rows:
        flag = ""
        if name in TRAINING_ON_DATA:
            flag = "  " + RED + " 训练用数据，红线排除"
        elif pct > 100:
            flag = "  " + RED + " 超月限"
        elif pct > 80:
            flag = "  " + WARN + " 贴顶"
        elif pct > 50:
            flag = "  " + WARN
        if worst > h5:
            flag += "  最重日>5h上限!"
        print("%-30s %9.2f %9.2f %9.1f %7.0f %10.0f %9.2f %9.2f%s"
              % (name, c_act, c_act2, pct, limit, cap, worst, h5, flag))

    print()
    print("读法：占用% 越低越划算；结论按「活跃外推」下判断（30 天实际含停摆日会低估）。")
    print("      月可支撑 = 该额度还能跑多少次我们这种请求；最重日 vs 5h 上限看会不会撞 5h 墙。")
    print("      换主力前还必须跑两个探针：带 tools 的小探针（会不会调工具）+ 流式长生成探针（快不快）。")


if __name__ == "__main__":
    main()
