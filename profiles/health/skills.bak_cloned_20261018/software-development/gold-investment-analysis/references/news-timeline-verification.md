# News Timeline Verification Rules

> Added 2026-06-19 after gold price analysis errors — headlines from January 2026 were misattributed to June 18.

## Core Rule

**Always extract pubDate BEFORE constructing any narrative.** Do not build a story from headlines alone.

## Extraction Pattern (Google News RSS)

```bash
curl -s -x http://127.0.0.1:7897 \
  "https://news.google.com/rss/search?q=QUERY&hl=en-US&gl=US&ceid=US:en" \
  -H "User-Agent: Mozilla/5.0" --max-time 15 2>&1 | \
  grep -oP '<title>[^<]+</title>' | head -15
  
# Then extract pubDate for EACH article:
grep -oP '<pubDate>[^<]+</pubDate>' | head -15
```

## Verification Checklist

1. **Extract pubDate first** — before reading titles, before building stories
2. **Convert GMT to Beijing** — pubDate is GMT, add 8 hours
3. **Filter by target window** — only keep articles from the time period being analyzed
4. **Flag mismatches** — if a dramatic headline doesn't have a timestamp in the target window, it's old news
5. **Keyword contamination** — old articles appear in search results because they share keywords (e.g., "Warsh" appeared in both January nomination articles and June FOMC articles)

## Common Failure Mode

| Symptom | Cause | Fix |
|---|---|---|
| "Silver plunged 30%, worst since 1980" attributed to June 18 | Article was from January 30 (Warsh nomination) | Check pubDate, reject if outside window |
| FOMC decision described as "last night" when it was 30 hours ago | Conflated event time with market reaction time | Separate "event occurrence" from "article publication" |
| Timeline feels too dramatic, too many events in one night | Multiple old articles mixed into current timeline | Filter strictly by pubDate |

## Multi-Day Events

When an event spans multiple days:
- Label each wave separately with its own timestamp window
- Never compress into "one continuous event"
- Distinguish "when the event happened" from "when articles about it were published"

## Cross-Reference

For investment analysis, always cross-check news claims against quantitative data (e.g., if news says "PBOC buying gold" but akshare shows MoM decrease → the news is wrong).
