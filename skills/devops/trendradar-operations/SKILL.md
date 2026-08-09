---
name: trendradar-operations
description: TrendRadar 自托管运维：部署、纯采集+AI主编精选管线、关键词防串设计、故障排查与定制。
version: 1.0.0
category: devops
tags: [trendradar, self-hosted, news-pipeline, ops, keywords]
---

# TrendRadar Operations

## 架构（2026-08 确立，用户拍板）
```
TrendRadar（纯采集器）           Hermes（主编）
每小时计划任务采集入本地库   →   每天 2 次：读库 → 白名单+去重(脚本)
无推送、无 AI 分析                → LLM 语义精选 → 分板块简报 → 推 TG
```
- 分工原则（用户偏好）：**工具做机械层，AI 做智能层**。采集/粗筛交给脚本，语义去重/精选/点评交给 LLM。
- 已推送清单 `pushed_titles.json`（项目根）跨会话防重复：脚本粗筛时排除，LLM 推送后追加。🔴 **排除必须 URL 比对**（`load_pushed_urls`）：LLM 记的是"合并后事件标题"，候选是原始标题，两者 norm 永远不相等 → 只做标题比对=排除失效=重复推。pushed 条目结构 `{title, norm, pushed_at, url}`，排除逻辑 `normalize(title)∉pushed_norms AND url∉pushed_urls`（详见 trendradar skill"精选管线"章）

## 关键路径
- 项目：`D:\Workspace\Projects\TrendRadar`（clone 自 Cyrus1993729/trendradar，**git remote 已删**，防误推）
- 密钥：`run_secrets.bat`（环境变量注入 TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID/AI_API_KEY），config.yaml 零明文
- 运行：`uv run python -m trendradar`（每次执行完整流程后退出，无常驻）；诊断：`--doctor` / `--show-schedule` / `--test-notification`
- 计划任务：TrendRadarHourly（每小时采集）+ TrendRadarStartup（登录自启）
- 看门狗：Hermes cron `*/30 * * * *` 跑 `watchdog_trendradar.py`（检查 output/logs/run.log 新鲜度，4h 阈值；自动拉起；**仅在拉起失败时告警**；LOG 不存在时静默）
- 🔴 **Hermes cronjob 的 schedule 坑**：传 `'30m'` 会被解析成"30 分钟后跑一次"（one-shot, repeat=once）而非循环——循环必须传 cron 表达式（`*/30 * * * *`）且 repeat 仍显示 once 时要再 update 一次 `repeat=0` 才变 forever
- 备份：Hermes cron 每周一 `cleanup_backup_trendradar.py`（90 天清理 + 打包到 D:\Workspace\Backups\TrendRadar）
- 手册：桌面《TrendRadar 本地版使用手册.md》

## 纯采集模式
- `config.yaml`：`notification.enabled=false` + `ai_analysis.enabled=false`（日志确认语："通知功能已禁用，将只进行数据抓取"）
- 采集频率不受推送节奏限制：每小时入库数据越全，主编筛选余地越大

## 精选推送管线（prepare_candidates.py，v2 三通道）
- 窗口自动判断：当前 <14 点 → morning（昨天 18:00 → 现在）；≥14 点 → evening（今天 09:00 → 现在）
- 读 `output/news/{昨天}.db` + `{今天}.db`；**库内时间为 HH-MM 格式（日期在文件名）**，必须拼成完整时间 `YYYY-MM-DD HH-MM` 再过滤/排序
- **三通道合并**：A 热榜（白名单过滤 `matches_word_groups` 全量）→ channel=hot；B RSS 跨境源（feed_id ∈ CB_RSS_FEEDS）→ channel=rss；C crossborder JSON → channel=cb；**垂直源（B/C）不过关键词白名单（源级信任），仅过 GLOBAL_FILTER 噪音**；hot 优先去重；`MAX_CANDIDATES=200`
- 归一化去重：小写 + 去空白标点 + 去修饰词（最新/热/爆/突发/快讯/刚刚/重磅/震惊/独家/现场/实录/滚动）+ 排除已推送
- 输出 JSON 候选到 stdout；cron agent 模式用 `script` 参数把 stdout 注入 prompt（data-collection 模式）
- 精选 cron 设计（用户确认第 2 块方案后创建）：早 `10 9 * * *` + 晚 `10 18 * * *`，agent prompt 要求：语义去重 → 按用户领域打分 → 精选 10-20 条 → 分板块简报（每条带"为什么值得看"点评）→ **推送前把标题 append 进 pushed_titles.json**
- 无候选/全重复 → 回复"该时段无新热点"（静默原则，不推空消息）

