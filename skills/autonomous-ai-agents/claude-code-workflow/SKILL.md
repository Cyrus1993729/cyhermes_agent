---
name: claude-code-workflow
description: "【用户自定义的 Claude Code 调用规则】模型选择协议、进度上报格式、操作确认要求。| 跟 claude-code 的区别：那个是 Claude Code CLI 本身的安装/命令/权限，这个是用户自己定的「什么时候用哪个模型、怎么汇报」的规则。两者需同时加载。"
requires: [claude-code]
license: MIT
compatibility: Hermes Agent → Claude Code CLI
metadata:
  author: user-custom
  version: "1.8.0"
  last_updated: "2026-07-03"
  changelog: "新增 Rule 0 401 诊断（claudeCodeFirstTokenDate: null）。新增 references/opus-code-review-workflow.md（Opus 红队审查 + 出 diff 四步流程）。"
---

# Claude Code Workflow Rules

User-specific rules for how Hermes Agent should orchestrate Claude Code. These rules apply every time Claude Code is invoked, regardless of the task.

## Rule 0: Proxy — 🔴 RED LINE

**🔴 多次无代理直连 Claude Code 可能导致 Anthropic 封号。这是用户明确划定的红线。**

Claude Code CLI (Node.js) 不会自动走系统代理。从中国直连 `api.anthropic.com` → 区域封锁 → 403。多次裸连积累异常流量可能触发账号安全审查。

### 调用前强制检查

每次调 `claude` 之前：
1. 确认代理存活：`curl -s --proxy http://127.0.0.1:7897 https://api.anthropic.com -o /dev/null -w "%{http_code}"`
2. 确认 env var 已 export：`echo $HTTP_PROXY $HTTPS_PROXY` 不为空
3. **代理挂了 → 宁可放弃本轮调用，也不裸连**

### 正确调用格式

```bash
export HTTP_PROXY="http://127.0.0.1:7897" HTTPS_PROXY="http://127.0.0.1:7897" && claude -p "..." --model opus --max-turns N --output-format text
```

### 代理持久化

代理变量已通过 `setx` 写入 Windows 注册表（`HKCU\Environment`）。**换端口时需两处同步更新：**
- 注册表：`setx HTTPS_PROXY "http://127.0.0.1:<新端口>"`
- 当前终端：`export HTTPS_PROXY="http://127.0.0.1:<新端口>"`

### 可用路径（⚠️ 调用前必读）

| 路径 | 状态 | 说明 |
|------|------|------|
| Claude Code CLI (`claude -p`) | ✅ **唯一可用** | 需代理。Google Play Pro 订阅含 CLI 权限 |
| Anthropic Direct API | ❌ 403 | Google Play 订阅不含 API key 权限 |
| Hermes Nous Provider | ❌ 余额不足 | OAuth 已配，需在 portal.nousresearch.com 充值 |
| `delegate_task` 调 Opus | ❌ **禁止使用** | delegate_task 走 Nous Portal API，余额始终不足。多次尝试只会反复失败并消耗 API 调用次数 |

### 🚨 Pitfall: delegate_task 调 Opus（最高频错误 — 2026-07-01 反复犯）

**症状：** Agent 想调 Opus → 走到 `delegate_task` → 子 agent 用 `Model: anthropic/claude-opus-4.8` → HTTP 404 / credits depleted。

**根因：** `delegate_task` 的子 agent 通过 `delegation.provider` / `delegation.model` 配置路由，默认走 Nous Portal API。该 API 需要独立充值，与 Google Play Claude Pro 订阅无关。

**正确做法：** 任何时候要调 Opus，必须用 `terminal()` 执行：
```bash
export HTTP_PROXY="http://127.0.0.1:7897" HTTPS_PROXY="http://127.0.0.1:7897"
timeout 60 claude -p "回复OK" --model opus --max-turns 1  # smoke test 先行
claude -p "完整任务" --model opus --max-turns N --output-format text
```
**永远不要**用 `delegate_task` 来调 Opus。这不是"配置错误"，是路径从根本上就不可用。

### 故障排查速查

**🔵 401 排查（2026-07-03 新增）：** 代理正常但返回 401 → OAuth token 过期。诊断：
```bash
python -c "import json,os; d=json.load(open(os.path.expanduser('~/.claude.json'))); print('claudeCodeFirstTokenDate:', d.get('claudeCodeFirstTokenDate'))"
```
`claudeCodeFirstTokenDate: null` → CLI 从未成功获取 token 或已完全过期，需刷新。修复：`claude auth login`（需 PTY 模式，会打开浏览器授权页，用户手动完成授权后自动恢复）。

403 时按顺序排查：① 代理是否 export？② 代理是否存活？③ 端口是否正确？→ 参见 `references/claude-code-auth-diagnosis.md`

## Rule 1: Model Selection Protocol

**CRITICAL — never change the model without explicit user approval.**

