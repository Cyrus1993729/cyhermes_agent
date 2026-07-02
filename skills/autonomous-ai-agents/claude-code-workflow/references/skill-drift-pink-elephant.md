# Skill 漂移案例：粉色大象效应（2026-06-23）

## 背景

两个并列的 Claude Code skill：
- `serenity-skill`（上游开源）— 供应链瓶颈深度研究方法论
- `serenity-value`（用户自建 overlay）— 估值增强 + 范围锚定

## 问题

用户下任务：「用 serenity-value 深度调研 A 股 AI 算力芯片产业链，仅限 A 股，禁止美股/存储链」。

连续两次运行，Claude Code Opus 都输出**美股存储产业链**（Micron/Seagate/SanDisk），完全无视约束。

## 排查过程

### 第一次失败 → 认为 prompt 约束不够
Prompt 写了"仅限 A 股"，但没写"禁止存储/HBM"。加了硬约束后重跑。

### 第二次失败 → 发现根因不在 prompt
硬约束清晰但依然跑偏。定位到 `serenity-skill/SKILL.md` 第 155-157 行：

> *"For A-share AI semiconductor scans, a strong opening can be: 先看带宽和工艺约束，再看纯算力芯片。AI 需求继续扩张时，先紧起来的往往是**内存互连**、CMP/减薄、刻蚀和耗材..."*

这是一行**具体正向路标**：「A 股 AI 半导体 → 内存互连」。而 serenity-value 的约束是**抽象禁令**：「禁止存储、禁止 HBM」。具体示例永远碾压抽象禁令。

### Clarify 方案：要不要改 serenity-skill L155-157？
用户提出能否修改原 skill。经分析，不改更好：
- 那是上游作者的作品，方法论的一部分
- 改了治标不治本——LLM 仍可从训练数据中重建 "AI 瓶颈 = HBM" 联想
- 正确解决层是 overlay，不是基底

### 委托 Claude Opus 做根因分析
Opus 的诊断摘要：

1. **粉色大象效应（pink-elephant problem）**：说「别想大象」 → 脑子里先出现大象。否定约束先被处理，被否定的词随后被激活。

2. **Skill bleed-through**：两个并列 skill 之间没有优先级裁决层。system > user 有层级，同级 skill 没有。LLM 选更显著的那个——具体示例。

3. **业界对应概念**：
   - Salience bias — 高显著度内容主导生成
   - Negative-constraint failure — 否定式约束失效
   - Instruction hierarchy 缺失 — 同级 skill 无裁决层

## 三件套修复（已落地于 serenity-value v1.1.0）

| 招数 | 做法 | 原理 |
|------|------|------|
| ① 用具体打具体 | 在 overlay 里放等量具体的正向路标（「A 股 AI 算力 → 寒武纪、海光、中微…从这些名字出发」） | 用正向具体替换正向具体，而非用抽象禁令对抗 |
| ② 显式作废 | 「serenity-skill L155-157 在本 overlay 下作废」——点名 supersede | 给 LLM 明确的优先级裁决，而非让它自己猜 |
| ③ 条件护栏 | 列出 Mcron/HBM/NAND 拦截词——**但仅当用户明确排除存储时才触发**，用户研究存储则不拦截 | 硬约束不该靠 prompt 说服，该靠代码级检测兜底 |

## 关键教训

1. **否定约束不可靠** — 不要说「不要 X」，要说「应该去 Y」，且 Y 要跟 X 一样具体
2. **抽象规则 < 具体示例** — 写 skill 时，每一条笼统规则都应该配一个具体正例
3. **硬约束在 LLM 外** — 真正不能越界的红线（市场、产业链），应该在 skill 里写检查逻辑，不靠 prompt
4. **条件触发，不永久封禁** — 关键词护栏必须跟用户范围绑定，不能说「永远禁止存储研究」
5. **同级 skill 无裁决层** — 如果两个 skill 可能冲突，必须在 overlay 里显式声明优先级

## 最低成本的复用

以后创建任何 overlay skill，三件套模版：

```markdown
## 范围锚定规则

### ① 正向具体开场白
给本 overlay 覆盖范围内的具体标的方向（人名地名公司名）

### ② 显式作废
点名基底 skill 中与本 overlay 冲突的具体行/段落 → 作废

### ③ 条件护栏
IF 用户明确排除了某类别 THEN 拦截关键词列表
ELSE 不拦截（不替用户做排除决定）
```

## 验证结果

第三次运行成功输出全 A 股 AI 半导体产业链报告（22 家候选，30+ 信源，零美股，零存储链）。自检通过。
