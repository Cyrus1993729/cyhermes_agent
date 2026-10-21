# Diagnosing Gateway Proxy Delays

## Symptoms

- Messages arrive in bursts after long silent periods
- Voice messages take 3+ minutes to get a response
- Gateway log shows `httpx.ConnectError` with retries
- User reports "waited a long time, then got spammed with messages"

## Diagnostic Recipe

### 1. Check gateway logs for proxy detection

```bash
grep -i "proxy\|ConnectError\|Network error" ~/AppData/Local/hermes/logs/gateway.log | tail -30
```

Look for:
- `Proxy detected; passing explicitly to HTTPXRequest: http://127.0.0.1:7897`
  → The platform adapter is routing through the proxy
- `Network error on send (attempt N/3), retrying in 1s`
  → Proxy connection failures causing retries
- `MarkdownV2 edit failed, falling back to plain text: httpx.ConnectError`
  → Even message edits are failing through proxy

### 2. Check current NO_PROXY configuration

```bash
# Check .env
grep NO_PROXY ~/AppData/Local/hermes/.env

# Check runtime env
echo "NO_PROXY=$NO_PROXY"
```

### 3. Identify the problematic platform host

Each platform adapter checks proxy with its own target hosts:

| Platform  | Target host(s)                    |
|-----------|-----------------------------------|
| Telegram  | `api.telegram.org` + fallback IPs |
| WeChat    | `ilinkai.weixin.qq.com`           |
| Discord   | `discord.com`                     |

The adapter code (e.g. `gateway/platforms/telegram.py`):
```python
proxy_url = resolve_proxy_url("TELEGRAM_PROXY", target_hosts=["api.telegram.org", ...])
```

`resolve_proxy_url()` in `gateway/platforms/base.py`:
1. Checks `<PLATFORM>_PROXY` env var first (platform override)
2. Falls through to `HTTPS_PROXY` / `HTTP_PROXY` / `ALL_PROXY`
3. Before returning, checks `NO_PROXY` against target_hosts via `should_bypass_proxy()`

### 4. Fix: Add the host to NO_PROXY

```bash
# Append to existing NO_PROXY in .env
sed -i 's/^NO_PROXY=.*/&,api.telegram.org/' ~/AppData/Local/hermes/.env
```

Or manually edit to include the missing host.

### 5. Restart gateway

```bash
hermes gateway restart
```
(Not possible from within the gateway — user must run `/restart` or restart manually)

### 6. Verify

```bash
hermes gateway status
```
Look for `✓ telegram connected` in the output.

## Root Cause Summary

`NO_PROXY` did not include the platform's API host, so the global
`HTTPS_PROXY=http://127.0.0.1:7897` was inherited. The proxy is
unnecessary for Telegram API (directly reachable from China) and
introduces latency + connection failures.
