# Anthropic API Billing — Separate from Claude Pro

## Key Finding
Anthropic API (console.anthropic.com) billing is COMPLETELY SEPARATE from
Claude Pro ($20/month) subscription. They are different products with different
billing systems.

## Official Evidence

### Anthropic Help Center (article 7996885)
> "This article is about our **commercial products** such as Claude for Work
> and the **Anthropic API**. For our **consumer products** such as Claude Free,
> Pro, Max and when accounts from those plans use **Claude Code**, see…"

Anthropic explicitly categorizes:
- **Commercial**: Claude for Work + Anthropic API → separate billing
- **Consumer**: Free, Pro, Max + Claude Code → subscription quota

### Pricing Page (anthropic.com/pricing)
> "Dedicated API credits and educational features for student learning"
> "Standard token rates apply."

API credits listed as a separate product from subscription plans.

## Source Code Evidence

```python
# Hermes anthropic provider
base_url="https://api.anthropic.com"    # ← Standard API endpoint
env_vars=("ANTHROPIC_API_KEY", "ANTHROPIC_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN")
```

Even with `CLAUDE_CODE_OAUTH_TOKEN`, requests go to `api.anthropic.com`
(API billing endpoint), NOT a subscription backend.

Contrast with OpenAI Codex:
```python
# Hermes openai-codex provider  
base_url="https://chatgpt.com/backend-api/codex"  # ← Subscription backend
```

## Pricing (2026-06)
Claude Sonnet 4 via API:
- Input: $3/M tokens
- Output: $15/M tokens
- MoA aggregator use: ~$3-10/month for moderate usage

## What IS Included in Claude Pro
Claude Code CLI (`claude` command) is included in Pro/Max subscription.
When you run `claude auth login` and use the CLI directly, it uses
subscription quota. But Hermes's `anthropic` provider does NOT use
the Claude Code backend — it goes through the standard API.

## Comparison: OpenAI vs Anthropic

| | OpenAI | Anthropic |
|:---|:---|:---|
| Consumer product | ChatGPT (Free/Plus/Pro) | Claude (Free/Pro/Max) |
| Coding tool in subscription | Codex | Claude Code CLI |
| Developer API platform | platform.openai.com | console.anthropic.com |
| API billing | Separate pay-as-you-go | Separate pay-as-you-go |
| Hermes OAuth uses subscription? | ✅ openai-codex → chatgpt.com | ❌ anthropic → api.anthropic.com |

## Research Date
2026-06-27 — verified against live documentation.
