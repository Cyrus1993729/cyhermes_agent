---
name: gateway-setup
description: "Connect messaging platforms (WeChat, Telegram, Discord, etc.) to Hermes gateway — interactive setup, Windows quirks, credential flows."
version: 1.1.0
author: agent
platforms: [windows, linux]
metadata:
  hermes:
    tags: [gateway, setup, messaging, wechat, weixin, platforms, windows, troubleshooting, proxy]
    related_skills: [hermes-agent]
---

# Gateway Platform Setup

Connect messaging platforms to the Hermes gateway. Covers the interactive setup
wizard, platform-specific credential flows, and Windows-specific pitfalls that
break interactive terminal workflows.

## Trigger Conditions

Load this skill when:
- User wants to connect a messaging platform (WeChat, Telegram, Discord, etc.)
- User asks about `hermes gateway setup`
- Platform login/QR flows require interactive terminal handling
- Running on Windows and interactive PTY commands fail with encoding errors

---

## General Workflow

### 1. Check Dependencies

Each platform has its own Python dependencies. Install into the Hermes venv:

```bash
uv pip install <packages> --python "$HERMES_HOME/hermes-agent/venv/Scripts/python.exe"
```

On Windows, the Hermes venv is stripped of pip — `uv pip install` is the
reliable way to add packages. Do NOT use `pip install` or `python -m pip`.

### 2. Check Gateway Status

```bash
hermes gateway status
```

If the gateway is running, it needs a restart after adding a new platform.

### 3. Run Platform Setup

For most platforms, the interactive wizard is the standard path:

```bash
hermes gateway setup
```

However, on Windows this often fails due to PTY encoding issues (see pitfalls).

### 4. Update Config + Restart

After credentials are obtained, ensure `config.yaml` has the platform entry
and restart the gateway:

```bash
hermes gateway restart
```

---

## WeChat / Weixin (iLink Bot API)

Hermes connects to personal WeChat accounts via Tencent's iLink Bot API.
Uses long-polling — no public endpoint or webhook needed.

### ⚠️ 平台硬限制：10 条回复额度

微信 iLink 有**每条用户消息只能回复 10 条**的 context_token 配额限制。
超 10 条后所有发送失败，直到用户发下一条新消息刷新 token。
这是平台硬限制，无代码层面绕过方法。

**推荐**：重度使用场景建议接入 Telegram（无此限制，Hermes 支持最成熟）。
详见 `hermes-wechat-delivery` skill。

### Dependencies

```bash
uv pip install aiohttp cryptography qrcode --python "$HERMES_HOME/hermes-agent/venv/Scripts/python.exe"
```

### QR Login Flow — 二维码约 90 秒，而且**可以全自动**

🔴 **2026-10-18 实测更正**：本 skill 之前的版本写「iLink 二维码只活 ~4-5 秒、
必须用户自己在自己终端跑 `hermes gateway setup`」——**那是错的**。
三张码实测存活 **121s / 92s / 92s**，而且整套绑定流程可以由 agent 全自动完成，
不需要用户进终端。

**可行方案：agent 自动补发循环 + 直接把二维码推到 Telegram**

1. `GET /ilink/bot/get_bot_qrcode?bot_type=3` 拿码（GET，只需 `iLink-App-Id` +
   `iLink-App-ClientVersion` 两个头，**不要 token**）
2. 🔴 **发码前先自检** `get_qrcode_status?qrcode=<token>` 应返回
   `{"ret":0,"status":"wait"}`。URL 拼错会让轮询全 404、用户白扫一次；
   先自检就不会发出接不住的码。
3. `qrcode` 库生成 PNG → 用 `hermes send --to telegram "..."`，消息里带
   `MEDIA:<png>` 直接推给用户。**不要靠主 agent 转发**——每轮回复十几秒的延迟
   会把二维码寿命吃掉一半。`hermes send` 无 LLM 延迟。
4. 轮询 status（每张码最长约 130s）：
   - `scaned` → **立刻再推一条「马上在微信里点确认」**。这是最常卡住的一步：
     用户扫上了但没点确认，状态会一直停在 `scaned` 直到过期。
   - `expired` → 补发下一张
   - 拿到 `ilink_bot_id` / `bot_token` → 写结果文件并退出
5. 循环 12 轮左右，首条消息里写明轮数，避免无限刷屏。

**扫不上不是码的问题，是节奏问题**：每张码从发出起只剩 90 秒，用户必须「看到即扫」。
实践中最有效的一句话是：
> “把手机拿在手上、微信停在『扫一扫』界面等着；看到新码立刻扫，扫完立刻点确认。”

**完整实战细节（请求头陷阱、扫码结果丢失后的二维码反解补救、时间线）见**
`hermes-wechat-delivery` 的 `references/ilink-rebind-2026-10.md`。

### 🔴 重新绑定后必须重启 gateway（否则改了也没用）

