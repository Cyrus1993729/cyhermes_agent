---
name: gold-investment-analysis
description: "【黄金积存金七因子打分系统】已落地的黄金专属评分+周报+cron 自动推送。| 跟 investment-analysis 的区别：那个是「怎么搭一个框架」的通用方法论，这个是已经做好的黄金专用系统。跟 gold-macro-framework 的区别：那个是宏观定价公式和传导机制分析，这个是量化打分+自动化报告。"
version: 3.3.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [gold, investment, scoring, china, data-fetching, yfinance, akshare, fredapi, synthesis, weekly, geopolitical]
    extends: [investment-analysis]
---

> **Prerequisite:** Before executing this skill, load `gold-macro-framework` for the pricing formula (Au ≈ f(−Real Rates, −USD, +Inflation, +CB Buying)) and transmission channel analysis.
---

# Gold Investment Analysis System v3.1

Build and operate automated gold investment analysis for 积存金 (Chinese gold accumulation plans). Covers the full pipeline: data fetching → seven-factor scoring → regime detection → signal layering → confidence scoring → synthesis generation → actionable recommendations.

## When to Use

When a user asks for:
- Gold price analysis or investment recommendations
- Automated trading signal systems for gold
- 积存金 strategy design
- Multi-factor scoring models combining macro/technical/sentiment/valuation/central-bank/china-domestic/geopolitical dimensions
- Weekly analytical report generation with news + quantitative analysis
- Cron-automated recurring investment reports

## Conceptual Framework

**Quantitative scoring is half the job. Before running the numbers, establish the macro conceptual framework.**

For gold price movement analysis (especially event-driven moves), load `gold-macro-framework` skill FIRST. It provides:
- Core pricing formula: Au ≈ f(−Real Rates, −USD, +Inflation Expectations, +CB Buying, +Tail Risk)
- Transmission channel analysis (rates, dollar, inflation, CB, geopolitics)
- Cross-asset triangulation (stocks + bonds + gold + silver + BTC)
- Distinction between "market's pricing of an event" vs "the event itself"

The seven-factor model is the **quantitative execution** of this framework. But if you start with the numbers without the conceptual lens, you'll fall into the "safe haven" trap — attributing every gold move to risk appetite instead of tracing the actual rate/dollar/inflation transmission chain.

Case study: `~/.hermes/references/gold-6-19-case-study.md`

## User Preferences

- **Output in Chinese** — all reports, signals, and explanations must be in Chinese
- **0-100 score scale only** — NOT `[-2, +2]`. Display as `47.9/100`, not `-0.08 [-2,+2]`. Internal computation still uses [-2,+2] but user-facing output is 0-100 only.
- **Signals need analysis, not just labels** — each signal must include specific data values and causal reasoning, not just a name + score
- **Comprehensive synthesis over signal listing** — the final output must include analytical narrative (five-paragraph synthesis), not just a list of bullish/bearish signals. Signals are input, synthesis is reasoning, recommendation is output.
- **Weekly reports, NOT daily** — monthly-frequency data (M2, PBOC reserves, TIPS trend) pollutes daily scores. Weekly with weight decay is the correct frequency. Reports go out Monday 8:00 AM via cron.
- **Confidence must be honest** — low confidence (40-59) when signals are conflicted is correct behavior, not a bug. Do not artificially boost confidence.
- **Concise in chat** — keep WeChat messages compact, use markdown for readability
- **Full report, not diff** — when delivering the weekly report, always present the COMPLETE formatted output. Never show only a comparison table, change summary, or partial excerpt. The user wants the full report as one piece, not snippets that require piecing together. If the user asks for a report update, deliver the entire thing.

## Architecture: Seven-Dimension Scoring with Weekly Cadence

```
┌──────────────────────────────────────────────────────┐
│           Gold Scoring Engine v3.1                    │
│                                                      │
│  Macro(20%) + Technical(15%) + Sentiment(10%)        │
│  + Valuation(15%) + CB(20%) + ChinaDomestic(10%)     │
│  + Geopolitical(10%)                                 │
│                    ↓                                 │
│           Composite [-2, +2] → [0-100]               │
│                    ↓                                 │
│    Signal Layering (L1/L2/L3) + Confidence           │
│                    ↓                                 │
│    Data Freshness Decay (monthly modules)            │
│                    ↓                                 │
│    Five-Paragraph Synthesis + News Integration       │
└──────────────────────────────────────────────────────┘
```

### Seven Dimensions

| Dimension | Weight | Key Indicators |
|-----------|--------|----------------|
| Macro Environment | 20% | 10Y TIPS real yield, DXY, Fed policy (2Y-10Y spread), fiscal/GPR |
| Technical Trend | 15% | 50-week MA, MACD weekly, RSI weekly, ADX |
| Sentiment & Positioning | 10% | COT report, GLD ETF flows, gold/silver ratio |
| Valuation | 15% | Fair value residual (TIPS+DXY regression), gold/M2, gold/SPX, gold/oil |
| Central Bank Behavior | 20% | PBOC reserve changes (akshare), gold-DXY decoupling proxy, price resilience |
| China Domestic Demand | 10% | Shanghai premium vs London, RMB FX impact, domestic gold ETF flow |
| **Geopolitical Risk** | **10%** | Oil-gold resonance (DXY-orthogonalized), precious metal divergence (Au-Ag spread), GVZ excess premium |

