# iLink（微信）限流机制

> 来源：2026.6.21 会话日志分析

## 规模

- 累计 429 次 `rate limited` 事件
- 限流集中在消息密集发送的窗口（多段报告、MEDIA 发送后）
- 每次限流后网关 backoff 3 秒重试

## 触发模式

```
同一秒内连续 3+ 条 send_message → iLink 返回 ret=-2 errmsg=rate limited
→ gateway 尝试 plain-text fallback → fallback 也可能被限
→ 消息永久丢失
```

## 日志证据

```
ERROR gateway.platforms.weixin: [Weixin] send failed to=o9cq805U: iLink sendmessage rate limited: ret=-2 errcode=None errmsg=rate limited
ERROR gateway.platforms.base: [Weixin] Fallback send also failed: iLink sendmessage rate limited
```

## 影响

| 场景 | 结果 |
|:---|:---|
| 单条短消息 | 正常 |
| 3-4 段连续发送 | 前 2-3 段到达，后段可能丢失 |
| 6 段连续发送 | 几乎必然丢失 2-3 段 |
| 消息 + MEDIA 连续发送 | 其中一条可能丢失 |

## 缓解

1. 段间加 3-5 秒延迟
2. 核心结论放前 2 段
3. 最后段附 .md 文件路径作为 fallback
4. 升级到 v0.17.0（release notes 提及平台改进）
