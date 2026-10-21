# Real Cleanup Example (2026-06-04)

## Before

| Store | Usage | Entries |
|-------|-------|---------|
| User profile | 83% (1,120/1,375 chars) | 8 |
| Personal notes | 70% (1,541/2,200 chars) | 6 |

### User profile entries (8)

1. 投资黄金积存金，中长线，deepseek-v4-pro，呈现框架优先 → 137 chars
2. "需要权限必须中文说明" → 63 chars
3. "需要权限时说明做什么为什么，输出中文" → 72 chars (duplicate of #2)
4. "当需要权限时，必须用中文说明，不要用英文" → 58 chars (duplicate of #2)
5. "rm -rf等危险操作需中文解释，有Claude Code" → 94 chars (duplicate of #2)
6. "任务中主动汇报进度" → 46 chars
7. "评分0-100刻度，信号带数据和因果" → 66 chars
8. "极度重视准确性，Claude设计评审助手实现，中文" → 130 chars (duplicate of #1)
9. "quantitative/system design: discuss with Claude Code..." → 454 chars (English duplicate of #1/#7)

## After

| Store | Usage | Entries |
|-------|-------|---------|
| User profile | 16% (227/1,375 chars) | 2 |
| Personal notes | 70% (1,541/2,200 chars) | 6 |

### Resulting user profile entries (2)

1. **投资画像** (merged #1 + #7 + #8 + #9): 中国黄金积存金投资者，中长线策略，无短期流动性压力。极度重视准确性——不允许为提升置信度而编造数据。评分用0-100刻度，信号需带具体数据和因果分析。模型偏好deepseek-v4-pro。分工：Claude Code设计评审，助手编码实现。呈现分析时先完整给出框架/结论，等用户评估后再讨论下一步。

2. **沟通规范** (merged #2 + #3 + #4 + #5 + #6): 沟通规范：所有输出和报告使用中文。需权限时用中文解释在做什么、为什么需要。任务进行中主动汇报进度，不沉默。代码工作可委托给 Claude Code。

## What Failed

- Attempted to remove standalone `x` entry from personal notes. `old_text='x'` matched 6 entries (every entry contained the letter 'x' in "export", "proxy", "exponential", etc.). Entry is too short to isolate via substring matching. Lesson: never save single-character entries.
- Accidentally removed Clash Verge routing entry during `x` cleanup attempt. Immediately re-added. Lesson: verify `old_text` uniqueness before remove.

## Key Numbers

- **83% → 16%**: user profile usage reduction
- **8 → 2**: user profile entry count reduction
- **0 information lost**: all preferences preserved, just consolidated
- **4 "Chinese/permissions" variants → 1 entry**
- **3 "investment/accuracy" variants → 1 entry**