### Signal Layering (L1/L2/L3)

Every sub-signal is classified by half-life:

| Layer | Chinese Label | Half-Life | Examples |
|-------|--------------|-----------|----------|
| **L1** | 短期扰动 | 1-10 days | MACD, RSI, COT positioning, ETF short-term flows, Shanghai premium, oil-gold resonance, GVZ premium |
| **L2** | 中期驱动 | 1-6 months | Real yield trend, DXY direction, MA position, fair value residual, GSR, PM divergence |
| **L3** | 结构性锚 | 1+ years | PBOC reserve trend, fiscal/GPR, gold resilience vs equities |

**Layer conflict handling**: When L1 contradicts L2/L3, L1 is treated as noise. L3 direction changes require 3 consecutive confirmations.

### Confidence Scoring (Four Dimensions, 0-100)

| Dimension | Max | Method |
|-----------|-----|--------|
| A: Signal Consensus | 25 | % of strong signals pointing same direction |
| B: Layer Alignment | 25 | L1/L2/L3 direction consistency |
| C: Signal Strength | 25 | Average absolute signal magnitude (proxy for decisiveness) |
| D: Data Quality | 25 | Completeness ratio across all components |

**Key insight**: Low confidence when signals are conflicted is **correct behavior, not a bug**. The confidence score is a truthfulness mechanism — it tells the investor when the market itself is unclear.

### Data Freshness & Weight Decay

Monthly-frequency data (M2, PBOC reserves, TIPS trend) decays in weight over time:

| Days Since Update | Weight Factor |
|-------------------|---------------|
| 0-7 days | 100% |
| 8-14 days | 80% |
| 15-30 days | 60% |
| 30+ days | 40% |

Affected modules: **macro** and **central_bank**. Other modules use weekly/daily data — no decay.

The weekly report displays a freshness panel:
```
【数据新鲜度】
  宏观环境: 上次更新 2026-05-25（9天前）→ 权重衰减至 80%
  央行行为: 上次更新 2026-05-08（26天前）→ 权重衰减至 60%
```

### Weekly Report Flow (Monday 8:00 AM Cron)

```
Step 1: News Recap — web_search (do NOT use delegate_task or execute_code)
  Use web_search for news headlines. delegate_task fails ~66% ("Authentication Fails"),
  and execute_code is BLOCKED in cron context. web_search is the only reliable option.
  ├─ Gold price + macro: "gold price June 2026" + "Federal Reserve rate June 2026"
  ├─ Geopolitical: "Israel Iran Middle East conflict June 2026"
  └─ China demand: "China gold demand Shanghai June 2026"
  
  delegate_task with web toolset fails ~66% of the time ("Authentication Fails (governor)").
  The curl + proxy approach is reliably available from cron.

Step 2: Quantitative Analysis (python main.py with proxy)
  └─ HTTP_PROXY=http://127.0.0.1:7897 HTTPS_PROXY=http://127.0.0.1:7897 python main.py

Step 2.5: Data Validation (see references/data-validation.md)
  ├─ 3.1 COMEX vs spot: gold-api.com may be blocked in China — skip if timeout. GC=F is reliable.
  ├─ 3.2 CNY conversion: formula is COMEX/31.1035 × USDCNH. System auto-computes in fetch_shanghai_gold().
  ├─ 3.3 Shanghai gold freshness: auto-handled by data_fetcher.py (see references/shanghai-gold-conversion.md)
  └─ 3.4 If FRED missing: check `pip list | grep fredapi` — package may not be installed even with .env key

Step 3: Integrated Report
  ├─ 本周要闻 (3-5 events, dated, factual only — from Step 1 headlines)
  ├─ 量化分析 (full main.py output, validated)
  └─ 综合研判 (cross-reference news + quantitative signals)
```

## Report Frequency Design Principle

**The enemy of accuracy is not frequency, but fake synchronization.** 

Old daily reports polluted 40% of the composite score with month-old data pretending to be "today's analysis." The correct approach:
- Weekly report (Monday) as primary output
- COT captures the only truly weekly data
- Monthly dimensions explicitly labeled with age and decay-weighted
- No daily reports — they create false certainty

### ⚠️ 交付前审查要求（2026.7.13 确立）

黄金周报属于投资分析类报告，**必须经过双审才能交付**：

1. **L1（千问 3.7 Max）**：形式审查 + 数据逻辑审查。当前 RUBRIC 已升级为四维度（含符号方向/跨小节勾稽/口径一致性/基本算术），脚本 `qwen_review.py` timeout=300s。CONDITIONAL < 3 且无 FAIL 时通过。
2. **Opus（Claude Code）**：实质准确性的最终 sign-off。L1 擅长形式和数据逻辑，但数值深度自洽（三数互洽、多口径交叉验证）是 Opus 的强项。**投资分析类报告不经 Opus PASS 不交付。**

典型审查分工：
- L1：符号方向（他写的+0.14%对吗？）、术语一致性（两处同概念用词统一吗？）、完成度（缺URL吗？）
- Opus：数据逻辑深度自洽（GC=F基准的价差和XAU基准的价差勾稽吗？）、投资逻辑合理性（估值便宜为什么不加码？）

