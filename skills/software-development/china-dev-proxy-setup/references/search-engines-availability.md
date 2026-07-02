# Search Engine Availability from China (2026-06)

> **Also see**: `automated-investment-research` skill and its `references/search-api-landscape.md` for programmatic search APIs (Tavily, Perplexity, ValueSERP).

Tested from this environment: Clash Verge proxy at `127.0.0.1:7897` (IP: 162.248.224.204, datacenter IP).

## Principle: Don't Waste Time Hacking Google

Google blocks datacenter IPs at the **IP-reputation layer** — not at the HTTP header level. No User-Agent, Cookie, or TLS fingerprint trick can bypass this. The response is always a reCAPTCHA challenge:

> *"Our systems have detected unusual traffic from your computer network."*

**When you need Google-quality search, use an API service that maintains its own residential IP pool (Tavily, ValueSERP, Perplexity). Do not try to curl Google directly.**

## Quick Reference

| Engine | Direct (noproxy) | Via Proxy (127.0.0.1:7897) | Verdict |
|--------|:---:|:---:|--------|
| **Google** `google.com` | ❌ Timeout | ❌ CAPTCHA block | Unusable |
| **Google** `google.com.hk` | ❌ Timeout | ❌ CAPTCHA block | Unusable |
| **Google** all search endpoints | ❌ Timeout | ❌ CAPTCHA block | Unusable |
| **Google Custom Search API** | ❌ | ✅ API reachable | ❌ Do NOT recommend — limited to CSE index, not full web |
| **Bing** `cn.bing.com` | ✅ | — | China-filtered results |
| **Bing** `www.bing.com` | ✅ | — | **Best free direct** — international results |
| **Startpage** `startpage.com` | ❌ | ⚠️ JS-only SPA | Unusable via curl |
| **Tavily API** | ✅ | ✅ | **Recommended** — free 1000/mo, agent-native |
| **ValueSERP API** | ✅ (proxy) | ✅ | Real Google results, $5/mo 5000 queries |
| **Perplexity API** | ✅ (proxy) | ✅ | Deep Research mode ~$5/query |

## Bing: International vs China

`cn.bing.com` returns China-filtered results. `www.bing.com` with `&setlang=en&cc=us` returns unfiltered international results. Always prefer `www.bing.com` for English research.

```bash
# Good
curl -sL --noproxy "*" "https://www.bing.com/search?q=OpenLight+Advantest&setlang=en&cc=us&mkt=en-US"
# Avoid
curl -sL --noproxy "*" "https://cn.bing.com/search?q=..."
```

## Google Custom Search API — Why NOT to Recommend

Despite being technically reachable via proxy:
1. Search scope is limited to **CSE-configured sites**, not the full web
2. Free tier is 100 queries/day — inadequate for investment research
3. Setting "Search the entire web" still differs from native Google results
4. Better alternatives exist (see above)
