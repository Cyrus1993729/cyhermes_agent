# 任务复盘: compaction 摘要注入用户消息 bug (2026-07-03)

## 做了什么
修复 `context_compressor.py` 中压缩摘要死锁时被注入用户当前消息的 bug。

## 怎么发现的
用户发"任务完成了吗？"查进度，Agent 却启动小红书分析。用户截图证实只发了进度询问。网关日志确认 PlanWeave 内容被注入。

## 根因
角色交替死锁 → `_merge_summary_into_tail = True` → 摘要 prepend 到 tail[0]（用户消息）→ Agent 误读历史指令。

## 修复
死锁时向后遍历找 assistant 消息 prepend，覆盖两种死锁场景。加中文框定文案。

## 决策
- 用户选择让 Opus 评估 → Opus 推荐 prepend 到 head 末尾 assistant
- Agent 本地优化：prepend 替代 append；向后遍历替代仅取 compressed[-1]
- 千问 L1 二轮审查通过

## 耗时
诊断 ~10min | Opus 评估 ~3min | 执行 ~5min | L1 审查 ~5min | 总计 ~25min

## 经验教训
- 边缘条件不要只考虑一种场景（千问第一轮发现 head=user+tail=assistant 的漏判）
- 用户消息被污染是最高优先级 bug，影响体验极严重
