# Claude Code Red-Team Design Review Pattern

Use Claude Code (`-p` print mode) as a critical design reviewer. This pattern
was discovered and validated through two successful uses in a single session.

## When To Use

- User presents a design document, proposal, or idea list
- User wants objective, critical feedback — not praise or balance
- User explicitly asks for "红队审查" (red-team review) or "找Claude讨论"
- The output should help the user decide whether to build, pivot, or kill

## Two-Round Pattern

### Round 1: Pure Red-Team Review (找问题)

Prompt Claude to attack the design mercilessly:

```
你是红队审查员。用中文回复。

请先阅读这份设计文档：{file_path}

从红队视角进行严格审查：
1. 不找优点，只找问题和风险
2. 重点审查：可实现性、工程复杂度、死循环、脆弱节点、根本矛盾
3. 对每个问题给出严重程度评级（致命/严重/中等/轻微）
4. 总体判断：该不该投入工程实现？
5. 不要客气，不要找补，不要"虽然...但是..."
```

### Round 2: Engineering Fixes (找解决方案)

If the user says "我不想放弃，有什么办法" — follow up:

```
继续红队角色，但任务不同。

用户不接受投降方案，一定要做。在这个前提下，
针对你发现的每个致命/严重问题，逐一给出工程解决方案。

约束条件：{list actual platform constraints}

目标：保留核心方法论，砍掉不可实现的部分。
```

## Key Prompt Design Rules

1. **Explicitly ban balance** — "不要找优点" / "不要客气" prevents the model from softening
2. **Chinese output** — the user reviews these results in Chinese
3. **Severity ratings required** — forces structured judgment, not vague impressions
4. **File path, not inline content** — let Claude read the file itself to save context
5. **State constraints** — the engineering-fix round must know what's actually available

## Integration with Hermes

```bash
# Pre-condition: proxy must be set for Claude Code
export HTTP_PROXY="http://127.0.0.1:7897"
export HTTPS_PROXY="http://127.0.0.1:7897"

# Round 1
claude -p "你是红队审查员...请先阅读 {file_path} ..." 

# Round 2 (only if user wants to proceed)
claude -p "继续红队...针对问题给出工程方案..."
```

## Round 3: Build the Optimal Version (自己写最优版本)

After Claude has critiqued a design, ask it to write ITS own version:

```
基于你的批判意见，直接写出一版你认为最优的方案。

约束条件：{specific to the user's situation}

要求：具体到可以直接开发的程度。不要任何"建议考虑"，
每个地方都给出确切的答案。包含：定位、模块、数据源、
评分模型、信号日志、技术栈、30天实施计划、自我批判。
```

This round emerged when the user said "你让他基于这一版...给出一版他认为最优的方案".
Claude produced a complete, concrete specification with specific API URLs, code
snippets, and acceptance criteria — far more actionable than generic critique.

**Key addition**: the prompt must include "**你作为红队，给自己这版方案的自我批判**"
— this forces Claude to acknowledge its own blind spots, preventing overconfidence.

## Round 4: Structured Comparison (对比打分)

When choosing between options, do NOT jump directly to a conclusion. First do a 
weighted multi-dimensional comparison:

```
针对每个候选方案，从以下N个维度用0-10打分：

| 维度 | 权重 | 含义 |
|------|------|------|
| 可执行性 | 25% | 个人能否执行？需要特殊权限吗？ |
| 数据可得性 | 20% | 数据能不能稳定、免费拿到？ |
...（根据问题领域定义维度）

每个维度打分时必须给出具体论据。
按加权总分排序，给出明确的MVP组合建议。
```

This pattern emerged when the user corrected Claude for jumping from 5 categories 
to 1 without comparison: "为什么把品类从5个只简化到一个？应先对比再决定。"

**Pitfall**: Do NOT skip comparison and go straight to conclusion. The user expects
structured, evidence-based narrowing, not intuition-based jumping.

## Meta-Review (审查审查本身)

When the user sends someone else's review/critique, have Claude review THAT review:

```
现在有一份文档，是对原始方案的审查与重构提案。
你的任务是：审查这份审查文档本身。

从以下角度进行元审查：
1. 审查者自己的盲区
2. 它的核心建议是否经得起推敲
3. 它自己的论证是否存在类似错误
4. 整体质量判断

不要客气。这份文档本身是在批评别人的方案，
所以你也应该以同样的标准审视它。
```

This was used to review a friend's critique document, uncovering that the reviewer
had committed the same error they criticized (equating technical feasibility with
business viability).

## Validated Results

This pattern suite has been used for:
1. v3.1-DRE 研究院 Agent 设计 → 7 fatal/severe issues → 9-file fix proposal (Round 1+2)
2. 11个赚钱方案脑洞 → eliminated 5, recommended 3, added 1 bonus (Round 1)
3. 套利监控机器人 v1 → 5品类七维对比 → 黄金胜出 8.60/10 (Round 4)
4. 朋友审查文档 → 元审查揭示自我矛盾 (Meta-Review)
5. 黄金价差监控 → Full spec with API URLs, code, 30-day plan (Round 3)

The method consistently produces higher-quality critique than in-session analysis
alone. The two-round pattern evolved into a four-round suite: attack → fix → compare 
→ build-the-optimal.