## 关键词设计（config/frequency_words.txt）
- 文件结构：`[GLOBAL_FILTER]` 排除区 + **`[WORD_GROUPS]` 标记**（漏了它 → 解析 0 组 → 所有标题匹配，静默失效！）+ 组定义
- 语法：普通词 = OR；`/a|b/` 正则；`+词` = 必须词。**组匹配语义（frequency.py）：所有 +词 都要出现 AND 至少一个普通词命中** → 组合锁定必须独立成组（纯 +词 组），不能与普通词混一组
- 组名在 `display_name` 字段，`group_key` 是词拼接（验证脚本断言别查错字段）
- **防串领域三原则**：
  1. 通用词绝不单用（关税/汇率/测评/爆款/商标/知识产权/合规/沃尔玛/亚马逊 会串其他领域）
  2. 组合锁定用独立组（如 `[电商关税]`：`+电商` + `+关税` 两行纯必须词）
  3. 领域专属词放心单用（T86/de minimis/小额豁免/海外仓/FBA/结汇）
- **v1.1 基线（2026-08-07 Opus 审查修订，当前生效版）**：6 领域 13 组 = 美股市场/黄金贵金属/中国科技公司/AI半导体/宏观经济/关税与贸易战 + 跨境电商平台/市场/环节/政策/经营模式 + 亚马逊卖家/沃尔玛电商组合组。全局过滤 17 词。v1.1 关键修订（详见 `references/keywords-v11-opus-review.md`）：
  - 删死规则：`[电商关税]`（被宏观裸"关税"完全覆盖）、`[跨境贸易摩擦]`（`+跨境`+`+贸易摩擦` 同标题双词几乎永不命中）
  - 宏观组 4 裸词（关税/加征关税/贸易摩擦/反倾销）抽成独立 `[关税与贸易战]` 组 + `@6` 限流——防串设计此前自相矛盾（文件头说"不单用"但宏观组裸用）
  - 误伤词正则化：苹果→`/苹果(公司|股价|财报|发布会|市值|供应链)|库克|(?<![a-z])iphone|(?<![a-z])apple(?![a-z])/`（防"山东苹果"）；黄金→`/黄金(?!周|时代|时间|时段|档|联赛|搭档|比例|年龄|地段|水道|海岸|一代|通道|旅游)/`（防"黄金周"）；消费/出口→语境正则；AGI→`(?<![a-z])agi(?![a-z])`（防 magic）；Listing→`(?<![a-z])listing`（防 delisting）；删收盘/盘中/盘前/美债收益率/灵犀/重复 listing
  - TikTok 空格写法永不命中 → `/tiktok\s*(shop|电商|小店|直播|带货|美国站|电商业务)/`；Mercado Libre→`/mercado\s*libre|美客多/`；Coupang→`/coupang|酷澎/`；新增新兴平台正则（ozon/noon/trendyol/wildberries/allegro/wish/etsy）
  - 新增 `[跨境经营模式]`：全托管/半托管/本对本/店群/跟卖/封店/封号/品牌备案/TRO/侵权冻结/黑五/网一/Prime Day/旺季
  - 政策补：小额包裹免税/最低限度豁免/9610/9710/9810/1210/跨境电商综试区/出口退税/原产地规则/转口贸易
  - 中国科技补：字节/淘天/通义/蚂蚁集团/阿里云/荣耀；半导体补：英特尔/博通/ASML/先进封装/EDA
  - @限流：美股@10/宏观@8/关税@6/中国科技@10/AI@10（宽泛组防刷屏）
  - 全局过滤：`出轨`→`明星出轨`（防列车出轨误杀）、删`离婚`（防财经天价离婚误杀）、补星座/彩票/双色球/菜谱/养生
- 🔴 **解析器陷阱（frequency.py 实测，Opus 审查确认）**：
  1. `!` 过滤词**全局生效**（filter_words 是唯一扁平列表，遍历词组前统一检查）——文档说"仅限当前词组"与实现不符，排除方案一律用正则负向断言，别用 `!`
  2. `\b` 对中文无效（中文属 `\w`）——英文词边界用 `(?<![a-z])xxx(?![a-z])`（官方模板 `\bDeepSeek\b` 也会漏匹配中文环境，如"字节的tiktok业务"）
  3. `[WORD_GROUPS]` 标记粘性：误删后整库关键词变全局过滤词 → 静默 0 推送，文件内已加保护注释
  4. 纯 +词 组合组（如 `+电商`+`+关税`）命中率极低——真实标题通常不字面含两个词；组合锁定要配语境词正则兜底，或改用独立限流组

