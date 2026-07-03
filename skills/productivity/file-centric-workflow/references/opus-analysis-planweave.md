# PlanWeave × Hermes：Opus 完整分析

> 2026-07-03 · 模型：Claude Opus · 上下文：xiaohongshu PlanWeave 帖子分析后

## 一、理念层面

**PlanWeave 核心哲学：把"真相源"从 Agent 上下文搬到文件系统。**

四个展开：
1. **状态外置**：进度在 state.json + results/，Agent 是无状态工人，杀掉重启读文件即恢复
2. **工作切成可领取原子单元 + 显式依赖图**：不是一个大任务扔给 AI，而是 T-001→T-002 有边有先后
3. **审查是图上的一等公民**：每个 Task 天然带 Review Block，不是事后手动的
4. **每次运行留痕 + 有限步长**：`--step-limit 10`，可中断可恢复

**Hermes vs PlanWeave 本质区别**：
- Hermes 是「对话中心」——真相活在上下文窗口
- PlanWeave 是「文件中心」——真相活在磁盘，Agent 只是临时读写器

所有五个痛点（失忆/踩文件/漏喊审/找不到产物/上下文混乱）全是「对话中心」这同一个根。

## 二、delegate_task 的范式反转

delegate_task 子代理看不到主对话历史 → 在对话中心范式是 bug，在文件中心范式是 feature。子代理不该依赖对话历史，应从 Block 文件拿到全部上下文。

## 三、Coordinator 映射纠正

错误：用 delegate_task 串行模拟 Coordinator。
正确：Coordinator 必须是主 Agent 自己。

**Coordinator 循环**：
1. 读 state.json → 找 ready 块
2. 标记 claimed → 写回（锁）
3. 派 1 个子代理，只给该 Block 上下文
4. 等回来 → 触发 Review
5. passed → done；needs_changes → 回第 3 步
6. 回到第 1 步

**并行条件**：多块 writes 目录不重叠才同时 delegate。

## 四、行动路线

### Tier 0 — 今天

1. 建 `~/planweave/` 骨架 + JSON 模板
2. L1 审查焊进干活 skill 末步（消灭漏喊审）
3. 给现有 cron 加 cursors.json（治好失忆）

### Tier 1 — 本周

4. Coordinator + Runner skill 搭档
5. 子代理 workspace 隔离
6. results/ + index.md 产物规范

### Tier 2 — 以后

7. 自动并行（writes 不重叠的 ≤3 块）
8. doctor/recovery skill
9. 画布注册表（跨项目检索）

## 五、核心金句

> 「缺的从来不是能力，是把真相搬出对话窗口这个决定。」
> 用现成的 skill + execute_code + terminal + memory + cronjob 就能拼出来。

## 六、与现有 Hermes 能力的映射

| PlanWeave 概念 | Hermes 等價物 |
|:---|:---|
| Task Graph | manifest.json + Python 算就绪 |
| state.json | 手写 JSON + terminal 读写 |
| Coordinator | 主 Agent（非子代理） |
| plan-runner | delegate_task（1个，非3个） |
| plan-reviewer | qwen_review.py 焊进 skill |
| plan-recovery | doctor 校验脚本 |
| Auto Run + step-limit | cronjob + cursors.json |
| Block context | 委托时只传该 Block 的内容 |
| results/ | 文件系统目录 + index.md |