> 教训来源：2026.7.13 黄金周报 L1 审查 6 轮未发现 +0.14%→−0.14% 符号错误和"折价"vs"估值偏离"术语混用，Opus 第 1 轮即发现。详见 `lessons.md` L9。

### ⚠️ 契约创建规范（2026.7.21 Opus 审查确立）

创建黄金周报契约时，须对照 [`references/contract-checklist.md`](references/contract-checklist.md) 确保 8 项必修已入契：
①USDCNH+CNH-CNY基差 ②统一时点快照 ③评分公式+权重 ④模型公允价值来源 ⑤定投去产品化 ⑥D4判定阈值表 ⑦双审终止条件 ⑧补发标注+投递确认。

**缺失任一项 = 契约不合格，Opus 必判 CONDITIONAL。**

## Data Source Patterns

### yfinance: ALWAYS use Ticker API with Session

**Never use `yf.download()`** — it triggers aggressive rate limiting (especially from China). Use `yf.Ticker(ticker, session=requests_session).history()` instead.

```python
import requests
import yfinance as yf

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})
session.get('https://finance.yahoo.com', timeout=5)  # pre-warm

tk = yf.Ticker("GC=F", session=session)
df = tk.history(period="2y", interval="1d", auto_adjust=False)
```

Retry with exponential backoff (4 retries, 5s base). 2s inter-call cooldown. Cache as CSV with 1-day TTL, force DatetimeIndex and strip timezone on load.

### akshare: Shanghai Gold Column Mapping

`ak.spot_golden_benchmark_sge()` returns Chinese column names. Rename to English:
```python
col_map = {'交易时间': 'Date', '晚盘价': 'Evening', '早盘价': 'Close'}
df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
```

For PBOC gold reserves, try multiple akshare functions in order: `macro_china_gold_reserve()`, `macro_china_fx_gold()`, `macro_china_foreign_exchange_gold()`, `gold_reserve()`, `gold_holding()`.

### FRED API: Setup

1. Register at https://fred.stlouisfed.org/docs/api/api_key.html
2. **Store the key in `.env` file at project root** — never hardcode it:
   ```
   FRED_API_KEY=your_32_char_key_here
   ```
3. **Add `.env` auto-loading to `config.py`** (before any `os.environ.get()` call). Use a no-dependency parser — do NOT require `python-dotenv`:
   ```python
   from pathlib import Path
   _ENV_PATH = Path(__file__).resolve().parent / ".env"
   if _ENV_PATH.exists():
       with open(_ENV_PATH, encoding="utf-8") as _f:
           for _line in _f:
               _line = _line.strip()
               if not _line or _line.startswith("#") or "=" not in _line:
                   continue
               _k, _, _v = _line.partition("=")
               _k, _v = _k.strip(), _v.strip().strip('"').strip("'")
               if _k and _k not in os.environ:
                   os.environ[_k] = _v
   ```
   This ensures the key is available in ALL contexts — manual runs AND cron jobs. Cron jobs run in fresh sessions and do NOT inherit the parent session's environment variables. The `.env` file is the only reliable cross-context mechanism.
4. Key series: `DFII10` (10Y TIPS), `M2SL` (M2), `T10Y2Y` (2Y-10Y spread)
5. TIPS yield from FRED is in percentage form (e.g., 2.07 for 2.07%) — do NOT multiply by 100 for display

### China Domestic: Sina API for ETF Data

For Chinese gold ETF volume data, Sina Finance API is more reliable than akshare (bypasses Clash TUN interception):
```python
url = "https://stock.finance.sina.com.cn/fundInfo/api/openapi.php/CaihuiFundInfoService.getNav"
# Fetch 518880 (华安黄金ETF) and 159937 (博时黄金ETF)
```

### Dual-Network Proxy Pattern

yfinance/FRED → needs proxy. akshare/eastmoney.com → needs DIRECT. Use Clash rule mode: `eastmoney.com` → DIRECT, everything else → proxy.

### Geopolitical Module: Three Market-Price Proxies

All signals DXY-orthogonalized to avoid double-counting with macro module:

1. **Oil-Gold Resonance (40%)**: DXY-orthogonalized oil+gold co-move, amplified when equities decline. Captures Middle East conflict fingerprint.
2. **Precious Metal Divergence (35%)**: Gold vs Silver 20-day return spread Z-score. Naturally DXY-orthogonal (both USD-priced). High spread = pure safe-haven demand.
3. **GVZ Premium (25%)**: GVZ excess over SPX-vol-expected level, filtered by gold direction. Rising gold + high GVZ excess = geopolitical tail-risk pricing.

## Project Convention

