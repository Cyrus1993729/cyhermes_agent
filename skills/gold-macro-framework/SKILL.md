---
name: gold-macro-framework
description: Gold macro analysis framework — pricing formula, transmission channels, cross-asset verification, and case study from June 2026 Iran deal/FOMC volatility.
version: 1.0.0
category: mlops
tags: [gold, macro, framework, rates, dollar, inflation]
---

# Gold Macro Analysis Framework v1.0

## When to Use

Any analysis of gold price movements — daily swings, weekly reports, major event reactions. Load before analyzing gold-related questions.

## Core Pricing Formula

```
Gold ≈ f( −Real Rates, −USD, +Inflation Expectations, +Central Bank Structural Buying, +Tail Risk Premium )
```

"Weak haven" is only a tiny slice of the last term. Never frame gold as primarily a "safe haven" asset — it is a **zero-coupon long-duration real rate asset**.

## Analysis Protocol

For any gold price movement, do NOT label it "bullish/bearish" based on the event headline. Instead:

1. **Identify which term(s) in the pricing formula this event touches**
2. **Trace the full transmission chain** (not just the first-order effect)
3. **Distinguish the event itself from the market's pricing of the event** — mispricing is where the real P&L lives
4. **Cross-verify with other assets**: stocks, bonds, silver, Bitcoin together paint the true driver

## Key Transmission Channels

### Channel 1: Rates (Dominant)
- Real yield (TIPS) ↑ → Gold ↓ (higher opportunity cost)
- Nominal yield ↑ driven by growth → Gold ↓, Stocks ↑ ("good" rate hike)
- Nominal yield ↑ driven by stagflation → Gold ↓, Stocks ↓ ("bad" rate hike)
- Critical distinction: **why** are rates rising?

### Channel 2: USD
- DXY ↑ → Gold ↓ (inverse relationship)
- For CNY investors: USD↑ hurts USD gold price but CNY depreciation partially offsets → RMB gold less volatile

### Channel 3: Inflation Expectations
- Inflation ↑ → Gold ↑ (inflation hedge demand)
- BUT: if Fed responds hawkishly to inflation → real rates rise → net effect can be negative
- Oil price changes affect gold through inflation expectations AND through rate expectations

### Channel 4: Central Bank Buying
- Structural, price-insensitive buyer (de-dollarization)
- Provides long-term floor, doesn't drive short-term swings
- Key metric: "% of central banks buying gold"

### Channel 5: Tail Risk / Geopolitics
- Small weight, short-lived
- Geopolitical events affect gold primarily through rates/oil channel, NOT through "fear"
- Example: Iran peace deal → lower oil → market priced in Fed dovish → gold RALLIED (not fell)

## Cross-Asset Triangulation

| Pattern | Stocks | Gold | Silver | Bitcoin | Interpretation |
|---|---|---|---|---|---|
| "Tight money + good growth" | ↑ | ↓ | ↓ | ↓ | Real rates driving, growth positive |
| "Risk-off" | ↓ | ↑ | ↑ | ↓ | Safe haven, but check if BTC confirms |
| "Stagflation" | ↓ | ? | ? | ↓ | Mixed for gold, need real rate direction |
| "Reflation / easing" | ↑ | ↑ | ↑ | ↑ | Dovish Fed, falling real rates |

## Case Study: Iran Deal → ¥950 → FOMC → ¥911 (June 2026)

**Phase 1: Iran deal → gold SURGE to ¥950**
- Market logic: Iran peace → oil crash → lower inflation → Fed will cut → real rates ↓, USD ↓ → gold ↑
- This was a mispricing: market confused supply-side CPI improvement with reason for Fed easing
- Fed sees lower oil as POSITIVE growth shock (higher real incomes, stronger demand) → needs HIGHER rates

**Phase 2: FOMC falsifies the thesis**
- Warsh removes cutting bias, dot plot flips to hikes
- Real rates spike to 2.23%, USD to 3-month high
- Entire "Fed dovish" premise collapses → ¥950 → ¥911

**Phase 3: Stock-gold divergence**
- Stocks rally on Iran deal (lower oil = margin expansion + ERP compression)
- Gold falls (real rates up, inflation hedge demand down)
- BTC -5%, silver drops confirm: this is "tight money + good growth", not risk-off

**Key lesson**: ¥950 was built on a false premise ("Fed will cut"). ¥911 is not oversold — it's rational re-pricing after the false premise was removed.

## Pitfalls

1. Never start gold analysis from "what happened in the news" — start from "what happened to real rates and the dollar"
2. "Safe haven" is the weakest and most misused framework for gold
3. Oil ↓ ≠ Fed dovish — this is the most expensive confusion in gold trading
4. Gold and stocks can diverge for perfectly rational reasons (growth-driven rate hikes)
5. For 积存金 (CNY gold): always account for USDCNH offset

## References

- Case archive: `~/.hermes/references/gold-6-19-case-study.md`
- Gold scoring system: load `gold-investment-analysis` skill for quantitative model
- News timeline verification: see `gold-investment-analysis` skill → `references/news-timeline-verification.md`
- Analysis workflow: load `deep-analysis-workflow` skill for framework-execution separation pattern
- Fallback workflow: if this framework is insufficient, use `claude-code` Framework-First Analysis Pattern to extend it
