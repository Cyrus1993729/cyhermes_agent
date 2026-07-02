# Pointer-to-File Pattern for Low-Frequency Knowledge

## Problem

Some knowledge entries are:
- Too detailed for memory's 2,200 char limit
- Low-frequency (may not be needed for weeks/months)
- But still important enough that we don't want to forget they exist

Storing full details in memory wastes capacity. Deleting them loses institutional knowledge.

## Solution: Two-Tier Storage

### Tier 1: Memory (pointer)
A compact one-line summary in memory that answers "what is this and where do I find details":

```
美股投资指南 → ~/.hermes/references/美股投资指南.md（QDII纳指定投 + 汇丰卓越→香港+美国账户路径）
```

~60 chars vs. ~140 chars (57% reduction).

### Tier 2: Reference file (details)
Full information in `~/.hermes/references/<topic>.md` with everything needed to act:
- What it is
- How to use it
- Pitfalls
- Links/commands

## When to Apply

| Criterion | Pointer-to-file | Keep in memory |
|:---|:---|:---|
| Frequency | Low (weeks between uses) | High (every session) |
| Detail level | Needs commands, links, multi-step | A single fact or short rule |
| Cost of forgetting | Moderate (nice to have) | High (catastrophic if lost) |
| Size | >100 chars in memory | <80 chars in memory |

## Real Example from 2026-06-18 Session

### Before (in memory, 300 chars)
```
Scrapling (D4Vinci/Scrapling): 64K⭐自适应爬虫框架。Python, PyPI:scrapling...
安装：pip install "scrapling[all]" && scrapling install...
```

### After (pointer in memory, 70 chars)
```
Scrapling爬虫框架 → ~/.hermes/references/Scrapling爬虫框架.md（64K⭐，欧美反爬，MCP可集成，用时装）
```

### Reference file (`~/.hermes/references/Scrapling爬虫框架.md`)
Contains full installation commands, capability matrix, suitable/unsuitable scenarios, Docker info.

### Savings
- Scrapling: 300→70 chars (77%)
- 美股投资指南: 140→60 chars (57%)
- Combined: 310 chars freed

## Agent Behavior

When the pointer entry is encountered in memory:
1. Recognize the `→ <path>` syntax as a pointer
2. If the topic becomes relevant to the current task, load the reference file
3. Do NOT load the file preemptively — only when needed

## Compatibility with Existing Hygiene Protocol

This is an additional tool beyond dedup/compression. Apply in Phase 4 (Prune personal notes):
- For entries >100 chars that are low-frequency → consider pointer-to-file
- Create reference file first, then replace memory entry with pointer
