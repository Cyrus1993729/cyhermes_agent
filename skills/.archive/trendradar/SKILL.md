---
name: trendradar
description: "TrendRadar 本地部署/精选管线：纯采集+Hermes主编推送、关键词语法防串领域、看门狗运维。"
version: 1.0.0
category: devops
tags: [trendradar, deployment, news-monitor, pipeline, keywords, telegram]
---

# TrendRadar 部署与精选管线

## 架构（2026-08 确立，08-07 更新）
- **TrendRadar = 纯采集器**：每小时采集 11 平台热榜 + RSS（含跨境垂直源）入本地 SQLite，**无推送无 AI 分析**（config.yaml `notification.enabled=false`、`ai_analysis.enabled=false`）
- **Hermes = 主编**：每天 16:00 跨境日报 cron（`--crossborder-only` 模式，24h 窗口，语义去重后**全推**，单独消息）+ **每天早上 9:30 五类日报 cron**（`--hot-only` 模式：纯热榜白名单、投资视角分析不喊单、独立防重复 `pushed_five.json`——2026-08-07 用户定版，详见 `references/five-class-report-2026-08.md`）
- 用户偏好演进：跨境新闻"跨平台语义去重、同一事件只保留一条、去重后全推不砍数量"；5 类新闻与跨境**分开推送**（用户明确）
- 用户接受简化流程：部署类任务 Opus 审完即执行，跳过 L1 审查/复盘

## 部署要点（Windows 本机）
- 安装：`git clone` → `uv sync`（清华镜像：`UV_DEFAULT_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple`，秒级）
- 🔴 **PYTHONPATH 污染**：Hermes 环境会注入 hermes venv 的 PYTHONPATH → 子进程 python 导错包（症状 `pydantic_core` ModuleNotFound）。所有 TrendRadar 运行前必须 `unset PYTHONPATH VIRTUAL_ENV`
- 密钥零落盘：`run_secrets.bat` 存 token/key，`start_trendradar.bat` call 它注入环境变量（`TELEGRAM_BOT_TOKEN`/`AI_API_KEY` 项目原生支持，loader.py 环境变量优先于 config.yaml）
- `git remote remove origin` 防误推（Opus B11）
- 开机自启：`schtasks /Create /TN TrendRadarHourly /SC HOURLY /MO 1` + `TrendRadarStartup /SC ONLOGON`
- 看门狗：Hermes cron 30min 跑 `watchdog_trendradar.py`——检查 `output/logs/run.log` 新鲜度（4h 阈值），陈旧则自动拉起 + 写触发标记，连续两次仍旧才告警（静默原则）
- 备份：每周 cron 跑 `cleanup_backup_trendradar.py`（90 天清理 + 打包到 `D:\Workspace\Backups\TrendRadar`）
- cron 的 script 参数必须是 `~/AppData/Local/hermes/scripts/` 下的文件名（不支持绝对路径）

## 配置体系
- `config.yaml` 关键开关：`notification.enabled`、`ai_analysis.enabled`、`schedule.enabled`、`report.mode`
- `timeline.yaml`：presets（always_on/morning_evening/office_hours/night_owl/custom）+ periods（start/end/report_mode/once）+ day_plans/week_map；`schedule.enabled=false` 时每次运行全流程
- report_mode：`current`（当前在榜）/ `daily`（当日全量）/ `incremental`（增量，无新增不推）
- 🔴 **incremental 跨天局限**：`detect_new_titles` 只查当天库（按天分文件）→ 每天第一次运行把全部在榜当新增推（昨晚推过的重复）。要跨天增量需改 sqlite_mixin + analyzer 两处（用户已认可方向，未实施——现用 Hermes 精选方案绕开，不碰上游代码）

