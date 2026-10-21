# 中国宏观数据一手源直抓指南（2026-07-24 实测）

适用场景：要中国官方宏观数据（GDP/CPI/PPI/社零/固投/工业增加值/房价/产能利用率），搜索引擎被降级或不可信时，直接抓一手源。

## 1. 国家统计局（首选，curl 直连可用）

- 最新发布列表：`https://www.stats.gov.cn/sj/zxfb/`（UTF-8，无需代理，加普通 UA 即可）
- 存档翻页：`index_1.html`、`index_2.html` …（约每月 1 页）
- 发布稿 URL 规律：`./YYYYMM/tYYYYMMDD_<id>.html`（相对列表页路径）
- **标题即含核心数字**：如「2026年6月份居民消费价格同比上涨1.0%」「2026年6月份工业生产者出厂价格同比上涨4.1% 环比下降0.3%」「2026年6月份规模以上工业增加值增长5.3%」——可先从标题取数，再抓正文核验环比/分类/累计均值。
- 发布节奏：CPI/PPI 每月 9-11 日；GDP 季度初步核算为季后 ~15-16 日；月度经济数据（工业/社零/固投）每月 15 日左右；70城房价每月 15 日。
- GDP 季度稿正文含：当季/累计同比、三次产业分行业增速、历史季度同比对照表、季调环比对照表。

解析片段（列表页取 CPI/PPI/GDP 链接）：

```python
import re
txt = open('nbs.html','rb').read().decode('utf-8', errors='replace')
for u,t in re.findall(r'href="([^"]+)"[^>]*>([^<]{6,80})</a>', txt):
    if any(k in t for k in ['居民消费价格','出厂价格','国内生产总值']):
        print(t.strip(), '|', u)
```

正文提取：先删 `<script>/<style>`，去标签，找锚句（如「6月份，全国居民消费价格」）截取上下文。

## 2. 全年预测 / 官方增长目标

NBS 不发布预测。备选：

| 源 | 可达性（本机实测） | 用法 |
|---|---|---|
| AP News `apnews.com/hub/china` | ✅ curl 200 | hub 页找 `/article/china-economy-...` 链接；正文常含 IMF 最新预测、两会增长目标、海关出口数据。正文在 `<div class="RichTextStoryBody">` 及内嵌 JSON 里 |
| TradingEconomics `/china/forecast`、`/china/gdp-growth-annual` | ✅ curl 200 | 表格列头为 `Actual, Q3/26, Q4/26, Q1/27, Q2/27`（季度同比预测）；正文有 "is expected to be X% by the end of this quarter" 和长期趋势句；表格含 Consensus 对比 |
| Reuters | ❌ 401 | — |
| IMF（imf.org 页面 + datamapper API） | ❌ Akamai Access Denied | — |
| World Bank worldbank.org | ❌ 连接被关闭 | — |
| DBnomics `IMF/WEO:latest` | ✅ 但**版本可能过旧** | 先查 resolved dataset 版本（如 WEO:2025-04），引用预测前必须核对；`GET /v22/series/IMF/WEO:latest/CHN.NGDP_RPCH?observations=1` |

## 3. Bing 降级信号（实测 2026-07）

- 浏览器路径：可能弹 Cloudflare「请验证您是真人」；勾选通过后结果仍可能退化为泛化结果（搜「中国2026年二季度GDP增速 国家统计局」返回中国百科条目）。
- curl 路径：HTML 页可能无 `b_algo` 结果块（72KB 空壳页）。
- RSS 路径（`&format=rss`）：CJK 多词查询被错误分词（「上半年GDP…」返回单字「上」的字典结果）；英文多词查询同样退化为单词泛化结果。
- 判定标准：结果与查询意图明显不相关 = 引擎在糊弄你 → 立即转一手源，不要继续重试同一路径。

## 4. 本次任务验证过的结论样例（2026-07-24）

- GDP：Q1 +5.0%，Q2 +4.3%，H1 +4.7%（NBS 2026-07-16 初步核算）
- CPI：4月 +1.2%，5月 +1.2%，6月 +1.0%
- PPI：4月 +2.8%，5月 +3.9%，6月 +4.1%
- 2026 官方增长目标 4.5%–5%；IMF 2026 预测 4.6%（AP 2026-07-14 转引）
