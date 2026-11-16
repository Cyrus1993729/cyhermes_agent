---
name: model-subscription-evaluation
description: 评估套餐额度够不够、或诊断「为什么变慢/上下文膨胀」时触发。用 agent.log/state.db 真实用量折算成本与延迟。
version: 1.0.0
metadata:
  hermes:
    tags: [subscription, quota, pricing, token-usage, cost-analysis]
    related_skills: [hermes-china-providers, trendradar-operations]
---

# Model Subscription Evaluation（模型订阅套餐额度评估）

用户问"XX 订阅/套餐的额度够不够"、"开 X 套餐能用什么档次的模型"、"涨价/活动取消后额度还剩多少"时用本流程。**核心原则：不数官方宣传的"请求次数"，用自己日志里的真实 token 消耗按套餐定价折算美元成本**。

🔴 **交付节奏（2026-10-25 用户再次当面要求，硬要求）**：这类评估要连抓好几个页面、跑好几段统计，是典型长任务。**每查实一个能独立成立的结论就冒一句**（1–3 行：刚查到什么 → 下面查什么），不要憋到全部查完才甩一份长文。用户原话：「如果是我直接问你的，不是跟健康相关的东西，我还是希望你可以每做一步都及时给我反馈，而不要让我直接等很长时间看你最终的结果。」本会话就先犯了——一口气跑了十几次工具调用才出第一句话，被中途叫停。**中间反馈只给结论和下一步，篇幅仍按精简口径。**

🔴 **2026-11-13 又被当面重申一次——触发条件不是「任务大小」，是「工具调用次数」。** 本次只是查一个 profile 的上下文水位，自我感觉是两分钟的小检查，结果连跑 8 次工具调用才开口，被用户中途插话：「你这个主 agent 你的汇报习惯应该是尽量实时的去汇报你的进展，你的动作只有派给了健康助理的任务才是一次性做完再汇报的。」
→ **判据改成数调用**：任何要跑 ≥3 次工具调用才出结论的活，第 2 次调用后就冒一句。诊断/审计/核对类任务**最容易被误判成「很快就好」**，恰恰是复发点。
→ **分工口径**：**主 agent 自己干的活＝边做边说**；**派给健康助理 / 子代理的活＝等它回执、一次性原样搬明细**。两套节奏别搞混——后者憋着是对的，前者憋着就是本条的错。

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
- 🔴 **`input_tokens` 字段本身已经排除了缓存**（2026-10-08 交叉验证确认）：它是"未命中缓存的输入"，与 `cache_read_tokens` 是**并列相加**关系，不是包含关系。分母口径别搞反
  - 与日志语义**不一致**：`agent.log` 的 `in=` 字段**含**缓存（行尾 `cache=50816/51677` 表示 51677 里有 50816 命中），所以日志口径的非缓存输入 = `in - cache`
  - 交叉验证法：挑一个会话，grep 出它全部 API call 行求 `Σ(in − cache)` 与 `Σ out`，量级应与 state.db 该行 `input_tokens` / `output_tokens` 对得上（精确相等不必强求，state.db 行是滚动更新的快照）

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

抓官方文档（如 opencode.ai/docs/go），需要：每模型 **输入/输出/缓存读取 的 $/1M tokens** + **月度额度** + **官方预估请求数** + **5h/周/月全局限制**。

🔴 **核实定价/额度一律 fresh curl 原始 HTML，不要用 `web_extract`**（2026-08-17 实踩：web_extract 返回缓存旧版，导致误判"额度未缩水"）。页面也可能跳转（`opencode.ai/docs/go` → `/v2/docs/console/go/`），要跟 `-L`。

### 🔴 第三方聚合站（OpenDesign / OpenCode Zen / Kilo / 中转站）比价铁律（2026-10-25 建立，2026-11-09 扩到 7 条）

1. **先看模型清单，再看价格。** 聚合站的便宜档位几乎都把旗舰模型标成 `Not included`，只在顶层开放。2026-10-25 实例：用户问「OpenDesign 用 Opus 5.5 和 Claude 官方 Pro 同样 $20 额度差多少」——抓官方定价页发现 **Plus($20) 卡片上 Claude Opus 5.5 / Claude Fable 5.1 / GPT-6 Astra 三个都明确标 Not included**，用户的前提直接不成立。要用 Opus 5.5 得 Pro 档（$100/月，年付 $60）。**比价第一步永远是确认目标模型落在哪个档位**，不确认就算出再多数字也是错的。
2. **横幅上的大数字先分清是"价格"还是"加赠额度"。** 同一页 hero 写着 `PRO $20 / MAX $100 / +$20 / +$100`，看着像降价，实际是"限时加赠 $20/$100 credits"。抓原始 HTML 找相邻的 `Limited-time bonus credits` 再定性。同理"限时加赠 20%"要让用户知道 `$120` 的原值是 `$100`。
3. **额度表按 `<tr>` 逐格解析，不要用去标签后的可见文本顺序。** 纯文本化会让表格列串位（本次中文页把 Plus 的套餐模型额度显示成 $160，实际是 $20，$160 是 Design Plan 额度）。正确姿势：`re.findall(r"<tr[\s\S]*?</tr>", html)` → 每行 `re.findall(r"<t[hd][\s\S]*?</t[hd]>", tr)` → 逐格 `re.sub(r"<[^>]+>"," ",c)`。
4. **双层额度要问清能不能挪用，方向要问反。** 聚合站常拆成「plan-model 额度（无窗口，按周期清零）」+「Design Plan / Coding Plan 额度（有 5h/7 天窗口）」。OpenDesign 的方向是**单向**：Design Plan 用完后可溢出到剩余 plan-model credits，但 **plan-model 调用只吃 plan-model credits，吃不到 Design Plan 池**。2026-11-09 实例：Pro 卡片写「总额度 $480 = Design Plan $360 + plan models $120」，而 Opus 5.5 属于 plan models → **Opus 的硬上限只有 $120，那 $360 一分都用不上**。用户问"够不够"时必须分别报两个数，不能加总当成一个池。
5. **先分清「额度型」和「充值型」，换算逻辑完全不同。** 额度型（OpenDesign / OpenCode Zen）：月费 → 一笔明码美元额度，折扣体现在杠杆率。充值型（**Kilo Pass**）：订阅额 1:1 进余额、**按 provider 原价消耗、零加价**，它**没有任何价格折扣**，唯一优惠是白送的 bonus credits。用户问"买它能用多少 X 模型"时，充值型的答案是 `(订阅额 + bonus) ÷ 该模型官方价`——别去找"套餐内模型价"，它不存在，直接去模型详情页拿原价。
6. **比较聚合站只用一个指标：「每 $1 实付换多少目标模型额度」。** 2026-11-09 实测这一栏：Kilo 月付 **1.33×**（另有 5% 处理费）、Kilo 年付 **1.5×**、OpenDesign Pro 月付 **1.2×**、OpenDesign Pro 年付（$720/年 = $60/mo 换 $120/mo）**2.0×**。单看月费或单看额度都会选错。
7. **充值型必须查 bonus 的领取条件——它常常是拿不到的折扣。** Kilo Pass：bonus 要**先把当月付费 credits 用完才发放**、**月末作废**、月付得**连续订到第 8 个月**才爬满 40%（第 1 月仅 10%，第 2 月一次性 50% 欢迎奖）。把 40%/50% 直接写进结论而不标领取条件 = 虚报，必须同时写"你当月没正好花超，这 40% 就是零"。
8. **聚合站的模型清单多半是客户端渲染，grep 正文 grep 不到。** 两条正确的取数路径：① 模型名/价格 → 直接抓**单模型详情页**（如 `kilo.ai/models/anthropic-claude-opus-5-5`，价格在 `<dt>`/`<dd>` 里，或 JSON-LD 的 `PriceSpecification`）；② 档位归属 → 按**容器顺序**切 `<ul data-astro-cid-...>` / 卡片 block，再看每个 block 的 header 标签（`Not included` / `Standard · $20/month` / `6× · $120/month`）判断该档开放了哪一层。整页 grep "Opus" 计数为 0 不代表模型不可用，只代表清单不是静态 HTML。
③ **充值型套餐的规则全在 JSON-LD 里**：Kilo Pass 页面（`kilo.ai/pricing/kilo-pass`）是 Next.js 客户端渲染，但**整套 FAQ 在 `<script type="application/ld+json">` 中**——三档价格、bonus 梯度（10% / 第 2 月 50% 欢迎奖 / 第 8 月满 40%）、年付 50%、bonus 月末作废、5% 处理费、credits 一年过期，**一次 walk `@type == "Question"` 就全拿到**，比抓正文快十倍。同理 `claude.com/pricing` 的额度口径与 `Monthly API credits` 那行也在 `__next_f.push` 内嵌 JSON 里（正文 grep 得到，但 FAQ 答案只在 JSON）。

