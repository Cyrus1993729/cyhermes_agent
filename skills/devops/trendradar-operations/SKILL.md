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

## 投递前自动审查（2026-08-11 上线，日报 cron 第 4.5 步）
所有日报发出前必须过一轮轻量质检（用户拍板：不走完整 5 步流程，日报高频）。脚本：`~/AppData/Local/hermes/scripts/daily_report_review.py`：
- **L0 硬规则**（本地正则零成本）：禁止词/喊单词/链接缺失/背景行标记/模块完整性
- **L1 模型审查**：默认 **GPT-5.6（Codex CLI）** 单模型（用户定调，qwen 暂不参与）；`--model gpt|qwen|both` 可切换，`both` 恢复双模型互补
- **L2 用户兜底**：日报保留来源标注，"背景："内容删或明示
- cron prompt 集成：草稿落盘 `output/_draft_five.txt`/`_draft_cb.txt` → 跑脚本 → hard findings 自动修复（≤1 轮不重审：删条/删背景行/改写）→ 投递；审查异常 → 降级照发 + 末尾标注"⚠️ 今日未经模型审查"
- 跨境日报第 1 步已改为 `prepare_candidates.py --crossborder-only > output/candidates_cb.json`（候选落盘供审查比对）
- 设计/调用姿势/验证方法/坑：`references/daily-report-review-2026-08.md`

## DeepSeek 过载避峰 + 引擎切换（2026-08-12 用户定调：避峰优先、切换兜底）
用户拍板原则：**qwen API 比 DeepSeek 贵，切换是最后兜底不是默认**——先监测 DeepSeek 延迟的时间段分布、调日报时间避开高峰；调整后仍遇偶发卡顿才切 qwen。
- **延迟时间模式**（2026-08-10/11/12 agent.log latency 521 条实测）：**早高峰 09:00-10:00 最严重**（平均 34-182s、最大 463s、>30s 占比 50-100%）；08:00-08:30 也偏高（平均 138s）；**10:30 后正常**（6-12s）；**下午 16:00-16:30 高峰**（平均 25-53s），16:30 后正常（8-12s）。结论：五类 9:30 档正踩早高峰、跨境 16:00 档踩下午高峰
- ✅ **已执行（2026-08-12 用户拍板）**：五类 9:30→**11:00**、跨境 16:00→**17:00**。用户否决了 8:30 方案（08:00-08:30 实测也偏高、平均 138s——"你都说了8.30也卡"），改选 11:00/17:00（11:00-11:30 平均 9s 0 慢、17:00-17:30 平均 8s 0 慢，均在有数据验证的舒适区）。投递检查 cron 同步：五类 11:45（2026-08-14 从 11:15 调整——原 11:15 与 agent 完成时间竞态连续两天误报，见 Pitfall 19）、跨境 17:45
- 脚本（`~/AppData/Local/hermes/scripts/`）：
  - `api_probe.py` — DeepSeek 真实 chat completion 延迟探测（25s 超时），输出 `OK <秒>`/`SLOW <秒>`/`ERROR <原因>`（阈值 30s：正常 2-15s、过载 60-265s）
  - `report_gen_qwen.py` — qwen3.7-max 日报生成引擎（`--candidates <json> --mode five|cb --out <file>`），编辑规则内嵌（与 cron prompt 第 2/3 步一致），读 config.yaml qwen-bailian key 直连；生成文件为 UTF-8 但含 CRLF，read_file 可能误判 binary，用 python 读
- **cron prompt 集成（✅ 已上线 2026-08-12 晚，两个日报 cron 均更新）**：第 0 步跑 api_probe → SLOW/ERROR 时取候选后跑 report_gen_qwen 生成草稿 → 核对完整性（非空/含速览/含清单）→ 跳过人工编辑从审查步骤继续 → 末尾标注"⚠️ 今日 DeepSeek 过载，日报由 qwen3.7-max 生成"；脚本失败则退回当前模型（慢总比没有强）。🔴 prompt 内脚本路径一律用正斜杠 `C:/Users/...`（agent 生成的 `C:\Users\...` 命令在 bash 下反斜杠会被吞，报 "can't open file 'C:\UsersAdministrator...'"，2026-08-12 实踩，agent 重试才成功）
- 详细延迟数据表/脚本验证（12/12 断言）/调用姿势：`references/deepseek-overload-avoidance-2026-08.md`
- 🔴 **读 cron jobs.json 用字段 `id` 不是 `job_id`**（2026-08-12 实踩 StopIteration）：`~/AppData/Local/hermes/cron/jobs.json` 结构 `{"jobs":[...],"updated_at":...}`，job 对象主键字段名是 `id`（cronjob list API 显示为 job_id）
- ⚠️ **避峰非万能 + 体检单次采样局限（2026-08-12 17:00 首跑实测）**：跨境日报改 17:00 首跑时 DeepSeek 依然 50-120s/次（前一天同段实测 8s——过载形态是**全天波动**而非固定高峰，8/12 全天都慢）；api_probe 启动时探测 1.66s 返回 OK，但后续每次调用 50-120s。**单次采样抓不住波动过载**——体检只能抓住"稳定持续过载"（如 8/12 早上的 60-265s 不回落形态），对"探测瞬间快、随后慢"无效。✅ **二次探测已实施（2026-08-14 用户拍板）**：cron prompt 新增【第 1.6 步二次探测】——取完候选（耗时 1-2 分钟，天然形成间隔）后再跑一次 api_probe.py；判定改"**任一 SLOW/ERROR → qwen 引擎，两次都 OK → deepseek**"。两个日报 cron prompt 均已更新（详见 `references/deepseek-overload-avoidance-2026-08.md`「二次探测」章）。8/14 当天 11:00 五类日报即遇波动过载（API 78-217s、19 分钟才跑完 9 步），正是此设计要抓的形态。结论：时间调整降低慢的概率但不保证；体检是粗筛不是保险。⚠️ 更新 cron prompt 的姿势：替换前用 execute_code 读 jobs.json（字段 `id` 非 `job_id`）验证目标段落唯一且 qwen 分支保留 → cronjob update 传完整新 prompt → 改后读回 jobs.json 验证落盘（断言新段落 in、旧判定 not in）

