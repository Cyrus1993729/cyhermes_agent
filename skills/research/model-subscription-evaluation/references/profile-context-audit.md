# Profile 级上下文审计（2026-10-31，健康助理实做）

用户说「检查一下 X 助理的上下文，如果过长就整理一下」时的完整做法。

## 0. 路径与前提

| 东西 | 主 profile | 其它 profile |
|---|---|---|
| 会话库 | `~/AppData/Local/hermes/state.db` | `~/AppData/Local/hermes/profiles/<name>/state.db` |
| 配置 | `hermes/config.yaml` | `profiles/<name>/config.yaml`（含 `memory.memory_char_limit`）|
| 记忆 | `hermes/memories/` | `profiles/<name>/memories/` |
| 日志 | `hermes/logs/agent.log` | `profiles/<name>/logs/agent.log` |

**本机没有 `sqlite3` 命令行** → 一律用 Python 标准库 `sqlite3`，并以 URI 只读模式打开（`file:...?mode=ro`），避免锁住正在跑的 gateway / serve 进程。

## 1. 找活跃会话 + 上下文规模

```python
import sqlite3
p = r"C:\Users\Administrator\AppData\Local\hermes\profiles\health\state.db"
con = sqlite3.connect(f"file:{p}?mode=ro", uri=True); cur = con.cursor()

# 最近的会话（hidden=1 通常是 bot 模式的常驻会话）
for r in cur.execute("""select id, source, message_count, tool_call_count,
   input_tokens, output_tokens, title, last_activity_at, hidden
   from sessions order by last_activity_at desc limit 15"""):
    print(r)

# 每个模型的口径（task='compression' 的行 = 压缩调用）
for r in cur.execute("""select session_id, model, task, api_call_count,
   input_tokens, output_tokens, cache_read_tokens
   from session_model_usage order by rowid desc limit 10"""):
    print(r)
```

**关键换算**：`cache_read_tokens / api_call_count` = 平均每次调用重放的 prompt tokens。
健康助理实测：`16,552,832 / 126 ≈ 131,000 tokens/次`，即「这个会话每说一句话都要重放 13 万 token」。

## 2. 判断有没有压缩过

```python
sid = '20261029_101937_81e395'
rows = cur.execute("""select role, active, compacted, length(coalesce(content,''))+length(coalesce(tool_calls,''))
   from messages where session_id=? order by id""", (sid,)).fetchall()
print("总条数", len(rows), "未压缩字符", sum(r[3] for r in rows if r[1] == 1))
```

- `active=1, compacted=0` 全为 0 → 这个会话从未被压缩
- 再查 `select compression_ineffective_count, compression_fallback_streak, compression_failure_error from sessions where id=?`
- `session_model_usage` 里没有 `task='compression'` 的行 = 压缩引擎一次都没触发过

## 3. 谁在吃上下文（按 role + tool_name 拆）

```python
import collections
byt, cnt = collections.Counter(), collections.Counter()
for role, tn, lc, tc in cur.execute("""select role, coalesce(tool_name,''),
   length(coalesce(content,'')), length(coalesce(tool_calls,'')) from messages where session_id=?""", (sid,)):
    k = role if role != 'tool' else f"tool:{tn}"
    byt[k] += (lc or 0) + (tc or 0); cnt[k] += 1
for k, v in byt.most_common(12):
    print(f"{k:18s} {v:8d} chars ({cnt[k]} 条)")
```

**健康助理 2026-10-31 实测画像**（272 条 / 485,579 字符 ≈ 16 万 tokens）：

| 来源 | 字符 | 占比 |
|---|---:|---:|
| assistant 自己的回复 | 173,413（127 条）| 35% |
| tool:terminal | 120,412（62 条）| 24% |
| tool:read_file | 69,309（13 条）| 14% |
| tool:patch | 38,637（27 条）| 7% |
| tool:skill_view | 26,511（2 条）| 5% |
| tool:web_extract | 21,508（2 条）| 4% |
| user | 11,157（10 条）| 2% |

可砍的优先级：**大文件整读**（38KB 的 `profile.md` 读了多遍）> terminal 全量输出 > 助手自己的长回复。

## 4. 模型窗口对照

```python
import json
d = json.load(open(r"...\profiles\health\models_dev_cache.json", encoding="utf-8"))
# 递归找 model id，读 limit.context
```

实测：`deepseek-v4.1-flash` = 1,000,000；`gpt-6-luna` = 1,050,000。
→ 16 万 tokens 只占窗口 16%，**不是「会崩」，是「每次调用都慢且重」**。结论要把这两件事分开说。

## 5. 时间分布（找出暴涨点）

```python
for r in cur.execute("""select strftime('%m-%d', datetime(timestamp,'unixepoch','+8 hours')) d,
   count(*), sum(length(coalesce(content,''))+length(coalesce(tool_calls,'')))
   from messages where session_id=? group by d order by d""", (sid,)):
    print(r)
```

实测：10-29 只有 2 条，**10-30 一天 270 条 / 48.5 万字符**——单日暴涨才是要动的信号。

## 6. 整理动作与风险

