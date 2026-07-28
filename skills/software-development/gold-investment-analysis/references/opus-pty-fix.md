# Opus Claude Code 进程管理 — PTY 陷阱

> 来源：2026-07-27 黄金周报 v2 审查流程验证。由 Opus 本尊诊断并给出 D 方案。

## 问题

PTY 模式下 `claude --dangerously-skip-permissions -p --model opus` 进程生成完完整响应后永不退出。
stdin 永不 EOF → 进程永久挂起 → `notify_on_complete` 不触发 → Agent 不知道审查已完成。

## 根因（Opus 诊断）

`--dangerously-skip-permissions` **不需要 PTY**。当初上 PTY 是"以为 skip 需要 TTY"的误判。
`claude -p`（print 模式）本身非交互，PTY 反而阻止了 stdin EOF。

## 正确用法

```bash
# Hermes terminal() 调用方式：
bash -c 'timeout 900 claude --dangerously-skip-permissions -p --model opus "prompt" < /dev/null'
```

或在 task-wrapup 审查步骤中：
```
timeout 900 claude --dangerously-skip-permissions -p --model opus \
    "审查交付物..." < /dev/null
```

- 非 PTY（不用 terminal pty=true）
- stdin 接 /dev/null（进程写完自然退出）
- timeout 900 外层保险

## 效果

实测：14 分钟生成 93 行完整审查，进程正常 exit 0，`notify_on_complete` 正确触发。
