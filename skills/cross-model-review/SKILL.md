---
name: cross-model-review
description: "双模型并行审查：将同一 prompt 同时发给两个不同模型独立审查，用确定性脚本对比输出、交叉验证证据。适用于任何需要高质量判断的审查场景。"
category: productivity
tags: [review, cross-validation, parallel, methodology, quality]
---

# Cross-Model Review — 双模型并行审查

将同一审查 prompt 同时发给两个不同模型（如 Opus + Codex），并行运行，各自独立输出，然后用确定性脚本对比两者的发现。消除单模型审查的"天花板"问题——一个模型漏掉的，另一个可能抓到。

## When to Use

- 对交付物质量要求极高的审查任务
- 涉及重大决策的论证质量检查
- 需要交叉验证单模型结论是否可靠时
- 两个模型都是顶级（$20/月会员已付），成本对等时

## Core Principle

**"证据驱动仲裁，不靠模型投票"**。两个模型的输出必须经过确定性预验证，不能直接信任任何一方的结论。

## Workflow

### 1. 准备相同 Prompt

两个模型收到完全一致的审查 prompt，包含：
- 审查标准（验收条件/维度/要求）
- 交付物内容
- 固定输出 schema（强制结构化，否则无法机械对比）

**关键**：不要让两个模型用完全相同的审查路径。prompt 中刻意给不同审查角度，例如：
- 审查器 A：从需求逐项寻找满足证据
- 审查器 B：假设交付物有缺陷，寻找反例和漏洞

### 2. 并行发送

```
Opus (Claude Code CLI):    background=true, stdin</dev/null, --effort high
Codex (Codex CLI):         background=true, pty=true, --sandbox danger-full-access
```

两者同时启动，互不依赖。用 `notify_on_complete=true` 等结果。

### 3. 确定性预验证（最关键的步骤）

对比脚本先不判语义，先做机械验证：

1. JSON schema 是否有效
2. 文件和定位是否在交付物中存在
3. quote/excerpt 是否逐字存在于原文（接地校验）
4. 公式是否可复算
5. 测试命令是否可复现

**验证失败的 finding → 标 invalid_evidence，丢弃。** 这一步几乎零成本，能拦截大量幻觉误报。

### 4. 问题归并

按（维度 + 定位 + 主张对象）聚类，区分关系类型：
- `agreement`：同一问题，结论一致 → 高置信
- `compatible`：不同问题，互不冲突
- `severity_dispute`：问题一致，严重程度不同
- `factual_conflict`：对同一可验证事实结论相反 → 需机械验证
- `unmatched`：单方发现 → 需交叉质证

### 5. 仲裁：不是一票否决

| 情形 | 处置 |
|---|---|
| 都过 | 放行（加"盲区风险"标签） |
| 都否同一处 | 高置信，修复 |
| 一方否（证据已验证） | 交叉质证：甩给沉默方令其"反驳或确认" |
| 一方否（无有效证据） | 丢弃 |
| 各执一词（同一点、各有证据、互斥） | 这才上抛用户 |
| critical/安全类可信指控 | 默认阻断 |

公式：`BLOCK = evidence_valid AND in_scope AND (critical OR reproducible OR violates_AC OR both_confirmed)`

## Pitfalls

- **双模型同质化**：两个顶配可能共享盲区→双双放行真缺陷（静默失败）。通过审查路径差异化缓解，但不可完全消除。高风险任务考虑保留弱异质模型（如千问）撒网。
- **Codex background+pty 不自动退出**（2026-08-01 实测）：输出完整后 PTY 进程可能不退出。检测 `tokens used` 出现即视为完成。
- **上抛洪水**：上线前先跑影子模式量分歧率。>15% 说明仲裁规则没对齐。
- **月费对等 ≠ 吞吐对等**：双模型双烧，token 消耗翻倍，可能撞速率上限。
- **同一模型生成≠同一模型审查**：如果交付物由某个审查模型生成，审查时它会延续自己的假设。避免向审查器暴露生成过程。

## Key Metrics

上线后持续监控：
- 两模型问题重合率（过高→假独立性）
- 单方 finding 验证成功率（过低→一票否决过激）
- 用户仲裁率（过高→标准不清）
- 逃逸缺陷率（终极指标）
- 审查延迟 P50/P95

## Related

- `l1-review` — 当前 L1 审查层 SOP（含已知"天花板"局限）
- `5step-workflow-architecture` — 5 步流程架构全景
- `codex` — Codex CLI 调用指南
- `claude-code` — Claude Code CLI 调用指南
