# Timeline Verification Protocol

## Why this exists

Google News RSS returns articles matching keywords across ALL dates. A Warsh-nomination
article from January 2026 can appear alongside June 2026 FOMC articles. Constructing a
timeline without pubDate verification leads to:
- Attributing old events to "last night"
- Mixing event occurrence time with article publication time
- Building compelling but false narratives ("triple whammy" when only one event happened)

## Protocol

### Step 1: Extract pubDates first, build narrative second

```bash
curl -s -x http://127.0.0.1:7897 \
  "https://news.google.com/rss/search?q=QUERY&hl=en-US&gl=US&ceid=US:en" \
  -H "User-Agent: Mozilla/5.0" --max-time 15 2>&1 | \
  grep -oP '<title>[^<]+</title>|<pubDate>[^<]+</pubDate>' | head -40
```

### Step 2: Filter to target window

All Google News pubDates are in GMT. Convert to Beijing: +8 hours.

- 18 Jun 2026 16:00 GMT → 19 Jun 2026 00:00 Beijing
- 17 Jun 2026 18:00 GMT → 18 Jun 2026 02:00 Beijing

### Step 3: Classify each article

| pubDate falls in? | Classification |
|---|---|
| Target window | ✅ Include in timeline |
| 1-3 days before | ⚠️ Background — label explicitly |
| > 3 days before or after | ❌ Drop or mark as 旧闻 |

### Step 4: Distinguish event time from article time

The FOMC decision at 17 Jun 14:00 ET = 17 Jun 18:00 GMT.
CNBC's article at 17 Jun 18:00:11 GMT = instant news.
NYT's analysis at 18 Jun 19:55 GMT = next-day follow-up.

Both are about the same event but 26 hours apart. The analysis piece should
NOT be placed at the time of the NYT publication — it refers to yesterday's event.

### Step 5: Cross-check event consistency

If the narrative says "FOMC triggered gold plunge at midnight Beijing"
but the FOMC pubDate is 17 Jun 18:00 GMT (= 18 Jun 02:00 BJ, 22 hours earlier),
the narrative is wrong. Either:
- The "midnight" drop was a SECOND wave (delayed reaction), or
- The event was mis-dated

## Common failure modes

1. **Keyword contamination**: "Silver plunges 30% worst day since 1980" appears in
   June 2026 search because article mentions Warsh and gold. Actual date: Jan 2026.
2. **Cross-timezone conflation**: Mixing ET (FOMC 14:00), GMT (pubDate), and BJ in
   the same sentence without conversion.
3. **Analysis-as-event**: Placing next-day analysis at the time the analysis was
   published, not the time the analyzed event occurred.
