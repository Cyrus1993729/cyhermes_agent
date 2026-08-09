# 跨境电商垂直数据源方案（Opus 完整方案，2026-08-07，待落地）

背景：热榜通道（newsnow 11 平台）跨境新闻连续多批 0 条——热榜是大众注意力榜，跨境电商是 B 端垂直行业，只有破圈事件（T86 取消/Temu 被调查）才上榜。**继续调关键词是沉没成本**；v1.1 跨境词组降级为"大事件哨兵"，日常供给必须靠独立垂直通道。

## 三个关键架构修正（Opus 挑战初版方案后确立）

1. **垂直源不过关键词白名单（源级信任）**：垂直源本身 100% 是跨境内容，再过白名单只会误杀（如"日本 JCT 申报"一个词不命中）。管线改双通道共池：
   - 通道 A（保留现状）：newsnow 热榜 ×11，每小时，走白名单过滤（有排名/热度信号）
   - 通道 B（新建）：垂直 RSS/API ×8-20，分级频率，**不过白名单**，源级信任
   - 统一候选池：热榜命中白名单 ∪ cb_items 中 24h 内未 picked 的（后者不过白名单）
2. **中文跨境媒体原生 RSS 大面积已失效**（雨果跨境/AMZ123/卖家之家/电商报关停 RSS 出口）——中文真实主战场是微信公众号。技术选型：公众号转 RSS 服务（wechat2rss 一类，¥100-200/年，全方案唯一建议花钱处）或 RSSHub 自建（本机 Docker ~200-300MB 内存）。
3. **政策源 > 媒体源**：政府源零维护、权威、比媒体早 12-48 小时。

## 数据源清单（按性价比）

### 起步 8 源（全部免费，当天可接，预计日产 60-120 条候选→精选 5-10 条）
| 源 | 类型 | 地址 |
|---|---|---|
| Google News RSS ×4 | 关键词聚合 | 中文 q1 `跨境电商 OR 出口电商 when:2d`、q3 `关税 (跨境 OR 电商 OR 包裹) when:2d`；英文 q4 `"de minimis" OR "Section 301" tariff ecommerce when:2d`、q5 `Temu OR Shein OR "TikTok Shop" (policy OR ban OR fine OR investigation) when:2d`。格式 `https://news.google.com/rss/search?q=<query>&hl=zh-CN&gl=CN&ceid=CN:zh-Hans`（英文换 hl=en-US&gl=US）。**限频 60min/源、走 7897 代理、防 429（错峰每 10min 打一个）**；只给标题+链接，无正文，入围条目需二次抓正文首 800 字 |
| Federal Register API | 美国法规库 | `https://www.federalregister.gov/api/v1/documents.json?conditions[term]=de+minimis&order=newest&per_page=20`（亦有 .rss）。**全方案 ROI 最高**：关键词+机构+类型组合查询、JSON 带全文摘要、零维护、比媒体早 12-48h。为 de minimis/section 301/section 232/country of origin 各建一条 |
| CBP CSMS | 美国海关公告 | `https://content.govdelivery.com/accounts/USDHSCBP/bulletins.rss`——关税细则第一时间，早于媒体 |
| Marketplace Pulse | 亚马逊数据分析 | `https://www.marketplacepulse.com/rss`（需验证） |
| Modern Retail | 品牌/DTC/平台 | `https://www.modernretail.co/feed/` |
| Rest of World | 新兴市场出海 | `https://restofworld.org/feed/latest/`（Temu/Shein/东南亚，选题独一份） |
| Tamebay | 英国电商政策 | `https://tamebay.com/feed` |
| r/FulfillmentByAmazon | 社群信号 | `https://www.reddit.com/r/FulfillmentByAmazon/top/.rss?t=day`——平台突发政策最早的体感信号，通常比媒体早半天 |

### 扩展（第 2-4 周加）
- 英文媒体：Retail Dive、Supply Chain Dive、eCommerceBytes、Practical Ecommerce、FreightWaves、The Loadstar、PYMNTS、Digiday（feed 地址见 Opus 原始输出，均需批量验证）
- 政策：USTR `ustr.gov/rss.xml`、CBP Newsroom、EU Commission Trade（Press Corner）、中国海关总署（RSSHub `/gov/customs` 或自写 5 行解析）、商务部、国务院关税税则委员会
- 平台官方：Shopify Changelog、TikTok Newsroom、About Amazon News、eBay Seller Updates（页面轮询）、Walmart Marketplace Blog
- 中文：雨果跨境/白鲸出海/亿邦动力/36氪出海/晚点 LatePost（公众号转 RSS 或 RSSHub 路由，选 2-3 个，同质化严重）
- X 账号（最后加，与 RSS 重叠 ~70%）：@juozaskaziukenas、@Tamebay、@ecommercebytes、@USTradeRep、@CBP——第 1 个月不做

## 抓取频率分级（配合 ETag/If-Modified-Since 条件请求，90% 返回 304）
- T1 政策源（Federal Register/CBP/USTR/海关）：15 min（更新稀疏、请求量极小）
- T2 权威媒体：60 min ｜ T3 Google News：60 min 错峰 ｜ T4 行业/社群/公众号：120 min ｜ T5 低频官方（Shopify Changelog 等）：6h