### 🔴 Claude 官方订阅侧的固有盲区（2026-10-25 建立，**2026-11-09 换掉全部旧数字**）

Anthropic **从不公布**任何档位的 token 数或金额额度，官方原话 `there's no fixed message count`，并保留「按我们的判断另行限制」的权利。只给相对倍数：**Pro ≥5× Free（每 5 小时会话）；Max = 5× Pro（5h 与每周都是）；Ultra = 10× Pro（每周）**。机制是滚动 5 小时窗口 + 每周上限，与网页版/Claude Code **共用同一池**。
🔴 **2026-10-30 改过名**：Max 5x → **Max**（$100）、Max 20x → **Ultra**（$200）。用户或旧文章说「Max 5x / Max 20x」时先对到新名字。Pro 仍是 $20/月，年付 $17/月（一次付 $200）。
🔴 **决定能不能接 Hermes 的不是额度，是 `Monthly API credits` 这一行**：**Pro = No，Max = $100/月，Ultra = $200/月**（Team 最高 $500/月合并池）。**Pro 没有 API access**，只能走官方 Claude Code CLI（`claude -p`）或界面，**不能配 base_url**——额度再大也只能人肉兑现。付费档都能开 `usage credits`：**撞限后按标准 API 价继续用**（有 $2,000/天兑换上限），等于自动降级成按量付费。Fable 在 Max/Ultra 含在每周额度的 50% 内，Pro 只能靠 usage credits。Opus 5.5 从 Pro 起就有（Free 只有 Sonnet/Haiku 级）。
→ 回答「Claude Pro 额度有多少」**必须明说没有官方数字**。现行最好的第三方口径（wokey.ai，**79 个真实账号**，10/26–11/02 那一周，2026-11-02 更新）：**Pro = 约 $155/周（中间 50% 在 $146–$173）≈ $673/月，是月费的 34 倍**；非缓存 token 24.2M/周、输出 1.7M/周；**一个 5h 窗口约 $12**，每周约 13 个满窗口。**Ultra 实测 $1,549/周 ≈ $6,711/月 = 10.0× Pro（不是 20×）**——官方那个 20× 只作用于 5h 窗口，**每周上限才是长期使用的天花板**。SemiAnalysis 受控测试（2026-10-05）Ultra 全用 Opus 5.5：agentic（96.6% 缓存）≈ **$11,726/月**、chat ≈ $9,200/月；与实测的差全在缓存命中率口径（92% vs 96.6%）。**两套数一起给，别只挑一个。**
→ ⚠️ **同一账号会漂**：Pro 周值 09-24 $125 → 10-08 $162 → 10-12 $170 → 11-02 $155。**不能拿它做预算**，报数必须带区间 + 测量周 + 账号数。旧的「博客园 $18/5h、$180/周」与「GitHub $1000/周」口径已作废，不要再用。
→ 与"明码美元额度"的聚合站比价时，把结构性差异摆出来（订阅＝不透明但杠杆 34×、会撞墙；聚合站＝透明可预算、无窗口），别只甩一个换算数字。完整档位表见 `references/opendesign-plans-2026-10.md`，Claude 侧全套数字见 `references/claude-plans-2026-11.md`。

### 🔴 订阅额度是给人用的，聚合站额度是给 agent 用的（2026-11-09）

只比「一美元换多少 Opus 用量」，会得出**官方订阅碾压 17–23 倍**的结论（Pro 34× vs Kilo 年付 1.5× / OpenDesign 年付 2.0×）。**照这个直接推荐会误导**，必须再走两步：

**① 把 5h 窗口换成「调用次数」，和自己的最重一天对撞。**
```
窗口内可用调用数 = 窗口美元等值 ÷ 我们的单次成本
Pro: $12 ÷ $0.070 ≈ 172 次/窗口
```
本机最重一天 400–1,100 次（10-21 = 1,116、10-25 = 1,053）→ **一天要撞 2–6 次窗口，只能干等重置**。聚合站的 plan-model 额度反过来**无 5h/周窗口**。这一条经常比总价更能决定选型。

**② 问清额度能不能程序化调用。** 没有 API credits 的档（Pro）进不了 Hermes 主链路。聚合站（Kilo / OpenDesign）天生可配 base_url，这是它们唯一不可替代的价值。

**结论口径**：订阅便宜到不合理但**只能人肉兑现**；聚合站贵，买的是「无窗口 + 可接 API」。**两者不是同一类商品，别比总价**——先问用户是「人在 Claude Code 里干重活」还是「agent 批量跑」。

### 🔴 「两类需求」怎么配：重活旗舰 + 日常便宜模型（2026-11-09 实做）

用户提「Opus 干重活、DeepSeek 这类做日常聊天/简单事项」时的固定三步，**别先报价格**：