## Pitfalls（实测踩坑）
1. **PYTHONPATH 污染（Hermes 环境）**：Hermes 注入 `PYTHONPATH` 指向自己的 venv → TrendRadar 的 litellm 导入 Hermes 的 pydantic → `ModuleNotFoundError: pydantic_core._pydantic_core`。解法：运行前 `unset PYTHONPATH VIRTUAL_ENV`，启动脚本 bat 里 `set PYTHONPATH=`。任何在本机跑第三方 Python 项目都会遇到。
2. **AI 分析"返回空响应"**：deepseek-v4-flash 是推理模型，分析全量新闻（255 条）>120s 超时 → `ai.timeout: 300` + `num_retries: 2`。
3. **newsnow API 403**：默认 curl UA 被 Cloudflare 拦；**带浏览器 UA 直连 200，走代理反而 403**（国内直连即可）。项目 fetcher 自带 Chrome UA 无此问题。
4. **数据库时间 HH-MM**：跨天窗口过滤必须拼日期，字符串比较 `YYYY-MM-DD HH-MM`。
5. **read_file 误判 binary**：CRLF 文件或含框线字符（═ ─ ═ 等装饰符，如 frequency_words.txt/timeline.yaml）会被 read_file 判为 binary——用 `python -c "open(...).read()"` 或 uv run python 读。
6. **Windows Python 不认 MSYS /tmp；bash 传参 MSYS 路径被错误转换**：`python "$HOME/scripts/x.py"` 中 `$HOME`（=/c/Users/...）传给 Windows 原生 Python 会变成 `C:\c\Users\...` 报 "can't open file"（2026-08-12 实踩）。**调 Windows 程序一律用原生正斜杠路径 `C:/Users/...`**（bash 不转换），或先 `cd` 到目标目录用相对路径。临时文件用项目目录或 %TEMP%。🔴 **bash 的 `$TEMP` 同样不可直接传 Windows Python**（2026-08-14 实踩：`cat > "$TEMP/verify.py"` 写入成功但 `python "$TEMP/verify.py"` 报 `can't open file 'C:\tmp\verify.py'`——MSYS 把 $TEMP 转换成了 C:\tmp）。**ad-hoc 验证脚本的正确姿势**：`VFILE=$(python -c "import tempfile,os; fd,p=tempfile.mkstemp(suffix='.py',prefix='hermes-verify-xxx-',dir=r'C:/Users/Administrator/AppData/Local/Temp'); os.close(fd); print(p)")` 生成 OS-safe 原生路径 → cat 写入 → python 运行 → rm 清理。
7. **杀进程红线**：`taskkill /F /IM python.exe` 会杀死 Hermes 自身，必须 `/PID`。
8. **关键词文件改动后必须验证**：用 `load_frequency_words` + 代表性标题测 `matches_word_groups`（防串用例：亚马逊 AWS 不命中[亚马逊卖家]但命中[AI半导体]）。
9. **Federal Register API 全文搜索噪音**：`conditions[term]` 命中大量无关法规（airspace 修正案等）→ 源头宽松正则过滤（`FEDREG_FILTER`：tariff/duty/trade/import/export/customs/china/de minimis/section 30[12]/antidumping 等），标题不命中即丢弃；剩余贸易救济文档属边缘相关，交 LLM 精选判断。
10. **垂直源截断顺序**：多通道候选合并时，MAX_CANDIDATES 过小会把排最后的通道（cb）截掉（120 时 99 条只进 18）——全量候选才 ~200 条，直接放宽不截断（LLM 输入 ~6K 字符成本仍低）。
11. **TrendRadar 不支持按源代理**：全局代理会让 newsnow 直连源挂（newsnow 走代理实测 403）→ 代理源（Google News/Reddit/Rest of World）必须走独立 fetcher 按请求带 proxy。
12. **中文媒体原生 RSS 大面积废弃**：雨果跨境 `/rss` 返回 HTML 订阅页（HTTP 200 但 content-type text/html）——不能只看状态码，要验证响应是 XML；中文通道靠公众号转 RSS。
13. **Google News RSS 限频**：多 query 必须错峰（间隔 ~10s），同 IP 高频会被 429；全部走代理。
14. **cron 排查：`last_run_at: null` ≠ 没触发**：cronjob list 的 last_run_at 要等任务**结束后**才写入——运行中显示 null（next_run 已跳下一天属正常排程）。排查先看 `~/AppData/Local/hermes/logs/agent.log` 里 `cron.scheduler: Job 'xxx'` 与 `session=cron_<jobid>_...` 的 API call/工具调用记录，确认是否在跑。DeepSeek 下午高峰期单次 API 可慢至 180s（正常 8-30s），一次日报 cron 从 5-8 分钟拖到 18 分钟属正常波动
   - 🔴 **严重过载案例（2026-08-10 实踩）**：DeepSeek 服务端过载时 latency 可达 **91-463s/请求**（agent.log API call latency 字段），五类日报 9:30 触发 45+ 分钟仍未完成（16 次调用），黄金周报 8:00 触发跑 70 分钟/37 次调用后 **`Session DB append_message failed: 'NoneType' object has no attribute 'execute'` → `Turn ended: reason=interrupted_during_api_call`** 被中断、无产出。区分"网络问题 vs 服务端过载"：curl 网络层快（连接 0.1s）+ 真实 chat completion 生成慢 = 服务端过载（fallback 不触发，见 hermes-china-providers）。慢响应会压垮长跑任务（DB 连接在长时间运行后失效）——**关键 cron 任务应独立指定备用模型**，不依赖主模型状态。⚠️ 方法（2026-08-10 实测）：cronjob 工具**不暴露** model/provider 参数（`cronjob update ... model=...` 报 `No updates provided`）——正确做法是 config.yaml `cron:` 段加 `model: qwen3.7-max` + `model_provider: qwen-bailian`（cron-fleet 默认，scheduler 每次运行重读 config.yaml → 改完立即生效；用 `hermes config set cron.model ...` 修改）。详见 hermes-china-providers「Cron-Fleet 模型覆盖」
