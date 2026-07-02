# Cron News Search — Google News RSS via curl

## Why not delegate_task web_search?

`delegate_task` with `toolsets=["web"]` for the 4 news searches fails ~66% of the time with
"Authentication Fails (governor)" on this host. The curl + proxy approach works reliably.

## Prerequisites

- Clash proxy running on `127.0.0.1:7897`
- `curl` available in git-bash/MSYS
- `grep` with `-oP` (PCRE) support in git-bash

## Search Patterns

Use `execute_code` to run multiple searches in parallel (each via `terminal()`). Stick to the
Google News RSS endpoint — it returns clean XML with titles and descriptions, no JavaScript.

### Base template

```python
from hermes_tools import terminal

proxy = "http://127.0.0.1:7897"
ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# Fetch titles
result = terminal(
    f'curl -s -x {proxy} '
    f'"https://news.google.com/rss/search?q=QUERY_HERE&hl=en-US&gl=US&ceid=US:en" '
    f'-H "User-Agent: {ua}" --max-time 15 2>&1 | '
    f'grep -oP \'<title>[^<]+</title>\' | head -15',
    timeout=20
)

# Fetch descriptions (for more context)
result = terminal(
    f'curl -s -x {proxy} '
    f'"https://news.google.com/rss/search?q=QUERY_HERE&hl=en-US&gl=US&ceid=US:en" '
    f'-H "User-Agent: {ua}" --max-time 15 2>&1 | '
    f'grep -oP \'<description>[^<]+</description>\' | sed "s/<[^>]*>//g" | head -10',
    timeout=20
)
```

### Required searches for weekly report

1. **Gold price + macro context**: `gold+price+June+2026`
2. **Fed / monetary policy**: `Federal+Reserve+rate+June+2026`
3. **Geopolitical**: `Israel+Iran+Middle+East+conflict+June+2026`
4. **China gold demand**: `China+gold+demand+Shanghai+June+2026`

Also worth checking specific events if headlines hint at them:
- Jobs data: `US+jobs+report+May+2026+nonfarm+payrolls`
- Fed Beige Book: `Fed+Beige+Book+June+2026`

## Extracting article content

When headline + description aren't enough, try direct article fetch:

```bash
curl -s -x http://127.0.0.1:7897 \
  "ARTICLE_URL" \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
  --max-time 15 -L 2>&1 | \
  sed -n "s/.*<p[^>]*>\(.*\)<\/p>.*/\1/p" | sed "s/<[^>]*>//g" | head -20
```

Note: `python3` is NOT available in git-bash on this host. Use `sed` / `grep` for text
extraction, not `python3 -c`. The `python` command is available but points to the Windows
Python, which may not be on PATH inside execute_code subprocesses.

## Timestamp Verification (MANDATORY before constructing event timelines)

**Google News RSS returns articles from ANY date that match the keywords** — not just the
current week. A search for "gold June 2026" can return results from January, February, or
any month. Every article cited in a timeline MUST have its `<pubDate>` verified.

### Extracting pubDate in execute_code

```python
from hermes_tools import terminal
import re

proxy = "http://127.0.0.1:7897"
ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# Fetch full RSS XML
r = terminal(
    f'curl -s -x {proxy} '
    f'"https://news.google.com/rss/search?q=QUERY&hl=en-US&gl=US&ceid=US:en" '
    f'-H "User-Agent: {ua}" --max-time 15 2>&1',
    timeout=20
)

output = r.get("output", "") if isinstance(r, dict) else str(r)

# Extract each article's title, pubDate, and source
items = re.findall(r'<item>(.*?)</item>', output, re.DOTALL)
for item in items:
    title = re.search(r'<title>(.*?)</title>', item)
    pubdate = re.search(r'<pubDate>(.*?)</pubDate>', item)
    source = re.search(r'<source[^>]*>(.*?)</source>', item)

    if title and pubdate:
        date_str = pubdate.group(1)  # e.g. "Thu, 18 Jun 2026 16:14:00 GMT"
        # Filter: only keep articles from the target date range
        if "18 Jun 2026" in date_str or "19 Jun 2026" in date_str:
            print(f"[{date_str}] {source.group(1) if source else '?'}")
            print(f"  {title.group(1)[:150]}")
            print()
```

### Timezone Conversion Reference

