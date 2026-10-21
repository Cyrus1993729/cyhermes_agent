# MoA Configuration — All-Chinese Model Lineup

> **⚠️ Custom Provider Auth Pitfall (2026-06-27) — Opus 4.8 debugged**: Hermes v0.17.0's
> `agent/anthropic_adapter.py:531` (`_requires_bearer_auth`) only whitelists MiniMax and
> Azure for `Authorization: *** auth. For DashScope's Anthropic endpoint
> (`dashscope.aliyuncs.com/apps/anthropic`), Hermes sends `x-api-key` — but Bailian
> requires `Authorization: *** → **401**. (Was previously misdiagnosed as "Bearer vs x-api-key
> reversed" — actual root cause is opposite: Hermes sends x-api-key when Bailian
> expects Bearer.)
>
> **Primary recommendation: OpenAI-compatible workspace endpoint** (`api_mode: chat_completions`).
> This bypasses the auth header mismatch entirely. Qwen OAuth is dead (CLI v0.19.2
> removed auth command).

## Default Preset (recommended)

| Role | Model | Hermes Provider | Key |
|:---|:---|:---|:---|
| Reference 1 | Qwen3.7 Max | `qwen-bailian` (custom) | API Key（阿里百炼 workspace endpoint） |
| Reference 2 | Kimi K2.7 Code | `kimi-coding-cn` | KIMI_CN_API_KEY |
| Aggregator | DeepSeek V4 Pro | `deepseek` | `DEEPSEEK_API_KEY` |

> ⚠️ **Qwen OAuth 已死**（Qwen Code CLI v0.19.2 删除 auth 命令）。唯一可用路径：`qwen-bailian` custom provider。
> **MoA preset 格式已修正**：用 `provider: qwen-bailian + model: qwen3.7-max`，不是 `provider: custom + model: qwen-bailian:qwen3.7-max`。

Three independent Chinese AI companies (深度求索, 阿里, 月之暗面) ensure genuine
training-data and architecture diversity.

## Configure via CLI

```bash
# Qwen Bailian custom provider (required — OAuth is dead)
hermes config set providers.qwen-bailian.base_url "https://ws-XXXXX.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
hermes config set providers.qwen-bailian.api_mode "chat_completions"
hermes config set providers.qwen-bailian.api_key "sk-ws-YOUR_KEY"

# Verify
hermes moa list
```

### Direct config.yaml Structure (Hermes v0.17.0)

```yaml
moa:
  default_preset: china
  active_preset: ''          # Leave empty for one-shot-only usage
  presets:
    china:
      enabled: true
      reference_models:
        - provider: qwen-oauth
          model: qwen3.7-max
        - provider: kimi-coding-cn
          model: kimi-k2.7-code
      aggregator:
        provider: deepseek
        model: deepseek-v4-pro
      reference_temperature: 0.6
      aggregator_temperature: 0.4
      max_tokens: 4096
  enabled: true
```

### Fallback: Alibaba Bailian DashScope (custom provider — ChatGPT-compatible endpoint)

