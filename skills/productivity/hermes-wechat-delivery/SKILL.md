---
name: hermes-wechat-delivery
description: "Hermes 微信消息投递可靠性——iLink 限流机制、熔断器行为、多源碰撞诊断、修复方案。适用于微信消息丢失/截断/限流的排查和预防。"
version: 1.1.0
category: productivity
tags: [hermes, wechat, weixin, delivery, rate-limit, debugging]
---

> ⚠️ **状态更新（2026-10-18）**：微信 iLink 通道曾被弃用（主平台迁 Telegram），但**用户已明确要把微信重新用作通知渠道**（"国内使用率高"）。2026-10-18 完成了一次完整的**会话超时 → 重新扫码绑定**，流程见 `references/ilink-rebind-2026-10.md`（必读，含 90 秒二维码生死线、自动补发循环、请求格式坑）。
> 下面关于 iLink 限流/熔断器的内容仍是有效的技术参考。

# Hermes 微信消息投递可靠性

> 来源：2026.7.3 实战——备份 cron 失败通知 + 会话回复同时触发 iLink 限流，一天内两次消息丢失事故。深入阅读 `gateway/platforms/weixin.py` 和 `cron/scheduler.py` 源码后整理。

## ⚠️ 平台硬限制：context_token 10 条回复额度（最高优先级）

**这是微信 iLink 最根本的限制，优先级高于所有速率/熔断器问题。下面所有速率控制、熔断器调优都是治标——10 条额度耗尽后一切都白搭。**

微信 iLink 使用 context_token 机制：
- 用户发一条消息 → 微信生成一个 context_token
- 该 token 的**回复额度 = 10 条**
- 超过 10 条 → 后续所有发送失败（表现为 iLink 返回错误）
- 用户发下一条新消息 → 新 token → 重置额度
- 有效期约 24 小时

**这意味着：**
- 不是"发太快被限"，而是"发太多被限"
- 之前的 3 秒间隔、退避重试、熔断器调优都是在用秒级节流对抗配额限制——方向全偏
- 6 分钟静默后仍被"限流"是因为 10 条额度已耗尽，不是冷却期没到
- 所谓的"熔断器死亡螺旋"真正的根因就是 10 条打满了

**应对：**
- 每轮回复控制在 10 条以内
- 多轮长任务时用户中途多互动几次刷新 token
- **强烈建议接入无此限制的平台（Telegram 等）作为主力通讯工具**

## 分块线：一条消息吃几个额度（2026-10-21 核实源码）

```python
# gateway/platforms/weixin.py
MAX_MESSAGE_LENGTH = 2000   # L1193
_SPLIT_THRESHOLD   = 1800   # L1592 —— 超过就拆块，iLink 按 ~2048 字符切
```

🔴 **拆块 = 多耗额度**：超过 1800 字的消息被拆成 N 块发送，每块各占 1 条 context_token 额度。所以「消息太长」不仅会因限流丢后半段，还直接烧配额。

→ 实践口径：**主动推送单条 ≤900 字**（拆块线的一半），既防截断又只吃 1 个额度。

## 主动发一条到微信（2026-10-21 实测可用）

与 Telegram 同一套 CLI，不必碰 token/代理：

```bash
hermes send --list weixin                 # 列出在册目标
hermes send --to "weixin:<wxid>@im.wechat" --file msg.txt --json
# → {"success": true, "platform": "weixin", "chat_id": "...",
#    "message_id": "hermes-weixin-...", "context_token_used": true}
```

- 返回里的 `context_token_used: true` 说明它走的是当前有效会话的配额——**所以主动推送依赖用户近期在微信说过话**。
- 用户久未发言会报 `errcode=-14 session timeout`；这时不要反复重试，发一条别的渠道（Telegram）告知，并请用户回微信说句话刷新会话。
- `success` 字段就是交付证据，失败 exit 1。

### 推荐封装：微信优先 + 跨平台兜底

脚本里不要直接发一条就算，写成：

```
send(text):
  1) 长度截到 ≤900 字（别让它自动拆块）
  2) 微信发送；success → 记账返回
  3) 失败 → 原文 + "（微信通道没发出去，这条走 Telegram）" 转 Telegram 再发一遍
  4) 两条路都失败才返回失败，并落 delivery.log
```

这样 iLink 配额打满/会话过期时，消息只是换了通道，不会静默消失。

### cron 里怎么接

如果用脚本自己发，cron 任务必须设 `deliver='local'`（只留日志），否则脚本 stdout 会被再投递一次，等于一内容发两遍、吃两个额度。

## 📢 微信端汇报口径（用户明确要求，2026-10-21）

