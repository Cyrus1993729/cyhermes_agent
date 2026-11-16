# 给 canonical Bot Chat 瘦身：为什么 rename / archive 都不行，只有压缩

一个独立 profile（= 一个 bot）聊久了，`Bot Chat` 会话会越积越重：每轮调用都要重放
十几万 tokens。2026-10-31 在 health profile 上完整走过一遍，结论和坑都在这里。

## 一、先量化，别凭感觉说「太长了」

```python
import sqlite3
p = r"...\profiles\<profile>\state.db"
con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)   # 只读，避免抢锁
cur = con.cursor()
cur.execute("""select id,title,message_count,tool_call_count,input_tokens,output_tokens,
               cache_read_tokens,compression_ineffective_count
               from sessions order by last_activity_at desc limit 10""")
# 每次调用的真实 prompt ≈ cache_read_tokens / api_call_count（缓存读按整段 prompt 计）
```

- **日志更直接**：`logs/agent.log` 里搜 `Preflight compression`，会打印
  `~218,615 tokens >= 120,000 threshold (model ..., ctx 1,000,000)`——这是官方估算，比自己数准。
- **按来源拆字符数**，才知道谁在吃上下文。实测占比：assistant 自己的回复 35%、
  terminal 输出 24%、read_file 14%（把 38KB 的档案整篇读了好几遍）、patch 7%。
- **当前活跃上下文别手算**：用 Hermes 自己的估算器 `agent.model_metadata.estimate_messages_tokens_rough`
  （把 `hermes-agent` 加进 `sys.path` 即可 import）。🔴 **中文 ≈ 2 字符/token，按 `len/4` 估会低估一半**，
  结论直接反掉。写法见 `references/context-governance-playbook.md` 第二节。
- 模型窗口查 `models_dev_cache.json`（`limit.context`），别拿旧印象套。

## 二、三个坑（全部实测，别再踩）

1. **`hermes sessions rename <id> "新名"` 对 canonical Bot Chat 直接被拒**：
   > `Error: This is the bot's canonical Bot Chat — its name is its identity, and renaming it would orphan the conversation. To start fresh, create a new bot instead.`

   「换个名字再新建」这条路对本 profile 的主会话是堵死的。
2. **`hermes sessions archive` 拦不住**：archive 只是 soft-hide，**title 还在**，
   `-c "Bot Chat"` 照样解析回同一个会话，下次接着长。归档对 canonical chat 等于没做。
   （`archive --dry-run` 能匹配到、能执行，所以别被「命令成功」骗了。）
3. **`-c <名字>` 找不到同名会话是 fail loudly（exit 1）**，不会静默落到「最近的会话」。
   源码 `hermes_cli/main.py::_resolve_continue_arg`：带 `--create-if-missing` 才自动建同名新会话。
   → 任何依赖 `-c "Bot Chat"` 的程序化/静默调用，改名前都必须先加这个 flag，否则下次直接报错。

## 三、正解：就地压缩（in-place compaction）

Hermes 的压缩是**非破坏性**的：旧消息 `active=0, compacted=1`，留在库里、FTS 可搜、可恢复，
新上下文由「摘要 + 最后 N 条」组成（`protect_last_n` 默认 20，`protect_first_n` 默认 3）。

### 关键配置

| 键 | 默认 | 说明 |
|:--|:--|:--|
| `compression.enabled` | true | 关了就永远不压 |
| `compression.threshold` | 0.5 | 占模型窗口 50% 才触发；窗口 1M 的模型 = 50 万 tokens 才开始压 |
| `compression.in_place` | **true** | 被显式设成 `false` 时是 **rotation**：fork 出新会话、**session id 变**，对 canonical bot 是灾难 |
| `compression.target_ratio` | 0.2 | 摘要目标比例 |

👉 做 canonical bot 的 profile，先确认 `in_place: true`。

### 非交互手动触发（实测可用）

