# Proxy Health Check — Clash/Telegram Diagnostic Recipe

When Telegram (or any proxied platform) stops working in China, the root cause
is one of three things. Use this recipe to identify which one fast.

## The Three Failure Modes

| # | Symptom | Cause | Where to Look |
|---|---------|-------|---------------|
| 1 | Pool timeout | Hermes httpx pool exhausted | gateway.log → `Pool timeout` |
| 2 | NO_PROXY bypass | `api.telegram.org` in NO_PROXY | gateway.log → missing `Proxy detected` line |
| 3 | **Proxy nodes dead** | Clash airport nodes all unreachable | sidecar log → `connectex: actively refused` |

This file focuses on mode 3 — the one that looks like "proxy is fine" but isn't.

## Diagnostic Flow (run in parallel)

### Step 1: Gateway Status
```bash
hermes status
```
Confirms: Telegram configured, gateway running, PID known.

### Step 2: Gateway Logs
```bash
grep -i "telegram\|ConnectError\|Reconnect" ~/AppData/Local/hermes/logs/gateway.log | tail -20
```
Pattern to look for:
```
[Telegram] Connect attempt 1/8 failed: httpx.ConnectError
Reconnect telegram error: telegram connect timed out after 30s
Reconnecting telegram (attempt 4)...
```

If you see repeated ConnectError with increasing retry intervals (1s→2s→4s→8s / 120s→240s→300s), the connection is failing at the transport layer — not at the application layer.

### Step 3: Proxy Reachability Test
```bash
# Test an external host through proxy
curl -s -o /dev/null -w "HTTP %{http_code} | %{time_total}s\n" --max-time 10 \
  --proxy http://127.0.0.1:7897 "https://www.google.com"

# Test Telegram API directly (should be blocked in China without proxy)
curl -s -o /dev/null -w "HTTP %{http_code} | %{time_total}s\n" --max-time 10 \
  --noproxy '*' "https://api.telegram.org/bot123456:ABC/getMe"

# Confirm direct (domestic) connections still work
curl -s -o /dev/null -w "HTTP %{http_code} | %{time_total}s\n" --max-time 5 \
  --noproxy '*' "https://www.bing.com"
```

**Interpretation:**
- Google through proxy → HTTP 502 or 000 → proxy is broken
- Telegram direct → HTTP 000 (timeout) → GFW blocking (expected)
- Bing direct → HTTP 302 → domestic connectivity fine

### Step 4: Clash Process Check
```bash
# Check Clash Verge and mihomo processes
wmic process where "name like '%clash%' or name like '%verge%' or name like '%mihomo%'" get ProcessId,Name,ExecutablePath

# Check proxy port
netstat -ano | grep ":7897" | head -5
```

If Clash processes exist AND port 7897 is LISTENING, proxy appears healthy at the OS level. But this is misleading — it only means Clash accepts connections, not that it can route them.

### Step 5: 🔑 The Definitive Step — Sidecar Logs

```bash
# Clash Verge Rev (newer)
cat "$APPDATA/io.github.clash-verge-rev.clash-verge-rev/logs/sidecar/sidecar_latest.log"

# Clash Verge (older)
cat "$APPDATA/io.github.clash-verge-rev.clash-verge-rev/logs/sidecar/sidecar_latest.log"
```

The sidecar log is the **verge-mihomo** core log — it shows what the proxy is actually doing with each connection attempt.

## Reading Sidecar Logs

### Healthy (proxy working)
```
[TCP] 127.0.0.1:59964 --> api.deepseek.com:443 match GeoIP(cn) using DIRECT
```
Domestic traffic matched by GeoIP rule → routed directly. Good.

### Broken (node dead)
```
[TCP] dial mm (match Match/) 127.0.0.1:59948 --> httpbin.org:80 
  error: mk006.mmkkddodc.top:443 connect error: dial tcp 0.0.0.0:443: 
  connectex: No connection could be made because the target machine 
  actively refused it.
```

Key indicators:
- `mk006.mmkkddodc.top` — the specific airport node being used
- `connectex: No connection could be made because the target machine actively refused it` — the node server rejected the connection
- If ALL external attempts show this (or i/o timeout), the entire airport/subscription is dead

### Mixed (some nodes dead, some alive)
If some connections succeed and others fail, individual nodes are unreliable. Try switching nodes in Clash Verge.

## Resolution

This is ALWAYS a user-side fix — the agent cannot restart Clash or switch nodes.

**User actions:**
1. Open Clash Verge → check current node → switch to a different one
2. If all nodes dead → update subscription (Profiles → right-click → Update)
3. If subscription update fails → airport may be down/maintenance → wait or contact provider
4. If subscription URL returns error → airport may have expired → renew or switch provider

**Agent should:**
- Report diagnostic clearly: "这不是 Hermes/Telegram 的问题，是你的代理机场节点全挂了"
- Point to the sidecar log evidence
- Suggest switching nodes or updating subscription
- DO NOT suggest restarting Hermes gateway — it won't help

## Cross-Reference

- Pool timeout → see `gateway-setup` SKILL.md "Pool timeout" section
- NO_PROXY bypass → see `gateway-setup` SKILL.md "Proxy configured but not used" section
- WeChat iLink proxy issues → see `gateway-setup` SKILL.md "WeChat iLink Disconnections" section
