# Signal Analysis Framework Design Specification

> Author: Claude Code (design consultant)
> Date: 2026-06-03
> Purpose: Design specification for upgrading gold scoring system from signal listing to layered analytical synthesis

## Core Design Principle

**Signals are input, synthesis is reasoning, recommendations are output.** There must be a visible logical chain between all three — not a black-box score followed by a one-line conclusion.

---

## 1. Signal Layering (L1/L2/L3)

Split all sub-signals by half-life rather than by module:

| Layer | Definition | Half-Life | Examples |
|-------|-----------|-----------|----------|
| **L1** | Short-term noise | 1-10 days | MACD direction, RSI overbought/oversold, COT extreme positioning, ETF short-term flows |
| **L2** | Medium-term driver | 1-6 months | Real yield trend, DXY direction, MA position, fair value residual, GSR |
| **L3** | Structural anchor | 1+ year | PBOC reserve trend, fiscal deficit trajectory, de-dollarization, gold resilience vs equities |

### L1 Handling Rules
- If L1 aligns with L2/L3 → weighted ×1.0
- If L1 contradicts L2/L3 → weighted ×0.3, annotated as "noise, doesn't change mid-term view"
- L1 alone never triggers "aggressive buy" or "pause" actions

### L3 Handling Rules
- Direction changes require 3 consecutive confirmation periods
- L3 + L2 alignment → confidence auto-upgrades
- L3 factors must be explicitly mentioned in final synthesis

---

## 2. Contradiction Handling

### Four-Step Framework

**Step 1: Identify logical root**
Contradictions arise from one of three mechanisms:
- Transmission lag (both signals real, different timing)
- Pricing difference (signals act on gold's different attributes: commodity vs monetary vs safe-haven)
- Genuine uncertainty (market at turning point)

**Step 2: Determine dominant signal**
Priority rules (applied sequentially):
1. Higher layer prevails (L3 > L2 > L1)
2. At same layer, trend signal > level signal (direction change > absolute value)
3. At same layer and type, side with more signals forming consensus

**Step 3: Evaluate market meaning**

| Contradiction Type | Market Meaning | Action Implication |
|-------------------|---------------|-------------------|
| L1 bearish vs L2 bullish | Short-term pressure, mid-term up | Buy dips, don't chase |
| L2 bearish vs L2 bullish | Market debating, direction uncertain | Reduce position changes, wait for divergence |
| L2 bearish vs L3 bullish | Cyclical correction, structural up | Maintain DCA, don't reduce |
| L2 bullish vs L3 bearish | Short rally, trend down | Cautious, reduce new buys |

**Step 4: Generate dialectical text**
Contradictions must be explicitly presented in synthesis, not averaged away.

---

## 3. Confidence Scoring (Four Dimensions, 0-100)

### Dimension A: Signal Consensus (0-25)
- % of strong signals (|score| > 0.2) pointing same direction
- ≥75% same → 25; 60-75% → 15; 50-60% → 5

### Dimension B: Layer Alignment (0-25)
- All three layers (L1+L2+L3) same direction → 25
- Two layers aligned → 15
- One layer or conflict → 5

### Dimension C: Signal Strength (0-25)
- Average absolute signal magnitude as decisiveness proxy
- For P3: replace with historical similar-situation hit rate

### Dimension D: Data Quality (0-25)
- Completeness ratio across all components
- Fewer missing/error statuses → higher score

### Confidence → Action Constraint

```
High confidence (80+): follow advice at full strength
Medium confidence (60-79): follow, moderate position sizing
Low confidence (40-59): conservative, reduce operation frequency
Insufficient (<40): maintain status quo, await clarity
```

---

## 4. Five-Paragraph Synthesis Structure

### Paragraph 1: Market Positioning
One-sentence macro cycle positioning + structural (L3) factors. Give the reader coordinates.

### Paragraph 2: Core Drivers
Top 1-2 L2 signals with causal chain explanation. "Because X, therefore Y on gold."

### Paragraph 3: Risks & Contradictions
Explicitly state the biggest uncertainty source. Demonstrate dialectical thinking — avoid blind trust in your own model.

### Paragraph 4: Directional Judgment
Clear directional bias (up / slight-up / neutral / slight-down / down) with:
- Time dimension ("next 1-3 months", not "going forward")
- Confidence level
- Validity period ("until next FOMC meeting or major data release")

### Paragraph 5: Investor Action Advice
- Specific, actionable, in plain language for retail investors
- Include price trigger conditions ("if gold drops below X, then Y")
- Distinguish "analysis" from "advice" — analysis is about the market, advice is about what to do

### Quality Standards

**Must include:**
- Explicit time dimension
- Causal logic ("because", not "shows")
- Conditional statements ("if X happens, then Y")
- Emotional anchoring ("this doesn't mean...", "this doesn't change...")

**Must avoid:**
- Unconditional absolute statements ("gold will definitely...")
- Technical indicator pile-up without explanation
- Disconnect between analysis and advice (bearish analysis + buy advice = broken)

---

## 5. Output Format (Recommended)

```
┌─────────────────────────────────────────┐
│ Gold Analysis Report  YYYY-MM-DD        │
│ Confidence: [高/中/低/存疑]  Score: X   │
└─────────────────────────────────────────┘

【综合研判】
Five-paragraph synthesis (150-250 characters)

【信号全景图】
▲ Structural (L3): [signal list with +/-]
● Mid-term Drivers (L2): [signal list with contradiction notes]
△ Short-term Noise (L1): [signal list, note if affects mid-term]

【分项评分】
Module-level scores with weights

【投资建议】
Action: [aggressive/mild/normal/hold/pause]
Time dimension: [this month / this quarter]
Triggers: [if X, adjust to Y]
```

### Language Principles for 积存金 Investors

- Avoid jargon: explain "real yield" as "扣除通胀后持有美债的真实收益"
- Give action anchors, not probability ranges: not "60% chance of going up", say "若月末未跌破XXX元/克，定投计划维持不变"
- Separate "judgment" from "advice" visually
- Mark validity period: "本判断适用至XXXX年XX月XX日或下一次重要数据发布前"

---

## Implementation Priority

| Priority | Item | Difficulty | Impact |
|----------|------|-----------|--------|
| **P0** | Add five-paragraph synthesis | Low | High — most direct user impact |
| **P1** | Implement three-layer signal classification | Medium | High — resolves contradiction confusion |
| **P2** | Build four-dimension confidence scoring + action constraint | Medium | Medium — improves conclusion credibility |
| P3 | Build historical situation database for dimension C | High | Medium — requires data accumulation |