Reference implementation at `C:\Users\Administrator\gold_analyzer\`:
- `config.py` — weights (7-dim), threshold configs, ticker symbols, weight decay schedule, env-var-driven API keys
- `data_fetcher.py` — unified data fetching with cache, retry, session management, dual-network routing
- `macro.py`, `technical.py`, `sentiment.py`, `valuation.py`, `central_bank.py`, `china_domestic.py`, `geopolitical.py` — per-dimension scorers
- `scorer.py` — composite scoring + regime detection + signal layering + confidence + freshness decay + synthesis
- `main.py` — weekly report entry point, formats Chinese report, saves JSON + archives

Run weekly report with:
```bash
cd C:\Users\Administrator\gold_analyzer
HTTP_PROXY=http://127.0.0.1:7897 HTTPS_PROXY=http://127.0.0.1:7897 python main.py
```
**Always include the proxy env vars.** yfinance will rate-limit without them; the run will time out after 300s.

Cron job for automated weekly delivery:
- Job ID: `54117ed8a949`
- Schedule: `0 8 * * 1` (Monday 8:00 AM CST)
- Delivers to: **Telegram**（2026.7.13 已从微信迁移，原因：微信 iLink 10条/轮硬限制导致长报告被吞）
- Workflow: 5-step sprint (sprint-contract → decision-gate → execute → task-wrapup+L1 → post-task-review)
- Skills loaded: sprint-contract, task-wrapup, post-task-review, l1-review
- Toolsets: terminal, file, web

**CRITICAL for Cron**: Never use `execute_code` or `delegate_task` in the cron prompt — both are blocked in cron context ("Cron jobs run without a user present to approve"). Use `web_search` for news and `terminal` for all commands. The cron job's prompt must explicitly say "不要用 execute_code" and "不要用 delegate_task".

## Claude Code as Design Consultant

When significant architectural changes are needed (not code, but design), use Claude Code as a consultant:

```bash
export HTTP_PROXY=http://127.0.0.1:7897
export HTTPS_PROXY=http://127.0.0.1:7897
claude --dangerously-skip-permissions -p "设计问题描述（中文）" 
```

Claude Code is used for: framework design, model review, analytical logic critique, report frequency analysis. It is NOT used for writing implementation code — Hermes Agent handles all code changes.

## Pitfalls

1. **yfinance rate limiting**: `yf.download()` fails silently. Always use `Ticker(session=...).history()` with retry.
2. **akshare column names**: Chinese names change between versions. Inspect raw output before mapping.
3. **Cache timezone**: CSV round-trips lose timezone. Force `tz_localize(None)` after loading.
4. **FRED TIPS yield units**: Returns percentage (2.07 = 2.07%), not decimal. Don't multiply by 100 for display.
5. **TIPS trend window**: Use fixed 63-day window, NOT `len/2` split (which varies by data availability).
6. **Decoupling double-counting**: Gold-DXY decoupling is checked in both macro and central_bank modules. Ensure scoring logic avoids double-counting.
7. **Signal dampening**: Use 70/30 EMA weighting for direction changes, not 50/50 mean. After 2+ consecutive periods in same direction, trust the signal.
8. **ETF volume alignment**: Domestic ETF volumes have different date indices — use `pd.concat().sum(axis=1)` for proper alignment.
9. **Fair value price guidance**: Always anchor price suggestions to fair value, even when composite score > 1.0. Never suggest buying above fair value.
10. **No scipy**: Use numpy for all statistical computations.
11. **Daily reports are WRONG**: 40% of model weight (macro + CB) uses monthly data. Daily reports create false certainty. Use weekly only.
12. **Confidence is honesty, not quality**: Low confidence during conflicted signals is correct. Don't boost it.
13. **Python string escaping**: When using patch tool for Python files, avoid backslash-escaped quotes (`\\\"`) — use unescaped quotes in old_string/new_string.
14. **scorer.py format string crash on missing FRED data**: `_explain_signal` for `fed_policy` does `f"{sp:.2f}%"` on the 2Y-10Y spread, but when FRED_API_KEY is unset, `sp` can be a string like `"no_data"` — causes `ValueError: Unknown format code 'f' for object of type 'str'`. Fix with `try: sp_val = float(sp)` / `except (ValueError, TypeError):` fallback. See the `_explain_signal` method around line 374. This bug silently breaks the entire report generation.
15. **auto_adjust=True on futures distorts prices**: `tk.history(auto_adjust=True)` on futures contracts (GC=F, SI=F, CL=F) applies contract-roll adjustment, which shifts historical prices to match the front-month contract — creating systematic price drift vs actual spot/market prices. **Always use `auto_adjust=False` for futures tickers.** The `_yf_download` method in data_fetcher.py must pass `auto_adjust=False`. After the fix, clear all yfinance caches (`gold_price.csv`, `dxy.csv`, `oil.csv`, `silver.csv`, `gld.csv`, `gvz.csv`, `sp500.csv`) before re-running — stale adjusted prices will persist in cache for up to 24 hours.
16. **auto_adjust=False returns Adj Close column → duplicate rename collision**: When `auto_adjust=False`, yfinance returns BOTH `Close` and `Adj Close` columns. The column rename logic in `_yf_download` matches "close" against both, creating duplicate "Close" columns. Then `df['Close']` returns a DataFrame (not Series), causing `float() argument must be a string or a real number, not 'Series'` in `safe_pct_change`. Fix: in the rename loop, match "adj close" / "adj" FIRST and drop those columns before renaming the remaining "Close".

