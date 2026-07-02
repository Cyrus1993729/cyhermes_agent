# Gold Analysis Data Source Details

## yfinance: The Session Pattern (MUST USE)

### The Problem
`yf.download()` triggers aggressive rate limiting from Yahoo Finance, especially from China-based IPs. It returns empty DataFrames with `YFRateLimitError` in logs, but does NOT raise Python exceptions — the error is caught internally by yfinance.

### The Fix
Use `yf.Ticker(ticker, session=requests.Session()).history()`:

```python
import requests
import yfinance as yf
import time

class DataFetcher:
    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        # Pre-warm connection
        try:
            self._session.get('https://finance.yahoo.com', timeout=5)
        except Exception:
            pass

    def _yf_download(self, ticker, period="2y"):
        max_retries = 4
        base_delay = 5.0

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    time.sleep(base_delay * (2 ** (attempt - 1)))

                tk = yf.Ticker(ticker, session=self._session)
                # auto_adjust=False: futures (GC=F, SI=F, CL=F) distort with
                # contract-roll adjustment. Never auto-adjust futures.
                df = tk.history(period=period, auto_adjust=False)

                if df is None or df.empty:
                    if attempt < max_retries - 1:
                        continue  # Probably rate limit, retry
                    return None

                time.sleep(2.0)  # Inter-call cooldown
                return df
            except Exception:
                if attempt < max_retries - 1:
                    continue
                return None
        return None
```

### Column Handling After `auto_adjust=False`

When `auto_adjust=False`, yfinance returns extra columns: `Adj Close`, `Dividends`, `Stock Splits`. The rename loop must **drop Adj Close first** to avoid a duplicate-"Close" collision:

```python
# After flattening MultiIndex columns:
drop_cols = []
rename_map = {}
for col in df.columns:
    col_lower = str(col).lower()
    if "adj close" in col_lower or "adj" in col_lower:
        drop_cols.append(col)  # drop — see below
    elif "close" in col_lower:
        rename_map[col] = "Close"
    elif "volume" in col_lower:
        rename_map[col] = "Volume"
    # ... etc for Open, High, Low
if drop_cols:
    df = df.drop(columns=drop_cols)
if rename_map:
    df = df.rename(columns=rename_map)
```

If `Adj Close` is NOT dropped, both `Close` and `Adj Close` map to `"Close"`, creating a duplicate-column DataFrame. Then `df['Close']` returns a DataFrame (not Series), breaking any `float(series.iloc[...])` call with `TypeError: float() argument must be a string or a real number, not 'Series'`.

| Ticker | Description | Period |
|--------|-------------|--------|
| GC=F | COMEX Gold Futures | 2y daily |
| DX-Y.NYB | US Dollar Index | 2y daily |
| ^GSPC | S&P 500 | 2y daily |
| CL=F | WTI Crude Oil | 2y daily |
| GLD | SPDR Gold ETF | 2y daily |
| ^GVZ | Gold Volatility Index | 2y daily |
| SI=F | Silver Futures | 2y daily |

---

## akshare: Gold Data Functions

### Shanghai Gold Benchmark Price
`ak.spot_golden_benchmark_sge()` returns:

```
Columns: ['交易时间', '晚盘价', '早盘价']
         交易时间     晚盘价     早盘价
0  2016-04-18  257.29  256.92
1  2016-04-19  259.97  261.15
```

Prices are in CNY/gram. Map to English:
```python
col_map = {'交易时间': 'Date', '晚盘价': 'Evening', '早盘价': 'Close'}
```

### PBOC Gold Reserves
Try `ak.macro_china_fx_gold()` for China's central bank gold reserve data. Function name and column format vary by akshare version — always inspect output first.

### Fallback
`ak.gold_spot_quote()` returns a single-row DataFrame with current spot price.

### Shanghai Gold Data Staleness & Synthetic Fallback

**Problem**: SGE data via akshare typically lags 1-2 trading days. Over weekends (Friday COMEX close → Monday SGE), the gap can be 3-4 days. If COMEX moved significantly during the gap (e.g., -4.7% from non-farm payrolls), the stale SGE price distorts the Shanghai premium calculation.