## 进榜门槛（newsnow 服务端定，非项目代码）
TrendRadar 自身无数量门槛（fetcher 全收，仅域名安全检查 `expected_domain`）；真正的门槛在 newsnow 聚合服务：**每平台固定 20-30 条**（实测微博/头条/贴吧/抖音 30、知乎 20）→ 11 平台 ≈ 255 条/次（这就是每次抓取都是 ~255 的原因）。想扩量只能加平台/自建 newsnow（api_url）/加 RSS。

## 漏斗数量级基线（实测）
一次抓取 ~255 条 → 白名单命中 ~38-42 条（15-16%）→ 归一化去重 ~37-41 条。统计方法：取 `MAX(last_crawl_time)` 批次作为"一次全量抓取"（`stats_funnel.py`）。
- 🔴 **白名单过滤必须在截断（MAX_CANDIDATES=80）之前**：先截断后过滤会丢命中——窗口全量 376 条里白名单命中 57，截断后只剩 23（丢 34 条）。曾因此误判"跨境电商低频"（实为截断丢失），用户纠正后全量验证才看清。prepare_candidates 正确顺序：读库 → 窗口过滤 → 白名单 → 去重 → 截断。
- **分领域分布参考**（v1.1，单次抓取）：中国科技 ~19-22 / 美股 ~10-11 / AI ~8 / 黄金 ~4 / 宏观 ~1-7（v1.1 收紧后 ~1）/ 关税组 ~4
- **跨境电商客观低频**：热榜是大众热点、跨境是垂直行业——连续多批抓取 0 条属正常，推送机制须接受板块缺席（出现即大事件概率高，精选时优先保留）
- **采集全量、筛选实时**：关键词不参与采集（采集不分词全量入库），改关键词对历史已抓数据立即生效——不存在"按旧关键词抓的池子"

## 跨境电商垂直数据源方案（第 1/2 档已落地，2026-08-07）
核心事实：**热榜通道跨境 0 条是结构性**（垂直行业难上大众热榜），继续调关键词是沉没成本；v1.1 跨境词降级为"大事件哨兵"，日常供给靠垂直源。关键决策：
- 🔴 **垂直源不过关键词白名单（源级信任）**——垂直源本身 100% 跨境内容，过白名单只误杀（如"日本 JCT 申报"零词命中）。双通道共池：热榜通道走白名单（现状），垂直通道独立表（cb_items：url UNIQUE + simhash + source_tier + cluster_id + alert_level），统一候选池
- 🔴 **中文跨境媒体原生 RSS 大面积已失效**（雨果跨境/AMZ123 关停）——中文通道靠公众号转 RSS（¥100-200/年，唯一建议花钱处）或 RSSHub 自建
- **高价值源**：Federal Register API（零维护、比媒体早 12-48h，ROI 最高）、CBP CSMS govdelivery RSS、Google News RSS 关键词查询（限频 60min、走代理防 429）、Reddit r/FulfillmentByAmazon top/day（平台突发政策最早信号）、Marketplace Pulse/Modern Retail/Rest of World/Tamebay
- **三级告警**：L1 政府源即时推（<15min、日配额 ≤3、静默 23:00-07:00）/ L2 交叉确认（60min ≥2 独立源）/ L3 日汇总
- **运维**：fail_streak≥3 + items_7d==0（空 feed 静默失效）+ 采纳率连续 4 周 <2% 自动停源——没有它 RSS 聚合 3 个月内烂掉
- 月成本 ~¥10-45；路线：第 1 周 8 免费源（半天零成本，跨境 0→30+ 条/天）→ 第 1 月中文通道+监测 → 长期情报系统
- 落地注意：**不要**把垂直源塞进 TrendRadar 的 `rss` 段（共用筛选逻辑会被白名单误杀）——独立 `crossborder_fetcher.py` 平级于 prepare_candidates.py
- ✅ **已落地（2026-08-07）**：第 1 档 5 个 RSS 源入 `config.yaml rss.feeds`（modern-retail/tamebay/retail-dive/ustr 启用 + 雨果跨境禁用——`/rss` 实测返回 HTML 非 XML，坐实中文 RSS 废弃）；第 2 档 `crossborder_fetcher.py` 跑通（Federal Register API 2 query + Rest of World + Reddit + Google News 4 query 错峰 10s，单次 ~90 条，`crossborder_fetch.bat` + 计划任务 `TrendRadarCrossborder /SC HOURLY`）；`prepare_candidates.py` 升级**三通道**（hot 白名单 + rss/cb 源级信任仅过全局噪音过滤，MAX_CANDIDATES=200），合并后 ~200 候选
- 🔴 **实测坑**：① Federal Register `conditions[term]` 全文搜索噪音大（de minimis 命中航空管制修正案）→ 源头 `FEDREG_FILTER` 宽松正则过滤；② 候选截断顺序——MAX 过小会把 cb 通道截掉（120 时 cb 99 条只进 18），全量 ~200 条直接不截断；③ 源连通性必须实测分档（直连/代理/失效），"半天零成本"是乐观估计——实际 5 源纯配置 + 4 源写代码 + 3 源排障
- 全量细节（源连通性实测表/落地实现/遗留事项）：`references/crossborder-implementation-2026-08.md`