`WeixinAdapter.__init__` 在启动时就把 token 读进实例属性（`self._token`），
**改 `.env` 不会热重载**——这点和 cron tick 每次重读 `.env` 的机制**不同，别搞混**。
所以重新扫码、换了 `WEIXIN_TOKEN` 之后，运行中的 gateway 里微信通道仍然是死的
（表现为 `[Weixin] Session expired; pausing for 10 minutes` 继续刷）。

- ✅ **最稳**：让用户在 Telegram 发一句 `/restart`（gateway 内置斜杠命令，优雅重启）
- ⚠️ 备用：杀 PID + `schtasks /run /tn Hermes_Gateway`；
  注意 `hermes gateway restart` / `stop` 在 gateway 进程内会被安全防护 **BLOCKED**

**重启之前就能验证绑定是否真的成功**——新进程会重新读 `.env`：
```bash
hermes send --to weixin "微信通道测试" --json
# 期望 {"success": true, "platform": "weixin", "chat_id": "...@im.wechat", ...}
```
这条通了 = 绑定确实成功，剩下的纯粹是「让 gateway 用上它」的运维问题，
与绑定本身无关。**重启后用 gateway.log 的 `inbound` / `Sending response` 做真实往返验证。**

### 诊断「iLink 会话超时」（`errcode:-14`）时的假阳性陷阱

验证 token 是否有效时，iLink 的 POST 接口**必须带齐** `AuthorizationType: ilink_bot_token`、
`X-WECHAT-UIN`（随机数字串）、body 里的 `base_info: {channel_version: ...}`、
以及 `iLink-App-Id` / `iLink-App-ClientVersion`。
**漏任何一个，返回的错误和「会话真过期」一模一样（`errcode:-14 session timeout`）** ——
会把「我请求写错了」误判成「token 也挂了」，从而错误地否掉重扫码方案。
正确格式下的成功响应：`{"msgs":[],"sync_buf":"...","get_updates_buf":"..."}`。

### Config After Successful Login

```yaml
platforms:
  weixin:
    enabled: true
    token: "<token-from-qr-login>"
    extra:
      account_id: "<account-id-from-qr-login>"
      base_url: "https://ilinkai.weixin.qq.com"
      dm_policy: "open"
      group_policy: "disabled"
```

Credentials are auto-saved to `~/.hermes/weixin/accounts/<account_id>.json`
by the `qr_login()` function in `gateway/platforms/weixin.py`.

### Programmatic QR Login (for scripting)

The `qr_login()` function in `gateway/platforms/weixin.py` can be called
directly. See `scripts/weixin_qr_login.py` for a complete script that
fetches a QR code, polls for scan, saves credentials, and updates config.

---

## Telegram (Bot API)

Hermes connects to Telegram via the Bot API. **In China, Telegram is blocked —\nthe bot MUST connect through a proxy.** The adapter auto-detects proxy from\n`TELEGRAM_PROXY` env var or `HTTP_PROXY`/`HTTPS_PROXY`, but setting it in\n`config.yaml` is more reliable across gateway restarts.

### Quick Setup (`.env` method, 2026-07-23 verified)

The simplest path — token and allowed users in `.env`, platform already enabled
in `config.yaml`:

```bash
# .env
TELEGRAM_BOT_TOKEN=8839546337:AAH...
TELEGRAM_ALLOWED_USERS=8938729264
```

In `config.yaml`:
```yaml
platforms:
  telegram:
    enabled: true
```

No `proxy_url` needed — v0.19.0 auto-discovers proxy from `HTTP_PROXY`/`HTTPS_PROXY`
and uses DNS-over-HTTPS to find Telegram API fallback IPs, bypassing DNS pollution.

Then install as auto-start:
```bash
hermes gateway install   # Creates Windows Scheduled Task 'Hermes_Gateway'
```

Log verification (should show proxy detection + connection):
```
[Telegram] Discovering Telegram API fallback IPs via DNS-over-HTTPS…
[Telegram] Auto-discovered Telegram fallback IPs: 149.154.166.110
[Telegram] Proxy detected; passing explicitly to HTTPXRequest: http://127.0.0.1:7897
[Telegram] Connected to Telegram (polling mode)
✓ telegram connected
```

### Full Config (config.yaml method, more explicit)

For explicit proxy control:

```yaml
# Both sections are needed — adapter reads from platforms.telegram
telegram:
  enabled: true
  token: "1234567890:ABCdef..."
  proxy_url: "http://127.0.0.1:7897"    # ← critical for China users
  reactions: false

platforms:
  telegram:
    enabled: true
    token: "1234567890:ABCdef..."
    proxy_url: "http://127.0.0.1:7897"    # ← critical for China users
```

The adapter reads `proxy_url` from the telegram config section and internally
sets `TELEGRAM_PROXY` before connecting. The `resolve_proxy_url` check order:
`TELEGRAM_PROXY` env var → `HTTP_PROXY`/`HTTPS_PROXY` → macOS proxy.