**Detection**: Compare the latest date in `shanghai_gold.csv` to the latest COMEX date:
```python
import pandas as pd
sg = pd.read_csv('data/shanghai_gold.csv', index_col=0, parse_dates=True)
gold = pd.read_csv('data/gold_price.csv', index_col=0, parse_dates=True)
sge_latest = sg.index[-1]
comex_latest = gold.index[-1]
stale = (comex_latest - sge_latest).days >= 2  # flag if 2+ days behind
```

**Fallback procedure** when stale:
```python
# 1. Delete stale cache and re-fetch (may still be same date if SGE hasn't published)
import os; os.remove('data/shanghai_gold.csv')

# 2. Convert COMEX to CNY
import yfinance as yf
session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0'})
com ex = float(yf.Ticker('GC=F', session=session).history('2d', auto_adjust=False)['Close'].iloc[-1])
usdcnh = float(yf.Ticker('CNH=X', session=session).history('2d', auto_adjust=False)['Close'].iloc[-1])
synthetic = round(comex / 31.1035 * usdcnh, 2)

# 3. Append synthetic row to cache (so main.py can pick it up)
today = pd.Timestamp.now().normalize()
sg = pd.concat([sg, pd.DataFrame({'Close': [synthetic]}, index=[today])])
sg.to_csv('data/shanghai_gold.csv')
```

**CRITICAL**: Do NOT add Shanghai premium to the synthetic estimate. The formula is `COMEX / 31.1035 × USDCNH` — pure conversion, no markup. The premium signal is computed by the model from actual market data. Adding an artificial premium creates a phantom signal.

After updating the cache, re-run `python main.py` so the model recalculates the premium and price guidance with the corrected Shanghai base price.

---

## FRED API: Setup & Key Series

### Registration
1. Go to https://fred.stlouisfed.org/docs/api/api_key.html
2. Register for free (email required)
3. Get API key instantly

### Key Series for Gold Analysis

| Series ID | Description | Update Frequency | Relevance |
|-----------|-------------|------------------|-----------|
| DFII10 | 10-Year TIPS Real Yield | Daily | #1 gold driver |
| DFII5 | 5-Year TIPS Real Yield | Daily | Near-term policy sensitivity |
| T10Y2Y | 10Y-2Y Treasury Spread | Daily | Recession signal |
| M2SL | M2 Money Supply (Seasonally Adjusted) | Monthly | Gold valuation vs money supply |
| DTWEXBGS | Trade-Weighted USD Index (Broad) | Daily | Alternative to DXY |

### Usage with fredapi
```python
from fredapi import Fred
fred = Fred(api_key="your_key_here")
tips = fred.get_series("DFII10")  # Returns pandas Series with Date index
m2 = fred.get_series("M2SL")
spread = fred.get_series("T10Y2Y")
```

### FRED from China
- Expect 5-15 seconds per request
- Set generous timeouts (30s+)
- Cache results aggressively (data updates daily/weekly, not real-time)

---

## CFTC COT Report: Parsing

### Source
URL: `https://www.cftc.gov/dea/futures/deacmxsf.htm`
This is the legacy futures-only report (not the disaggregated version).

### Parsing Steps
1. Download raw HTML via `requests.get(url, timeout=15)`
2. Split by `<PRE>` tags to get the text report
3. Find section containing "GOLD - COMMODITY EXCHANGE" and "Code-088691"
4. After the "COMMITMENTS" header line, parse the next line's numbers
5. Number order: NonComm_Long, NonComm_Short, Spreads, Comm_Long, Comm_Short, Total_Long, Total_Short, NonRep_Long, NonRep_Short

### Interpretation (Legacy Report)
- "Non-Commercial" ≈ "Managed Money" (speculators) in disaggregated report
- "Commercial" = producers/merchants hedging
- Extreme Managed Money net long (>200K contracts) = crowded trade, correction risk
- Commercial short covering = bullish signal (smart money)

---

## Cache Strategy

All fetched data should be cached as CSV with 1-day TTL:

```python
# Save
df.to_csv(cache_path)

# Load (with index fix)
df = pd.read_csv(path, index_col=0, parse_dates=True)
if not isinstance(df.index, pd.DatetimeIndex):
    df.index = pd.to_datetime(df.index, utc=True)
if df.index.tz is not None:
    df.index = df.index.tz_localize(None)
```

Cache invalidation: check file mtime — if older than 1 day, re-fetch.
