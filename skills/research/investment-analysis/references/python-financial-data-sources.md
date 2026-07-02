# Python Financial Data Sources — Pitfalls & Workarounds

> Condensed notes from building the gold_analyzer scoring system.
> Python 3.11+, Windows host, accessed from China.

---

## yfinance — Rate Limiting

### Problem
`yf.download()` frequently returns `YFRateLimitError: Too Many Requests` from China-based IPs. The error is caught internally by yfinance and returns an **empty DataFrame**, not a Python exception. Standard retry-on-exception patterns don't catch it.

### Fix: Ticker API + requests.Session

```python
import requests
import yfinance as yf
import time

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})

# Pre-warm connection
try:
    session.get('https://finance.yahoo.com', timeout=5)
except Exception:
    pass

def download(ticker: str, period: str = "2y"):
    for attempt in range(4):
        try:
            tk = yf.Ticker(ticker, session=session)
            df = tk.history(period=period, interval="1d", auto_adjust=True)
            if df is None or df.empty:
                if attempt < 3:
                    time.sleep(5 * (2 ** attempt))
                    continue
                return None
            time.sleep(2.0)  # inter-call cooldown
            return df
        except Exception as e:
            if attempt < 3 and any(k in str(e).lower() for k in
                ['rate limit', 'too many requests', 'timeout', '429']):
                time.sleep(5 * (2 ** attempt))
                continue
            return None
    return None
```

**Key**: `yf.Ticker(symbol, session=session).history()` works; `yf.download()` doesn't. The shared session handles Yahoo's cookie/auth flow properly.

### Ticker symbols
| Asset | Symbol |
|-------|--------|
| Gold futures | `GC=F` |
| DXY | `DX-Y.NYB` |
| S&P 500 | `^GSPC` |
| WTI Crude | `CL=F` |
| GLD ETF | `GLD` |
| Gold volatility | `^GVZ` |
| Silver | `SI=F` |

---

## akshare — Chinese Column Names

### Problem
akshare returns DataFrames with **Chinese column names**. Blindly taking `df.columns[0]` as the price column will grab the date column.

### Example: Shanghai Gold Benchmark
```python
import akshare as ak
df = ak.spot_golden_benchmark_sge()
# Columns: ['交易时间', '晚盘价', '早盘价']
#          date        evening   morning price (CNY/gram)
```

### Fix: Explicit mapping
```python
col_map = {
    '交易时间': 'Date',
    '晚盘价': 'Evening',
    '早盘价': 'Close',
}
existing = {k: v for k, v in col_map.items() if k in df.columns}
df = df.rename(columns=existing)
df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
```

Always verify column names with `print(list(df.columns))` before assuming.

---

## FRED (Federal Reserve Economic Data)

### Setup
```bash
pip install fredapi
```

### API Key
1. Register at https://fred.stlouisfed.org/docs/api/api_key.html (free)
2. Set in config: `FRED_API_KEY = "your_key_here"`
3. Or env var: `export FRED_API_KEY="your_key"`

### Key Series for Macro Analysis
| Series ID | Description |
|-----------|------------|
| `DFII10` | 10-Year TIPS real yield |
| `DFII5` | 5-Year TIPS real yield |
| `T10Y2Y` | 10Y-2Y Treasury spread |
| `M2SL` | M2 Money Supply |
| `DTWEXBGS` | Trade-weighted USD (broad) |

### Usage
```python
from fredapi import Fred
fred = Fred(api_key="your_key")
tips = fred.get_series("DFII10")  # returns pandas Series with date index
```

**Pitfall**: FRED is slow from China (5-10s per series). Cache aggressively.

---

## COT (Commitment of Traders) from CFTC

### Source
Weekly legacy futures-only report: https://www.cftc.gov/dea/futures/deacmxsf.htm

### Parsing Logic
```python
import requests
resp = requests.get("https://www.cftc.gov/dea/futures/deacmxsf.htm")
text = resp.text

# Split by market sections
sections = text.split("--------------------------------------------------------------------------------")
gold_section = None
for s in sections:
    if "GOLD - COMMODITY EXCHANGE" in s and "Code-088691" in s:
        gold_section = s
        break

# Parse COMMITMENTS line
lines = gold_section.split('\n')
for i, line in enumerate(lines):
    if 'COMMITMENTS' in line.upper() and i + 1 < len(lines):
        commit_line = lines[i + 1].strip()
        nums = [float(t.replace(',', '')) for t in commit_line.split()
                if t.replace(',', '').replace('.', '').isdigit()]
        break

# nums[0] = NonCommercial Long (Managed Money Long in disaggregated)
# nums[1] = NonCommercial Short
# nums[3] = Commercial Long
# nums[4] = Commercial Short
```

---

## Cache Strategy

All data sources benefit from 1-day CSV caching:

```python
import os
import pandas as pd
from datetime import datetime, timedelta

def load_cache(path):
    if not os.path.exists(path):
        return None
    mtime = datetime.fromtimestamp(os.path.getmtime(path))
    if (datetime.now() - mtime) > timedelta(days=1):
        return None
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index, utc=True)
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    return df

def save_cache(df, path):
    df.to_csv(path)
```

**Timezone trap**: yfinance may return timezone-aware indices. When loading from CSV, the timezone info is lost, causing `pd.to_datetime` to fail with "Mixed timezones detected." Fix: `utc=True` then `tz_localize(None)`.

---

## General Rules

1. **Always wrap external calls in try/except** — networks fail. Return None, log warning, let downstream handle missing data.
2. **Score 0 when data is missing** — never guess or extrapolate. Zero = neutral, doesn't distort the composite.
3. **Use `Optional[DataFrame]` everywhere** — None is the canonical "no data available" sentinel.
4. **Inter-call delay ≥ 2s for yfinance** — sequential fetches need cooldown to avoid rate limits.
5. **Prefer hardcoded API keys in config.py** for single-user systems — simpler than env var management across shell restarts.