## 关键词语法（frequency_words.txt）
- 必须有 `[GLOBAL_FILTER]`（排除区）和 `[WORD_GROUPS]`（词组区）两个区段标记——🔴 **漏 `[WORD_GROUPS]` 解析器认为无词组 → 全部标题匹配**（已踩）
- 普通词 = OR；`+词` = 必须词（AND）；**组内规则：所有 +词 全中 AND 至少一个普通词命中**
- 正则 `/a|b/ => 显示名`；`@N` 限条数
- **防串领域设计**：通用词（关税/贸易摩擦/亚马逊/沃尔玛）绝不单用——独立组合组（纯必须词或 +词+普通词正则）；专属词（T86/海外仓/FBA/TikTok Shop）放心单用
  - 例：`[电商关税]` 组内 `+电商` `+关税`（无普通词）→ 只命中同时含两词的标题
  - 例：`[亚马逊卖家]` 组内 `+亚马逊` + `/卖家|电商|FBA|封店|跟卖|店铺|Prime|平台/` → "亚马逊 AWS" 不串
- 关键词 **v1.1（2026-08-07，Opus 审查修订）**：6 领域 13 组，存 `config/frequency_words.txt`。v1.1 要点：删 2 个死规则（`[电商关税]`/`[跨境贸易摩擦]`——纯 +词 组合命中率极低且前者被宏观裸"关税"覆盖）；宏观组裸词（关税/贸易摩擦等）抽成独立 `[关税与贸易战]` 组 + `@6` 限流；修 5 类高频误伤词（苹果/黄金/消费/仰望/AGI→magic）；TikTok 空格写法永不命中→正则 `tiktok\s*(shop|电商|小店|...)`；新增 `[跨境经营模式]`（全托管/TRO/黑五等）。详见 `trendradar-operations` 的 `references/keywords-v11-opus-review.md`
- 🔴 **解析器陷阱（frequency.py 实测）**：① `!` 过滤词实际**全局生效**（filter_words 是扁平列表），非文档所说"仅限当前词组"；② `\b` 对中文无效（中文属 `\w`），英文边界一律 `(?<![a-z])xxx(?![a-z])`；③ `[WORD_GROUPS]` 标记粘性——误删后下方所有关键词变全局过滤词 → 静默 0 推送，务必保留该行

## 数据层（精选管线读取）
- `output/news/YYYY-MM-DD.db` 按天分库；表 `news_items`/`platforms`/`rank_history`
- 🔴 **库内时间 = `HH-MM` 格式**（日期在文件名），窗口过滤/排序需先拼 `full_time = f"{date} {HH-MM}"` 再字符串比较
- 爬取频率每小时 → 数据全、排名轨迹细，利于精选