1. **先查现有套餐里到底有没有目标模型。** 2026-11-08 现抓 OpenCode Go 文档：全表 33 个模型**没有 Opus 5.5**，Claude 系只有 Haiku 5.5（$15 额度）。→ 「在现有套餐里加 Opus」这条路直接不存在，**别假设同一供应商一定有更高档**。文档里 `Opus` 关键字命中 0 也可能是客户端渲染，要按模型表逐行确认。
2. **找额度天生分两层的套餐。** OpenDesign 的结构正好对上：`Design Plan` 池（DeepSeek/GLM/MiMo 等，有 7 天窗口）+ `plan models` 池（Opus 5.5 等旗舰，**无窗口**）。Pro 年付 $60/月 = Design Plan $360 + plan models $120，**一个订阅同时喂两类需求**。但**旗舰池是硬顶**（Pro 的 Opus 上限就是 $120，那 $360 一分用不上，方向见铁律 4）。
3. **算日常那部分真实值多少钱，别被「送了一大池」骗。** 我们 `deepseek-v4.1-flash` 近 30 天 = **$15.87**（全 peak $31.73），Design Plan 的 $360（DeepSeek 倍率 0.5×）只用到 **3–5%**。

**按重活强度分档给方案**（一次深度会话 ≈ 50 次调用 ≈ $3.5）：30 次/月以内 → OpenDesign Pro 年付 $60/月；60–80 次 → Max 年付 $98/月（$300 Opus）；不定量或不想锁年付 → 留 OpenCode Go $10 + Kilo Pass 按需充（**同等 Opus 额度贵 30–40%**）。给完方案必须补一句数据留存风险：聚合站查不到 OpenCode 那种 ZDR 明细，财报/公司业务内容进这类模型前要说清。
→ 与"明码美元额度"的聚合站比价时，把这条结构性差异摆出来（订阅＝不透明但超值、会撞墙；聚合站＝透明可预算、无窗口），别只甩一个换算数字。完整档位表见 `references/opendesign-plans-2026-10.md`。

### 🔴 官方限额换算公式（2026-10-20 fresh curl 原文确认）

OpenCode Go 文档原话：

> Each model has the following usage limits: **5-hour — 20% of the monthly limit; weekly — 50%; and monthly — 100%.**

→ 所以 **`5h 上限 = 月额度 × 20%`、`周上限 = 月额度 × 50%` 是官方口径，不是经验估计**。
`opencode_go_quota_rank.py` 用的就是这个比例，可以直接引用。

举例：DeepSeek V4.1 Flash（月 $80）→ 5h $16 / 周 $40；某 $15 档模型 → 5h 仅 **$3**，重活日很容易撞。
**给 $15 档模型做选型时，5h 墙往往先于月额度成为真正的否决项。**

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

### 🔴 外部 CLI 模型（Codex / Claude Code CLI）的用量审计盲区——state.db 查不到（2026-08-31 实踩）

`session_model_usage` 只记录 **Hermes 自己发起的 API 调用**。subprocess 直调的 Codex CLI（`codex.cmd exec`）、Claude Code CLI（`claude -p`）、`daily_report_review.py` 这类脚本的模型用量**完全不在 state.db**（实测 `WHERE model LIKE '%gpt-5.6%'` 返回空）。审计外部 CLI 订阅只能三源交叉：
1. **本地调用频率**：agent.log 里脚本名出现次数（如 `grep -c daily_report_review` → 8 月仅 3 次；`grep -c codex` 分布稀疏）——state.db 给不了这个
2. **官方用量页**：ChatGPT/Codex 用量统计、opencode 的 scode.ai/workspace 页面（5h/周/月三柱 + 模型级明细：如 8/31 实测 Flash $4.71/$30=17.9%、qwen3.7-max $0.10/$60=0.2%）
3. **官方定位 + 社区实测**：learn.chatgpt.com 定价页写死套餐定位（Plus="Power a few focused coding sessions each week"——"每周几次"就是官方设计容量）；OpenAI 社区 8 月大量"weekly 限额 2-3 天耗尽"抱怨（GPT-5.6 单次消耗大）——**5h 墙不是唯一约束，weekly 是隐性墙**，重度使用前先查社区当前抱怨模式

### 🚨 评估前必须先用数据核实负载，禁止凭印象假设（2026-08-31 用户纠正）

用户原话："你这段话里有一些描述是不是有点太绝对了"——当时输出"日报审查每天跑、一周 7 次会烧穿限额"，实际 `daily_report_review.py` 8 月只跑 3 次（抽查机制非每日任务），整个担忧是编造的。**评估额度/成本前先做三件事再下结论**：① 查实际频率（日志/脚本调用痕迹，不是猜）② 查官方定位与配额数字（learn.chatgpt.com 定价页）③ 查社区对真实瓶颈的共识。没有数据支撑的"会烧穿/用不完"论断用户会直接质疑——本会话两次凭直觉判断（"限额紧张"、"用量余量判断"）前者被纠、后者靠官方页数据才对。

## 六、从评估到迁移：套餐接入迁移清单（2026-08-15 OpenCode Go 实踩）

评估完"额度够"之后要真正切换 provider 时，**盘点全部接入点**是第一步，漏一个就有一条线静默走旧账单：

1. **Hermes 主配置** `~/.hermes/config.yaml`：`model.base_url`（顶部）、`model.provider`、MoA preset（`moa.presets.*.aggregator` / `reference_models` 的 provider）、`cron.model_provider`——全文 grep `base_url|provider` 逐个核对
2. **凭据** `~/.hermes/auth.json` 的 `credential_pool.<provider>`：`source: env:X` 指向 .env 变量；`base_url` 可能写死官方地址要同步换。⚠️ auth.json 受保护 read_file 会拒，用 terminal python 读或 hermes CLI
3. **`.env`**：API key 变量值替换，**旧 key 注释保留**便于回滚
4. **scripts/ 下的独立探测/健康检查**：`api_probe.py`、`api_healthcheck.py` 常硬编码 key 文件路径 + 官方 URL——grep `api.deepseek.com|DEEPSEEK_API_KEY|key.txt` 扫全目录
5. **skills 附属脚本**：如 `video-understand-core/scripts/pipeline.py` + `quick_summary.py`——注意它们可能用**旧模型名**（`deepseek-chat`），套餐里不存在，要一并改成套餐模型 ID（2026-10-08 现状 = `deepseek-v4.1-flash`）
6. **模型名映射**：官方名 ≠ 套餐名，且两侧会各自演进（`deepseek-chat` → `deepseek-v4-flash` → `deepseek-v4.1-flash`；官方 API 侧现行 ID 是 `deepseek-flash`），切换时逐处核对
7. 🔴 **扫描范围必须含 `skills/**/*.py`**：2026-10-08 全量换名时，首轮只扫了 `config.yaml` + `scripts/*.py` + `cron/jobs.json`，漏掉 `skills/video-understand-core/scripts/` 的 6 处，靠二次扫描才补回。活跃调用点 = config.yaml（含 `moa:` 段）+ cron/jobs.json（含 prompt 散文）+ `scripts/*.py` + `skills/**/*.py` + `models.json` + 部署项目 config
8. **验证**：改完先跑 `api_probe.py`（或对套餐 URL 发一次真实 chat/completions）确认 key+模型名都通。然后**用 state.db 收闭环**——跑一次一次性会话（`hermes -z "只回复：验证OK" --cli < /dev/null`），再查 `session_model_usage` 最新行应出现 `model=<新模型> / billing_provider=<新 provider>`；日志里查不到 CLI 一次性运行的 API call 行，别在那里找
   - 🔴 **改 `model.default` 这类纯配置值不需要重启 gateway**（2026-10-08 实证）：`load_config()` 的缓存以 `(config.yaml 的 mtime_ns, size)` 为键（`hermes_cli/config.py:3883` 文档字符串），文件一改，下一次读取即失效。**新会话自动用新模型**；老会话（agent 实例已建）保持旧模型直到 `/reset`。只有新增/更换 provider 插件、改 base_url 这类需要重建进程的才要重启
