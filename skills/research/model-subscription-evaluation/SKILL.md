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

## 参考数据

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
- `references/opencode-go-2026-08.md` — OpenCode Go 完整 18 模型定价表、额度机制、DeepSeek 8/17 涨价细节、本机用量画像与分情景测算结果（可直接复用数值）
- **2026-08-31 官方用量页实测画像**（scode.ai/workspace，半月周期）：5h 9.6% / 周 6.1% / 月 18.2%；模型级 = Flash $4.71/$30（17.9%，绝对主力）· qwen3.7-max $0.10/$60（0.2%）· 其余 <$0.02。含义：① 高峰负载也远不撞 5h 墙；② **同一 qwen3.7-max 走 OpenCode 网关近乎免费**（对比 qwen-bailian 直连烧钱，审查/兜底链路可迁移）；③ 月外推 ~36%，仍处"随便用"档
