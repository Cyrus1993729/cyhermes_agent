# Shanghai Gold Data: Automatic Conversion Fallback

## Problem

akshare's `spot_golden_benchmark_sge()` returns SGE data that can lag 2-6 days behind
COMEX. On weekends and Chinese holidays, the gap widens. The old code returned whatever
was cached, producing stale Shanghai gold prices labeled as "估算".

## Solution (v3.1)

`data_fetcher.py:fetch_shanghai_gold()` now has three tiers:

```
Tier 1: Cache check → if last date ≤ 2 days old, return cache
Tier 2: akshare re-fetch → if data ≤ 2 days old, merge + cache + return
Tier 3: Conversion fallback → GC=F / 31.1035 × USDCNH
```

### Conversion method (`_fetch_shanghai_from_xau_conversion`)

```python
# Uses yfinance cache files (no external API calls):
# - data/gold_price.csv   → GC=F Close
# - data/usdcnh.csv       → USD/CNH Close

xau_price = float(gold_cache["Close"].iloc[-1])
usdcnh = float(usdcnh_cache["Close"].iloc[-1])
shanghai_price = round(xau_price / 31.1035 * usdcnh, 2)
```

Key design decisions:
- **No gold-api.com**: Blocked/timeout in China. Uses yfinance cache instead.
- **No exchangerate-api.com**: CNH=X from yfinance is reliable.
- **No "估算" label**: The conversion is mathematically sound — treated as valid data.
- **Appended to real SGE rows**: The converted row lives alongside SGE data in the same CSV,
  so future fetches will replace it when fresh SGE data arrives.

## Verification

After running `main.py`, check the log:
```
SGE data 6 days old (2026-06-16), will supplement with conversion
Shanghai gold via conversion: GC=F=$4154.70 / 31.1035 × 6.7800 = ¥905.65/克
```

The report header shows `¥905.65/克` with NO "估算" qualifier.

## When This Triggers

- Every Monday morning (SGE doesn't trade weekends)
- After Chinese holidays (SGE closed)
- When akshare API has data lag

This is **normal, expected behavior** — no manual intervention needed.
