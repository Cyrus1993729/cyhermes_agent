# twscrape Setup Guide

## Overview

twscrape is a Python library that manages X (Twitter) account pools, providing
authenticated API access for timeline, search, and full tweet retrieval. It
handles IMAP email verification automatically — no manual intervention needed
after initial account setup.

## Installation

```bash
pip install twscrape
```

## Prerequisites

1. **1-3 X (Twitter) accounts** — create throwaway accounts. Each needs:
   - Username
   - Password
   - Email address
   - Email password (for IMAP verification)

2. **Email must support IMAP** — Gmail with app password, Outlook.com, or
   self-hosted email. twscrape auto-reads the verification code from inbox.

3. **Proxy** — If in China, ensure proxy is available (e.g., `127.0.0.1:7897`).

## Account Setup (One-time)

```python
import asyncio
from twscrape import API

async def setup():
    api = API(proxy="http://127.0.0.1:7897")

    # Add accounts to pool
    await api.pool.add_account(
        "bot_username",
        "bot_password",
        "bot_email@example.com",
        "email_password_for_imap"
    )

    # Auto-login with IMAP verification
    await api.pool.login_all()
    print("Accounts logged in and ready")

asyncio.run(setup())
```

## Common Usage Patterns

### Get user's latest tweets (timeline, ~3200 max)

```python
user = await api.user_by_login("target_username")
tweets = await gather(api.user_tweets(user.id, limit=200))
for t in tweets:
    print(f"{t.date} | {t.rawContent[:100]}")
```

### Search by keyword + date range (can exceed 3200)

```python
results = await gather(api.search(
    "from:aleabitoreddit NBIS since:2025-11-01 until:2025-12-01",
    limit=100
))
```

### Full historical archive (month-by-month slicing)

```python
from datetime import date, timedelta

START = date(2025, 7, 1)
END = date.today()
all_tweets = {}

cur = START
while cur < END:
    nxt = (cur.replace(day=28) + timedelta(days=4)).replace(day=1)
    q = f"from:{TARGET} since:{cur} until:{nxt}"
    chunk = await gather(api.search(q, limit=10000))
    for t in chunk:
        all_tweets[t.id] = t
    print(f"{cur} ~ {nxt}: +{len(chunk)}  total {len(all_tweets)}")
    cur = nxt
```

### Get tweets + replies

Use `api.user_tweets_and_replies()` instead of `api.user_tweets()`.

## Rate Limiting

twscrape automatically rotates accounts in the pool and waits for rate-limit
resets. For ~7500 tweets with monthly slicing (~12-15 requests), a single
account is sufficient. For bulk scraping, 2-3 accounts provide headroom.

## Notes

- The timeline endpoint has a hard ~3200 tweet limit. Use search with date
  slicing to exceed this.
- Search with `from:` operator is the recommended way to get full history.
- Account sessions persist — subsequent runs reuse cached auth tokens.