### Prerequisites

```bash
uv pip install python-telegram-bot httpx --python "$HERMES_HOME/hermes-agent/venv/Scripts/python.exe"
```

No additional dependencies needed — the Telegram adapter is bundled.

### Creating a Bot

1. Open Telegram, find @BotFather
2. Send `/newbot`
3. Follow prompts (name can be Chinese, username must end in `bot`)
4. Copy the token (format: `1234567890:ABCdef...`)
5. Never share the token — anyone with it controls your bot

### Pairing Approval (First-Time User)

When an unrecognized user sends a message, the bot replies with:

> "Hi~ I don't recognize you yet! Here's your pairing code: XXXXXXXX
> Ask the bot owner to run: hermes pairing approve telegram XXXXXXXX"

The bot owner runs:
```bash
hermes pairing approve telegram <pairing_code>
```

After approval, the user is recognized on their next message. This prevents
unauthorized access to your Hermes agent.

### Troubleshooting

#### Token rejected by server (`InvalidToken: Not Found`)

Log shows: `The token was rejected by the server.`

This is NOT a network/proxy issue — the request reached Telegram's servers
but the token is invalid. Causes:
- Token was copied incorrectly from @BotFather
- Token was revoked
- Token was never valid

**Fix**: Go to @BotFather → `/mybots` → select bot → `API Token` → copy
the fresh token → update both telegram sections in config.yaml.

#### Connection timeout (`httpx.ConnectError`)

Log shows: `Primary api.telegram.org connection failed` + `Fallback IP ... failed`

This IS a proxy issue — Telegram's servers are unreachable directly from
China. Check:
1. `proxy_url` is set in BOTH telegram config sections
2. Clash Verge is running and proxy port is listening (`netstat -ano | grep :7897`)
3. `api.telegram.org` is NOT in NO_PROXY list

#### Proxy detected on one restart but not another

The adapter reads `HTTP_PROXY`/`HTTPS_PROXY` from environment at startup.
If the gateway was started from a terminal that had these set, but the
desktop app restarts without them, the proxy disappears.

**Fix**: Don't rely on environment variables. Set `proxy_url` explicitly in
config.yaml under both `telegram:` and `platforms.telegram:`.

#### Pool timeout — connection pool exhausted

Log shows: `Pool timeout: All connections in the connection pool are occupied.`

The Telegram adapter's internal httpx connection pool filled up and new send
requests can't get a slot within `pool_timeout` (default 8 seconds). All
retries fail with the same error because they compete for the same pool.

**Root cause:** The default pool size (512) isn't always enough when the
proxy introduces connection churn, or CLOSE_WAIT sockets from the aggressive
`keepalive_expiry=2s` accumulate faster than the OS reclaims them.

**Fix — tune pool via .env:**

```bash
# Increase pool size and timeout
echo "HERMES_TELEGRAM_HTTP_POOL_TIMEOUT=30" >> ~/AppData/Local/hermes/.env
echo "HERMES_TELEGRAM_HTTP_POOL_SIZE=1024" >> ~/AppData/Local/hermes/.env
```

Then restart the gateway: `hermes gateway restart`

Optional fine-tuning env vars (with defaults shown):
- `HERMES_TELEGRAM_HTTP_CONNECT_TIMEOUT` (10s)
- `HERMES_TELEGRAM_HTTP_READ_TIMEOUT` (20s)
- `HERMES_TELEGRAM_HTTP_WRITE_TIMEOUT` (20s)
- `HERMES_GATEWAY_HTTPX_KEEPALIVE_EXPIRY` (2.0s)
- `HERMES_GATEWAY_HTTPX_MAX_KEEPALIVE` (10)

These are read in `plugins/platforms/telegram/adapter.py` → `request_kwargs`
and `gateway/platforms/_http_client_limits.py` → `platform_httpx_limits()`.

#### Proxy Running But All Connections Failing (502 / HTTP 000) — Airport Node Down

**Symptom:** The proxy port (e.g. 7897) is listening, Clash/verge-mihomo
process is running, but ALL outbound connections through the proxy return
HTTP 502 or HTTP 000 (connection refused / timeout). Gateway logs show
repeated `httpx.ConnectError` for Telegram.

**This is NOT a Hermes/gateway issue — the proxy's upstream nodes are dead.**

**Diagnostic recipe (do all in parallel if possible):**