17. **Shanghai gold data can lag 2-4 days behind COMEX** — **FIXED in v3.1: automatic conversion fallback**. akshare's SGE data (`spot_golden_benchmark_sge()`) typically lags 1-2 trading days, and can stretch to 6+ days. The `fetch_shanghai_gold()` method now:
   - Checks cache freshness: if last date > 2 days old, re-fetches from akshare
   - If akshare returns stale data (>2 days old), automatically falls back to `_fetch_shanghai_from_xau_conversion()`
   - Conversion formula: `GC=F Close / 31.1035 × USDCNH Close` — uses yfinance cache (gold.csv + usdcnh.csv), NO external API calls
   - The converted row is appended to the DataFrame and cached alongside real SGE rows
   - **No "估算" label** — the conversion is treated as a valid data source, not an inferior estimate
   
   When the cron report says "SGE data X days old, will supplement with conversion", this is NORMAL behavior — no manual intervention needed. The `_fetch_shanghai_from_xau_conversion()` method is in `data_fetcher.py`.

18. **USDCNH must be fetched fresh alongside COMEX for conversion**: When computing the synthetic Shanghai price, always fetch the latest USDCNH (via `CNH=X` from yfinance) at the same time as COMEX gold. Do not use a stale cached rate or a hardcoded value. The conversion formula is `COMEX_USD / 31.1035 × USDCNH` — a 0.1 CNY error in the rate translates to ~¥14/克 error in the price. **When yfinance CNH=X fetch fails** (returns empty data), the model falls back to stale `data/usdcnh.csv` cache. After fixing SGE data with external-rate conversion, the re-run premium may still be wrong for two reasons: (a) CNH rate mismatch between external API and model's internal cache, or (b) 5-day premium average contaminated by residual stale SGE data. See data-validation.md Gate 2b for the full diagnostic workflow, including how to distinguish the two root causes and when a fix is actually needed vs. when it self-corrects.

19. **PBOC reserves scoring must combine MoM + YoY, not binary recent-vs-prev**: The original `score_pboc_reserves()` in `central_bank.py` used a naive binary: `recent > prev ? +1.0 : -1.0`. A -0.99% MoM dip in a +40% YoY uptrend was scored identically to a genuine trend reversal. The fix uses the `黄金储备-同比` column (available from `ak.macro_china_fx_gold()`) to contextualize the MoM change. **The user explicitly rejected classifying a -0.99% MoM dip in a +40% YoY trend as negative** — such small monthly fluctuations are noise, not signals. Final thresholds:
    - MoM decrease + YoY > 20% + |MoM| < 1.5% → **+0.3** (strong uptrend, monthly noise — STILL POSITIVE)
    - MoM decrease + YoY > 20% + |MoM| < 3.0% → **0.0** (dip in uptrend, neutral)
    - MoM decrease + YoY > 20% + |MoM| >= 3.0% → **-0.3** (notable dip in uptrend)
    - MoM decrease + YoY < -5% → **-1.5** (genuine trend reversal)
    - MoM increase + YoY > 10% → **+1.0** (buying within strong trend)
    - MoM increase + YoY > 0% → **+0.8** (buying, modest trend)
    - Flat MoM + YoY > 10% → **+0.3** (steady accumulation)
    The akshare dataframe has `黄金储备-同比` and `黄金储备-环比` columns — use them.
    
20. **DXY scoring must be trend-adjusted, not purely level-based**: The DXY threshold table gives +2.0 for any reading < 100 (incl. 99.95) and +1.0 for 100-103. But a DXY at 99.95 that has risen 1.7% in the past month is fundamentally different from a DXY crashing from 105 to 97. The fix in `macro.py:score_dxy()`:
    - Compute 1-month DXY change via `safe_pct_change(dxy_df, col, window=21)`
    - If DXY has risen > 2% in a month → dampen level score by -1.0
    - If risen 1-2% → dampen by -0.5
    - If fallen < -2% → amplify by +1.0
    - Replace the old `decoupling_bonus` logic (which checked gold+DXY co-move) with this trend adjustment
    The signal explanation text must reflect the trend: "美元指数 99.95（近1月走强1.7%），虽处低位但趋势走强，对黄金的实际利好被削弱"

21. **COT signal explanation must distinguish net-long neutral from "净空"**: The original `_explain_signal` for COT used `score < 0 ? '偏重' : '偏轻或净空'`. For score=0 (176k net long), this falsely said "或净空" when the position was clearly net long. The fix splits into three cases:
    - score < 0 → "投机持仓偏重，利空后续加仓"
    - score > 0 → "持仓偏轻，有加仓空间，利于后续加仓"  
    - score == 0 → "持仓适中，利于后续加仓"

22. **real_yield signal explanation must handle missing FRED data**: When FRED_API_KEY is unset, `current_yield` is None. The old ternary `score>0 ? '走低利好' : '偏高利空'` falsely said "偏高利空" when there was no data. Fix: `score>0 ? '走低利好' : (score<0 ? '偏高利空' : '数据不可用')`. The fed_policy component has a similar issue (pitfall 14 — string format crash on `no_data`).

- **News from delegated subagents is NOT verified fact**: When the cron job uses delegate_task to search for weekly news, subagents can hallucinate specific numbers (e.g., "增持32万盎司" when akshare shows a decrease). Cross-check all subagent-sourced news against quantitative data. If news says "中国央行增持" but pboc_reserves signal shows a MoM decrease → the news is wrong, use the quantitative data. The 综合研判 section must reconcile news-data contradictions explicitly rather than papering over them.

