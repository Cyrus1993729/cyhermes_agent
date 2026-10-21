# OpenCode Go 全模型额度表（2026-10-20 fresh curl 核实）

> 数据源：`https://opencode.ai/docs/go`（实际跳转 `/v2/docs/console/go/`），
> 页面 52,856 字节，urllib 直取原始 HTML，未用 web_extract（有缓存旧版坑）。
> 核实方式：本文件由 `scripts/fetch_opencode_go_quota.py` 解析 `<table>` 自动生成，非手抄。

## 套餐结构（2026-10-20）

| 套餐 | 价格 | 说明 |
|---|---:|---|
| **Go** | **$10/月** | 低成本接入下列模型 |
| **Go Plus** | **$40/月** | 更高的用量上限 |

⚠️ 此前记录的「Flash 月额度 $15 → $30 → $60」**全部过时**。当前 Go 档 = **$80**，Go Plus 档 = **$160**。

## 全模型单价 + 月额度（USD / 1M tokens）

| 模型 | 输入 | 输出 | 缓存读 | 缓存写 | Go 月额度 | Plus 月额度 | 训练 | 留存 |
|---|---:|---:|---:|---:|---:|---:|:--|:--|
| GLM-5.3-Flash | $0.15 | $0.50 | $0.03 | - | $60 | $180 | Not used | 0 days |
| GLM-5.3 | $1.40 | $4.40 | $0.26 | - | $15 | $120 | Not used | 0 days |
| GLM-5.2 | $1.40 | $4.40 | $0.26 | - | $60 | $180 | Not used | 0 days |
| Kimi K3 | $3.00 | $15.00 | $0.30 | - | $15 | $60 | Not used | 0 days |
| Kimi K2.7 Code | $0.95 | $4.00 | $0.19 | - | $60 | $180 | Not used | 0 days |
| LongCat-2.0 | $0.30 | $1.20 | $0.006 | - | $60 | $240 | Not used | 0 days |
| LongCat 2.5 Preview Free | Free | Free | Free | - | Unlimited limited time | Unlimited limited time | Not used | 0 days |
| Step 5 Preview | $1.00 | $2.70 | $0.10 | - | $15 $60 4x · Limited time | $60 $240 4x · Limited time | Not used | 0 days |
| Beam Free | Free | Free | Free | - | Unlimited limited time | Unlimited limited time | Not used | 30 days |
| MiMo-V2.6-Flash | $0.14 | $0.28 | $0.0028 | - | $60 | $120 | Not used | 0 days |
| MiMo-V2.6-Pro | $0.435 | $0.87 | $0.003625 | - | $15 | $60 | Not used | 0 days |
| MiMo-V2.5 | $0.14 | $0.28 | $0.0028 | - | $60 | $120 | Not used | 0 days |
| MiMo-V2.5-Pro | $0.435 | $0.87 | $0.003625 | - | $15 | $60 | Not used | 0 days |
| MiniMax M3.1 Flash Free | Free | Free | Free | - | Unlimited limited time | Unlimited limited time | Not used | 0 days |
| MiniMax M3 | $0.30 | $1.20 | $0.06 | - | $60 | $180 | Not used | 0 days |
| Muse Spark 1.3 Contributor | $0.10 | $0.20 | $0.002 | - | $60 | $120 | Yes | Not ZDR |
| Muse Spark 1.2 Contributor | $0.10 | $0.20 | $0.002 | - | $60 | $120 | Yes | Not ZDR |
| Qwen3.8 Max | $2.00 | $6.00 | $0.25 | $2.50 | $15 | $60 | Not used | 0 days |
| Qwen3.8 Flash | $0.15 | $0.47 | $0.016 | $0.20 | $30 | $90 | Not used | 0 days |
| Qwen3.7 Plus (≤ 256K tokens) | $0.40 | $1.60 | $0.04 | $0.50 | $60 | $180 |  |  |
| Qwen3.7 Plus (> 256K tokens) | $1.20 | $4.80 | $0.12 | $1.50 | $60 | $180 |  |  |
| DeepSeek V4.1 Flash (Off-Peak) | $0.15 | $0.60 | $0.003 | - | $80 | $160 |  |  |
| DeepSeek V4.1 Flash (Peak) | $0.30 | $1.20 | $0.006 | - | $80 | $160 |  |  |
| DeepSeek V4 Pro (Off-Peak) | $0.66 | $1.98 | $0.022 | - | $15 | $60 |  |  |
| DeepSeek V4 Pro (Peak) | $1.32 | $3.96 | $0.044 | - | $15 | $60 |  |  |
| Hy4 preview | $0.834 | $2.501 | $0.042 | - | $30 | $120 | Not used | 0 days |
| Hy3 | $0.14 | $0.58 | $0.035 | - | $60 | $240 | Not used | 0 days |
| Grok 4.7 (≤ 200K tokens) | $2.00 | $6.00 | $0.50 | - | $15 | $60 |  |  |
| Grok 4.7 (> 200K tokens) | $4.00 | $12.00 | $1.00 | - | $15 | $60 |  |  |
| GPT 6 Luna (≤ 272K tokens) | $0.10 | $0.50 | $0.01 | $0.125 | $15 | $60 |  |  |
| GPT 6 Luna (> 272K tokens) | $0.20 | $0.75 | $0.02 | $0.25 | $15 | $60 |  |  |
| GPT 5.6 Luna (≤ 272K tokens) | $0.20 | $1.20 | $0.02 | $0.25 | $15 | $60 |  |  |
| GPT 5.6 Luna (> 272K tokens) | $0.40 | $1.80 | $0.04 | $0.50 | $15 | $60 |  |  |
| Claude Haiku 5.5 (≤ 100K tokens) | $0.10 | $0.50 | $0.01 | $0.125 | $15 | $60 |  |  |
| Claude Haiku 5.5 (> 100K tokens) | $0.50 | $2.50 | $0.05 | $0.625 | $15 | $60 |  |  |
| Gemini 4 Argon Contributor | $4.00 | $20.00 | $0.20 | - | $30 $60 2x · Limited time | $120 $240 2x · Limited time | Yes | Not ZDR |

