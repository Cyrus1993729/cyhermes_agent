---
name: automated-investment-research
description: Automated web research for investment discovery — search infrastructure, API tooling, and multi-step research pipelines when the user wants to programmatically find companies, supply chains, or investment opportunities.
triggers:
  - "分析/研究 XX 产业链"
  - "找受益的公司/标的"
  - "发现投资机会"
  - 需要自动化联网深度调研
---

# Automated Investment Research

Programmatic web research for investment discovery from China. Covers search infrastructure diagnosis, API selection, and multi-step research pipelines.

## Principle: Don't Hack Google — Choose the Right Tool

When the user asks for automated investment research, do NOT waste time trying to bypass Google's CAPTCHA on a datacenter proxy. Google blocks datacenter IPs at the IP-reputation level — no header/Cookie trick can bypass this. Instead:

1. **Quick fact-check**: Use Bing international (`www.bing.com`, NOT `cn.bing.com`) — works direct from China
2. **Deep research**: Use dedicated search APIs that maintain their own residential IP pools

## Search Infrastructure from China

### Available
| Engine | Access | Best For |
|--------|--------|----------|
| Bing international (`www.bing.com`) | ✅ 直连 | 快速事实验证、英文商业搜索 |
| Tavily API | ✅ 直连 | AI agent 搜索，返回结构化结果+摘要 |
| SerpAPI / ValueSERP | ✅ 代理 | 真实 Google 结果（住宅 IP 池） |
| Perplexity API | ✅ 代理 | Deep Research 模式（$5/次，多轮自主搜索） |

### Blocked
| Engine | Why |
|--------|-----|
| Google 直连 | 被墙 |
| Google + 数据中心代理 | **CAPTCHA 拦截**（IP 信誉层，非请求头层） |
| Startpage | JS 渲染，curl 不可用 |
| Brave Search | 直连超时 |

### Google Custom Search API Pitfall
Google Custom Search API 看起来像解决方案，但有两个坑：
1. 搜索范围不是全网，而是你配置的 CSE 索引
2. 免费 100 次/天，对付费投资研究不够

**不要推荐 Google Custom Search API 给用户。**

## Research Pipeline Architecture

### Quick Pipeline (Tavily + Sonnet)
```
Tavily 搜索 (N 次) → Sonnet 筛选整理 → 输出结构化结果
```
- 零额外成本起步（Tavily 免费 1000 次/月）
- Sonnet 负责 80% 工作（搜索、筛选、整理）
- 适合中等复杂度任务

### Deep Pipeline (Tavily + Sonnet + Opus)
```
Tavily 搜索 → Sonnet 初筛 → Sonnet 二次筛选 → Opus 关键推理
```
- Opus 仅用于 2-3 个核心标的的深度分析
- Opus 消耗降低 60-70%
- 用户 Claude Pro 会员可能有限额（不透明 usage units）

### Perplexity Deep Research ($5/次)
```
Perplexity sonar-deep-research → 自动多轮搜索 + 综合报告
```
- 最接近 ChatGPT/Gemini Deep Research 的可编程方案
- 适合"分析某技术产业链全景"这种大任务
- 每次 $5，成本确定

## Claude Pro 会员使用注意事项

- Opus 额度以不透明 "usage units" 计量，非 token 数
- 单次产业链分析（Tavily 5次 + Opus 3轮）预估 40K input + 6.5K output tokens
- 策略：Sonnet 做 80% 工作，Opus 仅做关键推理
- 超额后 CLI 返回 "exceeded usage limit"，需等待重置

## Workflow: Starting a Research Task

1. **先确认工具可用性**：Tavily API key 是否已配置？
2. **评估任务复杂度**：快速事实核查？还是产业链全景分析？
3. **选择 pipeline**：Quick（Tavily+Sonnet）或 Deep（需 Opus/Perplexity）
4. **告知用户成本/限额预期**：Pro 会员可能碰限额、Perplexity $5/次
5. **执行并输出结构化结果**