- If the user specifies a model (e.g., "用 Opus 跑"), use exactly that model. Do not downgrade or switch.
- If the first run with the user's chosen model appears slow or produces no output, do NOT silently switch to a faster model (Sonnet, Haiku, etc.). Instead:
  1. Wait a reasonable time (at least 5 minutes for deep research tasks)
  2. Report the status to the user
  3. ASK the user whether they want to continue waiting, switch models, or try another approach
- The user may have reasons for choosing a specific model (deeper reasoning, different strengths) that the agent should not override.

## Rule 2: Action Confirmation Protocol

**CRITICAL — confirm the approach before executing, especially for modifications.**

- Before making ANY change to files, configuration, installed skills, or running any action that has side effects, state the plan and ask for confirmation.
- This includes but is not limited to:
  - Modifying skill files (even user-created ones)
  - Changing Claude Code flags or parameters
  - Installing or removing software
  - Modifying project configuration
- **🔴 基础设施改动专项规则**：当 Opus 完成红队审查并推荐了代码/配置改动方案后，必须走完整六步管线（sprint-contract → 分析文档 → Opus 审查 → 用户确认 → diff+改 → 千问 L1），不可跳过任何一步。详见 `references/opus-code-review-workflow.md`。
- The only exception is when the user explicitly says "just do it" or equivalent.

## Rule 3: Progress Reporting During Long Tasks

**CRITICAL — provide periodic status updates during long-running tasks.**

- When Claude Code is running a deep research task (web searches, multiple turns), check progress every 2-3 minutes.
- Report to the user:
  - That the task is still running
  - How long it has been running
  - Any visible progress (e.g., "first turn complete, now searching")
- If the task has been running with zero visible output for >5 minutes, flag this to the user and ask how to proceed.
- Do NOT leave the user wondering whether the task is alive or dead.

## Rule 5: L2 Independent Review Pattern（Claude 独立评审模式）

**When making a consequential decision about a tool/framework/approach, ask Claude (Sonnet) for an independent judgment before committing.**

Applicable when:
- Evaluating whether to adopt/install a new tool
- Assessing a technical recommendation you've made
- The user is uncertain and wants a second opinion

The pattern (4 steps):
1. **Present the case to Claude** — describe the context, your own analysis, and your recommendation
2. **Ask explicitly for disagreement** — "请给出你的独立意见（同意/不同意/部分同意，并解释理由）" and "我的分析有没有遗漏或偏差？"
3. **Use `--model sonnet`** for L2 (quick validation), `--model opus` for L3 (new-domain framework design). The user decides which.
4. **Synthesize** — compare Claude's judgment against yours, identify blind spots, present the final recommendation.

**Key principle:** Claude should be asked to *judge your recommendation*, not to make the recommendation from scratch. This surfaces blind spots you missed. See `references/l2-independent-review-pattern.md` for the full template.

## Rule 6: Skill Modification Protection

**Do not modify installed skills without explicit user permission.**

- Skills installed from external sources (like serenity-skill from GitHub) represent the author's methodology. The user has chosen to use them as-is.
- If the user wants to extend a skill's behavior, create a NEW companion skill rather than modifying the original.
- If a modification is accidentally made, revert it immediately when the user objects.

## Rule 8: 🔴 delegate_task ≠ Claude Code — NEVER Confuse Them

## Rule 9: Two-Round Opus Prompt Drafting（提示词两轮起草 — 2026-07-01）

**delegate_task routes through the configured delegation provider, NOT through Claude Code CLI.** If delegation provider/model is configured as Nous/Opus, it will fail with "credits depleted" — NOT because Opus is broken, but because Nous Portal API requires a separate balance that this user does not have.

**This mistake happened on 2026-07-01:** the agent repeatedly used `delegate_task` to try calling Opus, got "credits depleted" errors, and told the user "Opus余额不足需要充值" — which was completely wrong. Opus is fully available through Claude Code CLI (`claude -p --model opus`).

### When user says "让Opus来分析" / "发给Opus"

✅ **CORRECT:** `export HTTP_PROXY="http://127.0.0.1:7897" HTTPS_PROXY="http://127.0.0.1:7897" && claude -p "..." --model opus --max-turns N`
❌ **WRONG:** `delegate_task(...)` with Nous/Opus config — will always fail

### delegate_task ≠ MOA either

MOA (Mixture of Agents) runs through Hermes's MOA pipeline with multiple models + aggregator. `delegate_task` spawns subagents that use the parent model or whatever is in delegation config. They are completely different mechanisms. MOA is triggered via `/moa` slash command, not via `delegate_task`.

### When to use delegate_task

- Parallel independent workstreams (research A + research B simultaneously)
- Reasoning-heavy subtasks using the CURRENT model (not switching models)
- Tasks that would flood context with intermediate data

### When NOT to use delegate_task