15. **AI 分析硬规则（用户纠正，第一优先级）**：**禁止任何"把读者推回原文"的空话**——"原文未说明/详见原文/原文给出应对策略/值得关注/有待观察/建议跟进"一律删除。候选摘要缺失或单薄时，用行业背景知识补"这是什么/影响谁/怎么办"（标注"背景："前缀），不得编造新闻中未出现的具体数字（可以说"成本上升、模式要变"这类确定性影响，不能编"8月29日生效"这种细节）。用户原话："这种话无法让我获取信息"
16. 🔴 **计划任务 bat 编码坑（2026-08-08 实踩，停摆 24h）**：`start_trendradar.bat`/`crossborder_fetch.bat` 是 **UTF-8 无 BOM + 中文 REM 注释** → cmd 按 GBK 解析乱码 → 报 `'ndRadar' 不是内部或外部命令`（乱码吞掉 "Trend" 前缀）→ bat 在 mkdir/抓取前中断。后果：**计划任务每小时跑但每次都失败（schtasks 上次结果=1），任务仍显示"就绪"** → 数据静默停摆。症状：日报"无新动态"但漏斗尾部是"唯一候选=已推送重复"；`output/news/` 无今日 db。定位法：bash 手动 `unset PYTHONPATH VIRTUAL_ENV && uv run python crossborder_fetcher.py` **成功** + cmd 复现 bat **失败** → 锁定 bat 层。修复：bat 全英文（中文注释删净）。**任何新建 bat 必须全英文**。
   - 🔴 **第二层坑（同次实踩）**：`crossborder_fetch.bat` 原版**缺 `mkdir output\logs`**——`uv run python ... >> output\logs\crossborder.log 2>&1` 重定向目标目录不存在 → cmd 报 **`The system cannot find the path specified`**（英文错误，区别于编码坑的 `'ndRadar' 不是命令`）。编码坑修好后这个坑才暴露。**凡 bat 里 `>> output\logs\xxx.log` 重定向，必须先 `if not exist "output\logs" mkdir "output\logs"`**（start_trendradar.bat 有、crossborder_fetch.bat 没有——两个都要检查）。
17. 🔴 **看门狗盲区：run.log 不存在时静默（已修复 2026-08-08）**：原逻辑 `if not os.path.exists(LOG): return` 把"日志从未生成"当"部署初期"——bat 编码挂掉时 run.log 永远不存在 → 看门狗每 30 分钟静默退出 → 24h 无人发现（2026-08-08 实踩）。若用户报"日报没内容"，不能信看门狗"ok"，直接查数据时间戳。**修复后逻辑**：run.log 不存在 → 无 FLAG 则 `_trigger()` 重启一次 + 输出"已自动触发一次重启"；已有 FLAG（上次触发过仍无日志）→ 输出 🚨 告警（含"检查 bat 是否 ASCII-only/计划任务是否禁用"提示）。行为验证 4 场景：无日志无标记→触发+建标记 / 无日志有标记→告警不重复触发 / 日志新鲜→静默 / 日志陈旧→触发（ad-hoc 脚本 monkeypatch 路径+Popen 验证，PASS）。

