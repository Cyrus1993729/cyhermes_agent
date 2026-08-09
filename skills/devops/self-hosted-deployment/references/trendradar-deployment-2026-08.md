# TrendRadar 本机迁移 — 首个落地案例（2026-08-06）

## 状态（会话结束时）
- 已确认方案A（本机 uv 本地部署），契约已写：`hermes/contracts/contract_trendradar_本地部署_2026-08-06.md`
- 追踪文件：`hermes/contracts/workflow_trendradar_本地部署_2026-08-06.md`
- Opus 红队审结论：**CONDITIONAL**（13 阻断 B1-B13 + 10 建议 S1-S10），已逐条给出解决方案，用户认可"都有解"
- 用户选**简化走**：采纳 Opus 必改项修订契约，跳过 L1 审查与复盘，修订后用户过目即开干
- 待用户提供：P1 fork 仓库 URL、P2 TrendRadar 专用 TG bot（复用 or 新建）、P3 DeepSeek key 确认

## 项目事实（TrendRadar，sansan0，61.2k star）
- Python + uv 管理（pyproject.toml + uv.lock），GPL-3.0，v6.10.0
- 定时抓多平台热榜（微博/知乎/B站/抖音/贴吧/华尔街见闻/财联社，走 newsnow API）+ RSS 订阅
- 筛选：frequency_words.txt（分组/正则/别名）或 AI 兴趣（ai_interests.txt，LiteLLM，模型格式 `provider/model`）
- 推送：TG/企业微信/个人微信/飞书/钉钉/邮件/ntfy/bark/slack；Web 报告 localhost:8080（WEBSERVER_PORT 可改）
- 存储：本地 SQLite（Docker/本地默认）或 S3 兼容（R2）；调度：timeline.yaml（v6.0.0+，含可视化周视图编辑器）
- 部署三路：Docker（wantcat/trendradar 镜像，内置 cron）、GitHub Actions（免服务器，7天签到痛点）、本地 uv（setup-windows.bat 一键装依赖）
- MCP 服务可选（localhost:3333，二期再考虑对接 Hermes）
- 用户现状：GA 部署半年，痛点=每 7 天手动签到（GA 免费额度/活跃限制，机制未核实）；对 GA 配置（关键词/推送节奏）很熟

## 方案对比结论（给用户的核心逻辑）
- 方案A 本地 uv：零新增安装（uv/git/python 齐）、进程级轻量、改配置最直接、TG 走现有 7897 代理通、无额度限制
- 方案B 本机 Docker：Docker Desktop + WSL2 VM 吃 2-4GB，8GB 老双核与 Hermes 共存吃力，无额外收益 → 出局
- 方案C 云 VPS：国内 IP 推 TG 反而要加代理中转，复杂度陡增 → 备选（用户 24h 开机故不需要）
- 迁移福利：clone 用户 fork 直接继承半年配置；R2 可切回本地 SQLite

## Opus 审查核心发现（B 级）
- B1 运行模式未定（一次性 vs 常驻）→ 实测本地调度行为后定
- B2 看门狗进程识别假阳性 → 按完整命令行（含项目路径）匹配，不按进程名
- B3 重启后登录态断链（Hermes 与 TrendRadar 同时归零）→ 系统级自启双保险
- B4 "重启实测可选"把核心需求排除在验收外 → 必须真重启实测（用户 24h 开机，成本可控）
- B6 代理分流（TG 走代理/DeepSeek 直连）+ 单实例锁 → 配置精确分流或全局代理+NO_PROXY；启动加 PID/端口锁
- B8 D2/D3 验收模糊（"能启动/无报错"）→ 改具体命令+退出码
- B10 无心跳 → 看门狗"自动拉起+拉起失败才通知"（用户=最终心跳，不做每日打扰）
- B11 密钥明文落 git 工作区 → .env + gitignore + `git remote remove origin`
- B12 用户动手项未穷举（TG /start 前置、新建 bot 步骤、改配置后生效机制）→ 用户操作清单 + 双击重启.bat
- B13 数据面空白（无轮转/清理/备份，且失去 GitHub 异地备份）→ 保留 90 天清理 + 每周打包备份
- S 级：GA 并存双份推送/git pull 冲突、资源护栏（峰值≤1GB/稳态≤400MB）、newsnow 国内 IP 实测（连续3次）、AI 成本上限、8080 端口探测、回滚方案、D7 改行为验收、D8 非交付物、7天签到前提措辞修正、"不做代码级二次开发"放宽为"不改上游业务源码，允许外围脚本"

## Opus 红队审执行要点（复用）
- 首次 `--max-turns 3` 失败："Error: Reached max turns" 且零输出（Opus 把轮次耗在工具调用上）
- 成功：`--tools ""` 禁工具 + `--max-turns 8` + 契约全文嵌入提示词（沙箱读不到本地文件）+ `tail -100` 截取
- 提示词要求：结论 PASS/CONDITIONAL/FAIL + 阻断级/建议级分级 + 每条"问题+为什么+修改建议" + 验收可判定性复核表 + 最大风险总结