```bash
# 1. Gateway status — confirms Telegram is configured, gateway running
hermes status

# 2. Gateway logs — look for ConnectError pattern
grep -i "telegram\|ConnectError\|Reconnect" ~/AppData/Local/hermes/logs/gateway.log | tail -20

# 3. Proxy reachability — test external targets through proxy
curl -s -o /dev/null -w "HTTP %{http_code}\n" --max-time 5 \
  --proxy http://127.0.0.1:7897 "https://www.google.com"

# 4. Clash process check
wmic process where "name like '%clash%' or name like '%verge%' or name like '%mihomo%'" get ProcessId,Name

# 5. 🔑 THE KEY STEP — Clash sidecar logs (mihomo core)
# This is the definitive source of truth for proxy health.
# Path: %APPDATA%/io.github.clash-verge-rev.clash-verge-rev/logs/sidecar/sidecar_latest.log
cat "$APPDATA/io.github.clash-verge-rev.clash-verge-rev/logs/sidecar/sidecar_latest.log"
```

**Reading the sidecar log:**

- `match GeoIP(cn) using DIRECT` → domestic traffic bypassing proxy (GOOD)
- `error: dial tcp ... connectex: No connection could be made because the target machine actively refused it` → node is dead
- `error: dial tcp ... i/o timeout` → node is unreachable (GFW or node down)

If sidecar shows ALL external connections failing but direct ones
succeeding, the proxy nodes are the problem. The user needs to:
1. Open Clash Verge → switch to a different node
2. Or update subscription (airport maintenance / expired)
3. Or wait for airport recovery

**This is categorically different from pool timeout or NO_PROXY issues.**
Pool timeout = proxy works but Hermes can't get a connection slot.
Node down = proxy accepts connections but can't route anywhere.

#### Proxy configured but not used — check NO_PROXY first

`resolve_proxy_url()` checks `NO_PROXY` / `no_proxy` **before** falling
through to `HTTP_PROXY`/`HTTPS_PROXY`. If `api.telegram.org` appears in
`NO_PROXY`, the adapter returns `None` immediately — no proxy, no matter
what `proxy_url` is in config.yaml or what `HTTP_PROXY` is set to.

Diagnostic signal: log shows `Auto-discovered Telegram fallback IPs` but
NO `Proxy detected` line. The proxy is being bypassed. Check `.env` for
`NO_PROXY=...,api.telegram.org,...` and remove it.

This is the most common misdiagnosis: config looks correct, proxy is running,
but NO_PROXY silently kills it before `proxy_url` or `TELEGRAM_PROXY` are
ever consulted.

**Quick diagnostic: verify reachability before changing config**

Before asserting that a host "should" be direct-reachable from China,
always test empirically with curl:

```bash
# Test WITH proxy (should succeed for blocked hosts)
curl -s -o /dev/null -w "HTTP %{http_code} | %{time_total}s" --max-time 10 \
  --proxy http://127.0.0.1:7897 "https://api.telegram.org"

# Test WITHOUT proxy (timeout = blocked in China)
curl -s -o /dev/null -w "HTTP %{http_code} | %{time_total}s" --max-time 10 \
  --noproxy '*' "https://api.telegram.org"
```

**Never** change NO_PROXY, proxy_url, or gateway config based on assumptions
about Chinese network reachability. Test first, configure second.

### PTY Encoding Failures

Interactive CLI tools (like `hermes gateway setup`) that use Rich/prompt_toolkit
can fail with `UnicodeDecodeError` when run through `terminal(pty=true)` on
Windows. The error looks like:

```
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xb4 in position 0
```

This is a subprocess encoding issue with PTY mode on Windows. The workaround
is to instruct the user to run the command in their own terminal.

### Asyncio Event Loop Policy

When running async Python code that uses `asyncio.run()` on Windows (especially
code that makes network requests via aiohttp), the default `ProactorEventLoop`
can hang silently. Always set the selector event loop policy:

```python
import sys, asyncio
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
```

Without this, `asyncio.run()` may hang indefinitely with no output — no error,
no timeout, just silence.

### Foreground Output Buffering

`terminal()` in foreground mode buffers ALL output until the command exits.
This means real-time interactive flows (QR scanning, progress bars, polling
loops) appear to the user as a single dump at the end. By the time they see
a QR code, it has already expired.

**Rule:** Any workflow that requires the user to react to output in real time
must either:
- Be run by the user in their own terminal, or
- Use background mode with `notify_on_complete=true` AND the user must poll
  the output manually (which is clunky)

Background mode on Windows may also suffer from output buffering — test first.

### `uv pip install` for Hermes Venv

The Hermes-installed venv on Windows has no `pip` module. The venv's
`Scripts/` directory contains `python.exe` but not `pip.exe`. Use `uv`:

```bash
uv pip install <package> --python "$HERMES_HOME/hermes-agent/venv/Scripts/python.exe"
```

Verify with:
```bash
"$HERMES_HOME/hermes-agent/venv/Scripts/python.exe" -c "import <package>; print('ok')"
```

## 中国大陆免代理消息平台（TG 替代候选，2026-09-03 调研）

背景：TG 在中国必须走代理 → 代理抖动导致丢消息。用户想找"同成熟、免代理、不限流"的入口。Hermes 原生支持平台里，国内直连候选 = 飞书 / 钉钉 / 邮箱。**微信 iLink 的 10 条配额限制是用户明确排除项**（见 hermes-wechat-delivery）。