## 三级去重
1. URL 规范化 + UNIQUE 约束（拦 60%；Google News 跳转 URL 需先解真实链接——解析 `url=` 参数或 HEAD 跟随）
2. 标题 SimHash 汉明距离 ≤3（拦转载改标题，72h 窗口；中文先分词）
3. 跨源同事件聚类（3-gram Jaccard >0.55 → cluster_id；同 cluster 只送 tier 最小那条进 LLM，其余作为"另有 N 家报道"佐证——顺带免费的重要性信号：5 源覆盖 = 大事）

## 三级告警（政策敏感度：只有"能改变你今天行动"的信息才配打断）
- **L1 即时推**（延迟 <15min）：`source_tier==1`（政府源）AND 命中硬触发词 → 直接推 TG 带 🚨。政府源天然不造谣，无需二次确认
- **L2 交叉确认**（30-60min）：tier∈{2,3} AND 硬触发词 → 暂存 alert_level=1，**60min 内同 cluster ≥2 独立源**才推（防标题党，成本是延迟 1h，很划算）
- **L3 日汇总**：其余全部进 09:10/18:10 精选
- 防轰炸三闸门：日配额即时推 ≤3 条（超出降级日汇总）、cluster 只推一次、静默时段 23:00-07:00（美东工作时间=北京深夜，拦下大部分误扰）
- 起步建议：只开 L1（政府源日均触发 <1 条，覆盖 90% 真·关键政策）

硬触发词（可进 frequency_words.txt 新板块 `crossborder_alert`）：
中文：关税/加征关税/取消关税/小额豁免/免税额度/800美元/de minimis/清关新规/海关新规/出口管制/实体清单/反倾销/双反/封店/封号潮/账号冻结/资金冻结/下架/合规新规/9610/9710/9810/综试区/跨境电商出口退税
英文：`"de minimis"` `"Section 301"` `"Section 232"` `"executive order"` `"final rule"` `"effective immediately"` tariff duty `"customs ruling"` `"seller account"` suspension `"mass suspension"` ban fine investigation VAT IOSS GPSR DSA `"country of origin"`

## 运维（没有它任何 RSS 聚合 3 个月内烂掉）
- 失效检测：`fail_streak>=3` → TG 运维告警；`items_7d==0` 且日更源 → 告警（抓"HTTP 200 但空 feed"的静默失效，比只看状态码可靠）
- 源健康周报：周日 20:00 自动推（每源 7 日条目数/最后成功时间/被精选采纳次数）
- 采纳率驱动汰换：被 LLM 选中数/产出数，连续 4 周 <2% → 自动停用（比人工判断客观）
- 反向验证（唯一发现未知盲区的方法）：每月人工抽 10 条"别处看到但系统没推的跨境新闻"反查缺失源

## 成本
- 全部免费接口（newsnow/RSS/Reddit/Federal Register/Google News）+ 已有 7897 代理 = ¥0
- 公众号转 RSS：¥8-17/月（可选，中文通道需要）
- LLM 精选：¥5-25/月（日候选 150-250 条→两阶段：先标题粗排，再入围 25 条带正文摘要；政策类用规则判定免费）
- **合计约 ¥10-45/月**

## 落地路线图（验收标准）
- **第 1 周**（半天，零成本）：批量验证 8 源（PowerShell Invoke-WebRequest 循环，FAIL 换同类替代）→ 写 `crossborder_fetcher.py`（feedparser + ETag + URL 规范化 + SimHash → cb_items 表）→ 接 Federal Register 两条 query + CBP CSMS → 改 prepare_candidates.py（候选池并入 cb_items，不过白名单，LLM prompt 加跨境板块）→ L1 即时告警（仅政府源+硬触发词，日配额 3，静默 23:00-07:00）→ 计划任务 T1 15min/其余 60min。验收：cb_items 日新增去重 ≥30；跨境板块 ≥3 条且"值得看"比例 ≥60%；连续 3 天无重复
- **第 1 月**：Docker 起 RSSHub（接 36氪出海/海关总署）、买公众号转 RSS（雨果跨境/白鲸出海/亿邦/晚点）、Google News 6 条 query + 跳转 URL 解析 + 二次抓正文、扩展 12 源、源健康监测上线、L2 交叉确认、事件聚类。验收：日候选 ≥100、跨境板块 5-8 条、源存活率 ≥90% 且失效 24h 内告警、中文贡献 ≥30%、政策发布→推送中位延迟 <30min、月成本 <¥50
- **长期**（2-6 月）：源自净化（采纳率汰换）、实体+时间线（政策第 N 次更新提示）、数值监控（运价指数/汇率/FBA 费率超阈值才推）、跨境周报（Top5 事件+政策日历）、x-monitor 接入（与 RSS 同去重池，验证漏报）、反向验证。验收：漏报率 <20%、人工维护 <20min/月、重大政策零漏报

## 落地方式说明
Opus 建议**不要**把垂直源塞进 TrendRadar 的 `rss` 段（共用关键词筛选与频次统计逻辑会被白名单误杀、稀释热榜频次权重）——新建独立 `crossborder_fetcher.py` 与 prepare_candidates.py 平级，独立表或加 channel 列。cb_items 表结构：id/url_canonical(UNIQUE)/title/title_norm/simhash/summary/source_id/source_tier(1=政府 2=权威媒体 3=行业 4=社群聚合)/lang/published_at/fetched_at/cluster_id/alert_level(0=常规 1=候选告警 2=已即时推)/picked_at。
