---
name: model-subscription-evaluation
description: 评估模型订阅套餐额度够不够时触发。用 agent.log 真实用量折算成本对比套餐额度，回答"能用什么档次模型"。
version: 1.0.0
metadata:
  hermes:
    tags: [subscription, quota, pricing, token-usage, cost-analysis]
    related_skills: [hermes-china-providers, trendradar-operations]
---

# Model Subscription Evaluation（模型订阅套餐额度评估）

用户问"XX 订阅/套餐的额度够不够"、"开 X 套餐能用什么档次的模型"、"涨价/活动取消后额度还剩多少"时用本流程。**核心原则：不数官方宣传的"请求次数"，用自己日志里的真实 token 消耗按套餐定价折算美元成本**。

## 一、先统计自己的真实用量（数据来源：agent.log）

```bash
cd ~/AppData/Local/hermes/logs
# API call 行格式：API call #N: model=xxx provider=yyy in=8947 out=159 total=9106 latency=Xs cache=8832/8947 (99%)
```

- 正则：`(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*?model=(\S+).*? in=(\d+) out=(\d+).*? cache=(\d+)/(\d+)`
  - ⚠️ `out=` 和 `cache=` 之间有 `total=/latency=` 字段，正则必须用 `.*?` 跳过
- 🔴 **区分 cron/日报与日常对话：用 `'[cron_' in line` 判断，不要用正则可选组**（2026-08-14 实踩：`(\[cron_[^\]]+\])?` 可选组因回溯顺序永远匹配空，所有 cron 调用被误计为对话）。日志里 cron 会话行带 `[cron_<jobid>_<时间戳>]` 前缀
- **5h 窗口峰值**：按天收集时间戳排序，对每个时间戳滑动 5 小时窗口计数 `sum(1 for t in times if t0 <= t < t0+5h)`——这是判断"5 小时限制"会不会撞墙的唯一依据（重活日峰值可达 400+ 次/5h，平时 50-150）
- 输出画像：总调用次数、日报 vs 对话占比、平均每次输入 tokens、缓存命中率（98% 是常态）、5h 峰值

## 二、拿套餐官方定价表

抓官方文档（如 opencode.ai/docs/go），需要：每模型 **输入/输出/缓存读取 的 $/1M tokens** + **月度额度**（$15/$60 两档很常见）+ **官方预估请求数** + **5h/周/月全局限制**。

## 三、折算真实成本（公式）

```
月成本 = cache_tokens×cache_price + miss_tokens×input_price + out_tokens×output_price   （per 1M）
占用比例 = 月成本 / 月度额度
```

- 缓存命中率决定一切：98% 命中时成本比 0% 命中低 ~50 倍（缓存读取价通常只有未命中的 1/50）
- 我们的请求平均 ~200K tokens/次（含缓存），是 OpenCode"典型编程请求"（~50-68K）的 3 倍 → **官方请求数对我们打 3 折**

## 四、分级结论（交付格式）

分两个情景给表：**只跑 X（如日报）** vs **全部任务（含日常对话）**：

| 结论 | 判定 | 含义 |
|---|---|---|
| ✅ 随便用 | 占用 <30% | 怎么用都用不完 |
| ⚠️ 够用但紧 | 30-75% | 能当主力但要留意 |
| ❌ 会超额 | >75% | 月底必爆或顶格（注意日常对话占比高的场景） |
| 🚨 5h 墙 | 5h 峰值×单次成本 >$12 | 高频 agent 直接撞墙，与月额度无关 |

## 五、关键陷阱（2026-08-14 实测）

1. **额度按模型隔离，不共享**：便宜模型（Flash/MiMo 等）$60/月、旗舰模型（Grok/GPT Luna/Kimi K3/V4 Pro）$15/月——**Flash 没用完不能挪给高级模型**。用户常误以为"Flash 省下的额度能拿去用高级模型"——要明确纠正
2. **"日报跑得起 Luna" ≠ "Luna 能当主力"**：日报只占 19% 调用，日常对话占 81%——把对话也算进去，$15 档旗舰普遍超 2-9 倍
3. **官方请求数假设失真**：基于典型编程请求（~68K 缓存 tokens），长上下文 agent 请求（~200K）按美元计消耗 3 倍
4. **平台定价与官方 API 价联动**：官方涨价（如 DeepSeek 2026-08-17 峰谷定价，Flash 输出 +125%）→ 平台大概率同步调价 → 额度对应请求数缩水。涨价前先给用户"涨价后占用比例"的敏感测算
5. **单次成本估算**：用"我们平均每次调用输入 × 模型输入价 + 输出 × 输出价"，不要用官方"每请求 $X"数字

## 参考数据

- `references/opencode-go-2026-08.md` — OpenCode Go 完整 18 模型定价表、额度机制、DeepSeek 8/17 涨价细节、本机用量画像与分情景测算结果（可直接复用数值）