25. **News timeline construction MUST verify pubDate before building narrative**: Google News RSS returns articles from ALL dates that match keywords via `<pubDate>` tags. A Warsh-nomination article from January 2026 can appear alongside FOMC articles from June 2026 because both contain "Warsh". **Before constructing any event timeline**: (a) extract ALL `<pubDate>` values from the RSS feed; (b) filter to articles within the target window; (c) convert GMT to Beijing time (+8h); (d) distinguish "event occurrence time" from "article publication time" (analysis pieces are published hours after the event); (e) if an article's pubDate does NOT fall in the target window, either drop it or explicitly label it as "background/旧闻". Classic failure mode: seeing "Silver plunges 30% in worst day since 1980" in search results and placing it on last night's timeline when the article is 5 months old — keywords matched, pubDate was never checked. See `references/timeline-verification.md` for the full protocol.

26. **Gold price moves are primarily driven by REAL RATES and the DOLLAR, not safe-haven demand**: The user explicitly rejected "safe-haven" as a shallow analytical framework. Gold's price function is: **Gold ≈ f(−real_yield, −DXY, +inflation_expectations, +central_bank_structural_buying, +tail_risk_premium)**. "Safe haven" is only the last, smallest term. When analyzing any gold price move: (a) FIRST ask what real yields and the dollar are doing; (b) distinguish "good" rate rises (growth-driven → stocks up, gold down) from "bad" rate rises (stagflation-driven → everything down); (c) a geopolitical event can move gold through the RATES CHANNEL (e.g., peace deal → lower oil → lower inflation expectations → market prices in Fed dovish → lower yields → gold UP) — this looks like a "safe haven" move but the mechanism is rates, not fear. The 2026-06 Iran peace deal → gold SURGE to ¥950 is the canonical example: markets mispriced "Iran deal = Fed will cut" and gold rallied on rate-cut expectations, not on war fears. When the FOMC proved hawkish, the entire thesis collapsed and gold fell to ¥911. The supply-side vs demand-side inflation distinction is key: markets read lower oil as "inflation falling → Fed can ease"; the Fed reads it as "purchasing power rising → core inflation stickier → rates must stay high." **Coding note**: the geopolitical module already uses DXY-orthogonalized signals (oil-gold resonance, Au-Ag divergence, GVZ premium) which partially captures this — but the SYNTHESIS in scorer.py must explicitly test whether gold moved WITH or AGAINST the safe-haven prediction before labeling any move as "避险".

24. **Price guidance uses china_domestic score, not overall composite**: In `china_domestic.py:compute_price_guidance()`, the `composite` parameter determines the verb (积极加仓/正常定投/等待回调/暂停) and price range. The original `scorer.py:run_analysis()` passed `china_score` (+0.86, almost always bullish) instead of the overall composite (typically 0.0-0.2, neutral). This made the 💰 guidance line ALWAYS say "正常定投" regardless of the actual action recommendation. **Symptom**: "维持观望, 定投50%" paired with "建议在 ¥X-Y/克 正常定投" — the verb contradicts the action. **Fix**: in scorer.py, after computing the overall `composite`, call `self.china.compute_price_guidance(au9999_df, gold_df, usdcnh_df, composite)` with the OVERALL composite and use that result for both the synthesis and the result dict. The result dict's `action_price_guidance` key must also use the corrected value, not `china_bd.get("action_price_guidance")`.

25. **COMEX futures (GC=F) ≠ spot gold (XAU) — the report headline price is futures, not spot**: `main.py` pulls GC=F from yfinance — this is the COMEX futures contract, which normally trades at a contango (premium) to spot. The weekly report header reads "📊 最新金价: $4,XXX | ¥XXX/克" but silently uses the futures price. This can cause a ~$20-30/oz (≈1.5-2.5%) discrepancy vs live spot, which compounds in the CNY conversion (`GC=F / 31.1035 × USDCNH`). For example, COMEX $4,208 → ¥943/克 vs spot $4,186 → ¥911/克 — a ¥32/克 gap that a retail investor will notice and challenge. **When the user asks for "最新金价" or "此时此刻的数据", they expect SPOT, not futures.** The fix: (a) in the report header, label the price as "COMEX 期货" not "最新金价"; (b) fetch spot from `https://api.gold-api.com/price/XAU` alongside the futures data and show both; (c) use spot × USDCNH for the CNY conversion when responding to real-time price queries. The scoring model can continue to use COMEX futures for consistency (trend analysis, MA, MACD are all computed on GC=F), but the user-facing price number must match what they see on their trading app.

24.5. **Cron jobs run in fresh sessions with NO inherited env vars**: `export FRED_API_KEY=...` in your terminal works for manual runs but cron jobs start from a clean environment. The only reliable cross-context mechanism is a `.env` file loaded by the application at startup. Any API key, proxy config, or credential needed by a cron job MUST live in the project's `.env` file, not just in the parent session's environment. See the FRED API Setup section for the no-dependency `.env` loader pattern.