9. **回滚保险**：官方 key 不删（.env 注释保留 + 桌面 key 文件不动），套餐撞墙（5h $12 / 周 $30 / 月 $60 全局限制）可秒切回

> 迁移决策的用量依据直接用本 skill 第一节的 state.db 查询：分模型 input/output/cache 折算套餐账单，对照套餐全局限额（如 Go 的 $12/5h、$30/周、$60/月），占用 <30% 全迁无压力、>75% 只迁低耗线。

## 七、从"够不够"到"选哪个"：多模型性价比排名法（2026-10-08 实做）

用户问"用哪个模型性价比高"时，不要只算主力一个模型——**把候选全排一遍再下结论**：

```
某模型月成本 = (非缓存输入×输入价 + 输出×输出价 + 缓存读×缓存读价) / 1e6
占用%       = 月成本 / 该模型月额度          ← 越低越划算
月可支撑次数 = 月额度 / 单次成本
```

三条判据，按顺序用：

1. **先按数据政策过滤，再比价格。** 套餐里常有"Contributor/贡献者"档模型标价极低，但官方 ZDR 表里写着 `Model training: Yes` / `Not ZDR`——**拿你的 prompt 和输出去训练模型**。日报、投资、公司业务内容一律不进这类模型，**直接排除，不要让它出现在排名表里**。选型输出第一段就要交代"排除了谁、为什么"——不写清楚，用户会以为你只是没看见那个更便宜的选项。
2. **缓存读单价才是决定性变量，不是输入价。** 长上下文 agent 负载下缓存读占输入 token 的 ~90%，而缓存价差可达 100 倍（DeepSeek $0.003/M vs Kimi K3 $0.30/M）。两个模型输入价相同、缓存价差 10 倍时，真实占用差 5-10 倍。**只看"输入 $"列必然选错模型。**
3. **工具调用能力必须实测，不能看文档。** 换主力前对每个候选发一次带 `tools` 的最小探针，确认响应里真的出现 `tool_calls`，顺带记录延迟。文档不会告诉你某个模型在 agent loop 里会不会退化成纯文本回复，也不会给你真实首字延迟。
4. **能写工具调用 ≠ 能用：必须再补一个「长文本吞吐探针」。** 小探针只输出 12-70 个 token，**完全暴露不出慢模型**。2026-10-08 实测：GLM-5.3-Flash 的小工具调用探针 1.5s 就返回（看着最快），但让它写 200 字要 **117.5 秒**（中间思考了 3658 字），要 400 字时 150 秒都没吐出正文——而我们一轮会话 20-27 次调用，按这个速度一次会话要跑一小时。**两个探针都要跑：小探针测「会不会用工具」，流式长生成探针测「能不能用」。** 流式探针量四件事：墙钟耗时、正文累计字数、reasoning 累计字数、`finish_reason`（None = 被超时截断）。
5. **能力分用中立第三方，不看厂商营销页。** 首选 Artificial Analysis：
   - 总榜 `https://artificialanalysis.ai/leaderboards/models`（服务端渲染，可直接 extract；列为 上下文/厂商/Intelligence Index/每任务成本/输出 t/s/TTFT/E2E）
   - **逐项对战页 `https://artificialanalysis.ai/models/comparisons/<模型A>-vs-<模型B>`** ← 这份最关键，给出 10 项子评测的分项对比（Intelligence Index / AA-Briefcase / GDPval-AA / **AutomationBench-AA** / Terminal-Bench 4.0 / SciCode / HLE / GDP.pdf / CritPt / AA-Omniscience / AA-LCR）+ 价格 + 速度 + 参数量
   - 第二源 `https://benchlm.ai/models/<slug>`（分品类排名 + 证据等级）；OpenRouter 模型页也挂 AA 分
   - 🔴 **总分高 ≠ 适合我们：一定要看分项，找出与「我们实际干的活」对应的那一项。** 2026-10-08 实例：MiMo-V2.6-Pro 总分 46 vs DeepSeek V4.1 Flash 39，其余 9 项全面领先，**唯独 `AutomationBench-AA`（SaaS 工作流自动化）59% vs 69% 明显更差**——而这正是日报/巡检/看门狗这类自动化的对口指标。GLM-5.3-Flash 同样在 AutomationBench 上 60% vs 69% 输给 DeepSeek。
   - ⚠️ AA 的速度/延迟是**首方 API** 数字，走 OpenCode 中转会差很多 → 速度只信本地实测（判据 4）
   - ⚠️ 分数字段是各模型 **max effort 推理档**；我们实际跑的档位可能更低、绝对分会掉，但**名次关系稳定**，报告时要说清这一点
6. **警惕「名字更强」陷阱。** 型号带 Pro/Max/Ultra 不代表更强：2026-10-08 实测 DeepSeek V4 Pro 的 AA 分 **36**，比 V4.1 Flash 的 **39 还低**，额度占用却 193%（官方已把 v4-pro 的请求路由到 V4.1 Flash 计费）。**任何「升级到 X」的建议之前，先在 AA 对战页上把两者的分项摆出来。**

**输出格式**：分梯队列（随便用 ≤10% / 宽裕 10-25% / 不能当主力 >50% / 超限 >100%），每行给 `月成本 = 占用%`，末尾给"结论 + 唯一值得试的替代项"。这份排名是**决策输入**不是决策本身——按 decision-gate 交给用户拍板。

**一条反直觉的经验（2026-10-08）**：按 state.db 折算出来的占用率，通常比直觉低一个量级。本次实测主力模型只占 6-13%，而此前手记里写的是"接近顶格 31-63%"——差在① 用的是 8 月迁移期的重负载窗口 ② 没把缓存读按缓存价算。**先算，再焦虑；也别信自己上一轮拍脑袋的估算。**