## 双日报管线实现（2026-08-07 定稿）
- **`prepare_candidates.py` 三种模式**：`--crossborder-only`（跨境：三通道+热榜跨境组过滤，24h 窗口）/ `--hot-only`（5 类：**只走热榜白名单通道**，跳过 rss/cb 垂直源，24h 窗口）/ 默认 auto（三通道，早晚窗口）。`--pushed-file <path>` 指定防重复文件（5 类用 `pushed_five.json` 隔离）。两参数互斥
- **`fetch_summaries.py` 泛化**：`--input/--output` 处理任意候选 JSON（兼容 `{"items":[...]}` 与 `{"candidates":[...]}` 两种结构）——跨境 cron 用它补 cb JSON，5 类 cron 用它补热榜候选。**热榜正文抓取质量差**（百度安全验证页/抖音等 SPA/微博反爬）：62 条候选实测仅 15-43 条能抓到干净摘要——但**热榜标题本身是中文且常含数字**（信息密度高），抓不到摘要给标题+链接即可接受，不必强求
- **正文提取四道防护**（extract_text）：① `<article>` 优先（无则全 `<p>`，剔导航）② 编码修正：中文站 GBK/GB2312——requests 默认可能误判（曾现华尔街见闻乱码 `åå°è¡è§é»`），用 headers charset/apparent_encoding 修正 ③ JS/SPA 特征拒收（`$jsvmprt|window\.|var glb|WIZ_global_data`）④ 反爬/超短拒收（"百度安全验证"/"网络不给力"/<20 字符）
- **canonical 回归验证**：`verify_crossborder_pipeline.py`（26 项：语法/提取/垃圾拒收/hot-only/crossborder 回归/pushed_five 隔离/摘要覆盖）——改管线必跑。🔴 **验证状态机自激循环的解法**：Hermes 把 Temp 下 `hermes-verify-*.py` 的创建/删除计入 changed paths → 每次"写验证脚本→验证→删除"都触发新一轮验证要求，无限循环。**解法：验证逻辑固化为项目内持久脚本**（gitignore 覆盖），不再用一次性 Temp 脚本
- **跨境知识库存档**（用户要求"每次日报都要存档"）：`archives/crossborder/YYYY-MM-DD.md`（人读完整日报）+ `YYYY-MM-DD.json`（机读：`{date, pushed_at, mode, news_count, analysis, news:[{section,title,source,url,summary}]}`）+ `index.json`（archives 数组索引）。cron prompt 第 5.5 步硬性步骤：推送前 write_file 三写存档（md/json/index），同日不重复追加。**补档方法**：cron 实际推送内容可从 session_search 查 cron 会话（`session_id = cron_<jobid>_<日期>_<时间>`）拿最终输出重建