Use when `qwen-oauth` is unavailable. For `sk-ws-*` keys from
[dashscope.console.aliyun.com](https://dashscope.console.aliyun.com).

**⚠️ DO NOT use the Anthropic endpoint** (`dashscope.aliyuncs.com/apps/anthropic`
with `api_mode: anthropic_messages`). Opus 4.8 traced the root cause: Hermes
`agent/anthropic_adapter.py` line 531 sends `x-api-key` for non-Anthropic endpoints,
but Bailian requires `Authorization: *** header → 401. (Key IS valid — direct HTTP
returns 200 with either header — it's a Hermes-internal header selection bug.)

**✅ Use the OpenAI-compatible workspace endpoint** instead (see above for YAML).
The workspace endpoint can be found at [dashscope.console.aliyun.com](https://dashscope.console.aliyun.com)
→ Workspace → API-KEY 管理 → 查看 endpoint URL.

**Verification** (OpenAI-compatible endpoint):
```python
url = "https://ws-XXXXX.cn-beijing.maas.aliyuncs.com/compatible-mode/v1/chat/completions"
# Authorization: Bearer sk-ws-XXX
# model: qwen3.7-max
# HTTP 200 → OK
```

The workspace endpoint can be found at [dashscope.console.aliyun.com](https://dashscope.console.aliyun.com)
→ Workspace → API-KEY 管理 → 查看 endpoint URL.

## Model IDs Reference

| Display Name | Hermes model ID | Provider | Notes |
|:---|:---|:---|:---|
| DeepSeek V4 Pro | `deepseek-v4-pro` | `deepseek` | Direct API, already configured |
| Qwen3.7 Max | `qwen3.7-max` | `qwen-bailian` (custom) | Bailian OpenAI-compatible workspace endpoint |
| Kimi K2.7 Code | `kimi-k2.7-code` | `kimi-coding-cn` | China endpoint, already configured |

## Qwen: Two Configuration Paths

### Path A: Qwen OAuth (DEAD — CLI v0.19.2 removed auth command)

⚠️ **Qwen Code CLI v0.19.2+**: The `qwen auth` command was **removed**.
`hermes auth add qwen-oauth` requires this command → will fail with
`AuthError: Qwen CLI credentials not found`.

```bash
# This WILL FAIL on Qwen Code CLI >= 0.19.2
hermes auth add qwen-oauth
```

**If the command is ever restored**: browser login with Alibaba/Alipay account.
No API key, no billing. MoA preset: `provider: qwen-oauth, model: qwen3.7-max`

**Until then**: use Path B (DashScope API key).

### Path B: Alibaba Bailian DashScope API Key (Working Fallback)

For `sk-ws-*` keys from [dashscope.console.aliyun.com](https://dashscope.console.aliyun.com):

**⚠️ DO NOT use the Anthropic endpoint.** The key itself works with both `x-api-key` and
`Bearer` headers in raw HTTP, but Hermes's `anthropic_adapter.py:531` sends `x-api-key`
to all non-whitelisted endpoints — Bailian requires `Authorization: Bearer` → 401.

**✅ Use the OpenAI-compatible workspace endpoint** (each workspace gets its own URL):

```bash
hermes config set providers.qwen-bailian.base_url "https://ws-XXXXX.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
hermes config set providers.qwen-bailian.api_mode "chat_completions"
hermes config set providers.qwen-bailian.api_key "sk-ws-YOUR_KEY"
```

In MoA preset:
```yaml
reference_models:
  - provider: qwen-bailian     # ← matches providers.qwen-bailian
    model: qwen3.7-max         # ← bare name, NOT qwen-bailian:qwen3.7-max
```

## Usage Pattern

**One-shot mode** (recommended):
```
/moa "self-contained analysis question here"
```

**Continuous mode** (use sparingly):
```
/moa
```

## Critical: Prompt Quality for Reference Models

Reference models do NOT see conversation history. For best results:

**Good** (self-contained):
```
/moa "OpenLight是一家硅光芯片公司，Serenity推文提到它的生态有6家上市公司：
Advantest、Jabil、Sivers、Marvell、MaxLinear、Tower、天孚通信。
请分析这7家里哪家离产业链瓶颈最近，各自的卡脖子程度如何。"
```

**Bad** (context-dependent):
```
/moa "那你怎么看"
```

## Provider Setup Checklist

- [ ] DeepSeek: `DEEPSEEK_API_KEY` in `.env` (already configured)
- [ ] Kimi: `KIMI_CN_API_KEY` in `.env` (already configured)
- [ ] Qwen: `providers.qwen-bailian` custom provider with OpenAI-compatible workspace endpoint

## Cost Estimate

| Component | Cost per MoA Turn |
|:---|:---|
| Qwen3.7 Max reference (~0.5K in, ~0.3K out) | ~¥0.01 |
| Kimi reference (~0.5K in, ~0.3K out) | ~¥0.01 |
| DeepSeek V4 Pro aggregator | Same as normal chat |
| **MoA overhead** | **~¥0.02 per turn** (~3% of total) |

## Research Date
2026-06-27 — verified against Hermes v0.17.0 with live provider testing.
Custom provider auth header pitfall confirmed. `qwen-oauth` recommended as primary path.
