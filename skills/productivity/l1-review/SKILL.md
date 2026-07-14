---
name: l1-review
description: "【L1 固定审查层】交付物完成、任务收尾时触发。用 qwen-bailian(千问3.7Max) 对照 sprint-contract 的契约逐条审查交付物，输出 PASS/CONDITIONAL/FAIL + 逐条裁决。走 execute_code 直连 API（不经 delegate_task，锁定 provider）。FAIL 或 CONDITIONAL≥3 建议手动升级 Opus。只报告不改文件。审交付物不审过程。"
version: 1.1.0
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

## Review Rubric（脚本内固化，四维度 ⚠️ v1.1 从三维升级）

> 2026.7.13 升级：新增第 3 维度「数据逻辑」。原三维只做形式审查（完成度/论证质量/合规），遗漏了符号错误（+0.14%→−0.14%）和术语混用（"折价"vs"估值偏离"）等低级错误。新四维度已在测试用例中验证能发现此类问题。

1. **任务完成度**：契约每项验收标准是否达成。
2. **论证质量**：关键论断按【事实/推理/判断】三分类——
   - 事实：权威来源？有无编造？
   - 推理：第一性原理？有无预设立场？
   - 判断：边界条件成立？
3. **数据逻辑**（⚠️ 2026.7.13 新增，必须逐项核验）：
   - a) 符号方向：偏差±号是否与比较关系一致（A<B→差为负）
   - b) 跨小节勾稽：同一组数在报告不同小节是否数值一致
   - c) 口径一致性：同一概念全文是否使用统一术语（不可一处叫"折价"一处叫"估值偏离"）
   - d) 基本算术：四则运算结果数量级和勾稽关系是否自洽
4. **风险合规**：越界、遗漏边界、凭证/安全红线。
> 逐条裁决，禁止打包。

## Verdict & Escalation
- 全 PASS → PASS
- 有 CONDITIONAL 无 FAIL → CONDITIONAL
- 任一 FAIL → FAIL
- **审查阶段全程自动**：L1/Opus 发现问题 → Agent 自动修复 → 重审 → 循环至 PASS（每层最多 3 轮）
- **第 4 轮启动前停下**：同一审查层连续 3 轮未 PASS（含 FAIL 和 CONDITIONAL），第 4 轮启动前停下询问用户
- CONDITIONAL 算审查轮次，修完必须重审
- 详见 sprint-contract v1.2 升级规则

> ⚠️ verdict/escalate 由脚本从 items 数组**确定性重算**，不信任 LLM JSON 里的自报字段。原理：任一条 FAIL→FAIL，CONDITIONAL≥3→escalate。防止千问在 verdict 字段里"放水"（self-completion bias）。

## 适用范围（重要）
- **所有交付物型任务都走 L1**：投资分析、内容分析、系统操作，一律审查。
- 用户觉得必要时才手动升 Opus，L1 不自触发 Opus。
## 已验证效果（案例库）

### 2026.7.3 — 捕获 compaction 修复的边缘条件
- **背景**：Agent 修复了 compaction 摘要注入用户消息的 bug（死锁时将摘要 prepend 到 `compressed[-1]`）
- **L1 发现**：当 `head=user, tail=assistant` 时也会死锁，但此时 `compressed[-1]` 是 user 消息——摘要又被注入用户消息，违反了"必须 prepend 到 assistant"的合约
- **结果**：Agent 补加了向后遍历找 assistant 的逻辑，二轮审查 PASS
- **教训**：边缘条件审查是 L1 的强项——模型擅长发现"你只考虑了情况 A，没考虑情况 B"

每次审查自动存档到 `reviews/review_log.jsonl`。查看趋势：
```
python scripts/review_trend.py          # 完整报告
python scripts/review_trend.py --summary  # 仅摘要
python scripts/review_trend.py --last 5  # 最近5条
```

## Pitfalls

### L1 API 超时的降级方案（2026.7.13 黄金周报 实踩）

qwen-bailian API 可能在直连和代理下都超时。根因通常是两层的：

**第一层：脚本超时太短**。`qwen_review.py` 原先 `timeout=90`，qwen3.7-max 是推理模型（有 reasoning_content），大 payload（契约+交付物 3-8K chars）时推理 tokens 可达 1000+，90s 不够。**已修复为 `timeout=300`**。如果以后再超时，先检查脚本 timeout 值。

**第二层：API 真的不可达**。此时不应无限重试，也不能静默跳过审查。

**降级流程**：
1. 先确认脚本 timeout≥300（已修）
2. 重试 2 次（直连 + 代理各一次）
3. 2 次均失败 → 执行人工自检：对照契约逐条检查 D1-D4，标注"L1 API不可达，人工自检替代"
4. 自检结果写进 task-wrapup 收尾摘要，裁决标 CONDITIONAL
5. 生成复盘时写入 lessons.md（L8 规则）

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
