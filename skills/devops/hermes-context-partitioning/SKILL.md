---
name: hermes-context-partitioning
description: "Use when 用户想给某类任务分开上下文或建独立 bot。分域隔离分层选型+零手动切换方案。"
version: 1.0.0
author: agent
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [hermes, config, profiles, telegram, topics, sessions, context, isolation]
    related_skills: [gateway-setup, hermes-agent]
---

# 任务域的上下文分区（分域 bot / 独立会话）

用户问「能不能单独建一个 bot 专门处理 X」「我不想每次手动切换到 X 对话」
「上下文太长 / 跟别的对话混在一起会出问题」时加载。

## 🔴 先纠正前提：专业度来自沉淀，不来自隔离

用户提出分域时，通常隐含一个错误前提——「新开一个专职 bot 会更专业」。
**恰恰相反：从零开始的新实例只会更不专业**，因为它不知道用户基线
（体重体脂、体检指标、工作性质、既有目标），也不知道之前分析过什么。

真正决定分析质量的是两样东西，都跟「几个 bot」无关：
1. **完整的历史数据** → 来自**落盘**，不是来自实例数量
2. **固化的分析框架** → 来自 **skill**，不是来自实例数量

把这一点讲清楚，用户往往会自己调整方案。

## 🔴 根因拆解：用户常把两个问题打包成一个

| 用户原话 | 真实根因 | 正确解法 |
|:--|:--|:--|
| 「上下文过长」 | 关键信息只存在于对话里，一压缩就丢 | **数据落盘**（文件在，压缩不可怕） |
| 「跟别的对话混在一起」 | 缺少会话级分区 | 话题会话 / 独立 profile |
| 「专业度不够」 | 缺固化框架 | **写 skill**，不是建 bot |

**第一个动作永远是数据落盘，不是建实例。**
反过来说：**建了 bot 但数据还留在对话里 = 白建**，一样会被压缩吃掉。
这句话是说服用户按顺序做的最有力论据。

## 零手动切换 —— 用户的硬要求

用户明确表达过：
> 「我也不想每次要先手动做一部新建对话，然后再开始跟你做健康类的对话」

所以**要求打命令的方案都不合格**：`/new`、`/topic`、口头说「切换到 X 对话」——全部排除。
**能接受的最轻交互是：在 Telegram 里点一下话题标签**（等同于切群聊，用户已有肌肉记忆）。
推荐任何方案前，先按这条筛一遍。

## 三层方案（成本从低到高，按可逆性排序）

### 第 1 层：只落盘（成本 0，必须做）
固定目录 + 一个写明路径的 skill。用户照常聊，什么都不用切。
对话被压缩也不怕——需要时 `read_file` 拿回来。
**这一层不做，上两层都是空中楼阁。**

### 第 2 层：Telegram DM 话题（同 bot 内分域）
每个话题 = **独立 session**（上下文真隔离）+ 可**绑定 skill**（自动加载）。
用户点标签即切换，零命令。**配置格式与源码核实行为见
`references/telegram-dm-topics.md`。**

### 第 3 层：独立 profile（彻底隔离）
```bash
hermes profile create NAME          # --clone / --clone-all / --clone-from
hermes profile list
```
独立 `config` / `skills` / `memory` / `sessions` / `cron`，位于
`~/.hermes/profiles/<name>/`。要独立 Telegram bot 就得走这层
（一个 profile 只配一个 `telegram.token`，**两个 bot = 两个 profile**）。

## 选型表

|  | 只落盘 | DM 话题 | 独立 profile |
|:--|:--|:--|:--|
| 切换动作 | 无 | 点标签 | 切到另一个对话 |
| 对话上下文隔离 | ✗ | ✅ 独立 session | ✅ |
| skill 自动加载 | 手动 | ✅ 话题级 | ✅ profile 级 |
| memory | 共享 | 共享 | **独立** |
| 额外 bot token | 不用 | 不用 | **要** |
| 维护成本 | 0 | 改 config | 多一套实例 |

## 🔴 可逆性优先：先落盘，跑 2-4 周再决定分不分

