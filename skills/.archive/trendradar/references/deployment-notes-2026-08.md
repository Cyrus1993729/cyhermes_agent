# TrendRadar 部署笔记（2026-08-06/07）

## 部署时间线
1. 研究项目（README 95K 字符，Changelog 占大半）→ 确认方案A（本地 uv）vs B（Docker）→ 用户选 A
2. 契约 → Opus 红队审查（CONDITIONAL，13 阻断 + 10 建议）→ 用户确认简化流程（跳过 L1/复盘）
3. clone Cyrus1993729/trendradar（template 仓库，非 fork——用户旧仓库已删，新 fork 是空模板）
4. uv sync（清华镜像 49s）→ 密钥环境变量注入 → 全链路验证 → 计划任务 + 看门狗 + 备份
5. 用户提出新架构：TrendRadar 纯采集 + Hermes 精选推送（替代改代码做跨天增量）

## Opus 审查关键意见（已吸收）
- 静默失败风险 → 看门狗"拉起失败才告警" + 用户"当天没收到推送就是信号"
- 密钥明文落 git → .env 环境变量 + `git remote remove origin` 物理防误推
- 开机自启环境断层（uv PATH/代理/工作目录在计划任务里全不同）→ 手动与计划任务共用同一 bat + 重启实测
- 数据面空白 → 90 天清理 + 每周备份
- 验收标准不可判定 → 全部改为"命令 + 退出码 + 可观察产物"

## 关键实测结论
- newsnow `https://newsnow.busiyi.world/api/s?id=X&latest`：带 Chrome UA 直连=200；默认 UA/走代理=403。项目 fetcher 自带 UA 无需处理
- DeepSeek `deepseek/deepseek-v4-flash`（LiteLLM 格式）有效；v4-flash 返回 reasoning_content（推理模型），全量分析超 120s → timeout 300
- 运行模式：本地 `python -m trendradar` 无参数 = 执行一次完整流程后退出（无常驻进程）→ 定时用计划任务触发
- config.yaml `schedule.enabled=false` 时 timeline 时间段不生效，每次运行全流程（--show-schedule 可确认）
- 数据库 `first_crawl_time` 存 `HH-MM`（日期在文件名），非完整时间戳
- `detect_new_titles` 只查当天库 → incremental 模式跨天第一次全量推（官方局限）
- 🔴 **Hermes cron schedule 坑**：schedule 传 `30m` 会被解析为"30 分钟后跑一次"（once/repeat=once）→ 必须用 cron 表达式 `*/30 * * * *`，创建后 `cronjob list` 确认 repeat=forever

## ad-hoc 验证方法（项目无测试套件）
每次改动后用临时验证脚本（`%TEMP%\hermes-verify-*.py`，跑完即删）：
- config.yaml：yaml 解析 + 关键开关断言
- 脚本：py_compile + 函数级断言（normalize/窗口计算）+ 集成跑一次输出 JSON 结构校验
- 关键词文件：用项目自己的 `load_frequency_words` + `matches_word_groups` 做防串领域行为测试（真实标题样例）
- 计划任务：`schtasks /Query /TN` 返回码
- 注意：验证脚本需在项目 venv 跑（`uv run python`），系统 python 缺 litellm
- 统计口径：白名单过滤必须在候选截断（MAX_CANDIDATES=80）之前，先筛后截断（否则丢候选 57→23）——详见 references/funnel-baseline.md

## 遗留事项（2026-08-07 状态）
- 第 1 块（关键词）✅ 完成：frequency_words.txt v1.0（6 领域 13 组）已写入并实测（防串行为 12/12）
- 第 2 块（筛选提炼）讨论中：四层漏斗方案（白名单→去重→语义精选→提炼）+ 跨境低频结论已实测，待用户最终确认
- 第 3 块（推送机制）待讨论：时间/格式/静默规则
- 精选 cron（09:10/18:10 agent 模式）尚未创建——等第 2/3 块讨论完 + 样例确认
- 样例简报已发用户（基于现有库数据模拟 morning 窗口）
- GA 部署仍保留（双份推送过渡期），本地稳定 3 天后停用
- 重启实测开机自启（用户配合项 C2）
- 跨天增量改代码选项（sqlite_mixin + analyzer 2 处）用户已认可方向但未实施（Hermes 精选方案绕开）

## 常用文件位置
- 项目：`D:\Workspace\Projects\TrendRadar`
- 关键词 v1.0：`config/frequency_words.txt`（6 领域 13 组）
- 候选管线：`prepare_candidates.py`、`pushed_titles.json`、`stats_funnel.py`（漏斗统计）
- 启动/密钥：`start_trendradar.bat`、`run_secrets.bat`（🔴 勿上传）
- 维护脚本（Hermes scripts 目录有副本）：`watchdog_trendradar.py`、`cleanup_backup_trendradar.py`
- 日志：`output/logs/run.log`；报告：`output/html/YYYY-MM-DD/`
- 备份：`D:\Workspace\Backups\TrendRadar\trendradar_*.zip`