## Tavily Setup

- API key: `C:\Users\Administrator\Desktop\Tavily API key.txt`
- Package: `tavily-python`（安装: `uv pip install tavily-python`）
- 免费层: 1000 次/月，直连可用（无需代理）
- 环境变量（可选）: `export TAVILY_API_KEY=$(cat /c/Users/Administrator/Desktop/Tavily\ API\ key.txt)`

## Zero-Dependency Curl Fallback

When Tavily API key is not configured, SerpAPI is not set up, or the `web_search` tool is missing from the agent's toolset, fall back to **curl-based HTML search**. Zero API keys, zero Python packages — just `curl` + `grep`.

### Diagnostic Workflow — Always Test Before Searching

When web search fails, do NOT assume nothing works. Test each engine individually on both routes:

```bash
# Test engines ONE AT A TIME (batching causes cascading timeouts)
curl -s -o /dev/null -w "%{http_code} %{time_total}s" --max-time 5 --noproxy '*' "https://www.bing.com" && echo " Bing直连"
curl -s -o /dev/null -w "%{http_code} %{time_total}s" --max-time 5 -x http://127.0.0.1:7897 "https://duckduckgo.com" && echo " DDG代理"
curl -s -o /dev/null -w "%{http_code} %{time_total}s" --max-time 5 -x http://127.0.0.1:7897 "https://lite.duckduckgo.com/lite/?q=test" && echo " DDGLite搜索"
```

Pick the fastest engine with HTTP 2xx/3xx before constructing the actual search query.

### Working Curl Methods

#### Bing 直连 (~1.2s, no proxy needed)

```bash
curl -sL --max-time 10 --noproxy '*' \
  "https://www.bing.com/search?q=URL_ENCODED_QUERY" \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
  | sed 's/<[^>]*>//g' | grep -iP "keyword1|keyword2" | head -50
```

- Use `www.bing.com` (not `cn.bing.com`) for international results
- Append `&setlang=en&cc=us&mkt=en-US` for English results
- The `User-Agent` header prevents mobile redirect

#### DuckDuckGo Lite via Proxy (~1.3s)

```bash
curl -sL --max-time 10 -x http://127.0.0.1:7897 \
  "https://lite.duckduckgo.com/lite/?q=URL_ENCODED_QUERY" \
  | sed 's/<[^>]*>//g' | grep -iP "pattern" | head -30
```

- `lite.duckduckgo.com` returns plain HTML — easy to parse with grep
- The JS-heavy `duckduckgo.com` main site is NOT usable via curl

### When to Use Fallback vs API

| Scenario | Use |
|----------|-----|
| Quick fact-check, news lookup, conference info | curl + Bing 直连 |
| Investment research needing structured results | Tavily API |
| Need Google-quality results | ValueSERP |
| Deep multi-turn research | Perplexity sonar-deep-research |

## Execution Template

```python
# 多轮搜索 → JSON → Claude 分析的标准模板
from tavily import TavilyClient
import json

KEY = open(r"C:\Users\Administrator\Desktop\Tavily API key.txt").read().strip()
client = TavilyClient(api_key=KEY)

queries = [
    "查询1 — 产业链全景",
    "查询2 — 公司A 合作关系",
    "查询3 — 公司B 合作关系",
    # ... 6-8 条覆盖所有角度
]

all_results = {}
for i, q in enumerate(queries):
    result = client.search(q, search_depth="advanced", max_results=8)
    all_results[f"q{i+1}"] = {"query": q, "results": [...]}

with open("C:/Users/Administrator/tmp/research_results.json", "w", encoding="utf-8") as f:
    json.dump(all_results, f, ensure_ascii=False, indent=2)

# 然后喂给 Claude:
# cat /c/Users/Administrator/tmp/research_results.json | claude -p '分析...' --model sonnet --max-turns 3
```

## References

- `references/search-api-landscape.md` — 搜索引擎 API 全面对比（2026-06 实测，含 Claude 评估）
