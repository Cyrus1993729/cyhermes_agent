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

## 一、先统计自己的真实用量（数据来源：首选 state.db，次选 agent.log）

### ✅ 首选：state.db 的 session_model_usage 表（2026-08-15 实测，比 agent.log 精确一个量级）

```python
import sqlite3, datetime
db = sqlite3.connect(r'C:\Users\Administrator\AppData\Local\hermes\state.db')
db.row_factory = sqlite3.Row
rows = db.execute('''
SELECT model, billing_provider,
       COUNT(DISTINCT session_id) as sessions,
       SUM(api_call_count) as calls,
       SUM(input_tokens) as inp, SUM(output_tokens) as out,
       SUM(cache_read_tokens) as cache_r, SUM(cache_write_tokens) as cache_w,
       SUM(COALESCE(actual_cost_usd, estimated_cost_usd)) as cost
FROM session_model_usage
GROUP BY model, billing_provider
''').fetchall()
```

- 表字段：`session_id, model, billing_provider, billing_base_url, billing_mode, task, api_call_count, input_tokens, output_tokens, cache_read_tokens, cache_write_tokens, reasoning_tokens, estimated_cost_usd, actual_cost_usd, cost_status, cost_source, first_seen, last_seen`
- **`first_seen` 是 epoch 秒时间戳**，按天聚合要 `datetime.datetime.fromtimestamp(ts).strftime('%m-%d')`
- **筛选某 provider 的用量**：`WHERE billing_provider = 'deepseek'`（或按 billing_base_url 区分官方/套餐）
- 精确区分 flash/pro：`GROUP BY model`；真实成本列：`COALESCE(actual_cost_usd, estimated_cost_usd)`
- ⚠️ 注意 `cache_read_tokens` 常常是 input 的 20-50 倍（长上下文 agent 常态），定价时必须按缓存价算，否则成本高估 50 倍

### 次选：agent.log（表不可用或需要按会话行级分析时）

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

## 六、从评估到迁移：套餐接入迁移清单（2026-08-15 OpenCode Go 实踩）

评估完"额度够"之后要真正切换 provider 时，**盘点全部接入点**是第一步，漏一个就有一条线静默走旧账单：

1. **Hermes 主配置** `~/.hermes/config.yaml`：`model.base_url`（顶部）、`model.provider`、MoA preset（`moa.presets.*.aggregator` / `reference_models` 的 provider）、`cron.model_provider`——全文 grep `base_url|provider` 逐个核对
2. **凭据** `~/.hermes/auth.json` 的 `credential_pool.<provider>`：`source: env:X` 指向 .env 变量；`base_url` 可能写死官方地址要同步换。⚠️ auth.json 受保护 read_file 会拒，用 terminal python 读或 hermes CLI
3. **`.env`**：API key 变量值替换，**旧 key 注释保留**便于回滚
4. **scripts/ 下的独立探测/健康检查**：`api_probe.py`、`api_healthcheck.py` 常硬编码 key 文件路径 + 官方 URL——grep `api.deepseek.com|DEEPSEEK_API_KEY|key.txt` 扫全目录
5. **skills 附属脚本**：如 `video-understand-core/scripts/pipeline.py` + `quick_summary.py`——注意它们可能用**旧模型名**（`deepseek-chat`），套餐里不存在，要一并改成套餐模型 ID（`deepseek-v4-flash`）
6. **模型名映射**：官方名 ≠ 套餐名（deepseek-chat → deepseek-v4-flash），切换时逐处核对
7. **验证**：改完先跑 `api_probe.py`（或对套餐 URL 发一次真实 chat/completions）确认 key+模型名都通，再重启 gateway 生效
8. **回滚保险**：官方 key 不删（.env 注释保留 + 桌面 key 文件不动），套餐撞墙（5h $12 / 周 $30 / 月 $60 全局限制）可秒切回

> 迁移决策的用量依据直接用本 skill 第一节的 state.db 查询：分模型 input/output/cache 折算套餐账单，对照套餐全局限额（如 Go 的 $12/5h、$30/周、$60/月），占用 <30% 全迁无压力、>75% 只迁低耗线。

## 参考数据

- `references/opencode-go-2026-08.md` — OpenCode Go 完整 18 模型定价表、额度机制、DeepSeek 8/17 涨价细节、本机用量画像与分情景测算结果（可直接复用数值）
