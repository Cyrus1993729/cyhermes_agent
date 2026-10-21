# Fxtwitter API 接口说明

## 端点

```
GET https://api.fxtwitter.com/{screen_name}
```

## 可用：用户资料

```json
{
  "code": 200,
  "message": "OK",
  "user": {
    "screen_name": "aleabitoreddit",
    "url": "https://x.com/aleabitoreddit",
    "id": "1940360837547565056",
    "followers": 882104,
    "following": 175,
    "likes": 12768,
    "media_count": 2129,
    "tweets": 7443,
    "name": "Serenity",
    "description": "...",
    "location": "NFA",
    "banner_url": "https://pbs.twimg.com/...",
    "avatar_url": "https://pbs.twimg.com/...",
    "joined": "Wed Jul 02 10:44:15 +0000 2025",
    "protected": false,
    "verification": {
      "verified": true,
      "type": "individual"
    }
  }
}
```

## 不可用：推文/时间线

以下端点**全部返回 404**，不要尝试：

- `/aleabitoreddit/tweets` → 404
- `/aleabitoreddit/status` → 404
- `/aleabitoreddit/timeline` → 404
- `/aleabitoreddit/latest` → 404
- `/aleabitoreddit/media` → 404

## 用途

仅用于**快速获取用户基础信息**（粉丝数、简介、认证状态等），不支持推文时间线。

## Nitter 状态（2026-06）

| 实例 | 状态 |
|------|------|
| nitter.net | HTTP 200 但 Content-Length: 0（空响应） |
| nitter.poast.org | HTTP 403 / 000 |
| nitter.1d4.us | HTTP 000（连接失败） |
| xcancel.com | HTTP 403 |

**结论：不要浪费时间尝试 Nitter。**
