---
name: moa-configuration
description: Configure Hermes MoA (Mixture of Agents) — model selection, billing evaluation, provider setup. Use when the user asks about MoA setup, model choice for reference/aggregator, or billing implications.
version: 1.0.0
metadata:
  hermes:
    tags: [moa, billing, model-selection, providers]
---

# MoA 配置与模型选择

## 核心概念

MoA = 多个参考模型并行分析 → 汇总模型综合回答。

| 角色 | 职责 | 需要的能力 |
|:---|:---|:---|
| Reference 模型 | 多角度分析、发现盲区 | 推理深度、领域知识、**不同训练分布** |
| Aggregator 模型 | 综合判断、去伪存真、调工具 | 指令遵循、整合能力、工具调用 |

## CLI 命令

```bash
hermes moa list              # 查看当前预设
hermes moa configure         # 交互式配置
hermes moa delete <name>     # 删除预设
```

会话内：`/moa`（持续模式）、`/moa "问题"`（一次性）。

## 模型计费路径（关键——决定走订阅配额还是API付额）

### 走订阅配额的路径

| Provider | 请求发到哪里 | 扣什么额度 | 认证方式 |
|:---|:---|:---|:---|
| `openai-codex` | `chatgpt.com/backend-api/codex` | ChatGPT Plus/Pro 计划 Codex 额度 | OAuth 登录 |

官方文档（OpenAI Help Center #11369540）：*"Codex is included across Free, Go, Plus, Pro, Business, Edu, and Enterprise plans."*

### 走API单独计费的路径

| Provider | 请求发到哪里 | 扣什么 | 认证方式 |
|:---|:---|:---|:---|
| `anthropic` | `api.anthropic.com` | API 预充值/按量 | API Key 或 OAuth Token |
| `openrouter` | `openrouter.ai/api` | OpenRouter 余额 | API Key |
| `deepseek` | `api.deepseek.com` | DeepSeek API 余额 | API Key |
| `alibaba` (DashScope) | `dashscope.aliyuncs.com` | 阿里云账户 | API Key |

Anthropic 帮助中心文章 7996885 明确将 API 归为 "commercial products"，与消费者产品（Free/Pro/Max + Claude Code）分开。

**注意：** Hermes 的 `anthropic` 提供商支持 `CLAUDE_CODE_OAUTH_TOKEN`，但请求发到 `api.anthropic.com`——即使用了 OAuth token，大概率仍走 API 计费而非 Pro 配额。与 `openai-codex`（专用 ChatGPT 后端）不同。

### Qwen 的路径

| Provider | 路径 | 计费 | 状态 |
|:---|:---|:---|:---|
| `qwen-oauth` | `portal.qwen.ai/v1`（OAuth） | 千问门户配额 | ⚠️ Qwen Code CLI v0.19.2+ 已移除 auth 命令，不可用 |
| `qwen-bailian` (custom) | OpenAI 兼容端点 | 阿里百炼按量 | ✅ 推荐——见下 |
| `openrouter:qwen/*` | OpenRouter | OpenRouter 余额 | ✅ |

**⚠️ Pitfall：阿里百炼 Anthropic 端点不可用**（根因来源：Claude Code Opus 4.8 源码排查）

DashScope `sk-ws-*` key 走 Anthropic 兼容端点 (`dashscope.aliyuncs.com/apps/anthropic`,
`api_mode: anthropic_messages`) 时，Hermes v0.17.0 的 `agent/anthropic_adapter.py:531`
（`_requires_bearer_auth` 函数）只白名单了 MiniMax 和 Azure 走 Bearer 认证。对
`dashscope.aliyuncs.com/apps/anthropic` 则走 `x-api-key`，而百炼要求
`Authorization: Bearer` → **401 Invalid Authentication**。

**正确配置**：使用阿里百炼的 OpenAI 兼容端点（workspace endpoint）：

```yaml
providers:
  qwen-bailian:
    base_url: https://ws-XXXXX.cn-beijing.maas.aliyuncs.com/compatible-mode/v1
    api_mode: chat_completions
    api_key: sk-ws-...
```