论证模板：
> 数据层在**三个方案里都要做**。先做它，你什么都不损失；
> 先建 bot 再做数据层，你就白建了一个从零开始的实例。
> 跑 2-4 周后如果还觉得混，再上话题/独立 profile——**那时数据已就绪，迁移零成本**。
> 反过来，先建 bot 再发现不需要，拆比建麻烦。

## 🔴 第二判据：这个领域的数据，已经不在对话里了吗

「专业度来自沉淀」只是第一层。落到具体领域时再问一句：**这类任务的真实数据在谁手里？**

- 数据只活在对话里（体检记录、分析结论）→ 落盘 / 分域都还得做，第 1 层优先。
- 数据已在**外部系统或云端主库**（日程在 Dayflow、账本在记账 app、代码在 git）→
  分域最核心的收益（防压缩丢数据）**用户已经拿到了**，建独立 bot 只剩「对话不互相淹」一条收益。
  此时默认**不建**，用 skill + 落盘目录 + cron 顶住。

本机两个现成对照（2026-10-21 实判，用户当时直接问「要不要像健康助理那样再建一个」）：

- **健康 → 建了独立 profile**：体检数据敏感、低频深挖、需要独立基线档案。
- **日程 → 不建**：数据在云端主库；讨论高频即时（「明晚八点加一条」当场就该改完），
  跨 profile 中转反而多一次失真与延迟；memory 虽已 97%，但日程规则写进 skill 里不占预算。
  → 口径：**先跑 2-4 周，数据在云上，真要分时迁移零成本**。

给用户时把「反着做才亏」讲清楚：先建 bot 再发现不需要，拆比建麻烦。

## 多通道软分工：同一 profile 里的「小秘书 + 总管」（2026-10-21 实做）

用户想让「微信 = 日程小秘书，Telegram = 总管」，同一个模型两种角色。

### 硬约束先说清楚

- **一个 profile 每个平台只能配一个凭据。** 微信 iLink bot 是扫码绑定的设备身份，
  想给微信单独挂一个独立小秘书实例**做不到**（要第二个微信号去扫码）。
- 只能走**软分工**：同一套 skill / memory / config，靠**会话隔离 + 规则约束**区分角色。
  **拦不死**——越界是可能的，所以必须有第三层「事后发现」，不能只靠规则。

### 平台消息的真实路由（实测，别向用户描述错）

用户曾以为「所有消息 agent 都看得见，只是决定从哪个通道回」。**不是**：

- 每个平台的消息进**各自的 session**，上下文不共享
- 回复**自动回到原平台**，由网关路由决定，agent 不选通道
- 微信里说的话，Telegram 会话里的 agent **不会自动知道**，得主动查 `state.db`
- **唯一由 agent 选通道的**是 cron 的 `deliver`

实测证据（2026-10-21）：微信 `09:58:51 在吗` 由微信 session 回「在。你说。」，
同一时刻 Telegram session 里完全没有这条。两个 session id 不同、`source` 不同。

### 三层实现

1. **角色定义进 memory** —— 跨会话注入，微信会话每次启动都读到「你是日程秘书」
2. **流程进 skill** —— 共享目录，两个会话都能加载同一套操作手册
3. **事后可观测** —— 两个来源：
   - **硬数据**：所有操作必须落外部主库（如 Dayflow），查库即知对方改了什么，不靠对话同步
   - **软信息**：对话里说了什么，靠 cron 定时扫 `state.db` 的对方会话，摘要落盘 +
     「对话里提到但库里没落地」的差异告警

> 为什么用「扫数据库」而不是让秘书自己写交接？**秘书可能漏写，数据库它绕不过去。**

### 🔴 让老会话「学会」新规则：必须重建会话（2026-10-21 实测）

写完规则、装完技能，**老会话依然按老办法干活**——不是不听话，是它根本没被告知。

Hermes 的 system prompt 在一个会话生命周期内 **byte-stable**（prompt caching 要求），
memory 与 skill 清单都在里面。所以：会话建好之后，**新写的 memory 进不去，新装的 skill 也不在它的清单里**。