## Pitfalls（实测踩坑）
1. **PYTHONPATH 污染（Hermes 环境）**：Hermes 注入 `PYTHONPATH` 指向自己的 venv → TrendRadar 的 litellm 导入 Hermes 的 pydantic → `ModuleNotFoundError: pydantic_core._pydantic_core`。解法：运行前 `unset PYTHONPATH VIRTUAL_ENV`，启动脚本 bat 里 `set PYTHONPATH=`。任何在本机跑第三方 Python 项目都会遇到。
2. **AI 分析"返回空响应"**：deepseek-v4-flash 是推理模型，分析全量新闻（255 条）>120s 超时 → `ai.timeout: 300` + `num_retries: 2`。
3. **newsnow API 403**：默认 curl UA 被 Cloudflare 拦；**带浏览器 UA 直连 200，走代理反而 403**（国内直连即可）。项目 fetcher 自带 Chrome UA 无此问题。
4. **数据库时间 HH-MM**：跨天窗口过滤必须拼日期，字符串比较 `YYYY-MM-DD HH-MM`。
5. **read_file 误判 binary**：CRLF 文件或含框线字符（═ ─ ═ 等装饰符，如 frequency_words.txt/timeline.yaml）会被 read_file 判为 binary——用 `python -c "open(...).read()"` 或 uv run python 读。
6. **Windows Python 不认 MSYS /tmp**：临时文件用项目目录或 %TEMP%。
7. **杀进程红线**：`taskkill /F /IM python.exe` 会杀死 Hermes 自身，必须 `/PID`。
8. **关键词文件改动后必须验证**：用 `load_frequency_words` + 代表性标题测 `matches_word_groups`（防串用例：亚马逊 AWS 不命中[亚马逊卖家]但命中[AI半导体]）。
9. **Federal Register API 全文搜索噪音**：`conditions[term]` 命中大量无关法规（airspace 修正案等）→ 源头宽松正则过滤（`FEDREG_FILTER`：tariff/duty/trade/import/export/customs/china/de minimis/section 30[12]/antidumping 等），标题不命中即丢弃；剩余贸易救济文档属边缘相关，交 LLM 精选判断。
10. **垂直源截断顺序**：多通道候选合并时，MAX_CANDIDATES 过小会把排最后的通道（cb）截掉（120 时 99 条只进 18）——全量候选才 ~200 条，直接放宽不截断（LLM 输入 ~6K 字符成本仍低）。
11. **TrendRadar 不支持按源代理**：全局代理会让 newsnow 直连源挂（newsnow 走代理实测 403）→ 代理源（Google News/Reddit/Rest of World）必须走独立 fetcher 按请求带 proxy。
12. **中文媒体原生 RSS 大面积废弃**：雨果跨境 `/rss` 返回 HTML 订阅页（HTTP 200 但 content-type text/html）——不能只看状态码，要验证响应是 XML；中文通道靠公众号转 RSS。
13. **Google News RSS 限频**：多 query 必须错峰（间隔 ~10s），同 IP 高频会被 429；全部走代理。
14. **cron 排查：`last_run_at: null` ≠ 没触发**：cronjob list 的 last_run_at 要等任务**结束后**才写入——运行中显示 null（next_run 已跳下一天属正常排程）。排查先看 `~/AppData/Local/hermes/logs/agent.log` 里 `cron.scheduler: Job 'xxx'` 与 `session=cron_<jobid>_...` 的 API call/工具调用记录，确认是否在跑。DeepSeek 下午高峰期单次 API 可慢至 180s（正常 8-30s），一次日报 cron 从 5-8 分钟拖到 18 分钟属正常波动
15. **AI 分析硬规则（用户纠正，第一优先级）**：**禁止任何"把读者推回原文"的空话**——"原文未说明/详见原文/原文给出应对策略/值得关注/有待观察/建议跟进"一律删除。候选摘要缺失或单薄时，用行业背景知识补"这是什么/影响谁/怎么办"（标注"背景："前缀），不得编造新闻中未出现的具体数字（可以说"成本上升、模式要变"这类确定性影响，不能编"8月29日生效"这种细节）。用户原话："这种话无法让我获取信息"
16. 🔴 **计划任务 bat 编码坑（2026-08-08 实踩，停摆 24h）**：`start_trendradar.bat`/`crossborder_fetch.bat` 是 **UTF-8 无 BOM + 中文 REM 注释** → cmd 按 GBK 解析乱码 → 报 `'ndRadar' 不是内部或外部命令`（乱码吞掉 "Trend" 前缀）→ bat 在 mkdir/抓取前中断。后果：**计划任务每小时跑但每次都失败（schtasks 上次结果=1），任务仍显示"就绪"** → 数据静默停摆。症状：日报"无新动态"但漏斗尾部是"唯一候选=已推送重复"；`output/news/` 无今日 db。定位法：bash 手动 `unset PYTHONPATH VIRTUAL_ENV && uv run python crossborder_fetcher.py` **成功** + cmd 复现 bat **失败** → 锁定 bat 层。修复：bat 全英文（中文注释删净）。**任何新建 bat 必须全英文**。
   - 🔴 **第二层坑（同次实踩）**：`crossborder_fetch.bat` 原版**缺 `mkdir output\logs`**——`uv run python ... >> output\logs\crossborder.log 2>&1` 重定向目标目录不存在 → cmd 报 **`The system cannot find the path specified`**（英文错误，区别于编码坑的 `'ndRadar' 不是命令`）。编码坑修好后这个坑才暴露。**凡 bat 里 `>> output\logs\xxx.log` 重定向，必须先 `if not exist "output\logs" mkdir "output\logs"`**（start_trendradar.bat 有、crossborder_fetch.bat 没有——两个都要检查）。