18. 🔴 **日报 prompt"背景补全"规则=幻觉窗口（2026-08-11 实踩）**：5 类日报 cron prompt 第 3 步硬性规则 3"候选摘要缺失时用背景知识补'这是什么'，标注'背景：'前缀"——候选只有标题无摘要（热榜常态）时，**该规则强制模型凭参数化记忆做事实性断言** → qwen3.7-max 在"DeepSeek重启融资"（B站热搜仅标题）补出"DeepSeek是字节旗下大模型团队"（实为幻方量化旗下，梁文锋创立）。**事实性背景（公司归属/人事/历史沿革）标题与摘要未提供时禁止凭记忆填充**；背景补充只允许确定无疑的常识。诱因链：8/10 API 过载切 cron 到 qwen3.7-max → 换模型引入知识偏差（deepseek 写自身归属正确，qwen 踩"DeepSeek×字节"共现混淆）→ 8/11 首跑即错。8/11 已切回 deepseek-v4-flash（用户定调：qwen 仅 DeepSeek 拥堵且短期无法恢复时应急，见 hermes-china-providers「cron 模型选择策略」）。**内容管线换模型后首轮输出必须盯事实性断言质量**。防御已落地：cron prompt 背景行规则收紧 + 投递前自动审查（见「投递前自动审查」章节）。