本例症状：给微信会话定好角色与操作手册（description 里明写「禁止自建 cron 充当提醒」）后，
它连续两次把「下午5点提醒我」做成自建 cron，完全没提目标系统，主库里零记录。

一眼诊断：

```python
# state.db 里看会话年龄 + system_prompt_hash
SELECT id, source, started_at, system_prompt_hash FROM sessions
ORDER BY last_activity_at DESC LIMIT 6
```

`started_at` 是三个月前、`system_prompt_hash` 与新建会话不同 → 就是它。

修复：删掉老会话，下次来消息自动按最新 system prompt 重建

```bash
hermes sessions delete <session_id> --yes
```

三条规矩：

1. **改 memory / 装 skill = 只对之后新建的会话生效**；要立即生效必须重建会话
2. **先查会话年龄，再改文案**——会话太老时改十遍文案也读不到
3. **验证用行为，不用自述**：让对方真跑一次，再回查主库有没有对应写入

完整诊断路径、证据与 export 参数坑见 `references/session-system-prompt-freeze.md`。

### 不同通道的汇报口径必须分开

角色不同，汇报风格也得分开——同一个 agent 在两个通道里不该用同一种语气：

| | 总管通道（如 Telegram） | 秘书通道（如微信） |
|:--|:--|:--|
| 过程 | 分步汇报、边说边做 | **只讲结果，不报过程** |
| 长度 | 不限 | 单条 ≤900 字（iLink 1800 字才拆块，拆块既丢内容又烧额度） |
| 格式 | 可用加粗/列表 | 纯文本，不用表格分隔线 |

两条硬规矩：

1. **角色定义必须同时写进 memory**，否则新会话会按默认习惯在微信里刷屏。
2. 🔴 **写操作必须先回读成功再回话。** 微信端没有「正在处理」的过程播报，
   用户只看得到最终结果——先说「已保存」再去改，一旦失败用户根本无从发现。

### 查另一通道说了什么

```python
# state.db：sessions 按 source 区分平台；messages 按 session_id 取
SELECT id, source, chat_id, last_activity_at FROM sessions ORDER BY last_activity_at DESC
SELECT role, content, timestamp FROM messages WHERE session_id = ? ORDER BY timestamp DESC
```
`timestamp` 是 epoch 秒，北京时间 = `utcfromtimestamp(ts + 8*3600)`；`messages` 表**没有** `created_at`。

## Memory 预算

独立 profile 的**真实好处之一**是独立 memory 预算（本用户 memory 已近满：
2175/2200 字符）。这是唯一站得住脚的「建独立 profile」论据，值得承认。

**但**：领域基线（健康指标、投资偏好）**不该塞 memory**，应放固定文件，
memory 里只留一行指针指向该目录。这条无论选哪个方案都成立。

## 第 3 层落地后：主实例如何调用子 profile（本机已验证）

手机只有一条 Telegram 通道时，用户在 main chat 里用**触发词**唤起子域，
由主实例用 `chat` 子进程中转。本机已在 health profile 上跑通：

```bash
hermes -p health chat -c "Bot Chat" --create-if-missing -Q --query-file <native-path>
```

- `-c "Bot Chat"` 命名会话 → **可续**（实测第二次会 `↻ Resumed session`），
  子 profile 记得住上次聊了什么
- `-Q` 安静模式；`--create-if-missing` 首次自动建会话
- ⚠️ **长 prompt 一律 `--query-file` 传文件**，不要 `$(cat f)` 内联
- ⚠️ **路径参数给原生正斜杠路径**（`C:/Users/...`）；MSYS 的 `/tmp/...` 原生程序读不到
- 无关警告 `Unknown toolsets: a2a` 是正常的，不影响执行

**这份能力不能靠猜**：`message_agent` 只存在于桌面端 Bot Mode 的 "Bot Chat" 会话
（`tools/bot_mode_dm.py`），**不在 CLI / 普通 gateway chat / group / cron / subagent 里**；
Telegram 里打 `@名字` 也不会触发（`@` 解析在 `apps/desktop/`）。
→ 「在手机上 @ 某个 bot」做不到，**只能用子进程中转 + 人为约定触发词**。