**MoA preset 里不能用 `provider: custom` + `model: qwen-bailian:qwen3.7-max`！**
正确格式是 `provider: qwen-bailian` + `model: qwen3.7-max`（两个独立字段，
provider 直接匹配 `providers.<name>` 的 key）。详见下方「配置 YAML 格式」。

## 配置流程

### 1. 确认可用模型和计费路径

对于每个候选模型，确认：
- 走哪个 provider
- 扣哪个配额
- 用户是否有该 provider 的认证

### 2. 交互式配置

```bash
hermes moa configure
```
交互式选择参考模型和汇总模型。

### 3. 编辑 .env 添加 API Keys

```env
DEEPSEEK_API_KEY=***
DASHSCOPE_API_KEY=***      # 阿里百炼
ANTHROPIC_API_KEY=***       # Anthropic Console
OPENROUTER_API_KEY=***      # 可选
```

### 4. 测试

```bash
hermes moa list    # 确认预设
/moa "测试问题"    # 在会话中一次性测试
```

## 模型选择建议

### 参考模型选择原则

1. **训练分布差异越大越好**——DeepSeek + Qwen 比两个 Qwen 好，GPT + DeepSeek 比两个 OpenAI 模型好
2. **不需要最强模型**——参考模型只看问题不看上下文，几百 token 的分析，中等推理能力就够
3. **成本极低**——参考模型每次分析 ≈ ¥0.003-0.01，可以忽略

### 汇总模型选择原则

1. **指令遵循能力第一**——Claude Sonnet > DeepSeek > GPT
2. **工具调用精准度**——汇总模型负责决定要不要查资料、调工具
3. **这是成本大头**——每次回复约 ¥0.3-0.5，占 MoA 总成本的 95%+

## 全国产模型阵容 (2026-06-27)

### 推荐配置（2026-06-27 生效）

| 角色 | 模型 | Provider | 认证 |
|:---|:---|:---|:---|
| 参考 1 | Qwen3.7 Max | `qwen-bailian`（custom provider） | API Key（阿里百炼 workspace endpoint） |
| 参考 2 | Kimi K2.7 Code | `kimi-coding-cn` | KIMI_CN_API_KEY |
| 汇总 | DeepSeek V4 Pro | `deepseek` | DEEPSEEK_API_KEY |

三家独立中国 AI 公司（深度求索、阿里、月之暗面），训练数据和技术路线完全不同，
真正做到了多角度碰撞。详见 `hermes-china-providers` 技能。

> ⚠️ **Qwen OAuth 路径已死**：Qwen Code CLI v0.19.2+ 删除了 `qwen auth` 命令，
> `hermes auth add qwen-oauth` 无法使用。唯一可行路径是 `qwen-bailian` custom provider。

### ⚠️ Qwen Custom Provider 配置格式（2026-06-27 已验证）

**`resolve_provider_client` 查找机制**（`hermes_cli/models.py` 行 ~4039）：
MoA reference model 的 `provider` 字段直接匹配 `config.yaml → providers.<name>`。
`model` 字段是裸模型名，不是 `provider-name:model` 前缀格式。

**正确（已验证通过）：**
```yaml
reference_models:
  - provider: qwen-bailian    # ← 直接匹配 providers.qwen-bailian
    model: qwen3.7-max        # ← 裸模型名，无前缀
```

**错误（会静默失败 / 401）：**
```yaml
  - provider: custom
    model: qwen-bailian:qwen3.7-max   # ← 冒号前缀被忽略！
```

### ⚠️ Qwen OAuth 已死

Qwen Code CLI v0.19.2+ 已删除 `qwen auth` / `qwen login` 命令。
`hermes auth add qwen-oauth` 会报 `AuthError: Qwen CLI credentials not found. Run 'qwen auth qwen-oauth' first.` — 但 `qwen auth` 命令不存在。**OAuth 路径不可用。**

### 推荐组合