26. **News article pubDate MUST be extracted and verified before constructing event timelines — never mix old articles into "current" narratives**: Google News RSS returns articles from a broad date range — a search for "gold June 2026" can return results from January, March, or any month with keyword matches. When constructing an event timeline (e.g., "what happened last night"), you MUST: (a) extract `<pubDate>` from every RSS `<item>`; (b) filter to only articles whose pubDate falls within the claimed event window; (c) convert all times to a single timezone (Beijing = GMT+8) before presenting to the user; (d) distinguish between "event articles" (published within hours of the event) and "analysis/retrospective articles" (published 1-2 days later with deeper context but not first-hand reporting). **DO NOT cite an article as evidence for "last night's events" unless its pubDate is within ~24 hours of the claimed event window.** Failure mode: "Silver plunges 30% worst day since 1980" (pubDate Jan 30, 2026) and "Gold drops to one-month low" (pubDate Mar 18, 2026) were incorrectly attributed to June 18-19 because pubDate was not checked. The user caught the error and explicitly questioned the timeline. **Always present the timeline with verified timestamps**, and when the user questions a date, re-verify rather than defending the claim.

27. **FOMC timing and multi-wave market reactions must be clearly separated**: Major central bank decisions (FOMC, ECB, PBOC) trigger market reactions in distinct waves — (Wave 1) immediate algorithmic response at announcement, (Wave 2) Asian/European session digestion, (Wave 3) US session institutional repricing when full implications sink in. When a user asks "what happened last night," identify WHICH wave they're asking about. The FOMC decision itself may have been 24-30 hours earlier; the overnight move they're seeing is often Wave 2 or Wave 3. Failure mode: attributing the FOMC press conference itself to "last night" when it was 30 hours prior, conflating cause and delayed effect. Verify: FOMC statement release time (typically 14:00 ET on Day 2) → convert to Beijing → compare against the user's "last night" window. See references/cron-news-search.md for timezone conversion patterns.

28. **Manual CNH CSV rows MUST use yfinance's multi-column format**: When `CNH=X` fetch fails (common from China), the model falls back to `data/usdcnh.csv`. If you manually add a row, the format must match yfinance's output exactly: `Date,Open,High,Low,Close,Volume,Dividends,Stock Splits` with values like `2026-06-22 00:00:00+00:00,6.78,6.78,6.78,6.78,0,0.0,0.0`. A plain 2-column `Date,Close` row will cause the Close column to be mis-parsed as NaN, producing wildly incorrect Shanghai premium values (e.g. -7.2% instead of ~0%). Always verify with `tail -3 data/usdcnh.csv` after editing. Use the external CNH rate from `https://api.exchangerate-api.com/v4/latest/USD` (field `rates.CNH`, not `rates.CNY`) — the model uses offshore CNH for premium calculation.

29. **gold-api.com has SSL certificate issues — use `curl -k` for manual validation**: The API `https://api.gold-api.com/price/XAU` returns SSL errors (exit code 35) from mainland China networks with standard curl. However, it works with `curl -k` (insecure SSL). The gold analyzer's `data_fetcher.py` uses yfinance GC=F + USDCNH cache instead, which has zero external API dependencies for automated paths. **For manual D4 validation only**: use `curl -k -x http://127.0.0.1:7897 -s "https://api.gold-api.com/price/XAU"` to get XAU spot for basis calculation. Never use gold-api.com in automated code paths — only for D4 spot-checks during manual report runs.

30. **fredapi package may not be installed even when .env has the key**: The FRED_API_KEY in `.env` is loaded by `config.py`, but `from fredapi import Fred` requires the `fredapi` PyPI package (`pip install fredapi`). If FRED data shows "不可用" in the report, run `python -c "from fredapi import Fred"` first — a `ModuleNotFoundError` means the package needs installation, not a key problem. The key alone is not sufficient.

31. **delegate_task subagents FABRICATE data when web search is unavailable**: On 2026-06-22, a delegate_task subagent was dispatched with `web` toolset to search for gold news. It returned fabricated data (gold price at $2,800 vs actual $4,154), explicitly admitting "缺乏实时网络访问，以下为基于典型市场逻辑构建的合理事件". The subagent's summary showed `api_calls=1` — it made one API call, found nothing, and invented plausible-sounding results. **Rule**: NEVER trust delegate_task subagent news summaries. Cross-check EVERY subagent-sourced number against quantitative data (main.py output). If subagent results contradict the model's actual data, the subagent is wrong — use the quantitative data. This is a stronger instance of the existing pitfall "News from delegated subagents is NOT verified fact" — subagents don't just get facts wrong, they can fabricate entirely.

32. **Google News RSS via curl is the reliable fallback when web_search is unavailable**: `web_search` tool may be absent in some environments (e.g., WeChat platform). Use:
   ```bash
   curl -s "https://news.google.com/rss/search?q=gold+price+June+2026&hl=en-US&gl=US&ceid=US:en"
   ```
   This returns real RSS with `<pubDate>` tags — verifiable, dated, and filterable. The output is verbose (100K+ chars); pipe through grep or Python for extraction. Always extract `<pubDate>` from each `<item>` before building a timeline (see pitfall 25/26). The pattern works from cron with proxy set.