**微信的回复风格与 Telegram 不同，别把 Telegram 那套搬过来。** 用户原话：

> 「你在微信端跟我联系的时候，要改汇报方式，首先确保信息不要过长导致截断丢掉，另外也不用汇报过程了，直接讲结果就好（这个跟我们约定好的在 telegram 上的汇报习惯不一样）」

| | Telegram（主通道） | 微信 |
|:--|:--|:--|
| 过程/进展播报 | ✅ 边做边说、分步汇报 | ❌ **不要**，直接给结果 |
| 单条长度 | 可长，必要时分多条 | **≤900 字硬顶** |
| 结构 | 标题 + 分点 + 必要的推导 | 结论先行，能一句说完就别两句 |
| 代码块/长表格 | ✅ | ⚠️ 克制，长列表改写成行内短句 |

**为什么：** 不是审美问题，是通道机制——超过 1800 字会拆块，拆块既丢内容又烧 context_token 配额（见上文「分块线」）。所以「别啰嗦」在微信上是可靠性要求。

**具体做法：**
- 结果先行，解释只留必要的一句
- 长任务在微信上只说「做完了 / 没做完，卡在哪」，拆解过程留给 Telegram 或下一轮
- 真的需要长内容（报告、清单）→ 微信发一句摘要 + 问要不要发到 Telegram
- 用户对机制的直觉可能不准（他以为是「连续发超过 10 条会丢」，实际是**每轮总额度 10 条、分块也算条数**）——纠正时给机制，别只附和

## 🔴 通知路由：什么该走微信，什么不该（2026-10-21 用户明确定调）

用户原话：「后续如果再有备份失败这种事，应该是通过 telegram 通知我，而不是微信了」

| 类别 | 通道 | 例子 |
|:--|:--|:--|
| 日程 / 待办 / 复盘（秘书域） | **微信** | 07:30 早报、开始前 15 分钟提醒、21:30 收尾 |
| 运维 / 故障 / 备份 / 日报（总管域） | **Telegram** | git 备份失败、Memory 体检、API 健康、IP 监控、跨境与五类日报 |

**为什么不能混**：微信每轮只有 10 条额度。运维告警一旦堆在微信，会把真正要送达的日程提醒挤掉——
2026-10-20/21 实测就是备份失败通知和日程推送抢同一份配额，两边都可能丢。

### 🔴 审计陷阱：`deliver=origin` 的 origin 可能指向微信

只改 `deliver` 不够。`deliver=origin` 表示「投回任务创建时所在会话」——如果那个 origin 是微信，
任务照样往微信发，而 `hermes cron list` 里看不出异常。

```python
# 必须同时检查 origin.platform，不能只看 deliver
import json
d = json.load(open(r'C:\Users\Administrator\AppData\Local\hermes\cron\jobs.json', encoding='utf-8'))
for j in d['jobs']:
    o = (j.get('origin') or {}).get('platform')
    if j.get('deliver') == 'origin' and o == 'weixin':
        print('仍会投微信:', j.get('name'))      # ← 改 deliver 为 'telegram'
```

本机 2026-10-21 就是这么揪出两个漏网的：**Hermes Git 自动备份**、**每周 Memory 体检**，
两者都是 `deliver=origin` 且 origin=weixin，失败通知一直往微信发。
改完复查口径：`deliver=origin 且 origin=weixin` 的应剩 **0 条**。

> 新建运维类 cron 时**显式写 `deliver='telegram'`**，不要依赖 origin。

## 问题清单

| 问题 | 症状 | 根因 |
|:---|:---|:---|
| 长消息截断 | 超长回复后半段丢失 | 分 chunk 发送中间触发限流，熔断器拒绝后续 chunk |
| cron/会话撞车 | cron 通知 + 用户等待的回复同时丢失 | 两个调度源同时争夺 iLink 通道，触发限流后全部被熔断器拒绝 |
| 熔断器 "拒绝" 非 "等待" | 限流后消息永久丢失，不排队 | `_send_text_chunk_locked` 在熔断器打开时 `raise` 而非 `await asyncio.sleep` |

## 关键代码路径

### 发送链路

```
会话回复 → adapter.send() → _send_text_gate (锁) → _send_text_chunk → _send_text_chunk_locked
                                                                              ↓
cron 通知 → _deliver_result → adapter.send() ─────────────────────────────────┘
```

所有发送（会话 + cron）最终都走同一个 weixin 适配器的 `send()`，由 `_send_text_gate`（`asyncio.Lock`）串行化。

### iLink 限流常数

