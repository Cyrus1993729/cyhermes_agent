# yfinance Rate-Limit Workaround

## Problem

`yf.download()` gets rate-limited from China IPs with:
```
YFRateLimitError('Too Many Requests. Rate limited. Try after a while.')
```

## Fix: Ticker API + Shared Session

```python
import yfinance as yf
import requests
import time

# Shared session with browser-like User-Agent
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})

# Pre-warm connection
try:
    session.get('https://finance.yahoo.com', timeout=5)
except Exception:
    pass

# Download with Ticker API (NOT yf.download)
def fetch_with_retry(ticker, period="2y", max_retries=4):
    for attempt in range(max_retries):
        if attempt > 0:
            delay = 5.0 * (2 ** (attempt - 1))
            time.sleep(delay)
        try:
            tk = yf.Ticker(ticker, session=session)
            df = tk.history(period=period, auto_adjust=True)
            if df is not None and not df.empty:
                time.sleep(2.0)  # inter-call cooldown
                return df
        except Exception:
            continue
    return None
```

## Key Points

- `yf.Ticker(ticker, session=session).history()` — NOT `yf.download()`
- Shared `requests.Session` with real User-Agent header
- `auto_adjust=True` for split-adjusted prices
- `auto_adjust=True` on futures (GC=F, CL=F) adjusts for contract rolls — this may distort technical indicators. For pure price analysis, consider `auto_adjust=False`.
- Inter-call delay of 2 seconds between tickers
- Exponential backoff on failure: 5s → 10s → 20s → 40s
