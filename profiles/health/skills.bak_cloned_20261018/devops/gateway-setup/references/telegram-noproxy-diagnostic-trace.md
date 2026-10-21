# Telegram NO_PROXY Silent Proxy Bypass — Diagnostic Trace

**Date**: 2026-07-04  
**Symptom**: Gateway shows `telegram: retry`, logs show `httpx.ConnectError`  
**Root cause**: `api.telegram.org` in `.env` NO_PROXY list

## Full Diagnostic Timeline

### Phase 1: Invalid Token (red herring)
```
[Telegram] Proxy detected; passing explicitly to HTTPXRequest: http://127.0.0.1:7897
[Telegram] Failed to connect to Telegram: The token was rejected by the server.
telegram.error.InvalidToken: Not Found
```
- Proxy was working, but token was wrong → replaced with fresh token from @BotFather

### Phase 2: Connection Timeout (real issue)
After gateway restart — proxy detection GONE:
```
[Telegram] Auto-discovered Telegram fallback IPs: 149.154.166.110
[Telegram] Telegram fallback IPs active: 149.154.166.110
...
WARNING: Primary api.telegram.org connection failed ()
WARNING: Fallback IP 149.154.166.110 failed:
ERROR: telegram connect timed out after 30s
```
- No "Proxy detected" = `resolve_proxy_url()` returned None
- Both `api.telegram.org` and fallback IP unreachable → China firewall

### Phase 3: Wrong Fixes (wasted effort)
1. ❌ Suggested disabling proxy (user correctly called this out — Telegram needs proxy in China)
2. ❌ Added `proxy_url: "http://127.0.0.1:7897"` to both telegram config sections — didn't help because NO_PROXY bypass ran first
3. ❌ Investigated `_apply_yaml_config` timing, `TELEGRAM_PROXY` env var, config load order — all distractions

### Phase 4: Root Cause Found
```bash
# .env file contained:
NO_PROXY=...,api.telegram.org,...
```

`resolve_proxy_url()` in `gateway/platforms/base.py`:
1. Checks platform-specific env var (TELEGRAM_PROXY) → not set
2. Checks NO_PROXY against target_hosts → `api.telegram.org` MATCHES → **returns None immediately**
3. Never reaches HTTP_PROXY/HTTPS_PROXY fallthrough
4. Never reaches proxy_url from config

**Fix**: Remove `api.telegram.org` from NO_PROXY in `.env`:
```
NO_PROXY=ilinkai.weixin.qq.com,novac2c.cdn.weixin.qq.com,localhost,127.0.0.1
```

## Key Diagnostic Signal

| Log pattern | Meaning |
|:---|:---|
| `Proxy detected; passing explicitly to HTTPXRequest: <url>` | Proxy IS working |
| `Auto-discovered Telegram fallback IPs` (no "Proxy detected") | Proxy bypassed — check NO_PROXY |
| `InvalidToken: Not Found` | Token wrong (not network) — get fresh token |
| `httpx.ConnectError: ` (empty error message) | Can't reach server — proxy or firewall |

## Resolution Order (for future diagnosis)

1. **Token check**: `InvalidToken` in log? → Go to @BotFather, get fresh token
2. **Proxy check**: No "Proxy detected" in log? → Check NO_PROXY in .env, check proxy_url in config
3. **Firewall check**: "Proxy detected" present but still `ConnectError`? → Proxy port not reachable, Clash might be down
