---
name: investment-analysis
description: "【通用量化投资框架方法论】教你如何为任意投资标的搭多因子评分体系——信号分层/时效衰减/置信度/数据管线/自动报告。| 跟 gold-investment-analysis 的区别：那个是已落地的黄金专属七因子打分系统（积存金），这个是「怎么搭一个框架」的通用方法论。跟 gold-macro-framework 的区别：那个是黄金宏观定价公式和传导机制，这个是量化评分系统搭建。"
version: 1.1.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [investment, analysis, framework, scoring, gold, commodity]
---

# Investment Analysis Framework Design

## Overview

Systematic methodology for building quantitative investment analysis frameworks. Produces a weighted multi-dimensional scoring engine with regime-switching logic, calibrated to the user's specific asset, investment horizon, and risk profile.

**Core principle:** Present the FULL framework for user evaluation before asking "what next." Never jump to next-step options before the user has seen and evaluated the work product.

## When to Use

Use this skill when the user asks for:
- Investment analysis framework for any asset (gold, stocks, crypto, etc.)
- Trading signal system / buy-sell recommendations
- Quantitative scoring model for investment decisions
- "Act as a financial analyst team"

## The Process

### Step 1 — Clarify Scope

Before any research, ask three questions:

1. **What asset?** (specific product — e.g., 积存金 vs 黄金ETF vs 期货 → different cost structures, different strategies)
2. **What time horizon?** (short-term swing / medium-term trend / long-term accumulation / mixed)
3. **Risk/liquidity constraints?** (urgent liquidity needs? maximum acceptable drawdown?)

### Step 2 — Parallel Research (use delegate_task)

Fan out two research subagents in parallel:

