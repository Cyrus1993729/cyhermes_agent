# 搜索引擎 API 全面对比（2026-06 实测）

## 中国网络环境下的搜索引擎可用性

| 引擎 | 访问方式 | 结果质量 | 成本 | 适用场景 |
|------|---------|:---:|------|------|
| Bing 国际版 (`www.bing.com`) | 直连 ✅ | ★★★★ | 免费无限 | 快速事实核查 |
| Tavily API | 直连 ✅ | ★★★★ | 免费 1000次/月 | AI agent 搜索 |
| ValueSERP | 代理 ✅ | ★★★★★ (真实 Google) | $5/月 5000次 | 需要 Google 质量 |
| Perplexity `sonar-deep-research` | 代理 ✅ | ★★★★★ | $5/次 | 产业链全景扫描 |
| SearXNG 自建 | 需境外服务器 | ★★★ | 服务器成本 | 聚合搜索 |

## 不可用的方案

| 方案 | 失败原因 |
|------|---------|
| Google 直连 | 被墙 |
| Google + 数据中心代理 | **CAPTCHA 拦截**（IP 信誉层，非请求头层，无法绕过） |
| Google Custom Search API | ①非全网搜索（CSE 索引限制）②免费 100次/天不够 |
| Startpage | JS 渲染，curl 不可用 |
| Brave Search | 直连超时 |
| Gemini Deep Research | 无 API，仅网页端 |
| ChatGPT Deep Research | 无 API，仅网页端 |

## Deep Research 选项对比（Claude 2026-06 评估）

| 服务 | API 可用？ | 定价 | 运作方式 | 投资研究适用性 |
|------|:---:|------|------|------|
| Perplexity `sonar-deep-research` | ✅ | ~$5/次 | 自动数十次搜索 + 综合报告 | 较适合，对英文内容覆盖好 |
| Perplexity `sonar-pro` | ✅ | $3/1M input + $5/1000次 | 单次搜索增强 | 适合快速查询 |
| Tavily | ✅ | 免费 1000次/月 | 返回结构化结果（标题/URL/摘要） | 搜索工具 building block |
| Exa（原 Metaphor） | ✅ | $5/1000次 | 语义搜索 + 爬取 | 找类似文章和文档 |
| You.com Research | ✅ | 按量 | 综合报告模式 | 不如 Perplexity 成熟 |
| OpenAI Responses API (`web_search_preview`) | ✅ | 按 token | 单步搜索，非多轮研究 | 一般 |
| Google Gemini API (Grounding) | ✅ | 按 token | 非完整 Deep Research pipeline | 一般 |

## Claude 推荐的分层架构

```
产业链扫描 (大任务): Perplexity sonar-deep-research ($5/次)
    +
精确检索 (公司/财报): Tavily + Exa
    +
推理综合: Claude Sonnet (80%) + Claude Opus (20%)
```

## Claude Pro 会员 Opus 使用注意事项

- 限额以不透明 "usage units" 计量，非 token 数
- 单次产业链分析（Tavily 5次 + Opus 3轮）预估 40K input + 6.5K output tokens
- 推荐策略：Sonnet 做信息搜集和初步整理，Opus 仅用于 2-3 个核心标的的深度推理
- 超额后 CLI 返回 "exceeded usage limit"，需等待重置

## 本次实战验证（OpenLight 产业链，2026-06-25）

- 工具：Tavily 6 次搜索 + Claude Sonnet 综合分析
- 耗时：~90 秒
- 发现：4 对官方合作关系确证，2 对确认为 Serenity 个人推断，发现 IQE 上游供应商（Serenity 未提及）
- 结论：Tavily + Sonnet 对产业链分析完全够用，不需要 Google/Opus