| 场景 | 参考1 | 参考2 | 汇总 |
|:---|:---|:---|:---|
| 全国产 | Qwen3.7 Max (qwen-bailian) | Kimi K2.7 Code | DeepSeek V4 Pro |
| 日常分析 | DeepSeek V4 Pro | Qwen3.7 Max | Claude Sonnet 4 |
| 预算敏感 | DeepSeek V4 Pro | Qwen3.7 Plus | DeepSeek V4 Pro（汇总同参考） |
| 极致质量 | GPT-5.5 (Codex OAuth) | DeepSeek V4 Pro | Claude Opus 4.8 |

## 成本估算（单次 MoA 调用）

| 环节 | 消耗 | 占比 |
|:---|:---|:---|
| 两个参考模型分析 | ~1K tokens 总计 | ~3% |
| 汇总模型处理+回复 | ~1.5K tokens | ~97% |

总成本 ≈ 正常对话的 1.15-1.2x，不是 3x。参考模型只看问题不看历史，缓存完全命中。

## DeepSeek V4 Pro 推理强度调参（2026-06-27）

DeepSeek V4 Pro 支持 `reasoning_effort` 参数（top-level API 参数），四个档位：

| 强度 | 说明 | 何时用 |
|:---|:---|:---|
| `low` | 快速、少思考 | 简单问答 |
| `medium` | 中等 | 日常对话 |
| `high` | **服务器默认（当前）** | 一般分析 |
| `max` | 最强推理，最慢最贵 | 深度分析、复杂决策 |

设置方式：
```bash
hermes config set model.reasoning_effort "max"   # 拉满
hermes config set model.reasoning_effort ""       # 回默认 high
```

**注意**：
- 不上调到 `max` 时，DeepSeek 走服务器默认 `high`
- `max` 会增加推理 token 消耗和响应时间
- 只在需要最强推理深度时临时开启，日常用 `high` 即可
- Qwen/Kimi 等其他国产模型**不支持**此参数——仅 DeepSeek V4+ 家族支持

## MoA vs 单一顶级模型：使用场景指南（2026-06-27 实践验证）

同一道深度分析题（2026下半年黄金走势），分别用 `/moa`（DeepSeek 汇总 Qwen+Kimi）和
Claude Opus 4.8 直接回答，对比发现：

| 维度 | MoA（3模型） | Opus 4.8 直答 |
|:---|:---|:---|
| 框架多样性 | ✅ 更多维度（AI资本开支映射独有） | 更聚焦 |
| 原创洞察锐度 | 中等（综合后平均化） | ✅ 更强（零弹性买家陷阱、稳定币分流等独有） |
| 概率权重/可操作性 | 弱（定性为主） | ✅ 强（45%/35%/20% 概率+具体区间） |
| 遗漏风险 | ✅ 低（多角度覆盖） | 高（单一模型的盲区无人纠正） |
| 适用场景 | 探索性分析、新领域、防止遗漏 | 有明确框架后追求锐度和操作性 |

**使用建议**：
- **先用 `/moa` 做探索**——获得多角度覆盖，发现意想不到的维度
- **再用 Opus 4.8 直答**——在有框架的基础上追求原创深度和概率加权判断
- 不要用 `/moa` 替代单一顶级模型——两者互补，不是替代关系

## MoA 作为 Opus 前置筛选器（2026-07-02 修订）

当遇到复杂问题但不确定是否值得花 Opus 的钱时，MoA 可以充当"省钱筛子"。

**决策逻辑**：
- 问题复杂、你不确定要不要 Opus → 先跑 MoA 探路
- 看完 MoA 结果 → **由你（用户）决定**要不要升 Opus
- 你已经确定要 Opus → 直接 Opus，别绕 MoA

**⚠️ 不能用"三模型一致/分歧"自动决定是否升级 Opus**：
- Agent 无法从 MoA 输出中可靠判断参考模型意见是否一致
- 参考模型看不到完整上下文，所谓"一致"不可信
- MoA 只是一个多视角参考，不做升级决策——看完由用户拍板

**定位**：MoA 是探索工具，不是决策工具。Opus 是终审。别拿 MoA 做最终判断。
**记忆同步**：Memory 中已记录 MoA 定位为「Opus 前置筛选器，非共识/分歧判定器」。