**Research Agent A — Analysis Frameworks:**
Research the most effective quantitative frameworks for this asset. Cover:
- Macro indicators (the foundational drivers)
- Technical indicators (asset-specific calibrations — don't use generic stock parameters)
- Sentiment & positioning indicators
- Valuation models (fair value, relative value, composite scoring)
- Signal synthesis approaches (weighted scoring, regime-switching, ensemble)
- Practical execution calendar (weekly/monthly/quarterly checklist)

**Research Agent B — Data Sources:**
Research accessible (preferably free) data sources for all indicators identified by Agent A. Cover:
- APIs and their endpoints, rate limits, fields
- Python libraries for data retrieval
- China-accessible alternatives where relevant

### Step 3 — Design the Framework

Synthesize research into a structured framework with:

1. **Multi-dimensional scoring engine** — typically 3-5 dimensions, each with:
   - Weight (must sum to 100%)
   - Specific indicators with thresholds
   - Scoring logic (-2 to +2 per indicator)

2. **Regime detection logic** — classify the current market environment and adjust weights/strategy

3. **Signal → action mapping** — clear score-to-action thresholds

4. **Execution calendar** — weekly/monthly/quarterly review cadence

### Step 4 — Present the FULL Framework

**CRITICAL — Don't skip this step or truncate it.**

Present each module clearly with:
- The indicators, their data sources, and their logic
- The specific thresholds for each signal
- The scoring formula and action mapping
- The regime-switching rules

Only AFTER presenting the full framework, ask the user to evaluate:
- Is the logic sound?
- Are the weights appropriate?
- Are the thresholds reasonable?
- What's missing?

### Step 5 — Iterate

Incorporate user feedback on weights, thresholds, missing indicators, or methodology changes. Re-present as needed.

### Step 6 — Advanced Analytics

Once the basic multi-dimensional scoring engine is built and running, layer on advanced analytical capabilities. These principles apply to any quantitative scoring system, not just investment.

#### 6a. Signal Layering (L1/L2/L3)

Classify every sub-signal by its **half-life**, not its source module:

| Layer | Chinese | Half-Life | Examples | Weight Treatment |
|-------|---------|-----------|----------|------------------|
| **L1** | 短期扰动 | 1-10 trading days | MACD cross, RSI extremes, ETF flow spikes | ×0.3 when conflicting with L2/L3 |
| **L2** | 中期驱动 | 1-6 months | Real yield trend, DXY direction, MA position | Standard weight |
| **L3** | 结构性锚 | 1+ years | Central bank reserves, de-dollarization, fiscal trajectory | Requires 3 consecutive confirmations to flip |

**Conflict resolution**: When L1 contradicts L2/L3, L1 is treated as noise — flag it but don't let it override the medium/long-term framework. When L2 bullish and L2 bearish signals coexist, the market is in genuine equilibrium and confidence should drop.

**Direction-confirmation for L3**: Structural anchors should be sticky. When L3 signals flip direction, require confirmation across multiple cycles before updating. A single contrary reading is not a reversal.

#### 6b. Data Freshness & Weight Decay

When a scoring system combines data sources with **different update frequencies** (daily, weekly, monthly), do not pretend all dimensions are synchronized. Use explicit freshness decay:

| Days Since Update | Weight Factor |
|-------------------|---------------|
| 0-7 days | 100% |
| 8-14 days | 80% |
| 15-30 days | 60% |
| 30+ days | 40% |

**Only apply to slow-frequency dimensions** (monthly data like M2, central bank reserves). Daily/weekly data dimensions refresh every cycle at full weight. The composite score's integrity improves because stale data is explicitly discounted rather than silently polluting the conclusion.

**Anti-pattern**: "假同步掩盖真异步" — a daily report that gives equal weight to a 30-day-old M2 reading and today's gold price produces worse conclusions than ignoring the stale dimension entirely.

#### 6c. Confidence Scoring as Honesty (0-100)

Confidence scoring answers: **"How reliable is today's conclusion given the signal distribution?"** — NOT "How good is our model?"

| Dimension | Max | What it measures | When it's low |
|-----------|-----|-----------------|---------------|
| A: Signal Consensus | 25 | % of strong signals pointing same direction | Market genuinely split ~50/50 |
| B: Layer Alignment | 25 | L1/L2/L3 direction agreement | Short vs. long-term forces in conflict |
| C: Signal Strength | 25 | Average absolute signal magnitude | No single factor overwhelming |
| D: Data Quality | 25 | Completeness ratio (1 - missing/total) | API failures, data gaps |

**Critical rule**: Never inflate confidence to make the model look better. Low confidence when signals are genuinely conflicting is **correct behavior**, not a bug. A system that outputs high confidence during market chaos is lying. 53/100 during a 50/50 split is honest; 75/100 during the same split is fraudulent.

When confidence is low, the correct action is to **reduce position size / defer decisions**, not to manipulate scores.

#### 6d. Report Frequency Aligned with Data Frequency

Match report cadence to the **slowest data source that drives actionable conclusions**. 

**Anti-pattern**: Daily reports when 40% of model weight comes from monthly data. This creates "今日分析" labels on conclusions that are 30 days stale.

**Correct pattern**: Weekly as primary report, with:
- Fast daily variables aggregated over the week (5-day mean, max single-day move)
- Slow variables at their natural refresh with explicit age labels
- No daily reports unless there's a threshold event trigger

**When to add a report frequency**: Only when there exists a data source whose natural frequency matches that cadence AND whose signal meaningfully changes at that cadence.

#### 6e. Claude Code as Design Consultant

For significant architectural changes (framework design, model review, analytical logic), use Claude Code as a design consultant. It reviews the current design and proposes improvements. Hermes Agent handles all code implementation.

> **Never let the designer and reviewer be the same model.** The reviewer must be independent, cold, and critical.

### Step 7 — Implementation & Build Patterns

Once the user approves the framework design, build the system following these patterns.

#### 7a. Validate Data Sources First (SMOKE TEST)

**This is the most important implementation step.** Before building the full system, verify each data source works:

```bash
python -c "
from data_fetcher import DataFetcher
f = DataFetcher()
print('gold:', 'OK' if f.fetch_gold_price() is not None else 'FAIL')
print('tips:', 'OK' if f.fetch_tips_yield() is not None else 'FAIL')
"
```

Classify results: ✅ working, ⚠️ needs config, ❌ broken. Fix data issues before building scorers. Data issues are the #1 cause of rework.

#### 7b. Modular Build Structure

```
project/
├── config.py          # Weights, thresholds, tickers, paths
├── data_fetcher.py    # One class, one method per source
├── module_a.py        # Scorer class per dimension
├── module_b.py        # Each returns (score, breakdown_dict)
├── scorer.py          # Composite engine + regime detection
├── main.py            # Entry point + report formatting
└── requirements.txt
```

**Rule**: Each scoring module MUST return `Tuple[float, Dict]` — (score, breakdown). The breakdown dict contains per-sub-component scores for debugging/reporting.

#### 7c. Scoring Architecture Rules

- **Weighted dimensions**: Each dimension gets a float weight. Weights MUST sum to 1.0. Regime detection can shift weights ±5%.
- **Threshold scoring**: Use `apply_threshold(value, [(low, high, score), ...])` pattern. Handle boundary values with `low <= value < high`.
- **Clamp everything to [-2, +2]**: Every module, sub-component, and composite must live in the same range for comparability.
- **Missing data = score 0**: When a data source is unavailable, score 0 (neutral). Don't fail. Don't guess. Log the gap.
- **Internal [-2,+2] vs user-facing 0-100**: Internal scores stay in [-2,+2] for math consistency. User-facing display converts to 0-100: `(score+2)/4*100`.

#### 7d. Composite Scoring Engine

```python
class Scorer:
    def __init__(self):
        self.modules = {name: ScorerClass() for name, ScorerClass in ...}
        self.regime = RegimeDetector()

    def run(self, data):
        regime = self.regime.detect(data)
        weights = adjust_weights(base_weights, regime)
        scores = {m: s.score(data) for m, s in self.modules.items()}
        composite = sum(s * weights[m] for m, s in scores.items())
        return composite, scores, regime
```

**Regime detection**: Use IF-THEN rules with scoring (not hard classification). Each regime gets a score; highest wins. Default to "mixed" when no signal is strong.

#### 7e. Data Source Patterns

See `references/python-financial-data-sources.md` for full details. Key patterns:

- **yfinance**: Never use `yf.download()` — use `yf.Ticker(ticker, session=requests_session).history()` with shared session and exponential backoff retry (4 retries, 5s base delay, 2s inter-call cooldown)
- **akshare**: Chinese column names change between versions — always inspect with `list(df.columns)` before mapping
- **FRED**: Requires free API key; set in `FRED_API_KEY` env var (never hardcode credentials)
- **Dual-network routing**: yfinance/FRED → proxy; akshare/eastmoney.com → DIRECT. Use Clash rule mode
- **Cache everything**: 1-day CSV caching with timezone-aware loading (`pd.to_datetime(index, utc=True)` then `tz_localize(None)`)
- **Cross-source data alignment**: When combining data from multiple ETFs with different date indices, use `pd.concat([s1, s2], axis=1).sum(axis=1).dropna()` — naive addition on mismatched dates silently produces NaN

#### 7f. Signal Damping

Save composite score to JSON each run. On direction change, dampen by blending with previous:
- Use 70/30 EMA weighting (`composite * 0.7 + prev * 0.3`) on direction changes
- After 2+ consecutive periods in same direction, trust the signal
- Track consecutive same-direction runs to let confirmed signals through

#### 7g. Report Generation

- **Console output**: Formatted text with bars, emojis, appropriate labels
- **Signal explanations**: Every signal in the report MUST carry a human-readable explanation with actual data values, not just a label. Build an `_explain_signal()` engine that maps each scoring component to a contextual sentence embedding key numbers.
- **User-facing 0-100 scale**: Consistent across all output
- **JSON output**: Full breakdown for programmatic use
- **Save to file**: For cron job consumption

## Personal Finance Research Pitfalls

When comparing savings rates, asset allocation ratios, or financial advice across different experts/institutions/countries:

- **Never mix unnormalized frameworks.** Different sources define "savings rate" differently (pre-tax vs post-tax, with/without employer match, including/excluding emergency fund). Always normalize to the same standard before comparing.
- **Verify each case individually.** Classify every source as ✅ verifiable, ⚠️ has data but different scope, or ❌ cannot confirm before including in a comparison.
- **Don't steer toward a pre-determined conclusion.** Present the full range of credible recommendations without cherry-picking. The user decides what applies to them.
- **"从零开始" means from zero.** When the user says to restart the analysis, discard all previous intermediate conclusions and rebuild from first principles.
- Full methodology in `references/financial-framework-comparison-methodology.md`.

## Pitfalls

**Design pitfalls:**
- **Jumping to "what next" before presenting the framework.** The user hired you to design the framework; they need to evaluate it before discussing execution. Present → evaluate → then discuss next steps.
- **Using generic stock parameters for commodities.** Gold trends differently — longer cycles, more persistent trends. MACD on weekly/monthly matters more than daily. RSI thresholds shift. Calibrate per asset.
- **Skipping the asset-specific product question.** 积存金 (accumulation plan with high fees) needs different strategy than gold futures or ETFs. The product structure constrains the strategy.
- **Not asking about time horizon before designing.** A daily swing trader needs completely different indicators and thresholds than a monthly accumulator.

**Advanced analytics pitfalls:**
- **Signal magnitude ≠ signal reliability**: A signal scoring +2.0 is not necessarily more predictive than one scoring +0.5. Don't use magnitude as a proxy for historical accuracy without validation.
- **Same-module double counting**: When adding a new dimension (e.g., geopolitical), ensure its sub-signals are orthogonal to existing ones. Geopolitical oil-gold resonance must strip out DXY effects (already captured by macro) before scoring.
- **Proxy decay**: A proxy built on correlation (e.g., "DXY weakness = geopolitical risk") will fail when the underlying correlation breaks. Mark all proxy-based signals explicitly.
- **Direction-confirmation mismatch**: When L3 signals (structural) flip direction, require confirmation across multiple cycles before updating. Structural anchors should be sticky.

**Data pipeline pitfalls (see `references/python-financial-data-sources.md` for full details):**
- **yfinance `download()` silently fails**: Returns empty DataFrame on rate limit, not an exception. Use `Ticker(session=session).history()` with retry.
- **akshare column names**: Chinese names change between versions. Always `list(df.columns)` before mapping.
- **Cache timezone**: CSV round-trips lose timezone. Force `tz_localize(None)` after loading.
- **Cross-ETF volume misalignment**: `pd.concat([etf1, etf2], axis=1).sum(axis=1)` not naive `vol1 + vol2` — mismatched dates silently produce NaN.

## Consolidation Note

This skill is the umbrella for quantitative investment framework design and implementation. It absorbed the following agent-created siblings:
- `quantitative-scoring-system` — design principles (signal layering, freshness decay, confidence scoring) integrated into Step 6 (archived 2026-06-10)
- `data-pipeline-builder` — implementation patterns (modular build, data source handling, coding conventions) integrated into Step 7 (archived 2026-06-10)
- `claude-research-to-png` — Claude Code research → PNG infographic pipeline demoted to `references/claude-research-to-png.md` (archived 2026-06-17)

## Reference Files

- `references/gold-framework.md` — Complete gold investment framework for 积存金 (v1 four-dimension design)
- `references/gold-scoring-architecture.md` — Seven-dimension gold scoring system architecture with signal layering, confidence scoring, and data freshness decay (v3 design)
- `references/python-financial-data-sources.md` — yfinance, akshare, fredapi, COT pitfalls and workarounds: rate limiting, Chinese columns, cache strategies, COT parsing
- `references/claude-research-to-png.md` — Claude Code investment research → PNG infographic pipeline: prompt template, Claude Code invocation, HTML rendering, Playwright+Edge screenshot workflow
- `references/serenity-dual-skill-system.md` — Serenity 双 skill 体系：serenity-skill（产业链卡点）+ serenity-value（估值 overlay）的架构、使用方式、prompt 模板、恢复方法
- `references/serenity-the-person.md` — Serenity 博主本人（@aleaborteddit，白毛股神）：身份背景、方法论哲学、与用户 skill 体系的关系
- `references/dca-retirement-calculator.md` — DCA 退休金计算器：日定投终值公式、多阶段策略分析框架、财务承受力评估、多情景对比输出规范
- `references/financial-framework-comparison-methodology.md` — 金融框架对比方法论：统一口径、逐个核实、不带结论、不硬推。适用于对比不同理财专家/机构的储蓄率/资产配置建议
- See also: `gold-investment-analysis` skill for the full v3.1 implementation with cron jobs, project structure, and 24+ resolved pitfalls from production debugging
## Framework Architecture Template

```
┌─────────────────────────────────────────────────┐
│          Multi-Dimension Scoring Engine          │
│                                                  │
│  Dimension 1 (W%) + Dimension 2 (W%) + ...       │
│                      ↓                           │
│          Composite Score [-2, +2]                │
│                      ↓                           │
│     Regime Detector (adjusts weights)            │
│                      ↓                           │
│  ┌─ Advanced Analytics Layer ──────────────┐    │
│  │  Signal Layering (L1/L2/L3)              │    │
│  │  Confidence Scoring (0-100)              │    │
│  │  Synthesis Generation (narrative)        │    │
│  └──────────────────────────────────────────┘    │
│                      ↓                           │
│    Action + Allocation + Price Guidance          │
└─────────────────────────────────────────────────┘
```

Default dimension weights (adjust per asset and horizon):
- **Macro/Structural**: 25-35% (foundational drivers)
- **Technical/Trend**: 15-20% (price action confirmation)
- **Sentiment/Positioning**: 10-15% (crowding/contrarian signals)
- **Valuation**: 15-20% (are you overpaying?)
- **Specialized dimensions**: 10-25% (asset-specific: central bank for gold, supply-demand for oil, etc.)


