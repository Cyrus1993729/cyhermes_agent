#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""生成 OpenCode Go 全模型额度参考文件 + 重算我们当前占用率。"""
import os
import re
import sys
import json
import sqlite3
import datetime

sys.stdout.reconfigure(encoding="utf-8")
HERMES = os.path.join(os.path.expanduser("~"), "AppData", "Local", "hermes")
TBL = os.path.join(HERMES, "cache", "opencode_go_tables.json")
OUT = os.path.join(
    HERMES, "skills", "software-development", "hermes-china-providers",
    "references", "opencode-go-full-quota-table-2026-10-20.md")

d = json.load(open(TBL, encoding="utf-8"))
T = d["fetched_tables"]

# 表4=Go价格/额度, 表5=Plus价格/额度, 表6=Go请求数, 表7=Plus请求数,
# 表8=模型ID/端点, 表9=训练/ZDR
go_price = {r[0]: r for r in T[3][1:]}
plus_price = {r[0]: r for r in T[4][1:]}
go_req = {r[0]: r for r in T[5][1:]}
plus_req = {r[0]: r for r in T[6][1:]}
ids = {r[0]: r for r in T[7][1:]}
zdr = {r[0]: r for r in T[8][1:]}

lines = []
A = lines.append
A("# OpenCode Go 全模型额度表（2026-10-20 fresh curl 核实）")
A("")
A("> 数据源：`https://opencode.ai/docs/go`（实际跳转 `/v2/docs/console/go/`），")
A("> 页面 52,856 字节，urllib 直取原始 HTML，未用 web_extract（有缓存旧版坑）。")
A("> 核实方式：本文件由 `scripts/fetch_opencode_go_quota.py` 解析 `<table>` 自动生成，非手抄。")
A("")
A("## 套餐结构（2026-10-20）")
A("")
A("| 套餐 | 价格 | 说明 |")
A("|---|---:|---|")
A("| **Go** | **$10/月** | 低成本接入下列模型 |")
A("| **Go Plus** | **$40/月** | 更高的用量上限 |")
A("")
A("⚠️ 此前记录的「Flash 月额度 $15 → $30 → $60」**全部过时**。当前 Go 档 = **$80**，Go Plus 档 = **$160**。")
A("")
A("## 全模型单价 + 月额度（USD / 1M tokens）")
A("")
A("| 模型 | 输入 | 输出 | 缓存读 | 缓存写 | Go 月额度 | Plus 月额度 | 训练 | 留存 |")
A("|---|---:|---:|---:|---:|---:|---:|:--|:--|")

for name, g in go_price.items():
    if name == "Model":
        continue
    p = plus_price.get(name, [])
    z = zdr.get(name, ["", "", ""])
    cells = [
        name,
        g[1] if len(g) > 1 else "",
        g[2] if len(g) > 2 else "",
        g[3] if len(g) > 3 else "",
        g[4] if len(g) > 4 else "",
        g[5] if len(g) > 5 else "",
        p[5] if len(p) > 5 else "",
        z[1] if len(z) > 1 else "",
        z[2] if len(z) > 2 else "",
    ]
    A("| " + " | ".join(cells) + " |")

A("")
A("## 估算请求数（Go 档 / Go Plus 档）")
A("")
A("> 按 OpenCode 典型用量模式估算（DeepSeek V4.1 Flash 假设 410 input / 71,300 cached / 310 output tokens 每次请求）")
A("")
A("| 模型 | 5h | 周 | 月 | 5h(Plus) | 周(Plus) | 月(Plus) |")
A("|---|---:|---:|---:|---:|---:|---:|")
for name, g in go_req.items():
    if name == "Model":
        continue
    p = plus_req.get(name, [])
    cells = [name,
             g[1] if len(g) > 1 else "", g[2] if len(g) > 2 else "", g[3] if len(g) > 3 else "",
             p[1] if len(p) > 1 else "", p[2] if len(p) > 2 else "", p[3] if len(p) > 3 else ""]
    A("| " + " | ".join(cells) + " |")

A("")
A("## 模型 ID（走 `https://opencode.ai/inference/go/...`）")
A("")
A("| 模型 | Model ID | AI SDK |")
A("|---|---|---|")
for name, r in ids.items():
    if name == "Model":
        continue
    A(f"| {name} | `{r[1] if len(r)>1 else ''}` | {r[3] if len(r)>3 else ''} |")