## 估算请求数（Go 档 / Go Plus 档）

> 按 OpenCode 典型用量模式估算（DeepSeek V4.1 Flash 假设 410 input / 71,300 cached / 310 output tokens 每次请求）

| 模型 | 5h | 周 | 月 | 5h(Plus) | 周(Plus) | 月(Plus) |
|---|---:|---:|---:|---:|---:|---:|
| GLM-5.3-Flash | 6,320 | 15,790 | 31,580 | 18,960 | 47,370 | 94,740 |
| GLM-5.3 | 220 | 540 | 1,080 | 1,760 | 4,320 | 8,640 |
| GLM-5.2 | 880 | 2,150 | 4,300 | 2,640 | 6,450 | 12,900 |
| Kimi K3 | 110 | 250 | 490 | 440 | 1,000 | 1,960 |
| Kimi K2.7 Code | 1,350 | 3,380 | 6,750 | 4,050 | 10,140 | 20,250 |
| LongCat-2.0 | 11,400 | 28,600 | 57,200 | 45,600 | 114,400 | 228,800 |
| LongCat 2.5 Preview Free | Unlimited | Unlimited | Unlimited | Unlimited | Unlimited | Unlimited |
| Step 5 Preview 4x · Limited time | 430 1,720 | 1,070 4,280 | 2,130 8,520 | 1,720 6,880 | 4,280 17,120 | 8,520 34,080 |
| Beam Free | Unlimited | Unlimited | Unlimited | Unlimited | Unlimited | Unlimited |
| MiMo-V2.6-Flash | 30,100 | 75,200 | 150,400 | 60,200 | 150,400 | 300,800 |
| MiMo-V2.6-Pro | 3,250 | 8,150 | 16,300 | 13,000 | 32,600 | 65,200 |
| MiMo-V2.5 | 30,100 | 75,200 | 150,400 | 60,200 | 150,400 | 300,800 |
| MiMo-V2.5-Pro | 3,250 | 8,150 | 16,300 | 13,000 | 32,600 | 65,200 |
| MiniMax M3.1 Flash Free | Unlimited | Unlimited | Unlimited | Unlimited | Unlimited | Unlimited |
| MiniMax M3 | 3,200 | 8,000 | 16,000 | 9,600 | 24,000 | 48,000 |
| Muse Spark 1.3 Contributor | 45,300 | 113,300 | 226,600 | 90,600 | 226,600 | 453,200 |
| Muse Spark 1.2 Contributor | 45,300 | 113,300 | 226,600 | 90,600 | 226,600 | 453,200 |
| Qwen3.8 Max | 160 | 400 | 810 | 640 | 1,600 | 3,240 |
| Qwen3.8 Flash | 5,400 | 13,500 | 27,000 | 16,200 | 40,500 | 81,000 |
| Qwen3.7 Plus | 4,300 | 10,800 | 21,600 | 12,900 | 32,400 | 64,800 |
| DeepSeek V4.1 Flash | 34,670 | 86,670 | 173,330 | 69,330 | 173,330 | 346,670 |
| DeepSeek V4 Pro | 1,050 | 2,600 | 5,200 | 4,200 | 10,400 | 20,800 |
| Hy4 preview | 1,350 | 3,380 | 6,770 | 5,400 | 13,520 | 27,080 |
| Hy3 | 4,300 | 10,750 | 21,500 | 17,200 | 43,000 | 86,000 |
| Grok 4.7 | 169 | 423 | 845 | 676 | 1,692 | 3,380 |
| GPT 6 Luna | 4,230 | 10,560 | 21,130 | 16,920 | 42,240 | 84,520 |
| GPT 5.6 Luna | 2,050 | 5,100 | 10,250 | 8,200 | 20,400 | 41,000 |
| Claude Haiku 5.5 | 3,850 | 9,620 | 19,230 | 15,380 | 38,460 | 76,920 |
| Gemini 4 Argon Contributor 2x · Limited time | 220 440 | 540 1,080 | 1,060 2,120 | 880 1,760 | 2,160 4,320 | 4,240 8,480 |