### 🔴 但别在「30 天实际」口径上收工——活跃日外推会让结论反向（2026-10-08 实做，判断因此翻转）

**统计窗口里一定有停摆日**：本次 45 天窗口里只有 33 天有活动（9/26–10/6 全停），近 30 天里只有 20 个活跃日。直接拿"近 30 天实际用量"折算是**系统性地低估一个正常月份**。

**两个口径都要算，结论按活跃日口径下判断，报告时写清用的是哪个**：

```
30 天实际      = 窗口内真实发生的 token 总和
活跃日外推 30 天 = (每个活跃日的 token 求和) / 活跃日数 × 30      ← 正常月份的代表值
活跃日定义：当天 api_call_count > 20（阈值可调，目的是滤掉零星 cron）
```

本次两个口径的差距足以改变选型结论：

| 模型 | 30 天实际 | 活跃日外推 | 结论变化 |
|---|---|---|---|
| DeepSeek V4.1 Flash (Off-Peak) | 6.3% | **11.3%** | 不变（依然宽裕） |
| MiMo-V2.6-Pro | 54.9%（看着"够用但紧"） | **98.7%** | **翻转为"贴顶、不能当主力"** |

→ 用户问"有没有更强的模型**且不超限额**"时，用低估的口径回答会给出**错误答案**。

**5h 墙用「最重的一天」当上界判定**：`当天非缓存输入×输入价 + 当天输出×输出价 + 当天缓存读×缓存读价`，与 `月额度×20%` 比。本次各候选的最重一天都远低于各自的 5h 上限（如 MiMo-V2.6-Pro 最重一天 $1.86 vs 5h 上限 $3.00），**5h 不是瓶颈，月池才是**。

### 🔴 2026-10-20 复评：没有比 DeepSeek V4.1 Flash 更好的替代

用户问「有没有性能更好的模型且额度充足」时，四步跑完（额度排名 → AA 总分 → **分项** → 双探针）。本次结论：

**额度够的候选只有 6 个**（活跃外推口径）：DeepSeek V4.1 Flash **10.6%** · MiMo-V2.5/V2.6-Flash 10.7% · LongCat-2.0 28.2% · GLM-5.3-Flash 34.3% · Hy3 38.5% · Qwen3.8 Flash 46.3%。

**更聪明的模型全在 $15 档，额度必爆**：MiMo-V2.6-Pro（AA 46.3）117.5% · Qwen3.8 Max（45.4）1338% · GLM-5.3（44.8）1209% · Kimi K3（43.6）1981%。

**对口分项 `AutomationBench-AA` —— DeepSeek 仍是第一**：

| 模型 | AA 总分 | AutoBench | 占额度 |
|---|---:|---:|---:|
| Gemini 4 Argon | 52.6 | **77.5%** | ❌ 训练用数据 + 1008% |
| DeepSeek V4.1 Flash（旧版） | 39.5 | **68.9%** | 10.6% |
| DeepSeek V4.1 Flash **1017** | **45.1** | 66.6% | 10.6% |
| GLM-5.3-Flash | 41.8 | 60.4% | 34.3% |
| MiMo-V2.6-Pro | 46.3 | 58.6% | ❌ 117% |
| Claude Haiku 5.5 | 43.4 | **35.4%** | 66% |

**本地双探针（走网关，非 AA 首方数字）**：DeepSeek **59.1 字/s** ≫ qwen3.8-flash 33.7 ≫ hy3 27.8 ≫ glm-5.3-flash 20.8（思考 6781 tokens，是 DeepSeek 的 17 倍）≫ longcat-2.0 **0.0 字/s**（finish=length，正文没吐出来）。

→ **额度/速度/对口分项三项同时赢，没有替代。** 唯一在 AutoBench 碾压的 Gemini 4 Argon 三条红线同时踩：训练用数据、1008%、贵 26 倍。

🔴 **AA 数据的提取坑**：`AutomationBench` 等分项在页面正文里是**空的**（图表客户端渲染），只有图表标题。真实数值在内嵌 JSON 的 `automationBenchPartialScore` / `automationBenchBreakdown.{strictScore,completion,violations}` 字段里。提取法：正则挖 `self.__next_f.push([1,"..."])` 的 JSON 块 → 找 `"name":"<模型>"` 往后 4000 字符内的 `automationBenchPartialScore`。现成脚本：`scripts/extract_aa_scores.py`。

### 🔍 单模型评估的固定六步（2026-10-20，用户问「XXX 怎么样」时）

用户点名一个模型问「怎么样」——**不是查一下分数就答，而是按这六步跑，结论才站得住**：

| # | 检查 | 对应什么 |
|---|---|---|
| 1 | **协议通不通** | 先发一个最小请求。OpenAI 兼容端点报 `ModelProtocolUnsupported` = 该走 Anthropic 端点（`/zen/go/v1/messages`）。**这是协议问题，不是模型不可用** |
| 2 | **额度 + 5h 墙** | 月额度、占用%（活跃日外推口径）、**5h = 月额度×20%** vs 我们最重日。$15 档 5h 只有 $3，往往先于月额度成为否决项 |
| 3 | **AA 总分** | 我们排在哪个档 |
| 4 | **对口分项** | **`AutomationBench-AA`**（日报/巡检/看门狗）+ 如相关看 `AnalystAgent`（表格/文档定量分析） |
| 5 | **本地速度实测** | 跑 `model_probe.py`。AA 速度是首方 API 数字，走网关差很多 |
| 6 | **数据留存 / 训练条款** | ZDR 表：`Model training: Yes` 直接否决；留存 30 天 vs 0 天要主动告知用户 |

**然后必须回答两个问题**（不答等于没评完）：
- **它比现在的主力强在哪一项？** —— 强项要具体到分项名，不是「总分高 3 分」
- **那个强项我们是不是已经有了更好的入口？** —— 2026-10-20 实例：Haiku 5.5 的强项是 AnalystAgent 53.8%（vs DeepSeek 35.0%，赢 18.8 点），但用户已经有 Claude Code CLI（同家血统 + 订阅内额度、不占 OpenCode 配额）→ **为边际能力再维护一套 Anthropic provider + 一个随时撞墙的 $3/5h 额度，不值得**

🔴 **单模型评估最容易犯的错：只看总分就推荐**。Haiku 5.5 总分 43.4 高于 DeepSeek 旧版 39.5，但它在 AutoBench 上只有 **35.4%**（DeepSeek 68.9%），且**违规次数 41,500 vs 25,200（1.6 倍）、每任务违规 83.7 vs 38.4（2.2 倍）**——AutoBench 的评分口径是「完成目标且不触发 guardrail」，违规翻倍 = 手比脑子快，**而这正是自动化任务最不能容忍的**。

## 八、变慢诊断：上下文膨胀 / 单轮调用数 / 账号被分走（2026-10-20 实做）

触发：用户问「你最近回消息怎么变慢了」「是不是装了 XX 之后变慢」。**别凭感觉猜，也别先归因到某个新装的东西**——三段日志跑完再下结论。