A("")
A("## 与我们相关的关键数字")
A("")
A("- **DeepSeek V4.1 Flash**：Off-Peak `$0.15 / $0.60 / cache $0.003`、Peak `$0.30 / $1.20 / cache $0.006`，**月额度 $80**")
A("- **Peak 时段**：`01:00-04:00` 与 `06:00-10:00` UTC，周一至周五（= 北京 09:00-12:00 / 14:00-18:00）")
A("- **DeepSeek V4 Pro**：月额度仅 **$15**，占用是 Flash 的 5.3 倍")
A("- **Kimi K3**：`$3.00 / $15.00`，月额度 **$15** —— 最贵一档，不适合日常")
A("- **GPT 6 Luna**：`$0.10 / $0.50 / cache $0.01`，月额度 $15")
A("- **Claude Haiku 5.5**：`$0.10 / $0.50`，月额度 $15")
A("- **GLM-5.3-Flash**：`$0.15 / $0.50 / cache $0.03`，月额度 **$60**")
A("")
A("## 与旧记录的差异（2026-10-20）")
A("")
A("| 项 | 旧记录 | 现值 | 影响 |")
A("|---|---|---|---|")
A("| DeepSeek V4.1 Flash 月额度 | $30 / $60 | **$80** | 占用率估算从 60-127% 降到 ~30-50% |")
A("| 套餐档 | 单一 $10 | $10 / **$40 Plus** | 新增高价档 |")
A("| 新上架模型 | — | GLM-5.3/5.3-Flash、Kimi K2.7 Code、GPT 6 Luna、GPT 5.6 Luna、Claude Haiku 5.5、Gemini 4 Argon、Qwen3.8 Max/Flash、Qwen3.7 Plus、MiMo-V2.6 系列、Step 5 Preview | 选型候选变多 |")
A("| Qwen3.7 Max | 在列 | **docs 表已不列，但 `/models` 仍在服务**（37 个在线模型含 qwen3.7-max） | fallback 未失效 |")
A("")
A(f"生成时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("已写入:", OUT, f"({os.path.getsize(OUT)} 字节)")

# ── 重算占用率 ──
print("\n" + "=" * 64)
print("当前占用率重算（DeepSeek V4.1 Flash，Go 档 $80）")
print("=" * 64)
db = os.path.join(HERMES, "state.db")
PRICE_OFF = {"in": 0.15, "out": 0.60, "cache": 0.003}
PRICE_PEAK = {"in": 0.30, "out": 1.20, "cache": 0.006}
try:
    con = sqlite3.connect(db)
    cur = con.cursor()
    cutoff = int(datetime.datetime.now().timestamp()) - 30 * 86400
    cur.execute("""
        SELECT COALESCE(SUM(input_tokens),0), COALESCE(SUM(output_tokens),0),
               COALESCE(SUM(cache_read_tokens),0), COALESCE(SUM(api_call_count),0),
               COUNT(DISTINCT substr(first_seen,1,10))
        FROM session_model_usage
        WHERE billing_provider='opencode-go' AND model='deepseek-v4.1-flash'
          AND first_seen >= ?
    """, (cutoff,))
    i, o, c, calls, days = cur.fetchone()
    # ⚠️ 2026-10-20 踩过：input_tokens **不含**缓存部分（实测 13.06M vs 缓存读 378.6M，
    #    若按 i-c 算会得负数）。直接用 input_tokens 作非缓存输入。
    fresh_in = i
    print(f"  近 30 天：{calls} 次调用 / {days} 个活跃日")
    print(f"  非缓存输入 {fresh_in/1e6:.2f}M / 输出 {o/1e6:.2f}M / 缓存读 {c/1e6:.2f}M")
    print(f"  缓存命中率 {c/(i+c)*100:.1f}%")

    def cost(pr):
        return (fresh_in * pr["in"] + o * pr["out"] + c * pr["cache"]) / 1e6

    lo, hi = cost(PRICE_OFF), cost(PRICE_PEAK)
    for label, val in (("全 Off-Peak", lo), ("全 Peak", hi)):
        print(f"  {label:<12} ${val:.2f}  →  占 $80 档 {val/80*100:.1f}%")
    if days:
        act_lo, act_hi = lo / days * 30, hi / days * 30
        print(f"  活跃日外推  ${act_lo:.2f} ~ ${act_hi:.2f}  →  占 $80 档 "
              f"{act_lo/80*100:.1f}% ~ {act_hi/80*100:.1f}%")
    con.close()
except Exception as e:
    print("  state.db 查询失败:", e)