| 平台 | 连接方式 | 能力表 | 限流 | 坑 |
|:---|:---|:---|:---|:---|
| **飞书 (Feishu/Lark)** 🥇 | 推荐 WebSocket 长连接（免公网 URL，SDK 自动重连）或 Webhook | Voice/Images/Files/Threads/Reactions/Typing/Streaming 全 ✅（与 TG 同档，官方能力表逐项对齐） | 应用机器人 5 QPS（同用户/同群）；自定义机器人 100 次/分、5 次/秒（普通聊天远够不到） | 整点/半点推送可能遇系统压力限流 11232（避开 10:00/17:30）；企业版应用发布需管理员审批，个人自建应用内部发布无需商店审核 |
| **钉钉 (DingTalk)** 🥈 | Stream Mode WebSocket（免公网 URL，NAT 后可用） | 图片/文件/Reactions/Streaming，AI Cards 可选 | 一般频控（个人场景够） | 🔴 `No session_webhook available`：回复依赖收到消息时的临时 session webhook，重启/过期后可能投递失败——与代理丢消息模式类似，扣分；需企业/组织账号 |
| **邮箱 (Email)** 保底 | IMAP/SMTP | 图片/文件/线程 | 无实质性限流（个人邮箱） | 非实时（轮询延迟几十秒），无打字指示/流式 |

**排除**：企业微信（微信生态限流）、QQ（个人号机器人走第三方框架有冻号风险）、Discord/Slack（国外服务同样要代理）。

### 配置要点

- **飞书**：`hermes gateway setup` 扫码创建应用（推荐路径）或手动：`.env` 设 `FEISHU_APP_ID`/`FEISHU_APP_SECRET`/`FEISHU_DOMAIN=feishu`/`FEISHU_CONNECTION_MODE=websocket`/`FEISHU_ALLOWED_USERS`。依赖：`uv pip install lark-oapi websockets`。DM 每消息必回，群聊需 @。
- **钉钉**：`.env` 设 `DINGTALK_CLIENT_ID`/`DINGTALK_CLIENT_SECRET`/`DINGTALK_ALLOWED_USERS`。依赖：`uv pip install dingtalk-stream httpx alibabacloud-dingtalk`。DM 免 @，群聊需 @。
- **邮箱**：无额外依赖（内置 adapter），QQ 邮箱零成本。

### 推荐组合（2026-09-03 建议，待用户拍板）

主通道切飞书（解决 TG 走代理丢消息，功能体验几乎无损），TG 保留备用（双通道备份），邮箱做兜底（日报/告警永不失联）。飞书/钉钉是国内服务，服务器在国内，无代理依赖；与修代理（Clash 节点）互不冲突。

---

## 盘点「能官方接入哪些生态」——先查源码，别背清单

Trigger：用户问「你有哪些可以官方接入的生态 / 能接哪些平台 / 支持什么官方渠道」——
常见于拿 Hermes 与其它 agent 产品（Muse 等）做对比时。**禁止凭记忆罗列**：适配器随版本
增删，必须扫本机源码再答，并把「已启用」和「只是支持」分清楚。

### 枚举命令（三条扫完整个接入面）

```bash
cd ~/AppData/Local/hermes/hermes-agent
ls gateway/platforms/     # 核心平台适配器
ls plugins/platforms/     # 插件式平台适配器（数量更多，别漏）
ls optional-mcps/         # 官方 MCP 目录，每个子目录一个 manifest.yaml
```

文件名基本就是平台名：`weixin.py`=微信（腾讯 iLink 官方个人号）、`yuanbao.py`=腾讯元宝、
`qqbot/`=QQ 官方机器人、`msgraph_webhook.py`=微软 365/Outlook、`bluebubbles.py`=iMessage 桥、
`dingtalk` / `feishu` / `wecom` = 钉钉 / 飞书 / 企业微信。

### ⚠️ 判定「已启用」的地面真相（别把能力注册表当启用状态）

| 看着像启用状态 | 实际含义 | 能作准吗 |
|:---|:---|:---|
| `known_plugin_toolsets` / `known_builtin_toolsets` | 该版本**存在**哪些 toolset 的能力注册表 | ❌ 列表里有 `spotify`/`yuanbao` ≠ 已配置凭证 |
| `gateway_state.json` → `platforms` | 运行时快照，实测可为 `null`/陈旧 | ⚠️ 不可单独作准 |
| `config.yaml` 的 `platforms:` / `mcp_servers:` 块 | 配置真身 | ✅ |
| `.env`（`WEIXIN_TOKEN` / `TELEGRAM_BOT_TOKEN` / `A2A_BEARER_TOKEN` …） | 凭证真身 | ✅ |