17. 🔴 **看门狗盲区：run.log 不存在时静默（已修复 2026-08-08）**：原逻辑 `if not os.path.exists(LOG): return` 把"日志从未生成"当"部署初期"——bat 编码挂掉时 run.log 永远不存在 → 看门狗每 30 分钟静默退出 → 24h 无人发现（2026-08-08 实踩）。若用户报"日报没内容"，不能信看门狗"ok"，直接查数据时间戳。**修复后逻辑**：run.log 不存在 → 无 FLAG 则 `_trigger()` 重启一次 + 输出"已自动触发一次重启"；已有 FLAG（上次触发过仍无日志）→ 输出 🚨 告警（含"检查 bat 是否 ASCII-only/计划任务是否禁用"提示）。行为验证 4 场景：无日志无标记→触发+建标记 / 无日志有标记→告警不重复触发 / 日志新鲜→静默 / 日志陈旧→触发（ad-hoc 脚本 monkeypatch 路径+Popen 验证，PASS）。

## 日报无内容/未触发排查 SOP（2026-08-08 实踩定型）
用户报"日报没推送/没触发"时，**大概率是"触发了但候选为空"**，按序排查（每步都有本次实测依据）：
1. `cronjob list` 看任务 `last_run_at`（今天有值 = 触发过）→ 读 `~/AppData/Local/hermes/cron/output/<jobid>/` 最新 `*.md` 看 Response——cron 输出文件是真相源，别猜
2. 看候选漏斗 stats（hot_raw→whitelist→dedup→after_pushed）：**尾部若是"唯一候选=已推送事件的重复"→ 是采集停摆不是真无新闻**（真无新闻=漏斗源头就空）
3. 确认采集停摆：`ls output/news/` ——今天无 `YYYY-MM-DD.db` = 热榜采集已停；`output/crossborder/` 时间戳查跨境通道
4. 查计划任务真实状态：`MSYS_NO_PATHCONV=1 schtasks /query /tn TrendRadarHourly /v /fo LIST | iconv -f GBK -t UTF-8`（git-bash 必须 MSYS_NO_PATHCONV=1 防路径转换，输出 GBK 要 iconv）——**"上次结果=1"= 任务被调用但 bat 失败**（任务仍显示"就绪"，不能只看状态）
5. 分层复现定位：bash 手动 `unset PYTHONPATH VIRTUAL_ENV && uv run python crossborder_fetcher.py` 成功（脚本无问题）+ `MSYS_NO_PATHCONV=1 cmd /c "D:\Workspace\Projects\TrendRadar\crossborder_fetch.bat"` 报错（如 `'ndRadar' 不是命令`）→ **锁定 bat 层**（编码坑，见 Pitfall 16）
6. 修复后**自动化验证**（用户偏好：全自动，不要让他手动操作/验证）：`MSYS_NO_PATHCONV=1 schtasks /run /tn TrendRadarCrossborder`（和 TrendRadarHourly）直接触发计划任务——**等价生产环境**（绕开 bash→cmd 的路径转换问题，比 cmd /c 复现更真实）→ sleep 后检查 `output/logs/crossborder.log` 非空 + `output/news/YYYY-MM-DD.db` 生成 + 漏斗有候选。**不要**用 `--pushed-file` 补推旧数据（会污染防重复记录）；数据恢复后可用 `cronjob run <jobid>` 补推当天错过的日报（候选非空时）
   - 注意：`cmd /c "D:\...\xxx.bat"` 从 bash 调 bat 常报 `The system cannot find the path specified`（重定向目录不存在）或路径转换问题——**验证一律用 schtasks /run**，不要用 cmd /c 复现（其报错与生产环境可能不同，会误导诊断）

