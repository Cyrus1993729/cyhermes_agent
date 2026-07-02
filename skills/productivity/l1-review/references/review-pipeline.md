# 审查管线架构参考

> 2026-07-02 落地。完整闭环：事前契约 → 事后 L1 审查 → 纵向评估 → 教训回流。

---

## 组件清单

| 组件 | 路径 | 功能 |
|:---|:---|:---|
| sprint-contract | skills/productivity/sprint-contract/ | 任务启动契约：交付物清单+验收标准+口径+边界+来源+安全底线 |
| l1-review | skills/productivity/l1-review/ | L1 审查调用指南，三维度(完成度/论证质量/风险合规)+升级规则 |
| post-task-review | skills/productivity/post-task-review/ | 任务收尾复盘 + 教训回流(写回 lessons.md) |
| qwen_review.py | scripts/qwen_review.py | L1 千问审查引擎：直连 qwen-bailian API，确定性重算 verdict/escalate |
| review_trend.py | scripts/review_trend.py | 纵向评估：读取 review_log.jsonl，输出 PASS/FAIL 趋势 |
| mem_gc.py | scripts/mem_gc.py | 记忆时效扫描器：STALE/VOLATILE/SUPERSEDED/DUP 四类标记 |
| lessons.md | hermes/lessons.md | 经验教训库，sprint-contract Step 0 自动加载 |
| safety_invariants.md | hermes/safety_invariants.md | 7 类安全不变量，所有契约自动引用 |
| review_log.jsonl | hermes/reviews/review_log.jsonl | 审查日志，每次 qwen_review 运行自动追加 |

---

## 完整流程

```
用户给任务
  ↓
[事前] sprint-contract → 读 lessons.md → 出契约草案 → 用户确认
  ↓
[干活] DeepSeek v4-pro 执行
  ↓
[事后 L1] execute_code 调 qwen_review.py → 千问 3.7 Max 逐条裁决
  ↓                        ↓
  │                  代码确定性重算 verdict/escalate
  ↓                        ↓
 存档 review_log.jsonl     告知用户：PASS/CONDITIONAL/FAIL
  ↓                        ↓
[复盘] post-task-review → 判断教训是否可复用
  ↓                        ↓
  可复用 → 写入 lessons.md   一次性 → 仅复盘记录
  ↓
[下次] sprint-contract Step 0 读 lessons.md → 历史教训融入新契约
```

---

## 关键设计决策

1. **不用 delegate_task**：Hermes 子代理不支持 per-call 指定 provider。千问审查走 execute_code + urllib 直连 qwen-bailian API。

2. **确定性重算 verdict**：不信任 LLM 自评的 verdict/escalate 字段，代码从 items 数组重新计算——任一 FAIL→FAIL，CONDITIONAL≥3→escalate。消除 self-completion bias。

3. **Opus 仅手动升级**：L2 永不自动触发。FAIL 或 CONDITIONAL≥3 时暂停，等用户决定。走 Claude Code CLI（`claude -p --model opus`+代理），禁 delegate_task 调 Nous Portal。

4. **审查只报告不改文件**：所有脚本/skill 不修改交付物、配置、或文件系统。异常 fail-open（exit 0 或 2，不抛未捕获异常）。

---

## 场景覆盖

| 场景 | 审查方式 | 备注 |
|:---|:---|:---|
| 投资分析 | 通用三维度 | 契约指定口径/来源要求 |
| 内容分析 | 通用三维度 | 契约要求标注来源性质 |
| 系统操作 | 通用三维度 | 用户觉得必要时手动升级 Opus |
| 日常聊天 | 不审查 | — |

---

## 各组件如何配合

- sprint-contract 的 Handoff 传给 l1-review 的 `--contract`
- post-task-review 的教训回流写入 lessons.md
- sprint-contract 的 Step 0 读取 lessons.md
- qwen_review.py 的日志供 review_trend.py 读取
- safety_invariants.md 被 sprint-contract 模板自动引用