19. 🔴 **投递健康检查与 agent 完成时间竞态（2026-08-13/14 实踩，连续两天误报）**：五类日报 11:00 触发后，agent 要 5-18 分钟才写完 cron 输出文件（DeepSeek 过载日单次 API 78-217s，8/14 触发 19 分钟还在 API call #5）——投递检查 11:15 跑时输出文件**必然还不存在** → 连续两天告警"今天 9:30 无输出文件"（8/13 日报 11:16:45 才写完 vs 检查 11:15:44 只差 1 分钟；8/14 检查时 agent 仍在生成中，纯误报）。**健康检查时间必须 = 触发时间 + 最坏 agent 完成时长（正常 18min、过载日更久），不能只 +15min**。✅ **已落地（2026-08-14 用户确认）**：五类投递检查 11:15→11:45；`healthcheck_daily.py` 告警文案/注释全部去时段化（"今天无输出文件"）+ TG 断连窗口正则同步（五类 11:05-11:49、跨境 16:55-17:49）；18 断言 ad-hoc 验证 PASS（旧时间零残留/新正则到位/真实运行 --five 输出无旧字样）。
   - **连带坑：改 cron 触发时间必须同步清下游脚本的硬编码时间**——8/12 五类 9:30→11:00 只改了 schedule，healthcheck_daily.py 文案/注释仍是"9:30 cron"/"TG 断连检查（五类窗口 9:25-10:00）"，8/14 告警消息仍写"今天 9:30 无输出文件"（用户看到直接问"为什么还写的9.30"）。**告警文案禁止硬编码具体时间**（写"今天无输出文件"即可，时间写死必过期）；改任何调度时间后，grep 项目内旧时间字面量（`9:30|16:00|11:15`）逐个清。

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
- **TG 间歇故障的深层根因定位（2026-08-09 实踩）**：TG 流量走 Clash Verge（7897）**固定单一节点**——sidecar 日志 `AppData/Roaming/io.github.clash-verge-rev.clash-verge-rev/logs/sidecar/sidecar_latest.log` 每行可见 `[TCP] ... api.telegram.org:443 match DomainSuffix(telegram.org) using mm[美国1130-KING]`（节点名固定）。节点抖动特征：每 2-4 小时故障几秒-十几秒（RemoteProtocolError 后接 ConnectError），**当前时刻测试往往正常**（20 次连续 curl 全通也排除不了间歇故障）。修复方向（2026-08-09 用户拍板，已落地）：
- 🔴 **用户硬性约束：固定单一节点，禁止自动切换**——Claude Code 需稳定 IP，切换会被判定封号。B 方案（Clash 规则自动切换）被用户否决。
- **A 已执行**：用户手动切「美国1130-KING」→「美国111-OVH」（mm 组 select 模式 23 节点含 11 个美国节点；候选优先级 OVH/GCORE/JUST > PRO/GEFENG > 避开 MEL 系（1130 同机房已证抖）与 ipv6 节点）
- **验证节点生效**：① sidecar 日志 `grep "api.telegram.org.*using mm\[" logs/sidecar/sidecar_latest.log`——切换后新连接节点名即更新 ② 连续 15-20 次 `curl -x http://127.0.0.1:7897 api.telegram.org/bot<token>/getMe` 0 失败 ③ gateway.log 断连计数归零（观察期 ≥12h，111-OVH 实测 12h 零断连）
- **换节点时机**：Claude Code 空闲时切（切换瞬间 IP 变化）；**低频切换原则**：固定观察 ≥1 天还抖再换下一个，不频繁切
- **C 已落地（2026-08-10）投递健康检查 cron**：`~/AppData/Local/hermes/scripts/healthcheck_daily.py`（`--five`/`--cb` 两模式）+ 包装脚本 `healthcheck_five.py`/`healthcheck_cb.py`（cron script 参数不带参，用包装注入 argv）+ cron `日报投递检查-五类`(45 11 * * *)/`日报投递检查-跨境`(45 17 * * *) 均 no_agent（stdout 空=静默，非空=告警投递）。检查项：cron 输出/存档存在性+新鲜度、news_count=0、数据源 db 新鲜度（26h）、投递窗口 TG 断连计数。9 场景分支覆盖验证 PASS（正常静默/缺失告警/过旧告警/断连告警/包装参数传递）
- **D 已落地（2026-08-10）API 健康监控 cron**：`~/AppData/Local/hermes/scripts/api_healthcheck.py` + cron `API健康检查-DeepSeek`(*/30 * * * *) no_agent——**真实 chat completion 生成延迟测试**（>30s 或失败才告警；网络层 curl 快 ≠ 服务端正常，必须发真实请求计时）。5 分支验证 PASS（正常静默/慢45s/HTTP500/网络异常/key缺失）。与 C 合并 16 场景验证全绿
- **healthcheck 类脚本的验证姿势**：告警逻辑分支（静默/缺失/过旧/断连）用 mock 文件系统+subprocess 模拟场景断言 stdout（`mock.patch('os.path.exists', side_effect=...)` 注意 `os.path.exists` 要用字符串路径形式 `mock.patch('os.path.exists', ...)` 而非 `mock.patch.object(os.path, 'exists', ...)`（后者报 ntpath 无 listdir）；datetime 用真实时间戳控制新鲜/过旧，不要 mock datetime 类）
- 🔴 **agent 自行分段 = 只发第一段（2026-08-11 实踩，用户只收到 1/3）**：日报完整生成（存档 14.5KB，agent 拆分日志 S1:3736/S2:3689/S3:1321 正常）但用户只收到前 1/3——cron prompt 第 4 步写了"Telegram 消息限制 4096 字符/条：超过时拆成多条消息分段发送，每条消息末尾标注（1/N）"，agent 照做把日报拆 3 段，但 **cron 机制只投递 final response（最后一次文本回复）一条消息**——agent 只输出了第 1 段（3736 字符带"（1/3）"）就 turn ended，第 2/3 段从未发出。排查信号：`agent.log` 的 `Turn ended: reason=text_response ... response_len=3738` 远小于存档大小（14.5KB）+ cron 会话最后一条 assistant 消息带"（1/N）"标记。**修复：cron prompt 严禁指示 agent 自行分段**——第 4/6 步统一改为"最终回复 = 完整日报全文（不自行分段、绝不要只发第一段），系统会自动按 Telegram 限制拆分投递"（8/10 跨境日报 15.5KB 完整送达正是系统层拆条的例证）。两个日报 cron 已改
- 🔴 **同一内容收到两遍（双投递，2026-08-11 实踩）**：症状 = 用户收到完整日报两次。场景是 **DM 会话内手动补发长回复**（非 cron 投递——cron 是独立单通道不受影响）。根因链：
  1. config.yaml `display.platforms.telegram.streaming: true`（Telegram 平台显式开流式）**覆盖**顶层 `streaming.enabled: false` → 回复走 streaming（边生成边发）+ final send（完成后兜底）双通道
  2. 短回复靠 `content_delivered` 去重正常抑制（gateway.log 见 `Suppressing normal final send ... content_delivered=True`，310 字符回复只发一遍）
  3. **>4096 字符触发拆条时去重失效**：`gateway/stream_consumer.py` 的 `delivered_final_matches` 对 `_turn_split_delivery` 直接 `return None` → `gateway/run.py` 25599 行去重判定不成立 → streaming 和 final send 都投递 → 用户收到两遍
  - 排查信号：gateway.log **只有一条** `Sending response (8828 chars)` 但用户收到两遍（拆条 3 条 ×2）；对比同会话短回复日志有 `Suppressing normal final send`
  - 修复：`hermes config set display.platforms.telegram.streaming false`（回复生成完一次性发出，系统自动拆条，无双通道；cron 投递不受影响；微信本来就没开 streaming）。改后需重启 gateway 生效（从 messaging 会话内重启有断连风险，用桌面 bat 或挑空档）
  - 相关文件：`gateway/run.py` ~25555-25607（去重判定）、`gateway/stream_consumer.py` ~408-470（delivered_final_matches / has_delivered_text）
