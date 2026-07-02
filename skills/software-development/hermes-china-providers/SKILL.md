---
name: hermes-china-providers
description: >-
  Configure and troubleshoot Hermes model providers. Covers China/international
  endpoint mismatch (Moonshot/Kimi, MiniMax, Z.AI/GLM), provider billing
  verification (OAuth vs API-key cost models), and multi-device safety research
  methodology. Also covers provider selection for auxiliary tasks (vision,
  compression, extraction).
triggers:
  - "kimi key 失效"
  - "moonshot 401"
  - "视觉识别不了"
  - "vision failed 401 moonshot"
  - "key 刚申请但报 Invalid Authentication"
  - Configuring moonshot/kimi/minimax as main or auxiliary provider
  - Switching between China and international providers
---

# Hermes China Providers

## Overview

Model providers with dual endpoints (China platform vs international platform)
require correct provider selection in Hermes. A key issued on one platform will
return **401 "Invalid Authentication"** on the other — even when the key is
fresh and valid.

## Provider → Endpoint Mapping

| Hermes Provider | Endpoint | Platform |
|-----------------|----------|----------|
| `moonshot` | `api.moonshot.ai/v1` | 国际站 |
| `moonshot-cn` | `api.moonshot.cn/v1` | 中国站 |
| `kimi` (alias) | → `moonshot` | 国际站 |
| `kimi-cn` (alias) | → `moonshot-cn` | 中国站 |

Note: `kimi-coding` / `kimi-coding-cn` are the internal Hermes provider IDs
that `moonshot` / `moonshot-cn` resolve to. They use the OpenAI-compatible
endpoint (`/v1`), NOT the Kimi Coding Plan (`api.kimi.com/coding`).

## Environment Variable Mapping

Each provider reads a specific env var — **this is the #1 pitfall**:

| Hermes Provider | Env Var It Reads | Endpoint |
|-----------------|-----------------|----------|
| `moonshot` | `KIMI_API_KEY` | `api.moonshot.ai` (国际站) |
| `moonshot-cn` | `KIMI_CN_API_KEY` | `api.moonshot.cn` (中国站) |

**Common trap**: User has a China-platform key stored in `KIMI_API_KEY`,
switches to `moonshot-cn` provider, but still gets 401 because `moonshot-cn`
reads `KIMI_CN_API_KEY` — which is not set. The key is valid, the endpoint
is correct, but the env var name is wrong.

**Fix**: Either:
- Add `KIMI_CN_API_KEY=<same-key>` to `~/.hermes/.env`, OR
- Use `moonshot` provider with a base_url override:
  ```bash
  hermes config set auxiliary.vision.provider moonshot
  hermes config set auxiliary.vision.base_url https://api.moonshot.cn/v1
  ```

## Vision / Auxiliary Configuration

```bash
# Chinese user — key from platform.moonshot.cn/console
# IMPORTANT: also set KIMI_CN_API_KEY in .env (same key as KIMI_API_KEY)
hermes config set auxiliary.vision.provider moonshot-cn
hermes config set auxiliary.vision.model moonshot-v1-8k-vision-preview

# International user — key from platform.moonshot.ai
hermes config set auxiliary.vision.provider moonshot
hermes config set auxiliary.vision.model moonshot-v1-8k-vision-preview
```

After changing, `/reset` the session to pick up the new config.

## Troubleshooting 401 "Invalid Authentication"

### Quick Test: Run the diagnostic script

```bash
python scripts/check-moonshot-endpoint.py
```

This script (bundled with the skill under `scripts/`) tests your `KIMI_API_KEY`
against both endpoints and prints the recommended fix.

### Manual Test (if script unavailable)

```python
import os, json, urllib.request
from dotenv import load_dotenv
load_dotenv("~/.hermes/.env")

key = os.getenv("KIMI_API_KEY")
for endpoint, label in [
    ("https://api.moonshot.cn/v1/models", "中国站 (moonshot-cn)"),
    ("https://api.moonshot.ai/v1/models", "国际站 (moonshot)"),
]:
    try:
        req = urllib.request.Request(endpoint, headers={"Authorization": f"Bearer {key}"})
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        print(f"✅ {label}: OK")
    except urllib.error.HTTPError as e:
        print(f"❌ {label}: HTTP {e.code} - {e.read().decode()[:200]}")
```

