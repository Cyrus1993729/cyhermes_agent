# akshare Chinese Column Name Patterns

akshare is a Chinese financial data library with Chinese column names that vary between functions and versions.

## Shanghai Gold (spot_golden_benchmark_sge)

```python
import akshare as ak

df = ak.spot_golden_benchmark_sge()
# Columns: ['交易时间', '晚盘价', '早盘价']
# Values: CNY/gram

# Standardize:
col_map = {'交易时间': 'Date', '晚盘价': 'Evening', '早盘价': 'Close'}
df = df.rename(columns=col_map)
df['Date'] = pd.to_datetime(df['Date'])
df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
df = df.set_index('Date')[['Close']].dropna()
```

## China Gold ETFs (fund_etf_hist_em)

```python
df = ak.fund_etf_hist_em(symbol='518880', period='daily', 
                          start_date='20260501', end_date='20260603', adjust='')
# Columns: ['日期', '开盘', '收盘', '最高', '最低', '成交量', '成交额', '振幅', '涨跌幅', '涨跌额', '换手率']

# Note: NO "份额" (shares) column available
# Use 成交量 (volume) as proxy for retail interest

date_col = next((c for c in df.columns if '日期' in str(c)), None)
vol_col = next((c for c in df.columns if '成交量' in str(c)), None)
```

## Key akshare Functions for Gold Analysis

| Function | Returns | Notes |
|----------|---------|-------|
| `spot_golden_benchmark_sge()` | AU9999 daily | Chinese columns |
| `fund_etf_hist_em(symbol='518880')` | 华安黄金ETF | Volume only, no shares |
| `fund_etf_hist_em(symbol='159937')` | 博时黄金ETF | Volume only, no shares |
| `macro_china_fx_gold()` | PBOC gold reserves | Monthly, columns vary |

## Pitfalls

- Column names are in Chinese and **change between akshare versions**
- Always use fuzzy column matching (`if '日期' in str(c)`) not exact strings
- ETF data has NO shares/holdings column — use volume as proxy
- `fund_etf_fund_daily_em()` returns fund NAV, not ETF market data
- `fund_etf_fund_info_em()` also returns NAV, not holdings
- akshare functions hit eastmoney.com — needs DIRECT connection (no proxy)