1. 备份 `config.yaml`
2. 临时把 `compression.threshold` 降到当前占用之下（如 `0.12`）
3. 跑一次**最简**查询：`hermes -p <profile> chat -c "Bot Chat" -Q --query-file <file>`
   （turn 开始时先 preflight 压缩，再回答；查询内容设计成「只回三行、不要调用任何工具」）
4. **答完立刻把 threshold 改回 0.5**，否则后续每轮都可能反复触发

### 实测结果（health profile，272 条 / 48.6 万字符）

- 会话：273 → 103 条 active；压缩耗时 102s；`split_status=in_place_committed`
- 上下文：**218,615 → 66,908 tokens**；随后那次 API 调用 `in=70,715`
- session id、title、模型全部不变（`20261029_101937_81e395` 仍是 `Bot Chat`）
- 旧消息 172 条 `compacted=1` + 100 条 `active=0` 保留在库，可搜可恢复

## 四、顺带修掉的两个隐性超限

- **memory 超 `memory_char_limit`（默认 2200）是静默失败**：文件超了，写记忆直接被拒，
  而模型还以为写进去了。health profile 当时 3403/2200。做法：memory 只留**指针**
  （数据目录、必加载的 skill、不可外移的硬规则），流程细节搬进 skill，**改完从磁盘重读核对**
  字符数与条目数（3403 → 742，7 条）。
- **搬细节前先核对目标 skill 有没有覆盖**，别凭「应该在里面」就删。用关键词数一遍
  （如 `anchor` / `llm_decompose` / `别名` / `2393`），缺的补进 skill 再删 memory。

## 五、压缩不是一劳永逸：派活的成本才是增长源

压缩完当天就能看到它反弹。实测同一天（2026-10-31，health profile）：

| 时点 | 上下文 | 发生了什么 |
|---|---:|---|
| 压缩刚完 | **66,908** | 273→103 条 |
| 第一次派活后 | 96,602 | 记一顿早餐（调了 22 次工具） |
| 第二次派活后 | **124,614** | 记一场运动 |

→ **一次带工具调用的 `-Q` 派活 ≈ +30K～55K tokens**，因为吃进来的是工具回显，不是对话。

三条对策（按性价比排）：

1. **一次派活只做一件事**。把「记早餐 + 记运动 + 算赤字」塞进同一条 query，
   工具轮数会翻倍，而每一轮都重放前面所有回显。
2. **任务书里写死「不要整篇 read_file 大档案，按节读」**。实测 profile.md 只有 38KB，
   但被整篇读了好几遍，单 `read_file` 就占了上下文的 14%。
3. 🔴 **先开「主动剪枝」，别急着调 threshold**（2026-11-13 补正；此前这里只写了「手动压 / 降 threshold」
   两条，漏了性价比最高的那条）：`compression.proactive_prune_tokens` 是**独立于全量压缩**的
   确定性剪枝——不调 LLM、秒级、不丢对话（剪掉的内容可用 `session_search` 找回）。
   日常主力应该是它，全量压缩只当兜底。
   ⚠️ **但它默认参数对聊天场景等于没开**：`proactive_prune_min_result_chars` 默认 8000，
   而聊天/核算场景的工具回显中位数只有几百字符（实测 193 条里只有 1 条 > 8000）——必须降到 200。
   完整参数、机理与四层治理框架见 `references/context-governance-playbook.md`。

🔴 **反过来也别过度压缩**：压缩本身要花一次大调用（16 万 tokens 进来生成摘要，
本例 102s）。频率按「每次压完能撐多少次派活」算，不是越频越好。

## 六、验证清单（做完必须跑）

- [ ] `messages` 表 `active=1` 的条数与字符数下降，`compacted=1` 有值
- [ ] `sessions` 表 title / id / model 未变
- [ ] 让 bot 回答一个能暴露 memory + skill 的问题（如「你 MEMORY 第一条讲什么」「手册在哪个 skill」），
      确认它读到的是新版
- [ ] `config.yaml` 的 threshold 已改回原值；临时查询文件已删
