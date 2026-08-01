# Subscription CLI Integration: Claude Code + Codex in Hermes

> 2026-07-31. Covers: using Claude Pro/Max and ChatGPT Plus/Pro subscription quotas
> through official CLI tools within Hermes Agent. Architecture decisions, OAuth behavior,
> sanctioned-path rationale, and model allocation framework.

## Background

User has two $20/mo subscriptions:
- **Claude Pro** ($20): includes Claude Code, already used for Opus L2 review
- **ChatGPT Plus** ($20): includes Codex, completely idle

Both quotas are underutilized. The goal is to integrate them into the 5-step workflow
without compromising architecture or violating ToS.

## Sanctioned Path: Official CLI > Provider Plugin

| Path | Vendor approval | OAuth behavior | Risk |
|---|---|---|---|
| `claude -p "prompt"` CLI | ✅ Official sanctioned | Rolling refresh (never expires if active) | None |
| `codex exec "prompt"` CLI | ✅ Official sanctioned | Fixed refresh (10-30 days then manual re-login) | Low — just re-auth |
| `openai-codex` provider (Hermes plugin) | ⚠️ Gray zone | Refresh may fail, known bugs #5883 #5736 | Medium — bugs + ToS gray |
| Direct API key | ✅ Official sanctioned | Never expires | None — but costs per token |

**Rule**: Always prefer the official CLI over a third-party OAuth plugin. The CLI is
the exact tool the vendor built and supports — same as a human typing in their terminal.

### Anthropic ToS (Feb 2026)

"OAuth tokens obtained through Free, Pro, or Max accounts are intended exclusively for
Claude Code and claude.ai. Using them in any other product, tool, or service constitutes
a violation." — Anthropic Consumer Terms of Service

Using `claude` CLI directly (as we do for Opus review) = compliant. Extracting the OAuth
token and injecting it into a third-party framework = violation.

### OpenAI ToS (implied)

No equivalent explicit clause found, but the same principle applies: `codex exec` via
the official CLI is the intended usage. Third-party OAuth plugins are gray.

## OAuth Behavior: Claude vs Codex

This is the most important operational difference.

| | Claude Code OAuth | Codex OAuth |
|---|---|---|
| Access token lifetime | ~1 hour | ~1 hour |
| Refresh token lifetime | **Rolling** (each refresh issues new refresh token) | **Fixed** (10-30 days, then expires) |
| Re-login required? | **Never** (as long as active) | **Every 10-30 days** |
| Auto-refresh | ✅ Silent, CLI handles it | ✅ Silent for access token; fails when refresh token expires |
| Failure mode | Only if Anthropic revokes server-side | Refresh token hard-expires → 401 → manual re-login |

**Why Claude never needs re-login**: Anthropic's OAuth implementation issues a NEW refresh
token on every access token refresh. This creates a rolling chain that never breaks as
long as the user is active. The only triggers for re-login are: explicit `claude logout`,
server-side revocation, or manual deletion of the credential store.

**Why Codex needs periodic re-login**: OpenAI's refresh tokens appear to be one-time or
fixed-expiry — they are NOT refreshed during the access token refresh cycle. After 10-30
days, the refresh token expires and the entire auth chain breaks. OpenClaw community has
reported `"Refresh token has already been used."` errors.

### Mitigation for Codex OAuth

1. **Health-check probe**: periodic lightweight `codex exec "ping" --json` to detect 401 early
2. **Telegram alert**: Hermes pushes "Codex needs re-login" to user when auth fails
3. **Don't chase zero-maintenance**: accept that re-login is inevitable; optimize for fast detection

## Codex CLI Usage Pattern

```bash
# Install
npm install -g @openai/codex

# Non-interactive invocation (parallel to Claude Code CLI pattern)
timeout 900 codex exec "your prompt here" --json < /dev/null

# In Hermes terminal() calls:
terminal(command="timeout 900 codex exec \"write a Python script that...\" --json < /dev/null",
         timeout=900, background=True, notify_on_complete=True)
```

- `codex exec` is the non-interactive mode, designed for scripts/CI
- `--json` outputs structured JSON instead of TUI formatting
- `< /dev/null` prevents stdin hang (same pattern as `claude -p`)
- Model selection: `codex exec -m gpt-5.4 "prompt"` or `-m gpt-5.4-mini` for lighter tasks

### Codex Capability Profile

Codex is a **coding-specialized model** — RLHF'd for code generation, debugging, and refactoring.
It is NOT a general-purpose reasoning model.

| Task type | Codex fit | Notes |
|---|---|---|
| Write/fix code | ✅ Strong | Primary strength |
| Code review | ✅ Good | Plays to coding specialization |
| General analysis | ❓ Weak | May miss nuance compared to general models |
| Investment research | ❌ Poor | Not trained for financial reasoning |
| Translation / simple Q&A | ✅ OK | But wasteful for such light tasks |

## Architecture Principle: API Tokens vs Subscription CLIs

| | API Token (DeepSeek, Qwen, Kimi) | Subscription CLI (Claude Code, Codex) |
|---|---|---|
| Billing unit | Per token (smooth, predictable) | Per message (hard cap per 5h window) |
| Failure mode | Gradual cost increase | Sudden quota wall — agent stops mid-task |
| Agent loop fit | ✅ No artificial ceiling | ❌ 5-25 turns drains quota |
| OAuth maintenance | None (API key never expires) | Varies (Claude=0, Codex=monthly) |
| Observability | Token counts, clear cost attribution | Message counts, opaque quota |

**Core rule**: Never put a message-count-billed subscription model in any role that
triggers on every turn (primary agent, fallback, delegation). They belong in
**low-frequency, high-value, human-triggered** roles.

**Human is the decision gate**: The user judges task complexity and decides whether to
invoke a subscription CLI. Small models (e.g. Flash) lack metacognition to self-assess
their limits — do NOT rely on the model to decide "I can't handle this."

## Final Model Allocation (2026-07-31)

| Role | Model | Billing | Frequency |
|---|---|---|---|
| Primary agent | **DeepSeek V4 Flash** | API token (1元/2元) | Every turn |
| Manual upgrade | DeepSeek V4 Pro | API token (3元/6元) | User-triggered `/model` |
| Fallback | Kimi K3 | API token | Rare (DeepSeek outage) |
| L1 review (general) | Qwen 3.7 Max | API token | Per delivery |
| L1 review (code) | Codex CLI | Subscription | Per code delivery |
| L2 review | Claude Opus | Subscription | Per delivery |
| Delegation (code) | Codex CLI | Subscription | User-triggered |
| Delegation (general) | Qwen 3.7 Max | API token | As needed |

Flash handles ~80% of daily tasks (chat, search, simple analysis). Pro is for complex
analysis where the human explicitly decides Flash isn't enough. Subscription CLIs serve
the review and code-gen tiers — low frequency, high value, zero marginal cost.
