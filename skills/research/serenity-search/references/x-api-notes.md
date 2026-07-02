# X GraphQL API 逆向笔记

## 认证方式
| 方式 | 时间线 | 搜索 | 限制 |
|------|--------|------|------|
| Guest token | 97条热门 | ❌ 空 | 无翻页 |
| auth_token + ct0 | ✅ 最新+翻页 | ❌ 空 | ~3200条上限 |

## 端点状态

| 端点 | Query ID | 状态 |
|------|----------|------|
| UserTweets | `hr4gzZONlq23okjU8fIe_A` | ✅ 可用 |
| UserTweetsAndReplies | `FIFgycIi-CNJcV0R-135Uw` | ❌ Guest 被封 |
| SearchTimeline | `Bcw3RzK-PatNAmbnw54hFw` | ❌ 返回空 |

## API 调用方式

### Bearer Token
```
AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA
```
来源：主 JS 文件 `main.bfb69eea.js`（X 定期更换，需重新提取）

### Guest token 获取
```bash
curl -X POST "https://api.x.com/1.1/guest/activate.json" \
  -H "Authorization: Bearer <BEARER>" \
  --proxy http://127.0.0.1:7897
```

### 带认证的 UserTweets 调用
```bash
curl "https://x.com/i/api/graphql/<QUERY_ID>/UserTweets?variables=..." \
  -H "Authorization: Bearer <BEARER>" \
  -H "Cookie: auth_token=<TOKEN>; ct0=<CT0>" \
  -H "x-csrf-token: <CT0>" \
  --proxy http://127.0.0.1:7897
```

## 已知限制
- Guest 模式下 UserTweets 返回 97 条按互动排序的热门推文
- 认证模式下时间线按时间排序，支持翻页（Bottom cursor）
- SearchTimeline 即使带认证也返回空——原因不明，可能需 Premium
- Python `requests`/`urllib` 被 X 的 SSL 层拒绝——必须用 curl subprocess
- 代理 127.0.0.1:7897 仅放行 x.com 域名，搜索引擎需直连

## 翻页机制
- 每页 ~17-19 条推文（不是请求的 count 数）
- 使用 Bottom cursor 翻到更早的推文
- 约可回溯 ~3200 条（X 硬限制）

## 替代方案评估
| 方案 | 结果 |
|------|------|
| twitterapi.io 付费 | 未测试 |
| twscrape (bot 账号) | 未测试 |
| syndication.twitter.com | guest 限制 97 条 |
| nitter.net RSS | 返回空 |
| fxtwitter API | 仅 profile，无 timeline |
