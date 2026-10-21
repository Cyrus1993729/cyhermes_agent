# TrendRadar 本地部署实录（2026-08-06）

部署对象：TrendRadar v6.10.0（AI 热点监控，Python，GPL-3.0，github.com/sansan0/TrendRadar）
目标机器：Windows 笔记本 i5-6200U / 8GB / 256GB，24h 开机，本机已有 Hermes + Clash 7897 代理
部署方式：本地 uv（方案A，用户确认不用 Docker）

## 关键事实
- 用户仓库：Cyrus1993729/trendradar（template 创建非 fork；用户删过旧版仓库，新版=空模板，配置从零配）
- 运行模式：`uv run python -m trendradar` = **每次运行执行一次完整流程后退出**（无常驻进程）
  - 诊断命令：`--doctor` / `--show-schedule` / `--test-notification`
  - 调度：timeline.yaml preset（morning_evening 等）+ schedule.enabled；本地模式每次运行按当前时间解析调度
- 数据源：newsnow 公共 API `https://newsnow.busiyi.world/api/s?id=<platform>&latest`（fetcher 内置 Chrome UA 头，直连 200；默认 curl UA 403）
- AI：DeepSeek `deepseek/deepseek-v4-flash`，国内直连 `api.deepseek.com`；**timeout 必须 300s**（120s 分析全量新闻超时返回空响应）；num_retries 2
- TG：bot "牛马宇"（8839546337 开头）与 Hermes 共用——**一个 bot token 多服务 sendMessage 零冲突**（TrendRadar 只发不收，getUpdates 仍归 Hermes）

## 部署产物（可复制的形态）
- `start_trendradar.bat`：set PYTHONPATH=（清 Hermes 污染）→ call run_secrets.bat → cd 项目 → uv run python -m trendradar >> output\logs\run.log
- `run_secrets.bat`：set TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID / AI_API_KEY（被 .gitignore 忽略）
- 计划任务：TrendRadarHourly（/SC HOURLY /MO 1）+ TrendRadarStartup（/SC ONLOGON），均指向 start bat
- 看门狗 cron：scripts/watchdog_trendradar.py（no_agent，*/30 * * * *，静默/触发/告警三态）
- 数据维护 cron：cleanup_backup_trendradar.py（0 4 * * 1，90 天清理 + 每周备份到 D:\Workspace\Backups\TrendRadar）
- config.yaml：notification.channels.telegram.bot_token/chat_id 与 ai.api_key **留空**，全走环境变量

## 配置要点
- display.regions：hotlist=true, new_items=false, rss=true, standalone=false, ai_analysis=true（默认）
- report.mode=current；filter.method=keyword；max_news_per_keyword=0（不限）
- 用户关注词在 config/frequency_words.txt（[GLOBAL_FILTER] 排除区 + [WORD_GROUPS] 分组区，`/词1|词2/ => 组名` 语法）

## 运行中的坑（本机特有）
- Hermes 注入 PYTHONPATH → 必须 unset 才能跑 uv run（否则从 Hermes venv 导 pydantic_core 报 ModuleNotFoundError）
- 看门狗初始状态：log 不存在时静默等待（首次运行由计划任务负责），写状态标记前先 makedirs

## 用户流程偏好（本任务确认）
- 部署类任务：契约 + Opus 审查照走，但**可跳过 L1 审查与复盘**（用户明确"不一定要走 5 步流程"）
- 用户接受"观察期双份推送"（GA 与本地并存 3 天），之后停 GA

## 推送模式讨论结论（2026-08-06 晚 → 2026-08-07 早最终架构）
用户目标：每天 2 次推送，只推增量不重复
- 09:00 推送：前日 18:00 → 当日 9:00 窗口的新闻
- 18:00 推送：当日 9:00 → 18:00 窗口的新闻

