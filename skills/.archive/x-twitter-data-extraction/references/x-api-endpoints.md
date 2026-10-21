# X (Twitter) API Endpoints Reference

## Guest Token (No Authentication Required)

### Activate Guest Token
```
POST https://api.x.com/1.1/guest/activate.json
Authorization: Bearer <BEARER_TOKEN>
→ {"guest_token": "2069..."}
```

### Get User Profile (fxtwitter — no auth)
```
GET https://api.fxtwitter.com/<screen_name>
→ user.id, followers, description, avatar, banner
```

## GraphQL API (Requires at least Guest Token)

All GraphQL endpoints live at:
```
https://x.com/i/api/graphql/<QUERY_ID>/<OperationName>
```

Query IDs are extracted from X's main JS bundle and **rotate periodically**.
Find the current bundle URL from `x.com` HTML, then extract from JS.

### How to Find Current Query IDs

```bash
# 1. Get main JS URL from x.com
curl -sL "https://x.com" | grep -oP 'src="(https://abs.twimg.com/responsive-web/client-web/main\.[^.]+\.js)"'

# 2. Extract query IDs from JS
curl -sL "<JS_URL>" | grep -oP '(queryId|operationName):"[^"]+"'
```

### Endpoint Catalog

| Operation | Guest Access | Purpose |
|-----------|:--:|---------|
| UserTweets | ✅ (97 only) | User timeline, engagement-sorted |
| UserTweetsAndReplies | ❌ | Timeline including replies |
| SearchTimeline | ❌ | Search by keyword |
| UserByScreenName | ✅ | User profile info |

### UserTweets Variables

```json
{
  "userId": "1940360837547565056",
  "count": 100,
  "includePromotedContent": false,
  "withVoice": true,
  "withV2Timeline": true
}
```

**Guest token behavior**: Returns exactly 97 tweets sorted by engagement
(likes descending). No `Bottom` cursor is returned — pagination is impossible.
Count parameter is ignored; always returns the full 97.

### Features Dictionary (Minimal Working)

```json
{
  "responsive_web_graphql_exclude_directive_enabled": true,
  "view_counts_everywhere_api_enabled": true,
  "longform_notetweets_consumption_enabled": true,
  "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": true
}
```

## Syndication (Embedded) Endpoint

```
GET https://syndication.twitter.com/srv/timeline-profile/screen-name/<screen_name>
```

Returns `__NEXT_DATA__` JSON with embedded timeline. Same 97-tweet guest limit
but cleaner JSON format than raw GraphQL. Good for quick one-off extraction.

Response structure:
```
props.pageProps.timeline.entries[]
  → type: "tweet"
  → content.tweet.{full_text, created_at, favorite_count, id_str, ...}
```

## Bearer Token

Extracted from X's main JS bundle. Format: `AAAAA...%3D...`. This token is
hardcoded in the client-side JS and relatively stable (changes only with new
JS bundle deployments, not per-session).

Known working token (verify against current JS bundle):
`AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA`

## Response Structure

### UserTweets Response Path
```
data.user.result.timeline.timeline.instructions[]
  → type: "TimelineAddEntries"
    → entries[]
      → content.entryType: "TimelineTimelineItem" | "TimelineTimelineCursor"
```

### Tweet Object
```
content.itemContent.tweet_results.result
  .legacy.full_text
  .legacy.created_at
  .legacy.favorite_count
  .legacy.retweet_count
  .legacy.reply_count
  .legacy.id_str
  .legacy.entities.symbols[] (.text)
  .legacy.entities.hashtags[] (.text)
  .legacy.entities.user_mentions[] (.screen_name)
  .views.count
  .is_quote_status
```

## Proxy Configuration

All X endpoints require a proxy when accessed from China.

```bash
# Environment variables for subprocess
export HTTP_PROXY="http://127.0.0.1:7897"
export HTTPS_PROXY="http://127.0.0.1:7897"

# Or per-command flag
curl --proxy "http://127.0.0.1:7897" ...
```

**Critical pitfall**: Python's `urllib` and `requests` libraries return 404
for X API calls through the proxy. Always use `subprocess.run(["curl", ...])`
instead. The issue is TLS/ALPN negotiation between Python's SSL stack and the
Clash/V2Ray proxy.

### Verified Working: curl subprocess pattern

```python
import subprocess, json

def x_api_call(method, url, headers=None):
    cmd = ["curl", "-sL", "--connect-timeout", "15",
           "-X", method, "--proxy", "http://127.0.0.1:7897"]
    if headers:
        for k, v in headers.items():
            cmd.extend(["-H", f"{k}: {v}"])
    cmd.append(url)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    return json.loads(result.stdout)
```

## Finding User IDs

```
# fxtwitter (no auth)
GET https://api.fxtwitter.com/<screen_name>
→ response.user.id

# GraphQL UserByScreenName (needs guest token)
Variables: {"screen_name": "aleabitoreddit"}
→ data.user.result.rest_id
```