33. **SGE折价有两个不同含义，不可混用（2026.7.13 L1审查实踩）**：
    main.py 终端输出中"上海金折价 -6.5%"与契约定义的"境内外价差"不是同一个指标：
    - **境内外价差**（契约口径 D4.3）：AU9999实盘价 − 理论平价（GC=F÷31.1035×USDCNH）。正常值在 ±1% 以内，反映汇率传导效率。
    - **公允价值偏离**（main.py 输出）：AU9999 vs 模型公允价值¥953.2。这是估值模块信号，反映境内需求强弱，可达 ±10%。
    - **两者完全不同**：本例中境内外价差仅 -0.14%（正常），但公允价值偏离达 -6.5%（散户看空）。在 D4 校验和 D3 研判中必须区分这两个概念，不能用"上海金折价"一个词同时指代两者。L1 审查会严格检查口径一致性。
    - **加仓条件中也需口径对齐**：若契约定义加仓条件为"上海金折价收窄至-3%"，应明确指向公允价值偏离而非境内外价差。推荐使用"公允价值偏离从-6.5%收窄至-3%以内"的表述，避免歧义。
    - **本周报告：COMEX期货 vs XAU现货基差 +0.64%，境内外价差 -0.14%（汇率传导正常），AU9999公允价值偏离 -6.5%**。三者互洽：GC=F基准价差 -0.14% + 基差 0.64% ≈ XAU现货基准 +0.50%。D4 校验应同时报告三个口径：①期现基差（COMEX vs XAU）、②境内外价差（AU9999 vs GC=F平价）、③公允价值偏离（AU9999 vs 模型公允价值）。境内外价差和公允价值偏离是两个不同的概念，不能混用\"上海金折价\"一个词指代。

34. **main.py 终端输出文本不可信——以数值评分为准（2026.7.13 黄金周报实踩）**：
    main.py 最终行的文本建议与数值评分逻辑可能出现矛盾。见本次案例：数值评分 38.4/100 → 30% 定投，但终端文本输出\"建议在¥886-925/克暂停，等待回落至该区间\"——当前价 ¥891 已在该区间内，\"等待回落\"自相矛盾。这是模型文本生成的典型幻觉，评分模块和文本建议模块使用不同的生成路径。**处理**：交付报告中以数值评分（module_scores → composite_100 → 定投映射）为准，终端文本输出仅作为辅助参考。若存在矛盾，在研判章节显式标注冲突并说明以数值为准（见 `lessons.md` L9）。契约 D2 已注明\"终端输出文本仅作为原始数据\"。

35. **DXY_THRESHOLDS 需随美元中枢迁移而校准（2026.7.21 Opus审查发现）**：
    2022-2024年美元中枢在95-105区间，<100给+2.0看多分是合理的。但2026年通胀+加息环境推高美元中枢至100+，DXY=100.94处于6个月高位+月度走强时，给+1.0看多分是错误的——信号文案写\"走弱利好\"而价格快照写\"走强、6个月高位\"，自相矛盾。**修复**：将阈值调整为 `(-999,97,+2.0) / (97,100,+1.0) / (100,103,0.0) / (103,105,-1.0) / (105,999,-2.0)`，使100-103区间从+1.0降为中性0.0。**每次美元中枢发生结构性迁移（如通胀周期、加息周期），必须复盘 DXY_THRESHOLDS 是否仍适配当前环境。**

36. **D4.1 期现基差必须跨源对比，不能用同一数据源自比（2026.7.21 Opus审查发现）**：
    gold-api.com 的 `/price/XAU` 端点返回的价格与 COMEX GC=F 恰好相同时，不是\"基差为0\"——是取了同一数据源。**真正的基差验证需要 yfinance GC=F vs 独立来源的XAU现货**（如CNBC报道、Reuters报价、Univest报道中引用的现货价）。若跨源不可得，D4.1应标\"⚠️ 无法校验（单源）\"而非\"✅\"。见本次案例：GC=F $4,023 vs Univest报道现货 $4,000.55 = 真实基差 +0.56%。

37. **CNH=X 数据源不可靠时的 D4/D3 降级路径（2026.7.21 Opus审查确立）**：
    CNH=X 通过 yfinance 经常拉取失败（4次重试全空），回退到15天前的缓存。此时：①D4.2 直接标\"❌ 不可用\"，不使用过期缓存计算任何对外数值；②D4.3 同步标\"❌ 不可用（依赖D4.2）\"；③D3 删除所有人民币价格区间，只给 COMEX 美元区间，注明\"本期不提供人民币折算\"。见本次案例：数值评分 38.4/100 → 30% 定投，但终端文本输出\"建议在¥886-925/克暂停，等待回落至该区间\"——当前价 ¥891 已在该区间内，\"等待回落\"自相矛盾。这是模型文本生成的典型幻觉，评分模块和文本建议模块使用不同的生成路径。**处理**：交付报告中以数值评分（module_scores → composite_100 → 定投映射）为准，终端文本输出仅作为辅助参考。若存在矛盾，在研判章节显式标注冲突并说明以数值为准（见 `lessons.md` L9）。契约 D2 已注明\"终端输出文本仅作为原始数据\"。

## 🧩 工作流配方

**任务**：黄金周报 / 黄金分析
**加载顺序**：
1. `gold-macro-framework` — 宏观定价公式 + 传导机制 + 跨资产验证（先建立宏观背景）
2. `gold-investment-analysis` — 本 skill：七因子量化打分 + 周报生成
3. 涉及产业链/地缘事件时，叠加 `deep-analysis-workflow` 做框架审视
4. 涉及调仓建议时，触发 `decision-gate`（汇报打分结果→征得同意→给操作建议）
**交付**：微信分段 + MEDIA 文件（格式见 xiaohongshu-analysis「输出与交付」章节）
**收尾**：任务完成后检查 `post-task-review` 触发条件，满足则生成复盘