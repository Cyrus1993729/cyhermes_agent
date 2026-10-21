---
name: china-dev-proxy-setup
description: "Configure Python projects for dual-network environments where international APIs need proxy but domestic Chinese APIs need direct connection. Covers Clash Verge, requests proxy bypass patterns, and per-source routing."
version: 1.0.0
platforms: [windows]
metadata:
  hermes:
    tags: [proxy, china, network, requests, clash, dual-network]
---

# China Dev Proxy Setup — Dual-Network Python Projects

## Problem

In China, a single Python project often needs **both**:
- International APIs (yfinance, FRED, Anthropic, Yahoo) → must go through proxy
- Domestic Chinese APIs (akshare → eastmoney.com, 东方财富) → must go DIRECT

Clash Verge in TUN mode intercepts **all** traffic at OS level. Even with `NO_PROXY` env vars or `trust_env=False`, domestic requests still get routed through the proxy and fail.

## Fixed Recipe

### 1. Clash Verge: Rule Mode (not Global)

System Proxy or TUN mode with **rules**, not global. Add direct rules for domestic data sources:

```
DOMAIN-SUFFIX,eastmoney.com,DIRECT
DOMAIN-SUFFIX,sse.com.cn,DIRECT
DOMAIN-SUFFIX,szse.cn,DIRECT
```

### 2. Per-Source Proxy Control in Python

For international calls (yfinance, fredapi): let them use system proxy naturally.

For domestic calls (akshare eastmoney): **temporarily strip proxy env vars** before the call, restore after:

```python
import os

def fetch_domestic():
    old_env = {}
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        if key in os.environ:
            old_env[key] = os.environ.pop(key)
    try:
        # akshare call that hits eastmoney.com
        df = ak.fund_etf_hist_em(...)
    finally:
        os.environ.update(old_env)
```

This works because Clash TUN respects application-level proxy bypass when env vars are unset AND the Clash rule also says DIRECT. The env var removal tells Python's `requests` not to explicitly use a proxy, and Clash's rule tells TUN to pass the traffic directly.

### 3. Claude Code on Windows (git-bash/MSYS)

Claude Code CLI requires proxy env vars in the git-bash session:

```bash
export HTTP_PROXY="http://127.0.0.1:7897"
export HTTPS_PROXY="http://127.0.0.1:7897"
claude auth login    # OAuth login
claude -p "task"     # print-mode tasks
```

Without these, OAuth returns 403. The npm binary may not be in PATH — install via:
```bash
npm install -g @anthropic-ai/claude-code
```

### 4. Shell Wrapper Script

Save as `scripts/run_with_proxy.sh` for projects that need both:

```bash
#!/bin/bash
# Set proxy for international APIs
export HTTP_PROXY="http://127.0.0.1:${PROXY_PORT:-7897}"
export HTTPS_PROXY="http://127.0.0.1:${PROXY_PORT:-7897}"
# Exclude domestic Chinese sites
export NO_PROXY="eastmoney.com,*.eastmoney.com,sse.com.cn,szse.cn"
exec "$@"
```

## Common Proxy Ports

| Tool | Default Port |
|------|-------------|
| Clash Verge | 7897 |
| Clash (standard) | 7890 |
| v2rayN | 10809 |

## Pitfalls

- **TUN mode overrides everything.** Even `trust_env=False` won't bypass TUN. The ONLY fix is Clash rules + env var stripping.
- **System proxy ≠ TUN.** System proxy mode (PAC/手动) is weaker — env vars CAN override it. TUN mode creates a virtual NIC that's lower in the network stack.
- **Git-bash on Windows uses MSYS.** Some env vars (`http_proxy` lowercase) may need to be set in addition to uppercase.
- **requests library caches proxy settings.** If a connection was made with proxy, subsequent connections may reuse it. Use `session.close()` or create fresh sessions.
- **NO_PROXY kills Telegram.** `resolve_proxy_url()` checks `NO_PROXY` before falling through to `HTTP_PROXY`. If `api.telegram.org` is in `NO_PROXY`, all Telegram connections fail with timeout — even if `proxy_url` is set in config.yaml or `TELEGRAM_PROXY` env var is populated. In China, `api.telegram.org` MUST NOT be in NO_PROXY.

## Search Engine Availability

See `references/search-engines-availability.md` for a complete matrix of which search engines work from this environment (Google blocked via CAPTCHA on datacenter proxy IP, Bing international works direct, Startpage JS-only, etc.). Use this before attempting web research — saves cycles on dead ends.

## Further Reading

- `references/yfinance-rate-limit-workaround.md` — Ticker API with shared session to avoid YFRateLimitError
- `references/akshare-chinese-columns.md` — Chinese column name patterns for Shanghai gold and domestic ETFs
- `references/playwright-edge-fallback.md` — Use system Edge when Playwright Chromium download fails behind GFW
- `references/xiaohongshu-access-limits.md` — Xiaohongshu anti-crawling and programmatic access limitations
- `references/search-engines-availability.md` — Which search engines work from China, proxy vs direct, CAPTCHA pitfalls