## 模型 ID（走 `https://opencode.ai/inference/go/...`）

| 模型 | Model ID | AI SDK |
|---|---|---|
| Grok 4.7 | `grok-4.7` | @ai-sdk/openai |
| GPT 6 Luna | `gpt-6-luna` | @ai-sdk/openai |
| GPT 5.6 Luna | `gpt-5.6-luna` | @ai-sdk/openai |
| Claude Haiku 5.5 | `claude-haiku-5-5` | @ai-sdk/anthropic |
| Gemini 4 Argon Contributor | `gemini-4-argon-contributor` | @ai-sdk/google |
| GLM-5.3-Flash | `glm-5.3-flash` | @ai-sdk/openai-compatible |
| GLM-5.3 | `glm-5.3` | @ai-sdk/openai-compatible |
| GLM-5.2 | `glm-5.2` | @ai-sdk/openai-compatible |
| Kimi K3 | `kimi-k3` | @ai-sdk/openai-compatible |
| Kimi K2.7 Code | `kimi-k2.7-code` | @ai-sdk/openai-compatible |
| LongCat-2.0 | `longcat-2.0` | @ai-sdk/openai-compatible |
| DeepSeek V4.1 Flash | `deepseek-v4.1-flash` | @ai-sdk/openai-compatible |
| DeepSeek V4 Pro | `deepseek-v4-pro` | @ai-sdk/openai-compatible |
| MiMo-V2.6-Flash | `mimo-v2.6-flash` | @ai-sdk/openai-compatible |
| MiMo-V2.6-Pro | `mimo-v2.6-pro` | @ai-sdk/openai-compatible |
| MiMo-V2.5 | `mimo-v2.5` | @ai-sdk/openai-compatible |
| MiMo-V2.5-Pro | `mimo-v2.5-pro` | @ai-sdk/openai-compatible |
| MiniMax M3 | `minimax-m3` | @ai-sdk/anthropic |
| Muse Spark 1.3 Contributor | `muse-spark-1.3-contributor` | @ai-sdk/openai |
| Muse Spark 1.2 Contributor | `muse-spark-1.2-contributor` | @ai-sdk/openai |
| Qwen3.8 Max | `qwen3.8-max` | @ai-sdk/anthropic |
| Qwen3.8 Flash | `qwen3.8-flash` | @ai-sdk/anthropic |
| Qwen3.7 Plus | `qwen3.7-plus` | @ai-sdk/anthropic |
| Hy4 preview | `hy4-preview` | @ai-sdk/openai-compatible |
| Hy3 | `hy3` | @ai-sdk/openai-compatible |
| MiniMax M3.1 Flash Free | `minimax-m3.1-flash-free` | @ai-sdk/openai-compatible |
| LongCat 2.5 Preview Free | `longcat-2.5-preview-free` | @ai-sdk/openai-compatible |
| Step 5 Preview | `step-5-preview` | @ai-sdk/openai-compatible |
| Beam Free | `beam-free` | @ai-sdk/openai-compatible |