**实踩（2026-10-08）**：微信平台在 `config.yaml` 里 grep 完全搜不到（只配在 `.env`），
只查 config 会误报「微信没接」。反之 `spotify` 出现在 toolset 注册表里但无配置块 = 实际没接。
两边都要查。

### 回答姿势（本用户偏好）

- 按三层给全貌：**消息平台适配器 / MCP 应用生态 / 内置插件**。
- 每层分档：**已启用 → 原生适配器只差凭证 → 需手动配 key**，不要混成一锅。
- 国内优先，并显式区分**官方渠道**（腾讯 iLink 个人号、QQ 官方机器人、飞书/钉钉/企微开放平台、
  高德官方 MCP）与 skill 级非官方采集（B站/小红书/公众号抓取）——这个区分是用户真正在意的点。
- 诚实交代差距：Hermes 是适配器框架，数量多但多数要自配凭证，≠ Muse 那种一键 SaaS 连接；
  但国产生态（微信个人号/高德/飞书钉钉）是 Hermes 的长板。不要吹成「开箱即用」。
- 聊天回复用 bullet / 标签行，不用 markdown 表格（Telegram 不渲染表格）。

完整实测清点结果（2026-10-08，含 65 个官方 MCP 目录条目与国内候选）见
`references/integration-surface-inventory.md`。

---

## Platform Config Structure

Each platform gets an entry under `platforms` in `config.yaml`:

```yaml
platforms:
  <platform_name>:
    enabled: true
    token: "<token>"          # if auth uses a token
    extra:
      # platform-specific fields
```

The `.env` file supports uppercase env vars like `WEIXIN_TOKEN`,
`WEIXIN_ACCOUNT_ID`, `TELEGRAM_BOT_TOKEN`, etc.

---

## Troubleshooting: Gateway Process Died / 网关进程异常停止

Symptom: messages stop arriving entirely; user says "网关异常停止" / "消息没人回".
This is the gateway PROCESS itself being gone — different from a platform
disconnect (Telegram/Weixin poll errors) where the process survives.

### Evidence chain (run in parallel)

1. **Lifecycle ledger — the smoking gun** (`logs/errors.log`):
   ```bash
   grep "lifecycle_ledger" ~/AppData/Local/hermes/logs/errors.log | tail
   ```
   - `exited UNCLEANLY (no exit path ran — SIGKILL / OOM / VM death)` + `last_heartbeat_at=...` + `suspected_oom=...`
   - **UNCLEANLY + no exit path = process was killed externally** (shutdown/reboot/power loss), NOT a crash. A clean stop logs `gateway.exit_clean` instead (see exit-diag log).

2. **Exit diagnostics log** (`logs/gateway-exit-diag.log`) — JSON lines per lifecycle event:
   `gateway.start` / `asyncio.run.returned` / `gateway.exit_clean` / `atexit.hook` /
   `gateway.previous_unclean_exit` (carries `prior_pid` + `last_heartbeat_at`). Tail it
   to see whether the previous gateway life exited cleanly.

3. **Start timestamps** (`gateway-starts.log`): epoch seconds per start. Two entries =
   gateway ran, died, restarted. Convert: `python -c "import datetime; print(datetime.datetime.fromtimestamp(<ts>))"`.

4. **Current state** (`gateway_state.json`): per-platform `connected` / `fatal` with
   `error_code` (e.g. `api_server_key_invalid`).

5. **Correlate with the Windows System event log** — the key cross-check:
   ```bash
   powershell.exe -NoProfile -Command "Get-WinEvent -FilterHashtable @{LogName='System'; StartTime='2026-08-04'; EndTime='2026-08-06'} | Where-Object {\$_.Id -in 1074,6005,6006,6008,41} | Select-Object TimeCreated,Id,ProviderName | Format-Table -AutoSize"
   ```
   - 1074 (User32/RuntimeBroker) = shutdown/restart requested; 计划外 (unplanned) = manual/remote user action, not scheduled
   - 6006 = clean shutdown · 6005/6013 = booted · 6008 = unexpected power loss · 41 = kernel power
   - If `last_heartbeat_at` ≈ a 1074 timestamp (seconds apart) → **the gateway was killed by that shutdown, not a bug**.
   - Note: on Chinese Windows the 1074 message body is GBK-garbled in bash — read Id + timestamp, not the text.

6. **Autostart check** — why it didn't come back after reboot:
   ```bash
   schtasks //Query //FO LIST | grep -i hermes   # Scheduled Task 'Hermes_Gateway' created by `hermes gateway install`
   reg query "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run"
   ```
   No entry = gateway is manually started only; a shutdown leaves it dead until someone
   restarts it. Fix: `hermes gateway install` (creates the Windows Scheduled Task).

### Verdict pattern
- UNCLEANLY exit + matching shutdown event + no Python traceback + `suspected_oom=False` → **external kill (user shutdown), not a defect** — report the timeline, don't chase a gateway bug.
- Gateway log's last entries may be hours before death: heartbeat probes keep running even while Telegram polling is degraded — trust `last_heartbeat_at` over log tail.