- 🔴 **DM 手动补发长回复也会静默丢失（2026-08-12 实踩，与 cron 投递同根因）**：补发 8/12 跨境日报（10176 字符）时 gateway.log 显示 `Sending response (10176 chars)` 但**无任何后续 Flushing/segment 确认日志**，用户没收到——前后时段 TG 网络抖动（17:34:00 ConnectError + 17:43:00 Timed out），发送在拆条过程中断，assume-delivered 把"没送出"当"已送"。**与 8/8 cron 投递丢失同一机制，场景扩展到 DM 会话长回复**（>4096 拆条 = 多条发送 = 撞抖动窗口概率更高）。排查信号：gateway.log 只有 Sending 无 sent/flush 确认 + 该时段有 `Telegram network error`/`polling degraded`。补发前先 `curl --proxy http://127.0.0.1:7897 https://api.telegram.org`（302/几秒内 = 网络可用）再发；发送后若用户仍未收到且日志无确认 → 等网络平稳后重发
补投递（**不重跑 cron**——重跑走 20 分钟全流程且可能重复推）：
- 跨境日报已存档：读 `archives/crossborder/YYYY-MM-DD.md` 全文，按 4096 字符/条分 3-4 段直接补发（标注"补发 1/N"）
- 5 类日报无存档：从 `~/AppData/Local/hermes/cron/output/<jobid>/YYYY-MM-DD_HH-MM-SS.md` 的 `## Response` 段提取日报全文补发
- 补充：cron 输出文件 Response 若是"验证总结"而非日报本体（agent 声称"已在上面分 N 段交付"）——说明日报在 agent 中间输出里，投递的只是最终响应；用户视角=没收到日报。**🔴 2026-08-12 17:00 实踩（跨境日报，response_len=529 字符）**：agent 生成完整日报（21 条已存档 ✅）后，最后一步把"20/20 ad-hoc 验证通过总结"输出为最终回复，日报正文被顶掉（cron 只投递 final response）。**修复已落地：cron prompt 第 6 步加铁律——"最终回复必须 ONLY 是日报全文本身；禁止输出任何验证总结/过程报告/步骤清单/测试结果/确认信息（这些写草稿/日志文件即可，绝不进入最终回复）；最终回复只允许出现日报正文"**（两个日报 cron 均已更新）。排查信号：`Turn ended ... response_len` 远小于存档大小 + cron 会话末条是技术性总结而非日报开头
   - 🔴 **第一版措辞修复无效（2026-08-13 连续第二天实踩）**：8/12 上线的"禁止验证总结"铁律**没拦住**——8/13 跨境日报 agent 仍自创 `Temp\hermes-verify-bookkeeping.py` 验证脚本（prompt 根本没让它写验证代码）+ 输出"13 项 PASS 验证总结"为最终回复（response_len=573，正文 20 条已存档但被顶掉）。**根因：agent 的"完成即输出"心智——它把中间轮输出日报正文当作步骤完成标志，把验证汇报当作最终交付；措辞级"禁止"打不过这个心智**。**第二版修复（2026-08-13）：第 6 步改为"用 read_file 读取 _draft_cb.txt 内容并**原样输出**为最终回复" + 明示"禁止自行创建或运行任何验证脚本（bookkeeping 脚本内部自带校验）" + 点名"连续两天事故"**。教训：**cron 最终回复要"钉死"为文件内容的原样输出（read_file），不要依赖 agent 自觉；任何让 agent"自行组织最终回复"的指令都会给它自由发挥的空间**。⚠️ 但 Opus 评审（2026-08-13）指出 read_file 方案仍有新坑（模型可能回"文件已读取如上"——tool result≠text response 但模型不区分；max_tokens 截断半截日报；陈旧文件静默；"文件缺失→无新动态"兜底有毒）。**用户拍板采用 Opus 方案 C+D：生成/投递分离架构（见「生成/投递分离架构」章节），8/13 下午已落地，不再依赖 agent 的最终回复**
- 🔴 **补发分段姿势（2026-08-09 实踩，两版对比）**：
  - ❌ 失败模式：在**用户消息触发的 run 结束后**（response ready 之后）再输出补发文本——**run 结束后的 agent 输出不进投递通道**（gateway.log 无 Sending/Flush 记录，用户收不到，且无任何报错）。MEDIA 文件也不可靠（用户可能不看文件，明确要求"直接在消息里发"）
  - ✅ 正确模式：补发必须发生**在用户消息触发的 run 内**——**分段文本 + 每段后跟一个工具调用**（如 `terminal echo ok`）维持 run 循环，run 内的文本随工具调用 flush 投递（帖 1-6 交付模式验证有效）。每段 ≤3800 字符
  - ✅ **补发开头必须先声明日期**：`今天 X 月 X 日，这是补发 Y 月 Y 日丢失的日报`——用户曾因补发 8月8日 日报被误认"今天发的怎么是昨天的内容"（实为补发昨天丢失的，用户提醒"今天不是8月9号吗"）
   - 🔴 **补发/排查前先 `date "+%Y-%m-%d %H:%M"` 确认当前日期（2026-08-13 实踩）**：跨天处理"未收到日报"时（8/12 晚补发 → 8/13 用户才看到），容易把昨天的日报当今天的处理，用户困惑"发 8.12 的给我干嘛"。**任何"未收到日报"排查/补发流程第一步：确认当前日期，再对照用户问的是哪天的日报**（8/13 11:00/17:00 双日报均有投递记录，用户问的可能是当天的）
  - 🔴 **补发前先核对已送达清单（2026-08-11 用户批评"又发两遍"）**：用户已收到第 1 段 + 首轮补发的 2/3、3/3 后，说"完整的发我一份"时误判为"全量重发"，把 2/3、3/3 又发了一遍被批。**任何补发/重发前：先确认用户已收到哪些（查 cron 会话最终输出 + 本轮已补发记录），只补缺口**。🔴 **用户要"完整一份"= 从头到尾完整重发分段文本——绝不改成"优先发文件"**（2026-08-11 用户明确否决文件优先："不要，长文字还是发消息给我，不要改成优先发文件"）。文件优先方案曾作为双投递规避手段被提出，用户拒绝

