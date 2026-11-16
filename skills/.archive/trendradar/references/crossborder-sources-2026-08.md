# 跨境电商垂直源清单与接入记录（2026-08-07）

## 连通性实测（2026-08-07，批量 probe 直连 vs 代理 7897）

| 源 | 直连 | 代理 | 结论 |
|---|---|---|---|
| Modern Retail `/feed/` | 200 | 200 | ✅ 第1档已接入 |
| Tamebay `/feed` | 200 | 200 | ✅ 第1档已接入 |
| Retail Dive `/feeds/news/` | 200 | 200 | ✅ 第1档已接入 |
| USTR `/rss.xml` | 200 | 200 | ✅ 第1档已接入 |
| Federal Register API | 200 | 200 | ✅ 第2档（JSON 非 RSS，需脚本） |
| 雨果跨境 `/rss` | 200 HTML | 200 HTML | ❌ **RSS 已废**（返回 HTML 页面，已禁用） |
| Rest of World `/feed/latest/` | 超时 | 200 | ✅ 第2档（被墙需代理） |
| Reddit r/FBA `.rss?t=day` | 超时 | 200 | ✅ 第2档（被墙需代理） |
| Google News RSS | 超时 | 200 | ✅ 第2档（被墙需代理） |
| Marketplace Pulse `/rss` | 404 | 404 | ⏳ 第3档排障（地址失效，需找正确 URL） |
| CBP CSMS govdelivery | 406 | 406 | ⏳ 第3档排障（UA/地址问题） |
| 亿邦动力 `/rss` | 302 | 302 | ⏳ 第3档排障（跟随跳转） |

## 第 2 档 crossborder_fetcher.py 设计要点

- 代理抓取：`requests.get(url, proxies={"http":..., "https":...}, headers=UA, timeout)` → `feedparser.parse(resp.text)`（feedparser 直接拉取无法灵活控制代理）
- Federal Register API：`https://www.federalregister.gov/api/v1/documents.json?conditions[term]=<词>&order=newest&per_page=10`；**必须 FEDREG_FILTER 宽松正则过滤**（tariff|duty|trade|import|export|customs|china|ecommerce|de minimis|section 30[12]|antidumping|countervailing|...）——全库全文搜索会混入航空管制等无关文书
- Google News RSS：`https://news.google.com/rss/search?q=<urlencode>&hl=zh-CN&gl=US&ceid=CN:zh-Hans`；4 query（中 2 英 2），**每条间隔 sleep(10) 防 429**；只有标题+链接无正文
- 单源 try/except 隔离，一个失败不影响其他；输出去重后统一 JSON 到 `output/crossborder/cb_candidates.json`
- 计划任务：`TrendRadarCrossborder` 每小时跑 `crossborder_fetch.bat`（unset PYTHONPATH → uv run → 日志 output/logs/crossborder.log）
- 实测产出 ~90 条/次：Federal Register 11 + Google News 62 + Rest of World 12 + Reddit 5

## Opus 起步组合（8 源，全部零成本，当天可接）

1. Google News RSS ×4（中文 2 + 英文 2 query）
2. Federal Register API（de minimis + section 301 两条 query）——**全方案 ROI 最高**：零维护、权威、比媒体早 12-48h
3. CBP CSMS（govdelivery RSS，关税细则第一时间）
4. Marketplace Pulse（需先修复 404）
5. Modern Retail ✅
6. Rest of World ✅
7. Tamebay ✅
8. r/FulfillmentByAmazon（top/day，平台突发政策最早体感信号，比媒体早半天）

扩展组合：Retail Dive✅/Supply Chain Dive/eCommerceBytes/Practical Ecommerce/USTR✅/EU Trade/海关总署(RSSHub)/Shopify Changelog/TikTok Newsroom/雨果跨境+白鲸出海+晚点(公众号转 RSS)

## Opus 三级告警设计（政策敏感度，待实施）

- L1 即时推：tier1 政府源 + 硬触发词 → TG 带 🚨，延迟<15min，**日配额 ≤3 条**，静默时段 23:00-07:00（政策多在美东工作时间=北京深夜）
- L2 交叉确认：tier2/3 + 触发词 → 60min 内 ≥2 独立源才推（防标题党）
- L3 日汇总：其余进 16:00 日报
- 起步建议：只开 L1（政府源日均触发<1 条）

## 运维机制（Opus 建议，未实施）

- 失效源检测：fail_streak≥3 告警；items_7d==0 且日更源 → 告警（抓"HTTP 200 空 feed"静默失效）
- 采纳率汰换：源被 LLM 选中/产出 <2% 连续 4 周 → 自动停用
- 源健康周报（周日 20:00 TG）

## 待办

- 第 3 档：Marketplace Pulse（找正确地址）/CBP（换 UA）/亿邦（跟随跳转）——用户暂缓
- 中文通道：公众号转 RSS（雨果/白鲸/晚点），¥8-17/月
- 5 类新闻（美股/黄金/科技/AI/宏观）推送安排——用户待定
- 16:00 跨境日报 cron 首跑验证（2026-08-07 16:00）
