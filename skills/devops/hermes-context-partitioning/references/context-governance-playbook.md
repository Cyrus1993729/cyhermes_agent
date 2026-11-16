# 长寿命 profile 的上下文治理（四层 playbook）

用户说「他的上下文是不是该压缩了」「他反应变慢、聊得越久越久，但不会主动提醒我」
「你帮我把这套管起来，别让我时刻盯着」时加载。

**这是 `canonical-bot-chat-compaction.md` 的上位框架**：那篇讲「怎么手动压一次」，
这篇讲「怎么让它长期不用人管」。

> 状态说明（2026-11-13）：第 1/2 节的**测量口径与配置语义**全部来自源码核实 + 真实库数据，
> 可信；第 5 节的四层框架是**已提出、尚未实施验证**的方案，实施后请回来补实测数字。

---

## 一、先纠正用户的默认假设

用户几乎总是把问题描述成「是不是该压缩了」。**压缩通常不是延迟主因**，
但「prompt 太长所以慢」这个替代解释**同样不能直接下结论**——2026-11-13 实测把它推翻了一半。

### 🔴 延迟归因必须实测，不能靠推理（2026-11-13 定论）

拿 agent.log 里每一行 `API call #N: in=… out=… latency=…s cache=a/b` 做**双桶对照**：

```python
import re, statistics
txt = open('logs/agent.log', encoding='utf-8', errors='replace').read()
pat = re.compile(r'API call #\d+: .*? in=(\d+) out=(\d+) .*?latency=([\d.]+)s', re.M)
rows = [(int(a), int(b), float(c)) for a, b, c in pat.findall(txt)]

# 桶 1：固定输出量（out<=300），只看 prompt 规模对延迟的影响
for lo, hi in [(0,50000),(50000,150000),(150000,250000),(250000,400000),(400000,600000)]:
    sel = [r[2] for r in rows if lo <= r[0] < hi and r[1] <= 300]
    if sel: print(f'prompt {lo//1000}K-{hi//1000}K: {len(sel)} 次, 延迟中位 {statistics.median(sel):.1f}s')

# 桶 2：按输出量分桶
for lo, hi in [(0,100),(100,300),(300,800),(800,2000),(2000,99999)]:
    sel = [r[2] for r in rows if lo <= r[1] < hi]
    if sel: print(f'out {lo}-{hi}: {len(sel)} 次, 延迟中位 {statistics.median(sel):.1f}s')
```

**health profile 实测结果（2026-11-13，1,624 次调用）**：

prompt 规模 → 延迟中位（筛 out≤300 控制变量）：
0–5 万 5.5s ｜ 5–15 万 4.0s ｜ 15–25 万 4.7s ｜ 25–40 万 5.1s ｜ 40–60 万 **5.6s**

输出规模 → 延迟中位：
0–100 **4.2s** ｜ 100–300 5.5s ｜ 300–800 7.2s ｜ 800–2000 11.5s ｜ 2000+ **21.4s**

→ **prompt 从 15 万涨到 50 万，单次只多约 0.9 秒；输出从 <100 涨到 >2000，单次多 17 秒。**
缓存命中 99–100% 时 prefill 基本免费，**延迟由输出 token 数主导，不是 prompt 长度**。

### 所以真正的延迟公式是

```
每轮等待 ≈ 每轮 API 调用次数 × 每次延迟(输出 token 数主导) + 工具执行时间
```

health profile 实测：**每轮 API 调用中位 13 次（最大 47）**、单次中位 6.8s
→ 一轮 ≈ 88 秒纯 API 等待。**上下文长度只解释其中约 12 秒（0.9s × 13）。**

### 结论口径（三句话，按这个顺序说）

1. **压缩不是主因**（一年约 180 次 × 80–115s，摊到上千次调用里占比很小）
2. **prompt 长度也不是主因**（实测 15 万→50 万只多 0.9s/次）
3. **主因是一轮任务要串行调多少次模型**（中位 13 次），其次是每次输出多少 token

→ 优化顺序：**先减调用次数（工具批量化 / 核算脚本化）> 再压输出量 > 最后才是上下文**。
上下文治理仍值得做（省 ~12 秒/轮 + 消掉 90 秒压缩停顿 + 避免撞线），
但**别把它当第一杠杆卖给用户**——做完他会发现没快多少。

🔴 **老口径「延迟来自每轮重放的 prompt 长度」已作废**，不要再用。
另外「压缩一年只几十次」也算错了：2 天一次 ≈ **每年 180 次**。

## 二、三个诊断口径（三个都对得上再下结论）

### ① 平均每轮 prompt —— 最接近「变慢」的量化指标

```python
import sqlite3
p = r"...\profiles\<profile>\state.db"
con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
# task='' 是主对话；'compression' / 'vision' 是辅助调用，别混进来
print(con.execute("""select api_call_count, cache_read_tokens
                       from session_model_usage
                       where session_id=? and task=''""", (sid,)).fetchone())
# 平均 prompt ≈ cache_read_tokens / api_call_count（缓存读按整段 prompt 计）
```

