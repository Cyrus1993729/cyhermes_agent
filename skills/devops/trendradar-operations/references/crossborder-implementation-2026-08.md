# 跨境电商垂直源落地记录（2026-08-07，第 1/2 档已完成）

## 源连通性实测（批量 curl/urllib 探测，直连 vs 代理 127.0.0.1:7897）

| 源 | 直连 | 代理 | 结论 |
|---|---|---|---|
| Modern Retail `modernretail.co/feed/` | ✅ 200 | ✅ | 纯配置（TrendRadar rss 段） |
| Tamebay `tamebay.com/feed` | ✅ 200 | ✅ | 纯配置 |
| Retail Dive `retaildive.com/feeds/news/` | ✅ 200 | ✅ | 纯配置 |
| USTR `ustr.gov/rss.xml` | ✅ 200 | ✅ | 纯配置 |
| Federal Register API（JSON） | ✅ 200 | ✅ | 需写代码（非 RSS） |
| 雨果跨境 `cifnews.com/rss` | ✅ 200（**HTML 页面！**） | ✅ | ❌ RSS 已废，禁用 |
| Rest of World | ✗ 超时 | ✅ 200 | 被墙，须代理 |
| Reddit `.rss` | ✗ 超时 | ✅ 200 | 被墙，须代理 |
| Google News RSS | ✗ 超时 | ✅ 200 | 被墙，须代理 |
| Marketplace Pulse `/rss` | ✗ 404 | ✗ 404 | 地址失效，待排障 |
| CBP CSMS govdelivery | ✗ 406 | ✗ 406 | 需换 UA/地址，待排障 |
| 亿邦动力 | ✗ 302 | ✗ 302 | 需跟随跳转，待排障 |

**关键结论**：
- 中文跨境媒体（雨果跨境）原生 RSS **已废弃**——`/rss` 返回 HTML 订阅页而非 XML。中文通道只能靠公众号转 RSS（¥100-200/年）或 RSSHub
- TrendRadar **不支持按源代理**：全局代理会让 newsnow 直连源挂掉（newsnow 走代理实测 403）→ 代理源必须独立 fetcher
- "8 源半天零成本"是 Opus 的乐观估计：实际 = 5 源纯配置（30 分钟）+ 4 源写代码（1-2 小时）+ 3 源排障

## 落地实现

### 第 1 档：5 个 RSS 源 → config.yaml `rss.feeds`（YAML 列表格式，非 JSON）
- 新增：modern-retail / tamebay / retail-dive / ustr（各带 `max_age_days: 2-3`）
- 雨果跨境 `enabled: false`（RSS 废，留待公众号通道）
- 验证：跑一次 TrendRadar，日志"6 个源成功 1 失败"；rss_items 表 feed_id 分布确认入库（各 10 条）

### 第 2 档：`crossborder_fetcher.py`（项目根，uv run）
4 类源，统一 JSON 输出到 `output/crossborder/cb_candidates.json`：
1. **Federal Register API**（直连）：2 条 query（`conditions[term]=de minimis` / `section 301`），JSON 解析
2. **Rest of World**（代理）：feedparser
3. **Reddit r/FulfillmentByAmazon top/day**（代理）：feedparser，带 UA
4. **Google News RSS**（代理）：4 条 query（中文跨境/中文关税/英文 de minimis/英文平台风险），**每条间隔 10s 防 429**

实测一次输出 ~90 条（fedreg 11 + gnews 62 + restofworld 12 + reddit 5）。

🔴 **Federal Register 全库搜索噪音**：`conditions[term]` 是全文搜索，"de minimis"/"section 301" 会命中大量无关法规（航空管制修正案、牙科研究等）。解法：源头 `FEDREG_FILTER` 宽松正则（tariff|duty|trade|import|export|customs|china|de minimis|section 30[12]|antidumping|countervailing|...），标题不命中即丢弃。过滤后剩贸易/关税/涉华法规（边缘相关如钢铁反倾销交给 LLM 精选判断）。

- 定时：`crossborder_fetch.bat`（set PYTHONPATH= + uv run + 日志重定向）→ 计划任务 `TrendRadarCrossborder /SC HOURLY`

### 管线 v2：prepare_candidates.py 三通道合并
- **通道 A 热榜**（newsnow）：白名单过滤（`matches_word_groups` 全量）→ channel=hot
- **通道 B RSS 跨境源**（TrendRadar rss 库，feed_id ∈ {modern-retail, retail-dive, tamebay, ustr}）→ channel=rss
- **通道 C crossborder JSON** → channel=cb
- **垂直源（B/C）不过关键词白名单（源级信任）**，仅过 GLOBAL_FILTER 噪音过滤（`matches_word_groups(title, [], [], global_filters)`）
- 合并去重：hot 优先保留（by_norm 先到先留）；排除 pushed_titles.json
- `MAX_CANDIDATES = 200`（三通道全量 ~200 条，LLM 输入 ~6K 字符成本仍低，不截断保留挑选空间）
- 输出 stats：hot_raw/hot_whitelist/rss_raw/cb_raw/after_dedup/after_pushed/per_channel_final

实测：hot_raw 614 → whitelist 86；rss_raw 40；cb_raw 90；合并去重后 192-201 候选 → per_channel {hot: 62, rss: 40, cb: 90}。

🔴 **截断顺序坑（已修）**：MAX_CANDIDATES 过小会把排在最后的 cb 通道截掉（120 时 cb 只进 18/99）——全量候选才 ~200 条，直接放宽不截断。

## 遗留（第 3 档 + 第 2 块收尾）
- 排障 3 源：Marketplace Pulse（找正确 RSS 地址）、CBP CSMS（换 UA/头）、亿邦（跟随 302）
- 中文通道：公众号转 RSS 服务（雨果跨境/白鲸出海/晚点 LatePost），用户尚未拍板花钱
- 精选 cron（09:10/18:10）尚未创建——等推送机制第 3 块确认后建
- L1 政府源即时告警（Federal Register + 硬触发词）未实现
- RSS 源接入后 LLM 精选 prompt 需加"跨境电商板块 + 源级信任说明"