```python
# weixin.py
RATE_LIMIT_ERRCODE = -2       # iLink 频率限制返回码
BACKOFF_DELAY_SECONDS = 30    # 熔断器冷却时长
```

### 熔断器

```python
# weixin.py 1669-1698
_rate_limit_circuit_threshold       # 窗口内触发几次后打开（默认 1，即首次就开）
_rate_limit_circuit_window_seconds  # 计数窗口（默认 30s）
_rate_limit_circuit_open_seconds    # 冷却时长（默认 30s）
```

触发路径：`_send_text_chunk_locked` 收到 `errcode=-2` → `_record_rate_limit_event()` → 达到阈值 → `_open_rate_limit_circuit()` → 后续发送直接 `raise rate_limit_error()`。

### 瓶颈所在（weixin.py ~1735 行）

```python
# 当前行为：熔断器打开时直接抛异常
if self._rate_limit_cooldown_remaining() > 0:
    raise self._rate_limit_error()  # ❌ 消息永久丢失

# 应改为：等待冷却结束后继续发送
remaining = self._rate_limit_cooldown_remaining()
if remaining > 0:
    await asyncio.sleep(remaining)  # ✅ 排队等待，消息不丢
```

## 诊断流程

### 1. 确认是限流

```bash
grep -i "rate limit\|cooldown\|send failed" ~/AppData/Local/hermes/logs/gateway.log | tail -20
```

关键信号——同一秒出现两条错误：
```
15:14:55 ERROR [Weixin] send failed: iLink sendmessage rate limited; cooldown 30s
15:14:55 ERROR cron.scheduler: Job 'xxx': delivery error: Weixin send failed
```
第一行 = 会话发送失败，第二行 = cron 投递失败。同时出现 = **限流碰撞**。

### 2. 确认熔断器状态

```bash
grep "rate limit\|cooldown\|circuit" ~/AppData/Local/hermes/logs/gateway.log | tail -30
```

冷却中会出现连续 30 秒的 `cooldown active for XX.Xs`。

### 3. 确认触发源

```bash
# 看 cron 投递时间
grep "delivery error" ~/AppData/Local/hermes/logs/errors.log | tail -10

# 看 cron 执行时间
hermes cron list  # 检查 last_run_at 和 last_delivery_error
```

## 预防方案

### 短期（无需改代码）

| 方案 | 操作 | 效果 |
|:---|:---|:---|
| 凌晨错峰 | cron 改 3:00~4:00 | 用户睡觉时不碰撞 |
| 静默成功 | `no_agent` 脚本成功时 stdout 为空 | 成功不推送，失败才发一条 |

### 中期（配置调优）

在 `config.yaml` 的 `platforms.weixin.extra` 或环境变量：

| 参数 | 当前默认 | 建议 | 作用 |
|:---|:---|:---|:---|
| `send_chunk_delay_seconds` | 1.5s | 3.0s | 分 chunk 发送间隔更宽松 |
| `send_chunk_retries` | 4 | 3 | 减少重试次数，降低 iLink 压力 |
| `rate_limit_circuit_open_seconds` | 30s | 30s | 保持不变 |

### 长期（代码修复，已全部落地 2026.7.3）

**修复 #1 — 熔断记账延迟**（`weixin.py` L1782）：

经 Opus 4.8 红队审查，否决了直接改 `raise`→`await sleep`（方案A，致命缺陷×3）。最终落地**中期方案**——推迟熔断记账时机到"重试用尽后"：

```diff
-                            if self._record_rate_limit_event():
-                                last_error = self._rate_limit_error()
-                                break
                             if attempt >= self._send_chunk_retries:
+                                if self._record_rate_limit_event():
+                                    last_error = self._rate_limit_error()
                                 break
```

**效果**：首次限流走退避重试（而非丢弃），重试用尽后才记账+熔断。已验证生效（日志出现 `backing off 3.0s before retry`）。

**修复 #2 — 全局发送间隔**（`weixin.py` L1178-1181 + L1726-1727）：

日志复盘（22:26-22:35 事故）：即使修复 #1 生效，**连续多条独立回复间隔不到 1 秒**仍触发 iLink 限流，导致 9 分钟消息延迟。根因是**多条回复之间没有强制间隔**。

Opus 4.8 评估方案 A（调 chunk 间隔 1.5→5s）和方案 B（全局间隔），明确推荐 B。落地实现：

```python
# __init__ — 新增参数（env var 或 config extra，默认 3s）
self._send_interval_seconds = float(
    extra.get("send_interval_seconds")
    or os.getenv("WEIXIN_SEND_INTERVAL_SECONDS", "3.0")
)

# _send_text_chunk — 锁内 sleep（强制串行 + 间隔）
async with self._send_text_gate:
    await self._send_text_chunk_locked(...)
    if self._send_interval_seconds > 0:
        await asyncio.sleep(self._send_interval_seconds)
```

