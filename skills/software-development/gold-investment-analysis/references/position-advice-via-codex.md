# 单笔持仓的操作建议（打包喂 Codex / GPT-5.6-Sol）—— 2026-10-08 实做

## 何时用

用户报出**具体持仓**（克数 + 买入均价）并问「接下来怎么操作」。这不是周报场景——周报给的是系统评分与通用定投建议；这是**针对一个人、一笔钱、一个产品形态**的决策咨询，需要外部大模型独立研判。

典型提问：`我手里有 23 克积存金，均价 952，给我操作建议`。

## 第一步：读最新评分（不要重跑 main.py）

`C:\Users\Administrator\gold_analyzer\output\latest_weekly.json`（另外有 `output/weekly_<起>_<止>.json`、`output/archive/`）里就是最近一期的全部读数，秒读，省掉一次 300s 的全量跑：

- `composite_100` / `regime_label` / `confidence.score` / `action` / `action_label` / `suggested_allocation_pct`
- `module_scores`（七项）+ `effective_weights`
- **上海金报价三件套**：`shanghai_price_cny` + `shanghai_source`(`sge_actual`/`sge_extrapolated`/`xau_conversion`) + `shanghai_as_of`(锚日期) + `shanghai_basis_note`
- `fair_value_cny` / `action_price_guidance`
- `regime_diagnostics`：`tips_3m_bp`、`gold_1m_pct`、`dxy_1m_pct`、`gvz`、`detected_regime`

⚠️ `data/shanghai_gold.csv` **可能根本不存在**（SGE 走 akshare→外推路径时不落这个文件）——别据此判断「数据缺失」或去重建它。

## 第二步：补实时价

- **XAU 现货**：`curl -k -x http://127.0.0.1:10808 -s https://api.gold-api.com/price/XAU`（`-k` 必须，见本 skill Pitfall 29）
- **COMEX / DXY / USDCNH 近月**：读 `gold_analyzer/data/*.csv` 尾部（最后一次 main.py 留下的，够用）；或用 terminal 跑 yfinance
- 🔴 **`execute_code` 沙箱里没有 yfinance/akshare**（ModuleNotFoundError）。抓行情走 `terminal`，或只用 stdlib 的 execute_code（urllib/curl 子进程）
- 折算口径：`XAU × USDCNY ÷ 31.1035` ≈ 人民币理论价。**银行报价 = 该值 + 境内升水 + 点差**，所以理论换算价 ≠ 用户能成交的价

## 第三步：打包喂 Codex

按 `codex-cli` skill 的 **background + notify** 配方跑（`-c 'model="gpt-5.6-sol"'`，prompt 写文件走 stdin，`--sandbox read-only`）。prompt 必备六块：

1. **投资者画像 + 产品约束**：克数、均价、产品只能按现价买卖且有点差、一年只操作 1-2 次的低频约束、长期配置视角、不盯盘
2. **定价框架**：`Au ≈ f(−实际利率, −美元, +通胀预期, +央行购金, +尾部风险)`，并明说「不要用『避险』当第一解释」
3. **数据快照**：每条带日期 + 来源，并注明「按待核实草稿对待，你有联网能力，发现过时/错误请主动纠正」
4. **系统读数**：把 `latest_weekly.json` 的关键字段原文贴进去（含分项分与 `regime_diagnostics`），但提醒它独立研判、不要被锚定
5. **四个必答**：①这轮大跌归因（本轮 vs 年内整体、与 2013/2008 异同、「央行还在买为何还跌」）②未来 1-3 个月情景 + 关键价位与触发信号 ③这笔持仓的卖/持/补分档条件（给具体价位）④「如果我是你」的 30 天执行清单
6. **输出要求**：中文、事实与推测分开标注、结尾给出「你认为最关键、最可能出错的假设」

## 第四步：Codex 会打回你喂的二手数据（本次实测）

我喂的 10Y 名义收益率 4.55%、SGE 收盘 893.94 **两处都被它打回**：

| 我给的草稿 | Codex 核实值 |
|---|---|
| 10Y 名义 ≈4.55% | **5.28%**（美国财政部） |
| 实际利率 ≈2.95%（来自本系统 TIPS 缓存） | **2.92%**（10/5 曾 2.95%）；隐含通胀补偿 2.36% → 压力来自**实际利率**而非通胀预期 |
| 上金所 9/28 Au99.99 收盘 893.94 | **900.89**（SHAU 早盘/午盘 911.70/901.50） |
| 「最近一个月统一下跌 6.6%」 | WGC 9 月：美元 -8.5%、人民币 -5.5%；**ETF 净流入 67 吨、COMEX 管理资金减仓约 84 吨** → 撤的是杠杆资金，不是长期资金 |

→ **凡是二手/缓存数字，一律在 prompt 里标成草稿**，并明确邀请它联网校正。这是 `codex-cli` skill 里「GPT-5.6-Sol 会主动纠正二手数据」的再次验证，在黄金场景尤其值钱（本系统 TIPS 缓存来自 FRED、周期长，容易滞后）。

## 第五步：交付口径（本用户）

- 报告**全文内联**，不要只给摘要、也不要甩文件了事（8.5k 字 → 拆 3-4 条发）
- 开头两三句给结论 + **明确列出 Codex 纠正了哪几处数据**（用户认这个，也防止用户拿错数字去决策）
- **触发价位必须以银行 App 的实际客户买入/卖出价为准**，理论换算价只是参考
- 结尾**追问一个关键未知量**：这笔黄金占可投资金融资产的比例。占比 ≤10% 与 >15-20% 会得出**相反**的结论（继续持有 vs 逢反弹减仓）——不问清这一项，操作建议就是悬空的
- 若建议里出现可量化的触发条件（如「银行价≤860 + 实际利率<2.75% + DXY<101」），可**提议**挂进现有黄金周报 cron 做提醒。先提议，等用户点头再动（同 `decision-gate`）
- 用户会主动要「用通俗易懂的话解释一下」——术语要给白话跟随（门牌号 / 握手被掐断一类比喻）
