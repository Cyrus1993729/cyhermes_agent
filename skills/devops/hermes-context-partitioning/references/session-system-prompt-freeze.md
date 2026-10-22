# 会话级 system prompt 固化：新 memory / 新 skill 进不去老会话

2026-10-21 实测诊断。适用于任何「我给某个平台会话写了规则、装了技能，它却依旧按老办法干活」的场景。

## 症状

给微信会话写好了角色规则（memory）与操作手册（skill），description 里明确写了「禁止自建 cron 充当提醒」。用户随后在微信连试两次：

1. 「今天下午5点确认晚上要不要打球」→ 它建了个 cron `f5cae23d71c5`，目标主库零记录
2. 修完规则再试「明天上午十点取快递」→ 又建 cron `bc476b9fe04c`，库里依然没有

两次都回复「已排好，X 点提醒你」，**完全没提目标系统，也没调用任何相关脚本**。

关键判据：这不是「不听话」，是它根本不知道有新工具存在。

## 诊断：查 state.db 的 sessions 表

```python
import sqlite3, os, datetime
p = os.path.join(os.environ['LOCALAPPDATA'], 'hermes', 'state.db')
con = sqlite3.connect(p)
for r in con.execute("""
    SELECT id, source, started_at, system_prompt_hash, message_count
    FROM sessions WHERE source IN ('weixin','telegram')
    ORDER BY last_activity_at DESC LIMIT 6
"""):
    started = datetime.datetime.utcfromtimestamp(r[2] + 8*3600).strftime("%Y-%m-%d %H:%M")
    print(r[1], r[0], started, (r[3] or '-')[:8], r[4])
```

实测结果：

```
weixin    20260720_174815_41cc4f07   建于 2026-07-20 17:48   hash=70eaf635  msgs=23
telegram  20261021_094243_a81b2f87   建于 2026-10-21 09:42   hash=6146f21d  msgs=383
```

两个判断点：

1. `started_at` 显示微信会话**三个月前**创建、一直复用
2. 两个会话 `system_prompt_hash` 不同 → **每个会话单独固化一份 system prompt**

## 根因

Hermes 为保证 prompt 缓存不失效，**system prompt 在一个会话生命周期内 byte-stable**
（hermes-agent 开发指南：「Per-conversation prompt caching is sacred ... a system prompt
that is byte-stable for the life of a conversation」）。memory 与技能清单属于 system prompt
的一部分，所以：

- 会话创建之后**新写的 memory 进不去**
- 会话创建之后**新装的 skill 也不在它的清单里**（本例技能部署于 10-20，会话建于 07-20）

于是老会话面对「下午5点提醒我」只能用最朴素的手段：自建 cron。

## 修复

删除老会话，下次该平台来消息时自动按最新 system prompt 重建：

```bash
hermes sessions delete <session_id> --yes
```

补充：`hermes sessions export` 的参数比较挑（`--format md` 后面接位置路径、以及 `--output`
实测都报 unrecognized arguments），要保留历史建议直接读 `messages` 表留证，别在 export 上耗轮次。

删前先看一眼内容价值。本例 23 条消息里 20 条是 cron 推送 + 一句「在吗」+ 两次失败对话，删掉无损失。

删后验证：`SELECT COUNT(*) FROM sessions WHERE source='weixin'` 只反映历史存量；
`ORDER BY last_activity_at DESC` 的最新一条不再是那个老 weixin 会话即可。

## 通用教训

1. **改完 memory / 装完 skill = 只对「之后新建的会话」生效。** 要在某平台立刻生效，必须让该会话重建。
2. **软约束之前先查会话年龄。** 会话跨周/跨月就先怀疑 system prompt 固化，不要反复改文案——改十遍它也读不到。
3. **验证用行为，不用自述。** 让对方真跑一次，再回查主库有没有对应写入；「规则已写入」不等于「它已经知道」。
4. 同一 profile 下，每个平台、每个 chat 都是**独立会话与独立上下文**；`chat_id` 不同就代表上下文不共享。
5. 新会话第一句话会显得「失忆」（看不到之前的对话），这是预期行为，需说明。

## 附：cron `deliver=origin` 的隐藏坑

备份失败通知曾长期投不出去：job 的 `deliver=origin`，而它的 origin 记录的是**微信** chat_id，
于是「备份失败 → 发微信 → 微信限流 → 也失败」双重静默。

排查：

```python
import json, os
d = json.load(open(os.path.expanduser("~/AppData/Local/hermes/cron/jobs.json"), encoding='utf-8'))
for j in d['jobs']:
    o = j.get('origin') or {}
    print(j.get('name'), j.get('deliver'), o.get('platform'), o.get('chat_id'))
```

结论：**运维/告警类 job 一律显式 `deliver=telegram`（或对应告警通道），不要依赖 `origin`**——
它跟着创建时所在平台走，很容易指向一个额度有限/不合适的通道。