**⚠️ 关键教训**：sleep 必须在锁**内**（async with 块内）。第一版实现放锁外 → 千问 L1 审查指出并发场景间隔失效。速率控制的本质是阻塞后续发送，锁外 sleep 无法保证全局间隔。

### 速率控制与熔断器的关系

| 机制 | 管什么 | 时机 | 局限性 |
|:---|:---|:---|:---|
| `send_chunk_delay_seconds` (已有) | 同一条消息的 chunk 间 | chunk→chunk | — |
| `WEIXIN_SEND_INTERVAL_SECONDS` (新增) | **所有**发送之间 | 任何两次 sendmessage | 防 burst，不防 iLink 已进入惩罚期 |
| 熔断器退避 (已有, 修复#1) | 被限流后的重试 | 已触发限流后 | threshold=1 导致死亡螺旋（见下方） |

三者配合：间隔控制**预防**限流 → 万一还是触发 → 退避重试**兜底** → 重试用尽 → 熔断器**最后防线**。（⚠️ 但当 iLink 处于长期惩罚期时，熔断器本身成为新问题——见下方。）

### ⚠️ 熔断器死亡螺旋（2026.7.3 — 后确认为 context_token 10 条额度耗尽）

> **更新**：后续发现真正根因是 context_token 10 条回复额度（见上文平台硬限制），而非 iLink 速率限流。以下分析保留作为排查历史参考。

`_rate_limit_circuit_threshold = 1`（默认值）导致以下循环：

```
发送 → iLink 限流(-2) → 4次重试失败 → 记录事件 → threshold=1 → 开闸30s
   ↓
30s 后闸关 → 第一条发送又被 iLink 限流 → 再开闸30s → 无限循环
```

**症状**：日志显示连续数分钟所有发送失败，无一条送达。如 `23:15:44` 到 `23:16:58` 和 `23:33:23` 到 `23:35:53` 两次事故——两次都是 Agent 静默工作 6 分钟后尝试发送，首次就被 iLink 限流，然后熔断器死亡螺旋阻止了所有后续消息。

**根因**：iLink 的限流不是简单的 30s 冷却，而是**累积配额耗尽后的长期惩罚期**（可能小时级）。熔断器 threshold=1 意味着一次 iLink 限流就封锁整个通道 30s，但 30s 后 iLink 还没解除惩罚，于是下一发立即触发新封锁。

**缓解方向**（尚未落地）：
- 提 threshold 到 3-5（容忍偶然限流，不封锁通道）
- 加指数退避（开闸时间逐次延长）
- 或改为等待模式（不拒绝，排队等待 iLink 冷却）

### 媒体文件绕过间隔锁（2026.7.3 发现）

`send()` 方法（L1860-1864）先发媒体附件，**不走 `_send_text_chunk`**，不使用锁或间隔：

```python
async def send(...):
    for media_path, is_voice in media_files:
        await _deliver_media(media_path, is_voice)  # ← 直接 iLink，无节流
    # 然后才发文本（走锁+间隔）
```

**影响**：MEDIA: 文件发送 + 紧接文本发送 = 两次 iLink 调用间隔可能 < 1s，增加触限概率。

## 已落地实例（2026.7.3）

| 配置项 | 值 |
|:---|:---|
| 备份 cron ID | `5b4b88f1f8bf` |
| 备份脚本 | `backup_git.py`（`.py` — `no_agent` cron 在 Windows 上必须用 Python） |
| 执行时间 | `0 8 * * *`（每天 8:00。凌晨错峰方案已讨论但未执行，错峰可进一步降低碰撞概率） |
| 投递策略 | ~~`deliver='weixin'`~~ → **2026-10-21 已改 `deliver='telegram'`**（微信只留日程提醒，见上方「通知路由」） |
| 脚本位置 | `~/AppData/Local/hermes/scripts/backup_git.py`（**不是** `~/.hermes/`，后者在 Windows 下不存在） |

## 相关技能

- `hermes-backup` — 备份 cron 配置、投递策略选择、故障排查
- `gateway-setup` — 微信网关初始配置（bundled skill）
- `claude-code-workflow` — Rule 0 代理要求、Opus 调用流程

## 支持文件

- `references/weixin-adapter-code-walkthrough.md` — weixin.py 发送链路完整代码走读（`send()` → `_send_text_chunk` → `_send_text_chunk_locked` → 熔断器 → cron 投递路径）
