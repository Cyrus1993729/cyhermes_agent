# Gold Investment Scoring System — Architecture Reference

Concrete implementation example of the quantitative-scoring-system principles, applied to a gold accumulation plan (积存金) scoring model.

## System Overview

- **7 dimensions**: Macro (20%), Technical (15%), Sentiment (10%), Valuation (15%), Central Bank (20%), China Domestic (10%), Geopolitical (10%)
- **Output**: 0-100 composite score, weekly report with data freshness labels
- **Language**: Chinese (user preference)
- **Data sources**: yfinance (7 tickers), FRED (3 series), CFTC COT, akshare (Shanghai gold), Sina API (ETF shares)

## Dimension Details

### Macro (20%) — L2
- real_yield (40%): TIPS 10Y level + trend (fixed 63-day window)
- dxy (30%): DXY level + gold-DXY decoupling check
- fed_policy (20%): 2Y-10Y spread + short-rate trend proxy
- fiscal_gpr (10%): DXY 3-month trend as fiscal confidence proxy

### Technical (15%) — L1/L2 mix
- ma_position (40%): 50-week + 200-day SMA positioning
- macd (25%): Weekly MACD direction + histogram turning
- rsi (20%): Weekly RSI(14) + bearish divergence detection
- trend_strength (15%): ADX + 200-week SMA long-term trend

### Sentiment (10%) — L1/L2 mix
- cot (50%): CFTC Managed Money net long, percentile or heuristic
- etf_flow (30%): GLD 20-day change + gold price divergence check
- gsr (20%): Gold/Silver ratio level

### Valuation (15%) — L2
- fair_value_residual (40%): ln(Gold) ~ TIPS + ln(DXY) residual Z-score
- gold_m2 (20%): Gold/M2 ratio Z-score
- gold_spx (20%): Gold/SPX ratio Z-score
- gold_oil (20%): Gold/Oil ratio with thresholds

### Central Bank (20%) — L2/L3 mix
- pboc_reserves (40%): akshare PBOC gold reserves, buying vs selling
- decoupling_proxy (30%): Gold-DXY simultaneous rise as CB buying proxy
- resilience (30%): Gold performance during equity weakness

### China Domestic (10%) — L1/L2 mix
- shanghai_premium (40%): AU9999 vs London CNY-equivalent premium (5-day avg)
- fx_impact (30%): USDCNH 20-day + 60-day trend alignment
- etf_flow (30%): Combined 518880 + 159937 volume change

### Geopolitical (10%) — L1/L2 mix
- oil_gold_resonance (40%): DXY-orthogonalized oil+gold co-move + equity filter
- pm_divergence (35%): Gold minus silver 20-day return spread Z-score
- gvz_premium (25%): GVZ excess over SPX-realized-vol expected, direction-filtered

## Confidence Scoring

Four dimensions, each 0-25:
- **A: Signal consensus** — bull/bear ratio deviation from 50%
- **B: Layer alignment** — L1/L2/L3 direction agreement count
- **C: Signal strength** — average absolute score (proxy for decisiveness, not historical accuracy)
- **D: Data quality** — 1 - (components_with_status / total_components)

Levels: >=80 high, >=60 medium, >=40 low, <40 questionable.

Confidence constrains action recommendations:
- Score >1.0 + high confidence: aggressive buy
- Score >1.0 + low confidence: normal DCA (downgrade)
- Score <-0.3 + high confidence: pause
- Score <-0.3 + low confidence: hold (don't pause on weak signal)

## Data Freshness Decay

For the weekly report, monthly-frequency dimensions (M2, PBOC reserves, TIPS trend) decay:
- Week 1: 100% weight
- Week 2: 80%
- Weeks 3-4: 60%
- 30+ days: 40%

Reset to 100% when new data arrives that week.

## Signal Layer Classification

```
L3 (structural): fiscal_gpr, pboc_reserves, resilience
L2 (medium-term): real_yield, dxy, fed_policy, ma_position, trend_strength,
                  gsr, fair_value_residual, gold_m2, gold_spx, gold_oil,
                  decoupling_proxy, fx_impact, pm_divergence
L1 (short-term): macd, rsi, cot, etf_flow, shanghai_premium,
                 etf_flow(china), oil_gold_resonance, gvz_premium
```

## Tools & Environment

- Claude Code CLI via OAuth, accessed through Clash proxy (7897 port):
  ```
  export HTTP_PROXY=http://127.0.0.1:7897
  export HTTPS_PROXY=http://127.0.0.1:7897
  claude --dangerously-skip-permissions -p "..."
  ```
- FRED API key via FRED_API_KEY environment variable (never hardcoded)
- Project at C:\Users\Administrator\gold_analyzer\
- All analysis and reports in Chinese

## Key Design Decisions

1. Removed redeem/sell advice: gold accumulation plans (积存金) don't support active selling
2. PBOC reserves promoted to independent dimension: structural driver post-2022
3. Geopolitical module uses market-price proxies (no news API)
4. Currency: XAU x CNH / 31.1035, with historical premium alignment
5. Signal dampening: EMA-style weighting (70/30) on direction changes
