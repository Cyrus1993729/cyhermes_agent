# Weixin 适配器发送链路代码走读

> 基于 `gateway/platforms/weixin.py` (2359 行)，2026.7.3 逐段阅读记录。

## 发送入口：`send()` (~1819 行)

```python
async def send(self, chat_id, content, ...) -> SendResult:
    # 1. 提取 MEDIA: 标签和本地文件路径
    # 2. 先投递媒体附件（图片/文件/音频）
    # 3. 文本分片 → 逐个发送 → chunk 间延迟
    chunks = self._split_text(self.format_message(final_content))
    for idx, chunk in enumerate(chunks):
        await self._send_text_chunk(chat_id=chat_id, chunk=chunk, ...)
        if idx < len(chunks) - 1:
            await asyncio.sleep(self._send_chunk_delay_seconds)  # 默认 1.5s
    return SendResult(success=True, ...)
```

**关键：** 异常被 `try/except` 捕获，返回 `SendResult(success=False, error=...)`。调用方（gateway run.py / cron scheduler.py）拿到 False 后放弃，不重试。

## 串行化锁：`_send_text_chunk()` (~1700 行)

```python
async def _send_text_chunk(self, ...):
    async with self._send_text_gate:  # asyncio.Lock — 全局唯一
        await self._send_text_chunk_locked(...)
```

**效果：** 所有并发发送（会话回复 + cron 通知）在锁处排队，逐个执行。但排队只是"等锁释放"，不意味着后面的消息不会失败——如果锁内第一条触发熔断器，后续消息进锁后立即被 `raise`。

## 核心瓶颈：`_send_text_chunk_locked()` (~1723 行)

```python
async def _send_text_chunk_locked(self, ...):
    for attempt in range(self._send_chunk_retries + 1):  # 默认最多 5 次
        # 🔴 熔断器检查 — 问题所在
        if self._rate_limit_cooldown_remaining() > 0:
            raise self._rate_limit_error()  # ← 直接抛异常，不等待

        try:
            resp = await _send_message(...)  # HTTP POST 到 iLink
            # 检查响应错误码
            if errcode == RATE_LIMIT_ERRCODE:    # -2
                # 记录限流事件，可能打开熔断器
                if self._record_rate_limit_event():
                    break  # 熔断器打开 → 跳出重试循环
                # 退避重试
                wait = self._send_chunk_retry_delay_seconds * 3
                await asyncio.sleep(wait)
                continue
            elif errcode == SESSION_EXPIRED_ERRCODE:  # -14
                # 去掉 context_token 重试一次
                continue
            else:
                raise RuntimeError(...)  # 其他错误直接抛
        except Exception:
            # 网络异常 → 等递增延迟后重试
            wait = retry_delay * (attempt + 1)
            await asyncio.sleep(wait)

    raise last_error  # 重试耗尽 → 抛给 send() → 消息丢失
```

**三个失败出口，全部导致消息永久丢失：**
1. 熔断器打开 → `raise rate_limit_error()`  — 不等，直接丢
2. 其他 iLink 错误 → `raise RuntimeError` — 直接丢
3. 重试耗尽 → `raise last_error` — 丢

## 熔断器：`_record_rate_limit_event()` (~1685 行)

```python
def _record_rate_limit_event(self) -> bool:
    now = time.monotonic()
    window_start = now - self._rate_limit_circuit_window_seconds  # 30s 窗口
    self._rate_limit_events = [ts for ts in self._rate_limit_events if ts >= window_start]
    self._rate_limit_events.append(now)
    if len(self._rate_limit_events) >= self._rate_limit_circuit_threshold:  # 默认 1
        self._open_rate_limit_circuit()  # 设置 _rate_limit_circuit_until = now + 30s
        return True
    return False
```

**默认行为：** 首次 `errcode=-2` 即打开 30s 冷却。冷却期内的所有发送调用 → `_rate_limit_cooldown_remaining() > 0` → `raise`。

## Cron 投递路径：`scheduler.py` `_deliver_result()` (~1060 行)

```python
def _deliver_result(job, content, adapters=None, loop=None):
    # 1. 解析投递目标（weixin / origin / local / all）
    # 2. 包装内容（Cronjob Response header/footer）
    # 3. 提取 MEDIA: 标签
    # 4. 遍历每个投递目标：
    for target in targets:
        # 优先用 live adapter（网关运行时的 weixin adapter 实例）
        runtime_adapter = adapters.get(platform)
        if runtime_adapter:
            # 走 adapter.send() → 串行化锁 → 熔断器
            router._deliver_to_platform(...)
        else:
            # 走独立 HTTP 发送
            _send_to_platform(...)
    if delivery_errors:
        return "; ".join(delivery_errors)  # 失败信息返回给调用方
```

**关键：** cron 投递走的是**同一个 weixin adapter 实例**的 `send()` 方法，所以锁和熔断器都能生效。但问题在于：锁只能保证"同一时刻只发一条"，不能保证"前一条触发的限流冷却期结束后再发下一条"。

## 调用方对失败的处理

### 会话回复（gateway run.py）
```python
# 伪代码
result = await adapter.send(chat_id, response)
if not result.success:
    # 尝试 plain-text fallback
    fallback = await adapter.send(chat_id, plain_text)
    if not fallback.success:
        logger.error("Fallback send also failed")  # 放弃
```

### Cron 投递（scheduler.py tick）
```python
# 伪代码
delivery_error = _deliver_result(job, content)
mark_job_run(job_id, success, error, delivery_error=delivery_error)
# 不重试，等下次 tick（最多 60s 后）才有机会再次发送
# 但 no_agent 每次 tick 重新执行脚本，输出可能不同
```

## 配置参数

| 参数 (extra / env var) | 默认 | 说明 |
|:---|:---|:---|
| `send_chunk_delay_seconds` | 1.5 | chunk 间延迟 |
| `send_chunk_retries` | 4 | 单 chunk 最大重试次数 |
| `send_chunk_retry_delay_seconds` | 1.0 | 基础重试延迟 |
| `rate_limit_circuit_threshold` | 1 | 窗口内触发几次开熔断 |
| `rate_limit_circuit_window_seconds` | 30.0 | 计数窗口 |
| `rate_limit_circuit_open_seconds` | 30.0 | 冷却时长 |

## 熔断器死亡螺旋（2026.7.3 新发现）

`threshold=1` 导致一次 iLink 限流就封锁 30s。iLink 进入长期惩罚期（小时级累积配额耗尽）后：

```
发送 → iLink 限流(-2) → 4次退避重试(3s×4=12s) → 全失败 → 记录事件 → threshold=1 → 开闸30s
      ↓ 30s 后
发送 → iLink 仍限流 → 又开闸30s → 无限循环
```

短时间内两次事故日志（23:15:44-23:16:58 和 23:33:23-23:35:53），每次持续数分钟无消息送达。

## 媒体绕过 `_send_text_chunk`（2026.7.3 新发现）

`send()` 方法在发文本前先发媒体附件（图片/文件/音频），`_deliver_media()` 直接调 iLink API，不走 `_send_text_gate` 锁，不受 `WEIXIN_SEND_INTERVAL_SECONDS` 约束。媒体+文本紧接发送可能 < 1s，增加触限概率。
