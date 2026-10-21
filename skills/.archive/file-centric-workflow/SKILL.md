---
name: file-centric-workflow
description: 文件中心工作流——把真相源从Agent上下文搬到文件系统。用state.json+cursors.json+manifest.json让Agent变成无状态工人，解决cronjob失忆、审查漏喊、产物丢失、上下文混乱。基于PlanWeave启示+Opus分析。
version: 1.0.0
tags: [workflow, state, agent, coordinator, cron, delegation]
---

# 文件中心工作流

## 核心心法

**把"真相源"从 Agent 上下文搬到文件系统。** Agent 是无状态的工人，文件是大脑。

根因：Hermes 是「对话中心」——进度、产物、审查全活在聊天窗口里，窗口关了就死。

## 画布骨架

```
~/planweave/<项目名>/
├── manifest.json      # 任务定义（有哪些任务、依赖、验收标准）
├── state.json         # 运行时状态（每个任务/块现在什么状态）
├── cursors.json       # cron 专用（last_seen_id、时间水位线）
├── results/<T-id>/<时间戳>/   # 每次运行的产物
└── index.md           # 人和 Agent 都能读的产物目录
```

### state.json schema

```json
{
  "updated_at": "ISO时间",
  "tasks": {
    "T-001": {
      "title": "任务名",
      "deps": [],
      "status": "pending|ready|claimed|done|needs_changes",
      "claimed_by": null,
      "claimed_at": null,
      "workspace": "results/T-001",
      "writes": ["results/T-001"],
      "review": "pending|passed|needs_changes"
    }
  }
}
```

### cursors.json schema

```json
{
  "last_seen_tweet_id": "12345",
  "last_run": "ISO时间",
  "total_processed": 42
}
```

## 六大模式

### 1. Coordinator = 主 Agent（⚠️ 不用 delegate_task 做协调）

主 Agent 当 Coordinator，循环如下：

```
每一轮：
  1. 读 state.json
  2. 算出 ready 的块，挑 1 个
  3. 标记 claimed，写回 state.json（锁）
  4. delegate_task 派 1 个子代理，只给该 Block 上下文
  5. 等回来 → 读 results/ 产物
  6. 触发 Review
  7. passed → done；needs_changes → 标回 ready
  8. 回到第 1 步
```

**并行条件**：多个 ready 任务的 `writes` 目录不重叠时才同时派。

### 2. 审查焊进 Skill 末步（消灭漏喊审）

每个干活类 skill 最后一步固定：
- 调千问逐条比对契约
- 最多重试 2 次
- 失败通知用户

### 3. cronjob + cursors.json（治失忆）

```
cron 每次：
  1. 读 cursors.json → last_seen_id
  2. 只抓比它新的
  3. 处理 → 产物写 results/
  4. 更新 last_seen_id 写回
```

加 id 去重 guard 防水位线写坏。

### 4. Workspace 隔离

每个子代理分配独立 `results/<T-id>/`，明确只准写这里。并行时互不踩。

### 5. 产物按规范落盘

`results/<任务>/<时间戳>/` + index.md 一行目录。Hermes memory 存指针，不存内容。

### 6. Doctor 校验

execute_code 检查 state.json 不变量：claimed 超 N 分钟无结果 → 重置为 ready。

## 关键洞察

**delegate_task 子代理看不到主对话历史** → 在文件中心范式这是 feature。子代理不该依赖对话历史，应从 Block 文件拿到全部上下文。

## 行动路线

| 层级 | 做什么 | 收益 |
|:---|:---|:---|
| 🟢 今天 | 建画布骨架 + JSON 模板 | 地基 |
| 🟢 今天 | L1 审查焊进干活 skill 末步 | 消灭漏喊审 |
| 🟢 今天 | 给现有 cron 加 cursors.json | 治好失忆 |
| 🟡 本周 | Coordinator + Runner skill 搭档 | 自动逐块推进 |
| 🟡 本周 | 子代理 workspace 隔离 | 并行不踩 |
| 🟡 本周 | results/ + index.md 产物规范 | 下次找得到 |
| 🔴 以后 | 自动并行（writes 不重叠） | 吞吐提升 |
| 🔴 以后 | doctor 自愈 | 鲁棒性 |

## 来源

Opus 对 PlanWeave (GaosCode/PlanWeave) 的分析，2026-07-03。原始对话见 xiaohongshu-analysis PlanWeave 帖子分析会话。

## 另见

- `sprint-contract` + `l1-review` — 本 skill 的审查模式可与之配对
- `subagent-driven-development` — 子代理开发流程，本 skill 提供 Coordinator 层的补充
- `xiaohongshu-analysis` — 触发本次分析的 skill，其视频下载决策流程采用同源的「槽位缺口」思路
