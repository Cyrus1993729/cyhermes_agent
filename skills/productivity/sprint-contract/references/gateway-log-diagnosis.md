# 涌现型任务 — 网关日志诊断技法

用于排查"Agent 收到的消息 ≠ 用户发送的消息"类 bug。

## 适用场景

- Agent 执行了用户没要求的任务
- 用户在对话中说"我没发这条消息/链接"
- 怀疑 compaction / session recovery / 消息注入 bug

## 三步技法

### 1. 网关日志确认真实消息

```bash
grep "inbound message" gateway.log | grep "msg=" | tail -5
```

找最后一条 inbound message 的 `msg=` 字段——这是用户真正发的内容。
对比 Agent 系统提示词里"第一条 user message"的内容，如果不一致 → 消息被注入了。

### 2. 追踪注入时间点

找 gateway.log 中 compaction 触发时间：
```bash
grep "Session hygiene" gateway.log
```

如果 compaction 和 inbound message 在同一秒发生，压缩摘要可能就是注入源。

### 3. 代码路径溯源

从 gateway/run.py 的 session hygiene 开始（第 9506 行），追踪：
- `history = _compressed`（第 9764 行）
- agent/context_compressor.py 的 `compress()` → `_merge_summary_into_tail`（第 2611-2616 行）
- anthropic_adapter.py 的 `convert_messages_to_anthropic()` —— system 消息只有最后一条有效（第 2291-2305 行）

## 已验证案例

2026-07-03：用户发"任务完成了吗？"，Agent 收到含 PlanWeave 链接的消息。
网关日志确认用户真实消息只有 14 个字。根因为 `_merge_summary_into_tail` 把含历史指令的压缩摘要 prepend 到了用户当前消息。

## 关键架构常识

- **Anthropic adapter 只保留最后一个 system 消息**：`anthropic_adapter.py` 的 `convert_messages_to_anthropic()` 中，`system` 变量被每个 `role="system"` 消息覆盖。这意味着不能在 mid-conversation 插入独立 system 消息——会覆盖系统提示词。设计修复方案时必须考虑此限制。
