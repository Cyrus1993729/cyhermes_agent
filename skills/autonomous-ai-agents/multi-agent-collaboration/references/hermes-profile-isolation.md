# Hermes 多 profile 隔离与跨 profile 调用

> 2026-10-18 实装调研。用户目标是"建一个只管健康的 bot，不被财经/美股上下文污染"。

## 结论先行

**Hermes 客户端里的"一个 bot" = 一个 Hermes profile。**
不需要第二个 Telegram bot、不需要第三方 UI、不需要额外常驻进程。
按需调用模式（`hermes -p <profile> chat`）已经实测跑通。

## 一、Bot Mode 是什么（客户端侧，读源码得来）

位置：`hermes-agent/apps/desktop/src/plugins/hermes-bots/`（内置插件，默认开启）。

`plugin.tsx` 顶部注释原文：

```
Hermes Bot Mode — a "one chat per agent" roster for the Hermes desktop.

Left pane "Bots": one row per Hermes profile (a bot = an agent profile)
  with a customizable avatar. Click opens that bot's chat; right-click → Edit Profile.
"New Bot" creates a profile — Name / Title / Description with an
  "Advanced" disclosure for full profile config.

Right tile "Routines": scheduled tasks (Hermes cron jobs) scoped to the
  bot you're currently chatting with — follows the live gateway profile.
```

`create-dialog.tsx` 佐证：第 6 行 `New Bot creates its profile LAZILY`；
提交调 `requestForTarget('profiles.create', …)`；删除调 `argv: ['profile','delete', draft, '--yes']`。

每个 bot 额外白送：自己的 **Routines**（cron，scoped 到该 bot）、bot 间 @ 互发消息、面板分组。

## 二、为什么 `@提及` 在 Telegram 上不能用

**证据 1 —— 解析代码只在桌面端**
```
grep -rn "resolveRosterMentions" apps/desktop/src/plugins/hermes-bots/
→ 全部命中在 apps/desktop/ 下
```
它拦截出站消息，并向当前 agent 附加一段注解：
```
[@mentions resolved from the Bot Mode roster — the user is referring to:
 @health = agent profile "health" ("健康"). If they want one of these agents
 contacted, compose your own message and send it with your message_agent tool
 … never forward the user's text verbatim.]
```

**证据 2 —— 工具被封闭在 Bot Chat 里**（`tools/bot_mode_dm.py`）：
> It is NOT registered in the global tool registry, is NOT part of any toolset,
> and never appears in CLI sessions, **ordinary gateway chats**, group-room member
> sessions, cron agents, or subagents.

注入门槛（`ensure_message_agent_tool`）：会话标题 == `BOT_CHAT_TITLE`（值 `"Bot Chat"`）
且 `is_bot_mode_managed(hermes_agent_home)` 为真。

Telegram = ordinary gateway chat → 两条都不满足。

## 三、`--clone` 的记忆污染陷阱

`hermes_cli/profiles.py`:

```python
# Files copied during --clone (if they exist in the source)
    "config.yaml",
    ".env",
    "SOUL.md",
# Subdirectory files copied during --clone (path relative to profile root)
    "memories/MEMORY.md",
    "memories/USER.md",
```

所以 `hermes profile create health --clone` **会把主 profile 的 MEMORY.md/USER.md 一并复制**。
若目标是"这个 agent 只看得到健康上下文"，这一步就把它污染了。

**修法**：clone 后立刻覆盖这两个文件为该域专属内容（例如健康 profile 只写体格、体检值、运动习惯、目标），
并移出无关 skills（skill 名与描述会进系统提示词）。

`--no-skills` 与 `--clone` 互斥，不能靠它规避。

## 四、跨 profile 调用命令（实测）

```bash
# 一次性问答（每次新建会话）
hermes -p <profile> chat -Q -q "<question>"

# 连续会话（推荐；--query-file 避开引号坑）
hermes -p <profile> chat --in ~ -c "Bot Chat" --create-if-missing -Q --query-file <tmpfile>
```

实测输出：
```
Warning: Unknown toolsets: a2a
session_id: 20261018_220559_bfacb7
通道正常
EXIT=0
```

关键 flag：
- `-p/--profile` 全局 flag，切换 HERMES_HOME
- `-c/--continue [SESSION_NAME]` 续接命名会话（**不写则每次新建，失去上下文**）
- `--create-if-missing` 会话不存在则新建
- `-Q/--quiet` 程序化使用
- `--query-file` 从文件读查询

Bot Mode 自己也是走这条路（源码原文）：
```
local teammate → hermes -p <name> chat --in ~ -c "Bot Chat" --create-if-missing -Q --query-file <tmp>
peer teammate  → hermes peer dm <peer>[/<name>] < <tmp>
```
并被 `terminal_tool(background=True, notify_on_complete=True)` 包装 → 回复以完成通知形式回到发起方**下一轮**（fire-and-forget，不阻塞当前回合）。

## 五、profile 管理命令速查

```bash
hermes profile list                              # 列出所有 profile + gateway 状态
hermes profile create <name> --clone             # 继承 config/.env/SOUL/skills（含 memory，见第三节）
hermes profile create <name> --clone-all         # 全量复制（含 state，不含 per-profile history）
hermes profile create <name> --no-skills         # 空 skill 库（与 --clone 互斥）
hermes profile show <name>
hermes gateway list                              # 列出各 profile 的 gateway
hermes gateway install                           # 给当前 profile 装自启
```

## 六、Telegram 侧的两条死路（别再提）

| 方案 | 为什么不满足"独立对话框" |
|:--|:--|
| `/topic`（Telegram DM 话题） | 是**同一个对话窗口内部的标签栏**，仍要先点进该对话再点选项 |
| 同一 profile 挂两个 Telegram bot | 不支持：`telegram.token` 是单值，适配器无多账号 |

要真正独立的对话框 → **独立 profile + 第二个 Telegram bot**（需 @BotFather 新建 token）。

## 七、单通道约束下的取舍

用户只用手机 Telegram 时，**"零切换"与"上下文隔离"互斥**：

- 要隔离 → 必须有第二个入口 → 必须点一下
- 完全不点 → 只能混在一个会话 → 靠**数据落盘**解决上下文长度问题

最后这条容易被忽略，值得强调：**"上下文过长"本质靠落盘解决，不是靠分流。**
数据写成文件后，即使会话被压缩，`read_file` 随时能捞回来。
所以带隔离需求的 agent 方案，第一步永远先做数据层（可逆、无副作用、两种方案都要）。
