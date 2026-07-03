---
name: l1-review
description: "【L1 固定审查层】交付物完成、任务收尾时触发。用 qwen-bailian(千问3.7Max) 对照 sprint-contract 的契约逐条审查交付物，输出 PASS/CONDITIONAL/FAIL + 逐条裁决。走 execute_code 直连 API（不经 delegate_task，锁定 provider）。FAIL 或 CONDITIONAL≥3 建议手动升级 Opus。只报告不改文件。审交付物不审过程。"
version: 1.0.0
category: productivity
tags: [review, qa, qwen, verification, methodology]
---

# L1 Review — 千问固定审查层

## When to Use
## When to Use
- **触发（硬规则）**：交付物已完成、任务收尾时。以下任一条件满足即触发，不是"建议"是"必须"：
  - 用户要求"复查/检查/审一下/看看有没有问题"
  - Agent 产出了分析报告、方案文档、配置变更建议
  - Agent 创建/修改了文件（skill、script、config、memory）
  - 一项任务的"出方案→确认→执行"循环走到"方案完成"节点
- **反例**：日常问答、信息查询、纯讨论、用户未确认方案时，不触发。
- **前置**：最好已有 `sprint-contract` 产出的契约文件；无契约时以任务原始要求代替。

## Why it uses execute_code, not delegate_task
`delegate_task` 不支持 per-call 指定 provider（子代理继承父模型）。要**固定用 qwen** 且不动全局 `delegation.provider`，就直连 API。

## Steps
1. 定位契约文件与交付物文件（或交付物文本）。
2. 运行：
   ```
   python C:\Users\Administrator\AppData\Local\hermes\scripts\qwen_review.py \
     --contract <契约文件> --deliverable <交付物文件>
   ```
   （通过 execute_code / terminal 执行；脚本从 config.yaml 读 qwen key。）
3. 读回 JSON 裁决，向用户呈现：总裁决 + 逐条(结论/依据/修复)。

## Review Rubric（脚本内固化，三维度）
1. **任务完成度**：契约每项验收标准是否达成。
2. **论证质量**：关键论断按【事实/推理/判断】三分类——
   - 事实：权威来源？口径统一（拒绝混比）？无编造？
   - 推理：第一性原理？无预设立场？
   - 判断：边界条件成立？
3. **风险合规**：越界、遗漏边界、凭证/安全红线。
> 逐条裁决，禁止打包。

## Verdict & Escalation
- 全 PASS → PASS
- 有 CONDITIONAL 无 FAIL → CONDITIONAL
- 任一 FAIL → FAIL
- **FAIL 或 CONDITIONAL≥3 → 停下，报告后由用户手动决定是否升级 Opus**（Opus 仅手动，走 Claude Code CLI）。

> ⚠️ verdict/escalate 由脚本从 items 数组**确定性重算**，不信任 LLM JSON 里的自报字段。原理：任一条 FAIL→FAIL，CONDITIONAL≥3→escalate。防止千问在 verdict 字段里"放水"（self-completion bias）。

## 适用范围（重要）
- **所有交付物型任务都走 L1**：投资分析、内容分析、系统操作，一律审查。
- 用户觉得必要时才手动升 Opus，L1 不自触发 Opus。
## 纵向评估

每次审查自动存档到 `reviews/review_log.jsonl`。查看趋势：
```
python scripts/review_trend.py          # 完整报告
python scripts/review_trend.py --summary  # 仅摘要
python scripts/review_trend.py --last 5  # 最近5条
```

## Pitfalls

## Pitfalls

- **触发太软（已由 task-wrapup 解决）**：原先审查靠用户喊"审"或末尾提示，Agent 经常漏。现在 `task-wrapup` skill 将审查焊死在所有干活类 skill 的最后一步——审查不靠人喊，流程自己审。只要干活类 skill 正确引用了 task-wrapup，审查就不会漏。详见 task-wrapup skill。
- **架构局限（2026.7.2 验证）**：问题本质是 LLM agent 天然不会逐条比对 memory。task-wrapup 通过在 skill SOP 结构层面固化审查步骤（而非依赖 memory/末尾提示）来缓解——这比「记得提醒」更强，因为它是流程结构的一部分，不靠记忆。
- **契约和交付物用了同一个文件** → 千问会判 FAIL（交付物=空）。确保交付物包含实际产出内容（配置详情、文件路径、用户确认记录），不是复述需求。
- 只输出审查报告，**不修改任何交付物/文件/配置**。
- 不自动升级 Opus（避免 Nous Portal 额外计费）。
- Opus 升级走 Claude Code CLI，参见 `hermes/model_routing.md` 路由规则。

## See Also
- `task-wrapup` — 收尾自检清单（硬触发本 skill 的地方）
- `references/review-pipeline.md` — 完整审查管线架构、组件清单、数据流、设计决策

## 配对 Skill
- **sprint-contract**：任务开始时出契约，收尾时对照逐条比对。
- **task-wrapup**：收尾自检清单，在第 3 步自动调用本 skill。审查触发从「依赖用户喊」升级为「流程结构固定步骤」。
- 三 skill 共同构成完整闭环：事前定标准 → 干活 → 事后逐条审。
