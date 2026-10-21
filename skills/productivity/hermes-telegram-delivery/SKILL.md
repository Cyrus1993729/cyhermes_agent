---
name: hermes-telegram-delivery
description: "Use when Telegram 消息丢失/只收到几个字。诊断 gateway.log，Bot API 补发。"
category: productivity
tags: [hermes, telegram, delivery, debugging, send_path_degraded]
---

# Hermes Telegram 投递可靠性与补发

主通信平台的投递排障（微信 iLink 已弃用，历史见 `hermes-wechat-delivery`）。

## 第一诊断规则（最重要）

Telegram 上「长回复只收到几个字 / 开头片段」**≠ 内容被截断**。
真实语义 = **整条投递失败 + 流式预览残留**（预览消息编辑失败，停在最早推送的片段）。
行动顺序：先 grep gateway.log 查发送结果，再谈分块/长度。

**另一种症状（2026-10-07）：「用户说『你怎么没回答我 / 我没收到』」**
这**不等于**回答没生成。常见真相是：回答已完整生成，但**最终发送整条失败**，且没有流式预览兜底 → 用户界面上完全空白，所以听起来像「你压根没理我」。
同样先 grep 日志确认，再决定是**补发**还是**重答**——**不要一上来就重新回答一遍**（浪费一轮，用户更困惑）。
判定链：`response ready: ... response=2295 chars` + `Failed to deliver response after 2 retries: send_path_degraded` = 内容存在、只是没送到 → 走补发。
文本不用重新研究：它还在你自己的会话上下文里，直接重建补发即可。

关键日志模式（gateway.log）：

```
[Telegram] Send failed (attempt 1/2, retrying in 2.4s): send_path_degraded
[Telegram] Send failed (attempt 2/2, retrying in 4.4s): send_path_degraded
ERROR [Telegram] Failed to deliver response after 2 retries: send_path_degraded
[Telegram] Transient network error editing message <id>  ← 预览残留，误导用户以为"截断"
```

前置信号：最近几分钟多条 `Telegram network error (attempt 1/10) ... httpx.ConnectError` 或 `polling degraded` → 线路抖动中，此时长回复极易整条丢。

## 根因（2026-10-08 定位到具体一层，此前只知道「抖动」）

完整链条，四步：

1. **不是线路质量问题。** 同一代理下 google 100/100、github 100/100、50MB 下载、40 路并发全通过。
2. **只有 `api.telegram.org` 这个端点会挂。** 对照：`core.telegram.org` 0/80、`telegram.org` 0/80、`t.me` 0/80 全通。
3. **挂的是某一个 IP。** `api.telegram.org` 只有一个 A 记录 `149.154.166.110`，从本机 VPS 出去约 **3-11% 的新建连接在 TLS 握手阶段被掐断**（`SSL: UNEXPECTED_EOF_WHILE_READING`）；Telegram 的另一个 Bot API 入口 `149.154.167.220` 是 **0/160**。
4. **只影响新建连接，复用连接不受影响**（keep-alive 对照 7/7 全通，每次新建的对照 5 次挂 1 次）。而适配器**故意关掉了 getUpdates 的连接复用**（`max_keepalive_connections=0`，防止拿到上轮僵尸连接）→ 每次轮询都新建 → 一天踩雷约 900 次。

失败的代价：踩雷后适配器重连，重连期间 `send_path_degraded=True`（接收路径未证实）→ `send()` 直接拒绝；重试 2 次、总窗口约 7s **< 重连恢复 7-11s** → 落在窗口里的最终回复整条丢。
（2026-09-03 首次记录；2026-10-08 用「并发剂量效应 + 连接复用对照 + 逐 IP 对照」把根因钉到单点 IP。）

**关键结构性事实：失败回复是落盘的，不是没救。**
`~/AppData/Local/hermes/state.db` → 表 `delivery_obligations` 会存下每一条未确认送达的最终回复**全文** + `last_error`（本类失败 = `send_path_degraded`）。
但核心自带的补发只在两种时机触发：①网关重启（`sweep_recoverable`）②适配器被整体重建（`sweep_failed_for_runtime`，白名单就是 `send_path_degraded`）。
「几十秒自己缓过来」的情况两种都不触发 → 记录烂在库里直到 24h 过期变 `abandoned` → 消息永久丢失。**这就是空档，看门狗补的就是它。**

查台账：

