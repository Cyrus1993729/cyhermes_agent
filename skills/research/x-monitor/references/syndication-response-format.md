# Syndication 接口返回格式

## 端点

```
GET https://syndication.twitter.com/srv/timeline-profile/screen-name/{screen_name}
```

## 响应结构

返回 HTML 页面，内含 `<script id="__NEXT_DATA__" type="application/json">` 标签。JSON 结构：

```json
{
  "props": {
    "pageProps": {
      "timeline": {
        "entries": [
          {
            "type": "tweet",
            "entry_id": "tweet-1972016308662513748",
            "sort_index": "2069682951259422720",
            "content": {
              "tweet": {
                "id_str": "1972016308662513748",
                "created_at": "Sat Sep 27 19:11:40 +0000 2025",
                "full_text": "...",
                "favorite_count": 881,
                "retweet_count": 125,
                "reply_count": 63,
                "quote_count": 15,
                "permalink": "/aleabitoreddit/status/1972016308662513748",
                "entities": {
                  "symbols": [
                    { "indices": [156, 161], "text": "CRWV" }
                  ],
                  "media": [ ... ]
                },
                "is_quote_status": true,
                "quoted_status": { ... }
              }
            }
          }
        ],
        "latest_tweet_id": "1972016308662513748"
      },
      "headerProps": {
        "screenName": "aleabitoreddit"
      }
    }
  }
}
```

## 提取要点

- `entries[]` 中 type="tweet" 的才是推文
- 每条推文有完整 `full_text`、时间、互动数、股票代码符号
- 引用推文 `quoted_status` 嵌套在同一条 entry 中
- `latest_tweet_id` 是嵌入组件当前缓存的最新推文 ID（用作去重基准）

## 已知限制

- **非实时。** 数据来自 X 的嵌入式组件缓存，延迟数小时到数天
- **条数有限。** 通常返回 10-20 条最近的推文
- **需要代理。** 中国直接访问 timeout

## Python 提取代码

```python
import sys, json, re

def extract_tweets(html):
    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
    if not match:
        return []
    data = json.loads(match.group(1))
    entries = data['props']['pageProps']['timeline']['entries']
    tweets = []
    for entry in entries:
        if entry.get('type') != 'tweet':
            continue
        t = entry['content']['tweet']
        tweets.append({
            'id': t['id_str'],
            'created_at': t['created_at'],
            'text': t['full_text'],
            'likes': t.get('favorite_count', 0),
            'retweets': t.get('retweet_count', 0),
            'replies': t.get('reply_count', 0),
            'symbols': [s['text'] for s in t.get('entities', {}).get('symbols', [])],
            'permalink': f"https://x.com{t['permalink']}",
            'is_quote': t.get('is_quote_status', False)
        })
    return tweets
```