## 生成/投递分离架构（方案 C+D，2026-08-13 落地，跨境日报）
连续两天"验证总结顶包日报"（8/12、8/13）后用户拍板采纳 Opus 方案 C+D——**根治"LLM 在正确时刻说出正确话"这个脆弱契约**：cron agent 不再负责投递，投递交给独立 no_agent 脚本读文件。核心原则（Opus）：**不要让 LLM 当字节的搬运工**；交付是动作不是话；控制面（对话）与数据面（文件）分离。

**架构**：
- **Job A 生成任务**（`TrendRadar跨境日报` f4506e87cc69，17:00，**deliver=local 不投递**）：prompt 改——第 4.5 步审查修复后覆盖写 `output/_draft_cb.txt`（投递任务唯一内容来源）；第 6 步=一行完成确认；🔴 铁律：全程禁止中间 text response 输出日报正文（只写文件，中间步骤以 tool call 收尾）、禁止自创验证脚本、无新闻日也写草稿（内容"📦 今日跨境无新动态…"）、生成失败**不更新** _draft_cb.txt（投递任务靠 mtime 检测告警）
- **Job B 投递任务**（`TrendRadar跨境日报投递` e8e436bbf9b1，**no_agent**，schedule `15,45 17 * * *`，deliver=origin）：跑 `scripts/deliver_cb.py`，**stdout 非空=原样投递、空=静默**。17:15 首投（正常情况）；17:45 重试（Job A 慢时补投，DeepSeek 过载日 Job A 可能 17:30+ 才完成）
- **`deliver_cb.py` 三个核心机制**：
  1. **幂等标记**：`output/_cb_delivered.txt` 记录上次投递时草稿的 mtime；草稿 mtime == 标记 → 已投递 → 静默（防 17:15/17:45 双投）
  2. **投递守卫**：正常日报须 ≥5000 字符且以 `⚡` 开头；"无新动态"短内容（<2000 字含"无新动态"）也放行；内容异常 → 输出告警不投递（防半截日报/格式污染）
  3. **大声失败**：草稿+存档都缺失且 ≥17:40 → 输出显式告警"跨境日报生成失败…"；17:15 时段静默（Job A 可能还在跑）。**"文件缺失→报错"而非"无新动态"**（Opus 指出原兜底分支有毒：写盘失败伪装成正常无新闻日）
- 存档兜底：草稿缺失但存档 `archives/crossborder/YYYY-MM-DD.md` 今天存在 → 读存档投递
- 健康检查 cron（`日报投递检查-跨境` 4267ecb32b42）同步调到 17:45（Job A 17:00-17:30 完成后才查）
- **cronjob create 坑**：`script` 参数必须是相对 `~/AppData/Local/hermes/scripts/` 的文件名（如 `deliver_cb.py`），绝对路径报错 "Script path must be relative to ~/.hermes/scripts/"
- 验证：8/8 分支 ad-hoc 验证 PASS（首次投递/幂等/存档兜底/mtime 重投/守卫拒投/无新闻日/缺文件不抛异常）；**执行代码验证脚本时用 execute_code 直接 import 模块 + monkeypatch 路径常量到临时目录，避免 Temp 脚本自激循环**（比写 hermes-verify-*.py 更干净）
- 完整方案（Opus A/B/C/D 评审原文要点/deliver_cb.py 逻辑/验证断言）：`references/delivery-separation-2026-08.md`

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
  - **跨境日报 17:00**（cron `TrendRadar跨境日报` f4506e87cc69，2026-08-12 从 16:00 调整避 DeepSeek 下午高峰；**2026-08-13 起生成/投递分离**：Job A 17:00 生成不投递 → Job B no_agent 投递 `deliver_cb.py` 17:15/17:45 读文件投递，见「生成/投递分离架构」）：`prepare_candidates.py --crossborder-only`（24h 窗口、三通道、去重后全推、独立消息）。顶部 Opus 设计的**模块化 AI 分析**（⚡今日速览 / 🏛政策风向 / 🛒平台规则 / 📈市场与成本 / 🧰实战参考 / 📖小白词典 / ✅今天该做的一件事，900-1200 字，小白教学风）+ 新闻清单（中文标题 + 2-3 句带数字摘要 + 链接；英文源「中文译名（English original title）」+🔤 标记）
  - **5 类日报 11:00**（cron `TrendRadar五类日报` 970113abe8a7，2026-08-12 从 9:30 调整避 DeepSeek 早高峰）：`prepare_candidates.py --hot-only --pushed-file pushed_five.json`（**纯热榜白名单**通道、24h 窗口、去重后全推）。**投资视角分析**（⚡速览 / 🇺🇸美股与纳指 / 🥇黄金 / 🇨🇳中国科技 / 🤖AI半导体 / 🌐宏观与政策 / 📌对投资的提示，700-1000 字，**不喊单不给买卖建议**，非小白教学）+ 新闻清单（5 板块）
  - 两日报**独立防重复文件**（pushed_titles.json / pushed_five.json），互不干扰；用户原话："早上9.30推送一次吧 一天只推送这一次"
  - 旧方案"每天 2 次（09:10/18:10）+ 精选 10-20 条"已废弃（用户改要 16:00 单窗口 + 全推）