```bash
python -c "import sqlite3,os;c=sqlite3.connect(os.path.join(os.environ['LOCALAPPDATA'],'hermes','state.db'));\
print(c.execute(\"SELECT obligation_id,chat_id,state,attempts,datetime(created_at,'unixepoch'),length(content) FROM delivery_obligations WHERE state!='delivered' ORDER BY created_at DESC LIMIT 10\").fetchall())"
```
（`datetime(...,'unixepoch')` 输出的是 **UTC**，比本地时间少 8 小时，别当成时钟异常。）

## 核验「本人某条 Telegram 指令到底执行没执行」（读侧审计，2026-10-21 定型）

对端或用户问「你收到没有 / 真查了没有 / 真保存没有」时，四段证据缺一段就不能说「做了」：

1. **收到**：`grep -a 'inbound message' gateway.log | grep <chat_id> | tail` → 命中 `inbound message: platform=telegram user=<名> chat=<id> msg='<原文>'` + 时间。
2. **跑完并投递**：同文件稍后的 `response ready: platform=telegram chat=<id> time=Ns api_calls=N response=N chars`；若伴随 `Suppressing normal final send ... content_delivered=True`，说明流式已确认送达。**没有 response ready 行 = 这一轮还没结束**，不能说完成。
3. **真调了接口**：去 `state.db` 找该会话的 tool 行，读 `content` 里的工具回执原文（`{"status":"saved",...}`、命中条数等）。只认回执，不认 assistant 自述、不认「我做过」。
4. **此刻状态**：再查一次真实数据源（items/API/文件），回报「现在读数」而不是「当时说过」。

```python
import sqlite3, os, datetime
p = os.path.join(os.environ['LOCALAPPDATA'],'hermes','state.db')
c = sqlite3.connect(p)
for r in c.execute("select id,role,tool_name,timestamp,substr(content,1,200) from messages where content like '%关键词%' order by timestamp desc limit 20"):
    print(r[0], r[1], r[2], datetime.datetime.utcfromtimestamp(r[3]+8*3600), r[4])
```

会话定位：`select id,source,chat_id,display_name,last_activity_at from sessions where chat_id='<chat_id>'`；取末尾用 `order by id desc`。

坑：
- `messages` 表**没有 created_at**，只有 `timestamp`（epoch 秒、浮点）；`datetime.utcfromtimestamp(ts+8*3600)` 才是北京时间。
- `tool_calls`、`api_content` 两列常为空 → **原始命令还原不出来**，只能用 tool 行的回执内容反推做了什么。
- 主机 `date` 不认 `TZ=`（`TZ=Asia/Shanghai date` 仍返 UTC 却标 GMT）→ 和对端的 `Z` 时间比对时自己 +8h，别把 00:09Z 当 08:09Z。
- 在 `~/AppData/Local/hermes` 整个目录 `search_files` 会超时（state.db 600MB+）→ 只搜具体日志文件，或直接上 SQL。
- 用户消息行的 timestamp 可能**晚于**当轮回复（落盘/重写时机），不是异常。

## 主动发一条给指定人：首选 `hermes send`（2026-10-21 实测最省事）

一次性主动推送（发链接、发授权码、发提示）**先用这条**，不必碰 token、不必碰代理参数：

```bash
hermes send --to telegram:8938729624 --file msg.txt --json
# → {"success": true, "platform": "telegram", "chat_id": "8938729624", "message_id": "6882", "mirrored": true}
```

- `--to telegram` 走 home channel；`--to telegram:<chat_id>` 指定私聊；`-f -` 读 stdin；`--json` 拿 `message_id` 当交付证据。
- 它复用 `.env` 里的真 token，**纯文本发送、不带 `parse_mode`** → URL 里的 `&` **不用转义**（下方坑位 9 那个坑不存在）。含长 URL 的授权链接优先走它。
- 失败会 exit 1，比裸 curl 好判（不要再手写 `api.telegram.org/bot<token>/sendMessage`：config.yaml 的 token 是 14 字符占位符，直调必 404 白跑一轮）。

## 补发（绕开网关，直连 Bot API）

`scripts/tg_resend.py` 可复用：

```bash
python tg_resend.py <msgs.json> [chat_id]
# msgs.json = JSON 字符串数组，每条一条消息；chat_id 缺省取 .env 的 TELEGRAM_HOME_CHANNEL
```

