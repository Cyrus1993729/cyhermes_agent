# OpenAI Codex Provider: Billing & Safety Research

**Date researched:** 2026-06-27
**Trigger:** User evaluating whether to add `openai-codex` provider to Hermes MoA preset, concerned about cost and account-ban risk.

## Core Finding: Codex OAuth uses ChatGPT plan quota, NOT API billing

### Official Documentation

**Source:** OpenAI Help Center — [Codex in ChatGPT](https://help.openai.com/en/articles/11369540-codex-in-chatgpt) (Article #11369540)

Key excerpts:

> "Codex is included across Free, Go, Plus, Pro, Business, Edu, and Enterprise plans. Usage limits and credit options vary by plan."

> "Codex is included in eligible ChatGPT plans, including Free. Usage limits vary by plan."

> "If you are nearing or have reached your Codex limit, check the Codex usage page or the limit banner for the options available on your plan. Some Plus and Pro users can add credits to continue using Codex; other users may need to upgrade or wait for the limit to reset."

### Code-Level Confirmation

Hermes `openai-codex` provider plugin (`plugins/model-providers/openai-codex/__init__.py`):

```python
base_url="https://chatgpt.com/backend-api/codex",
auth_type="oauth_external",
```

API calls go to `chatgpt.com/backend-api/codex` — the ChatGPT backend, NOT `api.openai.com` (the paid API platform). This confirms billing is through the ChatGPT subscription, not separate API credits.

### Billing Summary

| If you use... | Auth method | Calls go to... | Costs |
|:---|:---|:---|:---|
| `openai-codex` (OAuth) | ChatGPT account login | `chatgpt.com/backend-api/codex` | Covered by ChatGPT Plus/Pro plan quota |
| `openai-api` (API Key) | API Key | `api.openai.com` | Per-token billing against prepaid credits |

## Multi-Device Safety Research

### Search Methodology

Extensive web searches conducted on 2026-06-27 across multiple engines and communities:

| Engine | Query Examples | Results |
|:---|:---|:---|
| Bing International | `codex account banned multiple devices different IP` | Zero relevant hits |
| Bing Chinese | `Codex 多设备 封号 两台电脑` | Zero relevant hits |
| DuckDuckGo | `openai codex oauth multiple machines banned` | Zero relevant hits |
| Startpage (proxy) | `codex account suspended multiple devices` | Zero relevant hits |
| Reddit API | `r/OpenAI` + codex banned/suspended queries | Zero relevant hits |
| V2EX/Zhihu (Bing site:) | Codex 封号 reports | Zero relevant hits |

### Conclusion

**No community reports of Codex multi-device bans were found anywhere on the public internet.** This absence is itself a signal — if multi-device usage triggered bans, there would be discussion on Reddit, V2EX, Zhihu, or GitHub (as there is for topics like "ChatGPT virtual credit card bans" or "API key leak abuse").

Codex is designed for multi-client usage (CLI, IDE extension, Web App, desktop) — multi-device is the intended workflow, not a violation.

## Provider Authentication

To add `openai-codex` to Hermes:

```bash
hermes auth add openai-codex
```

This opens a browser for ChatGPT OAuth login. After authorization, the token works from any computer — no per-machine binding. For headless environments, add `--no-browser --manual-paste`.

## Usage Limits

OpenAI does not publish exact rate limits for Codex on Plus/Pro plans. The documented mechanism is:
1. Normal usage draws from plan quota
2. When nearing limit, a banner appears with options
3. Plus/Pro users can purchase additional credits
4. Otherwise, wait for limit reset

No separate API key or billing account is needed.