### 三段数据（全部只读，本机实测）

```bash
# ① 每次 API 调用的输入量与延迟，按天聚合
# agent.log 行：API call #34: model=… in=74260 out=457 total=74717 latency=9.3s cache=72832/74260 (98%)
python -c "…正则 '(\d{4}-\d{2}-\d{2}) .*API call #\d+: .*in=(\d+) out=\d+ total=\d+ latency=([\d.]+)s' …按天取中位数…"

# ② 每轮对话墙钟耗时与轮内调用数，按天聚合
# gateway.log 行：response ready: platform=telegram chat=… time=422.2s api_calls=1 response=188 chars

# ③ 按 session 拆，找吃上下文的大头
# 用 session id 分组，看每个 session 的「首调输入 / 末调输入 / 调用次数 / 单次最高输入」
```

### 本机基线数字（复用即可，别重新造）

- **新会话地板价**：cron 会话首调 `in≈11,777`；带一条长用户消息的 Telegram 会话首调 `in=18,473`、单次延迟 **4.2s**。这就是系统提示 + memory + 用户画像 + 技能清单 + 工具定义的下限，`/new` 之后回不到比这更低。
- **同一会话内的衰减**：本次 4 小时内 `in` 从 18K 涨到 75K，单次延迟从 4.2s 涨到 8–9s。**模型、账号、provider 全没变，唯一变量是历史长度。**
- **按天趋势（10/12→10/20）**：单次输入中位 5–6 万 → 8.4 万 → 24 万 → 13.6 万；单次延迟中位 4–5s → 9–16s，P90 20–35s。
- **Telegram 轮次耗时**：中位 150–220s，最慢一轮 1076s（那轮跑了 65 次 API 调用）。**中位 API 调用数只有 4 次 → 慢的不是每一步，是长轮次。**

### 归因三条，按证据强弱排序

1. **上下文膨胀**（主因）：单次 `in` 涨 3–4 倍，延迟同比例涨。来源＝会话历史 + 全量加载的大 skill（几万字一篇）+ 大段工具输出 + A2A 长消息。
2. **单轮工具调用次数**：一轮 30–65 次 API 调用 × 每次 8–9s = 4–18 分钟。**这同时是「用户觉得我没反馈」的直接原因**——憋着批量跑完才回一次。
   - 🔧 **对应的行为修正（2026-10-20 用户当面要求，硬要求）**：每完成一个可独立验收的子段就冒一句（1–3 行：刚做完什么 → 下面做什么）；**失败当场说**（例：零丢失校验发现丢 17 行，那一刻就报，不要修完再一次性汇报）；跨多轮工具调用的长任务至少一次中间反馈。用户原话：「不需要加倍仔细地汇报过程，但要回到以前的频率——不要做完所有事憋完再给我一段东西；中间有适度反馈，我好知道进展，有不对的地方也能及时告诉你。」**反面模式（被明确否决）**：跑完 30+ 次调用再甩一份完整报告——写得再好也不行，用户要的是可干预性。节拍多 ≠ 篇幅长，结论仍按精简口径。
3. **同账号被别的 profile 分走**：`--profile <name> serve` 是**独立进程、独立上下文**（读不到主助手的历史），不跑 cron，但**共用同一个 provider key 与同一份额度**。实测健康 profile 单次 `in` 高达 **41.8 万** token、当天 150 次调用 → 主助手在同一账号上排队。属放大器，不是主因。

### `/new` 到底清什么（用户会问，答准）

清：整段对话历史。不清：memory、用户画像、已装 skill、cron、config、模型设置 → **不会「失忆重来」**。
但有两点要说清：① 新会话里若又全量加载大 skill / 读大文件，照样重新涨上去，所以是「新会话 + 少加载大 skill + 大文件按需读」一套；② 中途 `/new` 丢任务进度 → **只在任务边界切换**，长任务的进度要提前落到文件（如 `deploy-log.md`），新会话读文件接手。

> 自带自动压缩（`compression.threshold: 0.5`、`protect_last_n: 20`）是**有损**的，且压缩本身要多花一次调用 → 宁可用户手动 `/new`。

### 排查设备的常驻进程（顺带会看到）

`wmic process where "name='python.exe'" get ProcessId,CommandLine`：主 profile 通常有 `serve` + `gateway run` 各一对（wrapper + `.hermes-runtime` 真身），每个 profile 再加一对。4 个 Python 运行时 + 若干 Hermes.exe ≈ 1.5GB 内存。**CPU 不是瓶颈，内存和 provider 排队才是。**

### 🔍 非默认 profile 的上下文审计（2026-10-31 实做，健康助理为例）

用户说「检查一下 XX 助理的上下文，过长就整理」时，**别只看主 profile**。每个 profile 是独立的 state.db + 独立 config：

- DB：`~/AppData/Local/hermes/profiles/<name>/state.db`（主 profile 才是 `hermes/state.db`）
- 记忆上限在**该 profile 自己的 config.yaml**：`memory.memory_char_limit` / `user_char_limit`
- 记忆文件：`profiles/<name>/memories/MEMORY.md`、`USER.md`

**三个必查数字**（一条 SQL 拿不到，要分开算）：

1. **上下文有多长** → `SUM(cache_read_tokens) / SUM(api_call_count)` = 平均每次调用重放的 prompt tokens。这是最硬的一个数，比数消息条数靠谱。
2. **有没有被压缩过** → `messages` 的实际列是 **`active` + `_compressed_summary`**（不是 `compacted`，写错直接 no such column）：`SELECT _compressed_summary, active, count(*), sum(length(content)) FROM messages WHERE session_id=? GROUP BY 1,2`。`(_compressed_summary=1, active=1)` 那行就是压缩摘要，**它本身也在上下文里、常有 5–6 万字符**，是容易被忽略的隐藏大户。再对照有没有 `task='compression'` 的 `session_model_usage` 行。
3. **谁在吃上下文** → 按 `role` + `tool_name` 分组求 `length(content)+length(tool_calls)`。实测健康助理：assistant 自己的回复 35%、terminal 输出 24%、read_file 14%（38KB 的 profile.md 整篇读了好几遍）、patch 7%——**大文件整读是最容易砍的一刀**。

**判断口径**：对照模型窗口（`models_dev_cache.json` 里 `limit.context`；DeepSeek V4.1 Flash 1M、gpt-6-luna 1.05M）。占用 <20% 不叫「爆」，但每次全量重放照样拖延迟；>50%、或**单日暴涨**（本次 270/272 条挤在同一天）才算必须整理。别把「占窗口 16%」说成危险，也别因为「没超窗口」就说没事——要把「慢/贵」和「会崩」分开讲。

### 🔴 最硬的口径：直接读 agent.log 里的压缩记录（2026-11-03 复做）