要点与坑：
1. **token 从 `~/AppData/Local/hermes/.env` 的 `TELEGRAM_BOT_TOKEN` 读**。config.yaml 里的 `telegram.token` 是残缺占位符（14 字符），直调 API 返回 404——勿用。
2. 走代理 `http://127.0.0.1:10808`（`HERMES_TG_PROXY` 可覆盖）。
3. 补发本身也撞抖动（`SSL: UNEXPECTED_EOF_WHILE_READING`），脚本已带 10 次重试 / 4s 间隔。
4. `parse_mode=HTML`（比 MarkdownV2 省事），文本里的 `& < >` 要转义。
5. 长回复拆 3-4 条（≤1500 字/条），单条失败只损失一块，不会整条丢。实测 4 条（197/810/740/685 字）一次全过（2026-10-07）。
6. **HTML 模式下 `**加粗**` 不生效**：正文要改写成 `<b>…</b>`，项目符号用 `•`，路径/命令用 `<code>`——否则补发出去的消息里会裸露一堆星号。
7. **不要现场手写补发脚本**：先加载本 skill，用现成的 `scripts/tg_resend.py`（吃 msgs.json）。2026-10-07 那轮因为没先加载本 skill，重写了一份等价脚本，纯浪费。
8. **它也是「主动发一条给指定人」的首选通道**（不只是补发）：把要发的文本写成 `["<html>"]` 的 json，第二个参数传目标 `chat_id`（如本人 Home 会话），成功输出 `chunk 1: OK msg_id=<id>` —— 把 `msg_id` 当交付证据记下来。不碰 gateway、不受会话上下文限制。
9. 🔴 **发链接必须自己转义 `&`**：`tg_resend.py` 固定 `parse_mode=HTML` 且**不做任何转义**，URL 里的每个 `&` 要写成 `&amp;`，否则 query 参数会被吃掉（实测发钉钉设备授权链接就靠这条）。

## 自动补发看门狗（2026-10-08 已上线，方案B）

`~/AppData/Local/hermes/scripts/tg_delivery_watchdog.py` —— **纯外围脚本，不碰 Hermes 核心**。

它做什么（每分钟一次，schtasks `hermes_tg_delivery_watchdog`）：

1. 扫 `delivery_obligations`，只接管 `platform='telegram'` + `last_error='send_path_degraded'` + `state='failed'` + 失败已超 60s（留给网关自己的重试/重建窗口）+ `attempts<3` + 24h 内
2. 原子认领（`UPDATE ... WHERE state='failed'` 靠 rowcount 判胜负），避免和网关/并发实例双发
3. 经 `127.0.0.1:10808` 直连 Bot API 补发，10 次重试、4s 间隔、>4000 字分块、`parse_mode` 不带（纯文本最稳）
4. 成功 → 标 `delivered`（网关后续 sweep 找不到它 → 不会重复）；失败 → 退回 `failed` 等下轮

日志：`~/AppData/Local/hermes/logs/tg_delivery_watchdog.log`（每轮一行 `扫描完成: 待接管 N 条`）。
上限与核心台账一致（attempts 3 / 24h），所以**最多补 3 次，不会无限重发**。

管理：`schtasks /Change /TN hermes_tg_delivery_watchdog /DISABLE`；删除 `/Delete /F`；立即跑一次 `/Run`。

重装/迁移本机时：`scripts/tg_delivery_watchdog.py` 拷到 `hermes/scripts/`，再用 **.bat** 注册（见坑位 4）。

**补发会带 `♻️ 自动补发…可能重复` 标记**——这是故意的（at-least-once 诚实话术），不是 bug。

## 严格按顺序：先标掉已处理的，再测补发工具

跑任何会「接管并重发」的工具（看门狗、手工补发脚本）**之前**，先把台账里已经被你手动补发过的行标成 `delivered`。
2026-10-08 实测踩坑：dry-run 已经列出那条昨晚手动补过的记录，我直接跑实测 → 看门狗把整条 2295 字的旧回答又发了一遍给用户，纯重复。

```bash
python -c "import sqlite3,os;c=sqlite3.connect(os.path.join(os.environ['LOCALAPPDATA'],'hermes','state.db'));\
c.execute(\"UPDATE delivery_obligations SET state='delivered' WHERE obligation_id=?\",('<oid>',));c.commit()"
```

## 汇报口径（本用户）

诊断类结论按三层交付，别只给一层：

1. **结论先行**（一两句，直接说「不是你的线路问题，是 X」）
2. **数据**（对照组 + 数字，用户重推导过程，不吃「应该/可能」）
3. **通俗比喻版**——本用户**会主动追问「用通俗易懂的话解释一下」**（2026-10-08）。所以主动把术语翻译掉：IP 说「门牌号」、TLS 握手失败说「接通了但握手的功夫被掐断」、重连窗口说「这 8 秒里它不敢发消息」。术语可以留，但每个都要有一句白话跟随。