1. **先修 memory 超限**（零风险）：对比 `len(MEMORY.md)` 与该 profile config 的 `memory.memory_char_limit`。健康 profile 实测 3403 vs 2200，超 55% → 长期写不进记忆（静默失败）。压缩到限内，细节搬进 skill/references。
2. **再动会话**（有风险）：`hermes -p <name> sessions archive --title "Bot Chat" --yes` 或 `rename`。
   🔴 **动之前必须确认用户是怎么启动这个 bot 的**。固定姿势是 `hermes -p health chat -c "Bot Chat" -Q --query-file ...`；改名/归档后 `-c` 匹配不到同名会话时的行为要先实测（必要时加 `--create-if-missing`），否则助理起不来。
3. **归档是否无损**：所有结论是否已落盘到工作目录（健康域 `~/health/diet|records|reviews`，共 78 个文件）。落盘了 = 会话历史只是冗余，可以放心归档；这点要主动讲给用户，他才肯同意。
4. 顺带检查该 profile 的 `skills/` 下 SKILL.md 大小（本次 `meal-photo-analysis` 32KB / `health-analysis` 15KB，尚可；主 profile 的 `health-nutrition-analysis` 已 108KB，属超限需拆分那类）。

---

# 2026-11-13 复做：当前上下文实算 + 压缩健康度

第二次被问「健康助理的上下文要不要压缩」。上面第 1–5 节的估算法已被本节取代，**优先用这一套**。

## A. 一条命令把「当前 tokens」算准

```python
import sys, sqlite3
sys.path.insert(0, r'C:/Users/Administrator/AppData/Local/hermes/hermes-agent')
from agent.model_metadata import estimate_messages_tokens_rough as est   # 判阈值用的同一个函数

p  = r'C:/Users/Administrator/AppData/Local/hermes/profiles/health/state.db'
sid = '20261104_114345_190ce9'          # 先按 last_activity_at desc 取
con = sqlite3.connect(f'file:{p}?mode=ro', uri=True)
rows = list(con.execute('select id,role,content from messages where session_id=? and active=1 order by id', (sid,)))
msgs = [{'role': r[1], 'content': r[2] or ''} for r in rows]
print(len(msgs), est(msgs))

# 拆开看：压缩摘要 vs 其余
summary = [m for m, r in zip(msgs, rows) if r[0] == 5630]
print('摘要', est(summary), '其余', est([m for m, r in zip(msgs, rows) if r[0] != 5630]))
```

**2026-11-13 健康助理实测**：418 条 active / 348,105 字符 → **176,227 tokens**（≈1.98 字符/token），其中
压缩摘要 1 条 = **28,905**、其余 417 条 = **147,322**（tool 结果 201,057 字符是大头）。

⚠️ 别再用「字符 ÷ 1.5~1.6」估——会高估 30% 以上。

## B. 另外三块固定开销（不在 messages 里，容易漏算）

| 项 | 取法 | 实测 |
|---|---|---|
| 系统提示 | `sessions.system_prompt` 或日志里 `Compaction rebuilt a drifted system prompt (… 16858 chars)` | ~4,215（16,858 字符）|
| Memory + 用户画像 | `memories/MEMORY.md` + `USER.md` 的 `wc -c` | ~1,089（2,601 + 1,754）|
| 工具定义 | 日志 `tools.tool_search: … 17 core/visible tools kept, 124 deferred (~38581 tokens)` | 常驻 17 个 + 目录 ~4,000（**别按 103 个 MCP 工具全量算**）|

合计 ≈ **19 万 / 1,000,000 = ~19%**。

## C. 压缩历史与节奏（grep 一次拿全）

```bash
grep -aiE "Pre-API compression|context compression done|Compression budget rearmed" \
  ~/AppData/Local/hermes/profiles/<name>/logs/agent.log
```

健康助理实测节奏：**11-07 / 11-09 / 11-11 各压一次**，每次 50.0–50.2 万 → **8.0–9.1 万**（71–105 条），耗时 82–113 秒。
→ **约 2 天压一次**，是自动行为；报结论时给「还剩多少 tokens 到线 + 折合几天」比给百分比更有用。

## D. 压缩健康度 / 误报排除

```python
cols = ['compression_failure_cooldown_until','compression_failure_error',
        'compression_fallback_streak','compression_ineffective_count','compression_recovery_deadline']
# 全 None / 0 → 压缩链路正常，没触发只是因为没到线
```

🔴 **`hygiene_hard_message_limit` 只作用于网关会话，CLI 不适用。**
本次 `message_count=418` > 配置 `400` 但没压——源码确认它在 `gateway/run.py:21718` 读取、默认 **5000**
（`hermes_cli/config_defaults.py:955`），`source='cli'` 的会话不走这条。**418 > 400 是正常，别报成漏压。**
反过来要主动提示：**该 bot 若改挂微信/Telegram，400 立刻变成强制压缩线。**

## E. schema 坑

- `sessions` **没有 `created_at`** → 用 `started_at` / `last_activity_at`（epoch 秒）
- `messages.token_count` **全是 NULL** → 长度只能用 `length(content)`
- 消息列是 `active` + `_compressed_summary`（**不是 `compacted`**，写错直接 `no such column`）

## F. 答复口径（用户问「需不需要压缩」时）

三行给完就够：**① 当前约 X tokens / 窗口 Y（~Z%）；② 触发线多少、还差多少；③ 上次压缩何时、从多少压到多少、约几天后下次触发。**
低于 30% 就明说「不需要压」，然后给可选项（调低 `compression.threshold`）让他拍板——**别自行动手做有损压缩**。
