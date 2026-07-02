# Data Validation — Pre-Report Quality Gates

Run between `python main.py` and report generation. Each gate must pass before the report is delivered.

## Gate 1: COMEX Gold Price

```bash
curl -s https://api.gold-api.com/price/XAU | python -c "import sys,json; d=json.load(sys.stdin); print(f\"XAU Spot: \${d['price']:.2f}\")"
```

Compare with `main.py` output. Deviation > 2% (~$85 at current levels) means `auto_adjust` is still True or cache is stale. Delete `data/gold_price.csv` and re-run.

## Gate 2: USD/CNY Exchange Rate

```bash
curl -s https://api.exchangerate-api.com/v4/latest/USD | python -c "import sys,json; d=json.load(sys.stdin); print(f\"USD/CNY: {d['rates']['CNY']:.4f}\")"
```

Manual cross-check: `COMEX_USD / 31.1035 × USDCNY` should match Shanghai gold price within 3%.
If deviation > 3%, check:
- Shanghai gold data stale? (Gate 3)
- Wrong premium baked into synthetic estimate?

### Gate 2b: Premium discrepancy after synthetic row fix (two root causes)

After fixing stale SGE data with a synthetic row, the model's re-run premium may still not be ~0% even though the synthetic row itself was created with the exact conversion formula. There are **two distinct root causes** — always check both:

**Root Cause 1 — CNH rate mismatch**: `main.py` uses yfinance's internal CNH rate (which may be stale or failed to fetch) while Gate 2 validation uses external APIs. The synthetic row was computed with the external rate, but the model re-reads and re-computes expected Shanghai using its own internal (possibly different) CNH.

**Root Cause 2 — 5-day average contamination**: `china_domestic.py:score_shanghai_premium()` uses a 5-day rolling average premium. When a synthetic row replaces only the latest stale SGE data point, the remaining 4 data points in the window are still real (possibly stale) SGE data that may carry large premiums/discounts from earlier in the week — especially if the week saw a sharp COMEX sell-off while SGE was slow to update. These residual data points distort the average even when the synthetic row itself is at ~0% premium.

**Diagnosis**: Before assuming CNH mismatch, check `data/shanghai_gold.csv` last 5 rows. If premiums on the pre-synthetic rows (computed manually as `(SH_price - COMEX×CNH/31.1035) / (COMEX×CNH/31.1035) × 100`) differ substantially from 0%, the discrepancy is from 5-day averaging, not CNH. In this case:
- Gate 2 passes (CNY conversion is correct at the latest point) — **no fix needed**
- Note the stale-data contamination in the report's data validation footnote
- The residual distortion will self-correct as new data fills the 5-day window

**Symptom**: Synthetic row written as `COMEX/31.1035 × CNH_external`, but re-run still shows -5% premium.  
**Fixes for Root Cause 1 (CNH mismatch only)**:
1. Check if `data/usdcnh.csv` exists and its last date
2. If CNH cache is stale (>2 days), delete `data/usdcnh.csv` and re-run
3. If CNH=X fetch persistently fails, manually write the latest CNH rate to `data/usdcnh.csv`:
   ```bash
   # IMPORTANT: Must use yfinance's multi-column CSV format (not just Date,Close).
   # The data_fetcher reads Open/High/Low/Close/Volume columns — a 2-column format
   # will cause silent parse failures or NaN prices.
   echo "Date,Open,High,Low,Close,Volume,Dividends,Stock Splits" > data/usdcnh.csv
   echo "$(date -u +%Y-%m-%dT%H:%M:%S)Z,${RATE},${RATE},${RATE},${RATE},0,0.0,0.0" >> data/usdcnh.csv
   ```
   Replace `${RATE}` with the current CNH rate (e.g. from `curl -s https://api.exchangerate-api.com/v4/latest/USD | python -c 'import sys,json;print(json.load(sys.stdin)["rates"]["CNH"])'`).
   Also fix any pre-existing stale rows with the wrong format: check with `tail -3 data/usdcnh.csv` — if you see plain `Date,Close` rows or rows with fewer than 8 columns, remove them with `head -n -1` or rewrite the file.

## Gate 3: Shanghai Gold Freshness

If `age_days > 2`: SGE data is stale. Compute synthetic row using `COMEX / 31.1035 × USDCNH` — **NO added premium**. Re-run `python main.py` after.

## Gate 4: Spot Check Composite Score

Score shift of 1-2 points is normal. Shift of 5+ points needs investigation.

## Gate 5: Signal Explanation Audit (MANDATORY)

After `main.py` runs, inspect these known failure modes:

### 5a: DXY trend direction
If DXY says "走弱利好" but dxy_1m_pct > 0 → explanation should show "虽处低位但趋势走强".

### 5b: COT "净空" false claim
If net_long > 0 and score == 0, must say "持仓适中" NOT "持仓偏轻或净空".

### 5c: real_yield with missing FRED data
If FRED unavailable, must say "数据不可用" NOT "偏高利空".

### 5d: pboc_reserves vs news consistency
If news says "增持" but PbOC MoM < 0, the news is wrong. Verify: `ak.macro_china_fx_gold()` -> check 环比/同比 columns.

### 5e: News vs quantitative contradiction test
| News Claim | Check Signal | If Contradicts |
|-----------|-------------|----------------|
| "央行增持" | pboc_reserves | Score < 0 → news wrong |
| "美元走弱" | dxy_1m_pct | > 0 → news wrong |
| "避险上升" | 贵金属分化+GVZ | Both neutral → news exaggerating |

If contradiction found, **rewrite the news** to match data. Never deliver contradictory news + signals.

### 5f: Price guidance verb must match composite score

The `action_price_guidance` line (💰 建议在 ¥X-Y/克 ...) must use the **overall composite score**, NOT the china_domestic module's internal score. In `scorer.py:run_analysis()`, the original code called `self.china.score(data)` which internally called `compute_price_guidance(composite=china_score)`. Since china_score (+0.86) is almost always bullish, the guidance always said "正常定投" even when the overall composite indicated "维持观望" or "等待回调".

**Fix** (scorer.py, after computing overall `composite`):
```python
corrected_guidance = self.china.compute_price_guidance(
    au9999_df, gold_df, usdcnh_df, composite  # ← overall composite, not china_score
)
action_price_guidance = corrected_guidance.get("action_price_guidance", fallback)
```

**Verb thresholds** (in `china_domestic.py:compute_price_guidance`):
| composite | Verb | Range |
|-----------|------|-------|
| > 1.0 (75+) | 积极加仓 | fair_value ±2% |
| >= 0.3 (57.5+) | 正常定投 | current_price ±2% |
| [-0.3, 0.3) (42.5-57.5) | 等待回调后买入 | fair_value ×0.98 ~ fair_value |
| < -0.3 (<42.5) | 暂停 | fair_value ×0.93~0.97 |

**Verify**: the verb must be consistent with the action label. "维持观望, 定投50%" should NEVER pair with "正常定投" — that's the telltale sign this bug is active.
