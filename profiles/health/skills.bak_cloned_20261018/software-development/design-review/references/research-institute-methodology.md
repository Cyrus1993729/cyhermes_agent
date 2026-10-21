# 研究院方法论知识库

> 来源：用户的两份设计文档 — v3.1-DRE（Agent 版）和 v3.2.1-DRE（Manual 版）

## 两份文档的关系

| | v3.1-DRE | v3.2.1-DRE |
|---|---|---|
| 定位 | 理想的 Agent 自动化版 | 保底的人工执行版 |
| 态度 | "这是我想做的" | "如果做不出 agent，至少可以这么做" |
| 核心创新 | 六层架构、委托式研究工程、多执行器 | H 检查点、Context Packet、Outcome Tracking、时间预算 |

**不是冲突关系，是 aspiration → fallback 的演进。**

## v3.1 的六层架构

```
0. Research Intake & Framing（问题接收与框定）
1. Research Design Gate（研究设计评审关）
2. Research Track（A/B/C 路由研究主线）
3. Delegated Research Engineering（委托式研究工程）
4. Development Prep（开发准备）
5. User Delivery & Decision Support（用户交付）
6. Knowledge Growth（知识成长层）
```

## v3.2.1 的 18 步流程 + 4 个 H 检查点

```
问题框定 → 快速侦察 → Go/No-Go → H1 研究设计确认
→ 双轴路由 → Baseline / Challenger（隔离）→ 比较
→ 证据表 → 重大发现检查 → [委托式数据研究]
→ Red Team 审稿 → H3 核心结论确认
→ 最终简报 → 置信度/决策 → 复盘 → H4 知识库确认
```

## 三条研究路径

| 路径 | 文件数 | 适用场景 | H 节点数 |
|------|--------|---------|---------|
| 快速 | ~9 | 低风险、公开资料够、快速判断 | 2 |
| 标准 | ~14 | 中等复杂、有决策价值 | 3 |
| 深度 | ~19 + outcome | 投研、战略、高价值 | 4 |

## 核心方法论精华（可复用）

### Baseline / Challenger 隔离
- Baseline 和 Challenger 必须独立运行
- Challenger 初始阶段不能看到 Baseline 的具体结论
- 目的：防止锚定效应——Challenger 看到 Baseline 后会只做局部反驳

### 证据表双轨
- `07_evidence_table.md`：总证据表（所有来源）
- `13_data_evidence_table.csv`：数据证据子表（仅来自委托式研究工程）
- 最终报告以 07 为总入口，数据来源链接到 13

### 置信度分层（强制）
```
1. 高置信度事实
2. 中置信度判断
3. 低置信度线索
4. 暂不能判断的问题
```

### Context Packet 模板
跨工具/跨 Agent 传递上下文的标准格式：
```
【项目名称】
【当前阶段】
【任务目标】
【必须阅读的内容】（粘贴全文）
【只需摘要参考的内容】
【禁止事项】
【输出格式】
【质量标准】
```

### Outcome Tracking
仅适用于「可验证结果型研究」（投资、产品判断、经营策略等），不适用于纯概念学习或资料整理。

## 红队审查结论（2026.06）

Claude Code 对 v3.1 的审查结果：
- **不该投入工程实现**
- 3 个致命问题：幽灵 API、无界返工循环、有状态 vs 无状态矛盾
- 4 个严重问题：路由伪逻辑、知识库坟场、LLM 验证 LLM、data_task_package 矛盾
- 建议：v3.2.1 人工版对当前阶段足够用
- 如果要工程化：先删幽灵 API、先做知识检索、先加返工终止条件
