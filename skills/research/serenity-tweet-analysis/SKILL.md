---
name: serenity-tweet-analysis
description: "分析 Serenity (@aleabitoreddit) 的推文：原文翻译 → 大白话解释 → 产业链/金融深度分析。| 跟 serenity-search 的区别：那个是「搜推文/缓存」，这个是「分析推文内容」。需同时加载 serenity-search 获取推文数据。"
requires: [serenity-search]
---

# Serenity 推文分析 — 标准工作流

## 触发条件

用户发送 Serenity 的推文截图或文本，要求分析。典型触发语：
- "分析这条推文"
- "帮我解读一下"
- "他是什么意思"
- "这段话怎么理解"

## 分析结构（必须三段式）

### 第一段：原文 + 翻译

- 先给出完整英文原文
- 再给中文翻译
- 保持原始格式（换行、$符号等）

### 第二段：大白话解释

用通俗易懂的语言、生活化的比喻解释：
- 这家公司是干嘛的？（一句话说清楚）
- 它所在的产业链在解决什么问题？
- 推文里提到的每家公司分别扮演什么角色？（用比喻，如"施工队""灯泡厂"）
- 整条逻辑链怎么串起来？

**原则：** 假设读者完全不懂这个产业，用日常事物打比方。避免术语堆砌。

### 第三段：金融与产业分析

根据推文内容灵活选择分析维度，可包括但不限于：

- **卡脖子程度**：供应商集中度、认证周期、扩产难度、不可替代性
- **估值水位**：当前股价、P/E、历史区间、行业对比
- **产业链位置**：上下游关系、谁离瓶颈最近
- **催化剂**：近期可能推动股价的事件
- **风险**：什么情况说明判断错了
- **市场共识 vs 分歧**：什么是市场已知的、什么可能是被忽视的
- **竞争格局**：同类公司对比、替代威胁

**数据来源要求：**
- 优先调用 Claude Code（`claude -p "..." --model opus --max-turns 12 --dangerously-skip-permissions`）联网获取实时数据
- Claude Code 不可用时，使用 `serenity-search` 工具搜索缓存推文
- 所有数据标注来源

### 第四段（可选）：综合排序

如果推文提到多家公司，给出综合吸引力排序表。

## 输出格式规范

- 使用微信分段格式 `（1/N）`
- 每段 ≤1500 字
- 表格用简洁的 Markdown
- 估值数据标注获取时间
- 结尾标注「研究参考，不构成投资建议」

## 产业链验证：关系发现方法论

当推文提到多家公司之间的供应链关系时，不要直接接受 Serenity 的推断。必须联网验证每一对关系。

### 验证 Pipeline（优先 Tavily + Claude Sonnet）

```
Tavily 多轮搜索 (6-8 次，覆盖不同关键词) 
    → 保存结果到 JSON
    → Claude Sonnet 读 JSON 做综合分析和置信度评估
```

### 工具链

| 步骤 | 工具 | 说明 |
|------|------|------|
| 获取推文原文 | `serenity-search` | 从缓存提取文本 |
| 产业链验证搜索 | **Tavily API**（直连可用，免费 1000次/月） | 多关键词搜索，每条推文提到的关系都要搜 |
| 搜索策略 | 每对公司一条 query + 产业全景一条 + 竞品一条 | 6-8 条 query 覆盖全面 |
| 分析推理 | **Claude Code Sonnet** (`--model sonnet`) | 读 Tavily JSON 结果，综合评估关系置信度 |
| 深度推理（可选） | Claude Code Opus | 仅在 Sonnet 不够时，限于 1-2 个核心问题 |
| 快速事实核查 | Bing 国际版 (`www.bing.com`) | 直连，单条事实验证 |

### 注意事项

- **Google 不可用**：当前代理 IP 被 Google CAPTCHA 拦截，不要浪费时间绕过
- **Claude WebSearch 不够用**：它的 WebSearch 是单步工具，不是 Deep Research pipeline。用 Tavily 替代
- **Sonnet 足够**：产业链整理和关系评估用 Sonnet 完全够，节省 Opus 额度
- **搜索结果标注来源**：每条结论标注是"搜索结果确证"还是"Serenity 推断"

详见 `automated-investment-research` 技能的完整搜索基础设施说明。

## 示例

参见 2026-06-24 对 OpenLight 推文的完整分析（6 段微信消息）。

## 🧩 工作流配方

**任务**：分析 Serenity 推文
**加载顺序**：
1. `serenity-search` — 搜索/拉取推文数据（先 --update 增量拉取，再搜索）
2. `serenity-tweet-analysis` — 本 skill：翻译→大白话→产业链/金融深度分析
3. 涉及产业链关系时，叠加 `supply-chain-ripple-analysis` 做供应链验证
4. 涉及投资建议/调仓判断时，触发 `decision-gate`（汇报发现→征得同意→再给建议）
**交付**：微信分段（格式见 xiaohongshu-analysis「输出与交付」章节）
**收尾**：任务完成后检查 `post-task-review` 触发条件，满足则生成复盘