Worked case (2026-08-05 manual-shutdown kill, full timeline + api_server fatal explanation): `references/gateway-exit-diagnosis.md`

---

## Troubleshooting: Gateway 计划任务启动失败（VBS 陈旧 PYTHONPATH）

### 症状（2026-08-16 实踩）

`hermes gateway status` 显示 `✓ Scheduled Task registered` + `✗ No gateway process detected`。
`schtasks /run /TN Hermes_Gateway` 返回 `成功: 尝试运行...`（exit 0），但 gateway 进程就是不出现。
`logs/gateway-exit-diag.log` 无新的 `gateway.start` 记录（进程根本没进入启动流程）。

### 诊断法（关键区分）

1. **exit-diag 无记录 + schtasks exit 0** = 启动脚本内部失败（VBS 静默），不是 gateway 崩溃。
2. **复现**：用 VBS 完全相同的环境变量前台跑（python.exe 代替 pythonw.exe 让错误可见）：
   ```bash
   cd ~/AppData/Local/hermes && HERMES_HOME='C:\...\hermes' PYTHONIOENCODING=utf-8 \
     HERMES_GATEWAY_DETACHED=1 VIRTUAL_ENV='C:\...\hermes-agent\venv' \
     PYTHONPATH='<VBS里第12/14行的PYTHONPATH原样>' \
     "<uv python>/python.exe" -m hermes_cli.main gateway run
   ```
   崩溃点即根因。
3. **历史启动全部是交互式 tty**（exit-diag `stdin_is_tty: true`）——计划任务/VBS 路径可能从未成功过，之前 gateway 都是手动 `hermes gateway start` 拉起的。

### 根因（2026-08-16 实踩）

`gateway-service/Hermes_Gateway.vbs` 与 `.cmd` 的 `PYTHONPATH` **首位**指向
`C:\Users\Administrator\AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Local\hermes\hermes-agent`
——Claude 桌面版沙盒的**陈旧残缺拷贝**（有 `hermes_cli/main.py` 但缺 `hermes_cli/colors.py`）。
它排在最前遮蔽真源码 → `ModuleNotFoundError: No module named 'hermes_cli.colors'` → pythonw 静默闪退。

### 修复

PYTHONPATH 首位换成真源码目录：
```
从: C:\...\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Local\hermes\hermes-agent;...\venv\Lib\site-packages
到: C:\Users\Administrator\AppData\Local\hermes\hermes-agent;C:\Users\Administrator\AppData\Local\hermes\hermes-agent\venv\Lib\site-packages
```
（vbs 有两处，用 patch replace_all；改前先 cp 备份 .bak-日期）。改完 `schtasks /run /TN Hermes_Gateway` 拉起，
验证 `wmic process ... | grep "gateway run"` + gateway.log 出现 `✓ telegram connected` 三平台全连 + `hermes gateway status` 报 PID。

> 注意：venv 的 editable 安装（`__editable__.hermes_agent-*.pth`）只对 venv python 生效；
> VBS 用的是 uv python + PYTHONPATH 注入，所以必须显式把真源码目录放 PYTHONPATH 首位，
> 只留 site-packages 会 `No module named 'hermes_cli'`。

---

## Troubleshooting: WeChat iLink Disconnections (Windows + Clash Verge)

### Symptom

User reports "disconnected" or messages stop being delivered both ways.
Gateway logs show repeated:

```
[Weixin] poll error (1/3): Cannot connect to host 127.0.0.1:7897 ssl:default
[远程计算机拒绝网络连接。]
```

### Root Cause

Windows system proxy (`ProxyEnable=1`, `ProxyServer=127.0.0.1:7897`) routes
ALL traffic through Clash Verge. When Clash Verge briefly goes down (restart,
crash, auto-update), port 7897 becomes unavailable, and WeChat iLink
long-polling to `ilinkai.weixin.qq.com` fails.

This is NOT a Hermes bug — it's a proxy routing issue. The iLink client
respects the system proxy by default via the `aiohttp` trust_env default.

### Diagnosis Commands

```bash
# 1. Check if Windows system proxy is enabled
reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" | grep ProxyEnable
# ProxyEnable = 0x1 means proxy is ON

# 2. Check if Clash proxy port is listening
netstat -ano | grep ":7897"
# If the port is NOT shown, Clash is down — this is the root cause

# 3. Check gateway logs for poll errors and timestamps
grep "poll error\|Cannot connect" ~/AppData/Local/hermes/logs/gateway.log | tail -20

# 4. Check Clash Verge process and its config location
wmic process where "name='clash-verge.exe'" get ProcessId,Name,ExecutablePath
# Config directory (Clash Verge Rev): %APPDATA%/io.github.clash-verge-rev.clash-verge-rev/
# Active profile: read profiles.yaml → find `current:` uid → profiles/<uid>.yaml
```