估算之前先 grep 日志捞**上一次压缩的真实数字**——它一次给出「窗口」「阈值」「压缩后基线」三个数，比按字符折算准得多：

```bash
grep -aiE "compress|summar" ~/AppData/Local/hermes/profiles/<name>/logs/agent.log | grep -v turn_context
# Preflight compression: ~218,615 tokens >= 120,000 threshold (model deepseek-v4.1-flash, ctx 1,000,000)
# Pre-API compression: ~500,929 request tokens >= 500,000 threshold (context=1,000,000, attempt=1/3)
# context compression done: session=… messages=690->95 rough_tokens=~82,969 awaiting_real_usage=true
```

- **`ctx 1,000,000` 就是真实窗口**，别再去 `models_dev_cache.json` 查（缓存里的 limit 常比实际配置旧）
- 压缩后 `messages=95 / rough_tokens=~82,969` 是当前会话的**压缩基线**；此后 `turn_context` 行的 `history=N` 给当前条数，按增长比例估现值即可（混合中英 ≈ 1.5–1.6 字符/token）
- 两条阈值别混：`Preflight` 那条是「历史闲置后重开」的 120K 前置阈值；`Pre-API` 那条才是硬阈值 = `compression.threshold: 0.5` × 窗口

**答复口径（用户问「是不是满了 / 要不要清理」时直接给这三行）**：① 当前约多少 tokens、占窗口百分之几 ② 压缩阈值是多少、什么时候触发 ③ 上次自动压缩在何时、从多少压到多少。**低于 30% 就明说「没满、不用清」，不要为了显得勤快去做有损的会话归档**——用户要的是判断不是动作；也别说「520 条消息太多了」，条数本身不是指标，tokens 占窗口才是。

**整理手段与顺序**：先修 memory 超限（零风险、可验证），再动会话（有可用性风险）。
- 会话归档/改名：`hermes -p <name> sessions rename|archive ...`（有 `--dry-run`、`--title` 过滤）
- ⚠️ 用户固定用 `hermes -p <name> chat -c "Bot Chat"` 续聊时，改名/归档后 `-c` 找不到同名会话的行为**必须先实测**（必要时补 `--create-if-missing`），否则助理直接起不来
- 能无损清空的前提：所有结论已落盘到工作目录文件（健康域 `~/health/diet|records|reviews`），会话历史只是冗余——这条要主动说给用户，他才会同意归档

详细查询脚本 + 本次基线数字见 `references/profile-context-audit.md`。

### 🔴 2026-11-13 复做：把「当前到底多少 tokens」从估算换成实算（三个抓手）

上一节只给到「按增长比例估」。2026-11-13 又查一次健康助理，摸到三个能把误差压掉的抓手，**优先级从高到低**：

1. **直接调 Hermes 自己的估算器，别手算字符比。** 判阈值用的是同一个函数，调它＝口径一致：
   ```python
   import sys; sys.path.insert(0, r'C:/Users/<u>/AppData/Local/hermes/hermes-agent')
   from agent.model_metadata import estimate_messages_tokens_rough as est
   # 从 state.db 取 active=1 的消息 → [{'role':..,'content':..}] → est(msgs)
   ```
   ⚠️ **本 skill 旧文写的「混合中英 ≈ 1.5–1.6 字符/token」会高估**：本次 348,105 字符估出 176,227 tokens（**≈1.98 字符/token**），估算器还含每条的固定开销。**字符比只能当粗筛，出结论前必须用 `est()` 过一遍。**
2. **`agent.log` 里的 `tool_search` 延迟加载行＝工具定义的真实开销。**
   ```
   tools.tool_search: tool_search activated (tier 1): 17 core/visible tools kept, 124 deferred (~38581 tokens), listing full (budget ~4000 tokens)
   ```
   → 工具这块 = 常驻 17 个 + 目录 ~4,000，**别按 MCP 注册的 103 个工具全量算**（那样会凭空多出 3–4 万 tokens，把 19% 说成 25%）。
3. **压缩健康度看 sessions 的三个字段，不看有没有报错**：`compression_failure_streak` / `compression_ineffective_count` / `compression_failure_cooldown_until`，全 0 或 None = 压缩链路正常，没触发只是因为没到线。

🔴 **`hygiene_hard_message_limit` 是「网关会话」专用的强制压缩线，CLI 会话不适用。**
本次 `sessions.message_count=418` > 配置里的 `400`，一度以为漏压。查源码确认：它在 `gateway/run.py:21718` 读取、默认值 **5000**（`hermes_cli/config_defaults.py:955`），只作用于微信/Telegram 这类网关会话。健康助理是 `source='cli'` → **418 > 400 是正常状态，不是 bug**。
→ 但反过来要提醒用户：**把这个 bot 挂到网关那天，400 会立刻变成强制压缩线**，届时要调高或接受更频繁的有损压缩。

🔴 **两个 schema 坑（踩过）**：`sessions` **没有 `created_at`**（用 `started_at` / `last_activity_at`，都是 epoch 秒）；`messages.token_count` **全是 NULL**，算长度只能用 `length(content)`。

## 九、额度百分比与缓存命中率：两个固定判读口径（2026-11-08 实测）

### 🔴 额度百分比是「订阅周期」不是「自然月」

opencode console 右上角那个 `Go NN% used`，**起点是订阅日（本例 2026-10-16）**，不是每月 1 号。
别看到「本月才过 8 天就用掉 68%」就去 alarm——先确认/询问订阅起始日，再按天折算：

```
日均% = 已用% ÷ (今天 − 订阅起始日)      本例 68 ÷ 23 天 = 2.96%/天
推到周期末 = 日均% × 30                → 88.7%
剩余里程天数 = (100 − 已用%) ÷ 日均%      → 约 10.8 天
```

判据：**剩余里程 < 7 天才是真警报**；剩 8–15 天属于「紧但够」，只需点一句中后期别爆量。
（用户 2026-11-08 当场补正了这一点——我先按自然月算错了一版。）

### 缓存命中率：先算分母，再拿基线比

```
命中率 = cache_read_tokens ÷ (input_tokens + cache_read_tokens)
```
`input_tokens` 已是「未命中」口径，与 cache_read **并列相加**，不是包含关系。

| 口径（2026-11 MTD 实测） | 命中率 |
|---|---|
| 健康 profile（单会话 444 次调用、上下文连续复用） | **98.52%** |
| 主 profile（50 个会话，碎） | **93.89%** |
| opencode console 全账号（3,162 请求） | **94.99%** |

**98% 不是空想——同机就有证据**；低于 95% 必须能解释。本机拉低平均的是 `background_review`：
20 个会话 / 314 次调用，命中 **90.3%**、未命中均值 **15.1K/次**（每个会话都从头开上下文）；
`title_generation` 命中只有 36%，但每次 0.3K，量小可忽略。
→ **结论方向：不是配置问题，是会话碎不碎的问题**（长任务同会话做完、别中途 `/new`）。