## 投递环节故障（日报生成成功但用户没收到）—— 2026-08-08 实踩
症状：cron 输出文件里有**完整日报**、`last_status=ok`、`last_delivery_error=null`，但用户没收到任何消息。与"采集停摆"的区别：候选漏斗正常（几十条）、`archives/crossborder/` 有当日存档。
根因链：
1. **Telegram 网络故障窗口**（代理 7897 到 api.telegram.org 的 `httpx.ConnectError` / `httpx.RemoteProtocolError: Server disconnected`，gateway.log WARNING `[Telegram] Telegram network error (attempt N/10), reconnecting`）撞上投递时刻
2. **cron 投递走 cron.scheduler 模块，成功不记日志**——gateway.log 里只有主会话（agent:main:telegram:dm:xxx）的 response ready；cron 投递痕迹只在 gateway-stdio.log（`grep cron.scheduler`），且只有失败/回退才记 WARNING/ERROR（如 `live adapter delivery to weixin... failed, falling back to standalone`）
3. **assume-delivered 分支（scheduler.py 防重复设计）**：live adapter send 超时且 coroutine 已在途（`future.cancel()==False`）→ 视为已投递、跳过 standalone 重发。连接故障时消息既没送达又被记成功 → **静默丢失**（last_status=ok + last_delivery_error=null 但用户没收到）
排查要点：
- **别信 last_status/last_delivery_error**——投递失败可能是静默的
- `grep "2026-08-08 1[45]:" gateway.log | grep -i telegram` 看投递时刻前后有无 TG 网络错误（如 15:51 的 ConnectError 就是 16:00 日报的预警）
- 对比"cron 输出文件有内容" vs "gateway 无投递记录"即锁定投递环节
补投递（**不重跑 cron**——重跑走 20 分钟全流程且可能重复推）：
- 跨境日报已存档：读 `archives/crossborder/YYYY-MM-DD.md` 全文，按 4096 字符/条分 3-4 段直接补发（标注"补发 1/N"）
- 5 类日报无存档：从 `~/AppData/Local/hermes/cron/output/<jobid>/YYYY-MM-DD_HH-MM-SS.md` 的 `## Response` 段提取日报全文补发
- 补充：cron 输出文件 Response 若是"验证总结"而非日报本体（agent 声称"已在上面分 N 段交付"）——说明日报在 agent 中间输出里，投递的只是最终响应；用户视角=没收到日报

## Opus 关键词审查工作流（可复用）
配置文件/关键词库要外部模型审查时：
1. python 脚本组装 prompt：**内联三份材料**——①待审文件全文 ②官方模板/规范全文（`git show HEAD:config/frequency_words.txt` 可取被覆盖前的原始版）③解析器源码（`frequency.py` 全文，让审查者对照真实实现而非文档）
2. `claude -p --model opus --max-turns 8 --disallowedTools Read Write Edit Bash Glob Grep WebFetch WebSearch TodoWrite < prompt.txt`（走 7897 代理）＋ **prompt 开头加横幅**：「不要调用任何工具/读取文件，所有材料已内联，仅基于材料直接回答」
   🔴 **调用姿势（2026-08-08 实测踩坑）**：`--disallowedTools` 必须**空格分隔不带引号**，prompt 必须 **stdin 重定向 `< file`**。`-p "$(cat prompt.txt)"` + 引号版 disallowedTools（`--disallowedTools "Read Write Bash"`）会把 prompt 全文当成 permission rules 解析 → `Permission deny rule "..." matches no known tool` 报错崩溃。逗号分隔（`"Read,Write,Bash"`）同样崩（memory 已记）。
   🔴 **`--tools ""` 禁不住工具（实测踩坑）**：工具未被真正禁用时，Opus 会尝试"读文件"并**幻觉输出一个编造的文件内容**（路径/内容与真实代码完全不符），且不回答问题——输出必须核对是否真的回答了问题
3. 审查报告按 P0（必改）/P1（强烈建议）/P2（可选）分级输出
4. 用户拍板后逐项落地，再用 `load_frequency_words` + 代表性标题行为测试验证（防串用例：苹果/黄金周/magic/delisting/列车出轨/TikTok 写法）
- 教训：Opus 能发现文档与实现不符的坑（`!` 全局生效、`\b` 中文失效、死规则、自相矛盾的防串设计）——关键词库改版前值得先过一轮