## 🔴 子 profile 的自报必须独立核验

**本会话实测事故**：把一份事实清单交给子 profile 归档，它自报
「已归档，记忆 9 条、1105 字符，内容完整」。实际读文件发现：

- `MEMORY.md` **首尾各有一段完全重复的条目**（它自己说的那次 `replace` 事故的残留）
- `USER.md` **仍是陈旧数据**——还写着「身高未知」和旧的目标体重，而主档案当天已更新过

**规则：**
1. **子 profile 的成功汇报 ≠ 事实。** 归档类任务必须回读真实文件核对
   （文件清单 + `wc -c` + `read_file`），不能只看它的总结。
2. **记忆不会跟着档案自动更新。** 基线数据一旦同时存在于「档案文件」和
   `USER.md`/`MEMORY.md`，两者必然漂移 → **指针 > 复制**：
   memory 里只留一句「完整档案在 X，分析前必读」。
3. **改完 memory 必须重读核对**：`replace` 动作实测会连带清掉相邻条目。
4. **验证用事实问答**：给子 profile 出 N 道只问事实、不要建议的题
   （数字 + 出处 + 缺口），全对才算交接完成。本会话用 8 题测，全对。
5. 交接口吻：把**事实**给子 profile，**不要**把你的建议/方案一起塞过去——
   否则它会把你的结论当成前提，失去独立判断。

## Pitfalls

- 🔴 **不要一上来就答应建 bot。** 先讲清「专业度来自沉淀」，再给分层方案。
- 🔴 **子 profile 的记忆里不要复制基线数据**（体重/指标/目标）——必然漂移；
  memory 只留指针，数据放档案文件。交接后务必回读核验，别信它的自报。
- 🔴 **别把「规则已经写进去了」当成「它已经知道了」。** 老会话的 system prompt 是固化的，
  新 memory / 新 skill 进不去；要让某平台会话立刻采纳新流程，必须 `hermes sessions delete` 重建。
- 🔴 **运维告警类 cron 不要用 `deliver=origin`**：origin 跟着创建时所在平台走，很容易落到
  额度有限的通道（本例备份失败通知一直发微信，微信限流后又失败，双重静默）。显式写目标平台。
- 🔴 **不要推荐要打命令的切换方式**（见「零手动切换」）。
- 🔴 **别承诺「定时任务每天跟你讨论计划」**：Hermes cron 无人值守、无交互，只能单向推送。
  正确拆法——cron 生成并**落盘**草案 + 推送里带可回复的问题，**真正的讨论发生在用户回复后的交互会话**。
  把「自动讨论」当成能建出来的东西，就是骗用户；开口前先把这条边界说出来。
- 🔴 **落地前必须做可行性验证。** Telegram DM 话题依赖 Bot API `createForumTopic`，
  需要客户端支持；**本机尚未实测过**。先建一个测试话题验通道，再改正式配置。
  若通道不通，退回独立 profile——此时数据层已就绪，直接搬。
- **一个 profile 只配一个 Telegram token。** 想在同一 profile 里挂第二个 bot 是做不到的。
- **Hermes 内置的跨实例协作**（Kanban 多 profile 工作队列、A2A）面向的是「多 worker
  协作」场景，**不是**「给用户的不同话题分上下文」，别拿错工具。
- 汇报用 bullet / 标签行，不用 markdown 表格（Telegram 不渲染表格）。

## 参考
- `references/session-system-prompt-freeze.md` — 会话 system prompt 固化：新 memory/skill
  不进老会话的完整诊断、`sessions` 表查询、`hermes sessions delete` 修复法、export 参数坑、
  以及 `cron deliver=origin` 误投通道的排查。
- `references/telegram-dm-topics.md` — DM 话题的源码核实行为：配置格式、
  自动建话题、thread_id 回写、话题级 skill 绑定、独立 session 的路由证据。
- `gateway-setup` — 平台接入与凭据（本 skill 是「接了之后怎么分域」）。
- `hermes-agent`（bundled，只读）— profiles / cron / kanban 的官方说明。