### Diagnostic Flow

1. **Confirm key works directly** — test both endpoints with raw HTTP. If the key works on one but not the other, it's an endpoint mismatch (not an expired key).
2. **Check what Hermes provider is configured** — `hermes config show | grep -A5 vision`
3. **Match provider to working endpoint** — if key works on `api.moonshot.cn`, use `moonshot-cn`. If it works on `api.moonshot.ai`, use `moonshot`.
4. **Apply fix** — `hermes config set auxiliary.vision.provider moonshot-cn` (or `moonshot`)

## Known Platform Issues

| 问题 | 影响 | 详见 |
|:---|:---|:---|
| Moonshot 端点不匹配 | 国际站 key 用在中国站 provider 会 401 | 见上方 Troubleshooting |
| WeChat iLink 限流 | 多段消息触发 429，导致部分消息丢失 | [`references/ilink-rate-limiting.md`](references/ilink-rate-limiting.md) |

## Provider Billing & Safety Research

When evaluating a new provider for Hermes (especially OAuth-based providers like
`openai-codex`), two questions always come up: (1) does this cost extra? and
(2) will multi-device usage get my account banned?

### Billing Verification Technique

The single most reliable way to determine billing model: **check the provider's
`base_url` in Hermes source code** (`plugins/model-providers/<name>/__init__.py`).

| base_url pattern | Billing model | Example |
|:---|:---|:---|
| `chatgpt.com/backend-api/*` | → Subscription quota (ChatGPT Plus/Pro) | `openai-codex` |
| `api.openai.com` | → Separate API billing (pay-as-you-go) | `openai`, `openai-api` |
| `api.anthropic.com` | → Separate API billing (pay-as-you-go) | `anthropic` (even with OAuth token) |
| `api.moonshot.*` | → Separate API billing | `moonshot`, `moonshot-cn` |

The billing model depends on **where the request goes**, not just what
authentication method is used. A Claude Code OAuth token sent to
`api.anthropic.com` still hits the API billing path — unlike `openai-codex`
which routes through `chatgpt.com/backend-api/codex` and uses subscription quota.

### Findings by Provider

**OpenAI Codex** (`openai-codex`): Uses ChatGPT plan quota. Official docs: "Codex
is included across Free, Go, Plus, Pro, Business, Edu, and Enterprise plans."
Zero ban reports found in extensive web search for multi-device usage.
[`references/openai-codex-billing-and-safety.md`](references/openai-codex-billing-and-safety.md)

**Anthropic API** (`anthropic`): Separate API billing, NOT included in Claude Pro.
Official help center (article 7996885) explicitly categorizes "Anthropic API" as
a commercial product separate from consumer plans (Free/Pro/Max). Even
`CLAUDE_CODE_OAUTH_TOKEN` routes through `api.anthropic.com` → API billing.
[`references/anthropic-api-billing.md`](references/anthropic-api-billing.md)

**Qwen**: Two options — DashScope API key (`alibaba` provider, pay-as-you-go) or
Qwen OAuth (`qwen-oauth` provider). 

⚠️ **Qwen OAuth CLI pitfall (2026-06-27)**: `hermes auth add qwen-oauth` requires
the Qwen CLI to be installed AND authenticated (`qwen auth qwen-oauth`). However,
**Qwen Code CLI v0.19.2+ has removed the `qwen auth` command**. This means
`hermes auth add qwen-oauth` fails with "Qwen CLI credentials not found" on
**Qwen**: Two options — DashScope API key (`custom` provider, pay-as-you-go via
workspace OpenAI-compatible endpoint) or Qwen OAuth (`qwen-oauth` provider).
⚠️ Qwen OAuth is **currently dead** — Qwen Code CLI v0.19.2 removed the `qwen auth`
command, breaking `hermes auth add qwen-oauth`. Use the DashScope API key path instead.