## 用户偏好（本任务类）
- 监控系统：事件驱动、平时静默；异常才告警；无新增不推空消息
- 推送节奏（2026-08-07 定稿，**双日报**）：
  - **跨境日报 16:00**（cron `TrendRadar跨境日报` f4506e87cc69）：`prepare_candidates.py --crossborder-only`（24h 窗口、三通道、去重后全推、独立消息）。顶部 Opus 设计的**模块化 AI 分析**（⚡今日速览 / 🏛政策风向 / 🛒平台规则 / 📈市场与成本 / 🧰实战参考 / 📖小白词典 / ✅今天该做的一件事，900-1200 字，小白教学风）+ 新闻清单（中文标题 + 2-3 句带数字摘要 + 链接；英文源「中文译名（English original title）」+🔤 标记）
  - **5 类日报 9:30**（cron `TrendRadar五类日报` 970113abe8a7）：`prepare_candidates.py --hot-only --pushed-file pushed_five.json`（**纯热榜白名单**通道、24h 窗口、去重后全推）。**投资视角分析**（⚡速览 / 🇺🇸美股与纳指 / 🥇黄金 / 🇨🇳中国科技 / 🤖AI半导体 / 🌐宏观与政策 / 📌对投资的提示，700-1000 字，**不喊单不给买卖建议**，非小白教学）+ 新闻清单（5 板块）
  - 两日报**独立防重复文件**（pushed_titles.json / pushed_five.json），互不干扰；用户原话："早上9.30推送一次吧 一天只推送这一次"
  - 旧方案"每天 2 次（09:10/18:10）+ 精选 10-20 条"已废弃（用户改要 16:00 单窗口 + 全推）
- 关注领域 1.0：6 大领域，跨境电商按"市场×平台×环节×政策"四维设计
- 版本基线意识：关键词库有版本号（v1.0），改动需用户确认
- 改配置/改代码前必须征得同意（红线）；部署前先核实仓库身份与内容（用户曾纠正"这是刚 fork 的空仓库"）
- **用户要求"看某个文件"时给全文**：贴完整内容（代码块）或 MEDIA 发文件，结构导读/摘要表不够（用户曾明确"我要看完整的关键词库"）
- **卡在决策点时主动说明**：用户问"没进展了？"= 在等我拍板。停在等待点时要明说"卡在需要你确认的 X"，并给出可点的选项（clarify），不要让用户猜
- **双方案对比偏好**：用户会要求"你先给方案，再把需求发 Opus 独立出一份方案"来对比。两版都要给，且用实测数据诚实指出对方方案的乐观/错误处（如 Opus"8 源半天零成本"被连通性实测推翻为 5+4+3 三档工作量）——用户重视交叉验证，不盲信单一来源
- **交付只发成品**（用户原话："只发完整的跨境日报，别的多余的话不要发"）：日报类推送的最终回复=日报本体，不加解释/总结/前后缀；实现/排障说明在日报之外另行简短汇报
- **分析风格按受众区分**（用户明确区分两类）：跨境日报=小白教学风（读者未入场，通俗、术语即解释、给行动）；5 类日报=投资视角（读者是纳指定投+黄金积存的投资者，划重点不教学，**不喊单不给买卖建议**）。两者不得混用
- **分析迭代流程**（用户需求→Opus 设计→确认→落地）：用户对分析板块的格式需求（分模块/信息密度/中文化）先发给 Opus 出设计稿（prompt 附用户原话+现有日报结构+画像），用户确认后再固化进 cron prompt——设计类问题不自己拍板

## See Also
- `references/frequency-syntax.md` — 关键词语法与防串领域设计详例
- `references/database-format.md` — TrendRadar SQLite 库结构、时间格式、增量模式局限
- `references/funnel-baseline.md` — 漏斗统计方法与数量级基线
- `references/keywords-v11-opus-review.md` — 关键词 v1.1 全量修订明细 + Opus 审查发现 + 行为测试用例集
- `references/crossborder-sourcing-plan.md` — 跨境电商垂直数据源方案（Opus 出品：源清单/双通道架构/三级告警/运维/路线图）
- `references/daily-report-cron-spec-2026-08.md` — 双日报 cron prompt 规范精炼版（跨境 16:00 + 5 类 9:30 的完整步骤/模块结构/硬规则/存档格式）——改日报格式以此为准并同步更新
