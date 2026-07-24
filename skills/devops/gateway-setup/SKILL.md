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

### QR Login Flow

The iLink QR codes expire in ~4-5 seconds. This is too fast for the agent's
foreground terminal (output is buffered and returned only on command exit).
The user MUST run the QR scan in their own terminal, ready with WeChat
scan already open.

**Correct workflow:**
1. Tell the user to open WeChat scan on their phone FIRST
2. Tell the user to run `hermes gateway setup` in their own terminal
3. User selects option 12 (Weixin / WeChat)
4. User scans QR immediately — it expires fast
5. After successful login, agent updates `config.yaml` and restarts gateway

**Do NOT attempt to run QR login through the agent's terminal** — the output
buffering will always cause the QR to expire before the user sees it.

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
  reference, QR expiration timing (~4-5s), poll statuses, credential storage
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