| Timezone | Offset from GMT | Label |
|----------|----------------|-------|
| GMT/UTC | ±0 | Reference |
| ET (US Eastern) | -4 (summer) / -5 (winter) | FOMC, US market hours |
| **Beijing (CST)** | **+8** | **User's timezone** |

**Conversion formula**: `Beijing = GMT + 8 hours`

Common market event times:
| Event | ET | GMT | Beijing |
|-------|-----|-----|---------|
| FOMC statement | 14:00 Day 2 | 18:00 Day 2 | 02:00 next day |
| Warsh/Fed press conference | 14:30 Day 2 | 18:30 Day 2 | 02:30 next day |
| US equity open | 09:30 | 13:30 | 21:30 |
| US equity close | 16:00 | 20:00 | 04:00 next day |
| Shanghai gold open | — | — | 09:00 |

### FOMC Multi-Wave Reaction Pattern

Major central bank decisions trigger distinct reaction waves — do NOT conflate them:

| Wave | Trigger | Beijing time window | Characteristics |
|------|---------|-------------------|----------------|
| **Wave 1** | FOMC statement + presser | 02:00-04:00 (next day) | Algorithmic, immediate, often volatile |
| **Wave 2** | Asian + European session digestion | 08:00-20:00 (next day) | Partial repricing, liquidity thinner |
| **Wave 3** | US session institutional repricing | 21:00-04:00 (next day) | Full implications sink in, largest flows |

When a user asks "what happened last night," identify which wave they mean. The FOMC decision
itself (Wave 1) may have been 24-30 hours prior; the overnight move they're observing is
often Wave 3 (US session). Never say "the FOMC happened last night" if it was 30 hours ago —
say "the FOMC was yesterday morning, and last night's move was the US session repricing."

## Pitfalls

- **Google News RSS returns HTML entities** — `&amp;`, `&lt;`, `&gt;` in titles/descriptions.
  These are cosmetic and don't affect news extraction. Don't bother decoding them.
- **Paywalled articles** (Fortune, WSJ, Bloomberg) return empty or "Content is currently unavailable."
  Skip them — use the RSS headline + description for these sources.
- **Google News URL encoding**: Use `+` for spaces, NOT `%20`. The RSS endpoint handles `+` correctly.
- **Rate limit**: Keep curl calls spaced by at least 2 seconds. Running 4+ in parallel within
  `execute_code` is fine — the terminal calls are serialized internally.
- **News-data contradiction**: Search results can include stale or fabricated claims (e.g., "中国央行增持32万盎司" when akshare shows a MoM decrease). After extracting news, cross-check any directional or quantitative claims against the `main.py` signals BEFORE writing the 本周要闻 section. If news says "增持" but pboc_reserves is negative → the news is wrong, use the quantitative data. If news says "美元走弱" but dxy_1m_pct > 0 → the news is wrong. See data-validation.md Gate 5e for the full contradiction test table.
- **TIMELINE VERIFICATION (MANDATORY)**: Always extract `pubDate` from RSS before building any narrative. Old articles with matching keywords (e.g., January Warsh nomination articles appearing in June FOMC search results) will contaminate the timeline if not filtered. See `references/news-timeline-verification.md` for the full protocol.
- **CRITICAL — Timeline verification**: Google News RSS returns articles matching keywords across ALL dates, not just the target window. A Warsh-nomination article from January 2026 can appear alongside June FOMC articles because both contain "Warsh". **ALWAYS extract `<pubDate>` from RSS items and filter to the target window BEFORE constructing any event timeline.** See `references/timeline-verification.md` for the full protocol with timezone conversion (GMT→Beijing) and event-vs-publication-time distinction.

- **Article timestamps MUST be verified — Google News RSS returns old articles**: RSS searches return articles from ANY date matching keywords, not just the current week. A search for "gold June 2026" can return January or March articles that happen to mention "June 2026" as a forecast or related context. Before citing any article in a timeline: (a) always extract and check `<pubDate>`; (b) discard articles older than the claimed event window; (c) never cite a January article as evidence for a June event. See the Timestamp Verification section above for extraction code.

- **Multi-wave FOMC reactions must be distinguished**: The FOMC statement + press conference (Wave 1) and the US session repricing (Wave 3) are separated by 18-24 hours. Do NOT tell the user "the FOMC happened last night" if it was 30 hours ago. Instead: "the FOMC was yesterday morning (Wave 1), and last night's acceleration was the US session digesting the implications (Wave 3)." See the FOMC Multi-Wave Reaction Pattern table above for timing.