**最终采纳架构（用户提出，2026-08-07）：「采集器 + Hermes 智能层」**
TrendRadar 改纯采集（每小时入库，不推送不做 AI），Hermes 每天 2 次读库 → 智能去重精选 → 推送。
理由：官方增量模式只做"当天内"精确标题去重（跨天第一次运行全量推=重复）；Hermes 可做语义去重（跨平台/改标题合并）、按用户兴趣排序、写点评，且**零上游代码改动**。
用户原话认可：改代码方案 vs Hermes 精选，选后者（"让 AI 干活"定位）。

### 纯采集模式配置（已执行）
- config.yaml：`notification.enabled: false`（总开关）+ `ai_analysis.enabled: false`
- 验证标志：运行日志出现"通知功能已禁用（ENABLE_NOTIFICATION=False），将只进行数据抓取"
- 计划任务保持每小时采集（采集不打扰，数据越全越好筛）；RSS/翻译照常

### 精选管线（Hermes 侧，已实现待挂 cron）
- `prepare_candidates.py`（项目根）：自动判断窗口——hour<14 → morning（昨天 18:00→现在）；hour>=14 → evening（今天 09:00→现在）
- 读库：`output/news/{昨天}.db + {今天}.db`（SQLite）
- ⚠️ **库内时间格式是 `HH-MM`**（无日期，日期在文件名里）！字符串比较窗口需拼成 `YYYY-MM-DD HH-MM` 全格式再比
- 归一化去重：小写+去空白标点+去修饰词（最新|热|爆|突发|快讯|刚刚…），跨平台合并
- 排除已推送：`pushed_titles.json`（[{norm, title, pushed_at}]）——LLM 精选后 append 推送的标题（防下次重复）
- 输出候选 JSON（≤80 条）到 stdout，供 cron agent 模式注入 prompt
- cron 设计（待建）：09:10 + 18:10 两个 agent 模式 cron，script=prepare_candidates.py，prompt=精选主编（语义去重→按兴趣排序→简报→先写 pushed_titles.json 再回复推送）
- 用户确认样例简报后建 cron；看门狗阈值需同步 4h→16h（每天 2 次间隔 9-15h）

### timeline 调度语法（v6.0.0+，config/timeline.yaml 是 UTF-8 但 read_file 会误判 binary，用 python 读）
- presets：always_on / morning_evening / office_hours / night_owl / custom；config.yaml `schedule.preset` 选择 + `schedule.enabled` 启用（enabled=false 时 timeline 时间段不生效，--show-schedule 显示"日计划: disabled"）
- periods 的 start/end = **推送执行窗口**（该时间区间内运行才触发该段行为），**不是数据窗口**
- report_mode：`current`（当前在榜）/ `daily`（当日全部）/ `incremental`（只推新增，无新增不推送——_has_valid_content 检查）
- `once.push/analyze: true` = 窗口内只执行一次（scheduler 记录已执行去重）
- morning_evening 结构示例：default 全天 current 推送 + periods.evening_summary（20:00-22:00, report_mode=daily, once: true）

### 增量跨天去重缺陷（核心发现，改代码依据）
- `_detect_new_titles_impl`（trendradar/storage/sqlite_mixin.py:620）：只查**当天**库（`_get_today_all_data_impl`）→ 跨天不查重
- `analyzer.py` incremental 分支（约 158-166 行）：`is_first_today`（当天第一次）→ `results_to_process = results` **全量当新增**；非第一次才走 new_titles
- 后果：每天第一次运行（如 9:00）会把昨天推过的在榜新闻重复推送
- 修正方案：
  1. sqlite_mixin `_detect_new_titles_impl`：历史数据从"当天"扩展为"昨天+今天"合并查重
  2. analyzer incremental 分支：当天第一次也走 new_titles（`new_titles if new_titles else results`）——配合①后 9:00 只推昨晚 18:00 后新上榜的，18:00 只推 9:00 后新增的
- 存储按天分库：`output/news/YYYY-MM-DD.db`；跨天查询需自行合并（无现成接口）

### 配套调整
- 计划任务 TrendRadarHourly：/SC HOURLY → 每天 09:00 + 18:00（两个触发器或 DAILY 任务）
- 看门狗 STALE_SECONDS：4h → 16h（两次推送最大间隔 15h + 缓冲）
