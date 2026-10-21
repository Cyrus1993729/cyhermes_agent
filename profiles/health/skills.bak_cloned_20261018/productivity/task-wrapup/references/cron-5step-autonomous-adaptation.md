# Cron 自治 5 步闭环适配模式

## 背景

标准「走流程」5 步闭环（sprint-contract → decision-gate → 执行 → task-wrapup → post-task-review）依赖用户交互——用户确认契约、用户说"改吧"触发闸门、用户喊"收尾"触发审查。但 cron 作业无人交互，必须适配。

## 适配总表

| 步骤 | 原版（人控） | Cron 适配 |
|:---|:---|:---|
| ① sprint-contract | Agent 出契约 → 用户确认 | Agent 自建契约文件 → 自检通过 |
| ② decision-gate | 用户说"改吧"/确认方案 | 自检闸门：前置条件全满足 → 自动通过 |
| ③ 执行 | 正常干活 | 不变（仍然用 terminal + web_search 等工具） |
| ④ task-wrapup | 用户说"收尾"触发 | 执行完自动触发：步骤完整性 + 来源 + L1 + 存档 |
| ⑤ post-task-review | 用户互动触发 | 自动生成复盘 → 判断是否写入 lessons.md |

## 关键适配细节

### decision-gate → 自检闸门

Cron prompt 中明确定义自检清单：
```markdown
### ② decision-gate（cron 自检闸门）
- [ ] 契约文件已创建
- [ ] 关键依赖可达（如代理、API、目录存在）
- [ ] 全部 ✓ → 自动通过，进入执行
```
不通过时应停止并报告原因。

### task-wrapup → 嵌入 cron prompt

不能依赖 cron agent 在完成工作后"记得"调 task-wrapup——执行惯性会跳过。**必须把 task-wrapup 的检查项直接写在 prompt 的第④步中**，作为不可跳过的硬步骤。

### L1 审查 → 在 cron 中跑 qwen_review.py

Cron 没有交互式工具限制，可以用 terminal 跑 `python ~/path/qwen_review.py`。
- PASS → 继续
- CONDITIONAL → 在最终回复中呈报条件项
- FAIL → 修复后重审（最多 2 次），仍 FAIL 则注明原因继续（不要死循环阻塞 cron）

### 最终回复规则

Cron 的 final response 只含两样：
1. 任务产出正文
2. 收尾自检摘要（`🔍 收尾自检：...`）

不要掺杂中间步骤进度——系统会把 final response 直接投递给用户。

## 实际案例

**黄金周报 cron（2026-07-13）**：
- 原 cron prompt 只有执行四步，无流程闭环
- 用户要求"每次触发都要走流程"
- 适配方案：prompt 改为 5 步结构 + skills 数组加载 sprint-contract/task-wrapup/post-task-review/l1-review + 投递从 origin 改为 telegram
- Cron ID: `54117ed8a949`

## 适用范围

- 任何需要"走流程"的 cron 作业
- 任何无人交互的定时交付物型任务
- 信号：用户说"这个 cron 每次触发都要走流程"

## 不要做的事

- 不要在 cron prompt 里写"等待用户确认"——cron 没有用户
- 不要让 cron agent 用 clarify 工具——会挂住
- 不要在中间步骤输出进度到 final response——会污染投递内容
