# Telegram 投递失败诊断（2026-09-15 实战）

## 症状 → 语义对照

- 「只收到几个字 / 开头片段」= **流式预览残留**（日志 `Transient network error editing message <id>`），整条最终消息投递失败。不是长度截断——别去查内容长度/分块。
- 多块内容中间缺一条 = 该块重试窗口内仍未恢复。

## 网关日志证据（当天 21:02-21:07 抖动，21:07:20 发送失败）

```
21:02:54 [Telegram] Telegram polling degraded (heartbeat probe)
21:03:59 [Telegram] Telegram network error (attempt 1/10) httpx.ConnectError
21:04:19 [Telegram] Telegram network error (attempt 1/10) httpx.ConnectError
21:05:34 [Telegram] Telegram network error (attempt 1/10) httpx.ConnectError
21:07:16 [Telegram] Telegram network error (attempt 1/10) httpx.ConnectError
21:07:19 [Telegram] Transient network error editing message 5390 (will retry)  ← 预览残留
21:07:20 [Telegram] Sending response (1931 chars) to 8938729624
21:07:20 [Telegram] Send failed (attempt 1/2, retrying in 2.4s): send_path_degraded
21:07:22 [Telegram] Send failed (attempt 2/2, retrying in 4.4s): send_path_degraded
21:07:27 ERROR [Telegram] Failed to deliver response after 2 retries: send_path_degraded
```

根因：重试总窗口约 7s < 抖动恢复 20-40s，重试全落在抖动期内 → 整条丢。

## 补发通道要点（scripts/tg_resend.py）

- token：`~/AppData/Local/hermes/.env` 的 `TELEGRAM_BOT_TOKEN`。**config.yaml 的 telegram.token 是残缺占位**（14 字符、尾随 `:***`），直接调 sendMessage 返回 404——本次先用它白跑 30 次才定位到。
- 代理：`http://127.0.0.1:10808`。
- 补发本身也撞一次 `SSL: UNEXPECTED_EOF_WHILE_READING`（chunk 2 首次尝试失败，重试成功）——脚本必须带重试。
- `parse_mode=HTML`：双引号/全角字符安全，仅需转义 `& < >`。
- 本次结果：3 条（767/601/588 字）全部送达（msg_id 5394-5396）。

## 复盘归档

`D:\Workspace\Projects\Hermes运维\复盘_2026-09-15_Telegram长回复投递失败与补发.md`

---

# 2026-10-07 实战：最终回复整条丢失（用户问「怎么没有回答我」）

触发场景：用户问了研究型长问题（Meta Muse 对比分析），我正常生成 2295 字回答；用户的下一句是「怎么没有回答我」——不是回答没生成，是投递失败。当晚 23:05-23:25 线路持续 ConnectError 抖动。

日志证据：

```
23:20:29 WARNING gateway.run: Normal final-send NOT suppressed despite active stream consumer
                   for session agent:main:telegram:dm:8938729624: streamed=False previewed=False
                   content_delivered=False transformed=False final_len=999
23:22:39 WARNING gateway.run: Normal final-send NOT suppressed ... content_delivered=False final_len=2295
23:22:39 INFO  gateway.run: response ready: platform=telegram chat=8938729624 time=49.4s api_calls=4 response=2295 chars
23:22:39 INFO  gateway.platforms.base: [Telegram] Sending response (2295 chars) to 8938729624
23:22:39 WARNING gateway.platforms.base: [Telegram] Send failed (attempt 1/2, retrying in 2.6s): send_path_degraded
23:22:42 WARNING gateway.platforms.base: [Telegram] Send failed (attempt 2/2, retrying in 4.6s): send_path_degraded
23:22:46 ERROR   gateway.platforms.base: [Telegram] Failed to deliver response after 2 retries: send_path_degraded
```

要点：

- `content_delivered=False` 是**前兆**：说明没有流式预览兜底，最终发送一旦失败，用户端就是彻底空白（连「几个字」都没有），所以症状会表现为「你根本没回答」。
- 前一晚 23:13 的同会话回复是因为 `Suppressing normal final send ... already confirmed (streamed=True)` 才躲过一劫——流式送达过的会话才有这层保护，别指望它。
- 补发结果：4 条（197/810/740/685 字，HTML parse_mode，`•` 代替 `-`，`<b>` 代替 `**`）全部送达，msg_id 5475-5478。
- 顺带确认一条仍存在的坑：抖动窗口内**连续两条**回复都可能丢（23:20 的 999 字、23:22 的 2295 字都撞上了），补发前先看抖动是否还在持续。