## 诊断步骤速查

0. **如果报的是「cron 日报没收到」**（不是交互回复）→ 跳过 gateway.log，直接查 `cron/jobs.json` 的三个状态字段，见下面「验证 cron 任务的投递是否成功」一节
1. 用户报「只收到几个字」→ `grep -E "Failed to deliver|send_path_degraded|editing message" gateway.log | tail`（当前 + 归档两侧都查，见下节）
2. 确认 `send_path_degraded` → 按上面补发
3. 顺带看最近是否连续 ConnectError，判断抖动是否还在持续，决定补发时机
4. 复盘归档到 `D:\Workspace\Projects\Hermes运维\`，文件名 `复盘_YYYY-MM-DD_主题.md`

## 日志轮转与时间判断陷阱（2026-10-07 实测）

- 判断「现在几点 / 日志最新在哪」前先 `ls -lt ~/AppData/Local/hermes/logs/`：gateway.log 超 ~5MB 会轮转到 gateway.log.N，**会话可能横跨数周**（本实例 9/15 → 10/7 隔了 22 天）。只 tail 当前文件会误判「这条消息根本没发过」。
- **看到日期对不上先查归档再下结论**：grep 归档 .1/.2 + 比对文件 mtime，别急着宣布「时钟异常」。本实例曾把「旧会话日志在轮转归档里」误判成「系统时钟跳变」，白费一轮排查。
- 端到端验证「某条消息发没发出」：`grep -n "<关键句>" gateway.log gateway.log.1` 两侧都查，归档命中 = 已发送过。
- 归档证据可交叉确认会话时间线：9/15 的用户消息在第 15470 行找到于 gateway.log.1，同时 `date` 返回 10/07 23:11 —— 两者都对，中间是轮转 + 关机空档，不是时钟错。

## 验证 **cron 任务**的投递是否成功（2026-10-18 实测；不能 grep gateway.log）

🔴 **Telegram 投递成功不打日志**（全历史 grep 含 Telegram 的投递成功行为 **0 条**）。
所以对 cron 任务，「grep gateway.log 找发送记录」这条路**无效**——**grep 不到 ≠ 没发出去**，据此报「投递失败」是误判。
（上一节说的「grep 关键句，归档命中 = 已发送过」只适用于**交互会话的最终回复**，它会有 `response ready: ... response=N chars` 之类的行；cron 投递没有。）

**cron 投递的唯一真相源 = `cron/jobs.json` 里该 job 的三个字段**：

| 字段 | 语义 |
|:--|:--|
| `last_status` | `ok` / `error` / `delivery_failed` |
| `last_delivery_error` | 非 `None` = 真失败（带平台报错原文，如 iLink `errcode=-14 session timeout`） |
| `last_delivery_unverified` | **「无法确认送达的目标列表」**（`platform:chat_id` 形式）；**`None` = 全部确认送达** |

```python
import json
d = json.load(open(r'C:\Users\Administrator\AppData\Local\hermes\cron\jobs.json', encoding='utf-8'))
# ⚠️ jobs.json 顶层是 {"jobs": [...], "updated_at": ...}，job 的 id 在 "id" 键（不是 job_id）
for j in d['jobs']:
    if j.get('id') == JOB_ID:
        print(j['last_status'], j['last_delivery_error'], j['last_delivery_unverified'])