**实测基准（health profile，2026-11-13）**：968 次调用 / 2.597 亿 cache_read
→ **平均每轮 26.8 万 tokens**。这就是用户口中「变慢」的真身。

### ② 当前活跃上下文 —— 用 Hermes 自己的估算器，别手算

```python
import sys, sqlite3, json
sys.path.insert(0, r"C:/Users/<user>/AppData/Local/hermes/hermes-agent")
from agent.model_metadata import estimate_messages_tokens_rough as est

c = sqlite3.connect(db)
rows = c.execute("select role, content, tool_calls, tool_call_id, reasoning_content "
                 "from messages where session_id=? and active=1 order by id", (sid,)).fetchall()
msgs = []
for role, content, tc, tcid, rc in rows:
    m = {"role": role, "content": content or ""}
    if tc: m["tool_calls"] = json.loads(tc)      # ← 千万别漏
    if tcid: m["tool_call_id"] = tcid
    if rc: m["reasoning_content"] = rc           # ← 也别漏
    msgs.append(m)
print(est(msgs))
```

🔴 **只统计 `content` 会严重低估——实测低估 2.4 倍。**
2026-11-13 health profile 实测（同一批 418 条 active 消息）：

- 只 `content`：348,105 字符 → 估 **176,227 tokens**（← 当时报给用户的就是这个，错的）
- 加 `tool_calls`（助手写文件/改文件的参数，**376,517 字符，比 content 还大**）→ **257,617**
- 再加 `reasoning_content`（121,313 字符）→ **303,510**

而 agent.log 里同期的真实 `in=` 是 **342,144 ~ 348,190**。
→ **上下文规模一律以 agent.log 的 `in=` 为准，DB 估算只当旁证。**

🔴 **中文 ≈ 2 字符/token，不是 4。** 按 `len/4` 估会把中文会话低估一半，结论直接反掉。

### ③ 上下文构成 —— 按 role 拆，才知道谁在吃

```sql
select role, count(*), sum(length(coalesce(content,'')))
from messages where session_id=? and active=1 group by role;
-- 另外单独看压缩摘要：_compressed_summary=1 的那些
```

**实测基准（health profile 当前窗口 348,105 字符）**：
工具回显 193 条 / 201,057 字符 = **58%**；助手回复 209 条 / 61,604 = 18%；
用户输入 16 条 / 30,521 = 9%；压缩摘要 1 条 / 54,923 = 16%。

→ **工具回显是最大且最可回收的一块**，且它是「一次性」的（读完就该扔）。

### ④ 顺带：工具定义的 token 成本在日志里白给

```
grep "tool_search activated" logs/agent.log
tools.tool_search: tool_search activated (tier 1): 17 core/visible tools kept,
                   124 deferred (~38581 tokens), listing full (budget ~4000 tokens)
```

MCP 挂一堆 server 的 profile，这条能直接告诉你「工具定义省了多少」。本例省了 3.8 万/次。

---

## 三、三个杠杆与取舍

| 杠杆 | 触发方式 | 单次成本 | 破坏性 |
|:--|:--|:--|:--|
| **主动剪枝** `proactive_prune_tokens` | 超过阈值自动 | **无 LLM、秒级** | 破坏一次 prompt cache；内容可 `session_search` 找回 |
| **全量压缩** `threshold` / `threshold_tokens` | 超过阈值自动 | LLM 摘要 80–115s | 破坏全部 cache；旧消息 `active=0` 保留可搜 |
| **派活纪律**（写进 skill） | 无 | 无 | 无 |

性价比排序：**派活纪律 > 主动剪枝 >> 全量压缩**。
日常靠剪枝，全量压缩只当兜底。

---

## 四、🔴 最大的坑：主动剪枝的默认参数，对聊天/分析场景等于没开

配置长这样（`hermes_cli/config_defaults.py`，compression 段）：

```yaml
compression:
  threshold: 0.5                  # 占窗口比例
  threshold_tokens: null          # 绝对上限，实际触发 = min(比例阈值, 本值)
  target_ratio: 0.2
  protect_last_n: 20
  protect_first_n: 3
  in_place: true                  # false = rotation，canonical bot 灾难
  proactive_prune_tokens: 0       # 0 = 关。开它！
  proactive_prune_min_result_chars: 8000   # ← 陷阱在这
  proactive_prune_min_reclaim_tokens: 4096
```

### 陷阱的机理

`agent/context_compressor.py::_prune_old_tool_results` 里：

```python
if len(content) <= min_prune_chars:   # line ~4310
    return False
```

`proactive_prune_min_result_chars` 被 clamp 到 `>= _PRUNE_MIN_CHARS = 200`（line ~876）。
**默认 8000 是给编码场景调的大输出**。聊天/核算场景的工具回显中位数只有几百字符：

