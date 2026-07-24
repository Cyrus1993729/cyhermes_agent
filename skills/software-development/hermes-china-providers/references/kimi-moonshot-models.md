# Kimi / Moonshot Model Catalog

Retrieved 2026-07-23 via `GET /v1/models` from `api.moonshot.cn/v1`.

## Active Models

### K-Series (Latest — Recommended)

| Model | Context | Vision | Video | Reasoning | Think Effort | Dynamic Tools |
|-------|---------|--------|-------|-----------|-------------|---------------|
| `kimi-k3` | **1,048,576** (1M) | ✅ | ✅ | ✅ | low/high/**max** (default: max) | ✅ |
| `kimi-k2.7-code-highspeed` | 262,144 | ✅ | ✅ | ✅ | — | — |
| `kimi-k2.7-code` | 262,144 | ✅ | ✅ | ✅ | — | — |
| `kimi-k2.6` | 262,144 | ✅ | ✅ | ✅ | — | — |
| `kimi-k2.5` | 262,144 | ✅ | ✅ | ✅ | — | — |

### V1-Series (Classic — Legacy)

| Model | Context | Vision |
|-------|---------|--------|
| `moonshot-v1-auto` | 131,072 | — |
| `moonshot-v1-8k` | 8,192 | — |
| `moonshot-v1-32k` | 32,768 | — |
| `moonshot-v1-128k` | 131,072 | — |
| `moonshot-v1-8k-vision-preview` | 8,192 | ✅ |
| `moonshot-v1-32k-vision-preview` | 32,768 | ✅ |
| `moonshot-v1-128k-vision-preview` | 131,072 | ✅ |

## Model Selection Guide

| Use Case | Recommended Model | Why |
|----------|-------------------|-----|
| Main agent / fallback | `kimi-k3` | 1M context, reasoning control, dynamic tools |
| Delegation (sub-agent) | `kimi-k3` | Same as above |
| Vision tasks | `moonshot-v1-128k-vision-preview` | 128K context with vision |
| Budget / simple code | `kimi-k2.7-code-highspeed` | Fast, cheaper than K3 |
| Budget / simple chat | `moonshot-v1-auto` | Auto-selects context, cheapest option |

## Hermes Provider Mapping

| Hermes Provider ID | Endpoint | Key Env Var |
|--------------------|----------|-------------|
| `kimi-coding` | `api.moonshot.cn/v1` | `KIMI_API_KEY` |
| `kimi-coding-cn` | `api.moonshot.cn/v1` | `KIMI_CN_API_KEY` |

## Discovery Command

To refresh this catalog (models may be added/removed):

```bash
KIMI_KEY=$(grep "^KIMI_API_KEY=" ~/.hermes/.env | sed 's/KIMI_API_KEY=//')
curl --noproxy '*' -s -H "Authorization: Bearer $KIMI_KEY" "https://api.moonshot.cn/v1/models" | python -m json.tool
```