## 与我们相关的关键数字

- **DeepSeek V4.1 Flash**：Off-Peak `$0.15 / $0.60 / cache $0.003`、Peak `$0.30 / $1.20 / cache $0.006`，**月额度 $80**
- **Peak 时段**：`01:00-04:00` 与 `06:00-10:00` UTC，周一至周五（= 北京 09:00-12:00 / 14:00-18:00）
- **DeepSeek V4 Pro**：月额度仅 **$15**，占用是 Flash 的 5.3 倍
- **Kimi K3**：`$3.00 / $15.00`，月额度 **$15** —— 最贵一档，不适合日常
- **GPT 6 Luna**：`$0.10 / $0.50 / cache $0.01`，月额度 $15
- **Claude Haiku 5.5**：`$0.10 / $0.50`，月额度 $15
- **GLM-5.3-Flash**：`$0.15 / $0.50 / cache $0.03`，月额度 **$60**

## 与旧记录的差异（2026-10-20）

| 项 | 旧记录 | 现值 | 影响 |
|---|---|---|---|
| DeepSeek V4.1 Flash 月额度 | $30 / $60 | **$80** | 占用率估算从 60-127% 降到 ~30-50% |
| 套餐档 | 单一 $10 | $10 / **$40 Plus** | 新增高价档 |
| 新上架模型 | — | GLM-5.3/5.3-Flash、Kimi K2.7 Code、GPT 6 Luna、GPT 5.6 Luna、Claude Haiku 5.5、Gemini 4 Argon、Qwen3.8 Max/Flash、Qwen3.7 Plus、MiMo-V2.6 系列、Step 5 Preview | 选型候选变多 |
| Qwen3.7 Max | 在列 | **docs 表已不列，但 `/models` 仍在服务**（37 个在线模型含 qwen3.7-max） | fallback 未失效 |

## 我们自己的实测占用（2026-10-20 重算）

数据源：`state.db` 的 `session_model_usage`，`billing_provider='opencode-go'` + `model='deepseek-v4.1-flash'`，近 30 天。

| 项 | 数值 |
|---|---:|
| 调用次数 | 2,287 次 / 69 个活跃日 |
| 非缓存输入 | 13.06M |
| 输出 | 2.70M |
| 缓存读 | 378.99M |
| **缓存命中率** | **96.7%** |

| 口径 | 月成本 | 占 Go $80 档 |
|---|---:|---:|
| 全 Off-Peak | $4.72 | **5.9%** |
| 全 Peak | $9.43 | **11.8%** |
| 活跃日外推（Off-Peak） | $2.05 | 2.6% |
| 活跃日外推（Peak） | $4.10 | 5.1% |

**结论：额度极其宽裕，占用 6-12%，是之前估算（60-127%）的十分之一。**

🔴 **踩过的坑：`input_tokens` 列**不含**缓存部分**。实测 input 13.06M、cache_read 378.99M，
若按 `input - cache` 算非缓存输入会得到**负数**。正确处理：`input_tokens` 本身就是非缓存输入。

⚠️ `estimated_cost_usd` / `actual_cost_usd` 两列**长期为 $0.00**（Hermes 未接 OpenCode 的计费回传），
**不能用它们算占用，必须按上表价格手工重算。**

生成时间：2026-10-20 10:43:38