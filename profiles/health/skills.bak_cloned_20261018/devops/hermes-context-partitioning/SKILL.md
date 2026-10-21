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

## Memory 预算

独立 profile 的**真实好处之一**是独立 memory 预算（本用户 memory 已近满：
2175/2200 字符）。这是唯一站得住脚的「建独立 profile」论据，值得承认。

**但**：领域基线（健康指标、投资偏好）**不该塞 memory**，应放固定文件，
memory 里只留一行指针指向该目录。这条无论选哪个方案都成立。

## Pitfalls

- 🔴 **不要一上来就答应建 bot。** 先讲清「专业度来自沉淀」，再给分层方案。
- 🔴 **不要推荐要打命令的切换方式**（见「零手动切换」）。
- 🔴 **落地前必须做可行性验证。** Telegram DM 话题依赖 Bot API `createForumTopic`，
  需要客户端支持；**本机尚未实测过**。先建一个测试话题验通道，再改正式配置。
  若通道不通，退回独立 profile——此时数据层已就绪，直接搬。
- **一个 profile 只配一个 Telegram token。** 想在同一 profile 里挂第二个 bot 是做不到的。
- **Hermes 内置的跨实例协作**（Kanban 多 profile 工作队列、A2A）面向的是「多 worker
  协作」场景，**不是**「给用户的不同话题分上下文」，别拿错工具。
- 汇报用 bullet / 标签行，不用 markdown 表格（Telegram 不渲染表格）。

## 参考
- `references/telegram-dm-topics.md` — DM 话题的源码核实行为：配置格式、
  自动建话题、thread_id 回写、话题级 skill 绑定、独立 session 的路由证据。
- `gateway-setup` — 平台接入与凭据（本 skill 是「接了之后怎么分域」）。
- `hermes-agent`（bundled，只读）— profiles / cron / kanban 的官方说明。
