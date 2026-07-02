# WeChat iLink 限流问题

## 现象

Hermes Agent 通过 iLink（微信机器人协议）收发消息时，频繁触发限流：

```
WARNING gateway.platforms.weixin: [Weixin] rate limited for o9cq805U; backing off 3.0s before retry
ERROR gateway.platforms.weixin: [Weixin] send failed: iLink sendmessage rate limited: ret=-2
```

## 数据（2026.6.21 会话）

- 总计 429 次 rate limit 事件（gateway-stderr.log）
- 集中发生在多段报告发送时（6 段报告 ≈ 6 次连续 send_message，1-2 秒内全部发出）
- Gateway 重试机制：被限后等待 3 秒重试，失败则尝试 plain-text fallback，再失败消息永久丢失

## 根因

iLink 的限流逻辑按「人类聊天节奏」设计（几秒一条），不適应 AI Agent 的消息爆发模式。
v0.14.0 的 gateway 没有内置 iLink 限流感知——消息来了就发。

## 影响

| 场景 | 结果 |
|:---|:---|
| 单条消息 | 正常 |
| 多段报告（3+ 段） | 前几段发出，后几段可能丢失 |
| 消息 + MEDIA 文件连续发送 | 可能触发限流 |

## 缓解措施

1. **减少分段**：每段更长但更少（v0.14.0 只能这样做）
2. **升级到 0.17.0**：新版本的平台适配可能有改進
3. iLink 提额：住宅 IP 低频账号无提额通道，不可行