- ❌ Calling a specific model (Opus, Sonnet, etc.) — use `claude -p --model <name>` instead
- ❌ Running MOA — use `/moa <preset>` slash command
- ❌ Simple tool calls — just call the tool directly

## Rule 9: Two-Round Opus Prompt Drafting（提示词两轮起草 — 2026-07-01）

**When the user asks to analyze a document with Opus, use a two-round workflow. Do NOT put all instructions in one prompt.**

### Round 1: Opus proposes questions（先出问题，不读文档）

Tell Opus about the user's background and the document topic. Ask it to propose 5-8 questions it wants to answer from the document, with a brief explanation of why each matters to the user. **Do not give Opus the document yet.** The output goes to the user for review.

### User review & confirmation

The user reviews the questions, may ask the agent to evaluate which are practical vs. academic. Revise if the user asks. Only proceed after explicit confirmation.

### Round 2: Opus reads and answers

Send the document (pre-extract PDF text with PyMuPDF if needed). Remind Opus of its own questions. Ask it to read and answer each one, with specific section references from the document.

### Why this pattern

- User wants to steer the direction before Opus invests reading time
- 88-page documents need focused reading, not general summaries
- User can filter out purely academic questions and keep only practical ones
- One-round "here's the PDF, analyze it" produces unfocused output that wastes Opus credits

### Key pitfalls

- **Do NOT** include Round 2 instructions in Round 1's prompt. The first prompt should ONLY ask for questions.
- **Do NOT** skip the user review step. Even if the questions look good to you, the user must confirm.
- **🔴 FEED THE DOCUMENT, NOT THE PATH（2026-07-01 踩坑）**：Claude Code CLI 的 `-p` 模式下，Opus 运行在沙箱中，**没有本地文件系统访问权限**，也没有 PDF 阅读工具（pdftoppm 等）。只提供文件路径（如 `C:\Users\...\paper.pdf`）→ Opus 打不开 → 只能凭通用知识回答 → 用户指出"怎么会让 op 读不到 PDF 就回答呢？"。**正确做法**：预先用 `pdftotext` 或 `PyPDF2` 把 PDF 提取为文本 → 将文本直接嵌入提示词 → 再发给 Opus。文件较大时先写临时文件（`> /tmp/prompt.txt`），再用 `claude -p "$(cat /tmp/prompt.txt)"` 发送。

## Rule 7: Skill Conflict — Concrete Examples Override Abstract Rules

**When multiple skills are loaded together, a concrete example in one skill will almost always override an abstract constraint in another skill or in the user's prompt.**

This is a fundamental LLM attention pattern, not a skill bug:

- A skill that says *"A-share AI semiconductor → start with memory interconnect"* (concrete) overrides a companion skill that says *"lock to user's market and scope"* (abstract).
- A skill with a full worked example of "US storage chain" biases the model toward storage, even when the user prompt says "A-share AI chips only, no storage."

**Prevention checklist — run before launching multi-skill Claude Code tasks:**

1. **Pre-scan for hard anchors** — check both skills for concrete examples that could compete with the user's intended direction.
2. **Put constraints in the prompt itself** — "仅限A股，禁止美股/存储链" must be in the `claude -p "..."` text, not just in a skill overlay's abstract rules.
3. **Use negative examples** — "研究 AI 算力芯片，不要研究 HBM/存储/内存，这是两个不同的产业链" — a concrete "don't do X" competes with the skill's concrete "do X."
4. **If drift happens twice**, the upstream skill's concrete anchor is too strong — report to user and propose editing the offending lines (with permission).

**If drift persists even with prompt-level constraints, apply the overlay three-part fix (validated 2026-06-23):**

1. **Concrete-to-concrete** — put an equally specific positive example in the overlay (not just a ban) that points to the correct direction.
2. **Explicit supersede** — name the offending skill section by line number and declare it void under this overlay.
3. **Keyword guardrail** — list forbidden keywords (Micron/HBM/NAND) and auto-reject output that contains them.

See `references/skill-drift-pink-elephant.md` for the full case study.

**This is NOT a bug in any specific skill** — it's how LLMs weigh concrete vs abstract instructions. Every multi-skill task carries this risk.

## Bundled Resources

- `references/claude-code-auth-diagnosis.md` — full step-by-step protocol for diagnosing Claude Code CLI auth failures (403, eligibility, OAuth token state)
- `references/cyclical-valuation-pitfalls.md` — valuation methodology pitfalls for cyclical stocks
- `references/l2-independent-review-pattern.md` — template for asking Claude Sonnet to independently review a technical decision
- `references/skill-drift-pink-elephant.md` — real-world case study (2026-06-23): skill drift root cause analysis + three-part fix
- `references/tool-preinstall-checklist.md` — 4-step checklist before installing new tools
- `references/opus-source-debugging.md` — Opus 4.8 源码只读排查模式 (2026-06-27)
- `references/opus-code-review-workflow.md` — Opus 红队审查 + 出代码 diff 四步流程（2026-07-03 实战验证）
