# 黄金积存金分析框架

> **Target**: 积存金 (Gold Accumulation Plan)
> **Horizon**: Medium-to-long-term (flexible, no urgent liquidity)
> **Compiled**: June 2026

---

## 1. MACRO ENVIRONMENT (35%)

### 1.1 US 10Y TIPS Yield (Real Rate)
- **Source**: FRED (DFII10)
- **Logic**: Gold's opportunity cost. Correlation ~ -0.85 historically.
- **Thresholds**:
  - Real yield < 0% → strongly bullish
  - 0-1% → neutral / mildly supportive
  - > 2% → headwind
- **Key signal**: TIPS declining faster than nominal yields → inflation expectations rising → gold breakout

### 1.2 USD Index (DXY)
- **Source**: ICE
- **Logic**: Gold priced in USD; explains ~50-60% of gold variance
- **Thresholds**: DXY < 100 → structural bullish; > 105 → headwind
- **Key signal**: Gold rising alongside DXY → geopolitical/safe-haven regime shift (most powerful signal)

### 1.3 Fed Policy & Rate Expectations
- **Fed Funds Futures**: CME FedWatch (12-month forward cuts > 100bp → accumulation window)
- **2Y-10Y Spread**: FRED (T10Y2Y). Inversion → recession signal → gold bullish
- **Fed Balance Sheet**: FRED (WALCL). Expansion → liquidity → gold bullish

### 1.4 Geopolitical & Central Bank
- **GPR Index**: > 200 → tactical gold spike probability elevated
- **Central bank quarterly purchases**: > 200 tonnes → structural floor under gold
- **Fiscal deficit > 6% GDP**: Long-term secular gold bull case

### Regime Detection
```
Regime = classify(
  if Real Yield < 0% and DXY < 100        → "Tailwind"
  if Real Yield > 1.5% and DXY > 105      → "Headwind"
  if GPR > 200                             → "Geopolitical Bid"
  if 2Y-10Y < -0.5% (inverted)            → "Pre-Recession"
  else                                      → "Mixed/Neutral"
)
```

---

## 2. TECHNICAL TREND (25%)

### Gold-Specific Moving Averages
- **50-week SMA**: Primary trend filter. Above = bull phase, accumulate on pullbacks.
- **200-day SMA**: Most watched gold MA. Above = bull, below = bear.
- **200-week SMA**: Long-term valuation anchor. Within 10% above → long-term undervalued → aggressive accumulation.
- **Fibonacci MAs**: 55-day EMA, 144-day EMA (gold desk standard)

### Other Indicators
- **Weekly MACD(12,26,9)**: Bullish signal → multi-month trend change
- **Weekly RSI(14)**: RSI < 30 on weekly → rare, high-conviction buy
- **Bollinger Bands(50,2.5) weekly**: Weekly close below lower band → oversold accumulation
- **GVZ (Gold VIX)**: > 25 → elevated fear, near bottoms; < 12 → complacency
- **Volume/OI**: Rising OI in uptrend → healthy; OI + price divergence → weak

### Fibonacci Levels (Gold-Specific)
- 2015 low ($1,046) → 2020 high ($2,075): 61.8% retracement at ~$1,440 (held as multi-year support)
- 161.8% extension from 2018-2020 move → $2,500 area

---

## 3. SENTIMENT & POSITIONING (20%)

### COT Report (Most Powerful Sentiment Tool)
- **Source**: CFTC weekly (Friday release for prior Tuesday)
- **Managed Money Net Long**:
  - > 200K contracts → crowded, correction risk → pause 积存金
  - Bottom quartile of 3-year range → contrarian buy
  - Commercial shorts decreasing sharply → bullish (smart money)

### ETF Flows
- **GLD tonnage**: Persistent outflows > 30 days → bearish; persistent inflows → bullish
- **Divergence**: Gold price up + GLD flat/declining → futures-driven (speculative, less durable)

### Other
- **Gold/Silver Ratio**: > 85 → risk-off; > 90 → extreme, often precedes turn
- **COMEX Registered Inventory**: Declining → delivery stress → upside pressure
- **Gold Lease Rates (GOFO)**: Negative → physical scarcity → bullish

---

## 4. VALUATION (20%)

### Core Model: Real Rate Fair Value
```
ln(Gold) = α + β₁(10Y TIPS) + β₂(ln DXY) + β₃(Inflation Expectations)
```
When actual gold > 1.5σ below fair value → undervalued/accumulate

### Composite Valuation Z-Score
```
Gold_Valuation_Z = mean(
    Z(Real Yield residual),
    Z(Gold/M2 deviation from trend),
    Z(Gold/SPX deviation from trend),
    Z(Gold/Oil deviation from trend)
)
```

### Thresholds
| Z-Score | Signal |
|---------|--------|
| < -1.5 | Significantly undervalued → aggressive accumulation |
| -1.5 to -0.5 | Moderately undervalued → steady accumulation |
| -0.5 to +0.5 | Fair value → maintain |
| +0.5 to +1.5 | Moderately overvalued → reduce/pause |
| > +1.5 | Significantly overvalued → consider partial redemption |

### Key Ratios
- **Gold/M2 Money Supply**: < trend → undervalued
- **Gold/SPX**: < 0.5x → equities extremely overvalued vs gold
- **Gold/Oil**: > 30 bbl/oz → gold rich; < 10 → gold cheap
- **CPI-adjusted 1980 high**: ~$3,300-3,500 in 2024 dollars

---

## 5. SIGNAL SYNTHESIS

### Weighted Scoring
| Dimension | Weight |
|-----------|--------|
| Macro | 35% |
| Technical | 25% |
| Sentiment | 20% |
| Valuation | 20% |

### Action Thresholds
| Score | Action |
|-------|--------|
| > +1.0 | Active accumulation (1.5x) |
| +0.3 to +1.0 | Normal accumulation (1.0x) |
| -0.3 to +0.3 | Maintain, minimal (0.5x) |
| -1.0 to -0.3 | Pause accumulation |
| < -1.0 | Consider partial redemption (20-30%) |

### Regime-Switching
| Regime | Strategy |
|--------|----------|
| Monetary Easing | Weight macro 40%, accumulate aggressively |
| Stagflation | Gold is best-in-class, accumulate |
| Risk-On | Gold underperforms, reduce accumulation |
| Deflationary Bust | Wait for liquidity shock to pass, then buy |
| Geopolitical Shock | Hold existing; new entries wait for GPR normalization |

---

## 6. EXECUTION CALENDAR

| Frequency | Actions | Time |
|-----------|---------|------|
| **Weekly** | Price vs 50-week SMA, COT check, GLD tonnage trend | 5 min |
| **Monthly** | Full macro dashboard, run scoring model, decide contribution size | 30 min |
| **Quarterly** | Deep valuation review, COT trend, monthly MACD, CB buying data | 1 hr |
| **Annual** | Portfolio rebalance, structural outlook, redemption decision | 2 hr |

---

## TOP 5 INDICATORS

1. **US 10Y TIPS Yield** — #1 macro driver. Trending down = accumulate.
2. **Gold / 50-week SMA** — Trend filter. Above = bull, below = caution.
3. **COT Managed Money Net Long** — Best contrarian signal at extremes.
4. **Composite Valuation Z-Score** — Accumulate when Z < -0.5.
5. **Fed Funds 12-Month Forward Pricing** — Cuts priced in = accumulation window.