⚠️ **Alibaba Bailian DashScope pitfall** (root cause: Opus 4.8 source analysis):
Keys starting with `sk-ws-` (workspace keys from dashscope.console.aliyun.com).
The Anthropic-compatible endpoint (`dashscope.aliyuncs.com/apps/anthropic`,
`api_mode: anthropic_messages`) **does NOT work** — Hermes v0.17.0's
`agent/anthropic_adapter.py:531` sends `x-api-key` for non-whitelisted endpoints,
but Bailian requires `Authorization: *** → 401. Fix: use the OpenAI-compatible
workspace endpoint (`api_mode: chat_completions`) instead.

## MoA (Mixture of Agents) with Chinese Models

Hermes v0.17.0+ supports MoA — multiple reference models analyze in parallel,
then an aggregator synthesizes the answer. Best used **one-shot** via
`/moa "question"` rather than continuously, to avoid extra cost on every turn.

### All-Chinese Model Lineup (no foreign API payments)

| Role | Model | Provider | Why |
|:---|:---|:---|:---|
| Reference 1 | Qwen3.7 Max | `qwen-oauth` or `alibaba` | Structured Chinese analysis, different training from DeepSeek |
| Reference 2 | Kimi (Moonshot) | `kimi-coding-cn` | Long-context reasoning, Moonshot/月之暗面 — independent training |
| Aggregator | DeepSeek V4 Pro | `deepseek` | Best CN model for tool calling + reasoning; already the main model |

Three independent Chinese AI companies (深度求索, 阿里, 月之暗面) with different
training data and architectures → genuine perspective diversity.

### Key MoA Design Facts

- Reference models only see the **latest user message** + a short analysis prompt
- They do NOT see conversation history → prompt quality is critical
- Aggregator has full context and decides when to call tools
- Per-turn cost: reference models ~1-2% each, aggregator >95%
- Use `/moa "self-contained question"` — summarize context in the prompt if
  coming from a long conversation

Full configuration guide:
[`references/moa-chinese-models.md`](references/moa-chinese-models.md)

Claude Code Opus 调试方法（max-turns 问题）:
[`references/claude-code-opus-debugging.md`](references/claude-code-opus-debugging.md)

## ⚠️ Custom Provider Auth Pitfall (2026-06-27)

When using `providers.<name>.api_mode: anthropic_messages` with a `custom`
provider in MoA, the auth header may not be forwarded correctly. Testing with
flat HTTP confirms keys are valid (200 with `x-api-key`), but `custom:qwen-bailian`
got 401 inside MoA. **Root cause:** Hermes's `custom` provider plugin does not
always translate `api_mode: anthropic_messages` into `x-api-key` header on every
code path (the reference-model dispatch path may use Bearer, which the Bailian
Anthropic endpoint rejects).

**Workaround:** Use `qwen-oauth` provider (`hermes auth add qwen-oauth`) for MoA
reference models. The OAuth path is more battle-tested and free — no API key
needed. Fall back to `custom:<name>:<model>` only when OAuth is unavailable.

```yaml
# ✅ Prefer this in MoA presets
reference_models:
  - provider: qwen-oauth
    model: qwen3.7-max
```

## Chinese LLM API Pricing

For current pricing comparison of major Chinese LLM providers (DeepSeek, Kimi, GLM, Qwen), see:
[`references/chinese-llm-pricing.md`](references/chinese-llm-pricing.md)

Last updated 2026-06-29. Includes scraping methodology (Chrome CDP for JS-rendered pages), DeepSeek peak/off-peak pricing (July 2026), and per-provider accessibility notes.

## delegate_task Provider Limitation (2026-07-02)

`delegate_task` **does NOT support per-call provider specification**. Sub-agents
always inherit the parent model. The `delegation.provider` / `delegation.model`
config keys set a **global** override for ALL sub-agents — there is no way to
say "this sub-agent use qwen, that one use deepseek" within the same session.

### Workaround: Direct API Calls via execute_code

When you need a specific model for a sub-task (e.g., L1 review must use
qwen-bailian but the main agent is DeepSeek), skip `delegate_task` entirely.
Instead, write a Python script that calls the provider's `/chat/completions`
endpoint directly via `urllib.request`, and invoke it via `execute_code` or
`terminal`. The script reads credentials from `config.yaml` at runtime.

Example: `scripts/qwen_review.py` reads qwen-bailian's `api_key` and `base_url`
from config.yaml, POSTs to `/chat/completions` with `model: qwen3.7-max`.

### Why Not Set delegation.provider Globally?

Because that would force ALL sub-agents (code-writing, research, data-fetching)
to use the same provider, losing DeepSeek's strengths for the main workflow.

## Related Skills

- `china-dev-proxy-setup` — proxy configuration for dual-network environments
- `hermes-agent` — general Hermes configuration (protected/bundled)
