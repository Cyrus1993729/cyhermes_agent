---
name: deep-analysis-workflow
description: "【框架执行分离】复杂分析时，先自检「有没有对应领域的框架」→ 有则加载框架 skill → 无则先向 Claude 借框架骨架再填数据审视。适用领域：金融/投资/黄金/产业链/AI/技术/商业/任何需要结构化推理的领域。| 被 xiaohongshu-analysis、bilibili-understand、gold-investment-analysis 等工作流配方条件触发。"
version: 1.1.0
category: software-development
tags: [analysis, framework, methodology, claude-code, workflow]
---

# Deep Analysis Workflow: Framework-Execution Separation

## When to Use

Any complex analysis task where you don't have a well-established analytical framework — finance, macroeconomics, technology architecture, strategy, business model evaluation, etc.

## Core Principle

**Separate "figuring out the framework" from "filling in the data."** Claude is strong at frameworks (cheap, few tokens). You are strong at execution (searching, verifying, computing). Don't do both poorly — split them.

## Workflow

```
Receive complex analysis request
    │
    ▼
Self-check: Do I have a domain framework?
    │
    ├─ YES → Load the skill, apply framework, fill data
    │
    └─ NO  → Step 1: Ask Claude (cheap, ~50 tokens):
              "这个问题的分析框架应该是什么？关键维度有哪些？"
              Get the framework only — not the full analysis.
              │
              ▼
            Step 2: Apply the framework yourself
              - Search for data
              - Verify facts and timelines
              - Fill in each dimension
              - Produce the analysis
              │
              ▼
            Step 3: Save the framework as a skill
              (so next time it's a YES on the self-check)
```

## Why This Works

| Approach | Token Cost | Accuracy | Framework Quality |
|---|---|---|---|
| Full Claude analysis | High (~3000+ tokens) | High | Good |
| Self + no framework | Low | Low (errors) | Ad-hoc |
| **Framework from Claude + Self execution** | **Low (~200 tokens)** | **High** | **Good** |

## Memory vs Skill vs Reference

Frameworks follow a three-layer storage design:

| Layer | What | Size Limit | Content |
|---|---|---|---|
| **Memory** | Triggers only | 2,200 chars | `"domain → load skill-name"` |
| **Skill** | Full framework | Unlimited | Steps, dimensions, pitfalls, formulas |
| **Reference** | Case studies | Unlimited | Specific instances, data, reports |

**Rule**: Never store framework details in memory. One line trigger → full framework in skill.

## Example: Gold Analysis

- Memory trigger: `黄金分析→先load gold-macro-framework skill`
- Skill (`gold-macro-framework`): Full pricing formula, transmission channels, cross-asset triangulation
- Reference: `gold-6-19-case-study.md` — the specific June 2026 event

## Related Templates

- `references/kai-fu-lee-claude-prompt.md` — 李开复的 Claude 系统提示词，用于高精度分析时提升 AI 回答质量（标注来源可信度、反奉承、不编造）。高 stakes 分析对话中可以要求 AI 遵守类似规则。

## When NOT to Use

- Simple factual questions (no framework needed)
- Tasks where you already have a loaded skill with the framework
- One-off lookups that won't recur

## Pitfalls

1. **Skipping the self-check** — jumping into analysis without first asking "do I have a framework?" is the root cause of shallow, error-prone analysis.
2. **Asking Claude for the full analysis** instead of just the framework — wastes tokens and you learn nothing.
3. **Not saving the framework** after the task — the same gap will recur next session.
4. **Storing frameworks in memory** — memory fills up fast; skills are unlimited.