```

判据：
- `ok` + 两个 `None` → **送达** ✓
- `delivery_failed` + `last_delivery_error` 有值 → **没送达**（走上面的补发流程）
- `ok` 但 `last_delivery_unverified` 有值 → 发出去了但**没拿到回执**，**别报成功**

**链路在日志里的唯一足迹**（只证明「已交给分段投递器」，**不代表送达**）：
```
INFO gateway.delivery: Cron output preserved for chunking adapter (6361 chars) — full output saved to ...\cron\output\<job_id>_<ts>.txt
```

**交叉核对（「没丢消息」的旁证）**：`logs/tg_delivery_watchdog.log` 每行的 `待接管 N 条`；持续 `0` = 没有遗留待补发的消息。同时段 `logs/errors.log` 无投递报错也一并看。

> 验证时**别只看 cron 自报的 result**（`cronjob(action="run")` 回执与后台完成通知都会说 `Result: ok`）——那只说明 job 跑完了，不代表消息到了用户手机上。

## cron 任务失败后的补跑流程（2026-10-18 实测定型）

日报类 job 因为 key/网络挂掉后补跑，**动手前先查三件事，不然会白跑或重复推**：

1. **先确认 job 有没有幂等短路**：读 `cron/jobs.json` 里该 job 的 `prompt`，搜 `幂等` / `已存在` / `SILENT`。
   本机现状：五类日报 **没有**幂等短路（可直接补跑）；跨境日报是 `30,40 20 * * *` **双触发 + 幂等**（补跑要小心重复）。
2. **检查上次失败留下的产物**：去 `cron/output/<job_id>/` 看当天那个文件。失败记录长得像正常报告（有 `## Prompt`、几十 KB 上下），但内容其实只是 **prompt 回显 + `# Cron Job: ... (FAILED)`**、没有 `## Response` 段 → **不是半成品报告，不会污染**，可以直接重跑。**判据 = 有没有 `## Response`**。
3. **检查状态文件有没有被写脏**：日报类 job 会在项目里维护去重清单（如 `D:\Workspace\Projects\TrendRadar\pushed_five.json`）。看它的 **mtime**——若停在**上一次成功运行**的时间，说明失败那次没写脏，补跑会把这段窗口的新闻全部当新事件捞回来（不漏）。

然后 `cronjob(action="run", job_id=<id>)` 触发，**跑完按上一节的三字段验证送达**，不要只看 `Result: ok`。

另一个坑：**手动 run 的 delivery target 是 `origin`**（= 发起它的那个会话），所以补跑的报告会发到当前对话，不是 home channel。

## 支持文件

- `references/telegram-delivery-debug.md` — 2026-09-15 实战：症状→语义对照、日志证据、补发坑位
- `references/bot-api-ip-routing-diagnosis.md` — 2026-10-08 完整诊断法：并发剂量效应 / 连接复用对照 / 逐 IP 对照，含全部实测数字与判定阈值
- `scripts/tg_resend.py` — 直连 Bot API 补发脚本（每次现用现跑，勿手写）
- `scripts/tg_delivery_watchdog.py` — 自动补发看门狗（已部署到 `hermes/scripts/`，此处为可重建副本）
- `scripts/probe_tg_path.py` — 线路抖动定位探针（多目标 + 逐 IP 失败率），判定「是线路还是单点」

## 坑位（本类任务专属，2026-10-08 实付）

1. **不要用真 token 起第二个 getUpdates 探针** —— 会和正在跑的网关抢更新。探测只用无效 token（返回 401 也照样走完 CONNECT+TLS 全链路），或直接打 `https://api.telegram.org/` 根路径。
2. **采样太少会得出完全相反的结论**：串行 75 次探测 0 失败，结论「线路很稳」是错的——真实失败率 ~1-5%，要 **300-400 次采样**（并发 20 约 30 秒跑完）才看得见。**判「线路没问题」必须配对照组**（google/github/其它 telegram 子域），否则分不清是线路、是目标、还是单点。
3. **失败的 `httpx.ConnectError` 消息在日志里被 token 脱敏成空串**，看不到底层 errno。要真错误类型就自己复现同样的调用（见 `references/bot-api-ip-routing-diagnosis.md`），别对着空消息猜。
4. **MSYS bash 下 `cmd //c "schtasks /Create ..."` 会被参数转义破坏**（报 `'reate' 不是内部或外部命令`，或干脆开出交互 cmd）。可靠做法：把命令写进 `.bat` 文件，然后直接 `./x.bat` 执行——git-bash 会自动用 cmd 跑它，参数一个都不会被转。
5. 补发/看门狗都会**真发消息给用户**，测试前按上一节先把已处理的行标掉。

## 仍然开放（未落地，可选）

- **根治抖动**（治本）：VPS 上把 `api.telegram.org` 钉到 `149.154.167.220`（`/etc/hosts`，或 xray 的 `dns.hosts`——若 xray 配了自己的 DNS，`/etc/hosts` 不生效，可用 nftables 把去 `.166.110` 的流量转走）。已验证两个 IP 调 `getMe` 都返回 200 同一个 bot，钉过去可用。等用户给 SSH 才动。
- 网关侧 `send_path_degraded` 重试窗口（当前 ~7s）仍偏短；但看门狗已覆盖该空档，优先级下降。
- 上述路由问题是会变的：今天坏 `.166.110`，明天可能轮到别的 IP——所以**看门狗比钉 IP 更耐久**，两者共存最好。