- 关注领域 1.0：6 大领域，跨境电商按"市场×平台×环节×政策"四维设计
- 版本基线意识：关键词库有版本号（v1.0），改动需用户确认
- 改配置/改代码前必须征得同意（红线）；部署前先核实仓库身份与内容（用户曾纠正"这是刚 fork 的空仓库"）
- **用户要求"看某个文件"时给全文**：贴完整内容（代码块）或 MEDIA 发文件，结构导读/摘要表不够（用户曾明确"我要看完整的关键词库"）
- **卡在决策点时主动说明**：用户问"没进展了？"= 在等我拍板。停在等待点时要明说"卡在需要你确认的 X"，并给出可点的选项（clarify），不要让用户猜
- 🔴 **告警即处理（2026-08-10 用户批评）**：投递健康检查/看门狗等自动告警**触发后必须立即排查根因并汇报解决进展**，不能等用户来问"报错了但你没有后续解决操作"。告警消息发出 ≠ 任务完成，收到告警 = 进入排查流程（按日报排查 SOP 走），并主动说明当前状态和下一步
- **双方案对比偏好**：用户会要求"你先给方案，再把需求发 Opus 独立出一份方案"来对比。两版都要给，且用实测数据诚实指出对方方案的乐观/错误处（如 Opus"8 源半天零成本"被连通性实测推翻为 5+4+3 三档工作量）——用户重视交叉验证，不盲信单一来源
- **交付只发成品**（用户原话："只发完整的跨境日报，别的多余的话不要发"）：日报类推送的最终回复=日报本体，不加解释/总结/前后缀；实现/排障说明在日报之外另行简短汇报
- **长文字继续发消息，不优先发文件**（2026-08-11 用户明确否决文件优先）：曾提议"长内容改发 MEDIA 文件规避双投递"，用户拒绝——长日报/长报告一律按原形态发文本消息（可分段），文件只用于存档场景。此偏好优先级高于"规避双投递"的工程考量
- **分析风格按受众区分**（用户明确区分两类）：跨境日报=小白教学风（读者未入场，通俗、术语即解释、给行动）；5 类日报=投资视角（读者是纳指定投+黄金积存的投资者，划重点不教学，**不喊单不给买卖建议**）。两者不得混用
- **分析迭代流程**（用户需求→Opus 设计→确认→落地）：用户对分析板块的格式需求（分模块/信息密度/中文化）先发给 Opus 出设计稿（prompt 附用户原话+现有日报结构+画像），用户确认后再固化进 cron prompt——设计类问题不自己拍板

## See Also
- `references/frequency-syntax.md` — 关键词语法与防串领域设计详例
- `references/database-format.md` — TrendRadar SQLite 库结构、时间格式、增量模式局限
- `references/funnel-baseline.md` — 漏斗统计方法与数量级基线
- `references/keywords-v11-opus-review.md` — 关键词 v1.1 全量修订明细 + Opus 审查发现 + 行为测试用例集
- `references/crossborder-sourcing-plan.md` — 跨境电商垂直数据源方案（Opus 出品：源清单/双通道架构/三级告警/运维/路线图）
- `references/daily-report-review-2026-08.md` — 日报投递前自动审查机制（三层质检/L1 模型选择/cron 第 4.5 步/Codex CLI 调用姿势/extract_json 陷阱/验证方法）
- `references/daily-report-cron-spec-2026-08.md` — 双日报 cron prompt 规范精炼版（跨境 16:00 + 5 类 9:30 的完整步骤/模块结构/硬规则/存档格式）——改日报格式以此为准并同步更新
- `references/deepseek-overload-avoidance-2026-08.md` — DeepSeek 过载避峰方案（延迟时间模式数据表/api_probe+report_gen_qwen 脚本/验证断言/cron 第 0 步集成设计/待办）
- `references/delivery-separation-2026-08.md` — 生成/投递分离架构（方案 C+D：Opus 四方案评审/deliver_cb.py 逻辑与验证/Job A/B cron 设计/可迁移设计原则）