实测（health profile 193 条工具回显）：

- `> 8000 字符`：**只有 1 条**（15,097 字符，占 8%）
- `> 2000 字符`：26 条，占 52%
- `> 200 字符`：163 条，占 **98%**
- 中位数 379 字符，均值 1,041 字符

→ **照默认值开，等于只剪得动 1 条，回收率接近 0。必须降到 200。**

### 推荐配置（聊天/分析型 profile）

```yaml
compression:
  proactive_prune_tokens: 48000            # 4.8 万就剪
  proactive_prune_min_result_chars: 200    # 关键：从 8000 降到下限 200
  proactive_prune_min_reclaim_tokens: 4096 # 保持默认，让剪枝「隔一阵一次」而非每轮
  threshold_tokens: 200000                 # 全量压缩从 50 万降到 20 万兜底
  in_place: true
```

**预期效果（按字符推算，未实测）**：198K 字符工具回显压成约 16K 字符，
上下文 176K → 约 83K tokens，砍掉一半。

⚠️ 每次剪枝会重写已发出的历史、破坏一次 prompt cache（那一轮全价）。
`proactive_prune_min_reclaim_tokens` 的闸门就是为摊薄这个成本而存在的，别关。

---

## 五、四层治理框架（用户要「不用我盯」时的标准答案）

> 2026-11-13 提出，**尚未实施**。实施后补实测数字。

### L1 存储规范 —— 让数据不依赖对话

症状（health profile 实测）：`profile.md` 42,224 字符（≈2.1 万 tokens，14 个章节，
被整篇读）；`diet/` 26 个日文件单日 1.4–4 万字符；`tools/` 404 个文件 12MB 全是
`_bak_*` / `_anchor_*` 临时脚本，污染 `ls` 与搜索。

规范：

- **索引层**：每个领域目录一个 `INDEX.md`（各目录放什么 / 当前基线在哪 / 最近三条结论 /
  常用脚本入口），新会话先读它再决定读什么
- **基线层**：大档案拆成「现行口径 ≤8KB」+ `archive/<name>_history.md`（历史决策，
  **作废方案标 ❌ 并保留原文**，防重建会话后被旧方案带偏）
- **日志层**：每个日文件顶部加 **15 行机器可读摘要头**（日期/热量/三大营养素/钠/赤字/状态/结论），
  agent 默认 `read_file limit=20` 只读头
- **报告层**：`reviews/*.md` 顶部 8 行结论块
- **原始层**：扫描件、截图文字，只增不改
- **工具层**：正式脚本 vs `_scratch/` 临时脚本分离，临时件 30 天自动清

### L2 上下文配置 —— 见第四节

### L3 派活纪律 —— 写进领域 skill，不靠用户记

实测一次带工具的派活 ≈ **+3~5 万 tokens**（吃进来的是工具回显，不是对话）。
三条规矩：

1. 一次派活只做一件事（记早餐 / 记运动 / 算赤字拆成三次，工具轮数翻倍）
2. 禁止整篇 `read_file` 大档案，按章节读
3. 优先读日文件的摘要头，不读正文

### L4 静默监测 —— 只在红线响

`no_agent` 纯脚本 cron，每天固定时点静默体检，**不满足条件就什么都不发**。

告警红线（任一条命中才推一条消息）：

- 当前上下文 > 30 万 tokens（说明剪枝/压缩失效）
- `compression_failure_streak > 0`
- memory 使用率 > 85% of `memory_char_limit`
- 距上次活动 > 7 天且上下文 > 20 万（闲置胖会话）

这才是「平时不吵、出事才说一句」。**别做成每日汇报**——用户明确说过不要。

---

## 六、🔴 `hygiene_hard_message_limit` 只对 gateway 会话生效

配置里 `compression.hygiene_hard_message_limit: 400` 看着像「超过 400 条强制压缩」，
**但它只作用于 gateway（Telegram/微信等）会话的 session hygiene**，CLI 会话不适用。

实测：health profile 的 `Bot Chat` 是 `source='cli'`，活跃 418 条 > 400，**没有触发任何压缩**，
这是对的。

⚠️ 但**如果哪天把这个 profile 挂到 gateway**，这条会立刻变成强制压缩线——
届时要么调高它，要么接受更频繁的压缩。给用户讲方案时要点出来。

---

## 七、汇报口径

- 先说**结论**（「现在不需要压缩 / 需要，因为 X」），再上数字，别倒过来
- 每个数字标来源（state.db / agent.log / config.yaml），用户会核对
- 给方案时**列清代价**：剪枝破坏 cache、压缩要 80–115 秒、太频繁反而更慢
- 用户要的是「不用我盯」，所以**主动给监测层**，并明确「不达标不推送」
- 需要拍板的点要收敛成 2–3 个具体选项（参数值 / 改造深度 / 告警红线），
  别问「你想怎么管」这种他判断不了的开放题