### Fix (Defense in Depth — apply both)

**A. Gateway-side: NO_PROXY bypass (China-specific)**

The `NO_PROXY` list should include hosts that are **directly reachable from
China without a proxy**. Critical rule:

| Host | Proxy? | Reason |
|:---|:---|:---|
| `ilinkai.weixin.qq.com` | **直连** (NO_PROXY) | 微信 iLink，国内 CDN |
| `api.telegram.org` | **必须走代理** | Telegram 在中国被封锁 |
| `localhost, 127.0.0.1` | **直连** (NO_PROXY) | 本机回环 |

```bash
# ⚠️ 不要把 api.telegram.org 放进 NO_PROXY — 它在中国必须走代理！
echo "NO_PROXY=ilinkai.weixin.qq.com,novac2c.cdn.weixin.qq.com,localhost,127.0.0.1" >> ~/AppData/Local/hermes/.env
```

The Telegram adapter uses `resolve_proxy_url("TELEGRAM_PROXY", ...)` which
checks in order: `TELEGRAM_PROXY` env var → `HTTP_PROXY`/`HTTPS_PROXY` →
macOS system proxy. For reliable proxy detection after gateway restarts,
prefer setting `proxy_url` in config.yaml (see Telegram section below).

**B. Clash-side: DIRECT rule**

Find the active custom rules file: read `profiles.yaml` in the Clash Verge
config directory, look up the `current:` profile uid, then edit
`profiles/<uid>.yaml`. Add to the `prepend:` section:

```yaml
prepend:
  # WeChat iLink — must go DIRECT; proxying causes disconnects
  - DOMAIN-SUFFIX,ilinkai.weixin.qq.com,DIRECT
  - DOMAIN-SUFFIX,novac2c.cdn.weixin.qq.com,DIRECT
```

Reload Clash config via the GUI (Profiles → Refresh on the active subscription).

**C. Restart gateway**

```bash
hermes gateway restart
```

### Verification

After both fixes are applied:
1. `hermes gateway status` should show `✓ weixin connected`
2. Send a test message from WeChat — agent should respond
3. Restart Clash Verge — the connection should survive (gateway logs will
   show `poll error` briefly, then recover on next iLink poll cycle)

## Verification

After setup, restart the gateway and check platform status:

```bash
hermes gateway restart
hermes gateway status
```

Look for the platform in the output. Send a test message from the platform
to confirm bidirectional communication.

---

## Support Files

- `scripts/weixin_qr_login.py` — Standalone script: fetch QR, poll for scan,
  save credentials, update config.yaml and .env. Includes the mandatory
  Windows asyncio event loop fix.
- `references/ilink-api-notes.md` — iLink Bot API behavior notes: endpoint
  reference, QR expiration timing (**~90–120 s; the earlier "~4-5s" note was wrong,
  corrected 2026-10-18**), poll statuses, credential storage
  paths, context token persistence, retry logic, and AES-128-ECB encryption
  details.
- `references/gateway-proxy-delay-diagnosis.md` — Diagnosing gateway response
  delays caused by platform APIs routed through proxy unnecessarily. Covers
  log analysis, NO_PROXY gaps, and the diagnostic recipe for identifying
  which platform host is missing from the bypass list.
- `references/telegram-noproxy-diagnostic-trace.md` — Full diagnostic timeline
  from 2026-07-04: InvalidToken → ConnectError → NO_PROXY silent bypass →
  fix. Step-by-step with exact log patterns and resolution order.
- `references/proxy-health-check.md` — Proxy health diagnostic recipe:
  three failure modes (pool timeout / NO_PROXY bypass / airport nodes down),
  parallel diagnostic flow, and Clash sidecar log interpretation.
- `references/gateway-exit-diagnosis.md` — Gateway process death diagnosis:
  worked case (2026-08 manual shutdown killed the gateway), evidence-chain
  commands, verdict pattern, autostart check, and the `--version` lifecycle-guard pitfall.
- `references/a2a-platform-notes.md` — v0.20 A2A v1.0 (agent-to-agent) platform:
  enable config, inbound/outbound tools, security defaults, env vars, plus the
  GitHub-API recipe for pulling Hermes release notes when release pages 404.
- `references/integration-surface-inventory.md` — 全量接入面清点（2026-10-08 源码实测）：核心/插件平台
  适配器全清单、65 个官方 MCP 目录条目、本机实际已启用项、国内官方渠道清单，
  以及 Gmail 类欧美生态的等价映射。回答「你能接哪些生态」时直接引用。
- 相关 skill：`hermes-context-partitioning` —— 用 Telegram DM 话题给不同任务域
  （健康 / 投资 / 运维）分独立会话，含话题级 skill 绑定、与独立 profile 的选型对比，
  以及「用户不想手动切换」时的零命令方案。用户问「能不能单独建个 bot 处理 X」时加载。
