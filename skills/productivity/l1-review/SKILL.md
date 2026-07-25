---
name: l1-review
description: "【L1 固定审查层】交付物完成、任务收尾时触发。用 qwen-bailian(千问3.7Max) 对照 sprint-contract 的契约逐条审查交付物，输出 PASS/CONDITIONAL/FAIL + 逐条裁决 + 疑点标记（独立于裁判）。疑点标记触发 L2（Opus）条件性深度审查。走 execute_code 直连 API（不经 delegate_task，锁定 provider）。只报告不改文件。审交付物不审过程。"
version: 1.2.0
category: productivity
tags: [review, qa, qwen, verification, methodology, depth, l2-escalation]
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

## Review Rubric（脚本内固化，六维度 ⚠️ v1.2 升级）

> 核心原则：dim1-4 管"对不对/全不全"（千问能判），dim5 管"深不深"（千问只做存在性检查——输出疑点标记，不做深度判定），dim6 是审查前置条件（读契约执行策略施加检查）。

1. **任务完成度**：契约每项验收标准是否达成。
2. **论证质量**：关键论断按【事实/推理/判断】三分类——
   - 事实：权威来源？有无编造？
   - 推理：第一性原理？有无预设立场？
   - 判断：边界条件成立？
3. **数据逻辑**（⚠️ 2026.7.13 新增）：
   - a) 符号方向：偏差±号是否与比较关系一致
   - b) 跨小节勾稽：同一组数在报告不同小节是否数值一致
   - c) 口径一致性：同一概念全文是否使用统一术语
   - d) 基本算术：四则运算结果数量级和勾稽关系是否自洽
4. **风险合规**：越界、遗漏边界、凭证/安全红线。
5. **深度体检**（⚠️ v1.2 新增 — 存在性检查，只查"有没有"，不判"对不对"。输出疑点标记而非深度通过/不通过）：
   - a) 证据链：关键结论是否有具体证据支撑？还是空泛断言？
   - c) 反方视角：是否至少提及了替代解释或反方观点？
   - d) 盲区标注：是否主动标出了不确定性、数据局限、未覆盖范围？
   - e) 承重假设：整个结论压在哪一条假设上？这条假设被说清楚了吗？被守住了吗？
   - f) 问题替代：交付物有没有把"真正的问题"偷换成一个更好答的邻近问题？
   - ⚠️ dim5 子项中「逻辑跳跃」（推理链条有无断层）属于 L2 审查范围，L1 不做——L1 只输出「疑似逻辑跳跃」疑点标记让 L2 确认。
6. **执行策略契合度**（⚠️ v1.2 新增 — 非独立维度，作为审查前置条件）：
   - 审查开始时先读契约「执行策略」字段
   - 选单模型 → 对 dim1/dim2 施加全局一致性检查（有无拼接痕迹、前后矛盾、论证断裂）
   - 选 Kanban → 对 dim1/dim2 施加接缝检查（子任务衔接处有无信息丢失、handoff 损耗、口径不一致）

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

## 疑点标记（⚠️ v1.2 新增 — 与裁判结果独立）

L1 输出的不是简单的 PASS/FAIL，而是**裁判 + 疑点标记**两件事：

| 输出 | 是什么 | 示例 |
|:---|:---|:---|
| **裁判** | 基于 dim1-6 自己能判定的：能不能过？ | PASS / CONDITIONAL / FAIL |
| **疑点标记** | 千问看到但无法确定的：要不要请 Opus 看看？ | 「证据链单薄」「承重假设未论证」「疑似逻辑跳跃」 |

**两者互不影响。** 可以 PASS 但有疑点（交付 + "建议 Opus 再看一眼这几处"），也可以 CONDITIONAL 但无疑点（修完格式即可）。

## L2 深度审查（⚠️ v1.2 新增 — Opus 条件触发）

### 触发条件
**不是每次都跑。** 仅当 L1 输出了疑点标记时，才触发 L2：

```
L1 完成 → 有疑点标记？
  ├─ 无 → 跳过 L2，直接进下一步
  └─ 有 → 触发 L2（Opus），专查疑点
```

### L2 专查什么
L1 能做但不敢拍板的事——L2 来确诊：

| L1 疑点 | L2（Opus）做什么 |
|:---|:---|
| 「证据链单薄」 | 判断：是真的证据不够，还是证据够了只是来源单一？ |
| 「疑似逻辑跳跃」 | 重推一遍逻辑链：A→B 中间真的有断层吗？ |
| 「承重假设未论证」 | 判断：这条假设被推翻的话，整个结论还站得住吗？ |
| 「问题替代」 | 判断：交付物回答的问题跟契约定义的问题是不是同一个？ |

### L2 执行方式
通过 Claude Code CLI 调用 Opus：
```
claude -p --model opus "审查以下交付物的疑点：[疑点描述] + [交付物内容]"
```
L2 输出：每个疑点 → 确诊/排除 + 具体修复建议。

### L2 的裁判
L2 不重新打分，只对疑点逐个给出：**确诊（需修复）/ 排除（疑点不成立）**。确诊的疑点视为 dim5 相关子项 CONDITIONAL。

## 审查总结（Agent 向用户呈报格式）

```
【L1 审查】
  总裁决：CONDITIONAL
  问题：dim3-a 符号方向搞反了 | dim1 缺少 XX 数据
  疑点：⚠ 证据链单薄 | ⚠ 承重假设未守住

【L2 审查】（仅疑点触发时有）
  ⚠ 证据链单薄 → 确诊 → 需补充 XX 数据源
  ⚠ 承重假设 → 排除 → 假设已充分论证

【修复计划】
  1. 修正符号错误
  2. 补充多源交叉验证
  修完重审
```

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
