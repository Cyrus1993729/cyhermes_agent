# v2 5步流程复盘 — 问题汇总

> 基于 2026-07-27 黄金周报 v2 实际运行。提交 Opus 审查。

---

## 一、本次执行摘要

| 步骤 | 耗时 | 结果 |
|:--|:--|:--|
| ① 契约 | 2 min | Opus CONDITIONAL → 补③.5描述 → PASS |
| ② 闸门 | — | 用户确认 |
| ③ 执行 | — | 复用 v1 交付物 |
| **③.5 自检** | **3 sec** | **exit 0，5项全绿** |
| **④ L1 ‖ Opus** | **~15 min** | L1 CONDITIONAL(3项) + Opus CONDITIONAL(2必修) → 合并修复 |
| ⑤ 复盘 | — | 本文件 |

---

## 二、发现的问题

### 问题 1：Opus PTY 进程永不退出 🔴

**现象**：`claude --dangerously-skip-permissions -p --model opus` 在 PTY 模式下生成完 93 行完整响应后，进程状态持续 "running"，从不发 exit signal。

**影响**：
- Agent 无法通过 `notify_on_complete` 获知 Opus 完成
- 必须手动 `process poll` / `process wait`（后者也超时）
- 并行审查的实际完成时间不可预测

**当前 workaround**：通过 `process log` 读输出判断内容是否已生成完整

**待 Opus 判断**：
- 这是 PTY 模式的通用 bug 还是 Claude Code 特定版本的问题？
- 修法 A：`claude` 命令外层包 `timeout 600`，超时强杀
- 修法 B：不用 `--pty`，改用普通 terminal 模式（但 `--dangerously-skip-permissions` 可能需要 PTY？）
- 修法 C：task-wrapup 步骤里不靠 `notify_on_complete`，改为主动轮询 `process poll` + 读 log

### 问题 2：并行审查的瓶颈在 Opus 生成速度 🟡

**现象**：L1 2 分钟出结果，Opus 14 分钟。并行省了"串行等 L1"的时间但没有省"等 Opus"的时间。实际墙钟 ≈ max(L1, Opus) = Opus 时间。

**影响**：并行收益被 Opus 生成速度稀释——不是审查模式的问题，是模型推理速度的物理瓶颈。

**待 Opus 判断**：
- 这是可接受的 trade-off，还是有优化空间（如精简 Opus prompt、减少要求检查的维度数量）？
- 当前 Opus prompt 要求读两个文件 + 逐项重算 D4 + 5 个检查维度 → 是否过度？

### 问题 3：③.5 只测了"通过"路径 🟡

**现象**：v2 交付物是 v1 经 4 轮审查过的，自检自然全绿。没有验证"闸门真的能拦住错误"。

**影响**：pre_review_check.py 的阻断逻辑（定投映射错误、阈值私改、振幅矛盾）未在实战中触发过。

**待 Opus 判断**：
- 是否需要专门做一次"注入错误"的闸门测试？
- 还是等下次自然遇到错误时验证即可？

### 问题 4：workflow_check.py 不支持 ③.5 🟡

**现象**：`workflow_check.py --step "③.5"` 无此步骤代码，手动 workaround。

**影响**：追踪文件打勾靠 Agent 手动 echo，违背"硬闸门"原则。

**待 Opus 判断**：
- 修法：给 workflow_check.py 加 `③.5` case（trivial，3 行代码）
- 还是有更优雅的方案？

---

## 三、做得好的（供参考，不需修）

- ③.5 闸门零摩擦 ✅
- 冲突规则实战验证 ✅（L1 权威→CNH口径，Opus权威→境内需求拆解）
- D5 跳过消除死锁 ✅
- L1‖Opus 互补效应明显 ✅（L1 漏掉的深度问题 Opus 补上）

---

请对 4 个问题逐一给修复建议，并综合裁决。