## 精选管线（Hermes 主编）
- `prepare_candidates.py`（v2 三通道，2026-08-07）：默认按当前时间自动选窗口（hour<14 → 昨天 18:00 起；否则 → 今天 09:00 起）；**跨境模式 `--crossborder-only`**：固定 24h 窗口（get_window mode="cb"）+ 只输出跨境候选（rss+cb 垂直源全量 + 热榜命中跨境 7 组的，实测热榜跨境命中≈0）→ 归一化去重 → 排除 `pushed_titles.json` → 候选 JSON 到 stdout
- 三通道：A 热榜白名单过滤 + B RSS 跨境源（CB_RSS_FEEDS：modern-retail/retail-dive/tamebay/ustr）+ C crossborder JSON。**垂直源源级信任不过白名单，仅过全局噪音过滤**（防误杀，如"日本 JCT 申报"一个白名单词都不命中）
- `pushed_titles.json`：已推送事件清单（title/norm/pushed_at/**url**），LLM 推送后 append（跨会话去重记忆）
- 🔴 **pushed 防重复的比对字段教训（2026-08-07 修复）**：最初只记"合并后事件标题"的 norm，prepare_candidates 用"**原始候选标题**"norm 去比对 → **永远匹配不上**（合并标题≠任何原始标题）→ 已推送排除形同虚设 → 手动推过的 16:00 cron 会重复推。修复：pushed 条目增加 `url` 字段（每条事件代表 URL），排除逻辑 = `normalize(title) not in pushed_norms AND url not in pushed_urls`（url 稳定可靠，标题 norm 兜底兼容旧数据）。同时 cron prompt 加"第 1.5 步"：LLM 先读 pushed_titles.json 了解已推事件标题，语义合并时与已推标题相同/高度相似的事件跳过不推（防同一事件的其他源版本重复推）
- cron（跨境日报 16:00，job 名 TrendRadar跨境日报）：**script 留空**——cron script 用系统 python 无项目依赖（litellm 在 uv venv），改由 prompt 第 1 步指示 agent 依次跑 `fetch_summaries.py`（补摘要，1-2 分钟）→ `prepare_candidates.py --crossborder-only`，读 stdout JSON
- 候选上限 200（三通道全量约 200；**MAX=120 会截掉 cb 通道**（99→18），已踩）

## 推送格式（UX 硬性要求，2026-08-07 用户纠正）
- 🔴 **每条必须带摘要 + 原文链接**：用户明确纠正"只有标题看不到新闻讲了什么，也没有链接"（例：「美国取消800美元小包免税，卖家该怎么应对」→ 怎么应对看不到）。无摘要/无链接 = 不合格推送
- 格式（cron prompt 第 3 步）：按板块分组（🛃 政策法规 / 🏪 平台动态 / 📦 物流与市场 / 💼 行业公司 / 📈 市场趋势），每条三行：
  `• 标题（来源）` / `摘要：1-2 句中文（基于 summary 提炼）` / `🔗 [查看原文](url)`
  重大政策标题加 🔴 前缀；TG 单条 4096 字符限制 → 超出拆多条，末尾标（1/N）
- **summary 数据现实**：`rss_items` 表有 summary（RSS description）、cb JSON 有 summary（Federal Register abstract 质量高）；🔴 **热榜 `news_items` 无 summary 列**（只有 title+url，热榜新闻只能给链接）；🔴 **Google News 的 summary 是跳转链接 HTML 不是正文**（`<a href="news.google.com/...`）→ 抓取时清空（`"<a href" in summary or "news.google.com" in summary → summary=""`）
- **方案 B（2026-08-07 用户选定，取代"无摘要只给链接"）**：`fetch_summaries.py` 在推送前为无摘要候选（Google News/Reddit）**抓正文补摘要**——requests + proxies 7897 + UA 抓 url，HTMLParser 提取正文（跳 script/style/iframe/svg、优先 p、截 300 字符、句末截断），ThreadPoolExecutor 6 并发，失败留空（推送给链接）。实测对非 Google 源成功率高（64/69 看似成功——但**那批"成功"其实抓到的是 Google 桥接页 JS 垃圾，见下**）
- 🔴 **Google News 抓正文最终结论（实测推翻早期乐观判断）**：requests 跟随 `news.google.com/rss/articles/CBMi...` 跳转**停在 Google 桥接页**（591KB，含 `window.WIZ_global_data` JS 数据），不达原文；桥接页 `og:url`/`canonical` 都指向 news.google.com 自己；CBMi payload base64url 解码后是 **protobuf 混淆**（无明文 URL，2023+ 新格式需专用解码器）。→ **Google News 条目无法抓正文，推送给标题+链接**（Markdown `[查看原文](url)` 隐藏超长链接，点击跳转正常）。不要投入时间做 CBMi 解码器
- 🔴 **extract_text 必须检测 WIZ 垃圾**：`if "WIZ_global_data" in text or "window.WIZ" in text: return ""`——否则 Google 桥接页 JS 数据会当摘要入库（曾污染 62 条）。fetch_summary 里"从桥接页提取真实 URL 重抓"逻辑仅当提取到**非 Google 域** URL 才执行（`"google.com" not in real`），大多数情况失败留空
- 摘要覆盖率的正确断言：**非 Google News 源覆盖 >80%**（Google News 无摘要是设计行为，不是缺陷）
- 🔴 **Google News 跳转链接无法简单解码**：新式 `CBMi...` base64url 编码（2023+ 格式）需专用解码器，通用 urlsafe_b64decode 提取不到明文 URL（解码函数要容错：失败返回原链接）→ 务实方案：推送用 Markdown `[标题](url)` 隐藏超长链接，点击照样跳转原文。不要在这上面投入解码时间
- 管线带出：prepare_candidates 输出 candidates 每项含 `url` + `summary` 字段（query_db 热榜无 summary；`read_rss_crossborder` 的 SELECT 必须加 summary 列；`read_cb_json` 带 summary；合并时 `by_norm` 存 summary）

## AI 分析板块（日报顶部，Opus 设计，v2 模块化 2026-08-07 用户确认）
用户要求日报不只是新闻清单，还要有一段给**小白**（想做跨境电商、未入场）看的通俗分析。形式由 Opus 设计：v1「先看这里 · 3 件事」用户认可通俗性，但反馈"新闻不会都点开看、英文多阅读难、想要更多信息、分析分模块" → v2 模块化（用户确认实施）：
- **v2 七模块**：⚡ 今日速览（3 条一句话 ≤35 字）→ 🏛 政策风向 · 门槛变了吗 → 🛒 平台规则 · 在哪卖、怎么卖 → 📈 市场与成本 · 钱往哪走 → 🧰 实战参考 · 别人怎么做的 → 📖 小白词典（2-3 术语一句话+生活化比喻）→ ✅ 今天该做的一件事（≤50 字）。空模块一行带过不注水
- **三行信息卡**（每条事件）：`▶ 一句话标题（谁·做了什么·何时生效）` / `　干货：2-3 个原文具体细节` / `　对你：一句话新手视角`。**数字必须落地**（金额/百分比/日期/门槛原样进"干货"行）；每条至少 2 个数据点，凑不出的不收录；单行 ≤40 字、单条 ≤120 字、单模块 ≤250 字、全文 900-1200 字
- **英文处理三层**：① 清单标题必译「中文译名（English original title）」+ 英文源行首 🔤 标记；② 摘要扩 2-3 句且带数字；③ 重要英文新闻进模块"译+补"（补英文媒体省略的背景：公司是谁/原政策/为何算新闻）。不做逐条全文翻译
- 🔴 **用户最后纠正（最重要，2026-08-07）**：「原文未说明具体执行细则，应对策略在原文中」这类话**无法让用户获取信息**——禁止一切把读者推回原文的措辞（值得关注/有待观察/建议跟进/详见原文/原文未说明/原文给出应对策略）。**候选 summary 缺失或单薄时，必须用行业背景知识把事件讲透**（这是什么政策/公司/模式、影响谁、应对方向），标注"背景："前缀区分事实与背景；不得编造新闻中未出现的具体数字（如具体生效日期/税率数值），但方向性影响（成本上升、模式要变）可讲。有摘要→翻译提炼+数字落地；无摘要但事件重要→背景补位
- 通俗性底线（v1 继承）：最多 2 个术语（"人话（行话叫 XX）"）；解读带不确定度词；推测标注"（这是我的推测）"；禁"赋能/闭环/抓手/生态位"等黑话；优先每天至少 1 件事是"具体的坑"（合规/账号/选品禁区）
- v1 设计（先看这里 3 件事）+ v2 模块化完整生成指令与示例：`references/ai-analysis-modular-v2.md`（同类"小白向行业日报"可复用此模板）

## 跨境电商垂直源（2026-08-07 接入，第1/2档）
- **现实**：跨境电商是垂直行业，newsnow 热榜（大众热点）实测连续多批 0 条命中 → 必须独立垂直源通道
- **第 1 档 = 纯配置 RSS**（TrendRadar config.yaml `rss.feeds` 加 URL + `max_age_days`）：modern-retail/retail-dive/tamebay/ustr 直连可达（各 10 条/次）；🔴 **中文媒体 RSS 大面积已废**——雨果跨境 `/rss` 实测返回 HTML 非 RSS（已禁用），中文通道需公众号转 RSS 服务（¥8-17/月）或 RSSHub
- 🔴 **USTR RSS 噪音**：大部分条目是"州出口数据"静态页面（Wyoming/Wisconsin/Texas 等按字母排），非贸易新闻——精选时整批剔除（可考虑 fetcher 层过滤州名）。Rest of World 是泛科技出海媒体，具体文章常与跨境无关（AI/EV/政治），精选时逐条判断；Modern Retail/Retail Dive 是泛零售，美国本土零售动态（Sweetgreen/Kroger/Home Depot 等）占多数，仅保留 Amazon 卖家/平台出海相关
- **第 2 档 = `crossborder_fetcher.py`（代理/API 源，独立脚本）**：requests + proxies(127.0.0.1:7897) + UA 抓取，feedparser.parse(响应文本)；4 类源：Federal Register API（JSON，2 query：de minimis/section 301，**FEDREG_FILTER 宽松正则过滤**——全库全文搜索噪音大，airspace 修正案等须滤）、Rest of World、Reddit r/FulfillmentByAmazon、Google News RSS（4 query，**每条间隔 10s 防 429**，URL 编码 query）；输出 `output/crossborder/cb_candidates.json`（去重后 ~90 条/次）；计划任务 `TrendRadarCrossborder` 每小时
- 🔴 **TrendRadar 不支持按源代理**（全局代理会让 newsnow 国内 API 403）→ 被墙源（Google News/Reddit/Rest of World）必须走独立脚本，不能塞进 TrendRadar rss 段
- **连通性实测方法论**：批量 probe（urllib 直连 vs ProxyHandler 7897 对比）——6/12 源直连可用、3 被墙需代理、3 需排障（Marketplace Pulse 404/CBP 406/亿邦 302）。接源前必测，别信"应该能访问"
- 详细源清单与 Opus 起步组合：见 `references/crossborder-sources-2026-08.md`

## 数据源与 AI 坑
- newsnow API：**带浏览器 UA 直连 = 200；默认 UA 或走代理 = 403**。项目 fetcher 自带 Chrome UA，无需额外处理
- **热榜门槛在 newsnow 服务端**：每平台固定返回 20-30 条（微博 30/知乎 20/头条 30/贴吧 30/抖音 30...），单次全量 ≈ 255 条 = 11 平台 × 20-30。TrendRadar 代码**无截断**（只做 expected_domain 域名安全校验）；"进榜"= 上平台官方热搜前 20-30，平台算法决定，不可调
- DeepSeek 分析超时：v4-flash 推理模型（带 reasoning_content）全量分析需 2-4 分钟，`ai.timeout` 从 120 → 300，`num_retries` → 2

## Opus 审查工作流（配置/代码审查类）
- 材料三件套内联进 prompt：我们的配置全文 + 官方模板规范 + 解析器源码（frequency.py）——Opus 能对照实现逐条核对，发现"文档与实现不符"（如 `!` 词全局生效）
- 🔴 **必须显式禁工具**：`--tools ""` 不总是生效——Opus 曾"读取"并**编造假文件**（幻觉输出假 prepare_candidates.py），且不回答问题。修复：prompt 开头加「不要调用任何工具，不要读取/创建文件，所有材料已包含」+ `--disallowedTools "Read,Write,Edit,Bash,Glob,Grep,WebFetch,WebSearch,TodoWrite"`
- 审查输出分级（P0 必改/P1 建议/P2 可选）+ 逐条可操作改法 → 用户拍板后照改，改后重新验证（行为测试+漏斗实测）

## 正文摘要补充（方案 B）与回归验证
- `fetch_summaries.py`：读 `output/crossborder/cb_candidates.json`，对 summary 空条目并发抓正文（requests + proxies 7897 + UA；HTMLParser 子类提取：跳 script/style/iframe/svg、`<p>` 加换行、300 字符、句号/问号处截断）。**幂等**（已有摘要不重抓）。🔴 **Google News 跳转链接抓不到正文**（停在桥接页，WIZ_global_data JS 垃圾；CBMi protobuf 混淆不可解码）→ extract_text 检测 WIZ 垃圾返回空，Google News 条目推送给链接（见"推送格式"章节的最终结论）
- cron（TrendRadar跨境日报 16:00）完整流程：`fetch_summaries.py`（补摘要）→ `prepare_candidates.py --crossborder-only`（取候选 JSON）→ LLM 语义去重 + 相关性过滤 + 全推 → 写 `pushed_titles.json` → 回复日报全文（自动投递 TG）
- **canonical 回归验证**：`verify_crossborder_pipeline.py`（**26 项断言**，2026-08-07 扩展：跨境 12 项 + 5类模式 5 项（--hot-only 窗口/纯hot通道/候选数/无rss-cb混入）+ pushed_five 4 项 + extract_text 垃圾/反爬/超短/article 优先 6 项。🔴 历史断言样本 <20 字符会被\"超短拒收\"规则挡掉——FAIL 是断言问题非代码 bug，样本需加长到 >20 字符）。改管线后跑：`cd /d D:\Workspace\Projects\TrendRadar && unset PYTHONPATH VIRTUAL_ENV && uv run python verify_crossborder_pipeline.py`
- 🔴 **验证脚本自激循环教训（Hermes 工作流）**：验证状态机把 Temp 下 `hermes-verify-*.py` 的创建/删除也计入 changed paths → 每次按指示建一次性临时验证脚本都会制造新的 changed path，无限循环无法收敛。解法：验证逻辑固化为项目内**持久 canonical 脚本**（如 verify_crossborder_pipeline.py，gitignore 覆盖），以后改管线跑它，不再用 Temp 一次性脚本

## 常用命令
- `uv run python -m trendradar --doctor`（体检）/ `--show-schedule` / `--test-notification` / 无参 = 运行一次全流程
- 日志 `output/logs/run.log`；报告 `output/html/YYYY-MM-DD/`
- schtasks 输出 GBK 乱码（subprocess text=True 解码会报错，用 returncode 判断即可）

## See Also
- `local-service-deployment` — 通用本地部署技术（Windows 自启/看门狗/备份模式），本技能是 TrendRadar 工具特定细节
- `references/deployment-notes-2026-08.md` — 部署全过程、Opus 审查要点、验证方法、遗留事项
- `references/crossborder-sources-2026-08.md` — 跨境垂直源连通性实测表、crossborder_fetcher 设计、Opus 起步组合/三级告警/运维机制
- `references/ai-analysis-block-opus-design.md` — v1「先看这里 3 件事」设计（小白向日报分析模板初版）
- `references/ai-analysis-modular-v2.md` — **v2 模块化设计（当前生效）**：七模块结构、三行信息卡、英文三层处理、用户纠正（禁"原文未说明"类空话，无摘要用背景补位）、完整生成指令与修订示范
- `references/five-class-report-2026-08.md` — **五类日报（9:30 投资视角，2026-08-07 定版）**：--hot-only/--pushed-file 管线改动、投资视角分析格式、fetch_summaries 泛化与编码/反爬/SPA 修复、热榜源正文抓取现实、验证 26 项

## cron 触发排查（Hermes 工作流）
- 🔴 `cronjob list` 的 `last_run_at: null` **不等于未触发**——job 运行中不写入 last_run_at（完成后才写），next_run 已推到下周期。判定用 agent.log：`grep 'cron_f<jobid>' "C:\Users\Administrator\AppData\Local\hermes\logs\agent.log"` 看 session 是否启动（`Job '<name>': loaded credential pool`）并持续推进（`API call #N`/`tool terminal completed`）；完成标记 = `Job '<name>' completed successfully` + `delivered to telegram:<id> via live adapter`
- DeepSeek 高峰时段响应可慢至 8-180s/次 → 日报 cron 执行时长可达 15-20 分钟（正常 5-8 分钟）；同刻看门狗等 no_agent cron 正常 = 调度器无问题，只是 API 慢。先查日志再下结论，别误判"没触发"