**成本敏感度**（DeepSeek V4.1 Flash Off-Peak：in 0.15 / cache 0.003 / out 0.60 $/M）：
- 未命中那 5% 的 token 吃掉**输入成本的 73%**，缓存读 95% 的 token 只占 27%
- **每提升 1 个百分点 ≈ 省 $0.65/月**；95%→98% 约省 $2/月
- 自证口径的办法：全 Off-Peak / 全 Peak 各算一遍，再与实际账单反推峰段占比（本机实测 ≈27%，与工作日 9–12/14–18 峰段吻合）

## 🔴 aux 视觉调用 MissingSessionID：识图会静默换模型（2026-11-08）

**症状**：用户发现「识图没走 minimax-m3，都用主模型了」。
**根因**：`agent/opencode_affinity.py` 的 `opencode_session_headers()` 在拿不到会话 ID 时返回 `{}`；
而网关的**图片预分析跑在主对话绑定上下文之前**，`_runtime_main_value("session_id")` 为空 →
不带 `x-opencode-session` → opencode 400 `MissingSessionID` → **静默退回主模型识图**。
**判别**：`grep -ai "MissingSessionID" ~/.hermes/logs/agent.log`——每条 `Image routing: text … Pre-analyzing`
后面紧跟 400 就是它。用 curl 对 `/zen/go/v1/messages` 试两次（带 / 不带头）即可证实是头的问题、不是模型不可用。
**修法**：key 为空时回落到一个进程内稳定的 fallback 键（`hermes-aux-<hex16>`），保证该头永不为空；
非 opencode 目标仍返回 `{}`（不能误伤其它供应商）。**改完需重启 gateway 才生效**；
消息平台会话里不自己 stop/start，让用户发 `/restart`。
**顺带**：Anthropic 协议的 opencode 端点认证走 **`x-api-key`**；用 `Authorization: Bearer` 会报 `Go requires a credential`。

## 参考数据

- `references/profile-context-audit.md` — **profile 级上下文审计**：只读查 state.db 的完整脚本、按工具来源拆字符占比、从 `models_dev_cache.json` 取模型窗口、2026-10-31 健康助理实测基线；**2026-11-13 新增：用 `estimate_messages_tokens_rough` 实算当前 tokens（取代字符比估算）、`tool_search` 延迟加载行的真实工具开销、压缩节奏与健康度字段、`hygiene_hard_message_limit` 网关专用误报排除、三处 schema 坑**
- `scripts/opencode_go_quota_rank.py` — **可直接跑的额度占用排名**（读 state.db + 内置价格表，同时输出「30 天实际」与「活跃日外推」两套口径、最重一天 vs 5h 上限）。选型第一步先跑它
- `scripts/model_probe.py` — **候选模型的「双探针」体检**（工具调用 + 流式长文本吞吐），判据 3/4 的落地实现。已内置 curl / `User-Agent: curl/8.0.0` / `x-opencode-session` / `stream:true` 四个必需姿势，换主力前对每个候选跑一遍：`python model_probe.py <模型ID> ...`
- `scripts/extract_aa_scores.py` — **AA 逐模型分项分数提取器**。AA 的图表数字在正文里取不到（客户端渲染），必须从内嵌 JSON 挖，本脚本已封装两种 Next.js JSON 源 + 内置候选模型过滤：
  ```bash
  python extract_aa_scores.py                        # 默认抽 AutomationBench-AA 页
  python extract_aa_scores.py --all --breakdown      # 全部模型 + AutoBench 明细
  python extract_aa_scores.py --url <AA页面> --models deepseek glm
  ```
  ⚠️ AA 会为同一模型建多条独立记录（如 `DeepSeek V4.1 Flash` 与 `DeepSeek V4.1 Flash 1017` 分数不同）——**选型时别把版本混为一谈**。

> ⚠️ **双探针里的 `model_probe.py` 只支持 OpenAI 兼容协议**。Claude Haiku 5.5 / Qwen / MiniMax 这类走 Anthropic 协议的模型会报
> `ModelProtocolUnsupported`——**那是协议不对，不是模型不可用**。改用 `/zen/go/v1/messages` + `x-api-key` + `anthropic-version: 2023-06-01` 头。
> 详见 skill `hermes-china-providers` 的「协议分裂」节。
- `references/model-strength-vs-quota-2026-10.md` — **「有没有更强的模型且不超限额」的完整实测**：AA 总分/分项对比表、双口径占用排名、长文本吞吐探针结果、逐候选否决理由（2026-10-08）
- `references/opencode-go-quota-selection-2026-10.md` — **2026-10-08 现抓官方 Go 定价表 + 本机用量画像 + 逐模型性价比排名 + 工具调用探针结果**（选型直接看这份；比下面 8 月那份新）
- `references/opendesign-plans-2026-10.md` — **OpenDesign（open-design.ai）四档价格/额度表、哪些模型在哪个档位 `Not included`、Opus 5.5 换算、与 Claude 官方 Pro 的口径差异**（2026-10-25 现抓；问聚合站套餐时直接看这份）
- `references/claude-plans-2026-11.md` — **Claude 官方订阅全套现行数字（2026-11-09 现抓 + 79 账号实测）**：Pro/Max/Ultra 改名与价格、相对倍数、`Monthly API credits` 哪档有哪档没有（决定能不能接 Hermes）、usage credits 撞限续用规则、Pro 每周 $155/**月 $673/34 倍**的实测区间与漂移记录、SemiAnalysis 受控测试口径、Opus 5.5 单价全表、5h 窗口换调用次数的公式。**问「Claude Pro 额度多少 / 订阅和聚合站谁划算」先看这份**
- `references/aggregator-plans-kilo-opendesign-2026-11.md` — **Kilo Pass 与 OpenDesign Pro 的 Opus 5.5 换算实测（比上面那份新）**：Opus 5.5 官方单价全表、Kilo Pass 三档充值机制与 bonus 领取条件、OpenDesign 四档哪档开 Opus 5.5、两家杠杆率对比、本机近 30 天用量新基线（每次 $0.070、月用量换 Opus 需 $581）与 HTML 解析坑
- `references/opencode-go-2026-08.md` — OpenCode Go 完整 18 模型定价表、额度机制、DeepSeek 8/17 涨价细节、本机用量画像与分情景测算结果（可直接复用数值）
- **2026-08-31 官方用量页实测画像**（scode.ai/workspace，半月周期）：5h 9.6% / 周 6.1% / 月 18.2%；模型级 = Flash $4.71/$30（17.9%，绝对主力）· qwen3.7-max $0.10/$60（0.2%）· 其余 <$0.02。含义：① 高峰负载也远不撞 5h 墙；② **同一 qwen3.7-max 走 OpenCode 网关近乎免费**（对比 qwen-bailian 直连烧钱，审查/兜底链路可迁移）；③ 月外推 ~36%，仍处"随便用"档
