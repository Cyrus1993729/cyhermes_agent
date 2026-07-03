---
name: sprint-contract
description: "【任务启动契约】接到交付物型任务（报告/分析/脚本产物）时，先与用户敲定一份可验收的『任务契约』：交付物清单、每项验收标准、口径定义、边界(不做什么)、来源要求。产出 contract_<任务名>_<日期>.md 供收尾时 l1-review 逐条比对。讨论/取数/只读类任务不触发。与 l1-review 配对使用。"
version: 1.0.0
category: productivity
tags: [workflow, contract, acceptance, review, methodology]
---

# Sprint Contract — 任务启动契约

## When to Use
- **触发**：交付物型任务（要产出报告、分析结论、脚本/数据产物）。
- **不触发**：纯讨论、纯取数、只读浏览（与验证管线触发规则一致）。

## Why
先定义"什么算做完 + 用什么口径"，收尾时 L1（qwen）才能逐条比对，而不是主观判断。
符合用户方法论：出方案→确认→执行；口径归一、拒绝混比；按结论拆条。

## Steps
0. **起草前读 `hermes/lessons.md`**：检查本次任务类型是否有历史经验教训可复用，有则融入契约的验收标准。
1. 从任务里抽取交付物，列成清单（每项一行，可独立验收）。
2. 为每项写**验收标准**（可判定的、非模糊的）。
3. 写**口径定义**：涉及的数据/指标用哪个标准，禁止不同标准混比。
4. 写**边界**：明确不做什么，防止范围蔓延。
5. 写**来源要求**：需权威来源的项标注；禁编造数据/引用。
6. 把契约存成文件 `hermes/contracts/contract_<任务名>_<YYYY-MM-DD>.md`，**给用户确认后**再开工。

## Contract Template
```markdown
# 任务契约: <任务名>  (<YYYY-MM-DD>)

## 交付物清单
- D1: <交付物> — 验收标准: <可判定条件>
- D2: ...

## 口径定义
- <指标A>: 采用 <标准/来源>，单位/时间范围 <...>

## 边界（不做）

## 来源要求
- 需权威来源: D1, D2；禁编造/推断标注为(推断)

## 适用的历史教训
- L1 <规则名> → 已转为验收标准 D#   （无则写"本类型无历史教训"）

## 升级规则
- L1(qwen) FAIL 或 CONDITIONAL≥3 → 停下，由用户决定是否升级 Opus

## ⚠️ 安全不变量（所有任务通用，不可协商）
本任务必须遵守 `hermes/safety_invariants.md` 中的全部底线规则。
违反任一条 = 立即停止，向用户报告。
```

## Pitfalls

### 边界措辞过窄 → L1 误判 FAIL（2026.7.3 PlanWeave 实踩）

写边界条款时，注意**信息载体多样性**：帖子/文章的内容可能同时分布在文本（desc/正文）和图片（配图/截图）中。写成「除非配图明确显示 URL」会把文本 URL 排除在外，即使帖子正文里已明确列出链接，L1 仍会判定越界。

**正确写法**：用概括性措辞覆盖所有信息载体，例如「除非帖子内容（正文或配图）中已直接提供的外部链接」，而非只限定一种载体。

**真实案例**：PlanWeave 分析时，契约写「不搜索 GitHub 仓库（除非帖子配图明确显示 URL）」→ 帖子 desc 文本中列出了 `GitHub: https://github.com/GaosCode/PlanWeave` → Agent 基于文本 URL 搜索仓库 → L1 判 FAIL → 修正契约为「帖子内容中明确列出了 URL，允许搜索」→ 重审 PASS。问题不在 Agent 行为，在契约措辞。

### 契约太窄导致低价值交付

如果边界写得太死（如完全禁止搜索外部资源），即使帖子内容已提供了线索，分析报告也只能基于极少的信息片段拼凑，质量大打折扣。写边界时应允许**基于帖子已提供线索的合理延伸搜索**，只禁止无线索的漫无目的搜索。

## Handoff
契约文件路径（`hermes/contracts/contract_<任务名>_<日期>.md`）传给收尾阶段的 **task-wrapup**（第 3 步自动调 `l1-review --contract`）。

## See Also
- `task-wrapup` — 收尾自检清单（含 L1 审查触发、来源区分、产物存档、微信分段）
- `l1-review` — 千问固定审查层
- `skills/productivity/l1-review/references/review-pipeline.md` — 完整审查管线架构

## 🔗 完整管线
审查系统完整参考见 l1-review skill 的 [`references/review-pipeline.md`](../l1-review/references/review-pipeline.md)（组件清单、数据文件、流程、技术决策）。
